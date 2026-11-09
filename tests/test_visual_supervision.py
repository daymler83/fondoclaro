"""Regresiones raster pedidas por la supervisión; datos SYNTHETIC de prueba."""
from datetime import date
from decimal import Decimal
from io import BytesIO
import math
from pathlib import Path
import re

from defusedxml.ElementTree import fromstring
from PIL import Image
import pytest

from fondoclaro.content.manifest import build_manifest
from fondoclaro.config import Blocked
from fondoclaro.content.templates import footer,whatsapp
from fondoclaro.finance.engine import calculate
from fondoclaro.render.render import rasterize,render_svg
from fondoclaro.render.visual_checks import compare_png_snapshot,path_points

from conftest import synthetic_series

NS="{http://www.w3.org/2000/svg}"
MIN_VISIBLE_SEGMENT_PIXELS=32
SNAPSHOT=Path(__file__).parent/"snapshots"/"individual_C_SYNTHETIC.png"


@pytest.mark.parametrize("monthly,color",[("-.02",(181,35,35)),(".02",(23,118,59))],ids=["negative","positive"])
def test_last_segment_visible_outside_endpoint_disk(monthly,color,tmp_path):
    manifest=build_manifest(calculate(synthetic_series(last=Decimal(monthly)),"C",date(2026,10,31)))
    svg=render_svg(manifest)
    png=rasterize(svg)
    (tmp_path/"SYNTHETIC_segment.png").write_bytes(png)
    root=fromstring(svg)
    segment=next(n for n in root.iter(NS+"path") if n.get("id")=="chart-last")
    p,q=path_points(segment.get("d"))
    marker=next(n for n in root.iter(NS+"circle") if abs(float(n.get("cx"))-q[0])<.001 and abs(float(n.get("cy"))-q[1])<.001)
    radius=float(marker.get("r"))+float(marker.get("stroke-width","0"))/2+.5
    image=Image.open(BytesIO(png)).convert("RGB")
    # Solo banda del último segmento: no cuentan la tarjeta ni el globo ni el
    # aro del punto final. Se exigen píxeles del color sólido, no antialias tenue.
    x0=max(0,math.floor(min(p[0],q[0])-4))
    x1=min(image.width,math.ceil(max(p[0],q[0])+4))
    y0=max(0,math.floor(min(p[1],q[1])-4))
    y1=min(image.height,math.ceil(max(p[1],q[1])+4))
    count=sum(image.getpixel((x,y))==color and (x+.5-q[0])**2+(y+.5-q[1])**2>radius**2
              for x in range(x0,x1) for y in range(y0,y1))
    assert count>=MIN_VISIBLE_SEGMENT_PIXELS, f"Solo {count} píxeles visibles fuera del disco; se requieren {MIN_VISIBLE_SEGMENT_PIXELS}"


@pytest.mark.parametrize("month",range(1,13))
@pytest.mark.parametrize("long,horizon",[("+40,0%",120),("−3,2%",60),("0,0%",12),(None,8)])
def test_whatsapp_month_date_and_word_limit(month,long,horizon):
    from fondoclaro.config import MONTHS,shift_month
    cutoff=shift_month(date(2026,month,1),0)
    text=whatsapp("C",cutoff,"−2,0%",long,"$14.000.000",horizon)
    image_date=re.search(r"al ([^.]+)\.",footer(cutoff))[1]
    message_date=re.search(r"al ([^.]+)\.",text)[1]
    assert message_date==image_date
    assert f"{MONTHS[month]} {cutoff.year}" in text
    assert len(text.split())<=40


def test_stored_pixel_snapshot(manifest):
    assert compare_png_snapshot(rasterize(render_svg(manifest)),SNAPSHOT.read_bytes())["snapshot"]=="PASS"


def test_snapshot_rejects_one_pixel_svg_shift(manifest):
    svg=render_svg(manifest)
    shifted=svg.replace('id="brand" x="140" y="88"','id="brand" x="140" y="89"')
    assert shifted!=svg
    with pytest.raises(Blocked,match="SNAPSHOT_PIXEL_MISMATCH"):
        compare_png_snapshot(rasterize(shifted),SNAPSHOT.read_bytes())


def test_footer_card_fits_its_content(manifest):
    root=fromstring(render_svg(manifest))
    card=next(n for n in root.iter(NS+"rect") if n.get("id")=="footer-card")
    bottom=float(card.get("y"))+float(card.get("height"))
    last=max(n["y"]+n["size"]*.18 for n in manifest["visible_texts"] if n["key"].startswith("footer_"))
    assert 24<=bottom-last<=30
    assert bottom<=1328
