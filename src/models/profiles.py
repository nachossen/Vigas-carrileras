"""Steel profile definitions and database loader."""

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SteelProfile:
    """Steel cross-section properties. All dimensions in mm, areas in mm^2,
    moments of inertia in mm^4, section moduli in mm^3, Cw in mm^6."""

    name: str
    profile_type: str  # "W", "C", "built_up"
    d: float       # Overall depth (mm)
    bf: float      # Flange width (mm)
    tf: float      # Flange thickness (mm)
    tw: float      # Web thickness (mm)
    Ix: float      # Strong-axis moment of inertia (mm^4)
    Iy: float      # Weak-axis moment of inertia (mm^4)
    Sx: float      # Strong-axis elastic section modulus (mm^3)
    Sy: float      # Weak-axis elastic section modulus (mm^3)
    Zx: float      # Strong-axis plastic section modulus (mm^3)
    Zy: float      # Weak-axis plastic section modulus (mm^3)
    A: float       # Cross-sectional area (mm^2)
    J: float       # Torsional constant (mm^4)
    Cw: float      # Warping constant (mm^6)
    rts: float     # Effective radius of gyration for LTB (mm)
    ho: float      # Distance between flange centroids (mm)
    k: float       # Distance from outer face of flange to web toe of fillet (mm)
    weight_kg_m: float  # Linear weight (kg/m)
    ry: Optional[float] = None  # Weak-axis radius of gyration (mm)

    def __post_init__(self):
        if self.ry is None:
            self.ry = (self.Iy / self.A) ** 0.5


def load_profiles_from_json(filepath: str) -> dict[str, SteelProfile]:
    """Load steel profiles from a JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)

    profiles = {}
    for entry in data:
        profile = SteelProfile(**entry)
        profiles[profile.name] = profile
    return profiles


def get_profile_database() -> dict[str, SteelProfile]:
    """Load the default AISC profile database."""
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "aisc_profiles.json",
    )
    return load_profiles_from_json(db_path)


def get_w_profiles() -> dict[str, SteelProfile]:
    """Return only W-shape profiles."""
    return {k: v for k, v in get_profile_database().items() if v.profile_type == "W"}


def get_channel_profiles() -> dict[str, SteelProfile]:
    """Return only channel profiles."""
    return {k: v for k, v in get_profile_database().items() if v.profile_type == "C"}
