"""Section 13 — Lynn Maps Overview: all Lynn schools + tract demographics + town context."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import LEHS_GOLD, LEHS_NAVY
from utils.geo_loader import load_geojson, load_geodataframe
from utils.maps import (
    DEFAULT_MAP_LAYOUT,
    LYNN_CENTER,
    choropleth_map,
    lynn_school_marker_size,
    school_points_map,
)

st.set_page_config(
    page_title="Maps — Lynn Overview | LEHS", page_icon="🗺️", layout="wide"
)
sidebar_attribution()

st.title("Lynn — Overview Map")
st.markdown(
    "All schools in Lynn pinned on the city, with Lynn's town outline and "
    "neighboring towns (Swampscott, Saugus, Peabody, Nahant, Lynnfield) for "
    "context. Use the toggle to layer in census tract boundaries."
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

schools = load_geodataframe("lynn_schools")
town = load_geojson("lynn_town")
tracts = load_geojson("lynn_tracts")

if schools.empty:
    st.warning("Lynn GIS data not yet built. Run scripts/09 + 11.")
    st.stop()

# Add LEHS-flag for highlighting (school code 01630510)
schools["is_lehs"] = schools["ORG_CODE"].astype(str).str.zfill(8) == "01630510" \
                     if "ORG_CODE" in schools.columns else False
schools["marker_size"] = schools["TOTAL_CNT"].apply(lynn_school_marker_size) \
                          if "TOTAL_CNT" in schools.columns else 12

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

col_a, col_b, col_c = st.columns([2, 2, 2])
with col_a:
    show_neighbors = st.checkbox("Show neighboring towns outline", value=True)
with col_b:
    show_tracts = st.checkbox("Show Lynn census tracts", value=False)
with col_c:
    color_by = st.selectbox(
        "Color schools by",
        options=["LEHS vs others", "% English Learner", "% Low Income", "% High Needs",
                 "Total enrollment"],
    )

# ---------------------------------------------------------------------------
# Build the map
# ---------------------------------------------------------------------------

color_map = {
    "% English Learner":    "EL_PCT",
    "% Low Income":         "LI_PCT",
    "% High Needs":         "HN_PCT",
    "Total enrollment":     "TOTAL_CNT",
}

if color_by == "LEHS vs others":
    schools["highlight_label"] = schools["is_lehs"].map(
        {True: "Lynn English High", False: "Other Lynn school"}
    )
    fig = px.scatter_mapbox(
        schools, lat="lat", lon="lon",
        color="highlight_label",
        color_discrete_map={"Lynn English High": LEHS_GOLD, "Other Lynn school": LEHS_NAVY},
        size="marker_size", size_max=30,
        hover_name="NAME",
        hover_data={"TYPE_DESC": True, "GRADES": True, "TOTAL_CNT": ":,",
                    "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                    "lat": False, "lon": False, "marker_size": False,
                    "highlight_label": False},
        zoom=12.5, center=LYNN_CENTER,
    )
else:
    col_attr = color_map[color_by]
    plot_df = schools.dropna(subset=[col_attr]).copy()
    fig = px.scatter_mapbox(
        plot_df, lat="lat", lon="lon",
        color=col_attr, color_continuous_scale="Viridis",
        size="marker_size", size_max=30,
        hover_name="NAME",
        hover_data={"TYPE_DESC": True, "GRADES": True, "TOTAL_CNT": ":,",
                    "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                    "lat": False, "lon": False, "marker_size": False},
        zoom=12.5, center=LYNN_CENTER,
    )

fig.update_layout(**DEFAULT_MAP_LAYOUT)

# Add tracts as a layer if toggled
layers = []
if show_tracts and tracts.get("features"):
    layers.append({"source": tracts, "type": "line", "color": "#999", "line": {"width": 1}})
if show_neighbors and town.get("features"):
    # Only neighbors (not Lynn itself, since school dots are already there)
    neighbors_only = {
        "type": "FeatureCollection",
        "features": [f for f in town["features"] if f["properties"].get("TOWN") != "LYNN"],
    }
    layers.append({"source": neighbors_only, "type": "line", "color": LEHS_NAVY,
                   "line": {"width": 1.5}, "opacity": 0.5})
# Lynn outline always on top (thicker)
if town.get("features"):
    lynn_only = {
        "type": "FeatureCollection",
        "features": [f for f in town["features"] if f["properties"].get("TOWN") == "LYNN"],
    }
    layers.append({"source": lynn_only, "type": "line", "color": LEHS_GOLD,
                   "line": {"width": 3}, "opacity": 1.0})

fig.update_layout(mapbox_layers=layers)
st.plotly_chart(fig, width="stretch")

st.caption(
    f"Showing {len(schools)} schools in Lynn (includes private and charter, not just LPS). "
    "Marker size reflects enrollment. Lynn's town boundary is highlighted in gold."
)

st.divider()

# ---------------------------------------------------------------------------
# Schools table for browsability
# ---------------------------------------------------------------------------

st.subheader("Lynn schools — full list")

display_cols = ["NAME", "TYPE_DESC", "GRADES", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT"]
display_cols = [c for c in display_cols if c in schools.columns]
display = schools[display_cols].rename(columns={
    "NAME": "School",
    "TYPE_DESC": "Type",
    "GRADES": "Grades",
    "TOTAL_CNT": "Enrollment",
    "EL_PCT": "% ELL",
    "LI_PCT": "% Low Income",
    "HN_PCT": "% High Needs",
}).copy()

if "Enrollment" in display:
    display["Enrollment"] = display["Enrollment"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "—"
    )
for c in ["% ELL", "% Low Income", "% High Needs"]:
    if c in display:
        display[c] = display[c].apply(
            lambda x: f"{x:.0%}" if pd.notna(x) else "—"
        )

st.dataframe(display.sort_values("School"), width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Why this view matters
# ---------------------------------------------------------------------------

st.subheader("What this view reveals")
st.markdown(
    """
- **Spatial concentration**: Lynn's 22+ schools cluster in specific neighborhoods.
  You can see which areas are school-dense and which are not.
- **Cross-district context**: Look how Lynn's edges abut Swampscott, Saugus,
  Lynnfield — districts with very different demographic profiles. The line
  between "47% ELL Lynn" and "1% ELL Swampscott" is literally one street wide.
- **Catchment hypothesis**: Without official attendance zones published, the
  spatial arrangement of schools suggests rough catchment areas. The
  **Lynn Equity** and **Lynn Novel Maps** pages explore this further.
"""
)
