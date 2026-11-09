"""Descarga autorizada de fuentes públicas. No envía mensajes ni usa secretos."""
import argparse
from pathlib import Path

from fondoclaro.data.history import collect_history,freeze_history

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, default=Path.cwd())
parser.add_argument("--start-year", type=int, default=2014)
parser.add_argument("--end-year", type=int, default=2026)
parser.add_argument("--manifest", type=Path, help="Inventario separado para conservar la descarga anterior")
parser.add_argument("--freeze-to", type=Path, help="Manifiesto de copias oficiales para pruebas offline")
args = parser.parse_args()
result = collect_history(args.root, args.start_year, args.end_year, manifest_path=args.manifest)
if args.freeze_to:
    freeze_history(args.root,args.manifest or args.root/"raw_data/history_manifest.json",args.freeze_to.resolve())
print(f"Guardados {len(result['entries'])} archivos; corte confirmado {result['cutoff']}")
