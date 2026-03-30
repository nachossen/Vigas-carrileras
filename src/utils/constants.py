"""Physical and engineering constants for structural calculations."""

# Elastic modulus of steel (MPa)
E_STEEL = 200_000.0

# Shear modulus of steel (MPa)
G_STEEL = 77_200.0

# Gravity acceleration (m/s^2)
GRAVITY = 9.81

# Unit conversions
KN_PER_TON = 9.81  # 1 metric ton = 9.81 kN
MM_PER_M = 1000.0
M_PER_MM = 0.001

# LRFD resistance factors (phi)
PHI_FLEXURE = 0.90
PHI_SHEAR = 0.90
PHI_COMPRESSION = 0.90
PHI_WEB_YIELDING = 1.00
PHI_WEB_CRIPPLING = 0.75

# Impact factors by CMAA service class (ASCE 7 / AISC DG7)
IMPACT_FACTORS = {
    "A": 0.00,  # Standby / infrequent use
    "B": 0.10,  # Light service
    "C": 0.20,  # Moderate service
    "D": 0.25,  # Heavy service
    "E": 0.25,  # Severe service
    "F": 0.25,  # Continuous severe service
}

# Lateral force coefficient (fraction of lifted load + trolley weight)
LATERAL_FORCE_COEFF = 0.20

# Longitudinal force coefficient (fraction of max wheel loads)
LONGITUDINAL_FORCE_COEFF = 0.10

# Deflection limits (span / limit)
VERTICAL_DEFLECTION_LIMIT = 600    # L/600 for crane beams (AISC DG7)
HORIZONTAL_DEFLECTION_LIMIT = 400  # L/400

# Fatigue: design cycles by CMAA service class
FATIGUE_CYCLES = {
    "A": 20_000,
    "B": 100_000,
    "C": 500_000,
    "D": 2_000_000,
    "E": 2_000_000,
    "F": 2_000_000,
}

# Fatigue threshold stress ranges (MPa) by detail category
# AISC 360 Table A-3.1 - Threshold FTH values
FATIGUE_THRESHOLD = {
    "A":  165.0,
    "B":  110.0,
    "B'": 83.0,
    "C":  69.0,
    "D":  48.0,
    "E":  31.0,
    "E'": 18.0,
}

# Fatigue constant Cf for S-N curves (MPa^3)
# FSR = (Cf / N)^(1/3) but must be >= FTH
FATIGUE_CF = {
    "A":  250e8,
    "B":  120e8,
    "B'": 61e8,
    "C":  44e8,
    "D":  22e8,
    "E":  11e8,
    "E'": 3.9e8,
}
