"""Fatigue verification per AISC 360 Appendix 3.

Critical check for crane runway beams due to cyclic loading.
"""

from dataclasses import dataclass

from src.utils.constants import (
    FATIGUE_CF,
    FATIGUE_CYCLES,
    FATIGUE_THRESHOLD,
)


@dataclass
class FatigueDetail:
    """A fatigue-sensitive detail to be checked."""

    name: str
    category: str  # "A", "B", "B'", "C", "D", "E", "E'"
    location: str  # Description of where the detail is


@dataclass
class FatigueCheckResult:
    """Result of a single fatigue detail check."""

    detail: FatigueDetail
    f_sr_mpa: float          # Computed stress range (MPa)
    F_SR_mpa: float          # Allowable stress range (MPa)
    F_TH_mpa: float          # Fatigue threshold (MPa)
    N_cycles: int            # Design number of load cycles
    utilization: float       # f_sr / F_SR
    status: str              # "OK" or "FAIL"


@dataclass
class FatigueResult:
    """Complete fatigue verification results."""

    checks: list[FatigueCheckResult]
    governing_detail: str
    governing_utilization: float
    status: str  # "OK" or "FAIL"


# Common fatigue details for crane runway beams
DEFAULT_DETAILS = [
    FatigueDetail(
        name="Base metal at midspan",
        category="A",
        location="Bottom flange at maximum moment section",
    ),
    FatigueDetail(
        name="Welded stiffener termination",
        category="C",
        location="Web-to-flange junction at stiffener end",
    ),
    FatigueDetail(
        name="Cap channel fillet weld",
        category="B",
        location="Longitudinal fillet weld connecting channel to top flange",
    ),
]


def compute_allowable_stress_range(category: str, N: int) -> float:
    """Compute the allowable fatigue stress range FSR for a given detail
    category and number of cycles.

    FSR = max( (Cf / N)^(1/3), FTH )

    Per AISC 360 Appendix 3, Eq. A-3-1.

    Args:
        category: Fatigue detail category ("A" through "E'").
        N: Number of stress cycles.

    Returns:
        Allowable stress range FSR (MPa).
    """
    Cf = FATIGUE_CF.get(category)
    FTH = FATIGUE_THRESHOLD.get(category)

    if Cf is None or FTH is None:
        raise ValueError(f"Unknown fatigue category: {category}")

    FSR_from_N = (Cf / N) ** (1.0 / 3.0) if N > 0 else float("inf")
    return max(FSR_from_N, FTH)


def compute_stress_range(
    M_max_kn_m: float, M_min_kn_m: float, Sx_mm3: float
) -> float:
    """Compute the stress range at a section.

    f_sr = (M_max - M_min) / Sx

    Args:
        M_max_kn_m: Maximum moment at the detail (kN·m).
        M_min_kn_m: Minimum moment at the detail (kN·m). Usually 0 or
                    self-weight moment only.
        Sx_mm3: Elastic section modulus (mm^3).

    Returns:
        Stress range (MPa).
    """
    delta_M = abs(M_max_kn_m - M_min_kn_m) * 1e6  # Convert kN·m to N·mm
    return delta_M / Sx_mm3


def check_fatigue(
    service_class: str,
    M_max_kn_m: float,
    M_min_kn_m: float,
    Sx_mm3: float,
    details: list[FatigueDetail] | None = None,
) -> FatigueResult:
    """Perform fatigue verification for all relevant details.

    Args:
        service_class: CMAA crane service class ("A" through "F").
        M_max_kn_m: Maximum moment (live + dead) at the critical section (kN·m).
        M_min_kn_m: Minimum moment (dead load only) at the critical section (kN·m).
        Sx_mm3: Elastic section modulus (mm^3).
        details: List of fatigue details to check. Uses defaults if None.

    Returns:
        FatigueResult with all detail checks.
    """
    if details is None:
        details = DEFAULT_DETAILS

    N = FATIGUE_CYCLES.get(service_class, 2_000_000)
    f_sr = compute_stress_range(M_max_kn_m, M_min_kn_m, Sx_mm3)

    checks = []
    for detail in details:
        FSR = compute_allowable_stress_range(detail.category, N)
        FTH = FATIGUE_THRESHOLD[detail.category]
        util = f_sr / FSR if FSR > 0 else float("inf")
        status = "OK" if util <= 1.0 else "FAIL"

        checks.append(FatigueCheckResult(
            detail=detail,
            f_sr_mpa=f_sr,
            F_SR_mpa=FSR,
            F_TH_mpa=FTH,
            N_cycles=N,
            utilization=util,
            status=status,
        ))

    # Find governing detail
    if checks:
        worst = max(checks, key=lambda c: c.utilization)
        governing_detail = worst.detail.name
        governing_util = worst.utilization
        overall_status = "FAIL" if governing_util > 1.0 else "OK"
    else:
        governing_detail = "None"
        governing_util = 0.0
        overall_status = "OK"

    return FatigueResult(
        checks=checks,
        governing_detail=governing_detail,
        governing_utilization=governing_util,
        status=overall_status,
    )
