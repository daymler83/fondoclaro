"""Insumos desde 2002, sin validación de un método anual aún no autorizado."""
from datetime import date
from pathlib import Path

import pytest

from fondoclaro.config import Blocked
from fondoclaro.data.history import freeze_history,sii_uf_url
from fondoclaro.data.loaders import load_sii_uf,load_sp_csv
from fondoclaro.serialization import file_hash,read_json,write_json

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/"tests/fixtures/official_history"


@pytest.fixture(scope="module")
def extended():
    return read_json(FIXTURES/"manifest_2002.json")


def test_extended_hashes_and_offline_copies(extended):
    original=read_json(ROOT/"raw_data/history_2002_manifest.json")
    assert extended["requested_start_year"]==2002
    assert extended["requested_end_year"]==2026
    assert extended["errors"]==[]
    assert len(extended["entries"])+len(extended["landing_pages"])==63
    for a,b in zip(original["entries"]+original["landing_pages"],extended["entries"]+extended["landing_pages"]):
        assert a["url"]==b["url"]
        assert file_hash(ROOT/a["path"])==file_hash(ROOT/b["path"])==a["sha256"]==b["sha256"]


@pytest.mark.parametrize("fund",list("ABCDE"))
def test_original_fund_coverage_and_no_invented_prelaunch_history(extended,fund):
    entry=next(e for e in extended["entries"] if e["source"]=="sp_quota_history" and e["fund"]==fund)
    rows=load_sp_csv(ROOT/entry["path"])
    first=min(r.date for r in rows)
    assert first==(date(2002,8,1) if fund in "ABD" else date(2002,1,1))
    assert max(r.date for r in rows if r.confirmed)==date(2026,10,31)
    assert {r.date.year for r in rows}==set(range(2002,2027))
    coverage=read_json(FIXTURES/"coverage_2002.json")["funds"][fund]
    assert coverage["raw_observations"]==len(rows)
    assert coverage["raw_start"]==str(first)
    if fund in "ABD":
        assert all(r.assets==0 for r in rows if r.date<date(2002,9,27))
        assert min(r.date for r in rows if r.assets>0)==date(2002,9,27)
        assert coverage["absences"][0]["reason"]=="FUND_NOT_ACTIVE"
        assert coverage["absences"][0]["end"]=="2002-09-26"


@pytest.mark.parametrize("year",range(2002,2014))
def test_old_sii_years_have_every_day_and_verifiable_values(extended,year):
    entry=next(e for e in extended["entries"] if e["source"]=="sii_uf" and e["year"]==year)
    assert entry["url"]==sii_uf_url(year)
    values=load_sii_uf(ROOT/entry["path"],year)
    assert len(values)==(date(year+1,1,1)-date(year,1,1)).days
    assert min(values)==date(year,1,1)
    assert max(values)==date(year,12,31)
    assert all(value>0 for value in values.values())


def test_freezing_is_idempotent_without_overwriting_original_files(extended,tmp_path):
    entry=dict(next(e for e in extended["entries"] if e["source"]=="sii_uf" and e["year"]==2002))
    original=ROOT/entry["path"]
    source=tmp_path/"raw"/"2002"/"response.raw"
    source.parent.mkdir(parents=True)
    source.write_bytes(original.read_bytes())
    (source.parent/"source.json").write_bytes((original.parent/"source.json").read_bytes())
    entry["path"]=str(source.relative_to(tmp_path))
    manifest=tmp_path/"raw_manifest.json"
    write_json(manifest,dict(entries=[entry],landing_pages=[]))
    target=tmp_path/"fixtures"/"manifest.json"
    frozen=freeze_history(tmp_path,manifest,target)
    before=file_hash(target)
    freeze_history(tmp_path,manifest,target)
    assert file_hash(target)==before
    copied=tmp_path/frozen["entries"][0]["path"]
    copied.write_bytes(b"changed fixture")
    with pytest.raises(Blocked,match="FREEZE_EXISTING_FIXTURE_CHANGED"):
        freeze_history(tmp_path,manifest,target)
    assert file_hash(source)==entry["sha256"]
