from decimal import Decimal, ROUND_HALF_UP, localcontext

from ..config import BASE


def rounded_percent(value: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 50
        return (value * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def percent(value: Decimal, *, svg=False) -> str:
    q = rounded_percent(value)
    sign = ("+" if q > 0 else "−" if svg else "-") if q else ""
    return sign + f"{abs(q):.1f}".replace(".", ",") + "%"


def rounded_money(value: Decimal) -> Decimal:
    # quantize(Decimal('10000')) redondea a unidades: hay que dividir primero.
    with localcontext() as ctx:
        ctx.prec = 50
        return (value / 10000).quantize(Decimal(1), rounding=ROUND_HALF_UP) * 10000


def money(value: Decimal, *, symbol=True) -> str:
    return ("$" if symbol else "") + f"{int(rounded_money(value)):,}".replace(",", ".")


def example_amount(real_return: Decimal) -> Decimal:
    """Monto visible coherente con el porcentaje visible.

    Cambio de §5.4 autorizado por el usuario el 2026-11-08. La serie del gráfico
    y las métricas del motor conservan su precisión íntegra para auditoría.
    """
    with localcontext() as ctx:
        ctx.prec = 50
        return BASE * (1 + rounded_percent(real_return) / 100)


def direction(value: Decimal):
    rounded = rounded_percent(value)
    return ("↑", "#17763b") if rounded > 0 else ("↓", "#b52323") if rounded < 0 else ("→", "#55635c")
