"""
Section 13 — Maps.

The interactive maps live as a standalone MapLibre GL JS app at
maxwellhowegis.com/Lynn-data-dive/maps/. This page is just the launch
pad — it sits inside the iframe-embedded Streamlit dashboard and uses
target="_top" to break out of the iframe when the user clicks through.

Why a separate page instead of in-Streamlit maps:
  - Vector tiles + custom MapLibre styling beat Plotly mapbox for serious
    cartography
  - True layer-panel UX (toggle layers, choose variables, 3D extrusion,
    bivariate mode) feels like ArcGIS rather than a notebook chart
  - Polygon symbology for the 351 MA municipalities replaces the previous
    "26 bubbles" approach
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
    """
Geographic views of every layer in this dashboard — Lynn schools, Lynn census
tract demographics, all 351 Massachusetts municipalities, the 26 Gateway
Cities, and MA's ~400 public school districts — rendered with vector tiles
and an ArcGIS-style layer panel.
"""
)

# ---------------------------------------------------------------------------
# Launch button — breaks out of the dashboard iframe to load the
# full-screen MapLibre app at /Lynn-data-dive/maps/
# ---------------------------------------------------------------------------

MAPS_URL = "https://maxwellhowegis.com/Lynn-data-dive/maps/"

st.markdown(
    f"""
    <div style='margin: 32px 0; text-align: center;'>
        <a href='{MAPS_URL}'
           target='_top'
           style='display: inline-block;
                  padding: 18px 36px;
                  background: #0A1F44;
                  color: white;
                  text-decoration: none;
                  font-size: 18px;
                  font-weight: 600;
                  border-radius: 8px;
                  box-shadow: 0 4px 12px rgba(10, 31, 68, 0.2);
                  transition: all 0.15s;
                  font-family: sans-serif;'>
            🗺️&nbsp;&nbsp;Open the Maps&nbsp;&nbsp;→
        </a>
        <div style='margin-top: 10px; color: #607D8B; font-size: 13px; font-family: sans-serif;'>
            Opens in the same browser tab — full screen, vector tiles, layer panel.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# What's in the maps section
# ---------------------------------------------------------------------------

st.subheader("What's in the maps section")

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
**Layer panel** *(ArcGIS-style controls)*
- ✅ Lynn census tracts (choropleth)
- ✅ Lynn schools (point markers, sized by enrollment)
- ✅ Lynn town + neighbors (outline)
- ✅ Massachusetts municipalities (all 351 towns as polygons)
- ✅ MA school districts (alternative polygon choropleth)
- Click any feature for a popup with the underlying data
"""
    )

with c2:
    st.markdown(
        """
**Tract choropleth — switchable variables**
- % non-English at home
- Median household income
- % Foreign-born
- % Bachelor's or higher
- % Severely rent-burdened

**District choropleth — switchable variables**
- 4-year graduation rate
- Per-pupil spending
- % English Learner / Low Income / High Needs

**Visual modes**
- **3D extrusion** — height = active metric
- **Bivariate** — % ELL × % Low Income on districts/munis (Brewer 3×3 palette)
- School label toggle
- Quick views: Lynn / Massachusetts / North Shore
"""
    )

st.divider()

st.caption(
    "Built with MapLibre GL JS, OpenFreeMap vector tiles, and GeoJSON sourced "
    "via jsDelivr from this dashboard's own repo. Updates automatically when "
    "the dashboard data is refreshed."
)
