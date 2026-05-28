"""
LEHS Data Dive — Home page content.

Rendered as the default page by `st.navigation` in the repo-root `Home.py`.
Page configuration (title, icon, layout) is set by the entry script — this
file just provides the body.
"""

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.branding import AUTHOR_NAME, AUTHOR_SITE, sidebar_attribution
from utils.constants import IMAGES_DIR, LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
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

# The LEHS Bulldog logo lives on the School card below, so the top
# header is text-only to avoid duplicating it.
col_title, col_author = st.columns([4, 1.2])
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
# Three-scope launch: School · District · City
# ---------------------------------------------------------------------------
# Each card is a hard link into the dedicated section, with the few
# metrics most likely to tell a visitor "yes, that's the scope I want."
# Numbers pull from the same parquet sources the destination pages use,
# so the card and the page always agree.

enrollment = load_dataset("enrollment_demographics")

if enrollment.empty:
    st.info(
        "**Data not yet loaded.** Run `python scripts/refresh_all.py` (after "
        "creating the conda env) to download and process the source datasets. "
        "Then refresh this page."
    )
    st.stop()


def _latest_row(df: pd.DataFrame, sort_col: str = "SY") -> pd.Series | None:
    if df.empty:
        return None
    return df.sort_values(sort_col).iloc[-1]


# --- School (LEHS) ---
lehs_row = _latest_row(enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE])
# --- District (Lynn Public Schools) ---
district_row = _latest_row(
    enrollment[
        (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (enrollment["ORG_TYPE"] == "District")
    ]
)
# --- Graduation rates: pull LEHS and LPS-district 4-yr cohort rates ---
grad = load_dataset("graduation_rates")
lehs_grad_row = None
district_grad_row = None
if not grad.empty:
    grad_4yr = grad[
        (grad["STU_GRP"] == "All Students")
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
    ]
    lehs_grad_row = _latest_row(
        grad_4yr[
            (grad_4yr["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (grad_4yr["ORG_TYPE"] == "School")
        ]
    )
    district_grad_row = _latest_row(
        grad_4yr[
            (grad_4yr["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (grad_4yr["ORG_TYPE"] == "District")
        ]
    )
# --- District per-pupil expenditure ---
dist_exp = load_dataset("district_expenditures")
district_ppe_row = None
if not dist_exp.empty:
    pp = dist_exp[
        (dist_exp["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (dist_exp["IND_CAT"].astype(str).str.contains("Per Pupil", case=False, na=False))
        & (dist_exp["IND_SUBCAT"].astype(str).str.contains("Total Expenditures", case=False, na=False))
    ].copy()
    if not pp.empty:
        pp["IND_VALUE"] = pd.to_numeric(pp["IND_VALUE"], errors="coerce")
        district_ppe_row = _latest_row(pp.dropna(subset=["IND_VALUE"]))
# --- City (Lynn, MA) ACS profile ---
city_df = load_dataset("lynn_city_stats")
city_row = city_df.iloc[0] if not city_df.empty else None


def _city_num(col):
    if city_row is None:
        return None
    v = city_row.get(col)
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


lehs_sy = int(lehs_row["SY"]) if lehs_row is not None else None

st.header("Where do you want to start?")
st.markdown(
    "Three nested views of the same place — **Lynn English** the school, "
    "**Lynn Public Schools** the district, and **Lynn** the city around them. "
    "Open whichever one you're curious about; jumping between them is always "
    "one click away in the sidebar."
)

s_col, d_col, c_col = st.columns(3, gap="medium")

# Each card opens with a fixed-height logo banner so the three columns
# line up vertically even though the logo files have different aspect
# ratios (LEHS bulldog 1.00, LPS 0.80, Lynn seal 1.55). The image is
# centered in a fixed-height flexbox and scaled with object-fit: contain
# so the title rows below the logos all sit at the same y-position.

_CARD_LOGO_HEIGHT_PX = 130


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


_MIME_BY_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def _card_logo(path: Path, alt_text: str) -> None:
    mime = _MIME_BY_EXT.get(path.suffix.lower(), "image/png")
    st.markdown(
        f"""
        <div style="
            height: {_CARD_LOGO_HEIGHT_PX}px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.25rem;
        ">
          <img src="data:{mime};base64,{_b64(path)}"
               alt="{alt_text}"
               style="max-height: 100%; max-width: 100%; object-fit: contain;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


with s_col:
    _card_logo(IMAGES_DIR / "lehs-bulldog.png", "LEHS Bulldogs")
    st.markdown("#### 🎓 The School")
    st.caption(
        f"Lynn English High · SY {sy_label(lehs_sy)}" if lehs_sy else "Lynn English High"
    )
    if lehs_row is not None:
        st.metric("Total Enrollment", f"{int(lehs_row['TOTAL_CNT']):,}")
        st.metric("% English Learners", f"{lehs_row['EL_PCT']:.0%}")
        st.metric("% Low Income", f"{lehs_row['LI_PCT']:.0%}")
    if lehs_grad_row is not None:
        st.metric(
            "4-yr Graduation Rate",
            f"{float(lehs_grad_row['GRAD_PCT']):.0%}",
            help=f"Most recent cohort: SY {sy_label(int(lehs_grad_row['SY']))}",
        )
    st.link_button(
        "Open School Profile →", "/School_Profile",
        type="primary", use_container_width=True,
    )

with d_col:
    _card_logo(IMAGES_DIR / "lps-logo.png", "Lynn Public Schools")
    st.markdown("#### 🏛️ The District")
    sy_dist = int(district_row["SY"]) if district_row is not None else None
    # Caption surfaces the two facts that frame the district's scale:
    # how many schools it runs and how multilingual the families are.
    st.caption(
        f"Lynn Public Schools · 26 schools · 12+ home languages · SY {sy_label(sy_dist)}"
        if sy_dist else "Lynn Public Schools · 26 schools · 12+ home languages"
    )
    if district_row is not None:
        st.metric("District Enrollment", f"{int(district_row['TOTAL_CNT']):,}")
        st.metric("% English Learners", f"{district_row['EL_PCT']:.0%}")
    if district_grad_row is not None:
        st.metric(
            "4-yr Graduation Rate",
            f"{float(district_grad_row['GRAD_PCT']):.0%}",
        )
    if district_ppe_row is not None:
        st.metric(
            f"Per-pupil expenditure (FY {int(district_ppe_row['SY'])})",
            f"${district_ppe_row['IND_VALUE']:,.0f}",
        )
    st.link_button(
        "Open District →", "/Lynn_District",
        type="primary", use_container_width=True,
    )

with c_col:
    _card_logo(IMAGES_DIR / "lynn-city-seal.jpg", "City of Lynn seal")
    st.markdown("#### 🏙️ The City")
    st.caption("Lynn, MA · coastal Gateway city · ACS 5-yr 2019–2023")
    pop = _city_num("pop_total")
    mhi = _city_num("median_household_income")
    fb = _city_num("foreign_born_total")
    if pop is not None:
        st.metric("Total Population", f"{int(pop):,}")
    if mhi is not None:
        st.metric("Median HH Income", f"${mhi:,.0f}")
    if fb is not None and pop:
        st.metric(
            "Foreign-born",
            f"{fb / pop:.0%}",
            help=f"{int(fb):,} of {int(pop):,} residents",
        )
    # Home-language count comes from ACS C16001's 12 non-English buckets;
    # two of those are catch-all "Other" groups, so the true distinct
    # count is higher — hence the "+".
    st.metric(
        "Home languages spoken",
        "12+",
        help=(
            "ACS C16001 tracks 12 non-English language groups in Lynn; "
            "two are catch-all 'Other Indo-European' and 'Other Asian or "
            "Pacific Island' buckets that fold in many more."
        ),
    )
    st.link_button(
        "Open Lynn City →", "/Lynn_City",
        type="primary", use_container_width=True,
    )

# --- Maps row (hard-linked beneath the three scopes) ---
m_text, m_btn = st.columns([4, 1.2], gap="medium")
with m_text:
    st.markdown("#### 🗺️ Maps")
    st.caption(
        "Interactive MapLibre experiences — Lynn-focused (school pins + "
        "tract demographics) and statewide MA Education Atlas. "
        "**1,700+ MA schools · 351 municipalities · 22 Lynn census tracts.**"
    )
with m_btn:
    # Vertical breathing room so the button sits next to the caption.
    st.write("")
    st.link_button(
        "Open Maps →", "/Maps", type="primary", use_container_width=True,
    )

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
- **Lynn Public Schools as a whole** — district context including all
  26 schools and elementary feeders
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
- **[Academic Performance](/Academic_Performance)** — MCAS scores, growth, subject-by-subject gaps
- **[Success After HS](/Success_After_HS)** — does the school's promise hold up through college?
- **[Lynn Schools](/Lynn_Schools)** — LEHS vs. Classical, Tech, Frederick Douglass, Harold Durgin
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
- **[Lynn Schools](/Lynn_Schools)** — LEHS vs. its same-district siblings
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
- **Academic Performance** — MCAS, growth, gaps
- **English Learners** *(central narrative)*
- **College & Career** — AP, MassCore, FAFSA, plans
- **Success After HS** — full pipeline (9th grade → grad → college → persistence → degrees → earnings)
- **Teachers & Workforce** — diversity, staffing
- **Finance** — per-pupil spending breakdowns
- **Discipline & Climate** — suspensions, attendance
- **Athletics** — Bulldogs season records, rivalry, hall of fame
- **Where Students Live** — residential pattern (private SIS, aggregated)
"""
    )

with c2:
    st.markdown(
        """
**Lynn**
- **District** — Snapshot of LPS as a whole · All Lynn Schools (filter/sort 22 schools). Two tabs in one page.
- **City** — Citywide demographics, economy, history · Neighborhoods (tract-level ACS, EJScreen, CDC PLACES). Two tabs in one page.

**Comparison**
- **Lynn Schools** — LEHS vs. Classical, Tech, Frederick Douglass, Harold Durgin (*closest peer view*)
- **Gateway Cities** — 26-city scorecard with LEHS, Classical, Tech, and LPS-district as four separate dots
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
