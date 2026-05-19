"""
Section 20 — Catchment & Absenteeism Research.

Original geospatial work by Maxwell Howe combining student address data
with absenteeism patterns. Source data is private student information
system data; all visualizations on this page are aggregated to protect
individual student privacy.
"""

from pathlib import Path

import streamlit as st

from utils.branding import sidebar_attribution
from utils.constants import PROCESSED_DIR

st.set_page_config(
    page_title="Catchment Research | LEHS", page_icon="🔬", layout="wide"
)
sidebar_attribution()

st.title("Catchment & Absenteeism Research")
st.markdown(
    "**Original geospatial research by Maxwell Howe.** Combines LEHS "
    "student address data with absenteeism patterns to answer a question "
    "DESE's published data cannot: *does distance from school predict whether "
    "a student shows up?*"
)

# ---------------------------------------------------------------------------
# Privacy disclaimer
# ---------------------------------------------------------------------------

st.warning(
    """
**Data privacy notice.** These visualizations are generated from secure
student information system data. **Individual student addresses are not
publicly shared.** All maps on this page show aggregated densities (KDE
surfaces, 100m and 150m grid cells), aggregate hotspot regions, or
statistical distributions — never individual locations. The full report
(including identifying point-level maps) is held privately by Maxwell
Howe and is not part of the public dashboard.
"""
)

st.divider()

IMG_DIR = PROCESSED_DIR / "lehs_research"


def show(slug: str, caption: str = "") -> None:
    path = IMG_DIR / f"{slug}.png"
    if not path.exists():
        st.info(f"Image not yet generated: {slug}.png")
        return
    st.image(str(path), caption=caption, width="stretch")


# ===========================================================================
# WHERE STUDENTS LIVE
# ===========================================================================

st.header("Where LEHS Students Live")
st.markdown(
    "Aggregated density of student residences. Individual addresses are not "
    "shown — only the underlying spatial pattern."
)

c1, c2 = st.columns(2)
with c1:
    show("kde_heatmap",
         "KDE density surface — relative concentration of LEHS student residences.")
with c2:
    show("grid_density_150m",
         "Raw student counts per 150m × 150m grid cell across Lynn.")

st.divider()

# ===========================================================================
# DISTANCE → ABSENTEEISM (THE KEY FINDING)
# ===========================================================================

st.header("Does distance to school predict absenteeism?")
st.markdown(
    "The key question this research answers. Spoiler: **yes, distance "
    "matters** — but the relationship is non-linear, with the largest "
    "effect appearing in specific distance bands rather than uniformly."
)

show("distance_histogram",
     "Distribution of how far LEHS students live from the school. "
     "Most students live within 1-2 miles, with a long tail.")

show("absence_vs_distance_gam",
     "Absenteeism rate vs. distance to school (GAM-smoothed). Reveals a "
     "non-linear pattern that simple linear regression would miss.")

c1, c2 = st.columns(2)
with c1:
    show("absence_by_distance_band",
         "Mean absence rate by distance band (0-0.25, 0.25-0.5, 0.5-1, "
         "1-2, 2-3, 3+ miles).")
with c2:
    show("absence_by_distance_quintile",
         "Absence rate by distance quintile — same students split into "
         "5 equally-sized groups by their distance from school.")

st.markdown(
    """
**Why this matters:** the public dashboard's *Discipline & Climate* page
shows chronic absenteeism rates over time. This research adds the missing
*where*: which neighborhoods drive the absence rate, and how strongly
geographic distance — independent of demographics — predicts attendance.
"""
)

st.divider()

# ===========================================================================
# GEOGRAPHIC HOTSPOTS
# ===========================================================================

st.header("Geographic Absenteeism Hotspots")
st.markdown(
    "Identifies *regions* of Lynn with concentrated absence rates above "
    "policy thresholds (20%, 30%, 40%). Hotspots are shown as aggregated "
    "areas (hexagonal cells), never individual points."
)

show("absenteeism_hotspots_geo",
     "Citywide view of absenteeism hotspots — colored regions where "
     "average absence rates exceed 20% or 30%.")

show("hexbin_absenteeism_100m",
     "Hexbin map of average absence rate per 100m hexagonal cell. Cells "
     "with fewer than ~5% student presence are filtered out.")

show("hotspot_hexagons_above_20",
     "Hexagonal cells (100m) with average absence rate > 20% — the "
     "explicit policy-attention hotspots citywide.")

st.divider()

# ===========================================================================
# Connection to the public dashboard
# ===========================================================================

st.header("How this connects to the public dashboard")

st.markdown(
    """
This research informs three other dashboard pages:

- **[Discipline & Climate](/Discipline_and_Climate)** — Lynn English's
  district-level chronic absence rate is one number. *This* analysis
  shows which neighborhoods drive that number, and how strongly distance
  matters independently of student demographics.

- **[ELL Pipeline](/ELL_Pipeline)** — distance often correlates with
  immigrant settlement patterns. Knowing where ELL students live in
  relation to the school helps explain attendance patterns specific
  to that population.

- **[Lynn Maps Overview](/Maps_Lynn_Overview)** — the public schools
  map shows where the schools *are*; this research shows where the
  *students* are, which can be very different.
"""
)

st.divider()

# ===========================================================================
# Methodology + author
# ===========================================================================

with st.expander("Methodology & data sources"):
    st.markdown(
        """
**Author:** Maxwell Howe (maxwellhowegis.com).

**Source data (private):**
- LEHS student address records (Lynn Public Schools student information system).
- LEHS daily attendance records.

**Tools:**
- Geocoding: Stadia Maps via R ggmap.
- Spatial aggregation: KDE (kernel density estimation), 100m and 150m
  hexagonal/square grid binning.
- Statistical smoothing: GAM (generalized additive model).

**Privacy protections applied to this public page:**
- Only aggregated densities (KDE, hex grids, distance histograms) shown.
- No individual address-level points.
- Hexagonal cells with fewer than the minimum count threshold are filtered out.
- The full report including identifying maps (pages 1-2 and 14-15 of the
  original PDF) is held privately.

**Future work:**
- Port these visualizations to interactive Plotly (currently static images).
- Cross-reference with Census ACS tract demographics to test whether
  distance-effect persists after controlling for income, language, and
  immigration status.
"""
    )
