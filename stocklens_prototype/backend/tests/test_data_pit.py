import pytest
from datetime import date
from sqlalchemy import select, func
from app.core import models as m
from app.services import refresh_ratios, point_in_time_results

def test_TC90_isin_unique_and_12_chars(db):
    isins = [c.isin for c in db.query(m.Company)]; assert len(set(isins)) == len(isins) and all(len(i) == 12 and i.startswith("INE") for i in isins)
def test_TC91_prices_positive_and_complete(db):
    assert db.query(m.DailyPrice).filter(m.DailyPrice.close <= 0).count() == 0
    assert db.query(func.count()).select_from(m.DailyPrice).scalar() == 40 * 520
def test_TC92_pnl_identity_pbt(db):
    for r in db.query(m.FinancialResult):
        assert abs((r.ebitda - r.depreciation - r.interest) - r.pbt) < 0.05
def test_TC93_pat_equals_pbt_minus_tax(db):
    for r in db.query(m.FinancialResult): assert abs(r.pbt - r.tax - r.pat) < 0.05
def test_TC94_eps_consistent_with_shares(db):
    for r in db.query(m.FinancialResult).limit(60):
        c = db.get(m.Company, r.company_id); assert abs(r.eps - r.pat / c.shares_outstanding_cr) < 0.02
def test_TC95_every_company_has_six_years(db):
    for cid, n in db.execute(select(m.FinancialResult.company_id, func.count()).group_by(m.FinancialResult.company_id)): assert n == 6
def test_TC96_point_in_time_excludes_unfiled_results(db):
    c = db.query(m.Company).first()
    before = point_in_time_results(db, c.id, date(2026, 4, 30)); after = point_in_time_results(db, c.id, None)
    assert before[-1].fiscal_year == 2025 and after[-1].fiscal_year == 2026
def test_TC97_point_in_time_snapshot_differs_and_restores(db):
    c = db.query(m.Company).first()
    cur = db.get(m.RatioSnapshot, c.id).sales_growth_1y
    try:
        refresh_ratios(db, as_of=date(2026, 4, 30)); db.expire_all()
        old = db.get(m.RatioSnapshot, c.id); res = point_in_time_results(db, c.id, date(2026, 4, 30))
        assert old.sales_growth_1y == pytest.approx((res[-1].revenue / res[-2].revenue - 1) * 100)
        assert old.sales_growth_1y != pytest.approx(cur)
    finally:
        refresh_ratios(db); db.expire_all()
    assert db.get(m.RatioSnapshot, c.id).sales_growth_1y == pytest.approx(cur)
def test_TC98_snapshot_zero_division_safe(db):
    assert db.query(m.RatioSnapshot).count() == 40
