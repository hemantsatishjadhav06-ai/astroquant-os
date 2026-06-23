"""Tests for Agent 5 — the Gann collector (Square of Nine, fan, time cycles)."""
from datetime import date

from astroquant.agents.base import RunContext
from astroquant.collectors.gann import (
    GANN_TIME_CYCLES,
    GannCollector,
    gann_fan,
    square_of_nine,
    time_cycles,
)


def test_square_of_nine_known_values():
    # sqrt(144) = 12. A 360° rotation adds 2 to the root: (12+2)^2 = 196; 180° -> (12+1)^2 = 169.
    levels = {(round(l.angle_deg), l.kind): l.price for l in square_of_nine(144.0)}
    assert abs(levels[(360, "resistance")] - 196.0) < 1e-6
    assert abs(levels[(180, "resistance")] - 169.0) < 1e-6
    assert abs(levels[(90, "resistance")] - 156.25) < 1e-6      # (12.5)^2
    assert abs(levels[(180, "support")] - 121.0) < 1e-6         # (12-1)^2


def test_square_of_nine_requires_positive_price():
    try:
        square_of_nine(0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_resistance_above_support_below():
    price = 256.0
    for lv in square_of_nine(price):
        if lv.kind == "resistance":
            assert lv.price > price
        else:
            assert lv.price < price


def test_time_cycles_project_forward():
    anchor = date(2024, 1, 1)
    hits = {h.cycle_len: h.target_date for h in time_cycles(anchor)}
    assert hits[90] == "2024-03-31"          # 90 calendar days on
    assert hits[365] == "2024-12-31"
    assert set(hits) == set(GANN_TIME_CYCLES)


def test_gann_fan_symmetry_and_slope():
    pts = {p.ratio: p for p in gann_fan(anchor_price=100.0, points_per_day=2.0, days_out=10)}
    one = pts["1x1"]
    # 1x1 at 2 pts/day for 10 days => ±20 around the pivot
    assert abs(one.price_up - 120.0) < 1e-6
    assert abs(one.price_down - 80.0) < 1e-6
    # 2x1 is twice as steep as 1x1
    assert abs((pts["2x1"].price_up - 100.0) - 2 * (one.price_up - 100.0)) < 1e-6


def test_gann_agent_runs_and_healthchecks():
    col = GannCollector()
    assert col.healthcheck().ok
    res = col.run(RunContext(run_id="t", start=date(2024, 1, 1),
                             config={"anchor_price": 100.0, "days_out": 60}))
    assert res.status == "ok"
    assert res.rows_written > 0
    assert res.metrics["cycles"] == len(GANN_TIME_CYCLES)
