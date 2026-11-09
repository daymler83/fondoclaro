"""Descarga explícita de fuentes públicas, sin acceso a credenciales."""
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import Blocked, FUNDS, ZONE
from ..serialization import file_hash, write_json
from .sources import BCCH_DAILY, SP_CSV, SP_RETURNS


def save_raw(root: Path, source: str, url: str, payload: bytes) -> Path:
    from ..serialization import digest
    stamp = datetime.now(ZONE).strftime("%Y-%m-%d")
    folder = root / "raw_data" / source / stamp / digest(payload)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "response.raw"
    if not path.exists():
        path.write_bytes(payload)
        write_json(folder / "source.json", dict(url=url, sha256=file_hash(path), downloaded_at=datetime.now(ZONE).isoformat(), kind="OFFICIAL_RAW"))
    return path


def fetch(root: Path, source="all", year=None) -> list[Path]:
    year = year or datetime.now(ZONE).year
    jobs = []
    if source in ("all", "sp"):
        jobs.append(("sp_rentabilidad", SP_RETURNS))
        for fund in FUNDS:
            params = urlencode(dict(aaaaini=year, aaaafin=year, tf=fund, fecconf=datetime.now(ZONE).strftime("%Y%m%d")))
            jobs.append((f"sp_cuota_{fund}", SP_CSV + "?" + params))
    if source in ("all", "bcch"):
        jobs.append(("bcch", BCCH_DAILY))
    paths = []
    for name, url in jobs:
        try:
            with urlopen(Request(url, headers={"User-Agent": "FondoClaro/0.1 public-data"}), timeout=20) as response:
                payload = response.read(25_000_001)
            if not payload or len(payload) > 25_000_000:
                raise Blocked("Respuesta vacía o demasiado grande")
            paths.append(save_raw(root, name, url, payload))
        except (OSError, ValueError) as exc:
            raise Blocked(f"FETCH_FAILED {name}; se conservaron {len(paths)} archivos. {type(exc).__name__}") from exc
    return paths
