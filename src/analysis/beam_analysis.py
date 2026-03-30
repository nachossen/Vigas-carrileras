"""Simply supported beam analysis with moving concentrated loads.

Handles wheel positioning for maximum moment and shear, and computes
deflections using elastic beam theory.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class BeamForces:
    """Internal forces and deflections at the critical section."""

    # Maximum values
    M_max_kn_m: float       # Maximum bending moment (kN·m)
    V_max_kn: float         # Maximum shear force (kN)
    x_Mmax_m: float         # Position of max moment from left support (m)

    # Moment and shear envelopes (for plotting)
    x_positions_m: np.ndarray   # Positions along beam (m)
    M_envelope_kn_m: np.ndarray  # Moment envelope (kN·m)
    V_envelope_kn_m: np.ndarray  # Shear envelope (kN·m)

    # Maximum deflection (mm) - computed later with section properties
    delta_max_mm: float = 0.0


def max_moment_two_wheels(
    P: float, s: float, L: float
) -> tuple[float, float]:
    """Find maximum moment for two equal concentrated loads on a simple beam.

    Uses the theorem of the resultant: the maximum moment under one of the
    loads occurs when the midpoint of the beam coincides with the midpoint
    between the resultant of all loads and the nearest concentrated load.

    For two equal loads P separated by distance s on span L:
    - The resultant R=2P is at the midpoint between the wheels.
    - Maximum moment occurs when one wheel is at x = L/2 - s/4.

    Args:
        P: Load magnitude per wheel (kN).
        s: Spacing between wheels (m).
        L: Beam span (m).

    Returns:
        (M_max, x_critical): Maximum moment (kN·m) and position from left (m).
    """
    if s >= L:
        # Wheels don't both fit on the beam; single wheel at midspan
        M_max = P * L / 4.0
        return M_max, L / 2.0

    # Critical position of the left wheel (wheel closer to left support)
    # For max moment under the RIGHT wheel:
    # Place right wheel at x_right = L/2 + s/4
    # Then left wheel is at x_left = L/2 + s/4 - s = L/2 - 3s/4
    # Reaction at A: R_A = P*(L - x_left)/L + P*(L - x_right)/L
    #              = P*(2L - x_left - x_right)/L = P*(2L - (L - s/4))/L ... nope
    # Let's do it properly:

    # Position right wheel for max moment under it
    x_right = L / 2.0 + s / 4.0
    x_left = x_right - s

    if x_left < 0:
        # Left wheel falls off; only right wheel on beam
        x_right = L / 2.0
        R_A = P * (L - x_right) / L
        M_under_right = R_A * x_right
        return M_under_right, x_right

    # Both wheels on beam
    R_A = P * (L - x_left) / L + P * (L - x_right) / L

    # Moment under the right wheel
    M_under_right = R_A * x_right - P * s  # P*(x_right - x_left) = P*s
    # More precisely:
    M_under_right = R_A * x_right - P * (x_right - x_left)

    # Also check moment under the left wheel (by symmetry, place left wheel
    # at L/2 - s/4)
    x_left_alt = L / 2.0 - s / 4.0
    x_right_alt = x_left_alt + s

    if x_right_alt > L:
        R_A_alt = P * (L - x_left_alt) / L
        M_under_left = R_A_alt * x_left_alt
    else:
        R_A_alt = P * (L - x_left_alt) / L + P * (L - x_right_alt) / L
        M_under_left = R_A_alt * x_left_alt

    if M_under_left > M_under_right:
        return M_under_left, x_left_alt
    else:
        return M_under_right, x_right


def max_shear_two_wheels(P: float, s: float, L: float) -> float:
    """Maximum shear for two equal loads: one wheel at the support.

    Args:
        P: Load per wheel (kN).
        s: Wheel spacing (m).
        L: Beam span (m).

    Returns:
        Maximum shear reaction (kN).
    """
    if s >= L:
        return P  # Only one wheel on beam
    # Left wheel at x=0 (at support), right wheel at x=s
    V_max = P + P * (L - s) / L
    return V_max


def compute_moment_envelope(
    P: float, s: float, L: float, n_points: int = 200
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the moment envelope for two moving loads.

    For each position along the beam, find the maximum moment that can
    occur at that section from any position of the two-wheel group.

    Args:
        P: Wheel load (kN).
        s: Wheel spacing (m).
        L: Beam span (m).
        n_points: Number of evaluation points.

    Returns:
        (x_array, M_envelope): Arrays of positions (m) and max moments (kN·m).
    """
    x = np.linspace(0, L, n_points)
    M_env = np.zeros(n_points)

    # Sweep wheel group position: left wheel at position 'a'
    for i, xi in enumerate(x):
        M_max_at_xi = 0.0

        # Case 1: Left wheel at various positions, evaluate moment at xi
        a_values = np.linspace(0, L, 500)
        for a in a_values:
            # Left wheel at 'a', right wheel at 'a + s'
            b = a + s

            # Compute reaction at left support
            R_A = 0.0
            loads_on_beam = []
            if 0 <= a <= L:
                R_A += P * (L - a) / L
                loads_on_beam.append(a)
            if 0 <= b <= L:
                R_A += P * (L - b) / L
                loads_on_beam.append(b)

            if not loads_on_beam:
                continue

            # Moment at section xi
            M = R_A * xi
            for load_pos in loads_on_beam:
                if load_pos < xi:
                    M -= P * (xi - load_pos)

            M_max_at_xi = max(M_max_at_xi, M)

        M_env[i] = M_max_at_xi

    return x, M_env


def compute_shear_envelope(
    P: float, s: float, L: float, n_points: int = 200
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the shear envelope for two moving loads.

    Args:
        P: Wheel load (kN).
        s: Wheel spacing (m).
        L: Beam span (m).
        n_points: Number of evaluation points.

    Returns:
        (x_array, V_envelope): Arrays of positions (m) and max shear (kN).
    """
    x = np.linspace(0, L, n_points)
    V_env = np.zeros(n_points)

    a_values = np.linspace(-s, L, 500)
    for i, xi in enumerate(x):
        V_max_at_xi = 0.0
        for a in a_values:
            b = a + s
            R_A = 0.0
            loads_on_beam = []
            if 0 <= a <= L:
                R_A += P * (L - a) / L
                loads_on_beam.append(a)
            if 0 <= b <= L:
                R_A += P * (L - b) / L
                loads_on_beam.append(b)

            if not loads_on_beam:
                continue

            # Shear just to the right of xi
            V = R_A
            for load_pos in loads_on_beam:
                if load_pos <= xi:
                    V -= P

            V_max_at_xi = max(V_max_at_xi, abs(V))

        V_env[i] = V_max_at_xi

    return x, V_env


def compute_deflection_two_wheels(
    P_kn: float, s_m: float, L_m: float, E_mpa: float, I_mm4: float
) -> float:
    """Compute maximum deflection for two equal concentrated loads.

    Uses superposition of deflections from each load, evaluated at midspan.
    For a simply supported beam with point load P at distance 'a' from
    left support:
        delta(x) = P*b*x/(6*E*I*L) * (L^2 - b^2 - x^2)  for x <= a
    where b = L - a.

    Args:
        P_kn: Wheel load (kN).
        s_m: Wheel spacing (m).
        L_m: Beam span (m).
        E_mpa: Elastic modulus (MPa = N/mm^2).
        I_mm4: Moment of inertia (mm^4).

    Returns:
        Maximum deflection at midspan (mm).
    """
    P = P_kn * 1000.0  # Convert kN to N
    L = L_m * 1000.0   # Convert m to mm
    s = s_m * 1000.0

    x_mid = L / 2.0

    def deflection_at_x(P_load: float, a: float, x: float) -> float:
        """Deflection at x for load P at distance a from left support."""
        b = L - a
        if a <= 0 or a >= L:
            return 0.0
        if x <= a:
            return P_load * b * x / (6.0 * E_mpa * I_mm4 * L) * (
                L**2 - b**2 - x**2
            )
        else:
            # Use symmetry: swap roles
            return P_load * a * (L - x) / (6.0 * E_mpa * I_mm4 * L) * (
                L**2 - a**2 - (L - x) ** 2
            )

    # Position wheels symmetrically about midspan for maximum deflection
    a1 = x_mid - s / 2.0
    a2 = x_mid + s / 2.0

    if a1 < 0:
        a1 = 0
        a2 = s

    delta = deflection_at_x(P, a1, x_mid) + deflection_at_x(P, a2, x_mid)
    return delta


def analyze_beam(
    P_wheel_kn: float,
    wheel_spacing_m: float,
    span_m: float,
    w_self_kn_m: float = 0.0,
) -> BeamForces:
    """Full beam analysis for a crane runway beam.

    Args:
        P_wheel_kn: Maximum wheel load (kN).
        wheel_spacing_m: Distance between wheels (m).
        span_m: Beam span (m).
        w_self_kn_m: Self-weight distributed load (kN/m).

    Returns:
        BeamForces with all computed values.
    """
    L = span_m
    P = P_wheel_kn
    s = wheel_spacing_m

    # Maximum moment from wheel loads
    M_wheels, x_Mmax = max_moment_two_wheels(P, s, L)

    # Self-weight moment at the same section
    M_self = w_self_kn_m * x_Mmax * (L - x_Mmax) / 2.0

    M_max = M_wheels + M_self

    # Maximum shear from wheel loads + self-weight
    V_wheels = max_shear_two_wheels(P, s, L)
    V_self = w_self_kn_m * L / 2.0
    V_max = V_wheels + V_self

    # Envelopes
    x_env, M_env = compute_moment_envelope(P, s, L)
    # Add self-weight moment to envelope
    M_self_env = w_self_kn_m * x_env * (L - x_env) / 2.0
    M_env = M_env + M_self_env

    _, V_env = compute_shear_envelope(P, s, L)
    # Add self-weight shear to envelope (approximate)
    V_self_env = np.abs(w_self_kn_m * (L / 2.0 - x_env))
    V_env = V_env + V_self_env

    return BeamForces(
        M_max_kn_m=M_max,
        V_max_kn=V_max,
        x_Mmax_m=x_Mmax,
        x_positions_m=x_env,
        M_envelope_kn_m=M_env,
        V_envelope_kn_m=V_env,
    )
