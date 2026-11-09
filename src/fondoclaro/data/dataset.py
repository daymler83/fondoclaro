"""Datos oficiales verificados, sin red durante una ejecución de informes."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from ..config import Blocked
from ..serialization import canonical,digest,file_hash,read_json
from .loaders import load_sii_uf,load_sp_csv,load_sp_published


@dataclass
class OfficialHistory:
    root: Path
    path: Path
    manifest: dict
    uf: dict
    quotas: dict
    csv_paths: dict
    uf_files: list
    published: dict

    @property
    def cutoff(self):return date.fromisoformat(self.manifest["cutoff"])

    @property
    def data_version(self):return digest(canonical([(e["url"],e.get("form"),e["sha256"]) for e in self.manifest["entries"]]))


def load_official_history(root:Path,manifest_path:Path):
    root=root.resolve();manifest=read_json(manifest_path)
    if manifest["errors"]:raise Blocked("HISTORY_INCOMPLETE")
    uf={};quotas={};csv_paths={};uf_files=[];published={}
    for e in manifest["entries"]+manifest.get("landing_pages",[]):
        path=(root/e["path"]).resolve()
        if e.get("kind")!="OFFICIAL_RAW" or urlsplit(e["url"]).hostname not in ("www.spensiones.cl","spensiones.cl","www.sii.cl"):
            raise Blocked("NON_OFFICIAL_SOURCE")
        if not path.is_relative_to(root) or file_hash(path)!=e["sha256"]:raise Blocked("HISTORY_RAW_HASH_MISMATCH")
        if e["source"]=="sii_uf":
            data=load_sii_uf(path,e["year"])
            if uf.keys()&data.keys():raise Blocked("HISTORY_DUPLICATE_UF")
            uf.update(data);uf_files.append((e["year"],path))
        elif e["source"]=="sp_quota_history":
            if e["fund"] in quotas:raise Blocked("HISTORY_DUPLICATE_FUND")
            quotas[e["fund"]]=load_sp_csv(path);csv_paths[e["fund"]]=path
        elif e["source"]=="sp_published_returns":
            if e["period"] in published:raise Blocked("HISTORY_DUPLICATE_PERIOD")
            published[e["period"]]=load_sp_published(path,e["period"])
    if set(quotas)!=set("ABCDE") or not uf:raise Blocked("HISTORY_INCOMPLETE")
    return OfficialHistory(root,manifest_path,manifest,uf,quotas,csv_paths,uf_files,published)
