"""Supervision: cuantas hipotesis de ponderacion reproducen el SISTEMA de SP a 12 meses.
Independiente de src/fondoclaro. Reutiliza los parsers de independent_recalc.py por exec,
sin importar el paquete del proyecto.
"""
from decimal import Decimal, getcontext
import pathlib, sys

getcontext().prec = 40
HERE = pathlib.Path(__file__).resolve().parent
src = (HERE / 'independent_recalc.py').read_text()
src = src.split("# --------------------------------------------------------------------- calculo")[0]
ns = {'__name__': 'recalc_parts', '__file__': str(HERE / 'independent_recalc.py')}
exec(compile(src, 'independent_recalc.py', 'exec'), ns)

parse_uf, parse_published, parse_quota = ns['parse_uf'], ns['parse_published'], ns['parse_quota']
addmonths, FUNDS, TOL = ns['addmonths'], ns['FUNDS'], ns['TOL']

uf = parse_uf()
pub = parse_published()
quota = {f: parse_quota(f) for f in FUNDS}
periods = sorted({p for (p, _) in pub})


def weighted(f, i, j, wfn):
    qi, qj = quota[f].get(i), quota[f].get(j)
    if not qi or not qj or i not in uf or j not in uf:
        return None
    common = [a for a in qj if a in qi]
    ws = {}
    for a in common:
        w = wfn(f, a, i, j)
        if w is None:
            return None
        ws[a] = w
    tot = sum(ws.values())
    if not tot:
        return None
    out = Decimal(0)
    for a in common:
        r = (qj[a][0] / qi[a][0]) * (uf[i] / uf[j]) - 1
        out += (ws[a] / tot) * r
    return out * 100


def pat(f, a, p):
    rec = quota[f].get(p)
    return rec[a][1] if rec and a in rec else None


def shares(f, a, p):
    """numero de cuotas = patrimonio / valor cuota"""
    rec = quota[f].get(p)
    if not rec or a not in rec:
        return None
    return rec[a][1] / rec[a][0]


VARIANTS = {
    'peso patrimonio mes j (corte)':      lambda f, a, i, j: pat(f, a, j),
    'peso patrimonio mes i (inicio-1)':   lambda f, a, i, j: pat(f, a, i),
    'peso patrimonio mes j-1':            lambda f, a, i, j: pat(f, a, addmonths(j, -1)),
    'peso cuotas mes j':                  lambda f, a, i, j: shares(f, a, j),
    'peso cuotas mes i':                  lambda f, a, i, j: shares(f, a, i),
    'peso patrimonio promedio(i,j)':      lambda f, a, i, j: (
        None if pat(f, a, i) is None or pat(f, a, j) is None
        else (pat(f, a, i) + pat(f, a, j)) / 2),
}

print(f"Celdas: {len(periods)} meses x 5 fondos, horizonte 12 meses = {len(periods)*5}")
print(f"Tolerancia §6.1: {TOL} pp\n")
for name, wfn in VARIANTS.items():
    diffs, fails = [], 0
    for p in periods:
        for f in FUNDS:
            off = (pub.get((p, f)) or {}).get('r_12m')
            if off is None:
                continue
            c = weighted(f, addmonths(p, -12), p, wfn)
            if c is None:
                continue
            d = abs(c - off)
            diffs.append(d)
            if d > TOL:
                fails += 1
    status = 'PASA' if fails == 0 else f'FALLA {fails}'
    print(f"  {name:36s} n={len(diffs):3d} dif_max={max(diffs):.6f} pp  -> {status}")

print()
print("Tambien sobre el horizonte de 1 mes, para contrastar:")
for name, wfn in VARIANTS.items():
    diffs, fails = [], 0
    for p in periods:
        for f in FUNDS:
            off = (pub.get((p, f)) or {}).get('r_1m')
            if off is None:
                continue
            c = weighted(f, addmonths(p, -1), p, wfn)
            if c is None:
                continue
            d = abs(c - off); diffs.append(d); fails += (d > TOL)
    print(f"  {name:36s} n={len(diffs):3d} dif_max={max(diffs):.6f} pp  "
          f"-> {'PASA' if fails==0 else f'FALLA {fails}'}")

# --- discriminacion por el residuo maximo que explica el redondeo de SP ---
print()
print("SP redondea a 2 decimales => el residuo maximo explicable es 0,005 pp.")
print("Una hipotesis que exceda 0,005 pp NO puede ser el metodo exacto de SP.")
print()
ROUND_BOUND = Decimal('0.005')
for name, wfn in VARIANTS.items():
    rows = []
    for p in periods:
        for f in FUNDS:
            for h, n in (('r_1m', 1), ('r_12m', 12)):
                off = (pub.get((p, f)) or {}).get(h)
                if off is None:
                    continue
                c = weighted(f, addmonths(p, -n), p, wfn)
                if c is not None:
                    rows.append(abs(c - off))
    over = sum(1 for d in rows if d > ROUND_BOUND)
    print(f"  {name:36s} n={len(rows):3d} dif_max={max(rows):.6f} pp  "
          f"celdas>0,005pp={over:3d}  -> "
          f"{'COMPATIBLE con el metodo de SP' if over == 0 else 'INCOMPATIBLE'}")

print()
print("Celda peor de Codex (B / 2024-12 / 12 meses), publicado SP = 7,44 %:")
i, j = addmonths('2024-12', -12), '2024-12'
for name, wfn in VARIANTS.items():
    c = weighted('B', i, j, wfn)
    print(f"  {name:36s} calculado={c:.9f} %  dif={abs(c - Decimal('7.44')):.9f} pp")
print("  Codex reporta official_period_weighting = 7,439592057653221668639013085336955299967 %")
