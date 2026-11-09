"""Orquestación con cierre seguro mientras §6.1 siga bloqueada.

No hay un flag que convierta fixtures sintéticos en informes publicables.
La conexión de fuentes al pipeline requiere resolver los bloqueos documentados.
"""
from datetime import datetime
from uuid import uuid4

from ..config import Blocked, FUNDS, ZONE, period_end
from ..serialization import write_json
from .registry import Registry
from .states import State

READINESS_BLOCKERS = (
    "OFFICIAL_GOLDEN_MISSING: faltan 24 meses × 5 fondos validados (§6.1)",
    "SYSTEM_SERIES_UNVERIFIED: no hay serie de cuota del sistema validada contra todos los horizontes SP",
    "UF_HISTORY_MISSING: no hay archivo histórico de UF de fin de mes verificado",
)


def run(root, fund, period, *, dev=False):
    registry = Registry(root)
    if period != "latest":
        cutoff = period_end(period)
        if cutoff >= datetime.now(ZONE).date().replace(day=1):
            raise Blocked("PERIOD_NOT_CLOSED")
    run_id = uuid4().hex
    outputs = []
    for selected in FUNDS if fund == "all" else (fund,):
        report_id = registry.create(selected, period, run_id=run_id, dev=dev)
        record, _ = registry.get(report_id)
        reasons = list(READINESS_BLOCKERS)
        if record["code_version"]["dirty"] and not dev:
            reasons.insert(0, "DIRTY_OR_UNVERSIONED_CODE: requiere commit limpio o --dev")
        # Nunca consumir la rentabilidad SP como dato de entrada ni reconstruir
        # artificialmente una cuota para esquivar la validación dorada.
        registry.transition(report_id, State.BLOCKED, stage="PREFLIGHT", reasons=reasons)
        outputs.append(dict(report_id=report_id, fund=selected, state=State.BLOCKED, reasons=reasons))
    if fund == "all":
        report_id = registry.create("all", period, run_id=run_id, dev=dev)
        registry.transition(report_id, State.BLOCKED, stage="SUMMARY", reasons=["INDIVIDUAL_REPORTS_NOT_VISUALLY_VERIFIED"], references=[r["report_id"] for r in outputs])
        outputs.append(dict(report_id=report_id, fund="all", state=State.BLOCKED, reasons=["INDIVIDUAL_REPORTS_NOT_VISUALLY_VERIFIED"]))
        write_json(root/"reports"/("review_"+run_id+".json"), outputs)
    return outputs
