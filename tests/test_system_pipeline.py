"""Método SP autorizado y ejecución completa offline con archivos oficiales."""
from datetime import date
from decimal import Decimal
from dataclasses import replace
from pathlib import Path
import os
import shutil
import subprocess

import pytest

from fondoclaro.config import Blocked,shift_month
from fondoclaro.content.manifest import build_manifest
from fondoclaro.content.text_checks import validate_manifest
from fondoclaro.data.dataset import load_official_history
from fondoclaro.data.loaders import AFPObservation
from fondoclaro.finance.engine import calculate_system
from fondoclaro.finance.independent import IndependentSystem,compare
from fondoclaro.finance.system import month_snapshots
from fondoclaro.serialization import read_json,write_json
from fondoclaro.workflow.pipeline import run
from fondoclaro.workflow.registry import Registry
from fondoclaro.cli import validate_report
from fondoclaro.audit.package import verify_package

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def official():
    return load_official_history(ROOT,ROOT/"tests/fixtures/official_history/manifest_2002.json")


def test_weights_are_from_previous_month_not_current_assets():
    start,end=date(2026,9,30),date(2026,10,31)
    data={start:{"X":AFPObservation(start,"X",Decimal(100),Decimal(1000)),"Y":AFPObservation(start,"Y",Decimal(100),Decimal(3000))},
          end:{"X":AFPObservation(end,"X",Decimal(110),Decimal(9000)),"Y":AFPObservation(end,"Y",Decimal(90),Decimal(1000))}}
    r=calculate_system(data,{start:Decimal(100),end:Decimal(100)},"C",end)
    assert r.metrics[1].real==Decimal("-.05")
    assert r.metrics[1].nominal==Decimal("-.05")
    assert r.method=="SP_HORIZON_WEIGHTED_V1"


@pytest.mark.parametrize("fund",list("ABCDE"))
def test_real_horizons_and_curve_match_independent_readers(official,fund):
    result=calculate_system(month_snapshots(official.quotas[fund],official.cutoff),official.uf,fund,official.cutoff)
    other=IndependentSystem(official.csv_paths[fund],official.uf_files)
    for n in (1,12,60,120):
        recalculated=other.return_for(shift_month(official.cutoff,-n),official.cutoff)
        compare(result.metrics[n].real,recalculated["real"])
        assert recalculated["included_afps"]==result.calculation_details[str(n)]["included_afps"]
    assert result.calculation_details["120"]["excluded_afps"]==["UNO"]
    assert len(result.chart_values)==121
    assert result.chart_values[0][1]==Decimal(10000000)
    assert validate_manifest(build_manifest(result))


def test_sign_check_does_not_assume_monthly_return_equals_curve_growth(official):
    r=calculate_system(month_snapshots(official.quotas["B"],official.cutoff),official.uf,"B",official.cutoff)
    assert r.metrics[1].real<0
    assert r.chart_values[-1][1]<r.chart_values[-2][1]
    assert validate_manifest(build_manifest(r))
    points=list(r.chart_values)
    points[-2]=(points[-2][0],points[-1][1]*Decimal(".99"))
    bad=build_manifest(replace(r,chart_values=tuple(points)))
    with pytest.raises(Blocked,match="LAST_SEGMENT_MISMATCH"):
        validate_manifest(bad)


def test_all_six_reports_are_unapproved_and_auditable_offline(official,tmp_path):
    shutil.copytree(ROOT/"tests/fixtures/official_history",tmp_path/"tests/fixtures/official_history")
    write_json(tmp_path/"raw_data/history_2002_manifest.json",official.manifest)
    (tmp_path/"docs").mkdir()
    shutil.copyfile(ROOT/"docs/METODOLOGIA.md",tmp_path/"docs/METODOLOGIA.md")
    output=run(tmp_path,"all","2026-10",dev=True)
    write_json(tmp_path/"e2e_output.json",output)
    assert len(output)==6
    assert [r["fund"] for r in output]==["A","B","C","D","E","all"]
    assert all(r["state"]=="HUMAN_REVIEW_PENDING" for r in output),output
    registry=Registry(tmp_path)
    for report in output:
        validate_report(registry,report["report_id"])
        verify_package(tmp_path/"audit_packages"/report["report_id"])
        assert not (registry.directory(report["report_id"])/"approval.json").exists()
    assert not (tmp_path/"reports/approved_index.json").exists()
