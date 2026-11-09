"""Supervision: recalculo INDEPENDIENTE de la rentabilidad real del SISTEMA.

No importa nada de src/fondoclaro. Lee los archivos oficiales de raw_data/
(CSV de valor cuota y patrimonio por AFP de la SP; tablas anuales de UF del SII)
y compara contra las rentabilidades del SISTEMA publicadas por la SP.

Hipotesis contrastadas para la cifra "SISTEMA":
  M1  indice agregado encadenado (equivale a patrimonio total / cuotas totales,
      rebalanceado cada mes): factor_t = sum_a w_a,t-1 * (VC_a,t / VC_a,t-1)
      con w = patrimonio del mes anterior. r_n = I_j/I_{j-n} - 1, I = N/UF.
      Es el metodo implicito en §5.1 de la especificacion.
  M2w peso patrimonio del mes i (mes anterior al inicio del periodo)
  M2j peso patrimonio del mes j (mes de corte)
      promedio ponderado de la rentabilidad REAL del horizonte de cada AFP:
      r_a(i,j) = (VC_a,j/VC_a,i)*(UF_i/UF_j) - 1 ;  r_sys = sum_a w_a * r_a(i,j)

Uso: python3 -I docs/supervision/scripts/independent_recalc.py
"""
from decimal import Decimal, getcontext
import html as htmlmod
import json, pathlib, re, sys, calendar

getcontext().prec = 40
ROOT = pathlib.Path(__file__).resolve().parents[3]
MAN = json.load(open(ROOT / 'raw_data/history_manifest.json'))
FUNDS = list('ABCDE')
TOL = Decimal('0.01')  # puntos porcentuales, §6.1

MESES = {m: i for i, m in enumerate(
    ['enero','febrero','marzo','abril','mayo','junio','julio','agosto',
     'septiembre','octubre','noviembre','diciembre'], 1)}


def dec_es(s):
    """'26.538,94' -> Decimal; '' -> None"""
    s = (s or '').strip()
    if not s or s in ('-', '&nbsp;'):
        return None
    s = s.replace('.', '').replace(',', '.')
    try:
        return Decimal(s)
    except Exception:
        return None


def entry(source, **kw):
    out = [e for e in MAN['entries'] if e['source'] == source
           and all(e.get(k) == v for k, v in kw.items())]
    return out


# ---------------------------------------------------------------- valor cuota
def parse_quota(fund):
    """-> {'YYYY-MM': {afp: (VC_ultimo_dia_mes, PAT_ultimo_dia_mes)}} solo confirmados."""
    e = entry('sp_quota_history', fund=fund)
    assert len(e) == 1, (fund, len(e))
    lines = open(ROOT / e[0]['path'], encoding='latin-1').read().splitlines()
    cols, confirmed = None, False
    by_day = {}          # 'YYYY-MM-DD' -> {afp: (vc, pat)}
    for ln in lines:
        s = ln.strip()
        if s == 'Valores Confirmados':
            confirmed = True; cols = None; continue
        if s.startswith('Valores Provisorios'):
            confirmed = False; cols = None; continue
        if s.startswith('Fecha;'):
            names = ln.split(';')
            cols = {}
            for i, nm in enumerate(names):
                if i == 0 or not nm.strip():
                    continue
                cols[nm.strip()] = i      # i = col del valor cuota, i+1 = patrimonio
            continue
        if not re.match(r'^\d{4}-\d{2}-\d{2};', ln):
            continue
        if not confirmed or cols is None:
            continue
        f = ln.split(';')
        day = f[0]
        rec = {}
        for afp, i in cols.items():
            vc = dec_es(f[i]) if i < len(f) else None
            pat = dec_es(f[i + 1]) if i + 1 < len(f) else None
            if vc is not None and vc > 0 and pat is not None and pat > 0:
                rec[afp] = (vc, pat)
        if rec:
            by_day[day] = rec
    month = {}
    for day in sorted(by_day):
        month[day[:7]] = by_day[day]      # el ultimo dia del mes gana
    return month


# ------------------------------------------------------------------------ UF
def parse_uf():
    """-> {'YYYY-MM': UF del ultimo dia calendario del mes} desde tablas SII.

    Estructura: <div class='meses' id='mes_<nombre>'> con pares
    <th><strong>DIA</strong></th><td>VALOR</td>.
    """
    uf = {}
    for e in entry('sii_uf'):
        year = e['year']
        raw = open(ROOT / e['path'], encoding='latin-1', errors='replace').read()
        parts = re.split(r"id='mes_([a-z]+)'", raw)
        # parts = [antes, nombre1, cuerpo1, nombre2, cuerpo2, ...]
        for k in range(1, len(parts) - 1, 2):
            mname, body = parts[k], parts[k + 1]
            mnum = MESES.get(mname)
            if not mnum:
                continue
            pairs = re.findall(
                r"<th[^>]*>\s*<strong>\s*(\d{1,2})\s*</strong>\s*</th>\s*"
                r"<td[^>]*>\s*([\d\.]+,\d+)\s*</td>", body)
            d = {int(a): dec_es(b) for a, b in pairs}
            lastday = calendar.monthrange(year, mnum)[1]
            # el ultimo dia publicado del mes (SII publica todos los dias calendario)
            avail = [x for x in sorted(d) if x <= lastday]
            if avail and avail[-1] == lastday:
                uf[f'{year}-{mnum:02d}'] = d[lastday]
    return uf


# ------------------------------------------------- rentabilidades publicadas
def parse_published():
    """-> {('YYYY-MM', fund): {'r_1m': Decimal%, 'r_12m': Decimal% or None}} SISTEMA."""
    out = {}
    for e in entry('sp_published_returns'):
        period = e['period']
        raw = open(ROOT / e['path'], encoding='latin-1', errors='replace').read()
        txt = htmlmod.unescape(re.sub(r'<[^>]+>', '|', raw))
        txt = re.sub(r'[|\s\xa0]+', ' ', txt)
        for fund in FUNDS:
            mm = re.search(
                r'RENTABILIDAD REAL DEL FONDO TIPO ' + fund + r' DEFLACTADA(.*?)(?=RENTABILIDAD REAL DEL FONDO TIPO |$)',
                txt, flags=re.S)
            if not mm:
                continue
            seg = mm.group(1)
            sm = re.search(r'SISTEMA((?:\s*-?[\d\.]+,\d+%)+)', seg)
            if not sm:
                continue
            nums = re.findall(r'(-?[\d\.]+,\d+)%', sm.group(1))
            vals = [dec_es(n) for n in nums]
            rec = {'r_1m': vals[0] if vals else None}
            # columnas: Del Periodo | Acumulado ano | Ultimos 12 meses | promedios...
            rec['r_12m'] = vals[2] if len(vals) >= 3 else None
            rec['all'] = [str(v) for v in vals]
            out[(period, fund)] = rec
    return out


def addmonths(p, n):
    y, m = int(p[:4]), int(p[5:7])
    t = (y * 12 + m - 1) + n
    return f'{t // 12:04d}-{t % 12 + 1:02d}'


# --------------------------------------------------------------------- calculo
def main():
    uf = parse_uf()
    pub = parse_published()
    quota = {f: parse_quota(f) for f in FUNDS}

    print(f"UF meses leidos: {len(uf)}  rango {min(uf)}..{max(uf)}")
    for f in FUNDS:
        ms = sorted(quota[f])
        print(f"  fondo {f}: {len(ms)} cierres mensuales confirmados {ms[0]}..{ms[-1]}  "
              f"AFP en ultimo mes: {len(quota[f][ms[-1]])}")
    print(f"publicaciones SP SISTEMA: {len(pub)} celdas (periodo,fondo)\n")

    # indice agregado encadenado M1
    idx = {}   # fund -> {'YYYY-MM': I_t}
    for f in FUNDS:
        ms = sorted(quota[f])
        nominal = Decimal(1)
        idx[f] = {}
        for k, p in enumerate(ms):
            if k > 0:
                prev, cur = quota[f][ms[k - 1]], quota[f][p]
                common = [a for a in cur if a in prev]
                wsum = sum(prev[a][1] for a in common)
                factor = sum(prev[a][1] / wsum * (cur[a][0] / prev[a][0]) for a in common)
                nominal *= factor
            if p in uf:
                idx[f][p] = nominal / uf[p]

    def r_m1(f, i, j):
        if i in idx[f] and j in idx[f]:
            return (idx[f][j] / idx[f][i] - 1) * 100
        return None

    def r_m2(f, i, j, weight_at):
        qi, qj = quota[f].get(i), quota[f].get(j)
        if not qi or not qj or i not in uf or j not in uf:
            return None
        wsrc = quota[f].get(weight_at)
        if not wsrc:
            return None
        common = [a for a in qj if a in qi and a in wsrc]
        wsum = sum(wsrc[a][1] for a in common)
        tot = Decimal(0)
        for a in common:
            r = (qj[a][0] / qi[a][0]) * (uf[i] / uf[j]) - 1
            tot += (wsrc[a][1] / wsum) * r
        return tot * 100

    methods = {
        'M1_indice_encadenado(§5.1)': lambda f, i, j, n: r_m1(f, i, j),
        'M2_horizonte_peso_mes_i':    lambda f, i, j, n: r_m2(f, i, j, i),
        'M2_horizonte_peso_mes_j':    lambda f, i, j, n: r_m2(f, i, j, j),
    }

    periods = sorted({p for (p, _) in pub})
    print(f"Periodos comparados: {len(periods)} ({periods[0]}..{periods[-1]})\n")

    results = {}
    for mname, fn in methods.items():
        stats = {'r_1m': [], 'r_12m': []}
        fails = []
        for p in periods:
            for f in FUNDS:
                rec = pub.get((p, f))
                if not rec:
                    continue
                for horizon, n in (('r_1m', 1), ('r_12m', 12)):
                    official = rec.get(horizon)
                    if official is None:
                        continue
                    calc = fn(f, addmonths(p, -n), p, n)
                    if calc is None:
                        continue
                    d = abs(calc - official)
                    stats[horizon].append(d)
                    if d > TOL:
                        fails.append((f, p, horizon, calc, official, d))
        results[mname] = (stats, fails)
        print(f"--- {mname}")
        for h in ('r_1m', 'r_12m'):
            ds = stats[h]
            if ds:
                nivel = 'A (mes)' if h == 'r_1m' else 'B (12 meses)'
                print(f"    nivel {nivel:14s} comparaciones={len(ds):3d} "
                      f"fallos={sum(1 for x in ds if x > TOL):2d} "
                      f"dif_max={max(ds):.6f} pp")
        print(f"    TOTAL comparaciones={len(stats['r_1m'])+len(stats['r_12m'])} fallos={len(fails)}")
        for fl in fails:
            print(f"      FALLA fondo {fl[0]} {fl[1]} {fl[2]}: calc={fl[3]:.6f} SP={fl[4]} dif={fl[5]:.6f} pp")
        print()

    # nivel C: promedios anuales publicados
    sample = pub.get((periods[-1], 'C'))
    print(f"nivel C (promedios anuales SP), columnas publicadas {periods[-1]} fondo C: {sample['all']}")
    print("    Los promedios anuales de SP arrancan en 27-sep-2002 (y jul-1981 para C y E).")
    print("    La historia descargada parte en 2014-01: el nivel C NO ES VERIFICABLE con estos insumos.")
    print()
    print("Contraste contra lo que reporta Codex en docs/GOLDEN_RESULT.json:")
    g = json.load(open(ROOT / 'docs/GOLDEN_RESULT.json'))
    print(f"    status={g.get('status')} compared={g.get('compared')} failed={g.get('failed')}")
    print(f"    max_difference_pp={g.get('max_difference_pp')}")
    wc = g.get('worst_case', {})
    print(f"    worst_case: fondo {wc.get('fund')} {wc.get('period')} {wc.get('metric')} "
          f"calc={wc.get('calculated')} SP={wc.get('published')} dif={wc.get('difference_pp')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
