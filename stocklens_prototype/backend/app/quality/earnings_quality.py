"""Transparent rule-based earnings-quality checks (v1). Output is a flag for investigation, not advice."""
from app.financial.engine import growth, cfo_to_pat

def assess(results: list) -> dict:
    if len(results) < 2:
        return {"status": "insufficient_data", "flags": [], "metrics": {}}
    cur, prev = results[-1], results[-2]
    rev_g = growth(cur.revenue, prev.revenue)
    pat_g = growth(cur.pat, prev.pat)
    rec_g = growth(cur.receivables, prev.receivables)
    conv = cfo_to_pat(cur.cfo, cur.pat)
    flags = []
    if conv is not None and conv < 0.6:
        flags.append(f"Low cash conversion: CFO/PAT = {conv:.2f}x (< 0.60x)")
    if rec_g is not None and rev_g is not None and rec_g - rev_g > 20:
        flags.append(f"Receivables grew {rec_g:.0f}% vs revenue {rev_g:.0f}% (gap > 20 pts)")
    if pat_g is not None and rev_g is not None and pat_g - rev_g > 25 and conv is not None and conv < 0.8:
        flags.append(f"PAT growth {pat_g:.0f}% far above revenue growth {rev_g:.0f}% with weak cash backing")
    status = "requires_investigation" if len(flags) >= 2 else ("watch" if flags else "ok")
    return {"status": status, "flags": flags,
            "metrics": {"revenue_growth": rev_g, "pat_growth": pat_g, "receivables_growth": rec_g, "cfo_pat": conv}}
