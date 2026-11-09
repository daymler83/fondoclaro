"""Supervision: recalcula, de forma independiente, las cifras VISIBLES de los informes
de octubre 2026 y las compara con lo que muestran los manifiestos de Codex.

No importa nada de src/fondoclaro. Metodo SP adoptado: promedio de las rentabilidades
reales de cada AFP en el horizonte, ponderado por patrimonio del mes j-1.
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
import glob, json, pathlib, sys

getcontext().prec = 40
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
src = (HERE / 'independent_recalc.py').read_text().split(
    "# --------------------------------------------------------------------- calculo")[0]
ns = {'__name__': 'parts', '__file__': str(HERE / 'independent_recalc.py')}
exec(compile(src, 'independent_recalc.py', 'exec'), ns)
parse_uf, parse_quota, parse_published = ns['parse_uf'], ns['parse_quota'], ns['parse_published']
addmonths, FUNDS = ns['addmonths'], ns['FUNDS']

uf = parse_uf()
quota = {f: parse_quota(f) for f in FUNDS}
pub = parse_published()
J = '2026-10'


def r_sp(f, i, j):
    """Promedio ponderado por patrimonio del mes j-1 de la rentabilidad real por AFP."""
    qi, qj, qw = quota[f].get(i), quota[f].get(j), quota[f].get(addmonths(j, -1))
    if not (qi and qj and qw) or i not in uf or j not in uf:
        return None
    common = [a for a in qj if a in qi and a in qw]
    tot = sum(qw[a][1] for a in common)
    return sum((qw[a][1] / tot) * ((qj[a][0] / qi[a][0]) * (uf[i] / uf[j]) - 1)
               for a in common) * 100


def fmt(p):
    q = p.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    if q == 0:
        return '0,0%'
    return f"{'+' if q > 0 else '-'}{abs(q)}%".replace('.', ',')


# cifras de los manifiestos de Codex
got = {}
for d in glob.glob(str(ROOT / 'reports/*/render_manifest.json')):
    m = json.load(open(d))
    lab = (m.get('fund_label') or '').replace('Fondo ', '').strip()
    if lab in FUNDS:
        got[lab] = (m.get('r_1m'), m.get('r_120m'), m.get('cutoff_date'),
                    m.get('chart_end_label'), pathlib.Path(d).parent.name)

print(f"Mes de corte: {J}    base: $10.000.000\n")
print(f"{'F':2} {'r_1m mio':>10} {'r_1m Codex':>11} {'SP publ.':>9} | "
      f"{'r_120m mio':>11} {'r_120m Codex':>13} | {'V_j mio':>12} {'V_j Codex':>12}")
print('-' * 100)
bad = 0
for f in FUNDS:
    m1, m120 = r_sp(f, addmonths(J, -1), J), r_sp(f, addmonths(J, -120), J)
    c1, c120, cut, endlab, rid = got.get(f, (None,) * 5)
    sp1 = (pub.get((J, f)) or {}).get('r_1m')
    vj_mio = (Decimal(10_000_000) * (1 + m120.quantize(Decimal('0.1'),
              rounding=ROUND_HALF_UP) / 100)).quantize(Decimal('1'))
    ok1, ok120 = fmt(m1) == (c1 or '').replace('−', '-'), fmt(m120) == (c120 or '').replace('−', '-')
    bad += (not ok1) + (not ok120)
    print(f"{f:2} {fmt(m1):>10} {c1 or '-':>11} {str(sp1)+'%':>9} | "
          f"{fmt(m120):>11} {c120 or '-':>13} | {vj_mio:>12,} {endlab or '-':>12}"
          f"  {'' if ok1 and ok120 else '  <-- DISCREPA'}")

print()
print("Diferencia exacta contra lo publicado por SP en el mes de corte:")
for f in FUNDS:
    m1 = r_sp(f, addmonths(J, -1), J)
    sp1 = (pub.get((J, f)) or {}).get('r_1m')
    if sp1 is not None:
        d = abs(m1 - sp1)
        print(f"  Fondo {f}: calculado {m1:.6f} %  SP {sp1} %  dif {d:.6f} pp  "
              f"{'OK' if d <= Decimal('0.01') else 'FUERA DE TOLERANCIA'}")

print()
print("Coherencia 6.3-4 (ultimo punto del grafico = 10.000.000 x (1 + r_120m)):")
for f in FUNDS:
    c1, c120, cut, endlab, rid = got.get(f, (None,) * 5)
    if not c120:
        continue
    pct = Decimal(c120.replace('−', '-').replace('%', '').replace(',', '.'))
    esperado = (Decimal(10_000_000) * (1 + pct / 100)).quantize(Decimal('1'))
    visto = Decimal((endlab or '0').replace('$', '').replace('.', '') or 0)
    print(f"  Fondo {f}: {c120:>7} -> esperado ${esperado:,}  globo {endlab}  "
          f"{'OK' if esperado == visto else 'DISCREPA'}".replace(',', '.'))

print()
print(f"RESULTADO: {'TODAS LAS CIFRAS VISIBLES COINCIDEN' if bad == 0 else f'{bad} DISCREPANCIAS'}")
