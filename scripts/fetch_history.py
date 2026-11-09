"""Descarga autorizada de fuentes públicas. No envía mensajes ni usa secretos."""
import argparse
from pathlib import Path

from fondoclaro.data.history import collect_history

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, default=Path.cwd())
parser.add_argument("--start-year", type=int, default=2014)
parser.add_argument("--end-year", type=int, default=2026)
parser.add_argument("--manifest", type=Path, help="Inventario separado para conservar la descarga anterior")
args = parser.parse_args()
result = collect_history(args.root, args.start_year, args.end_year, manifest_path=args.manifest)
print(f"Guardados {len(result['entries'])} archivos; corte confirmado {result['cutoff']}")
