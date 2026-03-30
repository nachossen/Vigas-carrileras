"""Tests for the design verification modules."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.models.beam import RunwayBeam, SectionType
from src.models.materials import ASTM_A992
from src.models.profiles import get_profile_database
from src.design.flexure import check_biaxial_bending, compute_Lp, compute_Lr
from src.design.shear import check_shear
from src.design.web_local import check_web_local
from src.design.fatigue import (
    check_fatigue,
    compute_allowable_stress_range,
    compute_stress_range,
)
from src.design.serviceability import check_serviceability


@pytest.fixture
def w18x50_beam():
    """Create a test beam: W18x50, A992, 8m span."""
    profiles = get_profile_database()
    profile = profiles["W18x50"]
    return RunwayBeam(
        span_m=8.0,
        lateral_bracing_spacing_m=8.0,
        section_type=SectionType.W_SHAPE,
        main_profile=profile,
        material=ASTM_A992,
    )


class TestFlexure:
    """Tests for flexural verification."""

    def test_Lp_formula(self):
        """Lp = 1.76 * ry * sqrt(E/Fy)."""
        ry = 50.0  # mm
        E = 200_000.0
        Fy = 345.0
        Lp = compute_Lp(ry, E, Fy)
        expected = 1.76 * 50.0 * (200_000.0 / 345.0) ** 0.5
        assert abs(Lp - expected) < 0.01

    def test_flexure_check_returns_result(self, w18x50_beam):
        result = check_biaxial_bending(w18x50_beam, Mu_x_kn_m=200.0, Mu_y_kn_m=10.0)

        assert result.phi_Mn_x_kn_m > 0
        assert result.phi_Mn_y_kn_m > 0
        assert result.interaction_ratio > 0
        assert result.status in ("OK", "FAIL")

    def test_small_moment_passes(self, w18x50_beam):
        result = check_biaxial_bending(w18x50_beam, Mu_x_kn_m=50.0, Mu_y_kn_m=5.0)
        assert result.status == "OK"
        assert result.interaction_ratio < 1.0

    def test_huge_moment_fails(self, w18x50_beam):
        result = check_biaxial_bending(w18x50_beam, Mu_x_kn_m=5000.0, Mu_y_kn_m=500.0)
        assert result.status == "FAIL"
        assert result.interaction_ratio > 1.0


class TestShear:
    """Tests for shear verification."""

    def test_shear_check_basic(self, w18x50_beam):
        result = check_shear(w18x50_beam, Vu_kn=100.0)
        assert result.Vn_kn > 0
        assert result.phi_Vn_kn > 0
        assert result.utilization > 0
        assert result.status in ("OK", "FAIL")

    def test_small_shear_passes(self, w18x50_beam):
        result = check_shear(w18x50_beam, Vu_kn=50.0)
        assert result.status == "OK"

    def test_cv1_for_typical_w_shape(self, w18x50_beam):
        """Most rolled W shapes have Cv1 = 1.0."""
        result = check_shear(w18x50_beam, Vu_kn=50.0)
        assert result.Cv1 == 1.0


class TestWebLocal:
    """Tests for web local effects."""

    def test_web_yielding_interior(self, w18x50_beam):
        result = check_web_local(w18x50_beam, Pu_kn=100.0, lb_mm=100.0, at_end=False)
        assert result.Rn_yielding_kn > 0
        assert result.status_yielding in ("OK", "FAIL")

    def test_web_crippling_interior(self, w18x50_beam):
        result = check_web_local(w18x50_beam, Pu_kn=100.0, lb_mm=100.0, at_end=False)
        assert result.Rn_crippling_kn > 0
        assert result.status_crippling in ("OK", "FAIL")

    def test_end_gives_lower_capacity(self, w18x50_beam):
        """Capacity at end should be less than at interior."""
        r_int = check_web_local(w18x50_beam, Pu_kn=100.0, lb_mm=100.0, at_end=False)
        r_end = check_web_local(w18x50_beam, Pu_kn=100.0, lb_mm=100.0, at_end=True)
        assert r_end.Rn_yielding_kn < r_int.Rn_yielding_kn


class TestFatigue:
    """Tests for fatigue verification."""

    def test_stress_range_calculation(self):
        f_sr = compute_stress_range(M_max_kn_m=200.0, M_min_kn_m=20.0, Sx_mm3=1000e3)
        expected = (200.0 - 20.0) * 1e6 / 1000e3  # 180 MPa
        assert abs(f_sr - expected) < 0.01

    def test_allowable_stress_range_cat_a(self):
        FSR = compute_allowable_stress_range("A", 500_000)
        assert FSR > 0
        assert FSR >= 165.0  # Must be at least the threshold

    def test_high_cycles_converge_to_threshold(self):
        """At very high cycles, FSR should equal FTH."""
        FSR = compute_allowable_stress_range("C", 100_000_000)
        assert abs(FSR - 69.0) < 1.0  # FTH for Cat C

    def test_fatigue_check_passes_with_low_stress(self):
        result = check_fatigue(
            service_class="B",
            M_max_kn_m=50.0,
            M_min_kn_m=5.0,
            Sx_mm3=2000e3,
        )
        # Stress range = 45*1e6 / 2e6 = 22.5 MPa, should be well below thresholds
        assert result.status == "OK"

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="Unknown fatigue category"):
            compute_allowable_stress_range("Z", 100_000)


class TestServiceability:
    """Tests for deflection checks."""

    def test_deflection_check_returns_results(self, w18x50_beam):
        result = check_serviceability(
            beam=w18x50_beam,
            P_service_kn=80.0,
            H_service_kn=5.0,
            wheel_spacing_m=3.0,
        )
        assert result.delta_v_mm > 0
        assert result.delta_h_mm > 0
        assert result.delta_v_limit_mm > 0
        assert result.delta_h_limit_mm > 0
        assert result.status_vertical in ("OK", "FAIL")
        assert result.status_horizontal in ("OK", "FAIL")

    def test_deflection_limits(self, w18x50_beam):
        """Verify deflection limits are L/600 and L/400."""
        result = check_serviceability(
            beam=w18x50_beam,
            P_service_kn=50.0,
            H_service_kn=5.0,
            wheel_spacing_m=3.0,
        )
        L_mm = 8000.0
        assert abs(result.delta_v_limit_mm - L_mm / 600.0) < 0.01
        assert abs(result.delta_h_limit_mm - L_mm / 400.0) < 0.01
