"""Crane Runway Beam Calculator - Streamlit Application.

Structural design of crane runway beams (vigas carrileras) per
AISC 360 / CIRSOC 301-2005.
"""

import sys
import os

import streamlit as st
import plotly.graph_objects as go

# Ensure src is importable
sys.path.insert(0, os.path.dirname(__file__))

from src.models.crane import CraneData
from src.models.beam import RunwayBeam, SectionType
from src.models.materials import MATERIAL_CATALOG
from src.models.profiles import get_w_profiles, get_channel_profiles
from src.design.design_runner import run_design

st.set_page_config(
    page_title="Crane Runway Beam Calculator",
    page_icon="\U0001F3D7",
    layout="wide",
)

st.title("Crane Runway Beam Calculator")
st.markdown(
    "Structural design of crane runway beams (vigas carrileras) "
    "per **AISC 360 / CIRSOC 301-2005**"
)

# --- Load profile databases ---
w_profiles = get_w_profiles()
c_profiles = get_channel_profiles()

# ============================================================
# SIDEBAR - INPUT PARAMETERS
# ============================================================
st.sidebar.header("Crane Data")

capacity_ton = st.sidebar.number_input(
    "Lifting Capacity (ton)", min_value=1.0, max_value=500.0, value=10.0, step=1.0
)
bridge_weight = st.sidebar.number_input(
    "Bridge Weight (kN)", min_value=1.0, max_value=5000.0, value=80.0, step=5.0
)
trolley_weight = st.sidebar.number_input(
    "Trolley Weight (kN)", min_value=1.0, max_value=1000.0, value=20.0, step=1.0
)
bridge_span = st.sidebar.number_input(
    "Bridge Span (m)", min_value=3.0, max_value=50.0, value=15.0, step=0.5
)
wheel_spacing = st.sidebar.number_input(
    "Wheel Spacing (m)", min_value=0.5, max_value=10.0, value=3.0, step=0.1
)
num_wheels = st.sidebar.selectbox(
    "Wheels per Rail", options=[1, 2, 4], index=1
)
service_class = st.sidebar.selectbox(
    "CMAA Service Class",
    options=["A", "B", "C", "D", "E", "F"],
    index=2,
    help="A=Standby, B=Light, C=Moderate, D=Heavy, E=Severe, F=Continuous",
)
min_approach = st.sidebar.number_input(
    "Min. Trolley Approach (m)", min_value=0.0, max_value=10.0, value=1.0, step=0.1
)

st.sidebar.header("Beam Geometry")

beam_span = st.sidebar.number_input(
    "Beam Span (m)", min_value=3.0, max_value=30.0, value=8.0, step=0.5
)
lb_spacing = st.sidebar.number_input(
    "Lateral Bracing Spacing (m)", min_value=1.0, max_value=30.0, value=8.0, step=0.5,
    help="Unbraced length Lb. Set equal to beam span if no intermediate bracing.",
)

st.sidebar.header("Material")

material_name = st.sidebar.selectbox(
    "Steel Grade", options=list(MATERIAL_CATALOG.keys()), index=2
)
material = MATERIAL_CATALOG[material_name]
st.sidebar.info(f"Fy = {material.Fy:.0f} MPa | Fu = {material.Fu:.0f} MPa")

st.sidebar.header("Section Selection")

section_type = st.sidebar.selectbox(
    "Section Type",
    options=["W Shape (Light)", "W + Channel (Medium)", "Built-up (Heavy)"],
    index=0,
)

section_type_map = {
    "W Shape (Light)": SectionType.W_SHAPE,
    "W + Channel (Medium)": SectionType.W_WITH_CHANNEL,
    "Built-up (Heavy)": SectionType.BUILT_UP,
}
selected_section_type = section_type_map[section_type]

main_profile_name = st.sidebar.selectbox(
    "Main W Profile", options=list(w_profiles.keys()), index=6  # Default ~W18x50
)
main_profile = w_profiles[main_profile_name]

cap_channel = None
if selected_section_type == SectionType.W_WITH_CHANNEL:
    channel_name = st.sidebar.selectbox(
        "Cap Channel", options=list(c_profiles.keys()), index=2
    )
    cap_channel = c_profiles[channel_name]

# ============================================================
# RUN DESIGN
# ============================================================
if st.sidebar.button("Run Design", type="primary", use_container_width=True):
    crane = CraneData(
        capacity_ton=capacity_ton,
        bridge_weight_kn=bridge_weight,
        trolley_weight_kn=trolley_weight,
        bridge_span_m=bridge_span,
        wheel_spacing_m=wheel_spacing,
        num_wheels_per_rail=num_wheels,
        service_class=service_class,
        min_approach_m=min_approach,
    )

    beam = RunwayBeam(
        span_m=beam_span,
        lateral_bracing_spacing_m=lb_spacing,
        section_type=selected_section_type,
        main_profile=main_profile,
        material=material,
        cap_channel=cap_channel,
    )

    result = run_design(crane, beam)

    # Store in session state so it persists
    st.session_state["result"] = result

# ============================================================
# DISPLAY RESULTS
# ============================================================
if "result" in st.session_state:
    result = st.session_state["result"]

    # --- Wheel Loads Summary ---
    st.header("1. Wheel Loads")
    wl = result.wheel_loads

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Wheel Load (kN)", f"{wl.P_wheel_max_kn:.1f}")
        st.metric("Impact Factor", f"{wl.impact_factor:.0%}")
    with col2:
        st.metric("Lateral Force/wheel (kN)", f"{wl.H_lateral_per_wheel_kn:.1f}")
        st.metric("Total Lateral (kN)", f"{wl.H_lateral_total_kn:.1f}")
    with col3:
        st.metric("Longitudinal Force (kN)", f"{wl.H_longitudinal_kn:.1f}")
        st.metric("Max Static Reaction (kN)", f"{wl.R_max_static_kn:.1f}")

    # --- Beam Analysis ---
    st.header("2. Beam Analysis")
    forces = result.beam_forces

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Max Moment Mu_x (kN\u00b7m)", f"{forces.M_max_kn_m:.1f}")
    with col2:
        st.metric("Max Shear Vu (kN)", f"{forces.V_max_kn:.1f}")

    # Moment diagram
    fig_m = go.Figure()
    fig_m.add_trace(go.Scatter(
        x=forces.x_positions_m,
        y=forces.M_envelope_kn_m,
        mode="lines",
        fill="tozeroy",
        name="Moment Envelope",
        line=dict(color="royalblue"),
    ))
    fig_m.update_layout(
        title="Moment Envelope (kN\u00b7m)",
        xaxis_title="Position (m)",
        yaxis_title="Moment (kN\u00b7m)",
        height=350,
    )
    st.plotly_chart(fig_m, use_container_width=True)

    # Shear diagram
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(
        x=forces.x_positions_m,
        y=forces.V_envelope_kn_m,
        mode="lines",
        fill="tozeroy",
        name="Shear Envelope",
        line=dict(color="firebrick"),
    ))
    fig_v.update_layout(
        title="Shear Envelope (kN)",
        xaxis_title="Position (m)",
        yaxis_title="Shear (kN)",
        height=350,
    )
    st.plotly_chart(fig_v, use_container_width=True)

    # --- Verification Results ---
    st.header("3. Design Verifications")

    # Summary table
    status_icon = {"OK": "\u2705", "FAIL": "\u274C"}

    data_rows = []
    checks = [
        ("Biaxial Bending (H1)", result.flexure.interaction_ratio, result.flexure.status),
        ("Shear (G2)", result.shear.utilization, result.shear.status),
        ("Web Yielding (J10.2)", result.web_yielding_crippling.util_yielding,
         result.web_yielding_crippling.status_yielding),
        ("Web Crippling (J10.3)", result.web_yielding_crippling.util_crippling,
         result.web_yielding_crippling.status_crippling),
        ("Fatigue (App. 3)", result.fatigue.governing_utilization, result.fatigue.status),
        ("Vertical Deflection", result.serviceability.util_vertical,
         result.serviceability.status_vertical),
        ("Horizontal Deflection", result.serviceability.util_horizontal,
         result.serviceability.status_horizontal),
    ]

    for name, util, status in checks:
        data_rows.append({
            "Limit State": name,
            "Utilization": f"{util:.3f}",
            "Ratio (%)": f"{util * 100:.1f}%",
            "Status": f"{status_icon.get(status, '?')} {status}",
        })

    st.table(data_rows)

    # Overall result
    if result.overall_status == "OK":
        st.success(
            f"**DESIGN OK** \u2014 Governing: {result.governing_limit_state} "
            f"({result.max_utilization:.1%})"
        )
    else:
        st.error(
            f"**DESIGN FAILS** \u2014 Governing: {result.governing_limit_state} "
            f"({result.max_utilization:.1%})"
        )

    # --- Detailed Results (Expanders) ---
    with st.expander("Flexure Details"):
        f = result.flexure
        st.write(f"**LTB Zone:** {f.ltb_zone}")
        st.write(f"**Lp:** {f.Lp_mm:.0f} mm | **Lr:** {f.Lr_mm:.0f} mm | "
                 f"**Lb:** {result.beam.Lb_mm:.0f} mm")
        st.write(f"**\u03c6Mn_x:** {f.phi_Mn_x_kn_m:.1f} kN\u00b7m | "
                 f"**Mu_x:** {f.Mu_x_kn_m:.1f} kN\u00b7m")
        st.write(f"**\u03c6Mn_y:** {f.phi_Mn_y_kn_m:.1f} kN\u00b7m | "
                 f"**Mu_y:** {f.Mu_y_kn_m:.1f} kN\u00b7m")
        st.write(f"**Interaction ratio:** {f.interaction_ratio:.3f}")

    with st.expander("Shear Details"):
        s = result.shear
        st.write(f"**Cv1:** {s.Cv1:.3f} | **h/tw:** {s.h_tw_ratio:.1f}")
        st.write(f"**\u03c6Vn:** {s.phi_Vn_kn:.1f} kN | **Vu:** {s.Vu_kn:.1f} kN")

    with st.expander("Web Local Effects"):
        w = result.web_yielding_crippling
        st.write(f"**Web Yielding \u03c6Rn:** {w.phi_Rn_yielding_kn:.1f} kN | "
                 f"**Pu:** {w.Pu_kn:.1f} kN | Util: {w.util_yielding:.3f}")
        st.write(f"**Web Crippling \u03c6Rn:** {w.phi_Rn_crippling_kn:.1f} kN | "
                 f"**Pu:** {w.Pu_kn:.1f} kN | Util: {w.util_crippling:.3f}")

    with st.expander("Fatigue Details"):
        fat = result.fatigue
        for chk in fat.checks:
            st.write(
                f"**{chk.detail.name}** (Cat. {chk.detail.category}): "
                f"f_sr = {chk.f_sr_mpa:.1f} MPa, "
                f"F_SR = {chk.F_SR_mpa:.1f} MPa, "
                f"Util = {chk.utilization:.3f} {status_icon.get(chk.status, '')}"
            )
        st.write(f"Design cycles N = {fat.checks[0].N_cycles:,}" if fat.checks else "")

    with st.expander("Serviceability Details"):
        sv = result.serviceability
        st.write(f"**Vertical:** \u03b4 = {sv.delta_v_mm:.2f} mm | "
                 f"Limit = L/{int(result.beam.span_mm / sv.delta_v_limit_mm) if sv.delta_v_limit_mm > 0 else 0}"
                 f" = {sv.delta_v_limit_mm:.2f} mm")
        st.write(f"**Horizontal:** \u03b4 = {sv.delta_h_mm:.2f} mm | "
                 f"Limit = L/{int(result.beam.span_mm / sv.delta_h_limit_mm) if sv.delta_h_limit_mm > 0 else 0}"
                 f" = {sv.delta_h_limit_mm:.2f} mm")

else:
    st.info("Configure parameters in the sidebar and click **Run Design** to start.")
