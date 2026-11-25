"""Synthetic dataset generator. ALL companies, numbers and prices are FICTIONAL test fixtures
(blueprint: 'first version may use historical data and simulated test fixtures')."""
import json, random
from datetime import date, timedelta
import numpy as np
import pandas as pd
from app.core.database import Base, engine, SessionLocal
from app.core import models as m

SECTORS = {
    "IT Services": ["Aurora Infotech", "Nimbus Digital", "Quanta Systems", "Veritas Tech", "Zenith Cloud"],
    "Pharma": ["Medora Labs", "Helix Pharma", "Sanora Biotech", "Curevita Drugs", "Alpine Remedies"],
    "Auto": ["Torque Motors", "Velo Auto", "Axle Components", "Rover Mobility", "Ignis Vehicles"],
    "FMCG": ["Pure Harvest", "Daily Basket", "Kiran Foods", "Lumina Care", "Savora Brands"],
    "Capital Goods": ["Granite Forge", "Kestrel Dynamics", "Orion Engineering", "Vertex Machines", "Ironwood Infra"],
    "Chemicals": ["Calyx Chemicals", "Polaris Specialty", "Elemental Dyes", "Argon Materials", "Synthra Labs"],
    "Energy": ["Solaris Power", "Windmark Energy", "Petra Fuels", "Gridline Utilities", "Hydron Renewables"],
    "Consumer Durables": ["Cool Breeze Appliances", "Brightline Electric", "Homestead Durables", "Nova Wires", "Spectra Home"],
}
SECTOR_DRIFT = {"IT Services": 0.0007, "Pharma": 0.0004, "Auto": 0.0009, "FMCG": 0.0002,
                "Capital Goods": 0.0010, "Chemicals": -0.0001, "Energy": 0.0006, "Consumer Durables": 0.0003}
RECENT_SHIFT = {"IT Services": -0.0006, "Pharma": 0.0007, "Auto": 0.0003, "FMCG": -0.0003,
                "Capital Goods": 0.0004, "Chemicals": 0.0008, "Energy": -0.0008, "Consumer Durables": 0.0002}
ANOMALY_COUNT = 4
LAST_FY = 2026
N_DAYS = 520
END_DATE = date(2026, 11, 20)

def make_symbol(name: str, used: set) -> str:
    base = "".join(c for c in name.upper() if c.isalpha())[:8]
    s, i = base, 1
    while s in used:
        i += 1; s = f"{base[:7]}{i}"
    used.add(s); return s

def generate(seed: int = 42, labels_path: str | None = None):
    rng = np.random.default_rng(seed); random.seed(seed)
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    db = SessionLocal()
    sec_ids = {}
    for name in SECTORS:
        s = m.Sector(name=name); db.add(s); db.flush(); sec_ids[name] = s.id
    days = pd.bdate_range(end=END_DATE, periods=N_DAYS)
    companies, used, idx = [], set(), 0
    for sec, names in SECTORS.items():
        for nm in names:
            idx += 1
            c = m.Company(company_name=f"{nm} Ltd (Fictional)", symbol=make_symbol(nm, used), exchange="NSE",
                          isin=f"INE{900 + idx:03d}A01{idx:03d}", sector_id=sec_ids[sec])
            db.add(c); db.flush(); companies.append((c, sec))
    anomaly_ids = set(rng.choice([c.id for c, _ in companies], size=ANOMALY_COUNT, replace=False).tolist())
    for c, sec in companies:
        rev = float(rng.uniform(800, 25000))
        margin = float(rng.uniform(0.09, 0.28)); base_g = float(rng.uniform(0.04, 0.22))
        equity = rev * float(rng.uniform(0.35, 0.8)); debt = equity * float(rng.uniform(0.0, 1.1))
        shares = float(rng.uniform(40, 600))
        prev_rec = rev * 0.16
        c.shares_outstanding_cr = round(shares, 2)
        rows = []
        for fy in range(2021, LAST_FY + 1):
            g = base_g + float(rng.normal(0, 0.05))
            rev = rev * (1 + g)
            ebitda = rev * (margin + float(rng.normal(0, 0.012)))
            dep = rev * float(rng.uniform(0.025, 0.05)); interest = debt * 0.085
            pbt = ebitda - dep - interest; tax = max(pbt, 0) * 0.25; pat = pbt - tax
            rec = rev * float(rng.uniform(0.13, 0.19)); cfo = pat * float(rng.uniform(0.8, 1.25)) + dep * 0.5
            if c.id in anomaly_ids and fy == LAST_FY:   # injected anomaly (ground-truth label)
                rev = rows[-1]["revenue"] * 1.18
                pat = rows[-1]["pat"] * 1.45                       # inflated profit growth
                pbt = pat / 0.75; tax = pbt - pat; ebitda = pbt + dep + interest   # keeps P&L identities exact
                rec = rows[-1]["receivables"] * 1.8; cfo = pat * 0.25
            equity = equity + pat * 0.7
            debt = max(debt * float(rng.uniform(0.9, 1.05)), 0)
            rows.append(dict(fy=fy, revenue=rev, ebitda=ebitda, dep=dep, interest=interest, pbt=pbt, tax=tax,
                             pat=pat, equity=equity, debt=debt, receivables=rec, cfo=cfo))
        for r in rows:
            db.add(m.FinancialResult(
                company_id=c.id, fiscal_year=r["fy"], period_end=date(r["fy"], 3, 31),
                filing_date=date(r["fy"], 5, 25) + timedelta(days=int(rng.integers(0, 12))),
                revenue=round(r["revenue"], 2), expenses=round(r["revenue"] - r["ebitda"], 2),
                ebitda=round(r["ebitda"], 2), depreciation=round(r["dep"], 2), interest=round(r["interest"], 2),
                pbt=round(r["pbt"], 2), tax=round(r["tax"], 2), pat=round(r["pat"], 2),
                eps=round(r["pat"] / shares, 2), total_equity=round(r["equity"], 2), total_debt=round(r["debt"], 2),
                cash=round(r["equity"] * 0.12, 2), current_assets=round(r["revenue"] * 0.34, 2),
                current_liabilities=round(r["revenue"] * float(rng.uniform(0.18, 0.3)), 2),
                receivables=round(r["receivables"], 2), cfo=round(r["cfo"], 2)))
        # prices: random walk, sector drift, regime shift in last ~90 days; scaled to a target P/E at the end
        last_eps = rows[-1]["pat"] / shares
        target = max(last_eps, 1) * float(rng.uniform(14, 45))
        drift = np.full(N_DAYS, SECTOR_DRIFT[sec]); drift[-90:] += RECENT_SHIFT[sec]
        rets = drift + rng.normal(0, 0.014, N_DAYS)
        path = np.cumprod(1 + rets); path = path / path[-1] * target
        base_vol = float(rng.uniform(2e5, 4e6))
        vols = (base_vol * np.exp(rng.normal(0, 0.35, N_DAYS))).astype(int)
        vols[-20:] = (vols[-20:] * (1 + (RECENT_SHIFT[sec] * 600))).clip(1000).astype(int)
        for d, p, v in zip(days, path, vols):
            db.add(m.DailyPrice(company_id=c.id, trading_date=d.date(), close=round(float(p), 2), volume=int(v)))
        prom = float(rng.uniform(20, 75)); fii = float(rng.uniform(5, 25)); dii = float(rng.uniform(5, 20))
        for per, dp in ((date(2026, 3, 31), -0.8), (date(2026, 9, 30), 0.0)):
            db.add(m.Shareholding(company_id=c.id, period_end=per, promoter_pct=round(prom + dp, 2),
                                  fii_pct=round(fii, 2), dii_pct=round(dii, 2),
                                  public_pct=round(100 - prom - dp - fii - dii, 2),
                                  pledged_pct=round(float(rng.uniform(0, 18)), 2)))
        if c.id <= 14:   # management guidance sample for the tracker
            g_actual = (rows[-1]["revenue"] / rows[-2]["revenue"] - 1) * 100
            centre = g_actual + float(rng.uniform(-6, 6)); half = float(rng.uniform(2, 4))
            gd = m.ManagementGuidance(company_id=c.id, metric="Revenue growth", guidance_low=round(centre - half, 1),
                                      guidance_high=round(centre + half, 1), unit="%", period=f"FY{LAST_FY}",
                                      guidance_date=date(2025, 5, 30), source_note="Synthetic concall extract")
            db.add(gd); db.flush()
            db.add(m.GuidanceActual(guidance_id=gd.id, actual_value=round(g_actual, 1), reported_date=date(2026, 5, 30)))
    for ds, st, mode, note in [("Historical prices", "Verified", "Historical", "Synthetic EOD to 2026-11-20"),
                               ("Financial results", "Verified", "Historical", "FY2021-FY2026 annual"),
                               ("Shareholding", "Verified", "Historical", "Latest quarter 2026-09-30"),
                               ("Live market feed", "Not licensed", "Live", "Planned: licensed vendor")]:
        db.add(m.DataQualityLog(dataset=ds, status=st, mode=mode, last_updated=END_DATE, note=note))
    db.commit()
    labels = sorted(int(x) for x in anomaly_ids)
    if labels_path:
        sym = {c.id: c.symbol for c, _ in companies}
        json.dump({"injected_anomaly_company_ids": labels, "symbols": [sym[i] for i in labels]},
                  open(labels_path, "w"), indent=2)
    db.close()
    return labels

if __name__ == "__main__":
    from app.services import refresh_ratios
    ids = generate(labels_path="../data/samples/anomaly_labels.json")
    with SessionLocal() as s:
        print("snapshots:", refresh_ratios(s))
    print("anomaly company ids:", ids)
