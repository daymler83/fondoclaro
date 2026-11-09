from pathlib import Path
import xml.etree.ElementTree as ET

import cairosvg
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .chart import chart_svg
from .font import outlines


def render_svg(manifest):
    env = Environment(loader=FileSystemLoader(Path(__file__).parent), undefined=StrictUndefined, autoescape=select_autoescape(default=True))
    scale = manifest["chart_scale"]
    grid = "".join(f'<line x1="205" y1="{n["y"]-7}" x2="1005" y2="{n["y"]-7}" stroke="#e7ece9"/>' for n in manifest["visible_texts"] if n["key"].startswith("y_axis_"))
    # Cada enero real recibe línea vertical, tenga o no rótulo por espacio.
    for i, row in enumerate(manifest["chart_series"]):
        if row["date"][5:7] == "01":
            x = 205 + 800 * i / (len(manifest["chart_series"])-1)
            grid += f'<line x1="{x}" x2="{x}" y1="{scale["top"]}" y2="{scale["bottom"]}" stroke="#e7ece9"/>'
    def background(text):
        return "#fdeceb" if text.startswith("-") else "#e8f4ec" if text.startswith("+") else "#ffffff"
    footer_nodes = [n for n in manifest["visible_texts"] if n["key"].startswith("footer_")]
    footer_bottom = max(n["y"] + n["size"]*.18 for n in footer_nodes) + 26
    return env.get_template("svg_template.svg.j2").render(nodes=manifest["visible_texts"], chart=chart_svg(manifest), grid=grid,
                month_background=background(manifest["r_1m"]), long_background=background(manifest["displayed_return"]),
                footer_height=footer_bottom-1120)


def render_summary_svg(manifest):
    from .chart import path,points
    charts=[]
    for row in manifest["rows"]:
        fund=row["fund"]
        p=points(dict(chart_scale=manifest["spark_scales"][fund],chart_series=row["chart_series"]))
        color="#b52323" if p[-1][1]>p[-2][1] else "#17763b" if p[-1][1]<p[-2][1] else "#55635c"
        charts.append(f'<path id="mini-{fund}" d="{path(p)}" stroke="#1f63b6" stroke-width="3" fill="none"/>'
                      f'<path id="mini-last-{fund}" d="{path(p[-2:])}" stroke="{color}" stroke-width="4" fill="none" stroke-linecap="round"/>')
    env=Environment(loader=FileSystemLoader(Path(__file__).parent),undefined=StrictUndefined,autoescape=select_autoescape(default=True))
    return env.get_template("svg_summary.svg.j2").render(nodes=manifest["visible_texts"],charts="".join(charts))


def rasterize(svg: str) -> bytes:
    """Convierte textos a contornos del OTF antes de CairoSVG: no usa fontconfig."""
    from defusedxml.ElementTree import fromstring
    root = fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    for parent in list(root.iter()):
        for element in list(parent):
            if element.tag != ns + "text":
                continue
            text = "".join(element.itertext())
            markup = '<g xmlns="http://www.w3.org/2000/svg" fill="' + element.attrib["fill"] + '">' + outlines(text, float(element.attrib["x"]), float(element.attrib["y"]), float(element.attrib["font-size"]), int(element.attrib["font-weight"])) + '</g>'
            index = list(parent).index(element)
            parent.remove(element)
            parent.insert(index, ET.fromstring(markup))
    return cairosvg.svg2png(bytestring=ET.tostring(root), output_width=1080, output_height=1350)
