"""Lynn Schools — school-by-school comparison across the district plus the family-facing HS options guide."""
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go

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
from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, data_downloads_panel
from utils.constants import (LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE, LYNN_SIBLING_HS,
                             LEHS_NAVY, LEHS_GOLD, STATE_COLOR, LYNN_SIBLING_COLOR, LVTI_COLOR)
st.set_page_config(page_title="Lynn Schools | LEHS", page_icon="🏙️", layout="wide")
sidebar_attribution()

st.title("Lynn Schools")
st.markdown(
    "Side-by-side views of the schools inside Lynn Public Schools: an "
    "**analytical comparison** of every Lynn school, and a **family-facing "
    "guide** to the high schools a Lynn student actually chooses between."
)
_tab_0, _tab_1 = st.tabs(['📊 Compare Lynn Schools', '🎒 Lynn HS Options (for families)'])

with _tab_0:
    # ==== from pages/Lynn_Schools.py ====
    st.header("Lynn Schools — Side by Side")
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

with _tab_1:
    # ==== from pages/Lynn_HS_Options.py ====
    # ---------------------------------------------------------------------------
    # The four Lynn public high schools a family chooses among.
    # Codes verified against DESE datasets 2026-06-13. KIPP Academy Lynn is a
    # Commonwealth charter and is NOT in these district datasets (see caveat below).
    # ---------------------------------------------------------------------------

    SCHOOLS = {
        "01630510": "Lynn English",
        "01630505": "Classical",
        "01630605": "Lynn Tech (LVTI)",
        "01630575": "Fredrick Douglass",
    }
    # Stable display order — focus school (LEHS) first.
    SCHOOL_ORDER = ["Lynn English", "Classical", "Lynn Tech (LVTI)", "Fredrick Douglass"]
    SCHOOL_COLORS = {"Lynn English": LEHS_GOLD, "Classical": LEHS_NAVY,
                     "Lynn Tech (LVTI)": LVTI_COLOR, "Fredrick Douglass": LYNN_SIBLING_COLOR}


    def _num(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce")


    def _norm_grp(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize the NBSP that DESE embeds in some STU_GRP labels."""
        if not df.empty and "STU_GRP" in df.columns:
            df = df.copy()
            df["STU_GRP"] = df["STU_GRP"].astype(str).str.replace("\xa0", " ")
        return df


    def _latest_slice(df: pd.DataFrame) -> pd.DataFrame:
        """Rows for our four schools at the max SY present in this dataset."""
        if df.empty or "ORG_CODE" not in df.columns:
            return pd.DataFrame()
        sub = df[df["ORG_CODE"].astype(str).isin(SCHOOLS)].copy()
        if sub.empty or "SY" not in sub.columns:
            return sub
        sub["SY"] = _num(sub["SY"])
        return sub[sub["SY"] == sub["SY"].max()].copy()


    # ---------------------------------------------------------------------------
    # Load + reduce each source to a per-school latest-year value keyed by ORG_CODE.
    # ---------------------------------------------------------------------------

    enroll = load_dataset("enrollment_demographics")
    acct = load_dataset("accountability_summary")
    mcas = _norm_grp(load_dataset("mcas_achievement"))
    grad = _norm_grp(load_dataset("graduation_rates"))
    ap = _norm_grp(load_dataset("ap_participation"))

    # Enrollment + demographic profile (percentages stored as 0-1 fractions).
    enr_latest = _latest_slice(enroll)
    enr_year = int(enr_latest["SY"].max()) if not enr_latest.empty else None

    # Accountability (SY 2025 only — no SY filter needed, all rows are 2025).
    acct_sub = acct[acct["ORG_CODE"].astype(str).isin(SCHOOLS)].copy() if not acct.empty else pd.DataFrame()

    # MCAS grade-10, All Students, ELA + Math, latest year.
    mcas_g10 = pd.DataFrame()
    if not mcas.empty:
        m = mcas[
            (mcas["ORG_CODE"].astype(str).isin(SCHOOLS))
            & (mcas["TEST_GRADE"].astype(str) == "10")
            & (mcas["STU_GRP"] == "All Students")
            & (mcas["SUBJECT_CODE"].isin(["ELA", "MATH"]))
        ].copy()
        m["SY"] = _num(m["SY"])
        if not m.empty:
            m = m[m["SY"] == m["SY"].max()]
            m["M_PLUS_E_PCT"] = _num(m["M_PLUS_E_PCT"])
            mcas_g10 = m
    mcas_year = int(mcas_g10["SY"].max()) if not mcas_g10.empty else None

    # Graduation — 4-year adjusted cohort, All Students, latest year.
    grad_latest = pd.DataFrame()
    if not grad.empty:
        g = grad[
            (grad["ORG_CODE"].astype(str).isin(SCHOOLS))
            & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
            & (grad["STU_GRP"] == "All Students")
        ].copy()
        g["SY"] = _num(g["SY"])
        if not g.empty:
            g = g[g["SY"] == g["SY"].max()]
            g["GRAD_PCT"] = _num(g["GRAD_PCT"])
            grad_latest = g
    grad_year = int(grad_latest["SY"].max()) if not grad_latest.empty else None

    # AP participation — test-takers, All Students, latest year.
    ap_latest = pd.DataFrame()
    if not ap.empty:
        a = ap[(ap["ORG_CODE"].astype(str).isin(SCHOOLS)) & (ap["STU_GRP"] == "All Students")].copy()
        a["SY"] = _num(a["SY"])
        if not a.empty:
            a = a[a["SY"] == a["SY"].max()]
            a["TEST_TAKERS_CNT"] = _num(a["TEST_TAKERS_CNT"])
            ap_latest = a
    ap_year = int(ap_latest["SY"].max()) if not ap_latest.empty else None

    # ---------------------------------------------------------------------------
    # Statewide reference values (ORG_TYPE == 'State') for benchmark lines.
    # These are published DESE statewide figures, pulled at the same year the
    # school bars display. Each helper returns None when the figure is absent so
    # the chart simply omits its reference line rather than inventing one.
    # ---------------------------------------------------------------------------


    def _state_value(df: pd.DataFrame, value_col: str, year, extra_filter=None):
        """Latest-year statewide value (0-1 fraction) for a metric, or None."""
        if df is None or df.empty or "ORG_TYPE" not in df.columns:
            return None
        s = df[df["ORG_TYPE"].astype(str) == "State"].copy()
        if extra_filter is not None:
            s = s[extra_filter(s)]
        if s.empty or "SY" not in s.columns:
            return None
        s["SY"] = _num(s["SY"])
        if year is not None and (s["SY"] == year).any():
            s = s[s["SY"] == year]
        else:
            s = s[s["SY"] == s["SY"].max()]
        if s.empty:
            return None
        val = _num(s[value_col]).iloc[0]
        return float(val) if pd.notna(val) else None


    # MCAS grade-10 statewide %M+E, All Students, by subject (fractions 0-1).
    _state_mcas = {}
    if not mcas.empty:
        for _subj in ("ELA", "MATH"):
            _state_mcas[_subj] = _state_value(
                mcas, "M_PLUS_E_PCT", mcas_year,
                lambda d, _s=_subj: (d["TEST_GRADE"].astype(str) == "10")
                & (d["STU_GRP"] == "All Students")
                & (d["SUBJECT_CODE"] == _s),
            )

    # Statewide 4-year graduation rate, All Students. State publishes this as the
    # "4-Year Graduation Rate" (the school bars use the "Adjusted Cohort" wording,
    # which the state row does not carry); both are DESE's statewide 4-year figure.
    state_grad = _state_value(
        grad, "GRAD_PCT", grad_year,
        lambda d: (d["GRAD_RATE_TYPE"] == "4-Year Graduation Rate")
        & (d["STU_GRP"] == "All Students"),
    )

    # Statewide demographic shares (All Students implied at the State total row).
    state_demo = {}
    if not enroll.empty:
        for _lbl, _col in [("% English Learners", "EL_PCT"),
                           ("% Low Income", "LI_PCT"),
                           ("% Students with Disabilities", "SWD_PCT")]:
            state_demo[_lbl] = _state_value(enroll, _col, enr_year)

    # ---------------------------------------------------------------------------
    # Page header + framing
    # ---------------------------------------------------------------------------

    st.header("🏫 Lynn High School Options")
    st.markdown(
        "These are the public high schools a Lynn family chooses among, shown side by "
    "side on the same outcome metrics. **Lynn English** and **Classical** are the two "
    "large comprehensive high schools. **Lynn Tech (LVTI)** is a career/technical school "
    "with a different mission — its program mix and selective-ish admissions shape every "
    "comparison below, so read its numbers in that light. **Fredrick Douglass Collegiate "
    "Academy** is a smaller alternative academy; its small enrollment makes rate-based "
    "metrics (graduation, MCAS) noisier year to year."
    )
    st.caption(
        "Figures are the most recent year published per dataset (years differ slightly by "
    "metric — each is labeled). Percentages from DESE are shown as percentages here."
    )

    st.info(
        "**KIPP Academy Lynn is not shown here.** As a Commonwealth charter school, KIPP "
    "Academy Lynn is governed and reported separately from Lynn Public Schools and does "
    "not appear in the DESE district datasets behind this dashboard. We do not estimate "
    "or fabricate its numbers — a family weighing KIPP should consult its DESE school "
    "profile directly."
    )

    # ---------------------------------------------------------------------------
    # Scorecard table — one row per school, LEHS first.
    # ---------------------------------------------------------------------------

    st.header("Scorecard")
    st.caption("One row per school. Each metric uses the latest year available in its source dataset.")

    DASH = "—"


    def _pct(frac) -> str:
        return f"{frac * 100:.0f}%" if pd.notna(frac) else DASH


    rows = []
    for code in SCHOOLS:  # dict preserves insertion order → LEHS first
        name = SCHOOLS[code]
        row = {"School": name}

        e = enr_latest[enr_latest["ORG_CODE"].astype(str) == code]
        row["Enrollment"] = f"{int(_num(e['TOTAL_CNT']).iloc[0]):,}" if not e.empty and pd.notna(_num(e["TOTAL_CNT"]).iloc[0]) else DASH
        row["% English Learners"] = _pct(_num(e["EL_PCT"]).iloc[0]) if not e.empty else DASH
        row["% Low Income"] = _pct(_num(e["LI_PCT"]).iloc[0]) if not e.empty else DASH
        row["% Students with Disabilities"] = _pct(_num(e["SWD_PCT"]).iloc[0]) if not e.empty else DASH

        ac = acct_sub[acct_sub["ORG_CODE"].astype(str) == code]
        row["State classification"] = str(ac["CLASSIFICATION"].iloc[0]) if not ac.empty and pd.notna(ac["CLASSIFICATION"].iloc[0]) else DASH
        pct = _num(ac["PERCENTILE"]).iloc[0] if not ac.empty else None
        row["State %ile"] = f"{int(pct)}" if pct is not None and pd.notna(pct) else DASH

        mm = mcas_g10[mcas_g10["ORG_CODE"].astype(str) == code]
        ela = mm[mm["SUBJECT_CODE"] == "ELA"]["M_PLUS_E_PCT"]
        mat = mm[mm["SUBJECT_CODE"] == "MATH"]["M_PLUS_E_PCT"]
        row["MCAS ELA % meeting/exceeding"] = _pct(ela.iloc[0]) if not ela.empty else DASH
        row["MCAS Math % meeting/exceeding"] = _pct(mat.iloc[0]) if not mat.empty else DASH

        gg = grad_latest[grad_latest["ORG_CODE"].astype(str) == code]
        row["4-yr Grad %"] = _pct(_num(gg["GRAD_PCT"]).iloc[0]) if not gg.empty else DASH

        aa = ap_latest[ap_latest["ORG_CODE"].astype(str) == code]
        row["AP test-takers"] = f"{int(_num(aa['TEST_TAKERS_CNT']).iloc[0]):,}" if not aa.empty and pd.notna(_num(aa["TEST_TAKERS_CNT"]).iloc[0]) else DASH

        rows.append(row)

    scorecard = pd.DataFrame(rows)
    st.dataframe(scorecard, width="stretch", hide_index=True)

    # Note which schools are absent from which sources (data-availability, not a judgment).
    missing_notes = []
    present_acct = set(acct_sub["ORG_CODE"].astype(str)) if not acct_sub.empty else set()
    for code, name in SCHOOLS.items():
        if code not in present_acct:
            missing_notes.append(f"{name} is not in the SY{int(acct['SY'].max()) if not acct.empty else ''} accountability summary")
    if grad_latest.empty or set(SCHOOLS) - set(grad_latest["ORG_CODE"].astype(str)):
        absent = [SCHOOLS[c] for c in SCHOOLS if grad_latest.empty or c not in set(grad_latest["ORG_CODE"].astype(str))]
        if absent:
            missing_notes.append(f"No published 4-year graduation rate for {', '.join(absent)}")
    if ap_latest.empty or set(SCHOOLS) - set(ap_latest["ORG_CODE"].astype(str)):
        absent = [SCHOOLS[c] for c in SCHOOLS if ap_latest.empty or c not in set(ap_latest["ORG_CODE"].astype(str))]
        if absent:
            missing_notes.append(f"No AP participation reported for {', '.join(absent)}")
    if missing_notes:
        st.caption("Data availability: " + "; ".join(missing_notes) + ". Blank cells (—) mean the metric is not published for that school.")

    # ---------------------------------------------------------------------------
    # Headline grouped bar charts
    # ---------------------------------------------------------------------------

    st.header("Headline metrics")


    def _ordered(df: pd.DataFrame) -> pd.DataFrame:
        """Sort by our fixed school order so colors/positions stay stable."""
        df = df.copy()
        df["School"] = pd.Categorical(df["School"], categories=SCHOOL_ORDER, ordered=True)
        return df.sort_values("School")


    def _bar(df: pd.DataFrame, y: str, title: str, fmt: str, yrange=None, color="School", barmode="group"):
        fig = px.bar(df, x="School", y=y, color=color, title=title,
                     color_discrete_map=SCHOOL_COLORS, text=df[y].map(lambda v: fmt.format(v) if pd.notna(v) else ""))
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(**DEFAULT_LAYOUT, height=330, showlegend=(color != "School"),
                          xaxis_title=None, legend_title_text="")
        if yrange:
            fig.update_yaxes(range=yrange)
        return fig


    c1, c2 = st.columns(2)

    # MCAS ELA + Math (grade 10, % meeting or exceeding).
    with c1:
        if not mcas_g10.empty:
            md = mcas_g10.copy()
            md["School"] = md["ORG_CODE"].astype(str).map(SCHOOLS)
            md["Pct"] = md["M_PLUS_E_PCT"] * 100
            md["Subject"] = md["SUBJECT_CODE"].map({"ELA": "ELA", "MATH": "Math"})
            md = _ordered(md)
            fig = px.bar(md, x="School", y="Pct", color="Subject", barmode="group",
                         title=f"MCAS grade 10 — % meeting/exceeding (SY{mcas_year})",
                         color_discrete_map={"ELA": LEHS_NAVY, "Math": LEHS_GOLD},
                         text=md["Pct"].map("{:.0f}%".format))
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(**DEFAULT_LAYOUT, height=330, xaxis_title=None,
                              yaxis_title="% meeting/exceeding", legend_title_text="")
            for _subj, _slabel in (("ELA", "MA ELA"), ("MATH", "MA Math")):
                _sv = _state_mcas.get(_subj)
                if _sv is not None:
                    fig.add_hline(y=_sv * 100, line_dash="dot", line_color=STATE_COLOR,
                                  annotation_text=f"{_slabel} {_sv * 100:.0f}%",
                                  annotation_position="top left",
                                  annotation_font_color=STATE_COLOR)
            st.plotly_chart(fig, width="stretch")
            if _state_mcas.get("ELA") is not None or _state_mcas.get("MATH") is not None:
                st.caption(f"Dotted lines mark the Massachusetts statewide grade-10 average (SY{mcas_year}).")
        else:
            st.caption("No grade-10 MCAS data available.")

    # 4-year graduation rate.
    with c2:
        if not grad_latest.empty:
            gd = grad_latest.copy()
            gd["School"] = gd["ORG_CODE"].astype(str).map(SCHOOLS)
            gd["Pct"] = _num(gd["GRAD_PCT"]) * 100
            gd = _ordered(gd)
            fig_g = _bar(gd, "Pct", f"4-year graduation rate (SY{grad_year})", "{:.0f}%", yrange=[0, 105])
            if state_grad is not None:
                fig_g.add_hline(y=state_grad * 100, line_dash="dot", line_color=STATE_COLOR,
                                annotation_text=f"MA statewide {state_grad * 100:.0f}%",
                                annotation_position="top left",
                                annotation_font_color=STATE_COLOR)
            st.plotly_chart(fig_g, width="stretch")
            _grad_note = "Douglass's small cohort is not published here; LVTI's near-100% reflects its CTE cohort."
            if state_grad is not None:
                _grad_note += " The dotted line is the Massachusetts statewide 4-year rate."
            st.caption(_grad_note)
        else:
            st.caption("No graduation-rate data available.")

    c3, c4 = st.columns(2)

    # Demographic profile — grouped by school across a few shared measures.
    with c3:
        if not enr_latest.empty:
            ed = enr_latest.copy()
            ed["School"] = ed["ORG_CODE"].astype(str).map(SCHOOLS)
            long = []
            for label, col in [("% English Learners", "EL_PCT"), ("% Low Income", "LI_PCT"), ("% Students with Disabilities", "SWD_PCT")]:
                for _, r in ed.iterrows():
                    long.append({"School": r["School"], "Measure": label, "Pct": _num(pd.Series([r[col]])).iloc[0] * 100})
            ld = _ordered(pd.DataFrame(long))
            fig = px.bar(ld, x="Measure", y="Pct", color="School", barmode="group",
                         title=f"Student population profile (SY{enr_year})",
                         color_discrete_map=SCHOOL_COLORS, category_orders={"School": SCHOOL_ORDER})
            fig.update_layout(**DEFAULT_LAYOUT, height=330, xaxis_title=None,
                              yaxis_title="% of students", legend_title_text="")
            _measures = ["% English Learners", "% Low Income", "% Students with Disabilities"]
            _state_pts = [(m, state_demo.get(m)) for m in _measures if state_demo.get(m) is not None]
            if _state_pts:
                fig.add_trace(go.Scatter(
                    x=[m for m, _ in _state_pts], y=[v * 100 for _, v in _state_pts],
                    mode="markers", name="Massachusetts",
                    marker=dict(symbol="diamond", size=11, color=STATE_COLOR,
                                line=dict(width=1, color="white")),
                ))
            st.plotly_chart(fig, width="stretch")
            if _state_pts:
                st.caption("Diamonds mark the Massachusetts statewide share for each measure.")
        else:
            st.caption("No enrollment/demographic data available.")

    # AP test-takers (counts).
    with c4:
        if not ap_latest.empty:
            ad = ap_latest.copy()
            ad["School"] = ad["ORG_CODE"].astype(str).map(SCHOOLS)
            ad["Takers"] = _num(ad["TEST_TAKERS_CNT"])
            ad = _ordered(ad)
            st.plotly_chart(
                _bar(ad, "Takers", f"AP test-takers (SY{ap_year})", "{:.0f}"),
                width="stretch",
            )
            st.caption(
                "Counts, not rates — larger schools naturally field more AP test-takers. "
            "No statewide reference line is drawn here: the state figure is a raw test-taker "
            "count (tens of thousands), not a per-school rate, so it is not a meaningful "
            "benchmark for these bars."
            )
        else:
            st.caption("No AP participation data available.")

    # ---------------------------------------------------------------------------
    # Demographic / mission context — neutral, factual, no recommendations.
    # ---------------------------------------------------------------------------

    st.caption(
        "Reading these together: the four schools serve different student populations and "
    "missions. Lynn Tech (LVTI) admits students into a career/technical program and is "
    "structured around CTE pathways, so its enrollment mix and outcome rates are not a "
    "like-for-like match to the two comprehensive high schools. Fredrick Douglass "
    "Collegiate Academy operates as a small alternative academy, which makes its "
    "rate-based metrics statistically noisier and means some state measures are not "
    "published for it. These differences are context for the numbers above, not a "
    "ranking — no single school here is 'best,' and the right fit depends on a student's "
    "goals and program needs."
    )

    # ---------------------------------------------------------------------------
    # Cross-links
    # ---------------------------------------------------------------------------

    crosslink_callout(
        "Want the deeper state-accountability view for LEHS specifically?",
        "Accountability",
        "See State Accountability →",
    )
    st.markdown(
        "Looking beyond Lynn? The [Gateway Peer Comparison](/Gateway_Peer_Comparison) page "
    "puts LEHS next to the main high schools of other Massachusetts Gateway Cities — "
    "districts with similar demographics and challenges."
    )

    # ---------------------------------------------------------------------------
    # Data downloads + footer
    # ---------------------------------------------------------------------------

    data_downloads_panel({"Lynn HS options scorecard": scorecard})

page_footer()
