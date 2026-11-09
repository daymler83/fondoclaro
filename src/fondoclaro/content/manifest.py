from dataclasses import asdict
from decimal import Decimal

from ..config import BASE, MONTHS
from ..finance.engine import chart_window
from ..finance.formatting import direction, example_amount, money, percent
from ..render.font import width, wrap
from .templates import SLOGAN, TECH_NOTE, footer, horizon_text, meaning, whatsapp


def text_node(key, text, x, y, size, weight=400, color="#15231b", max_width=948):
    return dict(key=key, text=text, x=x, y=y, size=size, weight=weight, color=color, max_width=max_width)


def build_manifest(results):
    horizon, series = chart_window(results)
    monthly = results.metrics[1].real
    long = results.metrics[horizon].real if horizon in (12, 60, 120) else None
    monthly_str = percent(monthly)
    long_str = percent(long) if long is not None else "s/d"
    displayed_amount = example_amount(long if long is not None else series[-1][1] / BASE - 1)
    final = money(displayed_amount)
    label = horizon_text(horizon)
    explanation = meaning(results.cutoff.month, monthly, long, final, horizon)
    m = dict(schema_version=1, fund=results.fund, cutoff_date=results.cutoff.isoformat(), brand="FondoClaro", slogan=SLOGAN,
             fund_label=f"Fondo {results.fund}", month_label=f"{MONTHS[results.cutoff.month]} {results.cutoff.year}",
             r_1m=monthly_str, r_120m=percent(results.metrics[120].real) if results.metrics[120].real is not None else "s/d",
             displayed_return=long_str, horizon=horizon, base_id="LARGO_120", base_amount=str(BASE),
             amount_rounding_policy="FROM_DISPLAYED_PERCENTAGE_V1", raw_final_amount=str(series[-1][1]), displayed_final_amount=str(displayed_amount),
             chart_series=[dict(date=str(d), value=str(v)) for d, v in series],
             chart_start_label=money(BASE), chart_end_label=final, meaning_text=explanation,
             footer_text=footer(results.cutoff),
             money=[dict(text=money(BASE), base_id="LARGO_120"), dict(text=final, base_id="LARGO_120")],
             unavailable={str(k): v.reason for k, v in results.metrics.items() if v.real is None},
             financial_results=asdict(results))
    n = [text_node("brand", m["brand"], 140, 88, 40, 700, "#ffffff"),
         text_node("slogan", SLOGAN, 140, 126, 23, 400, "#ffffff"),
         text_node("fund_label", m["fund_label"], 837, 104, 28, 700, "#0f5a2c", 177),
         text_node("month_title", "Este mes", 66, 218, 30, 600, max_width=435),
         text_node("month_label", m["month_label"], 66, 352, 26, max_width=435)]
    arrow, color = direction(monthly)
    n.append(text_node("r_1m", arrow + " " + percent(monthly, svg=True) + "*", 66, 305, 68, 700, color, 435))
    if long is not None:
        n.append(text_node("long_title", "Últimos " + label, 582, 218, 30, 600, max_width=435))
        arrow, color = direction(long)
        n.extend([text_node("displayed_return", arrow + " " + percent(long, svg=True) + "*", 582, 305, 68, 700, color, 435),
                  text_node("long_subtitle", "acumulado", 582, 352, 26, max_width=435)])
    title = f"Así pudo evolucionar $10.000.000 en {label}*" if long is not None else "Historia disponible del fondo*"
    n.append(text_node("chart_title", title, 66, 439, 29, 600))
    # Globos enteramente por encima de la banda de la curva (y >= 620).
    n.extend([text_node("chart_start_label", m["chart_start_label"], 210, 561, 25, 700, "#ffffff", 245),
              text_node("chart_end_label", final, 725, 521, 28, 700, "#ffffff", 285),
              text_node("end_return", f"hoy ({percent(long, svg=True)})" if long is not None else "hoy", 725, 559, 25, 600, "#ffffff", 285)])
    values = [Decimal(p["value"]) for p in m["chart_series"]]
    million = Decimal(1000000)
    lo = (min(values) // million - 1) * million
    hi = (max(values) // million + 1) * million
    plot_height=max(232,int((hi-lo)/million)*26)
    if plot_height>272:
        raise ValueError("CHART_RANGE_EXCEEDS_LAYOUT: no reducir fuentes ni omitir rótulos")
    m["chart_scale"] = dict(left=205, right=1005, top=852-plot_height, bottom=852, lo=str(lo), hi=str(hi))
    for tick in range(int(lo / million) + 1, int(hi / million) + 1):
        v = tick * million
        y = 852 - float((v - lo) / (hi - lo)) * plot_height
        n.append(text_node(f"y_axis_{tick}", money(v, symbol=False), 66, y + 7, 21, max_width=132))
    axis_indices = sorted(set([0, len(series) - 1] + [k for k, (d, _) in enumerate(series) if d.month == 1]))
    for index in axis_indices:
        d = series[index][0]
        x = 205 + 800 * index / (len(series) - 1)
        # Primer y último mes rotulados exactos; enero por año si hay espacio.
        text = f"{MONTHS[d.month][:3]} {d.year}" if index in (0, len(series) - 1) else str(d.year)
        size = 21
        xpos = min(1008 - width(text, size), max(200, x - width(text, size) / 2))
        y = 914 if index in (0, len(series)-1) else 884
        n.append(text_node(f"x_axis_{index}", text, xpos, y, size, max_width=110))
    n.append(text_node("meaning_title", "¿Qué significa?", 66, 978, 29, 700))
    lines = wrap(explanation, 28, 940)
    if len(lines) > 3:
        raise ValueError("Explicación supera tres líneas")
    for i, line in enumerate(lines):
        n.append(text_node(f"meaning_{i}", line, 66, 1022 + i * 37, 28))
    foot_lines = wrap(TECH_NOTE, 21, 935)
    remainder = m["footer_text"][len(TECH_NOTE)+1:]
    foot_lines += wrap(remainder, 21, 935)
    if m["unavailable"]:
        foot_lines += wrap("s/d: historia insuficiente o meses faltantes; gráfico de historia disponible.", 21, 935)
    if len(foot_lines) > 7:
        raise ValueError("Pie no cabe")
    for i, line in enumerate(foot_lines):
        n.append(text_node(f"footer_{i}", line, 66, 1151 + i * 26, 21, color="#46574c"))
    m["visible_texts"] = n
    m["whatsapp_text"] = whatsapp(results.fund, results.cutoff, monthly_str.replace("-", "−"), long_str.replace("-", "−") if long is not None else None, final, horizon)
    return m
