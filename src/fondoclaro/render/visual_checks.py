import re
from collections import Counter
from decimal import Decimal
from io import BytesIO

from defusedxml.ElementTree import fromstring
from PIL import Image

from ..config import Blocked
from ..content.text_checks import NUMBERS
from .font import width

NS = "{http://www.w3.org/2000/svg}"


def path_points(d):
    return [(float(x), float(y)) for x, y in re.findall(r"[ML]\s*([-\d.]+),([-\d.]+)", d)]


def segment_box(p, q, box):
    """Liang–Barsky: intersección exacta de segmento y rectángulo."""
    x0, y0, x1, y1 = box
    dx, dy = q[0]-p[0], q[1]-p[1]
    lower, upper = 0., 1.
    for a, b in ((-dx, p[0]-x0), (dx, x1-p[0]), (-dy, p[1]-y0), (dy, y1-p[1])):
        if a == 0:
            if b < 0:
                return False
        elif a < 0:
            lower = max(lower, b/a)
        else:
            upper = min(upper, b/a)
        if lower > upper:
            return False
    return True


def validate_svg(svg, manifest):
    root = fromstring(svg)
    elements = list(root.iter(NS+"text"))
    expected = manifest["visible_texts"]
    if len(elements) != len(expected):
        raise Blocked("SVG_EXTRA_OR_MISSING_TEXT")
    rendered, declared, boxes = [], [], []
    for element, node in zip(elements, expected):
        content = "".join(element.itertext())
        if content != node["text"] or element.attrib.get("id") != node["key"]:
            raise Blocked("SVG_TEXT_MISMATCH_INCLUDING_SPACES")
        if list(element):
            raise Blocked("TSPAN_NOT_SUPPORTED: usar nodos completos para preservar espacios")
        if element.attrib.get("{http://www.w3.org/XML/1998/namespace}space") != "preserve":
            raise Blocked("SVG_SPACE_NOT_PRESERVED")
        for attr, key in (("font-size", "size"), ("font-weight", "weight"), ("x", "x"), ("y", "y")):
            if float(element.attrib[attr]) != float(node[key]):
                raise Blocked("SVG_STYLE_POSITION_MISMATCH")
        if element.attrib["fill"] != node["color"]:
            raise Blocked("SVG_COLOR_MISMATCH")
        w = width(content, node["size"], node["weight"])
        if w > node["max_width"] or node["x"]+w > 1044:
            raise Blocked(f"TEXT_OVERFLOW: {node['key']}")
        box = (node["x"], node["y"]-node["size"], node["x"]+w, node["y"]+node["size"]*.18)
        if min(box) < 0 or box[3] > 1350:
            raise Blocked("TEXT_OUTSIDE_CANVAS")
        for other in boxes:
            if box[0] < other[2] and box[2] > other[0] and box[1] < other[3] and box[3] > other[1]:
                raise Blocked(f"TEXT_OVERLAP: {node['key']}")
        boxes.append(box)
        rendered += NUMBERS.findall(content)
        declared += NUMBERS.findall(node["text"])
    if Counter(rendered) != Counter(declared):
        raise Blocked("SVG_NUMBERS_MISMATCH")
    paths = {p.attrib.get("id"): p for p in root.iter(NS+"path")}
    line = path_points(paths["chart-line"].attrib["d"])
    scale = manifest["chart_scale"]
    values = [Decimal(p["value"]) for p in manifest["chart_series"]]
    if len(line) != len(values):
        raise Blocked("CHART_POINT_COUNT")
    lo, hi = Decimal(scale["lo"]), Decimal(scale["hi"])
    tolerance = (hi-lo) / Decimal(scale["bottom"]-scale["top"]) / 2
    for i, ((x, y), value) in enumerate(zip(line, values)):
        expected_x = scale["left"]+(scale["right"]-scale["left"])*i/(len(values)-1)
        decoded = lo + Decimal(str(scale["bottom"]-y)) / Decimal(scale["bottom"]-scale["top"]) * (hi-lo)
        if abs(decoded-value) > tolerance or abs(x-expected_x) > 0.00001:
            raise Blocked("CHART_DATA_MISMATCH")
    last = path_points(paths["chart-last"].attrib["d"])
    if last != line[-2:]:
        raise Blocked("LAST_SEGMENT_GEOMETRY")
    color = "#b52323" if values[-1] < values[-2] else "#17763b" if values[-1] > values[-2] else "#55635c"
    if paths["chart-last"].attrib["stroke"] != color:
        raise Blocked("LAST_SEGMENT_COLOR")
    area = path_points(paths["chart-area"].attrib["d"])
    if area[:len(line)] != line or min(x for x,y in area) < line[0][0] or max(x for x,y in area) > line[-1][0]:
        raise Blocked("AREA_EXCEEDS_LINE_DOMAIN")
    for box in boxes + [(200,526,470,586), (715,482,1020,584)]:
        if any(segment_box(p, q, box) for p,q in zip(line, line[1:])):
            raise Blocked("TEXT_OR_BALLOON_COVERS_CHART")
    return {"svg_texts": "PASS", "chart": "PASS", "layout": "PASS"}


def validate_png(png):
    img = Image.open(BytesIO(png))
    if img.size != (1080,1350) or img.format != "PNG":
        raise Blocked("PNG_DIMENSIONS_FORMAT")
    img.load()
    return {"png_dimensions": "PASS"}
