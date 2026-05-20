"""
Section 13 — Maps.

The interactive maps live as standalone MapLibre GL JS apps:
  - Lynn-focused: maxwellhowegis.com/Lynn-data-dive/maps/
  - Statewide MA Education Atlas: maxwellhowegis.com/ma-atlas/

This dashboard page is the launch pad — st.link_button opens each in a
new tab so the embedded iframe doesn't break.
"""

import streamlit as st

from utils.branding import sidebar_attribution

st.set_page_config(page_title="Maps | LEHS", page_icon="🗺️", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.title("Maps")

st.markdown(
    "Two interactive cartographic experiences — a Lynn-focused map for the "
    "dashboard, and a statewide MA Education Atlas as a standalone GIS "
    "portfolio piece. Both built with MapLibre GL JS, vector tiles, and "
    "polygon symbology (no bubble symbology)."
)

st.divider()

# ---------------------------------------------------------------------------
# Launch buttons
# ---------------------------------------------------------------------------

c1, c2 = st.columns(2, gap="large")

with c1:
    st.subheader("Lynn Maps")
    st.markdown(
        "Hyper-focused on Lynn: census-tract demographics (ACS 5-year), "
        "every Lynn school pinned, and Lynn's town outline + neighbors."
    )
    st.link_button(
        "Open Lynn Maps →",
        "https://maxwellhowegis.com/Lynn-data-dive/maps/",
        type="primary",
        use_container_width=True,
    )

with c2:
    st.subheader("MA Education Atlas")
    st.markdown(
        "Every public school and school district in Massachusetts on one "
        "map. 351 municipalities, 274 academic districts, 78 charters, "
        "26 regional vocational, 1,700 schools, 40+ joined metrics, year "
        "slider, group filter, compare mode, PNG export."
    )
    st.link_button(
        "Open MA Atlas →",
        "https://maxwellhowegis.com/ma-atlas/",
        type="primary",
        use_container_width=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# What's in the maps
# ---------------------------------------------------------------------------

st.subheader("What's in the MA Atlas")

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
**Layer panel** *(ArcGIS-style controls)*
- All 351 MA municipality polygons
- 274 academic school districts (dissolved town polygons)
- 78 charter schools, 26 regional vocational overlays
- 1,700 MA public schools as togglable points
- Click any feature for a sticky right-side detail panel
"""
    )

with c2:
    st.markdown(
        """
**40+ metrics across categories**
- Demographics, MCAS, graduation, AP, college plans
- Per-pupil spending, teacher workforce, retention
- Year slider 2017–2026 with slideshow playback
- Student-group filter (Hispanic, Black, ELL, Low Income, etc.)
- 12 color palettes (color-blind-safe group at top)
- Jenks natural breaks + quantile + equal-interval + continuous
- Compare mode with split-screen + synced pan/zoom
- PNG export · shareable URL state
"""
    )
