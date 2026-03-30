"""Tests for the beam analysis module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.analysis.beam_analysis import (
    max_moment_two_wheels,
    max_shear_two_wheels,
    compute_deflection_two_wheels,
    analyze_beam,
)


class TestMaxMoment:
    """Tests for maximum moment calculations."""

    def test_single_load_at_midspan(self):
        """When wheel spacing >> span, only one wheel fits: M = PL/4."""
        P, s, L = 100.0, 20.0, 8.0
        M, x = max_moment_two_wheels(P, s, L)
        assert abs(M - P * L / 4.0) < 0.1
        assert abs(x - L / 2.0) < 0.01

    def test_two_wheels_symmetric(self):
        """Two equal loads with known solution."""
        P = 100.0  # kN
        s = 2.0    # m
        L = 10.0   # m

        M, x = max_moment_two_wheels(P, s, L)

        # Expected: place wheels at 4.5 and 6.5 m
        # R_A = 100*(10-4.5)/10 + 100*(10-6.5)/10 = 55 + 35 = 90 kN
        # or by symmetry placement: L/2 - s/4 = 4.5 for left wheel
        # check moment under right wheel at 6.5:
        # R_A = 100*(10-4.5)/10 + 100*(10-6.5)/10 = 55+35 = 90
        # M_6.5 = 90*6.5 - 100*2 = 585 - 200 = 385 kN·m

        # The max moment should be around 380-390 kN·m
        assert M > 350  # Sanity check
        assert M < 420

    def test_moment_increases_with_load(self):
        M1, _ = max_moment_two_wheels(100.0, 3.0, 10.0)
        M2, _ = max_moment_two_wheels(200.0, 3.0, 10.0)
        assert M2 > M1

    def test_moment_position_near_midspan(self):
        """Critical position should be near midspan."""
        _, x = max_moment_two_wheels(100.0, 2.0, 10.0)
        assert 3.0 < x < 7.0  # Should be roughly near midspan


class TestMaxShear:
    """Tests for maximum shear calculations."""

    def test_single_wheel_shear(self):
        """One wheel at support: V = P."""
        V = max_shear_two_wheels(100.0, 20.0, 8.0)  # s > L
        assert abs(V - 100.0) < 0.01

    def test_two_wheels_shear(self):
        """Left wheel at support: V = P + P*(L-s)/L."""
        P, s, L = 100.0, 3.0, 10.0
        V = max_shear_two_wheels(P, s, L)
        expected = P + P * (L - s) / L  # 100 + 70 = 170
        assert abs(V - expected) < 0.01


class TestDeflection:
    """Tests for deflection calculations."""

    def test_single_midspan_load(self):
        """Known formula: delta = PL^3 / (48*E*I) for single load at midspan."""
        P_kn = 100.0
        L_m = 8.0
        E = 200_000.0
        I = 300e6  # mm^4

        # For two symmetric loads very close together (s~0), should approach PL^3/(48EI)
        # But we test with s=0.001 to approximate single load
        delta = compute_deflection_two_wheels(P_kn / 2, 0.001, L_m, E, I)

        P_N = P_kn * 1000
        L_mm = L_m * 1000
        expected = P_N * L_mm**3 / (48.0 * E * I)

        # Should be close (within 5%) since two half-loads at same point ~ one load
        assert abs(delta - expected) / expected < 0.05

    def test_deflection_positive(self):
        delta = compute_deflection_two_wheels(100.0, 3.0, 8.0, 200_000.0, 300e6)
        assert delta > 0

    def test_larger_load_more_deflection(self):
        d1 = compute_deflection_two_wheels(50.0, 3.0, 8.0, 200_000.0, 300e6)
        d2 = compute_deflection_two_wheels(100.0, 3.0, 8.0, 200_000.0, 300e6)
        assert d2 > d1


class TestAnalyzeBeam:
    """Tests for the full beam analysis function."""

    def test_basic_analysis(self):
        result = analyze_beam(
            P_wheel_kn=100.0,
            wheel_spacing_m=3.0,
            span_m=8.0,
            w_self_kn_m=1.0,
        )

        assert result.M_max_kn_m > 0
        assert result.V_max_kn > 0
        assert 0 < result.x_Mmax_m < 8.0
        assert len(result.x_positions_m) == 200
        assert len(result.M_envelope_kn_m) == 200

    def test_self_weight_increases_moment(self):
        r1 = analyze_beam(100.0, 3.0, 8.0, w_self_kn_m=0.0)
        r2 = analyze_beam(100.0, 3.0, 8.0, w_self_kn_m=2.0)
        assert r2.M_max_kn_m > r1.M_max_kn_m
