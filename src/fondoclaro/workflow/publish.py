"""Publicación gratuita a una página estática (GitHub Pages).

Canal de distribución en el sentido de §9.4: lee solo `approved_index.json`,
verifica los hashes y copia las PNG aprobadas. No calcula ni redacta cifras;
los pies de foto son los textos aprobados de §7.6.
"""
import shutil
from html import escape

from ..config import Blocked, FUNDS, RISK, period_end
from ..serialization import read_json, write_json
from .approved import approved_entries, stem

MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")

STYLE = """:root{--bg:#f2f7f3;--card:#fff;--ink:#17231c;--soft:#55635c;--line:#e7ece9;--brand:#17763b}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#101613;--card:#18211c;--ink:#eef3f0;--soft:#9fb0a7;--line:#263029;--brand:#4fbe7c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:620px;margin:0 auto;padding:0 16px 56px}
header{background:var(--brand);color:#fff;padding:22px 16px;margin-bottom:24px}
header .wrap{padding:0 0}
h1{margin:0;font-size:21px;letter-spacing:.2px}
header p{margin:6px 0 0;font-size:14px;opacity:.9}
figure{margin:0 0 28px;background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden}
figure img{display:block;width:100%;height:auto}
figcaption{padding:14px 16px;font-size:14px;color:var(--soft)}
h2{font-size:15px;margin:0 0 10px;color:var(--soft);font-weight:600}
footer{margin-top:32px;padding-top:18px;border-top:1px solid var(--line);font-size:13px;color:var(--soft)}
a{color:var(--brand)}
nav{font-size:14px;margin-bottom:20px}"""


def _page(period, selected, periods):
    end = period_end(period)
    label = f"{MONTHS[end.month]} {end.year}"
    order = {f: i for i, f in enumerate(("all", *FUNDS))}
    out = ['<!doctype html><html lang="es-CL"><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           f'<title>FondoClaro · {escape(label)}</title>',
           f'<meta name="description" content="Rentabilidad real de los cinco fondos de pensiones de Chile, {escape(label)}.">',
           f"<style>{STYLE}</style>",
           f'<header><div class="wrap"><h1>FondoClaro</h1><p>Los cinco fondos de pensiones · {escape(label)}</p></div></header>',
           '<div class="wrap">']
    for fund, entry, _ in sorted(selected, key=lambda s: order[s[0]]):
        title = "Los cinco fondos" if fund == "all" else f"Fondo {fund} · {RISK[fund]}"
        out.append(f'<h2>{escape(title)}</h2><figure>'
                   f'<img src="{stem(fund)}.png" width="1080" height="1350" alt="{escape(title)}, {escape(label)}" loading="lazy">'
                   f'<figcaption>{escape(entry["whatsapp_text"])}</figcaption></figure>')
    if len(periods) > 1:
        links = " · ".join(f'<a href="../{escape(p)}/">{escape(p)}</a>' for p in periods if p != period)
        out.append(f'<nav>Meses anteriores: {links}</nav>')
    out.append('<footer>Cifras reales, descontada la inflación. Fuente: '
               '<a href="https://www.spensiones.cl/apps/rentabilidad/getRentabilidad.php?tiprent=FP">Superintendencia de Pensiones</a>'
               ' y Banco Central. FondoClaro no es una AFP ni da recomendaciones de inversión.</footer>'
               '</div></html>')
    return "\n".join(out)


def publish_site(registry, period):
    """Escribe site/<period>/ con las imágenes aprobadas y su página, y site/index.html."""
    selected, missing = approved_entries(registry, period)
    if not selected:
        raise Blocked("NOTHING_APPROVED: no hay imágenes aprobadas para "+period)
    site = registry.root/"site"
    folder = site/period
    folder.mkdir(parents=True, exist_ok=True)
    for fund, _, source in selected:
        shutil.copyfile(source, folder/(stem(fund)+".png"))
    catalog = site/"periods.json"
    periods = sorted(set(read_json(catalog).get("periods", []) if catalog.exists() else []) | {period}, reverse=True)
    page = _page(period, selected, periods)
    (folder/"index.html").write_text(page)
    if period == periods[0]:
        (site/"index.html").write_text(page.replace('src="', f'src="{period}/').replace(f'href="../{period}/"', 'href="#"'))
    write_json(catalog, dict(periods=periods, latest=periods[0],
                             images={stem(f): f"{period}/{stem(f)}.png" for f, _, _ in selected}))
    (site/".nojekyll").write_text("")
    return folder, missing
