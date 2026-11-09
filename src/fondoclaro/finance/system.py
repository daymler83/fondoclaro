"""Ponderaciones patrimoniales SP, sin promediar cuotas de unidades distintas.

Las dos operaciones quedan separadas: el promedio publicado de un horizonte y
el índice que encadena promedios mensuales no son idénticos por definición.
La prueba dorada comprueba si el motor basado en índice reproduce la publicación.
"""
from datetime import date
from decimal import Decimal, localcontext

from ..config import Blocked, shift_month


def month_snapshots(observations, cutoff):
    months = {}
    for row in observations:
        if row.confirmed and row.date <= cutoff and row.date == shift_month(row.date, 0):
            months.setdefault(row.date, {})[row.afp] = row
    if not months:
        raise Blocked("SYSTEM_NO_MONTH_END_DATA")
    return months


def weighted_period_return(months, uf, cutoff, horizon, *, annualized=False):
    """Promedio de retornos por AFP ponderado con patrimonio del mes anterior.

    Fuente: informe SP junio 2025, nota 8 (igual peso de referencia en todas las
    columnas de su tabla). La fórmula por AFP anualiza por 365/días cuando aplica.
    No se invoca este método como sustituto del motor durante el contraste.
    """
    start, weight_date = shift_month(cutoff, -horizon), shift_month(cutoff, -1)
    if any(d not in months for d in (start, weight_date, cutoff)) or start not in uf or cutoff not in uf:
        raise Blocked("SYSTEM_PERIOD_DATA_MISSING")
    eligible = [afp for afp, row in months[weight_date].items() if row.assets > 0]
    if any(afp not in months[start] or afp not in months[cutoff] for afp in eligible):
        raise Blocked("SYSTEM_AFP_HISTORY_MISSING: no renormalizar ponderaciones")
    with localcontext() as ctx:
        ctx.prec = 40
        assets = sum((months[weight_date][afp].assets for afp in eligible), Decimal(0))
        if assets <= 0:
            raise Blocked("SYSTEM_ZERO_ASSETS")
        total = Decimal(0)
        for afp in eligible:
            factor = months[cutoff][afp].quota / months[start][afp].quota * uf[start] / uf[cutoff]
            value = factor ** (Decimal(365) / (cutoff-start).days) - 1 if annualized else factor - 1
            total += months[weight_date][afp].assets / assets * value
        return total


def build_system_index(observations, uf, cutoff):
    """Índice nominal encadenado desde cuotas/patrimonios, sin usar contraste SP.

    Se deflacta una sola vez en engine.py. No es una cuota oficial publicada.
    La normalización inicial 100 se cancela en todos los cocientes.
    """
    months = month_snapshots(observations, cutoff)
    dates = sorted(months)
    if dates[-1] != cutoff:
        raise Blocked("SYSTEM_CUTOFF_MISSING")
    for i, d in enumerate(dates):
        if d not in uf or i and shift_month(dates[i-1],1) != d:
            raise Blocked("SYSTEM_MONTH_OR_UF_GAP")
    with localcontext() as ctx:
        ctx.prec = 40
        index = Decimal(100)
        output, steps = {dates[0]: (index,uf[dates[0]])}, []
        for previous, current in zip(dates, dates[1:]):
            active = {afp: row for afp,row in months[previous].items() if row.assets > 0}
            if not active or set(active) - months[current].keys():
                raise Blocked("SYSTEM_ACTIVE_AFP_MISSING")
            assets = sum((row.assets for row in active.values()),Decimal(0))
            factor, components = Decimal(0), []
            for afp,row in sorted(active.items()):
                weight = row.assets/assets
                afp_factor = months[current][afp].quota/row.quota
                factor += weight*afp_factor
                components.append(dict(afp=afp, assets=row.assets, weight=weight, quota_start=row.quota,
                                       quota_end=months[current][afp].quota, nominal_factor=afp_factor))
            index *= factor
            output[current] = (index,uf[current])
            steps.append(dict(date=current,weight_date=previous,nominal_factor=factor,system_nominal_index=index,
                              uf=uf[current],components=components))
    return output, steps
