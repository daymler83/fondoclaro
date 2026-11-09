import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from html import unescape
from pathlib import Path

from ..config import Blocked
from ..serialization import file_hash, read_json


def cl_decimal(text: str) -> Decimal:
    try:
        result = Decimal(text.strip().replace(".", "").replace(",", ".").replace("%", ""))
        if not result.is_finite():
            raise InvalidOperation()
        return result
    except InvalidOperation as exc:
        raise Blocked(f"Número es-CL inválido: {text!r}") from exc


@dataclass(frozen=True)
class AFPObservation:
    date: date
    afp: str
    quota: Decimal
    assets: Decimal
    confirmed: bool = True


def load_sp_csv(path: Path) -> list[AFPObservation]:
    """CSV oficial por bloques/años/AFP; conserva la marca de provisionalidad."""
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("latin-1")), delimiter=";"))
    result, seen, names, labels, confirmed, expecting_labels = [], set(), None, None, None, False
    for row in rows:
        if not row or not any(row):
            continue
        if row[0].strip() in ("Valores Confirmados", "Valores Provisorios", "Valores Provisorios - Sujetos a Confirmacion"):
            confirmed = row[0].strip() == "Valores Confirmados"
            continue
        if row[0] == "Fecha":
            names, expecting_labels = row, True
            continue
        if expecting_labels:
            labels, expecting_labels = row, False
            if 1 + 2 * len(names[1::2]) != len(labels) or labels[1:] != [v for _ in names[1::2] for v in ("Valor Cuota", "Valor Patrimonio")]:
                raise Blocked("SP_SCHEMA_CHANGED: columnas cuota/patrimonio")
            if len(set(names[1::2])) != len(names[1::2]) or any(not name.strip() for name in names[1::2]):
                raise Blocked("SP_SCHEMA_CHANGED: AFP repetida o vacía")
            continue
        if names is None or labels is None or confirmed is None:
            raise Blocked("SP_SCHEMA_CHANGED: falta encabezado Fecha/estado")
        if len(row) != len(labels):
            raise Blocked("SP_SCHEMA_CHANGED: cantidad de columnas")
        d = date.fromisoformat(row[0])
        for index in range(1, len(labels), 2):
            afp = names[index]
            key = (d, afp)
            if key in seen:
                raise Blocked("DUPLICATE: fecha/AFP")
            seen.add(key)
            if row[index].strip() in ("", "-", "(*)") and row[index + 1].strip() in ("", "-", "(*)"):
                continue  # ausencia explícita, nunca relleno
            quota, assets = cl_decimal(row[index]), cl_decimal(row[index + 1])
            if quota <= 0 or assets < 0:
                raise Blocked("Valor cuota/patrimonio fuera de rango")
            result.append(AFPObservation(d, afp, quota, assets, confirmed))
    if expecting_labels:
        raise Blocked("SP_SCHEMA_CHANGED: encabezado incompleto")
    if not result:
        raise Blocked("SP_EMPTY")
    return result


def load_sii_uf(path: Path, year: int) -> dict[date, Decimal]:
    """Matriz anual pública SII, columnas día/Ene...Dic. Vacíos son ausencias."""
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    table = re.search(r'<table\b[^>]*\bid=["\']table_export["\'][^>]*>(.*?)</table>', text, re.I|re.S)
    if not table:
        raise Blocked("SII_SCHEMA_CHANGED: table_export")
    headers = re.findall(r'<th\b[^>]*>(.*?)</th>', table[1].split("</thead>")[0], re.I|re.S)
    clean = lambda value: unescape(re.sub(r"<[^>]+>", "", value)).strip()
    if [clean(x) for x in headers][1:] != ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]:
        raise Blocked("SII_SCHEMA_CHANGED: meses")
    output = {}
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', table[1], re.I|re.S):
        cells = [clean(x) for x in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.I|re.S)]
        if not cells or not cells[0].isdigit():
            continue
        if len(cells) != 13:
            raise Blocked("SII_SCHEMA_CHANGED: cantidad de columnas")
        day = int(cells[0])
        for month, value in enumerate(cells[1:], 1):
            if not value:
                continue
            try:
                d = date(year, month, day)
            except ValueError as exc:
                raise Blocked("SII_VALUE_ON_INVALID_DATE") from exc
            number = cl_decimal(value)
            if d in output or number <= 0:
                raise Blocked("SII_DUPLICATE_OR_INVALID_UF")
            output[d] = number
    if not output:
        raise Blocked("SII_EMPTY")
    return output


def load_sp_published(path: Path, period: str):
    """Fila de cada AFP y SISTEMA; todos los porcentajes publicados se preservan."""
    from ..config import MONTHS, period_end
    cutoff = period_end(period)
    raw = path.read_bytes().decode("latin-1")
    if f"{MONTHS[cutoff.month].capitalize()} de {cutoff.year}" not in raw:
        raise Blocked("SP_WRONG_PERIOD")
    parts = re.split(r"RENTABILIDAD REAL DEL FONDO TIPO ([ABCDE])", raw)[1:]
    result = {}
    for fund, section in zip(parts[::2], parts[1::2]):
        observations = {}
        header = unescape(re.sub(r"<[^>]+>", " ", section.split("SISTEMA")[0]))
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", section, re.I|re.S):
            cells = [unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.I|re.S)]
            if not cells or cells[0] not in ("CAPITAL","CUPRUM","HABITAT","MODELO","PLANVITAL","PROVIDA","UNO","SISTEMA"):
                continue
            if cells[0] in observations or len(cells) not in (5,6):
                raise Blocked("SP_PUBLISHED_SCHEMA_CHANGED")
            keys = ("r_1m","year_to_date","r_12m","annualized_since_2002","annualized_since_origin")
            observations[cells[0]] = {key: cl_decimal(value)/100 if value else None for key,value in zip(keys,cells[1:])}
        if "SISTEMA" not in observations:
            raise Blocked("SP_PUBLISHED_SYSTEM_MISSING")
        result[fund] = dict(period=period, rows=observations, header_text=" ".join(header.split()))
    if set(result) != set("ABCDE"):
        raise Blocked("SP_PUBLISHED_FUND_MISSING")
    return result


def load_sp_validation(path: Path) -> dict[str, dict[str, Decimal]]:
    """Captura de rentabilidad vigente: mensual y 12 meses (no insumo)."""
    raw = path.read_bytes().decode("latin-1")
    tables = re.split(r"RENTABILIDAD REAL DEL FONDO TIPO ([ABCDE])", raw)[1:]
    out = {}
    for fund, section in zip(tables[::2], tables[1::2]):
        match = re.search(r"<td[^>]*>\s*SISTEMA\s*</td>(.*?)</tr>", section, re.S | re.I)
        if not match:
            raise Blocked("SP_SCHEMA_CHANGED: fila SISTEMA")
        cells = re.findall(r"<td[^>]*>(.*?)</td>", match[1], re.S | re.I)
        values = [cl_decimal(unescape(re.sub("<[^>]+>", "", cell)).strip()) / 100 for cell in cells if "%" in cell]
        if len(values) < 3:
            raise Blocked("SP_SCHEMA_CHANGED: horizontes")
        out[fund] = {"r_1m": values[0], "r_12m": values[2]}
    if set(out) != set("ABCDE"):
        raise Blocked("SP_SCHEMA_CHANGED: faltan fondos")
    return out


def load_bcch_daily(path: Path) -> Decimal:
    text = path.read_text()
    match = re.search(r'<label id="lblValor1_1"[^>]*>([^<]+)</label>', text)
    if not match:
        raise Blocked("BCCH_SCHEMA_CHANGED: UF diaria")
    return cl_decimal(match[1])


def load_normalized(path: Path):
    """Contrato interno, no se presenta como un formato oficial."""
    from .checks import check_series
    obj = read_json(path)
    if set(obj) != {"kind", "source_hashes", "fund", "observations"}:
        raise Blocked("NORMALIZED_SCHEMA_CHANGED")
    if obj["kind"] not in ("SYNTHETIC", "OFFICIAL"):
        raise Blocked("Origen desconocido")
    seen, series = set(), {}
    for row in obj["observations"]:
        d = date.fromisoformat(row["date"])
        if d in seen:
            raise Blocked("DUPLICATE: fecha")
        seen.add(d)
        series[d] = (Decimal(row["quota"]), Decimal(row["uf"]))
    check_series(series)
    return obj, series


def verify_fixture(path: Path, metadata: Path):
    info = read_json(metadata)
    if file_hash(path) != info["sha256"]:
        raise Blocked("Hash de fixture distinto")
    return info
