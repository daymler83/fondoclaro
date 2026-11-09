"""Recolección explícita de archivos públicos para el contraste histórico.

Este módulo no usa rentabilidades publicadas como insumo del cálculo.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import Blocked, FUNDS, MONTHS, ZONE, period_end, shift_month
from ..serialization import digest, file_hash, read_json, write_json
from .sources import SP_CSV, SP_RETURNS


def archive_response(root, source, url, payload, *, form=None):
    """La huella incluye petición y bytes; preserva peticiones POST de contraste."""
    stamp = datetime.now(ZONE).strftime("%Y-%m-%d")
    identity = digest((url + str(form)).encode() + b"\0" + payload)
    directory = root / "raw_data" / source / stamp / identity
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "response.raw"
    info = dict(url=url, method="POST" if form else "GET", form=form, sha256=digest(payload),
                downloaded_at=datetime.now(ZONE).isoformat(), kind="OFFICIAL_RAW")
    if path.exists() and file_hash(path) != info["sha256"]:
        raise Blocked("RAW_ARCHIVE_INTEGRITY_ERROR")
    if not path.exists():
        path.write_bytes(payload)
        write_json(directory / "source.json", info)
    return dict(path=str(path.relative_to(root)), source=source, **read_json(directory / "source.json"))


def request_public(root, source, url, *, form=None):
    request = Request(url, data=urlencode(form).encode() if form else None,
                      headers={"User-Agent": "FondoClaro/0.1 official-source-validation"})
    with urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise Blocked(f"HTTP_{response.status}")
        payload = response.read(30_000_001)
    if not payload or len(payload) > 30_000_000:
        raise Blocked("RAW_SIZE_INVALID")
    return archive_response(root, source, url, payload, form=form)


def collect_history(root: Path, start_year=2014, end_year=2026, golden_months=24, *, manifest_path: Path | None = None):
    root = root.resolve()
    jobs = []
    # La fecha de confirmación se lee de cada página oficial, nunca de la fecha
    # del PC ni de un valor financiero supuesto.
    confirmations, landing_pages = {}, []
    for fund in FUNDS:
        entry = request_public(root, "sp_landing", f"https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFP.php?tf={fund}")
        entry["fund"] = fund
        landing_pages.append(entry)
        text = (root / entry["path"]).read_bytes().decode("latin-1")
        match = re.search(r"fecconf=(\d{8})", text)
        if not match:
            raise Blocked("SP_CONFIRMATION_DATE_MISSING")
        confirmations[fund] = date(int(match[1][:4]), int(match[1][4:6]), int(match[1][6:]))
        url = SP_CSV + "?" + urlencode(dict(aaaaini=start_year, aaaafin=end_year, tf=fund, fecconf=match[1]))
        jobs.append(("sp_quota_history", url, None, dict(fund=fund, start_year=start_year, end_year=end_year)))
    cutoff = min(confirmations.values())
    if cutoff != period_end(cutoff.strftime("%Y-%m")):
        cutoff = shift_month(cutoff, -1)
    for year in range(start_year, end_year+1):
        jobs.append(("sii_uf", f"https://www.sii.cl/valores_y_fechas/uf/uf{year}.htm", None, dict(year=year)))
    for offset in reversed(range(golden_months)):
        d = shift_month(cutoff, -offset)
        form = dict(aaaa=str(d.year), mm=f"{d.month:02}", btn="Buscar")
        jobs.append(("sp_published_returns", SP_RETURNS + "&template=0", form, dict(period=d.strftime("%Y-%m"))))
    jobs.extend([
        ("sp_methodology", "https://www.spensiones.cl/apps/GetFile.php?id=001&namefile=CAFP2268.pdf", None, {}),
        ("sp_methodology", "https://www.spensiones.cl/portal/institucional/594/w3-article-7457.html", None, {}),
        ("sp_methodology", "https://www.spensiones.cl/portal/institucional/594/articles-16643_recurso_1.pdf", None, dict(period="2025-06")),
        ("sp_methodology", "https://www.spensiones.cl/portal/institucional/594/articles-16971_recurso_1.pdf", None, dict(period="2026-02")),
    ])
    output = dict(created_at=datetime.now(ZONE).isoformat(), requested_start_year=start_year,
                  requested_end_year=end_year, cutoff=str(cutoff), golden_months=golden_months,
                  landing_pages=landing_pages, entries=[], errors=[])
    manifest = manifest_path or root / "raw_data" / "history_manifest.json"

    def job(task):
        source, url, form, extra = task
        try:
            result = request_public(root, source, url, form=form)
            data = (root/result["path"]).read_bytes()
            if source == "sp_quota_history" and b"Fecha;" not in data:
                raise Blocked("SP_CSV_NOT_RETURNED")
            if source == "sii_uf" and b"table_export" not in data:
                raise Blocked("SII_SCHEMA_CHANGED")
            if source == "sp_published_returns":
                end = period_end(extra["period"])
                title = f"{MONTHS[end.month].capitalize()} de {end.year}".encode("latin-1")
                if title not in data:
                    raise Blocked("SP_RETURNED_DIFFERENT_PERIOD")
            return dict(**result, **extra), None
        except (OSError, ValueError) as exc:
            return None, dict(source=source, url=url, form=form, **extra, error=str(exc))

    # Dos conexiones como máximo; no se modifica la configuración global.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for index, (entry, error) in enumerate(pool.map(job, jobs), 1):
            (output["entries"] if entry else output["errors"]).append(entry or error)
            write_json(manifest, output)
            print(f"{index}/{len(jobs)} {entry['source'] if entry else error['source']} {'OK' if entry else 'ERROR'}", flush=True)
    if output["errors"]:
        raise Blocked(f"HISTORY_DOWNLOAD_FAILED: {len(output['errors'])} archivos; ver {manifest}")
    return output
