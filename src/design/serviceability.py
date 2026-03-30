"""Serviceability (deflection) verification per AISC Design Guide 7."""

from dataclasses import dataclass

from src.analysis.beam_analysis import compute_deflection_two_wheels
from src.models.beam import RunwayBeam
from src.utils.constants import (
    HORIZONTAL_DEFLECTION_LIMIT,
    VERTICAL_DEFLECTION_LIMIT,
)


@dataclass
class ServiceabilityResult:
    """Results of the deflection verification."""

    # Vertical
    delta_v_mm: float           # Computed vertical deflection (mm)
    delta_v_limit_mm: float     # Allowable vertical deflection (mm)
    util_vertical: float        # delta_v / delta_limit
    status_vertical: str        # "OK" or "FAIL"

    # Horizontal
    delta_h_mm: float           # Computed horizontal deflection (mm)
    delta_h_limit_mm: float     # Allowable horizontal deflection (mm)
    util_horizontal: float      # delta_h / delta_limit
    status_horizontal: str      # "OK" or "FAIL"


def check_serviceability(
    beam: RunwayBeam,
    P_service_kn: float,
    H_service_kn: float,
    wheel_spacing_m: float,
) -> ServiceabilityResult:
    """Check vertical and horizontal deflections under service loads.

    Deflection limits (AISC Design Guide 7):
    - Vertical: L / 600
    - Horizontal: L / 400

    Args:
        beam: Runway beam definition.
        P_service_kn: Service (unfactored) vertical wheel load (kN).
        H_service_kn: Service (unfactored) horizontal wheel load (kN).
        wheel_spacing_m: Wheel spacing (m).

    Returns:
        ServiceabilityResult with deflection checks.
    """
    L_m = beam.span_m
    L_mm = beam.span_mm
    E = beam.material.E
    profile = beam.main_profile

    # Vertical deflection
    delta_v = compute_deflection_two_wheels(
        P_kn=P_service_kn,
        s_m=wheel_spacing_m,
        L_m=L_m,
        E_mpa=E,
        I_mm4=profile.Ix,
    )

    delta_v_limit = L_mm / VERTICAL_DEFLECTION_LIMIT

    # Horizontal deflection
    # Lateral loads are resisted by the top flange (and channel if present)
    if beam.cap_channel:
        # For W + Channel: use combined Iy (channel Ix contributes to beam Iy)
        Iy_eff = profile.Iy + beam.cap_channel.Ix
    else:
        # For W shape alone: lateral bending resisted by top flange only
        # Approximate: Iy_flange = tf * bf^3 / 12
        Iy_eff = profile.tf * profile.bf ** 3 / 12.0

    delta_h = compute_deflection_two_wheels(
        P_kn=H_service_kn,
        s_m=wheel_spacing_m,
        L_m=L_m,
        E_mpa=E,
        I_mm4=Iy_eff,
    )

    delta_h_limit = L_mm / HORIZONTAL_DEFLECTION_LIMIT

    util_v = delta_v / delta_v_limit if delta_v_limit > 0 else 0.0
    util_h = delta_h / delta_h_limit if delta_h_limit > 0 else 0.0

    return ServiceabilityResult(
        delta_v_mm=delta_v,
        delta_v_limit_mm=delta_v_limit,
        util_vertical=util_v,
        status_vertical="OK" if util_v <= 1.0 else "FAIL",
        delta_h_mm=delta_h,
        delta_h_limit_mm=delta_h_limit,
        util_horizontal=util_h,
        status_horizontal="OK" if util_h <= 1.0 else "FAIL",
    )
