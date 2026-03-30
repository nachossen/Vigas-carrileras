"""Steel material definitions."""

from dataclasses import dataclass

from src.utils.constants import E_STEEL, G_STEEL


@dataclass
class SteelMaterial:
    """Steel material properties."""

    name: str
    Fy: float  # Yield stress (MPa)
    Fu: float  # Ultimate tensile stress (MPa)
    E: float = E_STEEL   # Elastic modulus (MPa)
    G: float = G_STEEL   # Shear modulus (MPa)


# Common steel grades
ASTM_A36 = SteelMaterial(name="ASTM A36", Fy=250.0, Fu=400.0)
ASTM_A572_GR50 = SteelMaterial(name="ASTM A572 Gr.50", Fy=345.0, Fu=450.0)
ASTM_A992 = SteelMaterial(name="ASTM A992", Fy=345.0, Fu=450.0)

# Argentine equivalents (CIRSOC 301-2005)
F24_CIRSOC = SteelMaterial(name="F-24 (CIRSOC)", Fy=240.0, Fu=370.0)
F36_CIRSOC = SteelMaterial(name="F-36 (CIRSOC)", Fy=355.0, Fu=510.0)

MATERIAL_CATALOG = {
    "ASTM A36": ASTM_A36,
    "ASTM A572 Gr.50": ASTM_A572_GR50,
    "ASTM A992": ASTM_A992,
    "F-24 (CIRSOC)": F24_CIRSOC,
    "F-36 (CIRSOC)": F36_CIRSOC,
}
