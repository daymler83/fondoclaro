"""Arranque del bot para un servidor (Railway u otro).

No pasa por `cli.py` a propósito: ese módulo importa el renderizador, que
necesita Cairo instalado en el sistema. El bot no dibuja nada —solo entrega
imágenes ya aprobadas— así que arranca sin ninguna dependencia externa.

La raíz de datos se toma de FONDOCLARO_ROOT para poder apuntarla a un disco
persistente. Si ese disco está vacío, se copia una vez lo que trae el
repositorio, de modo que el bot pueda responder desde el primer arranque.
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fondoclaro.workflow.registry import Registry      # noqa: E402
from fondoclaro.workflow.telegram import serve         # noqa: E402

SEMILLA = Path(__file__).resolve().parent / "seed"


def preparar(root: Path) -> Path:
    """Siembra el disco persistente la primera vez."""
    root.mkdir(parents=True, exist_ok=True)
    destino = root / "reports"
    if destino.exists() and any(destino.glob("*/run.json")):
        return root
    origen = SEMILLA / "reports"
    if origen.exists():
        shutil.copytree(origen, destino, dirs_exist_ok=True)
        print(f"Sembrado desde {origen} -> {destino}", flush=True)
    return root


def main():
    root = preparar(Path(os.environ.get("FONDOCLARO_ROOT", ".")).resolve())
    print(f"FondoClaro: raíz de datos en {root}", flush=True)
    serve(Registry(root))


if __name__ == "__main__":
    main()
