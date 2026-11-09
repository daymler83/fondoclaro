"""Maqueta de la imagen FondoClaro v2 (cifras ficticias).

Estilo de tarjetas basado en el mockup original, con el contenido simplificado
de la especificación: dos cifras (mes y 10 años), un gráfico, una explicación.
Genera SVG desde datos y lo rasteriza con rsvg-convert. Al final imprime los
chequeos de la especificación (textos caben, nada tapa la línea, invariantes).

Uso: python render_maqueta.py [salida_sin_extension]
"""
import math
import random
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape

from PIL import ImageFont

W, H = 1080, 1350
M = 36  # margen exterior
FONT_DIR = "/usr/share/fonts/opentype/inter/"
WEIGHTS = {400: "Inter-Regular.otf", 500: "Inter-Medium.otf", 600: "Inter-SemiBold.otf",
           700: "Inter-Bold.otf", 800: "Inter-ExtraBold.otf"}

GREEN = "#17763b"
GREEN_DARK = "#0f5a2c"
GREEN_BG = "#e8f4ec"
BLUE = "#1f63b6"
BLUE_DARK = "#163d73"
RED = "#c62828"
RED_BG = "#fdeceb"
INK = "#15231b"
MUTED = "#55635c"
GRID = "#e7ece9"
PAGE = "#f2f7f3"
NOTE_BG = "#eef2f6"

# ---------------------------------------------------------------- datos ficticios
BASE = Decimal(10_000_000)
R_1M = Decimal("-0.020")
R_120M = Decimal("0.480")
MES, MES_ABR, ANIO = "octubre", "oct", 2026
START_YEAR, START_MONTH = 2016, 10


def build_series(seed=7):
    rnd = random.Random(seed)
    logs = []
    for k in range(119):
        year = START_YEAR + (k + START_MONTH) // 12
        month = (k + START_MONTH) % 12 + 1
        x = rnd.gauss(0, 0.012)
        if (year, month) == (2020, 3):
            x = -0.075
        if (year, month) in {(2020, 4), (2020, 5)}:
            x = 0.025
        if year == 2022 and month <= 9:
            x -= 0.006
        logs.append(x)
    target = math.log(float((1 + R_120M) / (1 + R_1M)))
    shift = (target - sum(logs)) / len(logs)
    logs = [x + shift for x in logs]
    vals = [float(BASE)]
    for x in logs:
        vals.append(vals[-1] * math.exp(x))
    vals.append(float(BASE * (1 + R_120M)))  # último mes: -2,0% exacto
    return vals


def pct(d: Decimal) -> str:
    q = (d * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
    if q == 0:
        return "0,0%"
    sign = "+" if q > 0 else "−"
    return f"{sign}{abs(q):.1f}".replace(".", ",") + "%"


def money(d) -> str:
    q = int(Decimal(str(d)).quantize(Decimal("10000"), ROUND_HALF_UP))
    return "$" + f"{q:,}".replace(",", ".")


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# ---------------------------------------------------------------- texto y chequeos
_fonts = {}
CHECKS = []
LABEL_BOXES = []  # cajas de etiquetas dentro del gráfico, para verificar que no tapan la línea


def tw(text, size, weight):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_DIR + WEIGHTS[weight], size)
    return _fonts[key].getlength(text)


def text(x, y, s, size, weight=400, fill=INK, anchor="start", max_w=None):
    if max_w is not None:
        w = tw(s, size, weight)
        CHECKS.append((f"cabe: '{s[:42]}'", w <= max_w, f"{w:.0f}px <= {max_w:.0f}px"))
    return (f'<text xml:space="preserve" x="{x:.1f}" y="{y:.1f}" font-family="Inter" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def rich(x, y, parts, size, max_w):
    total = sum(tw(t, size, wt) for t, wt, _ in parts)
    CHECKS.append((f"cabe: '{''.join(p[0] for p in parts)[:42]}'", total <= max_w,
                   f"{total:.0f}px <= {max_w:.0f}px"))
    spans = "".join(f'<tspan font-weight="{wt}" fill="{f}">{escape(t)}</tspan>' for t, wt, f in parts)
    return f'<text xml:space="preserve" x="{x}" y="{y}" font-family="Inter" font-size="{size}">{spans}</text>'


def wrap_rich(words, size, max_w):
    """words: [(palabra, weight, fill)] -> líneas de tramos."""
    lines, cur, cur_w = [], [], 0.0
    for w, wt, f in words:
        piece = (" " if cur else "") + w
        pw = tw(piece, size, wt)
        if cur and cur_w + pw > max_w:
            lines.append(cur)
            cur, cur_w = [(w, wt, f)], tw(w, size, wt)
        else:
            cur.append((piece, wt, f))
            cur_w += pw
    lines.append(cur)
    return lines


def card(x, y, w, h, fill, stroke=None, r=26):
    s = f' stroke="{stroke}" stroke-width="2"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"{s}/>'


def arrow(cx, cy, size, up, color):
    s = size
    if up:
        pts = [(cx, cy - s), (cx + s * 0.75, cy - s * 0.1), (cx + s * 0.28, cy - s * 0.1),
               (cx + s * 0.28, cy + s), (cx - s * 0.28, cy + s), (cx - s * 0.28, cy - s * 0.1),
               (cx - s * 0.75, cy - s * 0.1)]
    else:
        pts = [(cx, cy + s), (cx + s * 0.75, cy + s * 0.1), (cx + s * 0.28, cy + s * 0.1),
               (cx + s * 0.28, cy - s), (cx - s * 0.28, cy - s), (cx - s * 0.28, cy + s * 0.1),
               (cx - s * 0.75, cy + s * 0.1)]
    return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{color}"/>'


def pill_label(x_right, y_bottom, lines, fill, size=26, pad=14, tip_x=None):
    """Globo de etiqueta alineado a la derecha, con punta hacia abajo en tip_x."""
    widths = [tw(t, size, wt) for t, wt in lines]
    w = max(widths) + 2 * pad
    lh = size * 1.22
    h = lh * len(lines) + pad * 1.4
    x, y = x_right - w, y_bottom - h
    LABEL_BOXES.append((x, y, x + w, y_bottom + 12))
    out = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" fill="{fill}"/>']
    if tip_x is not None:
        tx = min(max(tip_x, x + 16), x + w - 16)
        out.append(f'<polygon points="{tx - 10:.1f},{y_bottom:.1f} {tx + 10:.1f},{y_bottom:.1f} '
                   f'{tx:.1f},{y_bottom + 12:.1f}" fill="{fill}"/>')
    for i, (t, wt) in enumerate(lines):
        out.append(text(x + w / 2, y + pad * 0.7 + lh * (i + 0.8), t, size, wt, "#ffffff", "middle"))
    return "\n".join(out)


def seg_hits_box(p, q, box):
    """¿El segmento p-q toca la caja? (muestreo fino, suficiente para la maqueta)."""
    x0, y0, x1, y1 = box
    for k in range(21):
        t = k / 20
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


# ---------------------------------------------------------------- composición
def build():
    vals = build_series()
    r1, r120 = pct(R_1M), pct(R_120M)
    end_money = money(vals[-1])
    month_neg = R_1M < 0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}">', f'<rect width="{W}" height="{H}" fill="{PAGE}"/>']

    # ---------- encabezado
    hx, hy, hw, hh = M, M, W - 2 * M, 112
    out.append(card(hx, hy, hw, hh, GREEN, r=30))
    for i, h in enumerate((22, 36, 50)):
        out.append(f'<rect x="{hx + 30 + i * 17}" y="{hy + 81 - h}" width="12" height="{h}" rx="3" fill="#ffffff"/>')
    out.append(text(hx + 104, hy + 56, "FondoClaro", 40, 800, "#ffffff"))
    out.append(text(hx + 104, hy + 90, "Tus ahorros, explicados en 30 segundos", 23, 500, "#d6f0de"))
    pill = "Fondo C"
    pw = tw(pill, 30, 700) + 50
    out.append(card(hx + hw - pw - 26, hy + 28, pw, 56, "#ffffff", r=28))
    out.append(text(hx + hw - 26 - pw / 2, hy + 67, pill, 30, 700, GREEN_DARK, "middle"))

    # ---------- dos cifras
    cy, ch, gap = hy + hh + 22, 196, 22
    cw = (W - 2 * M - gap) / 2
    # Este mes
    c1x = M
    col1 = RED if month_neg else GREEN
    out.append(card(c1x, cy, cw, ch, RED_BG if month_neg else GREEN_BG))
    out.append(text(c1x + 30, cy + 52, "Este mes", 30, 700, INK, max_w=cw - 60))
    out.append(arrow(c1x + 56, cy + 112, 26, not month_neg, col1))
    out.append(text(c1x + 98, cy + 134, r1, 64, 800, col1, max_w=cw - 128))
    out.append(text(c1x + 98 + tw(r1, 64, 800) + 4, cy + 108, "*", 40, 700, col1))
    out.append(text(c1x + 30, cy + 174, f"{MES} {ANIO}", 25, 500, MUTED, max_w=cw - 60))
    # 10 años
    c2x = M + cw + gap
    col2 = GREEN if R_120M >= 0 else RED
    out.append(card(c2x, cy, cw, ch, GREEN_BG if R_120M >= 0 else RED_BG))
    out.append(text(c2x + 30, cy + 52, "Últimos 10 años", 30, 700, INK, max_w=cw - 60))
    out.append(arrow(c2x + 56, cy + 112, 26, R_120M >= 0, col2))
    out.append(text(c2x + 98, cy + 134, r120, 64, 800, col2, max_w=cw - 128))
    out.append(text(c2x + 98 + tw(r120, 64, 800) + 4, cy + 108, "*", 40, 700, col2))
    out.append(text(c2x + 30, cy + 174, "acumulado", 25, 500, MUTED, max_w=cw - 60))

    # ---------- gráfico
    gx, gy, gw, gh = M, cy + ch + 20, W - 2 * M, 640
    out.append(card(gx, gy, gw, gh, "#ffffff", stroke="#e1e7e3"))
    out.append(text(gx + 30, gy + 60, "Así pudo evolucionar $10.000.000 en 10 años*", 31, 700, INK, max_w=gw - 60))

    left, right = gx + 150, gx + gw - 34
    top, bottom = gy + 104, gy + gh - 70
    d_top, d_bot = top + 118, bottom - 26  # banda donde vive la curva (deja espacio a los globos)
    lo, hi = min(vals), max(vals)

    def px(i):
        return left + (right - left) * i / (len(vals) - 1)

    def py(v):
        return d_bot - (d_bot - d_top) * (v - lo) / (hi - lo)

    def inv(y):
        return lo + (d_bot - y) * (hi - lo) / (d_bot - d_top)

    # grilla Y cada $1.000.000 dentro del área visible
    v_top, v_bot = inv(top), inv(bottom)
    step = 1_000_000
    tick = math.ceil(v_bot / step) * step
    while tick <= v_top:
        y = py(tick)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{GRID}" stroke-width="2"/>')
        out.append(text(left - 14, y + 8, thousands(int(tick)), 21, 500, MUTED, "end"))
        tick += step
    # años (enero de cada año)
    for k in range(len(vals)):
        year = START_YEAR + (k + START_MONTH - 1) // 12
        month = (k + START_MONTH - 1) % 12 + 1
        if month == 1:
            x = px(k)
            out.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="{GRID}" stroke-width="2"/>')
            out.append(text(x, bottom + 38, str(year), 22, 600, MUTED, "middle"))
    out.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#cfd8d3" stroke-width="2"/>')

    pts = [(px(i), py(v)) for i, v in enumerate(vals)]
    out.append('<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.22"/>'
               f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0.03"/></linearGradient></defs>')
    area = ("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            + f" L{pts[-1][0]:.1f},{bottom} L{pts[0][0]:.1f},{bottom} Z")
    out.append(f'<path d="{area}" fill="url(#g)"/>')
    out.append(f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pts[:-1])}" fill="none" '
               f'stroke="{BLUE}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>')
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    seg = RED if month_neg else (GREEN if R_1M > 0 else MUTED)
    out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{seg}" '
               f'stroke-width="7" stroke-linecap="round"/>')

    # globo final: sobre la parte más alta de la curva en su ancho
    end_lines = [(end_money, 800), (f"hoy ({r120})", 600)]
    end_w = max(tw(t, 26, wt) for t, wt in end_lines) + 28
    span_top = min(y for x, y in pts if x >= right - end_w - 10)
    out.append(pill_label(right, span_top - 24, end_lines, GREEN, tip_x=x1))
    out.append(f'<line x1="{x1:.1f}" y1="{span_top - 12:.1f}" x2="{x1:.1f}" y2="{y1 - 12:.1f}" '
               f'stroke="{GREEN}" stroke-width="2" stroke-dasharray="4 4"/>')
    out.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="10" fill="#fff" stroke="{seg}" stroke-width="5"/>')
    # globo inicial
    sx, sy = pts[0]
    start_lines = [("$10.000.000", 800)]
    start_w = tw("$10.000.000", 26, 800) + 28
    span_top_s = min(y for x, y in pts if x <= sx + start_w)
    out.append(pill_label(sx - 8 + start_w, span_top_s - 24, start_lines, BLUE_DARK, tip_x=sx))
    out.append(f'<line x1="{sx:.1f}" y1="{span_top_s - 12:.1f}" x2="{sx:.1f}" y2="{sy - 12:.1f}" '
               f'stroke="{BLUE_DARK}" stroke-width="2" stroke-dasharray="4 4"/>')
    out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="10" fill="#fff" stroke="{BLUE_DARK}" stroke-width="5"/>')

    # ---------- ¿Qué significa?
    ny, nh = gy + gh + 20, 150
    out.append(card(M, ny, W - 2 * M, nh, NOTE_BG))
    ix, iy = M + 32, ny + 44
    out.append(f'<rect x="{ix}" y="{iy}" width="72" height="72" rx="12" fill="none" stroke="{GREEN}" stroke-width="6"/>')
    out.append(f'<line x1="{ix}" y1="{iy + 22}" x2="{ix + 72}" y2="{iy + 22}" stroke="{GREEN}" stroke-width="6"/>')
    for dx in (18, 54):
        out.append(f'<line x1="{ix + dx}" y1="{iy - 10}" x2="{ix + dx}" y2="{iy + 8}" stroke="{GREEN}" stroke-width="6" stroke-linecap="round"/>')
    out.append(f'<line x1="{ix + 16}" y1="{iy + 42}" x2="{ix + 34}" y2="{iy + 42}" stroke="{GREEN}" stroke-width="6" stroke-linecap="round"/>')
    out.append(f'<line x1="{ix + 42}" y1="{iy + 42}" x2="{ix + 56}" y2="{iy + 42}" stroke="{GREEN}" stroke-width="6" stroke-linecap="round"/>')
    tx, tmax = M + 136, W - 2 * M - 136 - 28
    words = [("¿Qué", 800, GREEN_DARK), ("significa?", 800, GREEN_DARK)]
    msg = (f"{MES.capitalize()} fue un mes negativo. Aun así, en 10 años $10.000.000 "
           f"pasaron a ser {end_money}.")
    words += [(w, 500, INK) for w in msg.split()]
    lines = wrap_rich(words, 28, tmax)
    CHECKS.append(("¿Qué significa? cabe en 3 líneas", len(lines) <= 3, f"{len(lines)} líneas"))
    for i, ln in enumerate(lines):
        out.append(rich(tx, ny + 64 + i * 42, ln, 28, tmax))

    # ---------- pie
    fy = ny + nh + 32
    out.append(f'<circle cx="{M + 16}" cy="{fy - 8}" r="14" fill="none" stroke="{MUTED}" stroke-width="2.5"/>')
    out.append(text(M + 16, fy, "i", 20, 800, MUTED, "middle"))
    out.append(text(M + 42, fy, "* Descontada la inflación (variación de la UF). Montos en pesos de hoy.",
                    21, 600, MUTED, max_w=W - 2 * M - 42))
    out.append(text(M + 42, fy + 28, "Fuente: Superintendencia de Pensiones y Banco Central, al 31-oct-2026.",
                    21, 500, MUTED, max_w=W - 2 * M - 42))
    out.append(text(M + 42, fy + 56, "Promedio del sistema. Monto de ejemplo. No es una recomendación.",
                    21, 500, MUTED, max_w=W - 2 * M - 42))
    tag = "MAQUETA · CIFRAS FICTICIAS"
    tgw = tw(tag, 18, 700) + 24
    out.append(card(W - M - tgw, fy + 72, tgw, 30, "#fff1cc", r=15))
    out.append(text(W - M - tgw / 2, fy + 93, tag, 18, 700, "#8a5a00", "middle"))
    CHECKS.append(("sello de maqueta no tapa el pie", fy + 72 > fy + 62, "sello bajo la última línea"))
    CHECKS.append(("todo dentro del alto", fy + 104 <= H, f"termina en {fy + 104:.0f} <= {H}"))
    out.append("</svg>")

    # ---------- invariantes
    hits = [b for b in LABEL_BOXES if any(seg_hits_box(pts[i], pts[i + 1], b) for i in range(len(pts) - 1))]
    CHECKS.append(("ningún globo tapa la línea", not hits, f"{len(hits)} choques"))
    CHECKS.append(("último tramo según signo del mes", (y1 > y0) == month_neg, f"y0={y0:.1f} y1={y1:.1f}"))
    CHECKS.append(("globo final = último punto = base × (1 + r_120m)",
                   end_money == money(BASE * (1 + R_120M)), end_money))
    CHECKS.append(("la curva cabe en el gráfico", all(top <= y <= bottom for _, y in pts), ""))
    return "\n".join(out)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "maqueta_objetivo"
    svg = build()
    open(name + ".svg", "w", encoding="utf-8").write(svg)
    subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), name + ".svg", "-o", name + ".png"], check=True)
    bad = 0
    for label, ok, info in CHECKS:
        bad += not ok
        print(("OK   " if ok else "FALLA"), label, "-", info)
    print(f"\n{len(CHECKS) - bad}/{len(CHECKS)} chequeos OK")
