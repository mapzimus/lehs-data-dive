"""
LEHS Data Dive — Home page content.

Rendered as the default page by `st.navigation` in the repo-root `Home.py`.
Page configuration (title, icon, layout) is set by the entry script — this
file just provides the body.
"""

import base64
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.branding import AUTHOR_NAME, AUTHOR_SITE, page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, year_axis
from utils.constants import (
    IMAGES_DIR,
    LEHS_GOLD,
    LEHS_NAVY,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    SUBGROUP_PALETTE,
)
from utils.data_loader import load_dataset
from utils.interpret import sy_label

sidebar_attribution()

# ---------------------------------------------------------------------------
# Mobile-only hint — Streamlit auto-collapses the sidebar on narrow
# screens, so first-time mobile visitors don't realize where the
# sections are. CSS media query hides this on desktop.
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <style>
      /* Mobile-only hint banner. Global mobile CSS lives in
         utils/branding.sidebar_attribution() so it applies everywhere.
         Brand colors reference the constants tokens so the hint stays in
         step with the (concurrently darkened) palette. */
      .mobile-section-hint {{ display: none; }}
      @media (max-width: 768px) {{
        .mobile-section-hint {{
          display: block;
          background: linear-gradient(90deg, #FFF4D6 0%, #FFE9A6 100%);
          border-left: 4px solid {LEHS_GOLD};
          padding: 10px 14px;
          margin: 0 0 14px 0;
          border-radius: 6px;
          font-size: 13px;
          color: {LEHS_NAVY};
          line-height: 1.5;
        }}
      }}
    </style>
    <div class="mobile-section-hint">
      <strong>On mobile?</strong> Tap the gold-outlined arrow in the
      <strong>top-left corner</strong> to open the menu. Pages are
      grouped as The School, Students &amp; Community, Comparison,
      and About — plus Home, Maps, and Search at the top.
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
            <span style='color:{LEHS_NAVY}; font-size:0.95rem;'>Built by</span><br>
            <strong style='font-size:1.3rem; color:{LEHS_NAVY};'>{AUTHOR_NAME}</strong><br>
            <a href='https://{AUTHOR_SITE}' style='color:{LEHS_GOLD};'>{AUTHOR_SITE}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "Public numbers about **Lynn English High School** — and the district "
    "and city around it — in one place. Free to use. Not an official "
    "Lynn Public Schools or state website."
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
    "Start with the **school**, the **district**, or the **city**. They are "
    "three views of the same place. Switch anytime in the sidebar."
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
    ratio_frag = f" · {stu_tchr} student–teacher ratio" if stu_tchr else ""
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
    flne_frag = f" · {flne:.0%} non-English home language" if flne is not None else ""
    st.caption(
        f"Lynn English High · Grades 9–12{ratio_frag}{flne_frag}"
    )
    if lehs_row is not None:
        st.metric("Total Enrollment", f"{int(lehs_row['TOTAL_CNT']):,}")
        st.metric("% English Learners", f"{lehs_row['EL_PCT']:.0%}")
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
                    "% Chronic Absence",
                    f"{float(chronic_pct):.0%}",
                    help=(
                        f"Share of students who missed 10%+ of school days "
                        f"in SY {sy_label(int(chronic['SY']))} — see "
                        f"Discipline & Climate for the full breakdown."
                    ),
                )
    if lehs_grad_row is not None:
        st.metric(
            "4-yr Graduation Rate",
            f"{float(lehs_grad_row['GRAD_PCT']):.0%}",
            help=f"Most recent cohort: SY {sy_label(int(lehs_grad_row['SY']))}",
        )
    # Accountability deliberately does NOT appear on Home (owner direction):
    # the state determination belongs on its own page, not as a headline tile.
    # st.page_link navigates within the multipage app (no new tab),
    # whereas st.link_button always opens externally. For internal
    # routes we want to keep visitors in the same tab/iframe.
    st.page_link(
        "pages/1_School_Profile.py",
        label="Open School Profile →",
        width="stretch",
    )

with d_col:
    _card_logo(IMAGES_DIR / "lps-logo.png", "Lynn Public Schools")
    st.markdown("#### 🏛️ The District")
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
        f" · {flne_d:.0%} non-English home language" if flne_d is not None else ""
    )
    st.caption(
        f"Lynn Public Schools · 26 schools{flne_d_frag} · SY {sy_label(sy_dist)}"
        if sy_dist else f"Lynn Public Schools · 26 schools{flne_d_frag}"
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
    st.page_link(
        "pages/Lynn_District.py",
        label="Open District →",
        width="stretch",
    )

with c_col:
    _card_logo(IMAGES_DIR / "lynn-city-seal.jpg", "City of Lynn seal")
    st.markdown("#### 🏙️ The City")
    # Caption advertises the two-tab structure on the destination page —
    # Citywide rolls everything up; Neighborhoods drops to Lynn's 22
    # census tracts (ACS + EJScreen + CDC PLACES).
    st.caption(
        "Lynn, MA · a coastal Gateway City · city snapshot plus neighborhood maps"
    )
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
    st.page_link(
        "pages/Lynn_City.py",
        label="Open Lynn City →",
        width="stretch",
    )

# Visual break between the three scope cards (data-heavy) and the
# utility row below (supporting tools).
st.divider()

# ---------------------------------------------------------------------------
# The big picture — two context graphics reused from deeper pages (owner ask)
# so the landing page shows, not just lists: (1) LEHS's rising English-Learner
# share, and (2) the 9th-grade -> year-2-of-college cohort funnel.
# ---------------------------------------------------------------------------
st.header("The big picture")
_ctx_l, _ctx_r = st.columns(2, gap="medium")

with _ctx_l:
    st.markdown("**A changing student body — English Learner share**")
    _el = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY")
    _el = _el.dropna(subset=["EL_PCT"]) if "EL_PCT" in _el.columns else _el.iloc[0:0]
    if not _el.empty:
        _fig_el = go.Figure(go.Scatter(
            x=_el["SY"], y=_el["EL_PCT"], mode="lines",
            line=dict(color=SUBGROUP_PALETTE["English Learner"], width=3),
        ))
        _fig_el.update_layout(**DEFAULT_LAYOUT, height=280, yaxis_tickformat=".0%",
                              yaxis_title="% English Learner", xaxis_title="School Year")
        year_axis(_fig_el)
        st.plotly_chart(_fig_el, width="stretch", key="home_el_share")
        st.caption(
            "The English-Learner share at LEHS has roughly doubled since the "
            "early 2000s. [See English Learners →](/ELL_Pipeline)"
        )

with _ctx_r:
    _prog = load_dataset("student_progression_hs_to_postsec")
    _y2 = pd.DataFrame()
    if not _prog.empty:
        _prog = _prog.copy()
        _prog["ORG_CODE"] = _prog["ORG_CODE"].astype(str).str.zfill(8)
        _y2 = _prog[
            (_prog["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (_prog["INDICATOR"] == "Student progression from high school through second year of postsecondary education")
            & (_prog["STU_GRP"] == "All Students")
        ].sort_values("COHORTYR")
    if not _y2.empty and pd.notna(_y2.iloc[-1]["COHORT_CNT"]) and int(_y2.iloc[-1]["COHORT_CNT"]) > 0:
        _row = _y2.iloc[-1]
        _cn = int(_row["COHORT_CNT"])
        _gn = int(_row["GRAD_CNT"]) if pd.notna(_row["GRAD_CNT"]) else 0
        _en = int(_row["IMMEDIATEENR_CNT"]) if pd.notna(_row["IMMEDIATEENR_CNT"]) else 0
        _pn = int(_row["PERSIST_CNT"]) if pd.notna(_row["PERSIST_CNT"]) else 0
        st.markdown("**From 9th grade to year 2 of college**")
        _fig_fn = go.Figure(go.Funnel(
            y=["Entered 9th grade", "Graduated", "Enrolled in college", "Persisted to year 2"],
            x=[_cn, _gn, _en, _pn],
            text=[f"{c:,}<br>({c / _cn:.0%})" for c in [_cn, _gn, _en, _pn]],
            textposition="inside", textfont=dict(color="white", size=13),
            marker=dict(color=[LEHS_NAVY, "#8294AE", "#9CCFC4", LEHS_GOLD]),
            connector=dict(line=dict(color="#B0BEC5", width=1)),
        ))
        _fig_fn.update_layout(**DEFAULT_LAYOUT, height=280)
        st.plotly_chart(_fig_fn, width="stretch", key="home_cohort_funnel")
        st.caption(
            f"Of ~{_cn:,} 9th-graders, ~{_gn / _cn:.0%} graduate and "
            f"~{_pn / _cn:.0%} are still in college a year later. "
            "[See College, Career & Beyond →](/College_and_Career)"
        )

st.divider()

# --- Utility row: Maps + Data 101 side-by-side. Both are reference
# destinations rather than analytical pages, so they sit together as
# a separate band below the scope hero.
maps_col, learn_col = st.columns(2, gap="medium")

with maps_col:
    st.markdown("#### 🗺️ Maps")
    st.caption(
        "Two maps: one of Lynn (schools and neighborhoods) and one of all "
        "Massachusetts. **1,800+ schools · 351 cities and towns · "
        "22 Lynn neighborhoods.**"
    )
    st.page_link(
        "pages/Maps.py",
        label="Open Maps →",
        width="stretch",
    )

with learn_col:
    st.markdown("#### 📊 Data 101")
    st.caption(
        "New to charts? **Start here.** A short guide to reading bars, "
        "lines, maps, and percentages — written for students and anyone "
        "opening this site for the first time."
    )
    st.page_link(
        "pages/About_the_Data.py",
        label="Open About the Data →",
        width="stretch",
    )

st.divider()

# ---------------------------------------------------------------------------
# Start here — audience-specific landing routes.
# Promoted above the explainer copy so the strongest call-to-action
# (persona-tailored paths) sits right under the hero.
# ---------------------------------------------------------------------------

st.header("Or pick by role")
st.markdown(
    "Skip the cards above and start from your job: a parent choosing a "
    "school, a teacher planning support, or a committee member looking "
    "at the whole district."
)

p_col, t_col, sc_col = st.columns(3)

with p_col:
    st.markdown("### For families")
    st.caption("Who goes to Lynn English, how students do, and how it compares to the other Lynn high schools.")
    st.page_link("pages/1_School_Profile.py", label="School Profile — who attends LEHS today")
    st.page_link("pages/2_Academic_Performance.py", label="MCAS — test scores and growth")
    st.page_link("pages/College_Career_Beyond.py", label="College, Career & Beyond — life after graduation")
    st.page_link("pages/Lynn_Schools_Compared.py", label="Lynn Schools — English vs. Classical, Tech, and the others")

with t_col:
    st.markdown("### For teachers")
    st.caption("Test results, English Learners, attendance, and who is on staff.")
    st.page_link("pages/2_Academic_Performance.py", label="MCAS — results by subject and student group")
    st.page_link("pages/4_ELL_Pipeline.py", label="English Learners — the school's largest story")
    st.page_link("pages/Discipline_Climate_Wellbeing.py", label="Discipline & Wellbeing — who is out of school, and why")
    st.page_link("pages/7_Teachers_and_Workforce.py", label="Teachers & Workforce — who works at LEHS")

with sc_col:
    st.markdown("### For school committee")
    st.caption("District-wide numbers, spending, and how Lynn English compares with similar cities.")
    st.page_link("pages/Lynn_District.py", label="Lynn District — all 26 schools together")
    st.page_link("pages/8_Finance.py", label="Finance — where the money goes")
    st.page_link("pages/Lynn_Schools_Compared.py", label="Lynn Schools — English vs. the other Lynn high schools")
    st.page_link("pages/Gateway_Peer_Comparison.py", label="Gateway Cities — Lynn vs. 25 similar cities")
    st.page_link("pages/Correlation_Lab.py", label="Cross-Topic Explorer — which numbers tend to rise together")

st.caption(
    "These are starting points, not the only useful pages. The full sidebar "
    "shows every section."
)

st.divider()

# ---------------------------------------------------------------------------
# What is this?
# ---------------------------------------------------------------------------

st.header("What is this dashboard?")

st.markdown(
    """
**This site puts the public numbers about Lynn English in one place.**
It is for families choosing a school, teachers planning support,
journalists looking for context, and anyone in Lynn who wants a clear
picture — not a pile of separate state websites.

The official sources are spread out. Test scores sit in one state tool,
enrollment in another, spending in a third, teacher data in a fourth.
**Together, those pieces tell a story that no single site shows.**
"""
)

# ---------------------------------------------------------------------------
# Scope box
# ---------------------------------------------------------------------------

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
**What's in here**
- **50+ public datasets from about 10 sources** — mostly Massachusetts
  DESE (tests, graduation, AP, attendance, spending, staffing, college
  outcomes), plus federal civil-rights data, Census, and athletics.
  Full list on **About the Data**.
- **Lynn-only maps** of where students live and how absence varies
  by neighborhood (from aggregated district records)
- **Census and map layers** for the city of Lynn
- **History**: enrollment back to **1992–93**, MCAS back to 2017,
  graduation rates back to 2005
"""
    )

with c2:
    st.markdown(
        """
**Three ways to compare Lynn English**
- **Other Lynn high schools** — Classical, Tech, and the smaller
  academies. Same city and same rules, so differences are about the
  schools themselves.
- **The whole district** — Lynn English next to all 26 Lynn Public
  Schools, including the elementary and middle schools that feed it.
- **Similar cities** — the main public high school in each of
  Massachusetts' 26 Gateway Cities (Lawrence, Chelsea, Lowell,
  Holyoke, Springfield, and 21 others).
"""
    )
    st.page_link("pages/Lynn_Schools_Compared.py", label="→ Lynn Schools (same district)")
    st.page_link("pages/Lynn_District.py", label="→ Lynn District (same system)")
    st.page_link("pages/Gateway_Peer_Comparison.py", label="→ Gateway Cities (same role)")

st.divider()

# ---------------------------------------------------------------------------
# What questions can you answer here?
# ---------------------------------------------------------------------------

st.header("Questions you can answer here")

st.markdown(
    """
- **How is Lynn English doing?** — Snapshot and trends on
  **School Profile** and **MCAS**.
- **How are English Learners doing?** — From the ACCESS English test
  through MCAS and graduation, on **English Learners**.
- **Where does the money go?** — Spending per student on **Finance**.
- **Who teaches here?** — Staffing and teacher diversity on
  **Teachers & Workforce**.
- **Where do students live?** — Neighborhood maps on
  **Where Students Come From**.
- **How does Lynn compare with Lawrence, Chelsea, or Holyoke?** —
  Side-by-side numbers on **Gateway Cities**.
- **Do two numbers tend to move together?** — Pick any pair on
  **Cross-Topic Explorer**. Remember: moving together is not the same
  as one causing the other.

*Use the list below or the sidebar to jump in.*
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Section list
# ---------------------------------------------------------------------------

st.header("All sections")

st.markdown(
    "The sidebar has four groups — The School, Students & Community, "
    "Comparison, and About — plus Home, Maps, and Search at the top."
)

c1, c2 = st.columns(2)

with c1:
    st.markdown("**Top of sidebar**")
    st.page_link("pages/home.py", label="Home — this page")
    st.page_link("pages/Maps.py", label="Maps — Lynn map + statewide MA Education Atlas")
    st.page_link("pages/Search.py", label="Search — find any page or section")
    st.markdown("**The School (LEHS)**")
    st.page_link("pages/What_Changed.py", label="What Changed This Year — biggest year-over-year movers")
    st.page_link("pages/1_School_Profile.py", label="School Profile — demographics, enrollment trends")
    st.page_link("pages/2_Academic_Performance.py", label="MCAS — Grade-10 results, growth, gaps")
    st.page_link("pages/2b_Courses_and_Academics.py", label="Courses & Academics — G9 passing, AP, SAT, course access")
    st.page_link("pages/3_Accountability.py", label="State Accountability — DESE determination breakdown")
    st.page_link("pages/4_ELL_Pipeline.py", label="English Learners — ACCESS, MCAS, and after reclassification")
    st.page_link("pages/College_Career_Beyond.py", label="College, Career & Beyond — pathways + life after graduation")
    st.page_link("pages/7_Teachers_and_Workforce.py", label="Teachers & Workforce — diversity, staffing")
    st.page_link("pages/8_Finance.py", label="Finance — per-pupil spending breakdowns")
    st.page_link("pages/Discipline_Climate_Wellbeing.py", label="Discipline & Wellbeing — suspensions, attendance, wellbeing")

with c2:
    st.markdown("**Students & Community**")
    st.page_link("pages/Where_Students_Come_From.py", label="Where Students Come From — neighborhoods + feeder schools")
    st.page_link("pages/10_Athletics.py", label="Athletics — records, rivalry, hall of fame")
    st.page_link("pages/12_LEHS_History.py", label="LEHS History — 130+ years of the school's story")
    st.page_link("pages/Lynn_District.py", label="Lynn District — LPS snapshot + all 26 schools")
    st.page_link("pages/Lynn_City.py", label="Lynn City — demographics, economy, neighborhoods")
    st.markdown("**Comparison**")
    st.page_link("pages/Lynn_Schools_Compared.py", label="Lynn Schools — school comparison + HS options for families")
    st.page_link("pages/Gateway_Peer_Comparison.py", label="Gateway Cities — 26-city scorecard")
    st.page_link("pages/Correlation_Lab.py", label="Cross-Topic Explorer — cross-domain analysis")
    st.markdown("**About**")
    st.page_link("pages/Stories.py", label="Stories — short narrative reads")
    st.page_link("pages/About_the_Data.py", label="About the Data — methodology, Data 101, gaps, corrections")

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div style='text-align:center; margin-top:2rem; color:#455A64; font-size:0.9rem;'>
        Built by <strong>{AUTHOR_NAME}</strong> ·
        <a href='https://{AUTHOR_SITE}' style='color:{LEHS_GOLD};'>{AUTHOR_SITE}</a> ·
        <a href='https://github.com/mapzimus/lehs-data-dive' style='color:{LEHS_GOLD};'>source on GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)

page_footer()
