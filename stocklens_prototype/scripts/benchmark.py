"""Accuracy + performance evaluation. Writes docs/results.json. Run from backend/ after seeding."""
import os, sys, json, time, random, platform, statistics as st
os.environ.setdefault("DATABASE_URL", "sqlite:///./stocklens.db")
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from datetime import date
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.core.database import SessionLocal, Base
from app.core import models as m
from app.main import app
from app.screener.engine import run_screen, FIELDS
from app.services import refresh_ratios
from app.market.indicators import rsi

R = {"environment": {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count(),
                     "db": "SQLite (in-process)", "note": "In-process TestClient; no network latency; synthetic data"}}
db = SessionLocal()
def pct(a, p): return float(np.percentile(a, p))

# ---- A1 formula accuracy: independent pandas oracle vs production engine ----
fr = pd.read_sql(select(m.FinancialResult), db.bind)
snaps = pd.read_sql(select(m.RatioSnapshot), db.bind).set_index("company_id")
sh = pd.read_sql(select(m.Shareholding), db.bind)
checks = total = 0; maxerr = 0
for cid, g in fr.groupby("company_id"):
    g = g.sort_values("fiscal_year"); c, p, y3 = g.iloc[-1], g.iloc[-2], g.iloc[-4]
    s = snaps.loc[cid]; ebit = c.pbt + c.interest
    exp = {"ebitda_margin": c.ebitda / c.revenue * 100, "pat_margin": c.pat / c.revenue * 100,
           "roe": c.pat / ((c.total_equity + p.total_equity) / 2) * 100,
           "roce": ebit / (((c.total_equity + c.total_debt) + (p.total_equity + p.total_debt)) / 2) * 100,
           "debt_equity": c.total_debt / c.total_equity, "interest_coverage": ebit / c.interest,
           "current_ratio": c.current_assets / c.current_liabilities, "cfo_pat": c.cfo / c.pat,
           "sales_growth_1y": (c.revenue / p.revenue - 1) * 100, "profit_growth_1y": (c.pat / p.pat - 1) * 100,
           "sales_growth_3y": ((c.revenue / y3.revenue) ** (1 / 3) - 1) * 100, "profit_growth_3y": ((c.pat / y3.pat) ** (1 / 3) - 1) * 100,
           "pe": s.price / c.eps, "market_cap": s.price * db.get(m.Company, int(cid)).shares_outstanding_cr}
    for k, v in exp.items():
        total += 1; err = abs(s[k] - v) / max(abs(v), 1e-9); maxerr = max(maxerr, err); checks += err < 1e-6
R["formula_accuracy"] = {"values_checked": total, "values_matching": int(checks), "pct": round(checks / total * 100, 2), "max_rel_error": maxerr,
                         "ratios": 14, "companies": int(fr.company_id.nunique())}

# ---- A2 screener precision/recall vs oracle on random queries ----
df = snaps.join(pd.read_sql(select(m.Company.id, m.Company.sector_id), db.bind).set_index("id"))
num = [k for k in FIELDS]; rng = random.Random(11); tp = fp = fn = 0; nq = 300; exact = 0
for _ in range(nq):
    fl, mask_parts = [], []
    for _ in range(rng.randint(1, 4)):
        k = rng.choice(num); col = df[k].dropna(); op = rng.choice([">", "<", ">=", "<=", "between"])
        if op == "between":
            lo, hi = sorted(np.percentile(col, [rng.randint(5, 45), rng.randint(55, 95)])); val = [float(lo), float(hi)]
            mask = (df[k] >= val[0]) & (df[k] <= val[1])
        else:
            val = float(np.percentile(col, rng.randint(10, 90)))
            mask = {">": df[k] > val, "<": df[k] < val, ">=": df[k] >= val, "<=": df[k] <= val}[op]
        fl.append({"field": k, "operator": op, "value": val}); mask_parts.append(mask.fillna(False))
    logic = rng.choice(["AND", "OR"])
    mask = mask_parts[0]
    for mp in mask_parts[1:]: mask = (mask & mp) if logic == "AND" else (mask | mp)
    exp = set(df[mask].index); got = {r["company_id"] for r in run_screen(db, {"filters": fl, "logic": logic, "limit": 500})}
    tp += len(exp & got); fp += len(got - exp); fn += len(exp - got); exact += exp == got
R["screener_accuracy"] = {"random_queries": nq, "exact_match": exact, "precision": round(tp / max(tp + fp, 1), 4),
                          "recall": round(tp / max(tp + fn, 1), 4), "true_pos": tp, "false_pos": fp, "false_neg": fn}

# ---- A3 RSI vs reference Wilder loop ----
px = pd.read_sql(select(m.DailyPrice).where(m.DailyPrice.company_id <= 10), db.bind)
errs = []
for cid, g in px.groupby("company_id"):
    c = g.sort_values("trading_date").close.values; n = 14; gg = ll = 0.0
    for i in range(1, n + 1): d = c[i] - c[i - 1]; gg += max(d, 0); ll += max(-d, 0)
    gg /= n; ll /= n
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]; gg = (gg * 13 + max(d, 0)) / 14; ll = (ll * 13 + max(-d, 0)) / 14
    ref = 100 - 100 / (1 + gg / ll); errs.append(abs(rsi(pd.Series(c)).iloc[-1] - ref))
R["rsi_accuracy"] = {"series": len(errs), "max_abs_error_rsi_points": round(max(errs), 4), "mean_abs_error": round(float(np.mean(errs)), 4)}

# ---- A4 earnings-quality rule detection on labelled synthetic set ----
labels = set(json.load(open("../data/samples/anomaly_labels.json"))["symbols"])
client = TestClient(app); syms = [c["symbol"] for c in client.get("/api/v1/companies?limit=100").json()]
flag = {s for s in syms if client.get(f"/api/v1/companies/{s}/earnings-quality").json()["status"] == "requires_investigation"}
tp, fp, fn = len(flag & labels), len(flag - labels), len(labels - flag)
R["earnings_quality"] = {"companies": len(syms), "injected": len(labels), "tp": tp, "fp": fp, "fn": fn,
                         "precision": round(tp / max(tp + fp, 1), 3), "recall": round(tp / max(tp + fn, 1), 3),
                         "caveat": "Labelled synthetic anomalies validate rule logic only, not real-world predictive accuracy."}

# ---- P1 API latency (in-process) ----
eps = ["/api/v1/health", "/api/v1/companies?q=a", f"/api/v1/companies/{syms[0]}/overview", f"/api/v1/companies/{syms[0]}/financials",
       f"/api/v1/companies/{syms[0]}/prices?days=250", f"/api/v1/companies/{syms[0]}/earnings-quality", "/api/v1/market/overview", "/api/v1/sectors/rankings"]
lat = []
for e in eps:
    t = []
    for _ in range(40):
        a = time.perf_counter(); r = client.get(e); t.append((time.perf_counter() - a) * 1000); assert r.status_code == 200
    lat.append({"endpoint": e.split("?")[0].replace(syms[0], "{symbol}"), "p50_ms": round(pct(t, 50), 1), "p95_ms": round(pct(t, 95), 1), "max_ms": round(max(t), 1)})
body = {"filters": [{"field": "roce", "operator": ">", "value": 15}, {"field": "debt_equity", "operator": "<", "value": 0.8}], "sort": {"field": "roce", "direction": "DESC"}, "limit": 100}
t = []
for _ in range(40):
    a = time.perf_counter(); client.post("/api/v1/screener/query", json=body); t.append((time.perf_counter() - a) * 1000)
lat.append({"endpoint": "POST /api/v1/screener/query", "p50_ms": round(pct(t, 50), 1), "p95_ms": round(pct(t, 95), 1), "max_ms": round(max(t), 1)})
R["api_latency"] = lat

# ---- P2 screener scaling on synthetic snapshot tables of N companies ----
scal = []
for N in (40, 1000, 5000, 20000):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}); Base.metadata.create_all(eng); S = sessionmaker(bind=eng)()
    g = np.random.default_rng(3); S.add(m.Sector(id=1, name="X"))
    S.bulk_save_objects([m.Company(id=i, company_name=f"C{i}", symbol=f"S{i}", sector_id=1) for i in range(1, N + 1)])
    cols = [k for k in FIELDS]
    S.bulk_save_objects([m.RatioSnapshot(company_id=i, **{k: float(v) for k, v in zip(cols, g.normal(20, 10, len(cols)))}) for i in range(1, N + 1)]); S.commit()
    t = []
    for _ in range(30):
        a = time.perf_counter(); run_screen(S, {"filters": [{"field": "roce", "operator": ">", "value": 18}, {"field": "pe", "operator": "<", "value": 25}, {"field": "debt_equity", "operator": "<", "value": 30}], "sort": {"field": "roce", "direction": "DESC"}, "limit": 100}); t.append((time.perf_counter() - a) * 1000)
    scal.append({"companies": N, "p50_ms": round(pct(t, 50), 1), "p95_ms": round(pct(t, 95), 1)})
R["screener_scaling"] = scal

# ---- P3 batch jobs ----
a = time.perf_counter(); n = refresh_ratios(db); dt = time.perf_counter() - a
R["ratio_refresh"] = {"companies": n, "price_rows": int(db.query(m.DailyPrice).count()), "seconds": round(dt, 2), "companies_per_sec": round(n / dt, 1)}
a = time.perf_counter(); client.get("/api/v1/sectors/rankings"); R["sector_ranking_ms"] = round((time.perf_counter() - a) * 1000, 1)

# ---- junit summary ----
import xml.etree.ElementTree as ET
root = ET.parse("/tmp/junit.xml").getroot(); suite = root if root.tag == "testsuite" else root[0]
cases = []
for tc in suite.iter("testcase"):
    cases.append({"id": tc.get("name"), "file": tc.get("classname").split(".")[-1], "passed": tc.find("failure") is None and tc.find("error") is None})
R["tests"] = {"total": len(cases), "passed": sum(c["passed"] for c in cases), "duration_s": float(suite.get("time")), "cases": cases}
R["data"] = {"companies": db.query(m.Company).count(), "sectors": db.query(m.Sector).count(), "financial_rows": db.query(m.FinancialResult).count(),
             "price_rows": db.query(m.DailyPrice).count(), "screener_fields": len(FIELDS) + 1}
json.dump(R, open("../docs/results.json", "w"), indent=2)
print(json.dumps({k: v for k, v in R.items() if k != "tests"}, indent=1)[:4500]); print("tests", R["tests"]["passed"], "/", R["tests"]["total"])
