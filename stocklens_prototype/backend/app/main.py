import json
from datetime import date
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db, Base, engine
from app.core import models as m
from app.screener.engine import run_screen, FIELDS, QueryError
from app.quality.earnings_quality import assess
from app.quality.guidance import deviation
from app.sectors.scoring import sector_scores
from app.services import load_prices, point_in_time_results
from app.market.indicators import sma, rsi

app = FastAPI(title="StockLens API", description="Indian Stock Market Intelligence Platform (MVP)", version="0.2.0")
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

def _company(db: Session, symbol: str) -> m.Company:
    c = db.scalar(select(m.Company).where(m.Company.symbol == symbol.upper()))
    if not c: raise HTTPException(404, f"Company {symbol} not found")
    return c

@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    try:
        n = db.query(m.Company).count(); dbs = "connected"
    except Exception:
        n, dbs = 0, "error"
    return {"api": "healthy", "database": dbs, "companies": n, "version": app.version}

@app.get("/api/v1/data-quality")
def data_quality(db: Session = Depends(get_db)):
    return [dict(dataset=r.dataset, status=r.status, mode=r.mode, last_updated=str(r.last_updated), note=r.note)
            for r in db.scalars(select(m.DataQualityLog))]

@app.get("/api/v1/companies")
def companies(q: str = "", sector: str | None = None, limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    stmt = select(m.Company, m.Sector.name).join(m.Sector)
    if q: stmt = stmt.where(m.Company.company_name.ilike(f"%{q}%") | m.Company.symbol.ilike(f"%{q}%"))
    if sector: stmt = stmt.where(m.Sector.name == sector)
    return [dict(id=c.id, symbol=c.symbol, company_name=c.company_name, isin=c.isin, sector=s, exchange=c.exchange)
            for c, s in db.execute(stmt.order_by(m.Company.symbol).limit(limit))]

@app.get("/api/v1/companies/{symbol}/overview")
def overview(symbol: str, db: Session = Depends(get_db)):
    c = _company(db, symbol)
    snap = db.get(m.RatioSnapshot, c.id)
    d = {k: getattr(snap, k) for k in FIELDS} if snap else {}
    return {"symbol": c.symbol, "company_name": c.company_name, "isin": c.isin, "exchange": c.exchange,
            "sector": c.sector.name, "as_of": str(snap.as_of_date) if snap else None,
            "data_mode": "Historical / end-of-day (synthetic)", "ratios": d}

@app.get("/api/v1/companies/{symbol}/financials")
def financials(symbol: str, db: Session = Depends(get_db)):
    c = _company(db, symbol)
    rows = point_in_time_results(db, c.id, None)
    cols = ["fiscal_year", "revenue", "ebitda", "depreciation", "interest", "pbt", "tax", "pat", "eps",
            "total_equity", "total_debt", "cfo", "receivables"]
    return [{k: getattr(r, k) for k in cols} | {"filing_date": str(r.filing_date)} for r in rows]

@app.get("/api/v1/companies/{symbol}/prices")
def prices(symbol: str, days: int = Query(250, ge=5, le=1000), db: Session = Depends(get_db)):
    c = _company(db, symbol)
    rows = db.execute(select(m.DailyPrice.trading_date, m.DailyPrice.close, m.DailyPrice.volume)
                      .where(m.DailyPrice.company_id == c.id).order_by(m.DailyPrice.trading_date.desc()).limit(days)).all()
    s = pd.Series([r.close for r in rows[::-1]], index=[r.trading_date for r in rows[::-1]])
    s50, r14 = sma(s, 50), rsi(s, 14)
    return [{"date": str(d), "close": float(v), "sma50": None if pd.isna(s50[d]) else round(float(s50[d]), 2),
             "rsi14": None if pd.isna(r14[d]) else round(float(r14[d]), 1)} for d, v in s.items()]

@app.get("/api/v1/companies/{symbol}/shareholding")
def shareholding(symbol: str, db: Session = Depends(get_db)):
    c = _company(db, symbol)
    return [dict(period_end=str(r.period_end), promoter=r.promoter_pct, fii=r.fii_pct, dii=r.dii_pct,
                 public=r.public_pct, pledged=r.pledged_pct)
            for r in db.scalars(select(m.Shareholding).where(m.Shareholding.company_id == c.id).order_by(m.Shareholding.period_end))]

@app.get("/api/v1/companies/{symbol}/earnings-quality")
def earnings_quality(symbol: str, db: Session = Depends(get_db)):
    c = _company(db, symbol)
    return assess(point_in_time_results(db, c.id, None)) | {"symbol": c.symbol,
        "disclaimer": "Rule-based flag for further investigation; not an investment recommendation."}

@app.get("/api/v1/companies/{symbol}/guidance")
def guidance(symbol: str, db: Session = Depends(get_db)):
    c = _company(db, symbol); out = []
    for g in db.scalars(select(m.ManagementGuidance).where(m.ManagementGuidance.company_id == c.id)):
        a = db.scalar(select(m.GuidanceActual).where(m.GuidanceActual.guidance_id == g.id))
        item = dict(metric=g.metric, period=g.period, low=g.guidance_low, high=g.guidance_high, unit=g.unit,
                    guidance_date=str(g.guidance_date), source=g.source_note)
        if a: item |= {"actual": a.actual_value} | deviation(g.guidance_low, g.guidance_high, a.actual_value)
        out.append(item)
    return out

@app.get("/api/v1/screener/fields")
def screener_fields():
    return [{"key": k, "label": v[1], "category": v[2]} for k, v in FIELDS.items()] + \
           [{"key": "sector", "label": "Sector", "category": "Company"}]

@app.post("/api/v1/screener/query")
def screener_query(query: dict, db: Session = Depends(get_db)):
    try:
        rows = run_screen(db, query)
    except QueryError as e:
        raise HTTPException(422, str(e))
    return {"count": len(rows), "results": rows}

class SaveReq(BaseModel):
    name: str
    query: dict

@app.post("/api/v1/screener/saved", status_code=201)
def save_screen(req: SaveReq, db: Session = Depends(get_db)):
    try: run_screen(db, req.query)
    except QueryError as e: raise HTTPException(422, str(e))
    s = m.SavedScreen(name=req.name, query_json=json.dumps(req.query)); db.add(s); db.commit()
    return {"id": s.id, "name": s.name}

@app.get("/api/v1/screener/saved")
def list_saved(db: Session = Depends(get_db)):
    return [dict(id=s.id, name=s.name, query=json.loads(s.query_json)) for s in db.scalars(select(m.SavedScreen))]

@app.get("/api/v1/market/overview")
def market_overview(db: Session = Depends(get_db)):
    closes, vols = load_prices(db)
    names = {c.id: (c.symbol, c.company_name) for c in db.scalars(select(m.Company))}
    chg = (closes.iloc[-1] / closes.iloc[-2] - 1) * 100
    top, bot = chg.sort_values(ascending=False), chg.sort_values()
    fmt = lambda s: [dict(symbol=names[i][0], name=names[i][1], change_pct=round(float(v), 2),
                          price=float(closes[i].iloc[-1])) for i, v in s.head(5).items()]
    above50 = float((closes.iloc[-1] > closes.rolling(50).mean().iloc[-1]).mean() * 100)
    ew = (closes / closes.iloc[0]).mean(axis=1) * 100
    return {"as_of": str(closes.index[-1]), "data_mode": "Historical / end-of-day (synthetic)",
            "advancers": int((chg > 0).sum()), "decliners": int((chg < 0).sum()), "pct_above_50dma": round(above50, 1),
            "gainers": fmt(top), "losers": fmt(bot),
            "index": [{"date": str(d), "value": round(float(v), 2)} for d, v in ew.iloc[-250:].items()]}

@app.get("/api/v1/sectors/rankings")
def sector_rankings(db: Session = Depends(get_db)):
    closes, vols = load_prices(db)
    comp_sector = pd.Series({c.id: c.sector.name for c in db.scalars(select(m.Company))})
    g = {}
    for cid in closes.columns:
        res = point_in_time_results(db, int(cid), None)
        if len(res) >= 2 and res[-2].pat and res[-2].pat > 0:
            g[cid] = (res[-1].pat / res[-2].pat - 1) * 100
    df = sector_scores(closes, vols, comp_sector.loc[closes.columns], pd.Series(g))
    return {"as_of": str(closes.index[-1]),
            "note": "Relative-strength/participation rotation from price, volume, breadth and earnings; not fund-flow evidence.",
            "sectors": [{"sector": s, **{k: (None if pd.isna(v) else (v.item() if hasattr(v, 'item') else v)) for k, v in r.items()}}
                        for s, r in df.iterrows()]}

if FRONTEND.exists():
    @app.get("/", include_in_schema=False)
    def index(): return FileResponse(FRONTEND / "index.html")
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
