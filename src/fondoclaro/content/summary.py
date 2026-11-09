"""Validación previa de un resumen; su composición final queda pendiente."""
from ..config import Blocked, FUNDS, RISK
from .templates import INVITATION, RISK_NOTE


def build_summary(individuals):
    if len(individuals) != 5 or [x["manifest"]["fund"] for x in individuals] != list(FUNDS):
        raise Blocked("SUMMARY_ORDER_A_TO_E_REQUIRED")
    periods = {x["manifest"]["cutoff_date"] for x in individuals}
    if len(periods) != 1:
        raise Blocked("SUMMARY_PERIOD_MISMATCH")
    rows = []
    valid_states = {"VISUALLY_VERIFIED", "HUMAN_REVIEW_PENDING", "APPROVED_FOR_PUBLICATION", "MARKED_PUBLISHED"}
    for item in individuals:
        m = item["manifest"]
        if item["state"] not in valid_states or m["r_1m"] == "s/d":
            raise Blocked("INDIVIDUAL_REPORT_NOT_VERIFIED")
        rows.append(dict(fund=m["fund"], risk=RISK[m["fund"]], r_1m=m["r_1m"], r_120m=m["r_120m"],
                         chart_series=m["chart_series"], report_id=item["report_id"], content_hash=item["content_hash"]))
    return dict(cutoff_date=periods.pop(), rows=rows, risk_note=RISK_NOTE, invitation=INVITATION)


def validate_summary(summary, individuals):
    if summary != build_summary(individuals):
        raise Blocked("SUMMARY_EXTRA_CONTENT_OR_MISMATCH: prohibido ranking/destaque")
    return {"summary": "PASS"}
