"""Aceptación real §6.1: nunca SKIP, XFAIL ni datos SYNTHETIC."""
from pathlib import Path

from fondoclaro.finance.golden import evaluate_history
from fondoclaro.serialization import canonical,write_json

ROOT=Path(__file__).resolve().parents[1]


def test_golden_sp_24_months_five_funds(tmp_path):
    report=evaluate_history(ROOT,ROOT/"tests/fixtures/official_history/manifest.json")
    write_json(tmp_path/"golden_result.json",report)
    assert len(report["months"])>=24
    assert report["funds"]==list("ABCDE")
    assert report["compared"]>=24*5*2
    assert report["failed"]==0, canonical({key:report[key] for key in ("status","compared","failed","max_difference_pp","worst_case","by_metric","annualized_status")}).decode()
    assert report["status"]=="PASS",report["annualized_status"]
