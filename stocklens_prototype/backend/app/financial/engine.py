"""Deterministic financial formula engine. No AI is used for any calculation.
Functions return None (never raise / never divide by zero) when inputs are missing or meaningless."""
from typing import Optional, Sequence

Num = Optional[float]

def safe_divide(n: Num, d: Num) -> Num:
    if n is None or d is None or d == 0:
        return None
    return n / d

def pct(x: Num) -> Num:
    return None if x is None else x * 100

def growth(current: Num, previous: Num) -> Num:
    """YoY growth %. Undefined for a zero or negative base (sign change makes % meaningless)."""
    if current is None or previous is None or previous <= 0:
        return None
    return (current / previous - 1) * 100

def cagr(end: Num, start: Num, years: int) -> Num:
    if end is None or start is None or start <= 0 or end <= 0 or years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100

def avg(a: Num, b: Num) -> Num:
    if a is None or b is None:
        return None
    return (a + b) / 2

def ebitda_margin(ebitda, revenue): return pct(safe_divide(ebitda, revenue))
def pat_margin(pat, revenue):       return pct(safe_divide(pat, revenue))
def roe(pat, equity_now, equity_prev):
    return pct(safe_divide(pat, avg(equity_now, equity_prev)))
def roce(ebit, ce_now, ce_prev):
    return pct(safe_divide(ebit, avg(ce_now, ce_prev)))
def capital_employed(equity: Num, debt: Num) -> Num:
    return None if equity is None or debt is None else equity + debt
def debt_equity(debt, equity):
    return None if equity is None or equity <= 0 else safe_divide(debt, equity)
def interest_coverage(ebit, interest):
    return safe_divide(ebit, interest) if interest and interest > 0 else None
def current_ratio(ca, cl): return safe_divide(ca, cl)
def cfo_to_pat(cfo, pat):
    return safe_divide(cfo, pat) if pat is not None and pat > 0 else None
def pe_ratio(price, eps):
    return safe_divide(price, eps) if eps is not None and eps > 0 else None
def pb_ratio(mcap, equity):
    return safe_divide(mcap, equity) if equity is not None and equity > 0 else None
def ev_ebitda(mcap, debt, cash, ebitda):
    if mcap is None or debt is None or cash is None or ebitda is None or ebitda <= 0:
        return None
    return (mcap + debt - cash) / ebitda
def peg_ratio(pe, eps_growth_pct):
    return safe_divide(pe, eps_growth_pct) if pe is not None and eps_growth_pct and eps_growth_pct > 0 else None

def ttm(last_four_quarters: Sequence[Num]) -> Num:
    """TTM = sum of the latest FOUR reported quarters (never latest quarter x 4)."""
    if len(last_four_quarters) != 4 or any(q is None for q in last_four_quarters):
        return None
    return float(sum(last_four_quarters))

def compute_company_ratios(results: list, shareholding, price: Num, mcap: Num) -> dict:
    """results: FinancialResult-like rows sorted ascending by fiscal year (already point-in-time filtered)."""
    out = {}
    if not results:
        return out
    cur = results[-1]
    prev = results[-2] if len(results) >= 2 else None
    y3 = results[-4] if len(results) >= 4 else None
    ebit = None if cur.pbt is None or cur.interest is None else cur.pbt + cur.interest
    out["ebitda_margin"] = ebitda_margin(cur.ebitda, cur.revenue)
    out["pat_margin"] = pat_margin(cur.pat, cur.revenue)
    out["debt_equity"] = debt_equity(cur.total_debt, cur.total_equity)
    out["interest_coverage"] = interest_coverage(ebit, cur.interest)
    out["current_ratio"] = current_ratio(cur.current_assets, cur.current_liabilities)
    out["cfo_pat"] = cfo_to_pat(cur.cfo, cur.pat)
    eps_g = None
    if prev:
        out["roe"] = roe(cur.pat, cur.total_equity, prev.total_equity)
        out["roce"] = roce(ebit, capital_employed(cur.total_equity, cur.total_debt),
                           capital_employed(prev.total_equity, prev.total_debt))
        out["sales_growth_1y"] = growth(cur.revenue, prev.revenue)
        out["profit_growth_1y"] = growth(cur.pat, prev.pat)
        eps_g = growth(cur.eps, prev.eps)
    if y3:
        out["sales_growth_3y"] = cagr(cur.revenue, y3.revenue, 3)
        out["profit_growth_3y"] = cagr(cur.pat, y3.pat, 3)
    out["pe"] = pe_ratio(price, cur.eps)
    out["pb"] = pb_ratio(mcap, cur.total_equity)
    out["peg"] = peg_ratio(out["pe"], eps_g)
    out["ev_ebitda"] = ev_ebitda(mcap, cur.total_debt, cur.cash, cur.ebitda)
    if shareholding is not None:
        out["promoter_holding"] = shareholding.promoter_pct
        out["pledged_pct"] = shareholding.pledged_pct
        out["fii_holding"] = shareholding.fii_pct
        out["dii_holding"] = shareholding.dii_pct
    return out
