from calendar import monthrange
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from fondoclaro.config import Blocked
from fondoclaro.data.loaders import load_sii_uf,load_sp_csv,load_sp_published
from fondoclaro.finance.system import build_system_index,month_snapshots,weighted_period_return
from fondoclaro.serialization import file_hash,read_json

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def history():
    path=ROOT/"tests"/"fixtures"/"official_history"/"manifest.json"
    return read_json(path)


def source_path(entry):
    return ROOT/entry["path"]


def test_all_historical_raw_hashes(history):
    assert not history["errors"]
    for entry in history["entries"]+history["landing_pages"]:
        assert file_hash(source_path(entry))==entry["sha256"]


@pytest.mark.parametrize("fund",list("ABCDE"))
def test_real_csv_blocks_and_provisional_data(history,fund):
    entry=next(e for e in history["entries"] if e["source"]=="sp_quota_history" and e["fund"]==fund)
    data=load_sp_csv(source_path(entry))
    assert min(r.date for r in data)==date(2014,1,1)
    assert max(r.date for r in data if r.confirmed)==date(2026,10,31)
    assert any(not r.confirmed and r.date==date(2026,11,5) for r in data)
    snapshots=month_snapshots(data,date(2026,10,31))
    assert len(snapshots)==154
    assert set(snapshots[date(2014,1,31)])==set(("CAPITAL","CUPRUM","HABITAT","MODELO","PLANVITAL","PROVIDA"))
    assert "UNO" in snapshots[date(2026,10,31)]


@pytest.mark.parametrize("year",range(2014,2027))
def test_real_sii_year_no_daily_gaps(history,year):
    entry=next(e for e in history["entries"] if e["source"]=="sii_uf" and e["year"]==year)
    data=load_sii_uf(source_path(entry),year)
    assert min(data)==date(year,1,1)
    if year<2026:
        assert len(data)==(date(year+1,1,1)-date(year,1,1)).days
    for month in range(1,13 if year<2026 else 11):
        assert date(year,month,monthrange(year,month)[1]) in data


def test_real_published_periods_and_annual_values(history):
    entries=[e for e in history["entries"] if e["source"]=="sp_published_returns"]
    assert len(entries)==24
    for entry in entries:
        data=load_sp_published(source_path(entry),entry["period"])
        assert set(data)==set("ABCDE")
        for fund in data.values():
            row=fund["rows"]["SISTEMA"]
            assert row["r_1m"] is not None
            assert row["r_12m"] is not None
            assert row["annualized_since_2002"] is not None


def test_published_wrong_period_rejected(history):
    entry=next(e for e in history["entries"] if e["source"]=="sp_published_returns")
    with pytest.raises(Blocked,match="WRONG_PERIOD"):
        load_sp_published(source_path(entry),"2020-01")


def test_index_does_not_consume_validation_publications(history):
    # Solo archivos de cuota/patrimonio y UF; no se carga ningún retorno SP.
    entry=next(e for e in history["entries"] if e["source"]=="sp_quota_history" and e["fund"]=="C")
    uf={}
    for item in history["entries"]:
        if item["source"]=="sii_uf":
            uf.update(load_sii_uf(source_path(item),item["year"]))
    series,steps=build_system_index(load_sp_csv(source_path(entry)),uf,date(2026,10,31))
    assert len(series)==154 and len(steps)==153
    assert all(abs(sum(x["weight"] for x in step["components"])-1)<Decimal("1e-25") for step in steps)


def test_missing_active_afp_cannot_be_silently_reweighted(history):
    entry=next(e for e in history["entries"] if e["source"]=="sp_quota_history" and e["fund"]=="C")
    rows=load_sp_csv(source_path(entry))
    rows=[r for r in rows if not(r.afp=="HABITAT" and r.date==date(2026,10,31))]
    uf={date(2026,9,30):Decimal(40000),date(2026,10,31):Decimal(41000)}
    subset=[r for r in rows if r.date in uf]
    with pytest.raises(Blocked,match="ACTIVE_AFP_MISSING"):
        build_system_index(subset,uf,date(2026,10,31))
