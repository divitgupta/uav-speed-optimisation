"""Verification tests: the model must reproduce the Phase-1 reference curve (Zeng et al., 2019)."""
import numpy as np
import pytest

from uav_opt.model import UAV, Mission, energy_kj, power_w, reliability, time_s
from uav_opt.optimize import grid_search, nsga2, weighted_sum_scipy

PHASE1_CURVE = {4: 188.3, 6: 114.5, 8: 80.6, 10: 63.0, 12: 53.3, 14: 47.8, 16: 45.1,
                18: 44.2, 20: 44.6, 22: 46.0, 24: 48.4, 26: 51.4, 28: 55.1, 30: 59.4}


@pytest.mark.parametrize("v,expected", PHASE1_CURVE.items())
def test_reproduces_phase1_energy_curve(v, expected):
    e = energy_kj(v, UAV(v_max=30), Mission(distance_km=5))
    assert e == pytest.approx(expected, abs=0.1)


def test_hover_power_matches_zeng():
    assert power_w(0.0, UAV()) == pytest.approx(79.86 + 88.63, rel=1e-6)


def test_time_and_headwind():
    assert time_s(10, Mission(distance_km=5)) == pytest.approx(500)
    assert time_s(10, Mission(distance_km=5, headwind_ms=5)) == pytest.approx(1000)
    assert np.isinf(time_s(4, Mission(distance_km=5, headwind_ms=5)))


def test_reliability_bounds_and_monotonic_in_distance():
    u = UAV()
    r5 = reliability(10, u, Mission(distance_km=5))
    r10 = reliability(10, u, Mission(distance_km=10))
    assert 0 < r10 < r5 < 1


def test_optimisers_agree():
    u, m = UAV(v_max=25, battery_kJ=300), Mission()
    g, s, n = grid_search(u, m), weighted_sum_scipy(u, m), nsga2(u, m)
    assert s.v_energy == pytest.approx(g.v_energy, abs=0.15)
    assert s.v_star == pytest.approx(g.v_star, abs=0.15)
    assert n.v_star == pytest.approx(g.v_star, abs=0.5)


def test_infeasible_when_battery_too_small():
    assert grid_search(UAV(battery_kJ=1.0), Mission()).v_star is None
