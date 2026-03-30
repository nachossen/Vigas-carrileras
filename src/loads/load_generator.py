"""Load generation for crane runway beams.

Calculates wheel loads, lateral forces, and longitudinal forces
following ASCE 7, AISC Design Guide 7, and CMAA specifications.
"""

from dataclasses import dataclass

from src.models.crane import CraneData
from src.utils.constants import (
    LATERAL_FORCE_COEFF,
    LONGITUDINAL_FORCE_COEFF,
)


@dataclass
class WheelLoads:
    """Computed wheel loads for a crane runway beam.

    All forces in kN.
    """

    # Vertical loads
    R_max_static_kn: float       # Max static reaction on one rail (kN)
    R_min_static_kn: float       # Min static reaction on one rail (kN)
    P_wheel_max_kn: float        # Max dynamic wheel load including impact (kN)
    P_wheel_min_kn: float        # Min wheel load (bridge only, no crane load) (kN)
    impact_factor: float         # Applied impact factor

    # Lateral loads
    H_lateral_total_kn: float    # Total lateral force (kN)
    H_lateral_per_wheel_kn: float  # Lateral force per wheel (kN)

    # Longitudinal loads
    H_longitudinal_kn: float     # Total longitudinal braking force (kN)

    # Self-weight of beam (to be set by analysis)
    beam_self_weight_kn_m: float = 0.0


def compute_wheel_loads(crane: CraneData) -> WheelLoads:
    """Compute maximum dynamic wheel loads and associated forces.

    This function determines the critical wheel loads acting on a runway beam
    by positioning the trolley at the most unfavorable location (closest to
    the runway beam) and applying the appropriate impact factor.

    Args:
        crane: Crane operational and geometric data.

    Returns:
        WheelLoads with all computed forces.

    Reference:
        ASCE 7 - Crane loads
        AISC Design Guide 7 - Industrial Buildings
    """
    P_lifted = crane.lifted_load_kn
    W_trolley = crane.trolley_weight_kn
    W_bridge = crane.bridge_weight_kn
    L_bridge = crane.bridge_span_m
    d_min = crane.min_approach_m
    n_wheels = crane.num_wheels_per_rail

    # --- Maximum static reaction (trolley at closest approach to this rail) ---
    # R_max = (P + W_trolley) * (L - d_min) / L + W_bridge / 2
    if d_min > 0 and L_bridge > 0:
        R_max_static = (
            (P_lifted + W_trolley) * (L_bridge - d_min) / L_bridge
            + W_bridge / 2.0
        )
    else:
        # Trolley directly over the rail
        R_max_static = P_lifted + W_trolley + W_bridge / 2.0

    # --- Minimum static reaction (trolley at far side) ---
    # R_min = (P + W_trolley) * d_min / L + W_bridge / 2
    if d_min > 0 and L_bridge > 0:
        R_min_static = (
            (P_lifted + W_trolley) * d_min / L_bridge
            + W_bridge / 2.0
        )
    else:
        # Worst case: trolley at far end, reaction = bridge weight only
        R_min_static = W_bridge / 2.0

    # --- Impact factor ---
    impact = crane.impact_factor

    # --- Dynamic wheel load (per wheel) ---
    # For an end truck with n_wheels on this rail
    P_wheel_max = R_max_static * (1.0 + impact) / n_wheels
    P_wheel_min = (W_bridge / 2.0) / n_wheels  # Only bridge dead load

    # --- Lateral force (trolley traversing thrust) ---
    # H_lat = 0.20 * (P_lifted + W_trolley)  [ASCE 7 / AISC DG7]
    H_lateral_total = LATERAL_FORCE_COEFF * (P_lifted + W_trolley)
    total_wheels = n_wheels * 2  # wheels on both rails
    H_lateral_per_wheel = H_lateral_total / total_wheels

    # --- Longitudinal force (bridge braking) ---
    # H_long = 0.10 * (total max wheel loads on driven side)
    # Assumes all wheels on one rail are driven
    H_longitudinal = LONGITUDINAL_FORCE_COEFF * (P_wheel_max * n_wheels)

    return WheelLoads(
        R_max_static_kn=R_max_static,
        R_min_static_kn=R_min_static,
        P_wheel_max_kn=P_wheel_max,
        P_wheel_min_kn=P_wheel_min,
        impact_factor=impact,
        H_lateral_total_kn=H_lateral_total,
        H_lateral_per_wheel_kn=H_lateral_per_wheel,
        H_longitudinal_kn=H_longitudinal,
    )
