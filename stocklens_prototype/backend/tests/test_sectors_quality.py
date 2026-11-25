import pandas as pd, pytest, json
from app.sectors.scoring import WEIGHTS, minmax_0_100, classify_phase
from app.quality.earnings_quality import assess
from app.quality.guidance import deviation
from types import SimpleNamespace as NS

def test_TC70_weights_sum_to_one(): assert sum(WEIGHTS.values()) == pytest.approx(1.0)
def test_TC71_minmax_bounds():
    r = minmax_0_100(pd.Series([3.0, 9.0, 6.0])); assert r.min() == 0 and r.max() == 100
def test_TC72_minmax_constant_series_neutral(): assert (minmax_0_100(pd.Series([5.0, 5.0])) == 50).all()
def test_TC73_phase_leading(): assert classify_phase(5, 2) == "Leading"
def test_TC74_phase_improving(): assert classify_phase(-1, -4) == "Improving"
def test_TC75_phase_weakening(): assert classify_phase(4, 6) == "Weakening"
def test_TC76_phase_lagging(): assert classify_phase(-3, -1) == "Lagging"
def test_TC77_sector_scores_in_range_and_ranked(client):
    s = client.get("/api/v1/sectors/rankings").json()["sectors"]
    assert all(0 <= x["score"] <= 100 for x in s)
    assert [x["rank"] for x in s] == sorted(x["rank"] for x in s)
    assert [x["score"] for x in s] == sorted((x["score"] for x in s), reverse=True)

def _r(**k): return NS(**k)
def test_TC78_insufficient_data(): assert assess([_r()])["status"] == "insufficient_data"
def test_TC79_healthy_company_not_flagged():
    a = _r(revenue=100, pat=10, receivables=15, cfo=11); b = _r(revenue=110, pat=11, receivables=16.5, cfo=11)
    assert assess([a, b])["status"] == "ok"
def test_TC80_blueprint_example_flagged():   # PAT +42%, revenue +35%, CFO/PAT 0.35, receivables +58%
    a = _r(revenue=100, pat=10, receivables=10, cfo=9); b = _r(revenue=135, pat=14.2, receivables=15.8, cfo=14.2 * .35)
    assert assess([a, b])["status"] == "requires_investigation"
def test_TC81_all_injected_anomalies_detected(db, seeded):
    from app.main import earnings_quality
    from app.core import models as m
    for cid in seeded:
        sym = db.get(m.Company, cid).symbol
        assert earnings_quality(sym, db)["status"] == "requires_investigation"
def test_TC82_false_positive_rate_low(db, seeded):
    from app.main import earnings_quality
    from app.core import models as m
    others = [c.symbol for c in db.query(m.Company).all() if c.id not in seeded]
    flagged = [s for s in others if earnings_quality(s, db)["status"] == "requires_investigation"]
    assert len(flagged) / len(others) <= 0.10
def test_TC83_guidance_beat_met_missed():
    assert deviation(10, 14, 15)["status"] == "beat" and deviation(10, 14, 12)["status"] == "met" and deviation(10, 14, 8)["status"] == "missed"
def test_TC84_guidance_deviation_vs_midpoint(): assert deviation(10, 14, 15)["deviation_vs_midpoint"] == 3
