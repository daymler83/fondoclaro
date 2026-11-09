import re
from datetime import date
from decimal import Decimal

from ..config import BASE, Blocked
from ..finance.formatting import direction, example_amount, money, percent
from .templates import SLOGAN, TECH_NOTE, footer, meaning

FORBIDDEN = ("perdiste", "ganaste", "tu pensión", "aproximad", "recuperará", "no te preocupes", "tranquilo", "desplome", "catástrofe", "te conviene", "cámbiate", "deberías", "mejor afp", "peor afp", "capital", "cuprum", "habitat", "modelo", "planvital", "provida", "uno", "las inversiones de largo plazo pueden tener meses difíciles", "mejor fondo")
JARGON = ("real", "nominal", "deflactad", "inflación", "uf", "ipc", "rentabilidad", "poder adquisitivo", "anualizad", "volatilidad")
NUMBERS = re.compile(r"[+−-]?\$?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?%?")
PERSONAL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b|(?:\+56\s*9|\b9\s)\s*\d{4}\s*\d{4}\b")


def reject_language(text: str, *, technical=False):
    lowered = text.casefold()
    for word in FORBIDDEN:
        if (re.search(r"\b" + re.escape(word) + r"\b", lowered) if word in ("uno", "capital", "modelo") else word in lowered):
            raise Blocked(f"FORBIDDEN_TEXT: {word}")
    if "garantiza" in lowered.replace("no garantizan", ""):
        raise Blocked("FORBIDDEN_TEXT: garantiza")
    if not technical:
        for word in JARGON:
            if re.search(r"\b" + re.escape(word), lowered):
                raise Blocked(f"JARGON: {word}")
    if PERSONAL.search(text):
        raise Blocked("PERSONAL_DATA")


def validate_manifest(m):
    monthly = Decimal(str(m["financial_results"]["metrics"][1 if 1 in m["financial_results"]["metrics"] else "1"]["real"]))
    horizon = m["horizon"]
    metrics = m["financial_results"]["metrics"]
    metric = metrics.get(horizon, metrics.get(str(horizon)))
    long = Decimal(str(metric["real"])) if horizon in (12, 60, 120) and metric and metric["real"] is not None else None
    if m["base_id"] != "LARGO_120" or m["base_amount"] != str(BASE) or any(item["base_id"] != "LARGO_120" for item in m["money"]):
        raise Blocked("MIXED_BASES")
    if m["r_1m"] != percent(monthly) or m["displayed_return"] != (percent(long) if long is not None else "s/d"):
        raise Blocked("METRIC_MISMATCH")
    points = m["chart_series"]
    values = [Decimal(p["value"]) for p in points]
    if len(points) != horizon + 1 or values[0] != BASE:
        raise Blocked("CHART_WINDOW_MISMATCH")
    from ..config import shift_month
    cutoff = date.fromisoformat(m["cutoff_date"])
    if [p["date"] for p in points] != [str(shift_month(cutoff, i-horizon)) for i in range(horizon+1)]:
        raise Blocked("CHART_DATES_MISMATCH")
    if long is not None and abs(values[-1] - BASE * (1 + long)) > Decimal("1e-20"):
        raise Blocked("ENDPOINT_MISMATCH")
    if abs(values[-1] / values[-2] - 1 - monthly) > Decimal("1e-25"):
        raise Blocked("LAST_SEGMENT_MISMATCH")
    final = money(example_amount(long if long is not None else values[-1] / BASE - 1))
    if m["chart_end_label"] != final or m["chart_start_label"] != money(BASE):
        raise Blocked("END_LABEL_MISMATCH")
    if m["meaning_text"] != meaning(cutoff.month, monthly, long, final, horizon):
        raise Blocked("MEANING_MISMATCH")
    if m["footer_text"] != footer(cutoff) or not m["footer_text"].startswith(TECH_NOTE):
        raise Blocked("SOURCE_FOOTER_MISMATCH")
    allowed_prefix = ("y_axis_", "x_axis_", "meaning_", "footer_")
    allowed_keys = {"brand", "slogan", "fund_label", "month_title", "month_label", "r_1m", "long_title", "displayed_return", "long_subtitle", "chart_title", "chart_start_label", "chart_end_label", "end_return", "meaning_title"}
    texts = m["visible_texts"]
    keys = [n["key"] for n in texts]
    if len(keys) != len(set(keys)) or any(k not in allowed_keys and not k.startswith(allowed_prefix) for k in keys):
        raise Blocked("EXTRA_CONTENT")
    by_key = {n["key"]: n for n in texts}
    for key in ("brand", "slogan", "fund_label", "month_label", "chart_start_label", "chart_end_label"):
        if by_key[key]["text"] != m[key]:
            raise Blocked("VISIBLE_TEXT_MISMATCH")
    for key, value in (("r_1m", monthly), ("displayed_return", long)):
        if value is None:
            continue
        arrow, color = direction(value)
        if by_key[key]["text"] != arrow + " " + percent(value, svg=True) + "*" or by_key[key]["color"] != color:
            raise Blocked("SIGN_ARROW_COLOR_MISMATCH")
    if " ".join(n["text"] for n in texts if n["key"].startswith("meaning_") and n["key"] != "meaning_title") != m["meaning_text"]:
        raise Blocked("MEANING_RENDER_MISMATCH")
    if not " ".join(n["text"] for n in texts if n["key"].startswith("footer_")).startswith(m["footer_text"]):
        raise Blocked("FOOTER_RENDER_MISMATCH")
    expected_end = f"hoy ({percent(long, svg=True)})" if long is not None else "hoy"
    if by_key["end_return"]["text"] != expected_end or not by_key["chart_title"]["text"].endswith("*"):
        raise Blocked("END_RETURN_ASTERISK_MISMATCH")
    for index in (0, horizon):
        d = date.fromisoformat(points[index]["date"])
        if str(d.year) not in by_key[f"x_axis_{index}"]["text"]:
            raise Blocked("AXIS_YEAR_MISMATCH")
    for node in texts:
        reject_language(node["text"], technical=node["key"].startswith("footer_"))
    reject_language(m["whatsapp_text"], technical=True)
    allowed_numbers = set(NUMBERS.findall(" ".join(n["text"] for n in texts))) | set(NUMBERS.findall(m["cutoff_date"]))
    if set(NUMBERS.findall(m["whatsapp_text"])) - allowed_numbers:
        raise Blocked("WHATSAPP_UNKNOWN_NUMBER")
    if len(m["whatsapp_text"].split()) > 40:
        raise Blocked("WHATSAPP_TOO_LONG")
    # También fija todos los rótulos y números auxiliares: no se puede introducir
    # una tarjeta extra disfrazándola con una clave permitida.
    from ..finance.engine import Metric, Results
    from .manifest import build_manifest
    from ..serialization import canonical
    fr = m["financial_results"]
    metrics = {int(k): Metric(int(v["months"]), v["status"],
                *(Decimal(str(v[x])) if v[x] is not None else None for x in ("real", "nominal", "annualized")), v["reason"]) for k,v in fr["metrics"].items()}
    restored = Results(fr["fund"], date.fromisoformat(str(fr["cutoff"])), metrics,
                       tuple((date.fromisoformat(str(d)), Decimal(str(v))) for d,v in fr["real_index"]), fr["negative_months_120"])
    if canonical(m) != canonical(build_manifest(restored)):
        raise Blocked("MANIFEST_NOT_CANONICAL: cifra o texto extra")
    return {"content": "PASS"}
