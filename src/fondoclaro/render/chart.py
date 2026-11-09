from decimal import Decimal


def points(manifest):
    scale = manifest["chart_scale"]
    lo, hi = Decimal(scale["lo"]), Decimal(scale["hi"])
    data = manifest["chart_series"]
    return [(scale["left"] + (scale["right"] - scale["left"]) * i / (len(data) - 1),
             scale["bottom"] - float((Decimal(row["value"]) - lo) / (hi - lo)) * (scale["bottom"] - scale["top"]))
            for i, row in enumerate(data)]


def path(points):
    return "M" + " L".join(f"{x:.6f},{y:.6f}" for x, y in points)


def chart_svg(manifest):
    p = points(manifest)
    monthly = Decimal(manifest["r_1m"].replace("%", "").replace(",", "."))
    color = "#b52323" if monthly < 0 else "#17763b" if monthly > 0 else "#55635c"
    # Color de tramo usa el valor exacto, incluso si se redondea a cero.
    a, b = Decimal(manifest["chart_series"][-2]["value"]), Decimal(manifest["chart_series"][-1]["value"])
    color = "#b52323" if b < a else "#17763b" if b > a else "#55635c"
    bottom = manifest["chart_scale"]["bottom"]
    return (f'<path id="chart-area" d="{path(p)} L{p[-1][0]:.6f},{bottom} L{p[0][0]:.6f},{bottom} Z" fill="url(#area)"/>'
            f'<path id="chart-line" d="{path(p)}" stroke="#1f63b6" stroke-width="4" fill="none" stroke-linejoin="round"/>'
            f'<path d="M{p[0][0]},590 V{p[0][1]} M{p[-1][0]},590 V{p[-1][1]}" stroke="#55635c" stroke-dasharray="5 5" fill="none"/>'
            f'<circle cx="{p[-1][0]:.6f}" cy="{p[-1][1]:.6f}" r="2" fill="white" stroke="{color}" stroke-width="2"/>'
            f'<path id="chart-last" d="{path(p[-2:])}" stroke="{color}" stroke-width="6" stroke-linecap="round" fill="none"/>')
