"""Sector Radar: SMS = .25R1 + .20R3 + .10R6 + .15B + .15E + .10V + .05RS (each component 0-100)."""
import numpy as np
import pandas as pd

WEIGHTS = {"r1": 0.25, "r3": 0.20, "r6": 0.10, "breadth": 0.15, "earnings": 0.15, "volume": 0.10, "rs": 0.05}

def minmax_0_100(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or hi == lo:
        return pd.Series(50.0, index=s.index)
    return (s - lo) / (hi - lo) * 100

def classify_phase(rs_now: float, rs_prev: float) -> str:
    """Rules-based phase from relative-strength level and direction (price-based, not fund-flow)."""
    rising = rs_now > rs_prev
    if rs_now > 0 and rising: return "Leading"
    if rs_now <= 0 and rising: return "Improving"
    if rs_now > 0 and not rising: return "Weakening"
    return "Lagging"

def _rel_ret(closes: pd.DataFrame, comp_sector: pd.Series, n: int, offset: int = 0) -> pd.Series:
    end = closes.iloc[: len(closes) - offset] if offset else closes
    r = end.iloc[-1] / end.iloc[-1 - n] - 1
    bench = r.mean()
    sec = r.groupby(comp_sector).mean()
    return (sec - bench) * 100

def sector_scores(closes: pd.DataFrame, volumes: pd.DataFrame, comp_sector: pd.Series,
                  pat_growth: pd.Series) -> pd.DataFrame:
    """closes/volumes: date x company_id. comp_sector, pat_growth: indexed by company_id."""
    ret = lambda n: (closes.iloc[-1] / closes.iloc[-1 - n] - 1) * 100
    g = lambda s: s.groupby(comp_sector).mean()
    r1, r3, r6 = g(ret(21)), g(ret(63)), g(ret(126))
    above50 = (closes.iloc[-1] > closes.rolling(50).mean().iloc[-1]).astype(float) * 100
    breadth = g(above50)
    earn = pat_growth.clip(-50, 100).groupby(comp_sector).median()
    vol = g(volumes.iloc[-20:].mean() / volumes.iloc[-100:].mean())
    rs_now = _rel_ret(closes, comp_sector, 63)
    rs_prev = _rel_ret(closes, comp_sector, 63, offset=21)
    comp = pd.DataFrame({"r1": r1, "r3": r3, "r6": r6, "breadth": breadth, "earnings": earn,
                         "volume": vol, "rs": rs_now}).dropna()
    norm = comp.apply(minmax_0_100)
    score = sum(norm[k] * w for k, w in WEIGHTS.items())
    out = comp.round(2).copy()
    out["score"] = score.round(1)
    out["rs_prev"] = rs_prev.reindex(out.index).round(2)
    out["phase"] = [classify_phase(a, b) for a, b in zip(out["rs"], out["rs_prev"])]
    out["rank"] = out["score"].rank(ascending=False, method="min").astype(int)
    out["companies"] = comp_sector.groupby(comp_sector).size().reindex(out.index)
    return out.sort_values("rank")
