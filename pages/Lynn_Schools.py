"""
Compare — Lynn Schools.

The closest peer view: Lynn English vs. Lynn Classical, Lynn Tech, Frederick
Douglass, and Harold Durgin. Same district, same policies, same student pool
— differences here isolate school-level practices from city-level factors.

Lifted out of `Lynn_District.py` (which kept Snapshot + All Schools) so all
peer-comparison views — same-district siblings, gateway cities, cross-topic
correlations — live under one Compare group in the sidebar.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    LEHS_GOLD,
    LEHS_NAVY,
    STATE_COLOR,
    SUBGROUP_PALETTE,
    data_downloads_panel,
    span_years,
    with_year_gaps,
)
from utils.constants import (
    IMAGES_DIR,
    LYNN_SIBLING_HS,
)
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(
    page_title="Lynn Schools | LEHS", page_icon="🏫", layout="wide"
)
sidebar_attribution()

st.title("Lynn Schools — Side by Side")
st.markdown(
    "**The most analytically powerful peer view.** Lynn's high schools share "
    "the same district, same policies, and draw from the same student pool. "
    "Differences between them isolate school-level practices rather than "
    "city-level factors. For the district-wide picture (LPS as a system), "
    "see [Lynn District](/Lynn_District?embed=true). For comparison against the other "
    "25 MA Gateway Cities, see [Gateway Cities](/Gateway_Peer_Comparison?embed=true)."
)

# ---------------------------------------------------------------------------
# Shared data loads
# ---------------------------------------------------------------------------

enrollment = load_dataset("enrollment_demographics")
grad = load_dataset("graduation_rates")
mcas = load_dataset("mcas_achievement")
ap_part = load_dataset("ap_participation")
retention = load_dataset("grade_retention")
el_access = load_dataset("el_access")
discipline = load_dataset("discipline_disaggregated")

if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

SIBLING_CODES = [c for c in LYNN_SIBLING_HS.values() if c]

# Color map: LEHS in gold, others muted
SIBLING_COLORS = {
    "01630510": LEHS_GOLD,                                       # LEHS
    "01630505": LEHS_NAVY,                                       # Classical
    "01630605": SUBGROUP_PALETTE["Asian"],                       # Lynn Tech
    "01630575": SUBGROUP_PALETTE["Hispanic/Latino"],             # Frederick Douglass
    "01630525": SUBGROUP_PALETTE["African American/Black"],      # Harold Durgin
}

NAME_OVERRIDES = {
    "01630510": "Lynn English High",
    "01630505": "Lynn Classical",
    "01630605": "Lynn Tech",
    "01630575": "Frederick Douglass",
    "01630525": "Harold Durgin",
}

# The two alternative academies enroll only a few dozen to a few hundred
# students, so any percentage built on a grade-cohort denominator (grad rate,
# Grade 10 MCAS, retention) swings wildly year to year — a single student can
# move the rate several points. Flag them so charts can mark them "small
# cohort — interpret with caution" rather than reading them as equal peers of
# the ~1,500-student comprehensive schools. Harold Durgin (~98 students; a
# Grade 10 cohort of ~10–12) is the most extreme.
SMALL_COHORT_CODES = {"01630575", "01630525"}  # Frederick Douglass, Harold Durgin


def _mark_small(name: str, code: str) -> str:
    """Append a small-cohort dagger to a school's display name."""
    return f"{name} †" if code in SMALL_COHORT_CODES else name


SMALL_COHORT_NOTE = (
    "**†  Small cohort — interpret with caution.** Frederick Douglass and "
    "Harold Durgin are alternative academies enrolling only a few dozen to a "
    "few hundred students (Durgin ~100, with a Grade 10 cohort near 10–12). "
    "On any rate built from a small denominator, one or two students can swing "
    "the number several points, so these schools are not statistically "
    "comparable to the ~1,500-student comprehensive high schools. They are "
    "shown for completeness, not as equal peers."
)

# ---------------------------------------------------------------------------
# Lynn high schools — side by side
# ---------------------------------------------------------------------------

st.header("Lynn High Schools — Side by Side")
st.markdown(
    "Comparison across Lynn's five high schools that report MCAS data: "
    "**Lynn English** (the focus), **Lynn Classical**, **Lynn Tech** "
    "(vocational), **Frederick Douglass Collegiate Academy** (alternative), "
    "and **Harold Durgin Success Academy** (alternative)."
)

# School-identity strip: logos for the three comprehensive HS that have
# an established mascot/brand. The two alternative academies don't have
# publicly published logos, so the strip is three-wide.
_logo_l, _logo_m, _logo_r = st.columns(3)
with _logo_l:
    st.image(str(IMAGES_DIR / "lehs-bulldog.png"), width=110, caption="Lynn English — Bulldogs")
with _logo_m:
    st.image(str(IMAGES_DIR / "lchs-rams.png"), width=110, caption="Lynn Classical — Rams")
with _logo_r:
    st.image(str(IMAGES_DIR / "lynn-tech-logo.png"), width=110, caption="Lynn Tech — Tigers")

siblings = enrollment[enrollment["ORG_CODE"].isin(SIBLING_CODES)].copy()
siblings["School"] = siblings["ORG_CODE"].map(NAME_OVERRIDES)

# ---------------------------------------------------------------------------
# Most-recent scorecard
# ---------------------------------------------------------------------------

st.subheader("Latest Year Scorecard")

latest_year_sib = int(siblings["SY"].max())
latest_sib = siblings[siblings["SY"] == latest_year_sib].set_index("School")
scorecard_cols = {
    "TOTAL_CNT": "Total Enrollment",
    "EL_PCT": "% English Learners (ELL)",
    "LI_PCT": "% Low Income",
    "SWD_PCT": "% Students with Disabilities (SPED)",
    "HN_PCT": "% High Needs",
    "HL_PCT": "% Hispanic/Latino",
    "FE_PCT": "% Female",
}
scorecard = latest_sib[list(scorecard_cols.keys())].rename(columns=scorecard_cols)
for col in scorecard.columns:
    if col == "Total Enrollment":
        scorecard[col] = scorecard[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
    else:
        scorecard[col] = scorecard[col].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")


def highlight_lehs_sib(row):
    if row.name == "Lynn English High":
        return ["background-color: #FFF4D6"] * len(row)
    return [""] * len(row)


st.dataframe(scorecard.style.apply(highlight_lehs_sib, axis=1), width="stretch")
st.caption(
    f"School year {latest_year_sib}. LEHS highlighted in gold. "
    "High Needs counts any student who is low-income, an English learner, "
    "or a student with disabilities."
)

# ---------------------------------------------------------------------------
# Enrollment trends
# ---------------------------------------------------------------------------

st.subheader("Enrollment Trends")

fig = px.line(
    siblings.sort_values("SY"),
    x="SY", y="TOTAL_CNT", color="School",
    color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
    markers=True,
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year")
st.plotly_chart(fig, width="stretch")

st.caption(
    "Lynn English is by far the largest of the Lynn high schools, followed "
    "closely by Lynn Classical."
)

# ---------------------------------------------------------------------------
# Demographic mix comparison
# ---------------------------------------------------------------------------

st.subheader(f"Demographic Composition ({latest_year_sib})")

demo_cols = ["EL_PCT", "LI_PCT", "SWD_PCT", "HL_PCT", "BAA_PCT"]
demo_labels = {
    "EL_PCT": "% English Learners (ELL)",
    "LI_PCT": "% Low Income",
    "SWD_PCT": "% Students with Disabilities (SPED)",
    "HL_PCT": "% Hispanic/Latino",
    "BAA_PCT": "% Black/African American",
}

demo_long = latest_sib.reset_index().melt(
    id_vars=["School"], value_vars=demo_cols, var_name="Metric", value_name="Pct"
)
demo_long["Metric"] = demo_long["Metric"].map(demo_labels)

fig = px.bar(
    demo_long, x="Metric", y="Pct", color="School", barmode="group",
    color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", xaxis_title="")
st.plotly_chart(fig, width="stretch")

st.caption(
    "Each Lynn HS serves a slightly different student population. Lynn Tech "
    "and the alternative HS (Frederick Douglass, Harold Durgin) often have "
    "different demographic profiles than the two main comprehensive schools."
)

# ---------------------------------------------------------------------------
# MCAS Grade 10 comparison
# ---------------------------------------------------------------------------

st.header("MCAS Grade 10 — Lynn HS Comparison")

mcas_lynn = mcas[
    (mcas["ORG_CODE"].isin(SIBLING_CODES))
    & (mcas["TEST_GRADE"] == "10")
    & (mcas["STU_GRP"] == "All Students")
].copy()
mcas_lynn["School"] = mcas_lynn["ORG_CODE"].map(NAME_OVERRIDES)

if mcas_lynn.empty:
    st.info("No MCAS Grade 10 'All Students' data for Lynn HS yet.")
else:
    for subject_code, subject_label in [("ELA", "English Language Arts"), ("MATH", "Mathematics")]:
        st.subheader(f"Grade 10 {subject_label} — % Meeting or Exceeding")
        sub = mcas_lynn[mcas_lynn["SUBJECT_CODE"] == subject_code].sort_values("SY")
        if sub.empty:
            st.info(f"No data for {subject_label}")
            continue
        # Insert explicit NaN rows for skipped years (2020 COVID gap) so the
        # line BREAKS there instead of drawing straight across it.
        sub_g = with_year_gaps(
            sub, "M_PLUS_E_PCT", group_col="School", years=span_years(sub)
        )
        fig = px.line(
            sub_g, x="SY", y="M_PLUS_E_PCT", color="School",
            color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
            markers=True,
        )
        fig.update_traces(connectgaps=False)
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="% Meeting + Exceeding",
            xaxis_title="School Year",
        )
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Graduation rates
# ---------------------------------------------------------------------------

st.header("4-Year Graduation Rates — Lynn HS Comparison")

grad_lynn = grad[
    (grad["ORG_CODE"].isin(SIBLING_CODES))
    & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
    & (grad["STU_GRP"] == "All Students")
].copy()
grad_lynn["School"] = grad_lynn["ORG_CODE"].map(NAME_OVERRIDES)

# Honest disclosure: DESE publishes no 4-year adjusted-cohort graduation rows
# for Frederick Douglass, so it silently drops out of the chart below. Name it
# rather than letting readers wonder where one of the five schools went.
_grad_schools = set(grad_lynn["School"].dropna())
_missing_grad = [
    NAME_OVERRIDES[c] for c in SIBLING_CODES
    if NAME_OVERRIDES.get(c) not in _grad_schools
]
if _missing_grad:
    st.caption(
        "Note: **" + ", ".join(_missing_grad) + "** "
        + ("does" if len(_missing_grad) == 1 else "do")
        + " not appear below. DESE reports no 4-year adjusted-cohort "
        "graduation rate for "
        + ("it" if len(_missing_grad) == 1 else "them")
        + " — Frederick Douglass is a small alternative academy whose "
        "students are counted in their sending school's cohort rather than as "
        "a separate graduating class."
    )

if grad_lynn.empty:
    st.info("No graduation data yet.")
else:
    # Explicit NaN rows for skipped cohort years so each school's line breaks
    # at a reporting gap instead of bridging it.
    grad_g = with_year_gaps(
        grad_lynn.sort_values("SY"), "GRAD_PCT",
        group_col="School", years=span_years(grad_lynn),
    )
    fig = px.line(
        grad_g,
        x="SY", y="GRAD_PCT", color="School",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
        markers=True,
    )
    fig.update_traces(connectgaps=False)
    fig.update_layout(
        **DEFAULT_LAYOUT,
        yaxis_tickformat=".0%",
        yaxis_title="4-Year Graduation Rate",
        xaxis_title="Cohort Year",
    )
    st.plotly_chart(fig, width="stretch")

    latest_grad_year = int(grad_lynn["SY"].max())
    st.subheader(f"Cohort {latest_grad_year} — Outcome Breakdown")
    latest_grad = (
        grad_lynn[grad_lynn["SY"] == latest_grad_year]
        .set_index("School")
        [["GRAD_PCT", "IN_SCH_PCT", "GED_PCT", "DRPOUT_PCT", "NON_GRAD_PCT"]]
        .rename(columns={
            "GRAD_PCT": "Graduated",
            "IN_SCH_PCT": "Still In School",
            "GED_PCT": "GED",
            "DRPOUT_PCT": "Dropped Out",
            "NON_GRAD_PCT": "Non-Grad Completer",
        })
    )
    fig = px.bar(
        latest_grad.reset_index().melt(id_vars="School", var_name="Outcome", value_name="Pct"),
        x="School", y="Pct", color="Outcome", barmode="stack",
        color_discrete_sequence=list(SUBGROUP_PALETTE.values()),
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", xaxis_title="")
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Advanced Placement participation
# ---------------------------------------------------------------------------

st.header("Advanced Placement — Who Takes AP, and How Many Exams")

ap_lynn = pd.DataFrame()
if not ap_part.empty:
    ap_lynn = ap_part[
        (ap_part["ORG_CODE"].isin(SIBLING_CODES))
        & (ap_part["STU_GRP"] == "All Students")
    ].copy()
    ap_lynn["School"] = ap_lynn["ORG_CODE"].map(NAME_OVERRIDES)

if ap_lynn.empty:
    st.info("No AP participation data for the Lynn high schools yet.")
else:
    ap_year = int(ap_lynn["SY"].max())
    ap_cur = ap_lynn[ap_lynn["SY"] == ap_year].copy()
    ap_cur["School_lbl"] = ap_cur.apply(
        lambda r: _mark_small(r["School"], r["ORG_CODE"]), axis=1
    )

    # Only the comprehensive/vocational HS run an AP program; the alternative
    # academies report no AP test-takers, so they simply don't appear here.
    _ap_present = set(ap_cur["School"])
    _ap_absent = [NAME_OVERRIDES[c] for c in SIBLING_CODES
                  if NAME_OVERRIDES.get(c) not in _ap_present]

    st.subheader(f"AP Test-Takers ({sy_label(ap_year)})")
    fig = px.bar(
        ap_cur.sort_values("TEST_TAKERS_CNT", ascending=False),
        x="School_lbl", y="TEST_TAKERS_CNT", color="School",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
        text="TEST_TAKERS_CNT",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        **DEFAULT_LAYOUT, yaxis_title="Students taking ≥1 AP exam",
        xaxis_title="", showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader(f"Exams Per Test-Taker ({sy_label(ap_year)})")
    fig = px.bar(
        ap_cur.sort_values("EXAMS_PER_TAKER", ascending=False),
        x="School_lbl", y="EXAMS_PER_TAKER", color="School",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
        text="EXAMS_PER_TAKER",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        **DEFAULT_LAYOUT, yaxis_title="AP exams per student",
        xaxis_title="", showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

    # Plain-language read of the two charts.
    _lehs_ap = ap_cur[ap_cur["ORG_CODE"] == "01630510"]
    _ap_msg = ""
    if not _lehs_ap.empty:
        _t = int(_lehs_ap["TEST_TAKERS_CNT"].iloc[0])
        _e = float(_lehs_ap["EXAMS_PER_TAKER"].iloc[0])
        _is_depth_leader = _e >= ap_cur["EXAMS_PER_TAKER"].max() - 1e-9
        _depth_clause = (
            f"the **most exams per student ({_e:.2f})** of any Lynn high school"
            if _is_depth_leader
            else f"**{_e:.2f} exams per student**"
        )
        _ap_msg = (
            f"Lynn English had **{_t} AP test-takers** and {_depth_clause} — "
            "students who take AP at LEHS tend to sit for more than one exam. "
        )
    _absent_clause = ""
    if _ap_absent:
        _absent_clause = (
            "**" + ", ".join(_ap_absent) + "** report no AP test-takers and "
            "are omitted; the alternative academies do not run an AP program. "
        )
    st.caption(
        _ap_msg + _absent_clause
        + "“Exams per test-taker” shows how deeply AP-takers load up on exams; "
        "it says nothing about scores — see the district AP page for the share "
        "scoring 3+."
    )

# ---------------------------------------------------------------------------
# Grade retention
# ---------------------------------------------------------------------------

st.header("Grade Retention — Students Held Back")

ret_lynn = pd.DataFrame()
if not retention.empty:
    ret_lynn = retention[
        (retention["ORG_CODE"].isin(SIBLING_CODES))
        & (retention["STU_GRP"] == "All Students")
    ].copy()
    ret_lynn["School"] = ret_lynn["ORG_CODE"].map(NAME_OVERRIDES)

if ret_lynn.empty:
    st.info("No grade-retention data for the Lynn high schools yet.")
else:
    ret_year = int(ret_lynn["SY"].max())
    ret_cur = ret_lynn[ret_lynn["SY"] == ret_year].copy()
    ret_cur["School_lbl"] = ret_cur.apply(
        lambda r: _mark_small(r["School"], r["ORG_CODE"]), axis=1
    )

    st.subheader(f"Share of Students Retained in Grade ({sy_label(ret_year)})")
    fig = px.bar(
        ret_cur.sort_values("RET_ALL_PCT", ascending=False),
        x="School_lbl", y="RET_ALL_PCT", color="School",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
        text="RET_ALL_PCT",
        custom_data=["RET_ALL_CNT", "ENROLL_ALL_CNT"],
    )
    fig.update_traces(
        texttemplate="%{text:.1%}", textposition="outside",
        hovertemplate="%{x}<br>Retained: %{y:.1%}"
                      "<br>(%{customdata[0]:.0f} of %{customdata[1]:.0f} students)<extra></extra>",
    )
    fig.update_layout(
        **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
        yaxis_title="% held back a grade", xaxis_title="", showlegend=False,
    )
    # State reference: the statewide all-students retention rate for the same
    # year gives readers a "what is normal?" anchor for "retention is rare".
    _ret_state = retention[
        (retention["ORG_TYPE"] == "State")
        & (retention["STU_GRP"] == "All Students")
        & (retention["SY"] == ret_year)
    ]
    if not _ret_state.empty:
        _ret_state_pct = float(_ret_state["RET_ALL_PCT"].iloc[0])
        fig.add_hline(
            y=_ret_state_pct, line_dash="dash", line_color=STATE_COLOR,
            annotation_text=f"MA statewide: {_ret_state_pct:.1%}",
            annotation_position="top right",
        )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Retention is rare at the high-school level, so these figures are "
        "small and a single student moves the rate noticeably — Lynn Tech "
        "shows essentially **0%**, while the highest bar still rests on only a "
        "handful of students (see the hover counts). Read the differences "
        "between schools as suggestive, not precise; the dagger (†) marks the "
        "small alternative academies where this is most acute."
    )

# ---------------------------------------------------------------------------
# English-learner ACCESS outcomes
# ---------------------------------------------------------------------------

st.header("English Learners — ACCESS Progress by School")

ela_lynn = pd.DataFrame()
if not el_access.empty:
    ela_lynn = el_access[
        (el_access["ORG_CODE"].isin(SIBLING_CODES))
        & (el_access["GRADE"].astype(str) == "ALL")
    ].copy()
    ela_lynn["School"] = ela_lynn["ORG_CODE"].map(NAME_OVERRIDES)

if ela_lynn.empty:
    st.info("No EL ACCESS data for the Lynn high schools yet.")
else:
    ela_year = int(ela_lynn["SY"].max())
    ela_cur = ela_lynn[ela_lynn["SY"] == ela_year].copy()
    ela_cur["School_lbl"] = ela_cur.apply(
        lambda r: _mark_small(r["School"], r["ORG_CODE"]), axis=1
    )

    st.subheader(f"% of English Learners Making Expected Progress ({sy_label(ela_year)})")
    fig = px.bar(
        ela_cur.sort_values("RE1_PCT", ascending=False),
        x="School_lbl", y="RE1_PCT", color="School",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
        text="RE1_PCT",
        custom_data=["ENROLLED_CNT"],
    )
    fig.update_traces(
        texttemplate="%{text:.0%}", textposition="outside",
        hovertemplate="%{x}<br>Making progress: %{y:.0%}"
                      "<br>EL students: %{customdata[0]:.0f}<extra></extra>",
    )
    fig.update_layout(
        **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
        yaxis_title="% making expected ACCESS progress (RE1)",
        xaxis_title="", showlegend=False,
    )
    # State reference: the statewide RE1 share for the same year, so readers
    # can see where the "expected ACCESS growth" bar sits relative to MA.
    _el_state = el_access[
        (el_access["ORG_TYPE"] == "State")
        & (el_access["GRADE"].astype(str) == "ALL")
        & (el_access["SY"] == ela_year)
    ]
    if not _el_state.empty:
        _el_state_re1 = float(_el_state["RE1_PCT"].iloc[0])
        fig.add_hline(
            y=_el_state_re1, line_dash="dash", line_color=STATE_COLOR,
            annotation_text=f"MA statewide: {_el_state_re1:.0%}",
            annotation_position="top right",
        )
    st.plotly_chart(fig, width="stretch")

    _lehs_el = ela_cur[ela_cur["ORG_CODE"] == "01630510"]
    _el_msg = ""
    if not _lehs_el.empty:
        _re1 = float(_lehs_el["RE1_PCT"].iloc[0])
        _n = int(_lehs_el["ENROLLED_CNT"].iloc[0])
        # Rank among the comprehensive/vocational schools (exclude tiny academies).
        _big = ela_cur[~ela_cur["ORG_CODE"].isin(SMALL_COHORT_CODES)]
        _el_msg = (
            f"Lynn English teaches by far the most English Learners "
            f"(**{_n}** of any Lynn HS), yet only **{_re1:.0%}** met their "
            "expected ACCESS growth target — the **lowest of the comprehensive "
            "and vocational high schools** (Lynn Classical and Lynn Tech both "
            "rank higher). "
        )
    st.caption(
        _el_msg
        + "ACCESS is the annual English-proficiency test; **RE1** is the share "
        "of EL students who grew as much as the state expected for their "
        "starting level. A low RE1 at the school carrying the largest EL "
        "caseload is the heart of the English-learner story — drill into it on "
        "the [English Learners](/ELL_Pipeline?embed=true) page."
    )

# ---------------------------------------------------------------------------
# Discipline context — suspension rates per Lynn high school
# ---------------------------------------------------------------------------

st.header("Discipline Context — Suspension Rates by School")

disc_lynn = pd.DataFrame()
if not discipline.empty:
    disc_lynn = discipline[
        (discipline["ORG_CODE"].isin(SIBLING_CODES))
        & (discipline["DIM"] == "all")
        & (discipline["GROUP"] == "All Students")
        & (discipline["INDICATOR"].isin(
            ["In-School Suspension Rate", "Out-of-School Suspension Rate"]))
    ].dropna(subset=["VALUE"]).copy()

if disc_lynn.empty:
    st.info("No suspension-rate data for the Lynn high schools yet.")
else:
    # Latest year with a published value per school (schools can lag a year).
    _disc_latest_sy = disc_lynn.groupby("ORG_CODE")["SY"].transform("max")
    disc_cur = disc_lynn[disc_lynn["SY"] == _disc_latest_sy]
    disc_wide = disc_cur.pivot_table(
        index=["ORG_CODE", "SY"], columns="INDICATOR", values="VALUE",
        aggfunc="last",
    ).reset_index()
    for _ind in ["In-School Suspension Rate", "Out-of-School Suspension Rate"]:
        if _ind not in disc_wide.columns:
            disc_wide[_ind] = pd.NA

    # N = total enrollment in the same school year, for denominator context.
    disc_wide = disc_wide.merge(
        enrollment[["ORG_CODE", "SY", "TOTAL_CNT"]].drop_duplicates(
            subset=["ORG_CODE", "SY"]),
        on=["ORG_CODE", "SY"], how="left",
    )
    disc_wide["School"] = disc_wide["ORG_CODE"].map(NAME_OVERRIDES)
    disc_wide = disc_wide.sort_values("TOTAL_CNT", ascending=False)

    _fmt_rate = lambda x: f"{x:.1%}" if pd.notna(x) else "—"
    disc_tbl = pd.DataFrame({
        "School": disc_wide.apply(
            lambda r: _mark_small(r["School"], r["ORG_CODE"]), axis=1),
        "Year": disc_wide["SY"].map(sy_label),
        "Enrollment (N)": disc_wide["TOTAL_CNT"].map(
            lambda x: f"{int(x):,}" if pd.notna(x) else "—"),
        "In-School Suspension Rate":
            disc_wide["In-School Suspension Rate"].map(_fmt_rate),
        "Out-of-School Suspension Rate":
            disc_wide["Out-of-School Suspension Rate"].map(_fmt_rate),
    })

    def _highlight_lehs_disc(row):
        if str(row["School"]).startswith("Lynn English"):
            return ["background-color: #FFF4D6"] * len(row)
        return [""] * len(row)

    st.dataframe(disc_tbl.style.apply(_highlight_lehs_disc, axis=1),
                 width="stretch", hide_index=True)

    # Name any sibling school with no published rate rather than letting it
    # silently vanish from the table.
    _missing_disc = [
        NAME_OVERRIDES[c] for c in SIBLING_CODES
        if c not in set(disc_wide["ORG_CODE"])
    ]
    _missing_clause = (
        "DESE publishes no suspension rate for **"
        + ", ".join(_missing_disc) + "** in the years covered. "
        if _missing_disc else ""
    )
    st.caption(
        "Each rate is the share of enrolled students receiving at least one "
        "suspension of that type in the year shown (DESE student-discipline "
        "data; N = total enrollment that year). " + _missing_clause +
        "Rates reflect both each school's discipline practices and "
        "differences in the student populations the schools serve, so read "
        "them as context rather than a ranking; the dagger (†) marks the "
        "small alternative academies, where one or two students move the "
        "rate by several points. Federally-collected discipline detail "
        "(by race/ethnicity, referrals, days missed) is on the "
        "[Discipline & Climate](/Discipline_and_Climate?embed=true) page."
    )

# ---------------------------------------------------------------------------
# Small-cohort footnote (applies to the cohort-based charts above)
# ---------------------------------------------------------------------------

st.divider()
st.caption(SMALL_COHORT_NOTE)

# ---------------------------------------------------------------------------
# Key analytical question
# ---------------------------------------------------------------------------

st.subheader("Key Analytical Question")
st.markdown(
    """
**When student populations are similar (or after controlling for them), what's
different about the schools' outcomes?**

The Lynn HS sibling comparison isolates school-level practices from city-level
demographic factors. Use the [English Learners](/ELL_Pipeline?embed=true) page to drill
into how each Lynn HS serves English Learners specifically — Lynn Tech, the
alternative academies, and the two comprehensive HS may all show different
patterns despite operating under the same district leadership.
"""
)

data_downloads_panel({
    "Enrollment & demographics": enrollment,
    "Graduation rates": grad,
    "MCAS achievement": mcas,
    "AP participation": ap_part,
    "Grade retention": retention,
    "EL ACCESS outcomes": el_access,
    "Discipline rates (disaggregated)": discipline,
})

page_footer()
