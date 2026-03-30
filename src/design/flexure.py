"""Flexural strength verification per AISC 360 Chapter F and H.

Handles:
- Strong-axis nominal moment Mn (compact W shapes, LTB)
- Weak-axis nominal moment Mny
- Biaxial bending interaction check (AISC H1)
"""

import math
from dataclasses import dataclass

from src.models.beam import RunwayBeam, SectionType
from src.utils.constants import PHI_FLEXURE


@dataclass
class FlexureResult:
    """Results of the flexural verification."""

    # Strong axis
    Mn_x_kn_m: float        # Nominal strong-axis moment capacity (kN·m)
    phi_Mn_x_kn_m: float    # Design strong-axis moment capacity (kN·m)
    Lp_mm: float             # Limiting unbraced length for full plastic moment
    Lr_mm: float             # Limiting unbraced length for inelastic LTB
    ltb_zone: str            # "plastic", "inelastic", or "elastic"

    # Weak axis
    Mn_y_kn_m: float         # Nominal weak-axis moment capacity (kN·m)
    phi_Mn_y_kn_m: float     # Design weak-axis moment capacity (kN·m)

    # Interaction check
    interaction_ratio: float  # Biaxial interaction ratio (≤ 1.0 OK)
    Mu_x_kn_m: float         # Applied strong-axis moment
    Mu_y_kn_m: float         # Applied weak-axis moment
    status: str              # "OK" or "FAIL"


def compute_Lp(ry_mm: float, E: float, Fy: float) -> float:
    """Limiting laterally unbraced length for yielding (AISC F2-5).

    Lp = 1.76 * ry * sqrt(E / Fy)
    """
    return 1.76 * ry_mm * math.sqrt(E / Fy)


def compute_Lr(
    rts_mm: float, E: float, Fy: float,
    J_mm4: float, Sx_mm3: float, ho_mm: float, c: float = 1.0
) -> float:
    """Limiting laterally unbraced length for inelastic LTB (AISC F2-6).

    Lr = 1.95 * rts * (E / (0.7*Fy)) *
         sqrt( J*c/(Sx*ho) + sqrt( (J*c/(Sx*ho))^2 + 6.76*(0.7*Fy/E)^2 ) )
    """
    term = J_mm4 * c / (Sx_mm3 * ho_mm)
    Lr = 1.95 * rts_mm * (E / (0.7 * Fy)) * math.sqrt(
        term + math.sqrt(term**2 + 6.76 * (0.7 * Fy / E) ** 2)
    )
    return Lr


def compute_Mn_strong_axis(beam: RunwayBeam) -> tuple[float, float, float, str]:
    """Compute nominal strong-axis moment Mn considering LTB.

    Returns:
        (Mn_N_mm, Lp_mm, Lr_mm, ltb_zone)
        Mn in N·mm, Lp and Lr in mm.
    """
    profile = beam.main_profile
    mat = beam.material
    E = mat.E
    Fy = mat.Fy

    Mp = Fy * profile.Zx  # N·mm (since Fy in MPa, Zx in mm^3)
    My_07 = 0.7 * Fy * profile.Sx

    Lp = compute_Lp(profile.ry, E, Fy)
    Lr = compute_Lr(profile.rts, E, Fy, profile.J, profile.Sx, profile.ho)

    Lb = beam.Lb_mm

    if Lb <= Lp:
        Mn = Mp
        zone = "plastic"
    elif Lb <= Lr:
        # Inelastic LTB (AISC F2-2)
        Cb = 1.0  # Conservative for crane beams (moving loads)
        Mn = Cb * (Mp - (Mp - My_07) * (Lb - Lp) / (Lr - Lp))
        Mn = min(Mn, Mp)
        zone = "inelastic"
    else:
        # Elastic LTB (AISC F2-3 & F2-4)
        Cb = 1.0
        Fcr = (
            Cb * math.pi**2 * E / (Lb / profile.rts) ** 2
            * math.sqrt(
                1
                + 0.078 * profile.J / (profile.Sx * profile.ho)
                * (Lb / profile.rts) ** 2
            )
        )
        Mn = Fcr * profile.Sx
        Mn = min(Mn, Mp)
        zone = "elastic"

    return Mn, Lp, Lr, zone


def compute_Mn_weak_axis(beam: RunwayBeam) -> float:
    """Compute nominal weak-axis moment Mny.

    For W shapes: Mny = min(Fy * Zy, 1.6 * Fy * Sy) [AISC F6]

    For W + Channel sections, the weak-axis capacity is computed
    for the top flange assembly (W flange + channel acting compositely).

    Returns:
        Mny in N·mm.
    """
    profile = beam.main_profile
    Fy = beam.material.Fy

    if beam.section_type == SectionType.W_WITH_CHANNEL and beam.cap_channel:
        # Weak-axis bending is resisted primarily by the top flange + channel
        # Approximate: use combined Iy and compute Sy for the top flange region
        ch = beam.cap_channel
        # Channel Iy acts as additional Iy for the weak axis of the top flange
        Iy_combined = profile.Iy + ch.Ix  # Channel strong axis = beam weak axis
        Sy_combined = profile.Sy + ch.Sx
        Zy_combined = profile.Zy + ch.Zx

        Mny = min(Fy * Zy_combined, 1.6 * Fy * Sy_combined)
    else:
        Mny = min(Fy * profile.Zy, 1.6 * Fy * profile.Sy)

    return Mny


def check_biaxial_bending(
    beam: RunwayBeam, Mu_x_kn_m: float, Mu_y_kn_m: float
) -> FlexureResult:
    """Perform the complete biaxial bending verification.

    Interaction equation (AISC H1-1b for beams without axial load):
        Mux / (φ·Mnx) + Muy / (φ·Mny) ≤ 1.0

    Args:
        beam: Runway beam definition.
        Mu_x_kn_m: Required strong-axis moment (kN·m).
        Mu_y_kn_m: Required weak-axis moment (kN·m).

    Returns:
        FlexureResult with all verification data.
    """
    # Strong axis
    Mn_x_Nmm, Lp, Lr, zone = compute_Mn_strong_axis(beam)
    Mn_x_kn_m = Mn_x_Nmm / 1e6  # Convert N·mm to kN·m
    phi_Mn_x = PHI_FLEXURE * Mn_x_kn_m

    # Weak axis
    Mn_y_Nmm = compute_Mn_weak_axis(beam)
    Mn_y_kn_m = Mn_y_Nmm / 1e6
    phi_Mn_y = PHI_FLEXURE * Mn_y_kn_m

    # Interaction ratio
    ratio_x = Mu_x_kn_m / phi_Mn_x if phi_Mn_x > 0 else float("inf")
    ratio_y = Mu_y_kn_m / phi_Mn_y if phi_Mn_y > 0 else float("inf")
    interaction = ratio_x + ratio_y

    status = "OK" if interaction <= 1.0 else "FAIL"

    return FlexureResult(
        Mn_x_kn_m=Mn_x_kn_m,
        phi_Mn_x_kn_m=phi_Mn_x,
        Lp_mm=Lp,
        Lr_mm=Lr,
        ltb_zone=zone,
        Mn_y_kn_m=Mn_y_kn_m,
        phi_Mn_y_kn_m=phi_Mn_y,
        interaction_ratio=interaction,
        Mu_x_kn_m=Mu_x_kn_m,
        Mu_y_kn_m=Mu_y_kn_m,
        status=status,
    )
