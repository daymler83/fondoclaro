from datetime import date
from decimal import Decimal, localcontext

import pytest
from hypothesis import given, strategies as st

from fondoclaro.config import BASE, Blocked, period_end, shift_month
from fondoclaro.data.checks import select_latest
from fondoclaro.finance.engine import calculate, chart_window
from fondoclaro.finance.formatting import example_amount, money, percent, rounded_money, rounded_percent
from fondoclaro.finance.independent import compare, recalculate

from conftest import synthetic_series


@pytest.mark.parametrize("r", [Decimal(".02"), Decimal("-.02"), Decimal(0)])
def test_month_formula(r):
    end = date(2026,10,31)
    series = synthetic_series(last=r)
    assert abs(calculate(series,"C",end).metrics[1].real-r) < Decimal("1e-35")


def test_deflation():
    result=calculate({date(2026,9,30):(Decimal(100),Decimal(100)),date(2026,10,31):(Decimal(100),Decimal(99))},"C",date(2026,10,31))
    assert result.metrics[1].real > 0
    assert result.metrics[1].nominal == 0


def test_horizons_and_annualized(results):
    assert set(results.metrics) == {1,12,60,120}
    assert len(results.real_index) == 121
    assert results.negative_months_120 == 1
    assert results.metrics[120].annualized is not None
    assert results.metrics[12].annualized is None
    n, points=chart_window(results)
    assert n == 120
    assert points[0][1] == BASE
    with localcontext() as ctx:
        ctx.prec=40
        assert abs(points[-1][1]-BASE*(1+results.metrics[120].real)) < Decimal("1e-30")


@pytest.mark.parametrize("n", [1,12,60,120])
def test_independent_reader(synthetic_raw, results,n):
    compare(results.metrics[n].real,recalculate(synthetic_raw,results.cutoff,n))


def test_independent_rejects_disagreement():
    with pytest.raises(Blocked):
        compare(Decimal(".01"),Decimal(".011"))


@pytest.mark.parametrize("months,horizon",[(75,60),(30,12),(8,8)])
def test_short_history(months,horizon):
    result=calculate(synthetic_series(months=months),"C",date(2026,10,31))
    assert result.metrics[120].status == "NO_DISPONIBLE"
    assert chart_window(result)[0] == horizon


def test_gap_omits_not_fills(series):
    del series[date(2020,1,31)]
    result=calculate(series,"C",date(2026,10,31))
    assert result.metrics[120].real is None
    assert result.metrics[60].real is not None


def test_current_gap_blocks(series):
    del series[date(2026,9,30)]
    with pytest.raises(Blocked,match="R_1M"):
        calculate(series,"C",date(2026,10,31))


@pytest.mark.parametrize("bad",[Decimal(0),Decimal(-1),Decimal("NaN"),Decimal("Infinity")])
def test_invalid_data_blocks(series,bad):
    series[date(2026,10,31)]=(bad,Decimal(20000))
    with pytest.raises(Blocked):
        calculate(series,"C",date(2026,10,31))


def test_expired_fund():
    with pytest.raises(Blocked,match="NOT_ACTIVE"):
        calculate(synthetic_series(end=date(2027,4,30)),"C",date(2027,4,30))


def test_latest_and_calendar(series):
    assert select_latest(series,date(2026,11,8)) == date(2026,10,31)
    assert select_latest(series,date(2026,10,8)) == date(2026,9,30)
    assert shift_month(date(2024,3,31),-1) == date(2024,2,29)
    assert period_end("2026-10") == date(2026,10,31)
    with pytest.raises(Blocked):
        period_end("2026-1")


@pytest.mark.parametrize("value,expected",[("-.02","-2,0%"),(".48","+48,0%"),("-.00001","0,0%"),("0","0,0%")])
def test_format_percent(value,expected):
    assert percent(Decimal(value)) == expected


def test_rounding_counterexample_is_explicit():
    r=Decimal("-.0005")
    assert percent(r) == "-0,1%"
    assert money(BASE*(1+r)) == "$10.000.000"
    assert BASE*(1+rounded_percent(r)/100) == Decimal(9990000)
    assert money(example_amount(r)) == "$9.990.000"


@given(st.integers(min_value=0,max_value=999))
def test_required_universal_rounding_property(k):
    r=-(Decimal(k)/1000+Decimal(".0005"))
    visible_percent=Decimal(percent(r).replace("%","").replace(",","."))
    visible_money=Decimal(money(example_amount(r)).replace("$","").replace(".",""))
    assert visible_money == BASE*(1+visible_percent/100)


@given(st.decimals(min_value="-.99999",max_value=5,places=7,allow_nan=False,allow_infinity=False))
def test_rounding_property_for_all_valid_returns(r):
    visible_percent=Decimal(percent(r).replace("%","").replace(",","."))
    visible_money=Decimal(money(example_amount(r)).replace("$","").replace(".",""))
    assert visible_money == BASE*(1+visible_percent/100)
