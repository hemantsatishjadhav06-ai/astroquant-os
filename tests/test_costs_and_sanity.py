"""Tests for the India cost model (verified rates) and the research sanity guards."""
import numpy as np

from astroquant.research.costs import CostConfig, Segment, Side, compute_costs
from astroquant.research.sanity import random_feature_test, shuffle_label_test


def test_delivery_stt_both_sides():
    # Equity delivery STT = 0.1% on both buy and sell.
    buy = compute_costs(100_000, Segment.EQUITY_DELIVERY, Side.BUY)
    sell = compute_costs(100_000, Segment.EQUITY_DELIVERY, Side.SELL)
    assert abs(buy.stt - 100.0) < 1e-6        # 0.1% of 100k
    assert abs(sell.stt - 100.0) < 1e-6


def test_intraday_stt_sell_only():
    buy = compute_costs(100_000, Segment.EQUITY_INTRADAY, Side.BUY)
    sell = compute_costs(100_000, Segment.EQUITY_INTRADAY, Side.SELL)
    assert buy.stt == 0.0
    assert abs(sell.stt - 25.0) < 1e-6        # 0.025% of 100k


def test_stamp_duty_buy_side_only():
    buy = compute_costs(100_000, Segment.EQUITY_DELIVERY, Side.BUY)
    sell = compute_costs(100_000, Segment.EQUITY_DELIVERY, Side.SELL)
    assert buy.stamp_duty > 0
    assert sell.stamp_duty == 0.0


def test_gst_not_on_stt_or_stamp():
    c = CostConfig()
    b = compute_costs(100_000, Segment.EQUITY_INTRADAY, Side.SELL)
    expected_gst = c.gst * (b.brokerage + b.exchange + b.sebi)
    assert abs(b.gst - expected_gst) < 1e-4    # GST excludes STT & stamp duty


def test_dp_charge_only_on_delivery_sell():
    assert compute_costs(100_000, Segment.EQUITY_DELIVERY, Side.SELL).dp > 0
    assert compute_costs(100_000, Segment.EQUITY_DELIVERY, Side.BUY).dp == 0.0
    assert compute_costs(100_000, Segment.EQUITY_INTRADAY, Side.SELL).dp == 0.0


def test_total_is_sum_of_parts():
    b = compute_costs(250_000, Segment.FUTURES, Side.SELL)
    parts = b.brokerage + b.stt + b.exchange + b.sebi + b.stamp_duty + b.dp + b.gst
    assert abs(b.total - parts) < 1e-3


# --- research sanity guards ---

def test_shuffle_label_flags_noise_as_no_edge():
    # Random X,y with no relationship: a constant 'score' equals shuffled => should NOT pass (no edge).
    rng = np.random.default_rng(0)
    X = rng.standard_normal((200, 5))
    y = rng.integers(0, 2, 200)

    def score_fn(Xa, ya):  # correlation of first feature with label — ~0 for noise
        return abs(np.corrcoef(Xa[:, 0], ya)[0, 1])

    real = score_fn(X, y)
    res = shuffle_label_test(score_fn, X, y, real_score=real, n_permutations=100, seed=1)
    # On pure noise, the real score sits inside the shuffled distribution => no edge => passed=False.
    assert res.passed is False


def test_shuffle_label_detects_real_signal():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((300, 3))
    y = (X[:, 0] > 0).astype(int)            # label genuinely depends on feature 0

    def score_fn(Xa, ya):
        return abs(np.corrcoef(Xa[:, 0], ya)[0, 1])

    real = score_fn(X, y)
    res = shuffle_label_test(score_fn, X, y, real_score=real, n_permutations=100, seed=1)
    assert res.passed is True                 # genuine signal beats shuffled => edge detected


def test_random_feature_test():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((100, 4))

    def importance_fn(Xa):
        # real features get high importance, appended noise should be low
        base = np.array([10.0, 8.0, 9.0, 7.0])
        noise_imp = abs(np.corrcoef(Xa[:, -1], rng.standard_normal(Xa.shape[0]))[0, 1])
        return np.append(base, noise_imp)

    res = random_feature_test(importance_fn, X, seed=1)
    assert res.passed is True
