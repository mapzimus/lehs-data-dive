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
from utils.charts import el_share_figure
from utils.constants import IMAGES_DIR, LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset
from utils.i18n import t
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
            <span style='font-size:0.95rem;'>{t("Built by")}</span><br>
            <strong style='font-size:1.3rem;'>{AUTHOR_NAME}</strong><br>
            <a href='https://{AUTHOR_SITE}' style='color:#FFB81C;'>{AUTHOR_SITE}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    t(
        "A public, interactive data exploration tool centered on Lynn English "
        "High School (LEHS) — Lynn, Massachusetts."
    )
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

st.header(t("Where do you want to start?"))
st.markdown(
    t(
        "Three nested views of the same place — **Lynn English** the school, "
        "**Lynn Public Schools** the district, and **Lynn** the city around them. "
        "Open whichever one you're curious about; jumping between them is always "
        "one click away in the sidebar."
    )
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
    st.markdown(t("#### 🎓 The School"))
    # Pull the latest student-teacher ratio from teacher_data for the
    # "All Teachers" rollup row — it's already a pre-formatted "X.X to 1"
    # string, so we strip the unit to render compactly.
    stu_tchr = None
    teacher_df = load_dataset("teacher_data")
    if not teacher_df.empty:
        lehs_t = teacher_df[
            (teacher_df["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (teacher_df["ORG_TYPE"] == "School")
            & (teacher_df["SUBJECT"] == "All Teachers")
        ].sort_values("SY")
        if not lehs_t.empty:
            raw = str(lehs_t.iloc[-1]["STU_TCHR_RATIO"])
            # "13.2 to 1" → "13:1"
            if "to" in raw:
                num = raw.split("to")[0].strip().split(".")[0]
                stu_tchr = f"{num}:1"
    ratio_frag = t(" · {ratio} student–teacher ratio", ratio=stu_tchr) if stu_tchr else ""
    # FLNE (First Language Not English) tracks the actual story for Lynn:
    # waves of immigration, not racial categories. A US-born student
    # whose home language is English isn't counted; a recent immigrant
    # family is. Pairs with the % English Learners metric tile (current
    # EL services) by capturing the broader linguistic-heritage pool.
    flne = (
        float(lehs_row["FLNE_PCT"])
        if lehs_row is not None and pd.notna(lehs_row.get("FLNE_PCT"))
        else None
    )
    flne_frag = (
        t(" · {flne} non-English home language", flne=f"{flne:.0%}")
        if flne is not None
        else ""
    )
    st.caption(
        t("Lynn English High · Grades 9–12") + ratio_frag + flne_frag
    )
    if lehs_row is not None:
        st.metric(t("Total Enrollment"), f"{int(lehs_row['TOTAL_CNT']):,}")
        st.metric(t("% English Learners"), f"{lehs_row['EL_PCT']:.0%}")
    # % Chronic Absence — students missing 10%+ of school days. Pairs
    # with the Grad Rate below to tell the engagement-vs-completion
    # story. Pull the latest end-of-year value (mid-year "March"
    # interim rows are noisier).
    att_df = load_dataset("student_attendance")
    if not att_df.empty:
        lehs_att = att_df[
            (att_df["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (att_df["ORG_TYPE"] == "School")
            & (att_df["STU_GRP"] == "All Students")
            & (att_df["ATTEND_PERIOD"] == "End of Year")
        ].sort_values("SY")
        if not lehs_att.empty:
            chronic = lehs_att.iloc[-1]
            chronic_pct = pd.to_numeric(chronic["PCT_CHRON_ABS_10"], errors="coerce")
            if pd.notna(chronic_pct):
                st.metric(
                    t("% Chronic Absence"),
                    f"{float(chronic_pct):.0%}",
                    help=(
                        f"Share of students who missed 10%+ of school days "
                        f"in SY {sy_label(int(chronic['SY']))} — see "
                        f"Discipline & Climate for the full breakdown."
                    ),
                )
    if lehs_grad_row is not None:
        st.metric(
            t("4-yr Graduation Rate"),
            f"{float(lehs_grad_row['GRAD_PCT']):.0%}",
            help=f"Most recent cohort: SY {sy_label(int(lehs_grad_row['SY']))}",
        )
    # st.page_link navigates within the multipage app (no new tab),
    # whereas st.link_button always opens externally. For internal
    # routes we want to keep visitors in the same tab/iframe.
    st.page_link(
        "pages/1_School_Profile.py",
        label=t("Open School Profile →"),
        use_container_width=True,
    )

with d_col:
    _card_logo(IMAGES_DIR / "lps-logo.png", "Lynn Public Schools")
    st.markdown(t("#### 🏛️ The District"))
    sy_dist = int(district_row["SY"]) if district_row is not None else None
    # Caption frames the district's scale and immigration story. FLNE
    # (First Language Not English) indexes the share of students whose
    # families bring a non-English home language — the actual driver of
    # Lynn's diversity, not race coding.
    flne_d = (
        float(district_row["FLNE_PCT"])
        if district_row is not None and pd.notna(district_row.get("FLNE_PCT"))
        else None
    )
    flne_d_frag = (
        t(" · {flne} non-English home language", flne=f"{flne_d:.0%}")
        if flne_d is not None
        else ""
    )
    st.caption(
        t("Lynn Public Schools · 26 schools") + flne_d_frag + f" · SY {sy_label(sy_dist)}"
        if sy_dist else t("Lynn Public Schools · 26 schools") + flne_d_frag
    )
    if district_row is not None:
        st.metric(t("District Enrollment"), f"{int(district_row['TOTAL_CNT']):,}")
        st.metric(t("% English Learners"), f"{district_row['EL_PCT']:.0%}")
    if district_grad_row is not None:
        st.metric(
            t("4-yr Graduation Rate"),
            f"{float(district_grad_row['GRAD_PCT']):.0%}",
        )
    if district_ppe_row is not None:
        st.metric(
            t("Per-pupil expenditure (FY {fy})", fy=int(district_ppe_row['SY'])),
            f"${district_ppe_row['IND_VALUE']:,.0f}",
        )
    st.page_link(
        "pages/Lynn_District.py",
        label=t("Open District →"),
        use_container_width=True,
    )

with c_col:
    _card_logo(IMAGES_DIR / "lynn-city-seal.jpg", "City of Lynn seal")
    st.markdown(t("#### 🏙️ The City"))
    # Caption advertises the two-tab structure on the destination page —
    # Citywide rolls everything up; Neighborhoods drops to Lynn's 22
    # census tracts (ACS + EJScreen + CDC PLACES).
    st.caption(
        t(
            "Lynn, MA · coastal Gateway city · "
            "**Citywide + Neighborhoods (22 census tracts)** tabs"
        )
    )
    pop = _city_num("pop_total")
    mhi = _city_num("median_household_income")
    fb = _city_num("foreign_born_total")
    if pop is not None:
        st.metric(t("Total Population"), f"{int(pop):,}")
    if mhi is not None:
        st.metric(t("Median HH Income"), f"${mhi:,.0f}")
    if fb is not None and pop:
        st.metric(
            t("Foreign-born"),
            f"{fb / pop:.0%}",
            help=f"{int(fb):,} of {int(pop):,} residents",
        )
    # Home-language count comes from ACS C16001's 12 non-English buckets;
    # two of those are catch-all "Other" groups, so the true distinct
    # count is higher — hence the "+".
    st.metric(
        t("Home languages spoken"),
        "12+",
        help=(
            "ACS C16001 tracks 12 non-English language groups in Lynn; "
            "two are catch-all 'Other Indo-European' and 'Other Asian or "
            "Pacific Island' buckets that fold in many more."
        ),
    )
    st.page_link(
        "pages/Lynn_City.py",
        label=t("Open Lynn City →"),
        use_container_width=True,
    )

# Visual break between the three scope cards (data-heavy) and the
# utility row below (supporting tools).
st.divider()

# The single chart that captures LEHS's transformation — the English Learner
# share over a generation. Reused from the English Learners page (its opening
# graphic) as up-front context, per the 618 audit.
st.subheader(t("The shift that defines LEHS"))
st.markdown(
    t(
        "More than any single statistic, this is the story: the share of Lynn "
        "English students who are **English Learners** has climbed dramatically over "
        "a generation. It reshapes what the school teaches, who it hires, and how to "
        "read every other number in this dashboard."
    )
)
st.plotly_chart(el_share_figure(enrollment, LEHS_SCHOOL_CODE), use_container_width=True)
st.page_link(
    "pages/3_ELL_Pipeline.py",
    label=t("See the full English Learner pipeline →"),
)

st.divider()

# --- Utility row: Maps + Data 101 side-by-side. Both are reference
# destinations rather than analytical pages, so they sit together as
# a separate band below the scope hero.
maps_col, learn_col = st.columns(2, gap="medium")

with maps_col:
    st.markdown(t("#### 🗺️ Maps"))
    st.caption(
        t(
            "Interactive MapLibre experiences — Lynn-focused (school pins + "
            "tract demographics) and statewide MA Education Atlas. "
            "**1,800+ MA schools · 351 municipalities · 22 Lynn census tracts.**"
        )
    )
    st.page_link(
        "pages/13_Maps.py",
        label=t("Open Maps →"),
        use_container_width=True,
    )

with learn_col:
    st.markdown(t("#### 📊 Data 101"))
    st.caption(
        t(
            "New to dashboards? **Start here.** A beginner-friendly guide to "
            "what a dataset is, how to read each chart type (bar, line, "
            "histogram, scatter, choropleth, heatmap), what percentages "
            "actually mean, and the most common ways charts mislead. "
            "Built for LEHS students and anyone who's never opened a "
            "dashboard before."
        )
    )
    st.page_link(
        "pages/14_Data_Literacy.py",
        label=t("Open Data 101 →"),
        use_container_width=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Start here — audience-specific landing routes.
# Promoted above the explainer copy so the strongest call-to-action
# (persona-tailored paths) sits right under the hero.
# ---------------------------------------------------------------------------

st.header(t("Or pick by role"))
st.markdown(
    t(
        "The scopes above answer *what* you want to see. These three paths "
        "answer *who you are* — tailored entry points for families, teachers, "
        "and the school committee."
    )
)

p_col, t_col, sc_col = st.columns(3)

with p_col:
    st.markdown(t("### For families"))
    st.caption(t("Choosing a school, understanding outcomes, comparing to siblings."))
    st.page_link("pages/1_School_Profile.py", label=t("School Profile — who attends LEHS today"))
    st.page_link("pages/2_Academic_Performance.py", label=t("Academic Performance — MCAS scores, growth, gaps"))
    st.page_link("pages/5_Success_After_HS.py", label=t("Success After HS — does the promise hold up?"))
    st.page_link("pages/Lynn_Schools.py", label=t("Lynn Schools — LEHS vs. its sibling high schools"))

with t_col:
    st.markdown(t("### For teachers"))
    st.caption(t("Instructional planning, student insight, subgroup gaps."))
    st.page_link("pages/2_Academic_Performance.py", label=t("Academic Performance — MCAS by subject, growth, gaps"))
    st.page_link("pages/3_ELL_Pipeline.py", label=t("English Learners — LEHS's central narrative"))
    st.page_link("pages/8_Discipline_and_Climate.py", label=t("Discipline & Climate — chronic absence by group"))
    st.page_link("pages/6_Teachers_and_Workforce.py", label=t("Teachers & Workforce — who's in the building"))

with sc_col:
    st.markdown(t("### For school committee"))
    st.caption(t("Accountability, peer comparison, dollar-for-outcome leverage."))
    st.page_link("pages/Lynn_District.py", label=t("Lynn District — LPS as a whole"))
    st.page_link("pages/7_Finance.py", label=t("Finance — per-pupil spending by category"))
    st.page_link("pages/Lynn_Schools.py", label=t("Lynn Schools — vs. same-district siblings"))
    st.page_link("pages/11_Gateway_Peer_Comparison.py", label=t("Gateway Cities — 26-city scorecard"))
    st.page_link("pages/12_Correlation_Lab.py", label=t("Cross-Topic Explorer — what moves with what"))

st.caption(
    t(
        "These are starting points, not the only useful pages. The full sidebar "
        "shows every section."
    )
)

st.divider()

# ---------------------------------------------------------------------------
# What is this?
# ---------------------------------------------------------------------------

st.header(t("What is this dashboard?"))

st.markdown(
    t(
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
)

# ---------------------------------------------------------------------------
# Scope box
# ---------------------------------------------------------------------------

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        t(
            """
**Data scope**
- **22 datasets** from MA DESE's E2C Hub (MCAS, graduation, AP, attendance,
  finance, staffing, plans of graduates, pathways, postsecondary outcomes)
- **Original research**: Maxwell Howe's catchment + absenteeism geospatial
  study using aggregated Lynn Public Schools enrollment data
- **Federal data**: US Census ACS 5-year for Lynn tracts, MassGIS shapefiles
- **Historical depth**: enrollment back to **1992–93**, MCAS back to 2017,
  graduation cohorts back to 2005
"""
        )
    )

with c2:
    st.markdown(
        t(
            """
**Three peer cohorts** for comparing LEHS:
- **Same district** *(closest comparison)* — LEHS vs. its sibling
  Lynn high schools. Same city, same policies → school-level effects show through.
- **Same system** — LEHS within LPS as a whole, including all 26
  schools and elementary feeders.
- **Same role, different city** — LEHS vs. the main public high
  school in each of MA's 26 Gateway cities (Brockton, Lawrence,
  Chelsea, Lowell, Holyoke, Springfield, +19).
"""
        )
    )
    st.page_link("pages/Lynn_Schools.py", label=t("→ Lynn Schools (same district)"))
    st.page_link("pages/Lynn_District.py", label=t("→ Lynn District (same system)"))
    st.page_link("pages/11_Gateway_Peer_Comparison.py", label=t("→ Gateway Cities (same role)"))

st.divider()

# ---------------------------------------------------------------------------
# What questions can you answer here?
# ---------------------------------------------------------------------------

st.header(t("Questions you can answer here"))

st.markdown(
    t(
        """
- **How is LEHS doing?** — Headline metrics, trends, and peer comparison
  on **School Profile** and **Academic Performance**.
- **What does LEHS's English Learner pipeline actually look like?** —
  From WIDA proficiency through MCAS, graduation, and into former-EL
  years on **English Learners**.
- **Where does the budget go, and does it buy what we hope?** —
  Per-pupil spending by category on **Finance**, plus cross-domain
  analysis on **Cross-Topic Explorer**.
- **Who works at LEHS, and how does the teacher body match the student
  body?** — **Teachers & Workforce**.
- **Where do LEHS students live, and does distance from school predict
  absence?** — **Where Students Live** *(aggregated maps)*.
- **What can Lynn learn from Lawrence, Chelsea, Holyoke, and other peer
  cities?** — Side-by-side scorecards on **Gateway Cities**.
- **What patterns emerge when you cross-reference everything?** —
  **Cross-Topic Explorer** lets you pick any two metrics and see how they
  relate across the 26 gateway-city high schools.

*Jump to any of these from the index just below, or the sidebar.*
"""
    )
)

st.divider()

# ---------------------------------------------------------------------------
# Section list
# ---------------------------------------------------------------------------

st.header(t("All sections"))

st.markdown(
    t(
        "The sidebar is grouped into five clusters. Pick anything that's "
        "relevant to what you're trying to figure out."
    )
)

c1, c2 = st.columns(2)

with c1:
    st.markdown(t("**Top of sidebar**"))
    st.page_link("pages/home.py", label=t("Home — this page"))
    st.page_link("pages/13_Maps.py", label=t("Maps — Lynn map + statewide MA Education Atlas"))
    st.markdown(t("**The School (LEHS)**"))
    st.page_link("pages/1_School_Profile.py", label=t("School Profile — demographics, enrollment trends"))
    st.page_link("pages/2_Academic_Performance.py", label=t("Academic Performance — MCAS, growth, gaps"))
    st.page_link("pages/3_ELL_Pipeline.py", label=t("English Learners (central narrative)"))
    st.page_link("pages/4_College_and_Career.py", label=t("College & Career — AP, MassCore, FAFSA, plans"))
    st.page_link("pages/5_Success_After_HS.py", label=t("Success After HS — 9th grade → degrees → earnings"))
    st.page_link("pages/6_Teachers_and_Workforce.py", label=t("Teachers & Workforce — diversity, staffing"))
    st.page_link("pages/7_Finance.py", label=t("Finance — per-pupil spending breakdowns"))
    st.page_link("pages/8_Discipline_and_Climate.py", label=t("Discipline & Climate — suspensions, attendance"))
    st.page_link("pages/9_Athletics.py", label=t("Athletics — records, rivalry, hall of fame"))
    st.page_link("pages/16_Where_Students_Live.py", label=t("Where Students Live — residential pattern"))
    st.page_link("pages/15_LEHS_History.py", label=t("LEHS History — 130+ years of the school's story"))

with c2:
    st.markdown(t("**Lynn**"))
    st.page_link("pages/Lynn_District.py", label=t("District — LPS snapshot + all 26 schools"))
    st.page_link("pages/Lynn_City.py", label=t("City — demographics, economy, neighborhoods"))
    st.markdown(t("**Comparison**"))
    st.page_link("pages/Lynn_Schools.py", label=t("Lynn Schools — closest peer view"))
    st.page_link("pages/11_Gateway_Peer_Comparison.py", label=t("Gateway Cities — 26-city scorecard"))
    st.page_link("pages/12_Correlation_Lab.py", label=t("Cross-Topic Explorer — cross-domain analysis"))
    st.markdown(t("**About**"))
    st.page_link("pages/14_Data_Literacy.py", label=t("Data 101 — beginner's guide to the charts"))
    st.page_link("pages/99_Methodology.py", label=t("Methodology — sources and caveats"))

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div style='text-align:center; margin-top:2rem; color:#8A94A6; font-size:0.9rem;'>
        {t("Built by")} <strong>{AUTHOR_NAME}</strong> ·
        <a href='https://{AUTHOR_SITE}' style='color:#FFB81C;'>{AUTHOR_SITE}</a> ·
        <a href='https://github.com/mapzimus/lehs-data-dive' style='color:#FFB81C;'>{t("source on GitHub")}</a>
    </div>
    """,
    unsafe_allow_html=True,
)
