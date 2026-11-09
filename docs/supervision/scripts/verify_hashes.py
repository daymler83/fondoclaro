"""Supervision: verifica SHA-256 de raw_data y de las copias en tests/fixtures.
No importa nada de src/fondoclaro. Ejecutar: python3 -I docs/supervision/scripts/verify_hashes.py
"""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def check(manifest_path, entries, base):
    ok = bad = miss = 0
    problems = []
    for e in entries:
        p = ROOT / e['path'] if not str(e['path']).startswith(str(base)) else pathlib.Path(e['path'])
        if not p.exists():
            miss += 1; problems.append(('MISSING', e['path'])); continue
        got = sha(p)
        if got == e['sha256']:
            ok += 1
        else:
            bad += 1; problems.append(('MISMATCH', e['path'], e['sha256'], got))
    print(f"{manifest_path}: ok={ok} mismatch={bad} missing={miss}")
    for pr in problems:
        print("   ", pr)
    return bad + miss

total = 0
m = json.load(open(ROOT / 'raw_data/history_manifest.json'))
ent = list(m['entries'])
for lp in m.get('landing_pages', []):
    if isinstance(lp, dict) and 'sha256' in lp and 'path' in lp:
        ent.append(lp)
print(f"raw_data manifest: {len(m['entries'])} entries + {len(m.get('landing_pages',[]))} landing = {len(ent)} checked")
total += check('raw_data/history_manifest.json', ent, ROOT / 'raw_data')

fx = ROOT / 'tests/fixtures/official_history/manifest.json'
if fx.exists():
    mf = json.load(open(fx))
    fent = mf['entries'] if isinstance(mf, dict) and 'entries' in mf else mf
    if isinstance(fent, list):
        total += check(str(fx), fent, ROOT / 'tests/fixtures')

# Comparar que las copias congeladas tengan los mismos hashes que raw_data
raw_h = {e['sha256'] for e in m['entries']}
if fx.exists():
    mf = json.load(open(fx))
    fe = mf['entries'] if isinstance(mf, dict) and 'entries' in mf else mf
    fx_h = {e['sha256'] for e in fe if isinstance(e, dict) and 'sha256' in e}
    print(f"hashes raw_data={len(raw_h)} fixtures={len(fx_h)} fixtures_no_en_raw={len(fx_h - raw_h)} raw_no_en_fixtures={len(raw_h - fx_h)}")

print("RESULTADO:", "TODOS LOS HASHES COINCIDEN" if total == 0 else f"{total} PROBLEMAS")
sys.exit(0)
