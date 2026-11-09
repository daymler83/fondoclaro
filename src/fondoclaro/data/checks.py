from calendar import monthrange
from datetime import date
from decimal import Decimal

from ..config import Blocked, shift_month


def check_series(series: dict[date, tuple[Decimal, Decimal]]):
    if not series:
        raise Blocked("NO_DATA")
    for d, (quota, uf) in series.items():
        if d.day != monthrange(d.year, d.month)[1]:
            raise Blocked("Se requiere fecha de fin de mes exacta")
        if any(not x.is_finite() or x <= 0 for x in (quota, uf)):
            raise Blocked("Cuota y UF deben ser finitas y positivas")


def missing_months(series, end, n):
    return [shift_month(end, -k) for k in range(n + 1) if shift_month(end, -k) not in series]


def select_latest(series, today):
    eligible = [d for d in series if d < today.replace(day=1) and shift_month(d, -1) in series]
    if not eligible:
        raise Blocked("NO_CLOSED_MONTH")
    return max(eligible)


def revisions(previous, current):
    return [{"date": str(d), "before": [str(v) for v in previous[d]], "after": [str(v) for v in current[d]]}
            for d in sorted(previous.keys() & current.keys()) if previous[d] != current[d]]
