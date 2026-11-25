"""Screener: JSON query -> validated -> parameterised SQLAlchemy query. Users never write SQL."""
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from app.core.models import RatioSnapshot, Company, Sector

FIELDS = {  # field key -> (column, label, category)
    "market_cap": (RatioSnapshot.market_cap, "Market Cap (Rs Cr)", "Valuation"),
    "price": (RatioSnapshot.price, "Price (Rs)", "Price"),
    "pe": (RatioSnapshot.pe, "P/E", "Valuation"),
    "pb": (RatioSnapshot.pb, "P/B", "Valuation"),
    "peg": (RatioSnapshot.peg, "PEG", "Valuation"),
    "ev_ebitda": (RatioSnapshot.ev_ebitda, "EV/EBITDA", "Valuation"),
    "roce": (RatioSnapshot.roce, "ROCE %", "Profitability"),
    "roe": (RatioSnapshot.roe, "ROE %", "Profitability"),
    "debt_equity": (RatioSnapshot.debt_equity, "Debt/Equity", "Debt"),
    "interest_coverage": (RatioSnapshot.interest_coverage, "Interest Coverage", "Debt"),
    "current_ratio": (RatioSnapshot.current_ratio, "Current Ratio", "Debt"),
    "ebitda_margin": (RatioSnapshot.ebitda_margin, "EBITDA Margin %", "Margins"),
    "pat_margin": (RatioSnapshot.pat_margin, "PAT Margin %", "Margins"),
    "cfo_pat": (RatioSnapshot.cfo_pat, "CFO/PAT", "Cash flow"),
    "sales_growth_1y": (RatioSnapshot.sales_growth_1y, "Sales Growth 1Y %", "Growth"),
    "sales_growth_3y": (RatioSnapshot.sales_growth_3y, "Sales CAGR 3Y %", "Growth"),
    "profit_growth_1y": (RatioSnapshot.profit_growth_1y, "Profit Growth 1Y %", "Growth"),
    "profit_growth_3y": (RatioSnapshot.profit_growth_3y, "Profit CAGR 3Y %", "Growth"),
    "promoter_holding": (RatioSnapshot.promoter_holding, "Promoter Holding %", "Ownership"),
    "pledged_pct": (RatioSnapshot.pledged_pct, "Pledged %", "Ownership"),
    "fii_holding": (RatioSnapshot.fii_holding, "FII Holding %", "Ownership"),
    "dii_holding": (RatioSnapshot.dii_holding, "DII Holding %", "Ownership"),
    "ret_1m": (RatioSnapshot.ret_1m, "Return 1M %", "Price"),
    "ret_3m": (RatioSnapshot.ret_3m, "Return 3M %", "Price"),
    "ret_6m": (RatioSnapshot.ret_6m, "Return 6M %", "Price"),
    "rsi_14": (RatioSnapshot.rsi_14, "RSI (14)", "Technical"),
    "pct_from_52w_high": (RatioSnapshot.pct_from_52w_high, "% From 52W High", "Technical"),
    "volume_ratio": (RatioSnapshot.volume_ratio, "Volume Ratio (20d/100d)", "Volume"),
}
OPS = {">", "<", ">=", "<=", "==", "!=", "between"}
MAX_LIMIT = 500

class QueryError(ValueError):
    pass

def _cond(col, op, value):
    if op == ">": return col > value
    if op == "<": return col < value
    if op == ">=": return col >= value
    if op == "<=": return col <= value
    if op == "==": return col == value
    if op == "!=": return col != value
    lo, hi = value
    return and_(col >= lo, col <= hi)

def validate_query(q: dict) -> dict:
    if not isinstance(q, dict):
        raise QueryError("query must be an object")
    filters = q.get("filters", [])
    if not isinstance(filters, list):
        raise QueryError("filters must be a list")
    logic = str(q.get("logic", "AND")).upper()
    if logic not in ("AND", "OR"):
        raise QueryError("logic must be AND or OR")
    for f in filters:
        if f.get("field") not in FIELDS and f.get("field") != "sector":
            raise QueryError(f"unknown field: {f.get('field')!r}")
        if f.get("operator") not in OPS and f.get("field") != "sector":
            raise QueryError(f"unsupported operator: {f.get('operator')!r}")
        v = f.get("value")
        if f.get("field") == "sector":
            if not isinstance(v, str):
                raise QueryError("sector value must be a string")
        elif f["operator"] == "between":
            if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)):
                raise QueryError("between needs [low, high]")
        elif isinstance(v, bool) or not isinstance(v, (int, float)):
            raise QueryError(f"value for {f['field']} must be numeric")
    sort = q.get("sort") or {}
    if sort:
        if sort.get("field") not in FIELDS:
            raise QueryError("unknown sort field")
        if str(sort.get("direction", "DESC")).upper() not in ("ASC", "DESC"):
            raise QueryError("sort direction must be ASC or DESC")
    limit = q.get("limit", 100)
    if not isinstance(limit, int) or limit < 1 or limit > MAX_LIMIT:
        raise QueryError(f"limit must be 1..{MAX_LIMIT}")
    return {"filters": filters, "logic": logic, "sort": sort, "limit": limit}

def run_screen(db: Session, q: dict) -> list[dict]:
    q = validate_query(q)
    conds = []
    for f in q["filters"]:
        if f["field"] == "sector":
            conds.append(Sector.name == f["value"])
        else:
            col = FIELDS[f["field"]][0]
            conds.append(and_(col.isnot(None), _cond(col, f["operator"], f["value"])))
    stmt = (select(Company.id, Company.symbol, Company.company_name, Sector.name.label("sector"), RatioSnapshot)
            .join(RatioSnapshot, RatioSnapshot.company_id == Company.id)
            .join(Sector, Sector.id == Company.sector_id))
    if conds:
        stmt = stmt.where(and_(*conds) if q["logic"] == "AND" else or_(*conds))
    if q["sort"]:
        col = FIELDS[q["sort"]["field"]][0]
        d = str(q["sort"].get("direction", "DESC")).upper()
        stmt = stmt.where(col.isnot(None)).order_by(col.desc() if d == "DESC" else col.asc())
    else:
        stmt = stmt.order_by(RatioSnapshot.market_cap.desc())
    stmt = stmt.limit(q["limit"])
    rows = []
    for r in db.execute(stmt):
        snap = r.RatioSnapshot
        d = {"company_id": r.id, "symbol": r.symbol, "company_name": r.company_name, "sector": r.sector}
        for k, (col, _, _) in FIELDS.items():
            v = getattr(snap, col.key)
            d[k] = None if v is None else round(v, 2)
        rows.append(d)
    return rows
