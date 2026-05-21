"""Section 16 — Where Our Students Live.

The residential-pattern view of the LEHS attendance area. Where does the
school's student body actually live? How does that distribution map onto
the underlying community? Both questions are precursors to deeper analysis
elsewhere in the dashboard — chronic absenteeism (Page 8) and community
context (Page 9).

Originally part of the broader "Catchment Research" page; the absence-vs-
distance + hotspot content moved to Page 8 in the split, leaving this page
focused on the pure residential pattern + cross-references to community
data.
"""

from pathlib import Path

import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.constants import PROCESSED_DIR

st.set_page_config(
    page_title="Where Our Students Live | LEHS", page_icon="🏘️", layout="wide"
)
sidebar_attribution()

st.title("Where Our Students Live")
st.markdown(
    "**Where does the LEHS student body actually live?** The school's "
    "official boundary is one thing; the residential pattern of the kids "
    "who walk through the door every day is another. This page surfaces "
    "the second."
)
st.markdown(
    "This page focuses on the **residence pattern itself**. Two follow-on "
    "questions live on neighboring pages: *how does distance from school "
    "predict attendance?* is now part of "
    "[Discipline & Climate](/Discipline_and_Climate), and *what is the "
    "community context around those addresses?* lives on "
    "[Community Context](/Community_Context)."
)

# ---------------------------------------------------------------------------
# Privacy notice — same as before; this work uses private SIS data
# ---------------------------------------------------------------------------

st.warning(
    "**Data privacy notice.** These visualizations are generated from secure "
    "Lynn Public Schools student information system data. **Individual "
    "student addresses are not publicly shared.** All maps on this page "
    "show aggregated densities (KDE surfaces, 100m and 150m grid cells) "
    "— never individual locations. The full identifying analysis is held "
    "privately by Maxwell Howe and is not part of the public dashboard."
)

st.divider()

# ---------------------------------------------------------------------------
# Residential density maps
# ---------------------------------------------------------------------------

_IMG_DIR = PROCESSED_DIR / "lehs_research"


def _show(slug: str, caption: str = "") -> None:
    path = _IMG_DIR / f"{slug}.png"
    if not path.exists():
        st.caption(f"_(image not yet generated: {slug}.png)_")
        return
    st.image(str(path), caption=caption, use_container_width=True)


st.header("Residential Density of LEHS Students")
st.markdown(
    "Aggregated density of student residences across Lynn. Only the "
    "underlying spatial pattern is shown — individual addresses are not."
)

c1, c2 = st.columns(2)
with c1:
    _show(
        "kde_heatmap",
        "KDE density surface — relative concentration of LEHS student "
        "residences across Lynn.",
    )
with c2:
    _show(
        "grid_density_150m",
        "Raw student counts per 150m × 150m grid cell.",
    )

st.markdown(
    "**Read this against the school's catchment map.** Lynn does not draw "
    "neighborhood-school boundaries for high school (all four comprehensive "
    "HS are city-wide). The shape above is *who actually enrolls at LEHS*, "
    "not who's assigned to it."
)

st.divider()

# ---------------------------------------------------------------------------
# Cross-reference: census tracts (placeholder + roadmap)
# ---------------------------------------------------------------------------

st.header("Cross-Reference: Community Context")
st.markdown(
    "The residential pattern above sits inside a real community with its "
    "own demographic, environmental, and health profile. Linking the "
    "student-residence density to **Census ACS tracts**, **CDC PLACES** "
    "health indicators, and **EPA EJScreen** environmental burden lets "
    "us ask a deeper question: *do the neighborhoods our students come from "
    "look systematically different from Lynn overall?*"
)

st.info(
    "**Roadmap.** The tract overlays are not yet rendered on this page — "
    "the underlying data is downloaded (`lynn_tracts.geojson`, ACS data, "
    "and CDC PLACES; EPA EJScreen restored from the Harvard Dataverse "
    "mirror after EPA pulled it in early 2025), but the join + display "
    "logic is the next iteration."
)

st.markdown(
    "Until then, see [Community Context](/Community_Context) for the "
    "tract-level ACS demographics directly."
)

st.divider()

# ---------------------------------------------------------------------------
# Methodology + author
# ---------------------------------------------------------------------------

with st.expander("Methodology & data sources"):
    st.markdown(
        """
**Author:** Maxwell Howe (maxwellhowegis.com).

**Source data (private):**
- LEHS student address records from the Lynn Public Schools student information system.

**Tools:**
- Geocoding: Stadia Maps via R `ggmap`.
- Spatial aggregation: KDE (kernel density estimation), 100m and 150m
  hexagonal/square grid binning.

**Privacy protections applied to this public page:**
- Only aggregated densities (KDE, grid cells) shown.
- No individual address-level points.
- Cells with fewer than the minimum count threshold are filtered out.
- The full report including identifying point-level maps is held privately.

**Where the rest of this research lives:**
- *Distance from school × attendance* and *geographic absenteeism hotspots*
  are now on [Discipline & Climate](/Discipline_and_Climate) since chronic
  absence is the outcome they describe.
"""
    )

page_footer()
