"""Ponderaciones patrimoniales SP, sin promediar cuotas de unidades distintas.

Las dos operaciones quedan separadas: el promedio publicado de un horizonte y
el índice que encadena promedios mensuales no son idénticos por definición.
La prueba dorada comprueba si el motor basado en índice reproduce la publicación.
"""
from datetime import date
from decimal import Decimal, localcontext

from ..config import Blocked, shift_month


def period_components(months,uf,start,end,*,include_annualized=False):
    """Componentes transparentes de la media SP; sin relleno de historia AFP."""
    weights_at=shift_month(end,-1)
    dates=[]
    current=shift_month(start,0)
    while current<=end:
        dates.append(current)
        current=shift_month(current,1)
    # El diagnóstico anual puede tener inicio exacto 26-sep-2002.
    required=set(dates)|{start,end,weights_at}
    if any(d not in months or d not in uf for d in required):
        raise Blocked("SYSTEM_PERIOD_DATA_MISSING")
    active={a:r for a,r in months[weights_at].items() if r.assets>0}
    included=[]; excluded=[]
    for afp in sorted(active):
        if afp not in months[end]:
            raise Blocked("SYSTEM_ACTIVE_AFP_MISSING_AT_CUTOFF")
        if all(afp in months[d] and months[d][afp].quota>0 for d in required):
            included.append(afp)
        else:
            first=min(d for d,values in months.items() if afp in values)
            if start<first:
                excluded.append(afp)
            else:
                raise Blocked("SYSTEM_AFP_HISTORY_GAP: "+afp)
    if not included:
        raise Blocked("SYSTEM_NO_AFP_WITH_COMPLETE_HISTORY")
    with localcontext() as ctx:
        ctx.prec=40
        total=sum((active[a].assets for a in included),Decimal(0))
        components=[]
        real=nominal=Decimal(0)
        annualized=Decimal(0) if include_annualized else None
        for afp in included:
            qi,qj=months[start][afp].quota,months[end][afp].quota
            rn=qj/qi-1
            rr=(qj/qi)*(uf[start]/uf[end])-1
            ra=(1+rr)**(Decimal(365)/(end-start).days)-1 if include_annualized else None
            w=active[afp].assets/total
            real+=w*rr;nominal+=w*rn
            if include_annualized:
                annualized+=w*ra
            components.append(dict(afp=afp,weight=w,assets=active[afp].assets,quota_start=qi,quota_end=qj,real=rr,nominal=rn,annualized=ra))
    return dict(start=start,end=end,weight_date=weights_at,uf_start=uf[start],uf_end=uf[end],
                included_afps=included,excluded_afps=excluded,components=components,real=real,nominal=nominal,annualized=annualized)


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
