"""Maqueta de la imagen resumen "Los 5 fondos" (cifras ficticias).

Pensada para el primer envío a contactos cuyo fondo no se conoce, y para reenviar
en grupos. Reutiliza estilo y utilidades de render_maqueta.py.

Uso: python render_resumen.py [salida_sin_extension]
"""
import math
import random
import subprocess
import sys
from decimal import Decimal

import render_maqueta as rm
from render_maqueta import (W, H, M, GREEN, GREEN_DARK, GREEN_BG, BLUE, RED, RED_BG, INK, MUTED,
                            PAGE, CHECKS, card, text, rich, arrow, pct, tw, wrap_rich)

MES, ANIO = "octubre", 2026
# (letra, etiqueta de riesgo, r_1m, r_120m) — FICTICIOS
FONDOS = [
    ("A", "Más riesgoso", Decimal("-0.031"), Decimal("0.620")),
    ("B", "Riesgoso", Decimal("-0.026"), Decimal("0.550")),
    ("C", "Intermedio", Decimal("-0.020"), Decimal("0.480")),
    ("D", "Conservador", Decimal("-0.012"), Decimal("0.350")),
    ("E", "Más conservador", Decimal("-0.004"), Decimal("0.240")),
]


def series(r1, r120, vol, seed):
    rnd = random.Random(seed)
    logs = [rnd.gauss(0, vol) for _ in range(119)]
    target = math.log(float((1 + r120) / (1 + r1)))
    shift = (target - sum(logs)) / len(logs)
    vals = [1.0]
    for x in logs:
        vals.append(vals[-1] * math.exp(x + shift))
    vals.append(float(1 + r120))
    return vals


def sparkline(x, y, w, h, vals, r1):
    lo, hi = min(vals), max(vals)
    pts = [(x + w * i / (len(vals) - 1), y + h - h * (v - lo) / (hi - lo)) for i, v in enumerate(vals)]
    out = [f'<path d="M{" L".join(f"{a:.1f},{b:.1f}" for a, b in pts[:-1])}" fill="none" '
           f'stroke="{BLUE}" stroke-width="3.5" stroke-linejoin="round"/>']
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    col = RED if r1 < 0 else GREEN
    out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{col}" '
               f'stroke-width="5" stroke-linecap="round"/>')
    out.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="6" fill="#fff" stroke="{col}" stroke-width="3.5"/>')
    CHECKS.append((f"minigráfico: último tramo según signo", (y1 > y0) == (r1 < 0), ""))
    return "\n".join(out)


def build():
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}">', f'<rect width="{W}" height="{H}" fill="{PAGE}"/>']

    # encabezado
    hx, hy, hw, hh = M, M, W - 2 * M, 112
    out.append(card(hx, hy, hw, hh, GREEN, r=30))
    for i, h in enumerate((22, 36, 50)):
        out.append(f'<rect x="{hx + 30 + i * 17}" y="{hy + 81 - h}" width="12" height="{h}" rx="3" fill="#ffffff"/>')
    out.append(text(hx + 104, hy + 56, "FondoClaro", 40, 800, "#ffffff"))
    out.append(text(hx + 104, hy + 90, "Tus ahorros, explicados en 30 segundos", 23, 500, "#d6f0de"))
    pill = f"{MES.capitalize()} {ANIO}"
    pw = tw(pill, 28, 700) + 46
    out.append(card(hx + hw - pw - 26, hy + 28, pw, 56, "#ffffff", r=28))
    out.append(text(hx + hw - 26 - pw / 2, hy + 66, pill, 28, 700, GREEN_DARK, "middle"))

    # tabla
    tx, ty, tw_, th = M, hy + hh + 22, W - 2 * M, 862
    out.append(card(tx, ty, tw_, th, "#ffffff", stroke="#e1e7e3"))
    out.append(text(tx + 30, ty + 56, "¿Cómo le fue a cada fondo?", 32, 800, INK, max_w=tw_ - 60))
    c_fondo, c_mes, c_10, c_sp = tx + 30, tx + 352, tx + 568, tx + 790
    sp_w = tx + tw_ - 30 - c_sp
    hy2 = ty + 108
    out.append(text(c_fondo, hy2, "Fondo", 23, 700, MUTED))
    out.append(text(c_mes, hy2, "Este mes*", 23, 700, MUTED))
    out.append(text(c_10, hy2, "10 años*", 23, 700, MUTED))
    out.append(text(c_sp, hy2, "Evolución", 23, 700, MUTED))
    row_h = 130
    for k, (letra, riesgo, r1, r120) in enumerate(FONDOS):
        ry = ty + 128 + k * row_h
        if k % 2 == 0:
            out.append(f'<rect x="{tx + 12}" y="{ry}" width="{tw_ - 24}" height="{row_h}" rx="18" fill="#f6f9f7"/>')
        cy = ry + row_h / 2
        out.append(f'<circle cx="{c_fondo + 34}" cy="{cy}" r="34" fill="{GREEN}"/>')
        out.append(text(c_fondo + 34, cy + 15, letra, 42, 800, "#ffffff", "middle"))
        out.append(text(c_fondo + 84, cy - 4, f"Fondo {letra}", 30, 700, INK, max_w=c_mes - c_fondo - 100))
        out.append(text(c_fondo + 84, cy + 30, riesgo, 22, 500, MUTED, max_w=c_mes - c_fondo - 100))
        col1 = RED if r1 < 0 else GREEN
        out.append(arrow(c_mes + 14, cy - 2, 15, r1 >= 0, col1))
        out.append(text(c_mes + 38, cy + 15, pct(r1), 40, 800, col1, max_w=c_10 - c_mes - 50))
        col2 = GREEN if r120 >= 0 else RED
        out.append(arrow(c_10 + 14, cy - 2, 15, r120 >= 0, col2))
        out.append(text(c_10 + 38, cy + 15, pct(r120), 40, 800, col2, max_w=c_sp - c_10 - 50))
        vol = {"A": 0.016, "B": 0.013, "C": 0.011, "D": 0.007, "E": 0.004}[letra]
        out.append(sparkline(c_sp, cy - 38, sp_w, 76, series(r1, r120, vol, 11 + k), r1))
    risk_y = ty + 128 + 5 * row_h + 34
    out.append(text(tx + 30, risk_y, "Cada fondo tiene un nivel de riesgo distinto: más riesgo suele significar",
                    22, 500, MUTED, max_w=tw_ - 60))
    out.append(text(tx + 30, risk_y + 30, "subidas y bajadas más grandes. Esto no es una recomendación para cambiarse.",
                    22, 500, MUTED, max_w=tw_ - 60))

    # invitación
    iy, ih = ty + th + 20, 128
    out.append(card(M, iy, W - 2 * M, ih, GREEN_BG, stroke="#bfe0c9"))
    words = [("¿Quieres", 800, GREEN_DARK), ("el", 800, GREEN_DARK), ("gráfico", 800, GREEN_DARK),
             ("de", 800, GREEN_DARK), ("tu", 800, GREEN_DARK), ("fondo", 800, GREEN_DARK),
             ("cada", 800, GREEN_DARK), ("mes?", 800, GREEN_DARK)]
    words += [(w, 500, INK) for w in "Respóndeme con tu letra: A, B, C, D o E.".split()]
    lines = wrap_rich(words, 29, W - 2 * M - 60)
    CHECKS.append(("invitación cabe en 2 líneas", len(lines) <= 2, f"{len(lines)} líneas"))
    for i, ln in enumerate(lines):
        out.append(rich(M + 30, iy + 54 + i * 40, ln, 29, W - 2 * M - 60))

    # pie
    fy = iy + ih + 34
    out.append(f'<circle cx="{M + 16}" cy="{fy - 8}" r="14" fill="none" stroke="{MUTED}" stroke-width="2.5"/>')
    out.append(text(M + 16, fy, "i", 20, 800, MUTED, "middle"))
    out.append(text(M + 42, fy, "* Descontada la inflación (variación de la UF). Acumulado en 10 años.",
                    21, 600, MUTED, max_w=W - 2 * M - 42))
    out.append(text(M + 42, fy + 28, f"Fuente: Superintendencia de Pensiones y Banco Central, al 31-oct-{ANIO}.",
                    21, 500, MUTED, max_w=W - 2 * M - 42))
    out.append(text(M + 42, fy + 56, "Promedio del sistema por tipo de fondo. No es una recomendación.",
                    21, 500, MUTED, max_w=W - 2 * M - 42))
    tag = "MAQUETA · CIFRAS FICTICIAS"
    tgw = tw(tag, 18, 700) + 24
    out.append(card(W - M - tgw, fy + 72, tgw, 30, "#fff1cc", r=15))
    out.append(text(W - M - tgw / 2, fy + 93, tag, 18, 700, "#8a5a00", "middle"))
    CHECKS.append(("todo dentro del alto", fy + 104 <= H, f"termina en {fy + 104:.0f} <= {H}"))
    CHECKS.append(("nota de riesgo dentro de la tabla", risk_y + 30 + 14 <= ty + th, ""))
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "maqueta_resumen_5_fondos"
    svg = build()
    open(name + ".svg", "w", encoding="utf-8").write(svg)
    subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), name + ".svg", "-o", name + ".png"], check=True)
    bad = 0
    for label, ok, info in CHECKS:
        bad += not ok
        if not ok:
            print("FALLA", label, "-", info)
    print(f"{len(CHECKS) - bad}/{len(CHECKS)} chequeos OK")
