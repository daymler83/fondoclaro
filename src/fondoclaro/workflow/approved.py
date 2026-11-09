"""Lectura verificada del catálogo de imágenes aprobadas (§9.4).

Única fuente que puede leer un canal de distribución. Ningún canal genera
imágenes ni cifras: solo entrega las ya aprobadas, tras comprobar su hash.
"""
from ..config import Blocked, FUNDS, period_end
from ..serialization import file_hash, read_json
from .states import State

SLOTS = ("all", *FUNDS)


def approved_entries(registry, period):
    """Devuelve (seleccionadas, faltantes) para el período, con hashes verificados.

    Cada seleccionada es (fund, entry, png_path). Si un hash no coincide se
    detiene con APPROVED_INDEX_INTEGRITY_MISMATCH: no se entrega nada dudoso.
    """
    period_end(period)
    path = registry.reports/"approved_index.json"
    index = read_json(path) if path.exists() else {}
    selected, missing = [], []
    for fund in SLOTS:
        entry = index.get(period+"/"+fund)
        if not entry:
            missing.append(fund)
            continue
        record, state = registry.get(entry["report_id"])
        if state["state"] not in (State.APPROVED_FOR_PUBLICATION, State.MARKED_PUBLISHED):
            missing.append(fund)
            continue
        inventory = registry.integrity(entry["report_id"])
        source = registry.directory(entry["report_id"])/"infographic.png"
        approval = read_json(source.parent/"approval.json")
        if (record["period"] != period or record["fund"] != fund or record["dev"] or
                inventory["content_hash"] != entry["content_hash"] or
                approval["content_hash"] != entry["content_hash"] or
                file_hash(source) != entry["png_hash"]):
            raise Blocked("APPROVED_INDEX_INTEGRITY_MISMATCH")
        selected.append((fund, entry, source))
    return selected, missing


def stem(fund):
    return "00_resumen_5_fondos" if fund == "all" else "fondo_"+fund


def latest_approved(registry, fund):
    """Imagen aprobada más reciente de un fondo ('all' para el resumen).

    Devuelve (period, entry, png_path) o None. Verifica el hash antes de
    devolverla: si no coincide, no entrega nada.
    """
    path = registry.reports/"approved_index.json"
    if not path.exists():
        return None
    index = read_json(path)
    periods = sorted({key.split("/")[0] for key in index if key.endswith("/"+fund)}, reverse=True)
    for period in periods:
        try:
            selected, _ = approved_entries(registry, period)
        except Blocked:
            continue
        for slot, entry, source in selected:
            if slot == fund:
                return period, entry, source
    return None


def pending_reports(registry, period=None):
    """Informes en HUMAN_REVIEW_PENDING, del período dado o del más reciente.

    Devuelve (period, [(fund, report_id, content_hash, png_path, texto)]).
    """
    found = {}
    for run_path in registry.reports.glob("*/run.json"):
        record = read_json(run_path)
        if record.get("dev"):
            continue
        try:
            _, state = registry.get(record["report_id"])
        except (KeyError, OSError, Blocked):
            continue
        if state.get("state") != State.HUMAN_REVIEW_PENDING:
            continue
        found.setdefault(record["period"], []).append(record)
    if not found:
        return None, []
    chosen = period or max(found)
    order = {slot: i for i, slot in enumerate(SLOTS)}
    rows = []
    for record in sorted(found.get(chosen, []), key=lambda r: order.get(r["fund"], 99)):
        directory = registry.directory(record["report_id"])
        rows.append((record["fund"], record["report_id"],
                     registry.integrity(record["report_id"])["content_hash"],
                     directory/"infographic.png",
                     (directory/"whatsapp_text.txt").read_text().strip()))
    return chosen, rows
