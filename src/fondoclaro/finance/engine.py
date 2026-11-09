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
    chart_values: tuple[tuple[date, Decimal], ...] | None = None
    method: str = "SINGLE_SERIES_ENDPOINTS"
    calculation_details: dict | None = None


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
    if results.chart_values is not None:
        return len(results.chart_values)-1, results.chart_values
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


def calculate_system(snapshots, uf, fund: str, cutoff: date, *, include_chart=True) -> Results:
    """Motor de producción: promedio SP por horizonte, curva con inicio fijo."""
    from .system import period_components
    if fund not in FUNDS or cutoff >= date(2027,4,1):
        raise Blocked("FUND_NOT_ACTIVE")
    metrics,details={},{}
    for n in (1,12,60,120):
        try:
            part=period_components(snapshots,uf,shift_month(cutoff,-n),cutoff,include_annualized=n>12)
            metrics[n]=Metric(n,"DISPONIBLE",part["real"],part["nominal"],part["annualized"] if n>12 else None)
            details[str(n)]=part
        except Blocked as exc:
            metrics[n]=Metric(n,"NO_DISPONIBLE",reason=str(exc))
    if metrics[1].real is None:
        raise Blocked("R_1M_NO_DISPONIBLE: "+str(metrics[1].reason))
    if not include_chart:
        return Results(fund,cutoff,metrics,(),None,None,"SP_HORIZON_WEIGHTED_V1",details)
    horizon=next((n for n in (120,60,12) if metrics[n].real is not None),None)
    if horizon is None:
        horizon=1
        while horizon<120 and shift_month(cutoff,-horizon-1) in snapshots and shift_month(cutoff,-horizon-1) in uf:
            horizon+=1
    begin=shift_month(cutoff,-horizon)
    curve=[(begin,BASE)]
    curve_details=[]
    with localcontext() as ctx:
        ctx.prec=40
        for k in range(1,horizon+1):
            end=shift_month(begin,k)
            part=period_components(snapshots,uf,begin,end)
            curve.append((end,BASE*(1+part["real"])))
            curve_details.append(part)
    negative=None
    if metrics[120].real is not None:
        negative=sum(period_components(snapshots,uf,shift_month(cutoff,k-1),shift_month(cutoff,k))["real"]<0 for k in range(-119,1))
    details["curve"]=curve_details
    return Results(fund,cutoff,metrics,(),negative,tuple(curve),"SP_HORIZON_WEIGHTED_V1",details)
