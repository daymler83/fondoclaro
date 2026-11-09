from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext

from ..config import BASE, FUNDS, Blocked, shift_month
from ..data.checks import check_series, missing_months


@dataclass(frozen=True)
class Metric:
    months: int
    status: str
    real: Decimal | None = None
    nominal: Decimal | None = None
    annualized: Decimal | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Results:
    fund: str
    cutoff: date
    metrics: dict[int, Metric]
    real_index: tuple[tuple[date, Decimal], ...]
    negative_months_120: int | None


def calculate(series, fund: str, cutoff: date) -> Results:
    check_series(series)
    if fund not in FUNDS:
        raise Blocked("Fondo desconocido")
    if cutoff >= date(2027, 4, 1):
        raise Blocked("FUND_NOT_ACTIVE: multifondos hasta marzo de 2027")
    start = date(1981, 7, 31) if fund == "C" else date(2000, 5, 31) if fund == "E" else date(2002, 9, 30)
    metrics = {}
    with localcontext() as ctx:
        ctx.prec = 40
        for n in (1, 12, 60, 120):
            begin = shift_month(cutoff, -n)
            if begin < start or missing_months(series, cutoff, n):
                metrics[n] = Metric(n, "NO_DISPONIBLE", reason="Historia insuficiente o meses faltantes")
                continue
            qi, ui = series[begin]
            qj, uj = series[cutoff]
            nominal = qj / qi - 1
            real = (qj / uj) / (qi / ui) - 1
            annual = (1 + real) ** (Decimal(12) / n) - 1 if n > 12 else None
            metrics[n] = Metric(n, "DISPONIBLE", real, nominal, annual)
        if metrics[1].real is None:
            raise Blocked("R_1M_NO_DISPONIBLE: falta mes actual/anterior o fondo inexistente")
        indices = tuple((shift_month(cutoff, -k), series[shift_month(cutoff, -k)][0] / series[shift_month(cutoff, -k)][1])
                        for k in reversed(range(121)) if shift_month(cutoff, -k) in series and shift_month(cutoff, -k) >= start)
        negative = sum(indices[k][1] < indices[k-1][1] for k in range(1, len(indices))) if metrics[120].real is not None else None
    return Results(fund, cutoff, metrics, indices, negative)


def chart_window(results: Results):
    """Único ejemplo monetario. Base conservadora para el horizonte disponible."""
    horizon = next((n for n in (120, 60, 12) if results.metrics[n].real is not None), None)
    values = dict(results.real_index)
    if horizon is None:
        # Solo tramo contiguo que termina en el mes de corte, sin cruzar huecos.
        horizon = 1
        while horizon < 120 and shift_month(results.cutoff, -horizon - 1) in values:
            horizon += 1
    begin = shift_month(results.cutoff, -horizon)
    with localcontext() as ctx:
        ctx.prec = 40
        points = tuple((shift_month(begin, k), BASE * values[shift_month(begin, k)] / values[begin]) for k in range(horizon + 1))
    return horizon, points
