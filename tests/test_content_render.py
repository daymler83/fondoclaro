from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from fondoclaro.config import Blocked
from fondoclaro.content.manifest import build_manifest
from fondoclaro.content.summary import build_summary, validate_summary
from fondoclaro.content.templates import meaning
from fondoclaro.content.text_checks import reject_language, validate_manifest
from fondoclaro.finance.engine import calculate
from fondoclaro.render.render import rasterize, render_svg
from fondoclaro.render.visual_checks import segment_box, validate_png, validate_svg
from fondoclaro.serialization import canonical

from conftest import synthetic_series


@pytest.mark.parametrize("month,long,phrase",[("-.02",".48","Aun así"),(".02",".48","En 10 años,"),("-.02","-.48","En 10 años,"),(".02","-.48","Aun así"),("0",".48","no cambió")])
def test_five_templates(month,long,phrase):
    assert phrase in meaning(10,Decimal(month),Decimal(long),"$14.800.000",120)


def test_manifest_roundtrip(manifest):
    import json
    assert validate_manifest(json.loads(canonical(manifest))) == {"content":"PASS"}


def test_negative_tie_keeps_visible_numbers_consistent():
    m=build_manifest(calculate(synthetic_series(monthly=Decimal(0),last=Decimal("-.0005")),"C",date(2026,10,31)))
    assert m["displayed_return"] == "-0,1%"
    assert m["chart_end_label"] == "$9.990.000"
    assert Decimal(m["raw_final_amount"]) == Decimal(9995000)
    assert Decimal(m["displayed_final_amount"]) == Decimal(9990000)
    assert "$9.990.000" in m["meaning_text"]
    assert "$9.990.000" in m["whatsapp_text"]
    assert validate_manifest(m)


def test_all_january_years_are_labeled(manifest):
    keys={n["key"] for n in manifest["visible_texts"]}
    for i,p in enumerate(manifest["chart_series"]):
        if p["date"][5:7]=="01":
            assert f"x_axis_{i}" in keys


@pytest.mark.parametrize("months",[120,75,30,8])
def test_manifest_and_svg_available_horizons(months):
    m=build_manifest(calculate(synthetic_series(months=months),"C",date(2026,10,31)))
    assert validate_manifest(m)
    assert validate_svg(render_svg(m),m)


def test_svg_and_png_deterministic(manifest,tmp_path):
    svg=render_svg(manifest)
    assert validate_svg(svg,manifest)
    a,b=rasterize(svg),rasterize(svg)
    assert a == b
    assert validate_png(a)
    (tmp_path/"SYNTHETIC_UNIT_TEST.png").write_bytes(a)


@pytest.mark.parametrize("phrase",["Perdiste $200.000", "Tu pensión en 30 segundos", "Cifras aproximadas", "No te preocupes", "te conviene cambiarte", "mejor AFP", "CAPITAL", "El fondo se recuperará", "Las inversiones de largo plazo pueden tener meses difíciles y aun así generar crecimiento"])
def test_forbidden_language(phrase):
    with pytest.raises(Blocked):
        reject_language(phrase)


def test_regression_E1_mixed_bases(manifest):
    manifest["money"][1]["base_id"]="MES"
    with pytest.raises(Blocked,match="MIXED_BASES"):
        validate_manifest(manifest)


def test_regression_E2_wrong_last_segment(manifest):
    manifest["chart_series"][-1]["value"]=str(Decimal(manifest["chart_series"][-2]["value"])*Decimal("1.02"))
    with pytest.raises(Blocked):
        validate_manifest(manifest)


@pytest.mark.parametrize("error,phrase",[("E3","Cifras aproximadas"),("E4","Tu pensión en 30 segundos"),("E5","Perdiste $200.000"),("E9","Las inversiones de largo plazo pueden tener meses difíciles y aun así generar crecimiento")])
def test_regressions_forbidden_text_in_svg(manifest,error,phrase):
    svg=render_svg(manifest).replace("¿Qué significa?",phrase)
    with pytest.raises(Blocked,match="TEXT_MISMATCH"):
        validate_svg(svg,manifest)


def test_regression_E6_footer_missing_cutoff(manifest):
    manifest["footer_text"]="Fuente: SP y Banco Central"
    with pytest.raises(Blocked,match="FOOTER"):
        validate_manifest(manifest)


def test_regression_E7_area_beyond_line(manifest):
    svg=render_svg(manifest).replace("L1005.000000,852", "L1030.000000,852")
    with pytest.raises(Blocked,match="AREA_EXCEEDS"):
        validate_svg(svg,manifest)


def test_regression_E8_wrong_axis_year(manifest):
    next(n for n in manifest["visible_texts"] if n["key"]=="x_axis_120")["text"]="oct 2025"
    with pytest.raises(Blocked,match="AXIS_YEAR"):
        validate_manifest(manifest)


def test_regression_E10_extra_cards(manifest):
    manifest["visible_texts"].append(dict(key="r_12m",text="+20,0%",x=10,y=20,size=60,weight=700,color="#17763b",max_width=400))
    with pytest.raises(Blocked,match="EXTRA_CONTENT"):
        validate_manifest(manifest)


def test_disguised_extra_numbers(manifest):
    next(n for n in manifest["visible_texts"] if n["key"]=="long_subtitle")["text"]="5 años +20,0%"
    with pytest.raises(Blocked,match="CANONICAL"):
        validate_manifest(manifest)


def summary_inputs(manifest):
    rows=[]
    for fund in "ABCDE":
        m=deepcopy(manifest)
        m["fund"]=fund
        rows.append(dict(manifest=m,state="VISUALLY_VERIFIED",report_id=fund,content_hash=fund*64))
    return rows


def test_summary_contract(manifest):
    inputs=summary_inputs(manifest)
    summary=build_summary(inputs)
    assert validate_summary(summary,inputs)
    assert [r["fund"] for r in summary["rows"]] == list("ABCDE")
    assert summary["invitation"] and summary["risk_note"]


@pytest.mark.parametrize("mutation",["reorder","highlight","metric"])
def test_regression_E11_summary_no_ranking(manifest,mutation):
    inputs=summary_inputs(manifest)
    summary=build_summary(inputs)
    if mutation=="reorder":
        summary["rows"].reverse()
    elif mutation=="highlight":
        summary["rows"][0]["best"]=True
    else:
        summary["rows"][0]["r_1m"]="+9,0%"
    with pytest.raises(Blocked):
        validate_summary(summary,inputs)


def test_summary_requires_verification(manifest):
    inputs=summary_inputs(manifest)
    inputs[2]["state"]="BLOCKED"
    with pytest.raises(Blocked):
        build_summary(inputs)


def test_space_and_color_tampering(manifest):
    svg=render_svg(manifest)
    with pytest.raises(Blocked):
        validate_svg(svg.replace("Aun así, en","Aun así,en"),manifest)
    with pytest.raises(Blocked):
        validate_svg(svg.replace('fill="#b52323"','fill="#17763b"'),manifest)


def test_box_intersection():
    assert segment_box((0,0),(100,100),(49,49,51,51))
    assert not segment_box((0,0),(100,0),(49,49,51,51))
