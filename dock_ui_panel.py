"""
Wiederverwendbares Streamlit-UI-Panel für eine einzelne Tor-Zuordnungs-
Heuristik: Kennzahlen, Hallengrundriss, PDF-Export.
"""

import streamlit as st

from dock_visualization import FLOW_LINE_CAPTION, FULL_WIDTH_PX, HOT_LANE_CAPTION, LABEL_DENSITY_CAPTION, build_hall_figure


def render_assignment_panel(prefix, label, assignment, positions, flow, hall_width, hall_depth, hot_lane_idxs, stats, pdf_bytes, width_hint_px=FULL_WIDTH_PX):
    m1, m2 = st.columns(2)
    m1.metric("Ø Distanz je Bewegung", f"{stats['avg_distance_per_move']:.1f} m")
    m2.metric("Gewichtete Gesamtdistanz", f"{stats['total_weighted_distance']:.0f} m·Bew./Tag")

    fig = build_hall_figure(positions, assignment, flow, hall_width, hall_depth, hot_lane_idxs, width_hint_px=width_hint_px)
    st.plotly_chart(fig, width="stretch", key=f"{prefix}_plot")
    st.caption(f"{HOT_LANE_CAPTION} {FLOW_LINE_CAPTION} {LABEL_DENSITY_CAPTION}")

    st.download_button(
        "📄 Tor-Zuordnungsplan als PDF herunterladen", data=pdf_bytes,
        file_name=f"tor_zuordnung_{prefix}.pdf", mime="application/pdf", key=f"{prefix}_pdf_download",
    )

    return {"label": label, "assignment": assignment, **stats}
