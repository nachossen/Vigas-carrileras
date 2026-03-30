"""Design runner: orchestrates all structural verifications.

Runs all AISC 360 / CIRSOC 301 checks and produces a consolidated report.
"""

from dataclasses import dataclass, field

from src.analysis.beam_analysis import analyze_beam, BeamForces
from src.design.fatigue import FatigueResult, check_fatigue, DEFAULT_DETAILS
from src.design.flexure import FlexureResult, check_biaxial_bending
from src.design.serviceability import ServiceabilityResult, check_serviceability
from src.design.shear import ShearResult, check_shear
from src.design.web_local import WebLocalResult, check_web_local
from src.loads.load_generator import WheelLoads, compute_wheel_loads
from src.models.beam import RunwayBeam, SectionType
from src.models.crane import CraneData
from src.utils.constants import GRAVITY


@dataclass
class DesignResult:
    """Consolidated design verification results."""

    # Input summary
    crane: CraneData
    beam: RunwayBeam
    wheel_loads: WheelLoads

    # Analysis
    beam_forces: BeamForces

    # Verifications
    flexure: FlexureResult
    shear: ShearResult
    web_yielding_crippling: WebLocalResult
    fatigue: FatigueResult
    serviceability: ServiceabilityResult

    # Summary
    governing_limit_state: str = ""
    max_utilization: float = 0.0
    overall_status: str = "OK"

    utilization_summary: dict = field(default_factory=dict)

    def __post_init__(self):
        self.utilization_summary = {
            "Biaxial Bending": self.flexure.interaction_ratio,
            "Shear": self.shear.utilization,
            "Web Yielding": self.web_yielding_crippling.util_yielding,
            "Web Crippling": self.web_yielding_crippling.util_crippling,
            "Fatigue": self.fatigue.governing_utilization,
            "Vertical Deflection": self.serviceability.util_vertical,
            "Horizontal Deflection": self.serviceability.util_horizontal,
        }

        self.max_utilization = max(self.utilization_summary.values())
        self.governing_limit_state = max(
            self.utilization_summary, key=self.utilization_summary.get
        )
        self.overall_status = "OK" if self.max_utilization <= 1.0 else "FAIL"


def run_design(crane: CraneData, beam: RunwayBeam) -> DesignResult:
    """Execute the complete design verification sequence.

    Args:
        crane: Crane operational data.
        beam: Runway beam definition.

    Returns:
        DesignResult with all verification results.
    """
    profile = beam.main_profile

    # 1. Compute wheel loads
    wheel_loads = compute_wheel_loads(crane)

    # Beam self-weight (kN/m)
    w_self = profile.weight_kg_m * GRAVITY / 1000.0  # kg/m -> kN/m

    # 2. Structural analysis - vertical
    forces = analyze_beam(
        P_wheel_kn=wheel_loads.P_wheel_max_kn,
        wheel_spacing_m=crane.wheel_spacing_m,
        span_m=beam.span_m,
        w_self_kn_m=w_self,
    )

    # 3. Lateral analysis (weak-axis moment)
    # Lateral wheel load produces weak-axis bending
    # Use same beam model but with lateral load
    forces_lateral = analyze_beam(
        P_wheel_kn=wheel_loads.H_lateral_per_wheel_kn,
        wheel_spacing_m=crane.wheel_spacing_m,
        span_m=beam.span_m,
        w_self_kn_m=0.0,
    )

    Mu_x = forces.M_max_kn_m
    Mu_y = forces_lateral.M_max_kn_m

    # 4. Flexure check (biaxial bending)
    flexure_result = check_biaxial_bending(beam, Mu_x, Mu_y)

    # 5. Shear check
    shear_result = check_shear(beam, forces.V_max_kn)

    # 6. Web local effects (concentrated wheel load)
    web_result = check_web_local(
        beam=beam,
        Pu_kn=wheel_loads.P_wheel_max_kn,
        lb_mm=100.0,  # Typical rail base width
        at_end=False,
    )

    # 7. Fatigue check
    # Minimum moment = dead load only moment at critical section
    M_min_dead = w_self * forces.x_Mmax_m * (beam.span_m - forces.x_Mmax_m) / 2.0

    # Select appropriate fatigue details based on section type
    if beam.section_type == SectionType.W_WITH_CHANNEL:
        details = DEFAULT_DETAILS  # Includes cap channel weld
    else:
        details = [d for d in DEFAULT_DETAILS if "channel" not in d.name.lower()]

    fatigue_result = check_fatigue(
        service_class=crane.service_class,
        M_max_kn_m=Mu_x,
        M_min_kn_m=M_min_dead,
        Sx_mm3=profile.Sx,
        details=details,
    )

    # 8. Serviceability check (service loads = unfactored)
    # Service wheel load = static wheel load (no impact for deflection)
    P_service = wheel_loads.R_max_static_kn / crane.num_wheels_per_rail
    H_service = wheel_loads.H_lateral_per_wheel_kn  # Already unfactored

    svc_result = check_serviceability(
        beam=beam,
        P_service_kn=P_service,
        H_service_kn=H_service,
        wheel_spacing_m=crane.wheel_spacing_m,
    )

    return DesignResult(
        crane=crane,
        beam=beam,
        wheel_loads=wheel_loads,
        beam_forces=forces,
        flexure=flexure_result,
        shear=shear_result,
        web_yielding_crippling=web_result,
        fatigue=fatigue_result,
        serviceability=svc_result,
    )
