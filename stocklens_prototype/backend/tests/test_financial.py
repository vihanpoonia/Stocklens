import pytest
from types import SimpleNamespace as NS
from app.financial import engine as e

def test_TC01_safe_divide_normal(): assert e.safe_divide(10, 4) == 2.5
def test_TC02_safe_divide_zero_denominator(): assert e.safe_divide(5, 0) is None
def test_TC03_safe_divide_none_inputs():
    assert e.safe_divide(None, 3) is None and e.safe_divide(3, None) is None
def test_TC04_growth_positive(): assert e.growth(120, 100) == pytest.approx(20.0)
def test_TC05_growth_negative_base_is_undefined(): assert e.growth(50, -10) is None
def test_TC06_growth_zero_base(): assert e.growth(50, 0) is None
def test_TC07_cagr_known_value(): assert e.cagr(133.1, 100, 3) == pytest.approx(10.0, rel=1e-6)
def test_TC08_cagr_invalid_inputs(): assert e.cagr(100, -5, 3) is None and e.cagr(100, 100, 0) is None
def test_TC09_margins():
    assert e.ebitda_margin(20, 100) == pytest.approx(20) and e.pat_margin(8, 100) == pytest.approx(8)
def test_TC10_roe_uses_average_equity(): assert e.roe(30, 220, 180) == pytest.approx(15.0)   # 30/200
def test_TC11_roce_uses_average_capital_employed():
    ce1, ce0 = e.capital_employed(300, 100), e.capital_employed(260, 100)
    assert e.roce(76, ce1, ce0) == pytest.approx(20.0)                                  # 76/380
def test_TC12_debt_equity_negative_equity_undefined(): assert e.debt_equity(100, -5) is None
def test_TC13_interest_coverage_zero_interest(): assert e.interest_coverage(100, 0) is None
def test_TC14_cfo_pat_loss_making_undefined(): assert e.cfo_to_pat(50, -10) is None
def test_TC15_pe_negative_eps_undefined(): assert e.pe_ratio(100, -2) is None
def test_TC16_peg_requires_positive_growth(): assert e.peg_ratio(20, 0) is None and e.peg_ratio(20, 10) == 2
def test_TC17_ev_ebitda_known(): assert e.ev_ebitda(1000, 300, 100, 150) == pytest.approx(8.0)
def test_TC18_ttm_is_sum_of_four_quarters_not_x4():
    assert e.ttm([10, 12, 11, 15]) == 48 and e.ttm([10, 12, 11, 15]) != 15 * 4
def test_TC19_ttm_needs_exactly_four_quarters():
    assert e.ttm([1, 2, 3]) is None and e.ttm([1, 2, None, 4]) is None

def _res(fy, **k):
    base = dict(fiscal_year=fy, revenue=None, ebitda=None, pbt=None, interest=None, pat=None, eps=None,
                total_equity=None, total_debt=None, cash=None, current_assets=None, current_liabilities=None, cfo=None)
    return NS(**(base | k))

def test_TC20_compute_company_ratios_hand_checked():
    rs = [_res(2023, revenue=1000, pat=100, eps=10, total_equity=500, total_debt=100),
          _res(2024, revenue=1100, pat=110, eps=11, total_equity=560, total_debt=100),
          _res(2025, revenue=1210, pat=121, eps=12.1, total_equity=630, total_debt=90),
          _res(2026, revenue=1331, ebitda=266.2, pbt=190, interest=10, pat=133.1, eps=13.31,
               total_equity=710, total_debt=80, cash=50, current_assets=400, current_liabilities=200, cfo=120)]
    r = e.compute_company_ratios(rs, None, price=200, mcap=2000)
    assert r["sales_growth_1y"] == pytest.approx(10.0) and r["sales_growth_3y"] == pytest.approx(10.0)
    assert r["profit_growth_3y"] == pytest.approx(10.0, rel=1e-6)
    assert r["ebitda_margin"] == pytest.approx(20.0) and r["pat_margin"] == pytest.approx(10.0)
    assert r["roe"] == pytest.approx(133.1 / 670 * 100)
    assert r["roce"] == pytest.approx(200 / ((710 + 80 + 630 + 90) / 2) * 100)
    assert r["pe"] == pytest.approx(200 / 13.31) and r["debt_equity"] == pytest.approx(80 / 710)
    assert r["interest_coverage"] == pytest.approx(20.0) and r["cfo_pat"] == pytest.approx(120 / 133.1)
    assert r["ev_ebitda"] == pytest.approx((2000 + 80 - 50) / 266.2)

def test_TC21_missing_history_gives_none_not_crash():
    r = e.compute_company_ratios([_res(2026, revenue=100, pat=10, eps=1, total_equity=50, total_debt=0)], None, 10, 100)
    assert "roe" not in r and "sales_growth_3y" not in r and r["pat_margin"] == pytest.approx(10)
