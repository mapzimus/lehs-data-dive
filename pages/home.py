"""
LEHS Data Dive — Home page content.

Rendered as the default page by `st.navigation` in the repo-root `Home.py`.
Page configuration (title, icon, layout) is set by the entry script — this
file just provides the body.
"""

import streamlit as st

from utils.branding import AUTHOR_NAME, AUTHOR_SITE, sidebar_attribution
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label

sidebar_attribution()

# ---------------------------------------------------------------------------
# Mobile-only hint — Streamlit auto-collapses the sidebar on narrow
# screens, so first-time mobile visitors don't realize where the
# sections are. CSS media query hides this on desktop.
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
      /* Mobile-only hint banner. Global mobile CSS lives in
         utils/branding.sidebar_attribution() so it applies everywhere. */
      .mobile-section-hint { display: none; }
      @media (max-width: 768px) {
        .mobile-section-hint {
          display: block;
          background: linear-gradient(90deg, #FFF4D6 0%, #FFE9A6 100%);
          border-left: 4px solid #FFB81C;
          padding: 10px 14px;
          margin: 0 0 14px 0;
          border-radius: 6px;
          font-size: 13px;
          color: #0A1F44;
          line-height: 1.5;
        }
      }
    </style>
    <div class="mobile-section-hint">
      <strong>On mobile?</strong> Tap the gold-outlined arrow button
      in the <strong>top-left corner</strong> to open the sections menu
      (the dashboard is organized into four groups: The School, Lynn,
      Comparison, About — plus Maps at the top).
    </div>
    """,
    unsafe_allow_html=True,
)

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
# Start-here / audience-specific landing routes
# ---------------------------------------------------------------------------

st.header("Start Here — Pick the View That Fits You")
st.markdown(
    "Use the sidebar to jump anywhere. Three suggested paths by who you are:"
)

p_col, t_col, sc_col = st.columns(3)

with p_col:
    st.markdown(
        """
### For families
*Choosing a school, understanding outcomes, comparing to siblings.*

- **[School Profile](/School_Profile)** — who attends LEHS today
- **[Success After HS](/Success_After_HS)** — does the school's promise hold up through college?
- **[College & Career](/College_and_Career)** — AP, MassCore, FAFSA, postsecondary plans
- **[Lynn District](/Lynn_District)** — LEHS vs. Classical, Tech, others (*LEHS vs Siblings* tab)
        """
    )

with t_col:
    st.markdown(
        """
### For teachers
*Instructional planning, student insight, subgroup gaps.*

- **[Academic Performance](/Academic_Performance)** — MCAS by subject, growth, gaps (with CIs)
- **[English Learners](/ELL_Pipeline)** — LEHS's central narrative
- **[Discipline & Climate](/Discipline_and_Climate)** — chronic absence by neighborhood + subgroup
- **[Teachers & Workforce](/Teachers_and_Workforce)** — who's in the building
        """
    )

with sc_col:
    st.markdown(
        """
### For school committee
*Accountability, peer comparison, dollar-for-outcome leverage.*

- **[Lynn District](/Lynn_District)** — LPS as a whole (*Snapshot* tab)
- **[Finance](/Finance)** — per-pupil spending by category
- **[Gateway Cities](/Gateway_Peer_Comparison)** — 26-city scorecard
- **[Cross-Topic Explorer](/Correlation_Lab)** — what moves with what
        """
    )

st.caption(
    "These are starting points, not the only useful pages. The full sidebar "
    "shows every section."
)

st.divider()

# ---------------------------------------------------------------------------
# Section list
# ---------------------------------------------------------------------------

st.header("All sections")

st.markdown(
    "The sidebar is grouped into five clusters. Pick anything that's "
    "relevant to what you're trying to figure out."
)

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
**Top of sidebar**
- **Home** — this page
- **Maps** — Lynn-focused map + statewide MA Education Atlas

**The School (LEHS)**
- **School Profile** — demographics, enrollment trends
- **Success After HS** — full pipeline (9th grade → grad → college → persistence → degrees → earnings)
- **Academic Performance** — MCAS, growth, gaps
- **English Learners** *(central narrative)*
- **College & Career** — AP, MassCore, FAFSA, plans
- **Success After HS** — graduation, college persistence
- **Teachers & Workforce** — diversity, staffing
- **Finance** — per-pupil spending breakdowns
- **Discipline & Climate** — suspensions, attendance
- **Where Students Live** — residential pattern (private SIS, aggregated)
"""
    )

with c2:
    st.markdown(
        """
**Lynn**
- **District** — Snapshot of LPS as a whole · All Lynn Schools (filter/sort 22 schools) · LEHS vs Siblings (*closest comparison*). Three tabs in one page.
- **City** — Citywide demographics, economy, history · Neighborhoods (tract-level ACS, EJScreen, CDC PLACES). Two tabs in one page.

**Comparison**
- **Gateway Cities** — 26-city scorecard
- **Cross-Topic Explorer** — cross-domain analysis

**About**
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
