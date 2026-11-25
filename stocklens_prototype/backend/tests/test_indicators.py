import numpy as np, pandas as pd, pytest
from app.market.indicators import rsi, sma, ema, period_return

def _ref_rsi(close, n=14):
    c = list(close); g = l = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]; g += max(d, 0); l += max(-d, 0)
    g /= n; l /= n
    out = {n: 100 - 100 / (1 + g / l) if l else 100}
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n; l = (l * (n - 1) + max(-d, 0)) / n
        out[i] = 100 - 100 / (1 + g / l) if l else 100
    return out

def test_TC22_rsi_monotonic_up_is_100(): assert rsi(pd.Series(np.arange(1, 60, dtype=float))).iloc[-1] == 100
def test_TC23_rsi_flat_is_50(): assert rsi(pd.Series([10.0] * 40)).iloc[-1] == 50
def test_TC24_rsi_bounded_0_100():
    s = pd.Series(np.cumprod(1 + np.random.default_rng(1).normal(0, .02, 400)) * 100)
    r = rsi(s).dropna(); assert ((r >= 0) & (r <= 100)).all()
def test_TC25_rsi_matches_wilder_reference_loop():
    s = pd.Series(np.cumprod(1 + np.random.default_rng(2).normal(0, .02, 300)) * 100)
    ref = _ref_rsi(s.values); r = rsi(s)
    # pandas ewm(min_periods) seeds with the first diff, so compare after burn-in
    assert max(abs(r.iloc[i] - v) for i, v in ref.items() if i > 120) < 0.5
def test_TC26_sma_known(): assert sma(pd.Series([1, 2, 3, 4, 5.0]), 3).iloc[-1] == 4
def test_TC27_ema_responds_faster_than_sma():
    s = pd.Series([10.0] * 30 + [20.0] * 5); assert ema(s, 10).iloc[-1] > sma(s, 10).iloc[-1]  # 16.3 vs 15.0
def test_TC28_period_return(): assert period_return(pd.Series([100.0, 110, 121]), 2) == pytest.approx(21.0)
def test_TC29_period_return_insufficient_history(): assert period_return(pd.Series([1.0, 2.0]), 5) is None
