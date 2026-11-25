"""Ratio refresh job: raw statements + prices -> RatioSnapshot (screener-ready). Supports point-in-time (as_of)."""
from datetime import date
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core import models as m
from app.financial.engine import compute_company_ratios
from app.market.indicators import rsi, period_return

def load_prices(db: Session, as_of: date | None = None):
    q = select(m.DailyPrice.company_id, m.DailyPrice.trading_date, m.DailyPrice.close, m.DailyPrice.volume)
    if as_of: q = q.where(m.DailyPrice.trading_date <= as_of)
    df = pd.DataFrame(db.execute(q).all(), columns=["company_id", "date", "close", "volume"])
    closes = df.pivot(index="date", columns="company_id", values="close").sort_index()
    vols = df.pivot(index="date", columns="company_id", values="volume").sort_index()
    return closes, vols

def point_in_time_results(db: Session, company_id: int, as_of: date | None):
    q = select(m.FinancialResult).where(m.FinancialResult.company_id == company_id)
    if as_of: q = q.where(m.FinancialResult.filing_date <= as_of)   # no look-ahead bias
    return list(db.scalars(q.order_by(m.FinancialResult.fiscal_year)))

def refresh_ratios(db: Session, as_of: date | None = None) -> int:
    closes, vols = load_prices(db, as_of)
    db.query(m.RatioSnapshot).delete()
    n = 0
    for c in db.scalars(select(m.Company)):
        if c.id not in closes.columns: continue
        cl = closes[c.id].dropna(); vo = vols[c.id].dropna()
        if cl.empty: continue
        price = float(cl.iloc[-1]); mcap = price * (c.shares_outstanding_cr or 0)
        res = point_in_time_results(db, c.id, as_of)
        sh_q = select(m.Shareholding).where(m.Shareholding.company_id == c.id)
        if as_of: sh_q = sh_q.where(m.Shareholding.period_end <= as_of)
        sh = db.scalars(sh_q.order_by(m.Shareholding.period_end.desc())).first()
        r = compute_company_ratios(res, sh, price, mcap)
        r_rsi = rsi(cl, 14).iloc[-1]
        snap = m.RatioSnapshot(company_id=c.id, as_of_date=cl.index[-1], price=round(price, 2),
                               market_cap=round(mcap, 2), **r,
                               ret_1m=period_return(cl, 21), ret_3m=period_return(cl, 63), ret_6m=period_return(cl, 126),
                               rsi_14=None if pd.isna(r_rsi) else float(r_rsi),
                               pct_from_52w_high=float((cl.iloc[-1] / cl.iloc[-252:].max() - 1) * 100),
                               volume_ratio=float(vo.iloc[-20:].mean() / vo.iloc[-100:].mean()) if len(vo) >= 100 else None)
        db.add(snap); n += 1
    db.commit()
    return n
