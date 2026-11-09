from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from fondoclaro.config import Blocked
from fondoclaro.data.checks import revisions
from fondoclaro.data.collectors import save_raw
from fondoclaro.data.loaders import load_bcch_daily, load_normalized, load_sp_csv, load_sp_validation, verify_fixture
from fondoclaro.serialization import read_json, write_json

FIXTURES=Path(__file__).parent/"fixtures"


@pytest.mark.parametrize("name",["sp_c_2025.csv","sp_rentabilidad.html","bcch_diario.html"])
def test_official_fixture_hash(name):
    assert verify_fixture(FIXTURES/name,FIXTURES/(name+".source.json"))["kind"] == "OFFICIAL_RAW"


def test_actual_sp_csv():
    rows=load_sp_csv(FIXTURES/"sp_c_2025.csv")
    assert len(rows) == 365*7
    assert rows[0].date == date(2025,1,1)
    assert rows[0].quota == Decimal("60512.60")
    assert rows[0].assets == Decimal("11006399466865")


def test_actual_validation_html():
    data=load_sp_validation(FIXTURES/"sp_rentabilidad.html")
    assert set(data) == set("ABCDE")
    assert data["C"] == {"r_1m": Decimal(".0097"),"r_12m":Decimal("0")}


def test_actual_bcch_daily():
    assert load_bcch_daily(FIXTURES/"bcch_diario.html") == Decimal("41290.15")


def test_csv_schema_changed(tmp_path):
    path=tmp_path/"changed.csv"
    path.write_bytes((FIXTURES/"sp_c_2025.csv").read_bytes().replace(b"Valor Cuota",b"Otra Columna"))
    with pytest.raises(Blocked,match="SCHEMA_CHANGED"):
        load_sp_csv(path)


def test_duplicate_normalized(synthetic_raw):
    obj=read_json(synthetic_raw)
    obj["observations"].append(obj["observations"][0])
    write_json(synthetic_raw,obj)
    with pytest.raises(Blocked,match="DUPLICATE"):
        load_normalized(synthetic_raw)


def test_normalized_reader(synthetic_raw):
    obj,series=load_normalized(synthetic_raw)
    assert obj["kind"] == "SYNTHETIC"
    assert len(series) == 121


def test_revisions_are_detected_without_mutation():
    old={date(2025,1,31):(Decimal(1),Decimal(2))}
    new={date(2025,1,31):(Decimal(3),Decimal(2))}
    diff=revisions(old,new)
    assert diff[0]["before"] == ["1","2"]
    assert old[date(2025,1,31)][0] == 1


def test_raw_downloads_are_content_addressed(tmp_path):
    p=save_raw(tmp_path,"sp","https://www.spensiones.cl/example",b"original")
    q=save_raw(tmp_path,"sp","https://www.spensiones.cl/example",b"revised")
    assert p != q
    assert p.read_bytes() == b"original"


