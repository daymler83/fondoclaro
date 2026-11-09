from decimal import Decimal

from ..config import MONTHS
from ..finance.formatting import rounded_percent

SLOGAN = "Tus ahorros, explicados en 30 segundos"
TECH_NOTE = "* Descontada la inflación (variación de la UF). Montos en pesos de hoy."
RISK_NOTE = "Cada fondo tiene un nivel de riesgo distinto: más riesgo suele significar subidas y bajadas más grandes. Esto no es una recomendación para cambiarse."
INVITATION = "¿Quieres el gráfico de tu fondo cada mes? Respóndeme con tu letra: A, B, C, D o E."


def horizon_text(months):
    return f"{months // 12} años" if months >= 12 else f"{months} meses"


def meaning(month: int, monthly: Decimal, long: Decimal | None, final: str, horizon: int):
    name = MONTHS[month]
    sign = rounded_percent(monthly)
    first = f"{name.capitalize()} fue un mes {'positivo' if sign > 0 else 'negativo'}." if sign else f"En {name} el fondo no cambió."
    if long is None:
        return first + " El gráfico muestra la historia disponible."
    opposite = sign != 0 and rounded_percent(long) != 0 and (sign > 0) != (rounded_percent(long) > 0)
    return first + (f" Aun así, en {horizon_text(horizon)} " if opposite else f" En {horizon_text(horizon)}, ") + f"$10.000.000 pasaron a ser {final}."


def cutoff_label(cutoff):
    return f"{cutoff.day:02d}-{MONTHS[cutoff.month][:3]}-{cutoff.year}"


def footer(cutoff, *, summary=False):
    return TECH_NOTE + f" Fuente: Superintendencia de Pensiones y Banco Central, al {cutoff_label(cutoff)}. " + ("Promedio del sistema por tipo de fondo. No es una recomendación." if summary else "Promedio del sistema. Monto de ejemplo. No es una recomendación.")


def whatsapp(fund, cutoff, monthly, long, final, horizon):
    # 40 palabras, fuente y fecha exacta incluidas. No usa segunda base monetaria.
    intro = f"FondoClaro · Fondo {fund} · {MONTHS[cutoff.month]} {cutoff.year}: {monthly}* en el mes."
    if long is not None:
        intro = f"FondoClaro · Fondo {fund} · {MONTHS[cutoff.month]} {cutoff.year}: {monthly}* mensual; {long}* en {horizon_text(horizon)}. $10.000.000 pasaron a {final}."
    text = intro + f" *Descontada la inflación. Fuente: Superintendencia de Pensiones y Banco Central, al {cutoff_label(cutoff)}."
    if len(text.split()) > 40:
        raise ValueError("Texto WhatsApp excede 40 palabras")
    return text
