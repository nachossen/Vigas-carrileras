"""Crane data model."""

from dataclasses import dataclass

from src.utils.constants import IMPACT_FACTORS, KN_PER_TON


@dataclass
class CraneData:
    """Bridge crane operational and geometric data.

    Attributes:
        capacity_ton: Lifting capacity in metric tons.
        bridge_weight_kn: Total bridge weight in kN.
        trolley_weight_kn: Trolley (carro) weight in kN.
        bridge_span_m: Span of the bridge crane in meters.
        wheel_spacing_m: Distance between runway wheels on the same rail in meters.
        num_wheels_per_rail: Number of wheels per end truck on one rail (typically 2).
        service_class: CMAA crane service classification ("A" through "F").
        min_approach_m: Minimum trolley approach distance to the runway beam (m).
            If None, assumes trolley can reach directly above the rail.
    """

    capacity_ton: float
    bridge_weight_kn: float
    trolley_weight_kn: float
    bridge_span_m: float
    wheel_spacing_m: float
    num_wheels_per_rail: int = 2
    service_class: str = "C"
    min_approach_m: float = 0.0

    @property
    def lifted_load_kn(self) -> float:
        """Lifted load in kN."""
        return self.capacity_ton * KN_PER_TON

    @property
    def impact_factor(self) -> float:
        """Vertical impact factor based on CMAA service class."""
        return IMPACT_FACTORS.get(self.service_class, 0.25)

    def __post_init__(self):
        valid_classes = set(IMPACT_FACTORS.keys())
        if self.service_class not in valid_classes:
            raise ValueError(
                f"Invalid service class '{self.service_class}'. "
                f"Must be one of {sorted(valid_classes)}"
            )
        if self.num_wheels_per_rail < 1:
            raise ValueError("num_wheels_per_rail must be >= 1")
