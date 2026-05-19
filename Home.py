"""
LEHS Data Dive — Home (landing page).

Run locally: `streamlit run Home.py`
"""

import streamlit as st

from utils.branding import AUTHOR_NAME, AUTHOR_SITE, sidebar_attribution
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(
    page_title="LEHS Data Dive",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

sidebar_attribution()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

col_title, col_author = st.columns([3, 1])
with col_title:
    st.title("Lynn English High School")
    st.subheader("Data Dive")
with col_author:
    st.markdown(
        f"""
        <div style='text-align:right; margin-top:2rem;'>
            <span style='color:#0A1F44; font-size:0.95rem;'>Built by</span><br>
            <strong style='font-size:1.3rem; color:#0A1F44;'>{AUTHOR_NAME}</strong><br>
            <a href='https://{AUTHOR_SITE}' style='color:#FFB81C;'>{AUTHOR_SITE}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "A public, interactive data exploration tool centered on Lynn English "
    "High School (LEHS) — Lynn, Massachusetts."
)

st.divider()

# ---------------------------------------------------------------------------
# Hero stats from real LEHS data
# ---------------------------------------------------------------------------

enrollment = load_dataset("enrollment_demographics")

if enrollment.empty:
    st.info(
        "**Data not yet loaded.** Run `python scripts/refresh_all.py` (after "
        "creating the conda env) to download and process the source datasets. "
        "Then refresh this page."
    )
    st.stop()

lehs = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY")
current = lehs.iloc[-1]
current_sy = int(current["SY"])

st.caption(f"All metrics below are for school year {sy_label(current_sy)} (most recent available).")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Enrollment", f"{int(current['TOTAL_CNT']):,}")
with c2:
    st.metric("% English Learners", f"{current['EL_PCT']:.0%}")
with c3:
    st.metric("% Low Income", f"{current['LI_PCT']:.0%}")
with c4:
    st.metric("% High Needs", f"{current['HN_PCT']:.0%}")

st.divider()

# ---------------------------------------------------------------------------
# What is this?
# ---------------------------------------------------------------------------

st.header("What is this dashboard?")

st.markdown(
    """
**The LEHS Data Dive pulls together every publicly available dataset relevant
to Lynn English High School and renders it as a single navigable analysis.**
It's designed for the people who actually need to *understand* the school —
families choosing schools, educators planning supports, journalists looking
for context, researchers studying urban education, and the Lynn community
itself.

It exists because the official sources are fragmented: MCAS scores live in
one DESE Power BI dashboard, enrollment in another, finance in a third,
educator data in a fourth, federal civil-rights data in a fifth, Census
community context in a sixth. **Pulling them together at the school level
is the difference between a stack of separate facts and a coherent picture
of one school.**
"""
)

# ---------------------------------------------------------------------------
# Scope box
# ---------------------------------------------------------------------------

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
**Data scope**
- **22 datasets** from MA DESE's E2C Hub (MCAS, graduation, AP, attendance,
  finance, staffing, plans of graduates, pathways, postsecondary outcomes)
- **Original research**: Maxwell Howe's catchment + absenteeism geospatial
  study using Lynn Public Schools student records (aggregated for privacy)
- **Federal data**: US Census ACS 5-year for Lynn tracts, MassGIS shapefiles
- **Historical depth**: enrollment back to **1992–93**, MCAS back to 2017,
  graduation cohorts back to 2005
- ~3 MB processed Parquet files; 1.7 GB raw downloads
"""
    )

with c2:
    st.markdown(
        """
**Three peer cohorts** compared simultaneously:
- **Lynn sibling high schools** — LEHS vs. Lynn Classical, Lynn Tech,
  Frederick Douglass, Harold Durgin *(same district → isolates
  school-level effects)*
- **Lynn Public Schools as a whole** — district context including the
  ~22 schools and elementary feeders
- **MA Gateway City main high schools** — Brockton, Lawrence, Chelsea,
  Lowell, Holyoke, Springfield, and 19 others
"""
    )

st.divider()

# ---------------------------------------------------------------------------
# What questions can you answer here?
# ---------------------------------------------------------------------------

st.header("Questions you can answer here")

st.markdown(
    """
- **How is LEHS doing?** — Headline metrics, trends, comparison to peers.
- **What does LEHS's English Learner pipeline actually look like?** — From
  WIDA proficiency through MCAS, graduation, and into former-EL years.
- **Where does the budget go, and does it buy what we hope?** — Per-pupil
  spending by category, plus cross-domain correlation analysis.
- **Who works at LEHS, and how does the teacher body match the student body?**
- **Where do LEHS students live, and does distance from school predict
  absence?** *(Original Catchment Research — aggregated maps from private data.)*
- **What can Lynn learn from Lawrence, Chelsea, Holyoke, and other peer
  cities?** — Side-by-side scorecards for all 26 MA Gateway Cities.
- **What patterns emerge when you cross-reference everything?** — A custom
  Correlation Lab lets you pick any two metrics and see how they relate
  across the 26 gateway-city high schools.
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Section list
# ---------------------------------------------------------------------------

st.header("How to navigate")

st.markdown("Click any section in the sidebar to jump in. The sections are organized in four groups:")

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
**LEHS-focused (sections 1–8)**
- **School Profile** — demographics, enrollment trends
- **Academic Performance** — MCAS, growth, gaps
- **ELL Pipeline** *(central narrative)*
- **College & Career** — AP, MassCore, FAFSA, plans
- **Success After HS** — graduation, college persistence
- **Teachers & Workforce** — diversity, staffing
- **Finance** — per-pupil spending breakdowns
- **Discipline & Climate** — suspensions, attendance

**Community + comparison (9–12)**
- **Community Context** — neighborhood demographics
- **Lynn District & Siblings** — *closest comparison*
- **Gateway Peer Comparison** — 26-city scorecard
- **Correlation Lab** — cross-domain analysis
"""
    )

with c2:
    st.markdown(
        """
**Lynn maps (13–17)**
- **Lynn Overview Map** — all schools pinned
- **Lynn Equity Maps** — tract demographics + linguistic landscape
- **Lynn Novel Maps** — Voronoi catchments + bivariate
- **MA Districts Statewide** — every district colored by metric
- **Gateway Cities Map** — 26 cities on the MA map

**Companion + research (18–20, 99)**
- **All Lynn Schools** — filter/sort all 22 LPS schools
- **Lynn District Dashboard** — LPS as a whole
- **Catchment Research** — original geospatial analysis
- **Methodology** — sources and caveats
"""
    )

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div style='text-align:center; margin-top:2rem; color:#455A64; font-size:0.9rem;'>
        Built by <strong>{AUTHOR_NAME}</strong> ·
        <a href='https://{AUTHOR_SITE}' style='color:#FFB81C;'>{AUTHOR_SITE}</a> ·
        <a href='https://github.com/mapzimus/lehs-data-dive' style='color:#FFB81C;'>source on GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
