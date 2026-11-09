from datetime import date
from decimal import Decimal, localcontext

import pytest

from fondoclaro.config import shift_month
from fondoclaro.content.manifest import build_manifest
from fondoclaro.finance.engine import calculate
from fondoclaro.serialization import write_json


def synthetic_series(monthly=Decimal("0.003"), last=Decimal("-0.02"), months=120, end=date(2026,10,31)):
    """SYNTHETIC: exclusivamente para pruebas unitarias, nunca CLI real."""
    with localcontext() as ctx:
        ctx.prec = 40
        series = {}
        real = Decimal(100)
        for index in range(months+1):
            if index:
                real *= 1 + (last if index == months else monthly)
            uf = Decimal(25000) + index * 30
            series[shift_month(end, index-months)] = (real*uf, uf)
        return series


@pytest.fixture
def series():
    return synthetic_series()


@pytest.fixture
def results(series):
    return calculate(series, "C", date(2026,10,31))


@pytest.fixture
def manifest(results):
    return build_manifest(results)


@pytest.fixture
def synthetic_raw(tmp_path, series):
    path = tmp_path/"SYNTHETIC.json"
    write_json(path, dict(kind="SYNTHETIC", fund="C", source_hashes=[], observations=[dict(date=str(d), quota=str(q), uf=str(u)) for d,(q,u) in series.items()]))
    return path
