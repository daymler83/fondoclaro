"""Lector propio y producto mensual. No importa engine ni loaders."""
import json
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

from ..config import Blocked, shift_month


def recalculate(raw_path: Path, cutoff: date, months: int) -> Decimal:
    raw = json.loads(raw_path.read_bytes())
    observations = {}
    for row in raw["observations"]:
        key = date.fromisoformat(row["date"])
        if key in observations:
            raise Blocked("INDEPENDENT_DUPLICATE")
        observations[key] = (Decimal(row["quota"]), Decimal(row["uf"]))
    with localcontext() as ctx:
        ctx.prec = 40
        value = Decimal(1)
        for offset in range(-months + 1, 1):
            prev = shift_month(cutoff, offset - 1)
            end = shift_month(cutoff, offset)
            if prev not in observations or end not in observations:
                raise Blocked("INDEPENDENT_GAP")
            qi, ui = observations[prev]
            qj, uj = observations[end]
            value *= (qj / qi) * (ui / uj)
        return value - 1


def compare(expected: Decimal, actual: Decimal):
    # Cerca de cero, error absoluto <= 1e-30; fuera de cero, relativo <= 1e-9.
    if abs(expected - actual) > max(abs(expected) * Decimal("1e-9"), Decimal("1e-30")):
        raise Blocked("INDEPENDENT_MISMATCH")
