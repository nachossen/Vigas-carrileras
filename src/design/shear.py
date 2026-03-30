"""Shear strength verification per AISC 360 Chapter G."""

import math
from dataclasses import dataclass

from src.models.beam import RunwayBeam
from src.utils.constants import PHI_SHEAR


@dataclass
class ShearResult:
    """Results of the shear verification."""

    Vn_kn: float            # Nominal shear strength (kN)
    phi_Vn_kn: float        # Design shear strength (kN)
    Vu_kn: float            # Required shear strength (kN)
    utilization: float      # Vu / φVn
    Cv1: float              # Web shear coefficient
    h_tw_ratio: float       # Web slenderness h/tw
    status: str             # "OK" or "FAIL"


def check_shear(beam: RunwayBeam, Vu_kn: float) -> ShearResult:
    """Verify shear strength per AISC 360 Chapter G.

    Vn = 0.6 * Fy * Aw * Cv1 (AISC G2-1)

    For most rolled W shapes with h/tw ≤ 2.24*sqrt(E/Fy):
        Cv1 = 1.0 and φ = 1.00

    For other cases:
        φ = 0.90 and Cv1 per AISC G2-3/G2-4

    Args:
        beam: Runway beam definition.
        Vu_kn: Required shear strength (kN).

    Returns:
        ShearResult with verification data.
    """
    profile = beam.main_profile
    mat = beam.material
    Fy = mat.Fy
    E = mat.E

    # Web area
    Aw = profile.d * profile.tw  # mm^2

    # Web slenderness
    h = profile.d - 2.0 * profile.tf  # Clear web height (approximate)
    h_tw = h / profile.tw

    # Check Cv1
    limit_1 = 2.24 * math.sqrt(E / Fy)

    if h_tw <= limit_1:
        Cv1 = 1.0
        phi = 1.00  # Per AISC G2.1(a)
    else:
        phi = PHI_SHEAR
        kv = 5.34  # No transverse stiffeners
        limit_2 = 1.10 * math.sqrt(kv * E / Fy)

        if h_tw <= limit_2:
            Cv1 = 1.0
        else:
            limit_3 = 1.37 * math.sqrt(kv * E / Fy)
            if h_tw <= limit_3:
                Cv1 = limit_2 / h_tw
            else:
                Cv1 = 1.51 * kv * E / (h_tw**2 * Fy)

    # Nominal shear strength
    Vn_N = 0.6 * Fy * Aw * Cv1  # N (since Fy in MPa, Aw in mm^2)
    Vn_kn = Vn_N / 1000.0  # kN
    phi_Vn = phi * Vn_kn

    utilization = Vu_kn / phi_Vn if phi_Vn > 0 else float("inf")
    status = "OK" if utilization <= 1.0 else "FAIL"

    return ShearResult(
        Vn_kn=Vn_kn,
        phi_Vn_kn=phi_Vn,
        Vu_kn=Vu_kn,
        utilization=utilization,
        Cv1=Cv1,
        h_tw_ratio=h_tw,
        status=status,
    )
