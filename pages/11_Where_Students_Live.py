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
    "[Discipline & Climate](/Discipline_and_Climate?embed=true), and *what is the "
    "community context around those addresses?* lives on the "
    "[Lynn page](/Lynn_City?embed=true) (Neighborhoods tab)."
)

# ---------------------------------------------------------------------------
# Privacy notice — same as before; this work uses private SIS data
# ---------------------------------------------------------------------------

st.caption(
    "Source: Lynn Public Schools student information system, provided via a "
    "data request to the district. All maps show aggregated densities (KDE "
    "surfaces, 100m and 150m grid cells), not individual locations."
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
    st.image(str(path), caption=caption, width="stretch")


st.header("Residential Density of LEHS Students")
st.markdown(
    "Aggregated density of student residences across Lynn."
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
# Which neighborhoods the density covers — and who that makes the student body.
# The density maps above are pre-rendered surfaces (no per-tract residence
# counts are published), so the neighborhood read is an honest interpretation
# of the maps, paired with LEHS's real demographic profile from DESE.
# ---------------------------------------------------------------------------

import pandas as pd  # noqa: E402

from utils.constants import LEHS_SCHOOL_CODE  # noqa: E402
from utils.data_loader import load_dataset  # noqa: E402
from utils.interpret import sy_label  # noqa: E402

st.subheader("Which neighborhoods — and who that makes the student body")
st.markdown(
    "Reading the density maps above, the deepest concentrations of LEHS "
    "students sit in **central and western Lynn** — the blocks around "
    "**Lynn Common and Central Square (downtown)**, spreading west into "
    "**West Lynn** (where the school itself sits, on O'Callaghan Way) and "
    "north into the **Brickyard**. The pattern thins toward the coastal "
    "**Diamond District** and the **Highlands and Wyoma** to the north. "
    "Because Lynn runs no neighborhood-school zoning for high school, this "
    "*is* the school's community — so the people who live in those central "
    "blocks are, in effect, the people the school serves."
)

_enr = load_dataset("enrollment_demographics")
if not _enr.empty:
    _lehs = _enr[_enr["ORG_CODE"].astype(str) == LEHS_SCHOOL_CODE].sort_values("SY")
    if not _lehs.empty:
        _cur = _lehs.iloc[-1]

        def _pct(v):
            return f"{v:.0%}" if pd.notna(v) else "—"

        st.markdown(f"**Who that makes the student body — LEHS, {sy_label(int(_cur['SY']))}:**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hispanic / Latino", _pct(_cur.get("HL_PCT")))
        m2.metric("English Learners", _pct(_cur.get("EL_PCT")))
        m3.metric("Low income", _pct(_cur.get("LI_PCT")))
        m4.metric("High needs", _pct(_cur.get("HN_PCT")))
        st.caption(
            "“High needs” counts a student in at least one of: English Learner, "
            "low income, or students with disabilities (DESE definition). "
            "Compare these against the tract indicators below to see how the "
            "neighborhoods the density map covers line up on income, "
            "foreign-born share, and health."
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

from utils.charts import DEFAULT_LAYOUT, csv_download  # noqa: E402
from utils.constants import LEHS_GOLD, LEHS_NAVY  # noqa: E402
from utils.data_loader import load_dataset  # noqa: E402
from utils.geo_loader import tract_display_label  # noqa: E402

_TRACTS_PATH = PROCESSED_DIR / "lynn_tracts.geojson"

if _TRACTS_PATH.exists():
    with open(_TRACTS_PATH, encoding="utf-8") as f:
        _fc = json.load(f)
    _rows = [feat["properties"] for feat in _fc.get("features", []) if feat.get("properties")]
    _tracts_df = pd.DataFrame(_rows)

    # Public-facing neighborhood label, e.g. "West Lynn (Tract 2057)".
    if "NAMELSAD" in _tracts_df.columns:
        _tracts_df["tract_label"] = _tracts_df["NAMELSAD"].map(tract_display_label)
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
        st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("% Foreign-born (ACS)")
        st.caption(
            "Share of residents born outside the U.S. (5-year ACS). The tract "
            "geojson ships no direct low-income column, so we report foreign-born "
            "share — a published demographic indicator — rather than inventing a "
            "poverty figure."
        )
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
        "neighborhoods (lower median household income, higher foreign-born share, "
        "higher chronic-disease and housing-cost burden). That's a structural "
        "finding: school-level interventions happen *inside* a community that "
        "already has community-level needs. See the "
        "[Lynn page](/Lynn_City?embed=true) (Neighborhoods tab) for the full "
        "statewide-comparison view of these same indicators."
    )

    st.subheader("Housing-cost burden by Lynn neighborhood")
    st.caption(
        "Share of households spending 30%+ of their income on housing "
        "(5-year ACS, severe + moderate cost burden). A high burden squeezes "
        "the same families whose children fill the residence-density maps "
        "above — leaving less slack for everything from school supplies to "
        "stable housing."
    )
    _ranked_bar(
        "severe_burden_pct",
        "% of households cost-burdened (30%+ of income on housing)",
        "{:.0%}", "Oranges",
    )

    # One-click export of the tract table behind the four charts above —
    # same attribute set the maps carry (ACS + CDC PLACES per tract).
    csv_download(
        _tracts_df,
        "lynn_tracts.csv",
        label="⬇ Download the Lynn neighborhood table (CSV)",
        key="dl_lynn_tracts",
    )
else:
    st.info(
        "`data/processed/lynn_tracts.geojson` not found — community context "
        "overlay is unavailable. Re-run the refresh pipeline to regenerate."
    )

st.divider()

# ---------------------------------------------------------------------------
# Housing affordability — what it costs to live where these students live
# ---------------------------------------------------------------------------

st.header("Housing affordability")
st.markdown(
    "Where students live is shaped by what housing costs. Lynn's home values "
    "and rents are the economic backdrop behind the residence maps above. "
    "(This is affordability only — building-permit and zoning data, which would "
    "show housing *supply*, aren't in this pipeline; see "
    "[What We Don't Know](/Data_Gaps).)"
)

_housing = load_dataset("lynn_housing_trend")
if not _housing.empty:
    zhvi = _housing[(_housing["scope"] == "Lynn") & (_housing["metric"] == "ZHVI")].copy()
    zhvi["date"] = pd.to_datetime(zhvi["date"], errors="coerce")
    zhvi["value"] = pd.to_numeric(zhvi["value"], errors="coerce")
    zhvi = zhvi.dropna(subset=["date", "value"]).sort_values("date")
    if not zhvi.empty:
        fig = px.line(zhvi, x="date", y="value",
                      labels={"date": "", "value": "Typical home value"})
        fig.update_traces(line=dict(color=LEHS_NAVY, width=2.5))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                          title="Lynn typical home value, 2000–present (Zillow ZHVI)")
        st.plotly_chart(fig, width="stretch")
        first, latest = zhvi.iloc[0], zhvi.iloc[-1]
        st.caption(
            f"Zillow's typical Lynn home value rose from about "
            f"${first['value']:,.0f} in {first['date']:%Y} to "
            f"${latest['value']:,.0f} in {latest['date']:%Y}. Source: Zillow "
            "Home Value Index (ZHVI), all homes, smoothed."
        )

_city = load_dataset("lynn_city_stats")
if not _city.empty:
    row = _city.iloc[0]

    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    occ = _num(row.get("occupied_housing_units"))
    owner = _num(row.get("owner_occupied"))
    mhv = _num(row.get("median_home_value"))
    rent = _num(row.get("median_gross_rent"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Median home value", f"${mhv:,.0f}" if mhv else "—")
    c2.metric("Median gross rent", f"${rent:,.0f}/mo" if rent else "—")
    if occ and owner:
        c3.metric("Owner-occupied", f"{owner / occ:.0%}")
        c4.metric("Renter-occupied", f"{1 - owner / occ:.0%}")

    # Age of the housing stock — Lynn's is notably old (a maintenance-cost and
    # lead-paint signal), so show the year-built distribution.
    built = {
        "2014+": "built_2014_or_later", "2010–13": "built_2010_to_2013",
        "2000–09": "built_2000_to_2009", "1990–99": "built_1990_to_1999",
        "1980–89": "built_1980_to_1989", "1970–79": "built_1970_to_1979",
        "1960–69": "built_1960_to_1969", "1950–59": "built_1950_to_1959",
        "1940–49": "built_1940_to_1949", "≤1939": "built_1939_or_earlier",
    }
    bdf = pd.DataFrame(
        [{"Era": k, "Units": _num(row.get(v))} for k, v in built.items()]
    ).dropna(subset=["Units"])
    if not bdf.empty:
        fig = px.bar(bdf, x="Era", y="Units", text="Units")
        fig.update_traces(marker_color=LEHS_GOLD, texttemplate="%{text:,.0f}",
                          textposition="outside", cliponaxis=False)
        fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Decade built",
                          yaxis_title="Housing units",
                          title="When Lynn's housing was built")
        st.plotly_chart(fig, width="stretch")
        acs_yr = row.get("acs_year")
        st.caption(
            "Lynn's housing stock skews old — the largest single group predates "
            "1939 — which tends to mean higher maintenance costs and more "
            "lead-paint risk in the homes these students live in."
            + (f" Source: ACS {int(acs_yr)} 5-year estimates." if acs_yr else
               " Source: ACS 5-year estimates.")
        )

st.divider()

# ---------------------------------------------------------------------------
# Methodology + author
# ---------------------------------------------------------------------------

with st.expander("Methodology & data sources"):
    st.markdown(
        """
**Author:** Maxwell Howe (maxwellhowegis.com).

**Source data:**
- LEHS student address records from the Lynn Public Schools student information system (provided via a data request to the district).

**Tools:**
- Geocoding: Stadia Maps via R `ggmap`.
- Spatial aggregation: KDE (kernel density estimation), 100m and 150m
  hexagonal/square grid binning.

**Aggregation:**
- Maps show aggregated densities (KDE, grid cells), not address-level points.
- Grid cells below a minimum count threshold are dropped.

**Where the rest of this research lives:**
- *Distance from school × attendance* and *geographic absenteeism hotspots*
  are now on [Discipline & Climate](/Discipline_and_Climate?embed=true) since chronic
  absence is the outcome they describe.
"""
    )

page_footer()
