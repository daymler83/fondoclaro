"""Supervision: valida el metodo SP en un horizonte LARGO (24 anios), que es el unico
contraste posible para dar confianza a la cifra de 10 anios de la imagen.

Compara contra la columna "Promedio Anual Periodo 27 Sep 2002 - Oct 2026" que publica la
SP para el SISTEMA, usando la anualizacion de la propia SP: (1+r)^(365/nd) - 1, con nd =
dias entre el 27-sep-2002 y el 31-oct-2026.

Independiente de src/fondoclaro.
"""
from decimal import Decimal, getcontext
from datetime import date
import html as htmlmod
import json, pathlib, re, calendar

getcontext().prec = 40
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FUNDS = list('ABCDE')
MESES = {m: i for i, m in enumerate(
    ['enero','febrero','marzo','abril','mayo','junio','julio','agosto',
     'septiembre','octubre','noviembre','diciembre'], 1)}

M2002 = json.load(open(ROOT / 'raw_data/history_2002_manifest.json'))
ENT = M2002['entries'] if isinstance(M2002, dict) else M2002


def dec_es(s):
    s = (s or '').strip()
    if not s or s in ('-', '&nbsp;'):
        return None
    try:
        return Decimal(s.replace('.', '').replace(',', '.'))
    except Exception:
        return None


def quota_days(fund):
    """-> {'YYYY-MM-DD': {afp: (vc, patrimonio)}} solo bloques confirmados."""
    e = [x for x in ENT if x['source'] == 'sp_quota_history' and x.get('fund') == fund][0]
    out, cols, confirmed = {}, None, False
    for ln in open(ROOT / e['path'], encoding='latin-1').read().splitlines():
        s = ln.strip()
        if s == 'Valores Confirmados':
            confirmed, cols = True, None; continue
        if s.startswith('Valores Provisorios'):
            confirmed, cols = False, None; continue
        if s.startswith('Fecha;'):
            cols = {n.strip(): i for i, n in enumerate(ln.split(';')) if i and n.strip()}
            continue
        if not re.match(r'^\d{4}-\d{2}-\d{2};', ln) or not confirmed or cols is None:
            continue
        f = ln.split(';')
        rec = {}
        for afp, i in cols.items():
            vc = dec_es(f[i]) if i < len(f) else None
            pat = dec_es(f[i+1]) if i+1 < len(f) else None
            if vc and vc > 0 and pat and pat > 0:
                rec[afp] = (vc, pat)
        if rec:
            out[f[0]] = rec
    return out


def uf_days():
    """-> {'YYYY-MM-DD': UF}. Soporta los dos formatos del SII:
    tablas por mes (anios recientes) y matriz dia x mes (anios antiguos)."""
    uf = {}
    for e in [x for x in ENT if x['source'] == 'sii_uf']:
        year = e['year']
        raw = open(ROOT / e['path'], encoding='latin-1', errors='replace').read()
        if "id='mes_" in raw:
            parts = re.split(r"id='mes_([a-z]+)'", raw)
            for k in range(1, len(parts)-1, 2):
                mnum = MESES.get(parts[k])
                if not mnum:
                    continue
                for d, v in re.findall(
                        r"<th[^>]*>\s*<strong>\s*(\d{1,2})\s*</strong>\s*</th>\s*"
                        r"<td[^>]*>\s*([\d\.]+,\d+)\s*</td>", parts[k+1]):
                    if int(d) <= calendar.monthrange(year, mnum)[1]:
                        uf[f'{year}-{mnum:02d}-{int(d):02d}'] = dec_es(v)
        else:
            # matriz: <tr><td>DIA</td><td>ene</td>...<td>dic</td></tr>
            for row in re.findall(r"<tr>(.*?)</tr>", raw, flags=re.S):
                cells = re.findall(r"<td[^>]*>\s*([^<]*?)\s*</td>", row)
                if len(cells) != 13 or not cells[0].strip().isdigit():
                    continue
                day = int(cells[0])
                for mnum, cell in enumerate(cells[1:], 1):
                    v = dec_es(cell)
                    if v and day <= calendar.monthrange(year, mnum)[1]:
                        uf[f'{year}-{mnum:02d}-{day:02d}'] = v
    return uf


def published_long():
    """-> {fund: Decimal} promedio anual del SISTEMA desde 27-sep-2002, en oct-2026."""
    e = [x for x in ENT if x['source'] == 'sp_published_returns'
         and x.get('period') == '2026-10']
    if not e:
        e = [x for x in json.load(open(ROOT/'raw_data/history_manifest.json'))['entries']
             if x['source'] == 'sp_published_returns' and x.get('period') == '2026-10']
    raw = open(ROOT / e[0]['path'], encoding='latin-1', errors='replace').read()
    txt = re.sub(r'[|\s\xa0]+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', '|', raw)))
    out = {}
    for f in FUNDS:
        mm = re.search(r'RENTABILIDAD REAL DEL FONDO TIPO ' + f + r' DEFLACTADA(.*?)'
                       r'(?=RENTABILIDAD REAL DEL FONDO TIPO |$)', txt, re.S)
        sm = re.search(r'SISTEMA((?:\s*-?[\d\.]+,\d+%)+)', mm.group(1))
        vals = [dec_es(n) for n in re.findall(r'(-?[\d\.]+,\d+)%', sm.group(1))]
        out[f] = vals[3] if len(vals) >= 4 else None   # 4a col: promedio anual desde 2002
    return out


uf = uf_days()
pub = published_long()
START, END = '2002-09-27', '2026-10-31'
nd = (date(2026, 10, 31) - date(2002, 9, 27)).days

print(f"Horizonte: {START} -> {END}   nd = {nd} dias ({nd/365:.1f} anios)")
print(f"Anualizacion de la SP: (1+r)^(365/nd) - 1\n")
print(f"{'F':2} {'acum. 24 anios':>16} {'anualizada mia':>16} {'SP publica':>11} {'dif':>10}")
print('-' * 62)
worst = Decimal(0)
for f in FUNDS:
    q = quota_days(f)
    if START not in q or END not in q:
        print(f"{f:2}  sin dato en alguna punta ({START in q}, {END in q})"); continue
    qi, qj = q[START], q[END]
    # ponderacion por patrimonio del mes anterior al corte (sep-2026), como el metodo adoptado
    prev = max(d for d in q if d.startswith('2026-09'))
    qw = q[prev]
    common = [a for a in qj if a in qi and a in qw]
    tot = sum(qw[a][1] for a in common)
    r = sum((qw[a][1]/tot) * ((qj[a][0]/qi[a][0]) * (uf[START]/uf[END]) - 1)
            for a in common)
    annual = (1 + r) ** (Decimal(365) / Decimal(nd)) - 1
    got, p = annual * 100, pub[f]
    d = abs(got - p) if p is not None else None
    worst = max(worst, d or Decimal(0))
    print(f"{f:2} {r*100:>15.4f}% {got:>15.4f}% {str(p)+'%':>11} {d:>9.4f} pp"
          f"  {'OK' if d is not None and d <= Decimal('0.01') else 'FUERA'}")
    print(f"   AFP usadas: {len(common)} | UF {START}={uf[START]} UF {END}={uf[END]}")

print(f"\nDiferencia maxima: {worst:.6f} pp  (tolerancia §6.1: 0,01 pp)")
print("Si esto calza, el metodo adoptado reproduce a la SP tambien en horizonte largo,")
print("y la cifra de 10 anios de la imagen descansa en un metodo validado a 24 anios.")
