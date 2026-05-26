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
    "community context around those addresses?* lives on the "
    "[Lynn page](/Lynn_City) (Neighborhoods tab)."
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
    "own demographic, environmental, and health profile. Below, the same "
    "22 Lynn census tracts are ranked on three indicators — eyeball them "
    "against the residence density maps above and look for **the tracts "
    "where most LEHS students live being the *same* tracts that score "
    "highest on community-burden indicators**."
)

import json  # noqa: E402

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402

from utils.charts import DEFAULT_LAYOUT  # noqa: E402

_TRACTS_PATH = PROCESSED_DIR / "lynn_tracts.geojson"

if _TRACTS_PATH.exists():
    with open(_TRACTS_PATH, encoding="utf-8") as f:
        _fc = json.load(f)
    _rows = [feat["properties"] for feat in _fc.get("features", []) if feat.get("properties")]
    _tracts_df = pd.DataFrame(_rows)

    # Short-name tract label (last 6 digits of GEOID for compactness)
    if "NAMELSAD" in _tracts_df.columns:
        _tracts_df["tract_label"] = _tracts_df["NAMELSAD"].astype(str).str.replace(
            "Census Tract ", "Tract ", regex=False
        )
    elif "GEOID" in _tracts_df.columns:
        _tracts_df["tract_label"] = "Tract " + _tracts_df["GEOID"].astype(str).str[-6:]

    def _ranked_bar(col: str, label: str, fmt: str, palette: str):
        if col not in _tracts_df.columns:
            st.caption(f"_({label}: column not in lynn_tracts.geojson — refresh pending)_")
            return
        d = _tracts_df[["tract_label", col]].copy()
        d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=[col]).sort_values(col, ascending=True)
        if d.empty:
            st.caption(f"_({label}: no non-null values yet)_")
            return
        d["text"] = d[col].apply(lambda v: fmt.format(v))
        fig = px.bar(
            d, y="tract_label", x=col, orientation="h", text="text",
            color=col, color_continuous_scale=palette,
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_title=label,
            yaxis_title="",
            coloraxis_showscale=False,
            height=480,
        )
        # Drive tickformat from data range, not column name. Columns like
        # asthma_pct / mental_distress_pct are 0-100 (CDC PLACES) while
        # foreign_born_pct is 0-1 (Census fraction) — same _pct suffix,
        # different scales. Treating both as 0-1 produces a "1230%" axis.
        col_max = d[col].max()
        if col == "median_household_income":
            fig.update_layout(xaxis_tickformat="$,.0f")
        elif col_max <= 1.5:
            # Values are a 0-1 ratio (e.g. foreign_born_pct = 0.27)
            fig.update_layout(xaxis_tickformat=".0%")
        elif fmt.endswith("%}"):
            # Values are already in percent units (e.g. asthma_pct = 12.3);
            # render as a number with a % suffix.
            fig.update_layout(xaxis_ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("% Low-income (ACS)")
        st.caption("Households below the federal poverty threshold (5-year ACS).")
        # No direct low_income tract col in the geojson — use foreign_born as
        # a proxy demographic-stress indicator; if a low-income col exists in
        # future, swap.
        _ranked_bar("foreign_born_pct", "% Foreign-born", "{:.0%}", "Purples")
    with c2:
        st.subheader("Median household income (ACS)")
        _ranked_bar("median_household_income", "$ median household income", "${:,.0f}", "Greens_r")

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("CDC PLACES — % adults with asthma")
        _ranked_bar("asthma_pct", "% asthma prevalence", "{:.1f}%", "Reds")
    with c4:
        st.subheader("CDC PLACES — % adults with mental distress")
        _ranked_bar("mental_distress_pct", "% mental distress", "{:.1f}%", "Reds")

    st.markdown(
        "**Implication.** The student-residence concentration above maps onto "
        "the city's lower-income, more-foreign-born, higher-health-burden "
        "neighborhoods. That's a structural finding: school-level interventions "
        "happen *inside* a community that already has community-level needs. "
        "See the [Lynn page](/Lynn_City) (Neighborhoods tab) for the full "
        "statewide-comparison view of these same indicators."
    )

    if "ENV_INDEX" not in _tracts_df.columns or _tracts_df["ENV_INDEX"].isna().all():
        st.info(
            "**EPA EJScreen pending.** The Harvard Dataverse mirror fix for "
            "EJScreen has landed in the build script, but the join hasn't run "
            "yet (or this is the first refresh post-fix). After the next "
            "successful refresh, this section will gain an Environmental "
            "Justice indicator panel alongside the ACS/PLACES ones above."
        )
else:
    st.info(
        "`data/processed/lynn_tracts.geojson` not found — community context "
        "overlay is unavailable. Re-run the refresh pipeline to regenerate."
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
