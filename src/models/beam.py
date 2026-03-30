"""Runway beam (viga carrilera) data model."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.models.materials import SteelMaterial
from src.models.profiles import SteelProfile


class SectionType(Enum):
    """Cross-section typology for crane runway beams."""

    W_SHAPE = "w_shape"               # Light duty: simple W shape
    W_WITH_CHANNEL = "w_with_channel"  # Medium duty: W + cap channel
    BUILT_UP = "built_up"             # Heavy duty: welded plate girder


@dataclass
class RunwayBeam:
    """Crane runway beam definition.

    Attributes:
        span_m: Beam span in meters.
        lateral_bracing_spacing_m: Unbraced length Lb in meters.
        section_type: Cross-section typology.
        main_profile: Primary W shape or built-up section.
        material: Steel material properties.
        cap_channel: Optional channel welded on top flange (for W_WITH_CHANNEL type).
    """

    span_m: float
    lateral_bracing_spacing_m: float
    section_type: SectionType
    main_profile: SteelProfile
    material: SteelMaterial
    cap_channel: Optional[SteelProfile] = None

    def __post_init__(self):
        if self.section_type == SectionType.W_WITH_CHANNEL and self.cap_channel is None:
            raise ValueError(
                "cap_channel is required for W_WITH_CHANNEL section type"
            )

    @property
    def span_mm(self) -> float:
        """Beam span in mm."""
        return self.span_m * 1000.0

    @property
    def Lb_mm(self) -> float:
        """Unbraced length in mm."""
        return self.lateral_bracing_spacing_m * 1000.0
