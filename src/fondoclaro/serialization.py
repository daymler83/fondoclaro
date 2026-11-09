import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


def _default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (Decimal, date, Path)):
        return str(value)
    raise TypeError(type(value).__name__)


def canonical(value) -> bytes:
    normalized = json.loads(json.dumps(value, default=_default, ensure_ascii=False, allow_nan=False))
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_hash(path: Path) -> str:
    return digest(path.read_bytes())


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")


def read_json(path: Path):
    return json.loads(path.read_text())
