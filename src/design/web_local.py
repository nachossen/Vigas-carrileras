"""Web local effects: yielding and crippling under concentrated loads.

Per AISC 360 Sections J10.2 and J10.3.
"""

import math
from dataclasses import dataclass

from src.models.beam import RunwayBeam
from src.utils.constants import PHI_WEB_CRIPPLING, PHI_WEB_YIELDING


@dataclass
class WebLocalResult:
    """Results of web local effects verification."""

    # Web Yielding (J10.2)
    Rn_yielding_kn: float      # Nominal web yielding strength (kN)
    phi_Rn_yielding_kn: float  # Design web yielding strength (kN)
    util_yielding: float       # Utilization for web yielding

    # Web Crippling (J10.3)
    Rn_crippling_kn: float     # Nominal web crippling strength (kN)
    phi_Rn_crippling_kn: float # Design web crippling strength (kN)
    util_crippling: float      # Utilization for web crippling

    Pu_kn: float               # Applied concentrated load (kN)
    status_yielding: str       # "OK" or "FAIL"
    status_crippling: str      # "OK" or "FAIL"


def check_web_local(
    beam: RunwayBeam,
    Pu_kn: float,
    lb_mm: float = 100.0,
    at_end: bool = False,
) -> WebLocalResult:
    """Verify web yielding and web crippling under concentrated wheel loads.

    Args:
        beam: Runway beam definition.
        Pu_kn: Concentrated factored load (kN).
        lb_mm: Bearing length at the load point (mm). Typically the rail
               base width (~100-150 mm).
        at_end: True if the load is at or near the beam end (within d/2).

    Returns:
        WebLocalResult with all verification data.
    """
    profile = beam.main_profile
    mat = beam.material
    Fy = mat.Fy
    E = mat.E

    tw = profile.tw
    tf = profile.tf
    d = profile.d
    k = profile.k

    # ---- Web Yielding (AISC J10.2) ----
    if at_end:
        # At beam end: Rn = Fy * tw * (2.5*k + lb) [AISC J10-3]
        Rn_yield_N = Fy * tw * (2.5 * k + lb_mm)
    else:
        # Interior: Rn = Fy * tw * (5*k + lb) [AISC J10-2]
        Rn_yield_N = Fy * tw * (5.0 * k + lb_mm)

    Rn_yield_kn = Rn_yield_N / 1000.0
    phi_Rn_yield = PHI_WEB_YIELDING * Rn_yield_kn

    # ---- Web Crippling (AISC J10.3) ----
    if at_end and lb_mm / d <= 0.2:
        # AISC J10-5a
        Rn_crip_N = (
            0.40 * tw**2
            * (1.0 + 3.0 * (lb_mm / d) * (tw / tf) ** 1.5)
            * math.sqrt(E * Fy * tf / tw)
        )
    elif at_end:
        # AISC J10-5b
        Rn_crip_N = (
            0.40 * tw**2
            * (1.0 + (4.0 * lb_mm / d - 0.2) * (tw / tf) ** 1.5)
            * math.sqrt(E * Fy * tf / tw)
        )
    else:
        # Interior: AISC J10-4
        Rn_crip_N = (
            0.80 * tw**2
            * (1.0 + 3.0 * (lb_mm / d) * (tw / tf) ** 1.5)
            * math.sqrt(E * Fy * tf / tw)
        )

    Rn_crip_kn = Rn_crip_N / 1000.0
    phi_Rn_crip = PHI_WEB_CRIPPLING * Rn_crip_kn

    util_yield = Pu_kn / phi_Rn_yield if phi_Rn_yield > 0 else float("inf")
    util_crip = Pu_kn / phi_Rn_crip if phi_Rn_crip > 0 else float("inf")

    return WebLocalResult(
        Rn_yielding_kn=Rn_yield_kn,
        phi_Rn_yielding_kn=phi_Rn_yield,
        util_yielding=util_yield,
        Rn_crippling_kn=Rn_crip_kn,
        phi_Rn_crippling_kn=phi_Rn_crip,
        util_crippling=util_crip,
        Pu_kn=Pu_kn,
        status_yielding="OK" if util_yield <= 1.0 else "FAIL",
        status_crippling="OK" if util_crip <= 1.0 else "FAIL",
    )
