from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Decimal("10000000")
FUNDS = tuple("ABCDE")
MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
RISK = dict(zip(FUNDS, ("Más riesgoso", "Riesgoso", "Intermedio", "Conservador", "Más conservador")))
FONT_DIR = Path(__file__).parent / "render" / "fonts"
ZONE = ZoneInfo("America/Santiago")


class Blocked(ValueError):
    """Una validación bloqueante falló; nunca sustituir datos o metodología."""


def shift_month(d: date, n: int) -> date:
    year, month = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(year, month + 1, monthrange(year, month + 1)[1])


def period_end(period: str) -> date:
    try:
        d = date.fromisoformat(period + "-01")
        if d.strftime("%Y-%m") != period:
            raise ValueError()
        return shift_month(d, 0)
    except ValueError as exc:
        raise Blocked("Período inválido: se requiere YYYY-MM") from exc


def now() -> str:
    return datetime.now(ZONE).isoformat()
