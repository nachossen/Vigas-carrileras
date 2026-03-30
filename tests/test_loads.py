"""Tests for the load generation module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.models.crane import CraneData
from src.loads.load_generator import compute_wheel_loads
from src.utils.constants import KN_PER_TON


def make_crane(**kwargs) -> CraneData:
    """Create a test crane with default values."""
    defaults = dict(
        capacity_ton=10.0,
        bridge_weight_kn=80.0,
        trolley_weight_kn=20.0,
        bridge_span_m=15.0,
        wheel_spacing_m=3.0,
        num_wheels_per_rail=2,
        service_class="C",
        min_approach_m=1.0,
    )
    defaults.update(kwargs)
    return CraneData(**defaults)


class TestWheelLoads:
    """Tests for wheel load calculations."""

    def test_lifted_load_conversion(self):
        crane = make_crane(capacity_ton=10.0)
        assert abs(crane.lifted_load_kn - 10.0 * KN_PER_TON) < 0.01

    def test_impact_factor_class_c(self):
        crane = make_crane(service_class="C")
        assert crane.impact_factor == 0.20

    def test_impact_factor_class_a(self):
        crane = make_crane(service_class="A")
        assert crane.impact_factor == 0.0

    def test_max_static_reaction(self):
        """Verify R_max = (P+W_trolley)*(L-d_min)/L + W_bridge/2."""
        crane = make_crane(
            capacity_ton=10.0,
            bridge_weight_kn=80.0,
            trolley_weight_kn=20.0,
            bridge_span_m=15.0,
            min_approach_m=1.0,
        )
        wl = compute_wheel_loads(crane)

        P = 10.0 * KN_PER_TON  # 98.1 kN
        expected_R_max = (P + 20.0) * (15.0 - 1.0) / 15.0 + 80.0 / 2.0
        assert abs(wl.R_max_static_kn - expected_R_max) < 0.1

    def test_dynamic_wheel_load_includes_impact(self):
        crane = make_crane(service_class="C", num_wheels_per_rail=2)
        wl = compute_wheel_loads(crane)

        expected = wl.R_max_static_kn * 1.20 / 2
        assert abs(wl.P_wheel_max_kn - expected) < 0.01

    def test_lateral_force(self):
        """H_lat = 0.20 * (P_lifted + W_trolley)."""
        crane = make_crane(capacity_ton=10.0, trolley_weight_kn=20.0)
        wl = compute_wheel_loads(crane)

        P = 10.0 * KN_PER_TON
        expected = 0.20 * (P + 20.0)
        assert abs(wl.H_lateral_total_kn - expected) < 0.1

    def test_longitudinal_force(self):
        """H_long = 0.10 * (P_wheel_max * n_wheels)."""
        crane = make_crane(num_wheels_per_rail=2)
        wl = compute_wheel_loads(crane)

        expected = 0.10 * (wl.P_wheel_max_kn * 2)
        assert abs(wl.H_longitudinal_kn - expected) < 0.01

    def test_min_static_reaction(self):
        """Min reaction when trolley is at far side."""
        crane = make_crane(min_approach_m=1.0, bridge_span_m=15.0)
        wl = compute_wheel_loads(crane)

        P = crane.lifted_load_kn
        expected_R_min = (P + 20.0) * 1.0 / 15.0 + 80.0 / 2.0
        assert abs(wl.R_min_static_kn - expected_R_min) < 0.1

    def test_invalid_service_class_raises(self):
        with pytest.raises(ValueError, match="Invalid service class"):
            make_crane(service_class="Z")

    def test_zero_approach_distance(self):
        """When min_approach=0, trolley is directly over the rail."""
        crane = make_crane(min_approach_m=0.0)
        wl = compute_wheel_loads(crane)

        expected = crane.lifted_load_kn + 20.0 + 80.0 / 2.0
        assert abs(wl.R_max_static_kn - expected) < 0.01
