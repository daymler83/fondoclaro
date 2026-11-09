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


def contrast_ratio(foreground,background):
    def luminance(color):
        color={"white":"#ffffff","black":"#000000"}.get(color,color)
        rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))
    a,b=sorted((luminance(foreground),luminance(background)))
    return (b+.05)/(a+.05)


def background_at(root,x,y):
    color="#ffffff"
    for element in root.iter():
        fill=element.get("fill")
        if not fill or fill=="none" or fill.startswith("url("):continue
        if element.tag==NS+"rect":
            left,top=float(element.get("x",0)),float(element.get("y",0))
            if left<=x<=left+float(element.get("width",0)) and top<=y<=top+float(element.get("height",0)):color=fill
        elif element.tag==NS+"circle":
            if (x-float(element.get("cx",0)))**2+(y-float(element.get("cy",0)))**2<=float(element.get("r",0))**2:color=fill
    return color


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


def validate_svg_text(svg, manifest):
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
        if contrast_ratio(node["color"],background_at(root,(box[0]+box[2])/2,node["y"]-node["size"]*.4))<4.5:
            raise Blocked(f"TEXT_CONTRAST_BELOW_AA: {node['key']}")
        rendered += NUMBERS.findall(content)
        declared += NUMBERS.findall(node["text"])
    if Counter(rendered) != Counter(declared):
        raise Blocked("SVG_NUMBERS_MISMATCH")
    return root,boxes


def validate_svg(svg, manifest):
    root,boxes=validate_svg_text(svg,manifest)
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


def validate_summary_svg(svg,manifest):
    root,boxes=validate_svg_text(svg,manifest)
    paths={p.get("id"):p for p in root.iter(NS+"path")}
    for row in manifest["rows"]:
        f=row["fund"];scale=manifest["spark_scales"][f]
        p=path_points(paths[f"mini-{f}"].get("d"))
        values=[Decimal(x["value"]) for x in row["chart_series"]]
        if len(p)!=len(values):raise Blocked("SUMMARY_POINT_COUNT")
        lo,hi=Decimal(scale["lo"]),Decimal(scale["hi"])
        for i,((x,y),value) in enumerate(zip(p,values)):
            decoded=lo+Decimal(str(scale["bottom"]-y))/Decimal(scale["bottom"]-scale["top"])*(hi-lo)
            if abs(decoded-value)>(hi-lo)/Decimal(scale["bottom"]-scale["top"])/2 or abs(x-(scale["left"]+(scale["right"]-scale["left"])*i/(len(p)-1)))>.00001:
                raise Blocked("SUMMARY_CHART_DATA_MISMATCH")
        last=paths[f"mini-last-{f}"]
        if path_points(last.get("d"))!=p[-2:]:raise Blocked("SUMMARY_LAST_SEGMENT")
        monthly=Decimal(row["raw_r_1m"])
        delta=values[-1]-values[-2]
        if ((monthly>0)-(monthly<0))!=((delta>0)-(delta<0)):raise Blocked("SUMMARY_LAST_SIGN")
        color="#b52323" if delta<0 else "#17763b" if delta>0 else "#55635c"
        if last.get("stroke")!=color:raise Blocked("SUMMARY_LAST_COLOR")
        if any(segment_box(a,b,box) for a,b in zip(p,p[1:]) for box in boxes):raise Blocked("SUMMARY_TEXT_COVERS_CHART")
    return {"svg_texts":"PASS","chart":"PASS","layout":"PASS"}


def validate_png(png):
    """Solo tamaño/formato. No implementa el hueco raster de espacios de §8.4.

    El snapshot se compara aparte con compare_png_snapshot; la mitigación actual
    de espacios rechaza tspan y usa nodos completos. Véase DECISIONES.md #8.
    """
    img = Image.open(BytesIO(png))
    if img.size != (1080,1350) or img.format != "PNG":
        raise Blocked("PNG_DIMENSIONS_FORMAT")
    img.load()
    return {"png_dimensions": "PASS"}


def compare_png_snapshot(actual_png, reference_png, *, max_channel_delta=2, max_changed_pixels=0):
    """Snapshot de píxeles: diferencia de canal <=2, cero píxeles fuera de ella.

    Los umbrales se declaran explícitamente y un desplazamiento de 1 px no se
    absorbe en una tolerancia porcentual sobre la imagen completa.
    """
    actual=Image.open(BytesIO(actual_png)).convert("RGBA")
    reference=Image.open(BytesIO(reference_png)).convert("RGBA")
    if actual.size!=reference.size:
        raise Blocked("SNAPSHOT_SIZE_MISMATCH")
    from PIL import ImageChops
    difference=ImageChops.difference(actual,reference)
    changed=sum(max(pixel)>max_channel_delta for pixel in difference.getdata())
    if changed>max_changed_pixels:
        raise Blocked(f"SNAPSHOT_PIXEL_MISMATCH: {changed} píxeles, permitidos {max_changed_pixels}; delta canal {max_channel_delta}")
    return {"snapshot":"PASS","changed_pixels":changed,"max_channel_delta":max_channel_delta,"max_changed_pixels":max_changed_pixels}
