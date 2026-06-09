"""Section 4 — College & Career Readiness."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, STATE_COLOR, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
from utils.data_loader import get_dart_indicator, load_dataset
from utils.interpret import sat_methodology_note, sy_label

st.set_page_config(page_title="College & Career | LEHS", page_icon="🎓", layout="wide")
sidebar_attribution()

st.title("College & Career Readiness")
st.markdown(
    "AP access and performance, MassCore completion, FAFSA, SAT, and pathway "
    "programs (CTE, Early College, Innovation Pathways) — the building blocks "
    "of post-graduation success."
)

ap = load_dataset("ap_performance")
masscore = load_dataset("masscore_completion")
pathways = load_dataset("pathways_enrollment")
ec_part = load_dataset("early_college_participation")

if ap.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------------------------

st.header("Headline Metrics")

cols = st.columns(4)

# DART-sourced tiles (per-student rates, stored 0–100). The AP "scoring 3+"
# tile is intentionally NOT here — it's sourced from ap_performance below as the
# % of AP *exams* scoring 3+, so the headline matches the by-group AP chart
# further down the page (which already uses PCT_3_5). Keeping a per-student DART
# AP figure up here next to an exam-weighted chart below was the ambiguity.
for col, ind, label in zip(
    [cols[0], cols[2], cols[3]],
    [
        "Jr/Sr enrolled in one or more AP / IB courses",
        "High school graduates who completed MassCore",
        "Grade 12 students who completed FAFSA",
    ],
    ["% Juniors/Seniors in AP/IB", "% Completed MassCore", "% Completed FAFSA"],
):
    sub = get_dart_indicator(LEHS_SCHOOL_CODE, ind)
    if not sub.empty:
        v = sub.iloc[-1]["VALUE"]
        with col:
            # DART indicator VALUEs are stored on a 0–100 scale, so render them
            # as a literal percentage (e.g. 16.0 -> "16%"). The labels above all
            # say "%", so the value must carry the sign too.
            st.metric(label, f"{v:.0f}%")

# AP "scoring 3+" tile — canonical % of AP EXAMS scoring 3+ (exam-weighted, All
# Subjects), from ap_performance PCT_3_5 (already 0-1). This is the same metric
# and definition as the "AP pass rate by student group" chart below, so the
# headline number and that chart's All-Students bar now agree.
ap_all = ap[
    (ap["ORG_CODE"] == LEHS_SCHOOL_CODE)
    & (ap["SUBJ"] == "All Subjects")
    & (ap["STU_GRP"] == "All Students")
].copy()
ap_all["PCT_3_5"] = pd.to_numeric(ap_all["PCT_3_5"], errors="coerce")
ap_all = ap_all.dropna(subset=["PCT_3_5"]).sort_values("SY")
if not ap_all.empty:
    with cols[1]:
        st.metric("% of AP exams scoring 3+", f"{ap_all.iloc[-1]['PCT_3_5']:.0%}")

st.divider()

# ---------------------------------------------------------------------------
# AP Performance
# ---------------------------------------------------------------------------

st.header("Advanced Placement Performance")

ap_lehs = ap[(ap["ORG_CODE"] == LEHS_SCHOOL_CODE) & (ap["STU_GRP"] == "All Students")].copy()
ap_lehs["STU_GRP"] = ap_lehs["STU_GRP"].astype(str)

# Test counts by subject (latest year)
if not ap_lehs.empty:
    latest_year = int(ap_lehs["SY"].max())
    # Each subject category has BOTH a category-summary row (SUBJ == SUBJ_CAT)
    # and its individual leaf-subject rows; there is also a grand-total
    # "All Subjects" category. Keep only the per-category summary rows so the
    # bar chart shows true category totals (not double-counted, and without a
    # bogus grand-total bar). "All AP Tests" never appears in this file — the
    # real aggregate label is "All Subjects".
    latest = ap_lehs[
        (ap_lehs["SY"] == latest_year)
        & (ap_lehs["SUBJ_CAT"] != "All Subjects")
        & (ap_lehs["SUBJ"] == ap_lehs["SUBJ_CAT"])
    ].copy()

    st.subheader(f"AP tests taken by subject category — SY {latest_year}")
    cat = latest.groupby("SUBJ_CAT")["TESTS_TAKEN"].sum().reset_index().sort_values("TESTS_TAKEN", ascending=False)
    if not cat.empty:
        fig = px.bar(cat, x="SUBJ_CAT", y="TESTS_TAKEN",
                     color_discrete_sequence=[LEHS_NAVY])
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Tests taken", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    # Score distribution for All Subjects
    st.subheader("AP score distribution — All Subjects")
    all_subj = ap_lehs[(ap_lehs["SUBJ_CAT"] == "All AP Tests") | (ap_lehs["SUBJ"] == "All Subjects")]
    if not all_subj.empty:
        for_scoring = all_subj.sort_values("SY")
        score_long = for_scoring.melt(
            id_vars="SY",
            value_vars=["SCORE_1", "SCORE_2", "SCORE_3", "SCORE_4", "SCORE_5"],
            var_name="Score", value_name="Count",
        )
        score_long["Score"] = score_long["Score"].str.replace("SCORE_", "")
        # Sequential ramp: a higher AP score is simply better, so shade it
        # light (low) -> dark (high) rather than a red/blue diverging scheme
        # that wrongly implies the two ends are opposite-valenced.
        fig = px.bar(
            score_long, x="SY", y="Count", color="Score", barmode="stack",
            category_orders={"Score": ["1", "2", "3", "4", "5"]},
            color_discrete_map={
                "1": "#DEEBF7", "2": "#9ECAE1", "3": "#6BAED6",
                "4": "#3182BD", "5": "#08519C",
            },
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Tests")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Scores 3, 4, 5 are typically considered 'passing' / college-credit-eligible.")

# AP equity: who's in AP?
st.subheader("AP Access by Student Group")

ap_groups = ap[
    (ap["ORG_CODE"] == LEHS_SCHOOL_CODE)
    & (ap["SUBJ"] == "All Subjects")
].copy()
ap_groups["STU_GRP"] = ap_groups["STU_GRP"].astype(str).str.replace("\xa0", " ")
ap_groups["PCT_3_5"] = pd.to_numeric(ap_groups["PCT_3_5"], errors="coerce")

groups_focus = [
    "All Students", "English Learners", "Hispanic or Latino",
    "Black or African American", "Asian", "White", "Low Income",
    "Students with Disabilities",
]
ap_groups = ap_groups[ap_groups["STU_GRP"].isin(groups_focus)]

if not ap_groups.empty:
    latest_ap = ap_groups[ap_groups["SY"] == ap_groups["SY"].max()].copy()
    latest_ap = latest_ap.sort_values("TESTS_TAKEN", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=latest_ap["STU_GRP"], y=latest_ap["TESTS_TAKEN"],
        name="Tests taken", marker_color=LEHS_NAVY,
    ))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Tests taken (latest year)",
                      title="AP tests taken by student group at LEHS")
    st.plotly_chart(fig, use_container_width=True)

    # AP pass rate (PCT_3_5) by subgroup — the equity story access alone misses.
    # Access = how many students sat for an exam. Pass rate = how many of those
    # earned a college-credit-eligible score (3+). Both matter; pass rate is
    # often the gap most amenable to instructional intervention.
    pass_by_grp = latest_ap.dropna(subset=["PCT_3_5"]).sort_values("PCT_3_5", ascending=True)
    if not pass_by_grp.empty:
        st.markdown(f"**AP pass rate (% scoring 3+) by student group — SY {sy_label(int(pass_by_grp['SY'].max()))}**")
        pass_by_grp["label"] = pass_by_grp.apply(
            lambda r: f"{r['PCT_3_5']:.0%} ({int(r['TESTS_TAKEN'])} tests)" if pd.notna(r["TESTS_TAKEN"]) else f"{r['PCT_3_5']:.0%}",
            axis=1,
        )
        fig = px.bar(
            pass_by_grp, x="PCT_3_5", y="STU_GRP", orientation="h", text="label",
        )
        fig.update_traces(marker_color=LEHS_GOLD, textposition="outside", cliponaxis=False)
        all_rate = latest_ap[latest_ap["STU_GRP"] == "All Students"]["PCT_3_5"]
        if not all_rate.empty and pd.notna(all_rate.iloc[0]):
            fig.add_vline(
                x=all_rate.iloc[0], line_dash="dash", line_color=LEHS_NAVY,
                annotation_text="All-students rate", annotation_position="top",
            )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_tickformat=".0%", xaxis_title="% of exams scoring 3+ (college-credit-eligible)",
            yaxis_title="", height=max(360, 28 * len(pass_by_grp)),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Pass rate (scoring 3 or higher) is what makes an AP exam count for "
            "college credit. The DESE subgroup label \"Economically Disadvantaged\" "
            "was renamed \"Low Income\" in 2022 — older charts may use the prior "
            "name for the same group."
        )

    # AP pass rate by subject — which AP courses are LEHS strong/weak at?
    ap_subj = ap[
        (ap["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (ap["STU_GRP"] == "All Students")
        & (ap["SUBJ"] != "All Subjects")
    ].copy()
    if not ap_subj.empty:
        latest_subj_year = int(ap_subj["SY"].max())
        ap_subj_latest = ap_subj[
            (ap_subj["SY"] == latest_subj_year) & (ap_subj["TESTS_TAKEN"] >= 5)
        ].dropna(subset=["PCT_3_5"]).sort_values("PCT_3_5", ascending=True)
        if not ap_subj_latest.empty:
            st.markdown(f"**AP pass rate by subject — SY {sy_label(latest_subj_year)}** (subjects with ≥5 takers)")
            ap_subj_latest["label"] = ap_subj_latest.apply(
                lambda r: f"{r['PCT_3_5']:.0%} ({int(r['TESTS_TAKEN'])})", axis=1
            )
            fig = px.bar(
                ap_subj_latest, x="PCT_3_5", y="SUBJ", orientation="h", text="label",
                color="SUBJ_CAT",
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_tickformat=".0%",
                xaxis_title="% scoring 3+",
                yaxis_title="", legend_title="Subject area",
                height=max(360, 24 * len(ap_subj_latest)),
            )
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# AP Participation (37cp-pad8) — how many students sit for AP, and how many
# exams they take. Distinct from AP *performance* (score mix) shown above.
# ---------------------------------------------------------------------------

st.header("AP Participation")
st.caption(
    "Beyond how students *score*, how many sit for AP at all? DESE's AP "
    "Participation file counts unique test-takers and total exams (all subjects)."
)

ap_part = load_dataset("ap_participation")
if ap_part.empty:
    st.info("AP-participation data is temporarily unavailable.")
else:
    lehs_ap = ap_part[(ap_part["ORG_CODE"] == LEHS_SCHOOL_CODE)
                      & (ap_part["STU_GRP"] == "All Students")].sort_values("SY")
    if not lehs_ap.empty:
        cur = lehs_ap.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"LEHS AP test-takers (SY {int(cur['SY'])})", f"{int(cur['TEST_TAKERS_CNT']):,}")
        c2.metric("AP exams taken", f"{int(cur['TESTS_TAKEN_CNT']):,}")
        c3.metric("Exams per test-taker", f"{cur['EXAMS_PER_TAKER']:.2f}")

        m = lehs_ap.melt(id_vars="SY", value_vars=["TEST_TAKERS_CNT", "TESTS_TAKEN_CNT"],
                         var_name="Measure", value_name="Count")
        m["Measure"] = m["Measure"].map({"TEST_TAKERS_CNT": "Test-takers",
                                         "TESTS_TAKEN_CNT": "Exams taken"})
        fig = px.line(m, x="SY", y="Count", color="Measure", markers=True,
                      color_discrete_map={"Test-takers": LEHS_NAVY, "Exams taken": LEHS_GOLD})
        fig.update_layout(**DEFAULT_LAYOUT,
                          title="AP participation at Lynn English over time",
                          yaxis_title="Students / exams", xaxis_title="School Year")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Opportunity & course access — an EQUITY lens on who gets to TAKE rigorous
# coursework, not how they score. DESE's DLCS (digital-literacy / computer-
# science) and Arts course-taking dashboards report, per school x subgroup x
# year, the share of enrolled students taking one or more such courses. The
# gap between subgroups (and vs the statewide rate) is the access story.
# ---------------------------------------------------------------------------

st.header("Opportunity & Course Access")
st.caption(
    "Beyond performance: *who gets the chance* to take computer-science and "
    "arts coursework at all. These are DESE's DLCS (Digital Literacy & Computer "
    "Science) and Arts course-taking dashboards — each shows the share of "
    "enrolled students taking one or more courses in that area. Reading them "
    "side by side, by student group, is an access-and-equity lens. Source: "
    "DESE E2C (datasets fbdq-3q4d and w3f3-phkq)."
)

# Subgroups to surface as the access/equity lens: All Students plus the
# race/EL/disability/income groups (the DESE labels used in these two files).
_ACCESS_GROUPS = [
    "All Students", "Hispanic or Latino", "Black or African American", "Asian",
    "White", "Multi-Race, Not Hispanic or Latino", "English Learners",
    "Students with Disabilities", "Low Income", "High Needs",
]


def _course_access_block(name: str, pct_col: str, area_label: str,
                          x_axis_label: str, key_slug: str) -> None:
    """Render the latest-year by-subgroup access bar (vs the MA rate) plus a
    short All-Students trend, for one course-access dataset at LEHS."""
    df = load_dataset(name)
    if df.empty:
        st.info(f"{area_label} course-access data is temporarily unavailable.")
        return
    df = df.copy()
    df["STU_GRP"] = df["STU_GRP"].astype(str).str.replace("\xa0", " ")
    df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce")

    lehs = df[df["ORG_CODE"] == LEHS_SCHOOL_CODE]
    if lehs.empty:
        st.info(f"No LEHS {area_label.lower()} course-access rows.")
        return
    latest_sy = int(lehs["SY"].max())

    # Latest-year share by subgroup at LEHS, sorted low→high so the most
    # under-served groups sit at the bottom of the horizontal bars.
    grp = (
        lehs[(lehs["SY"] == latest_sy) & lehs["STU_GRP"].isin(_ACCESS_GROUPS)]
        .dropna(subset=[pct_col])
        .sort_values(pct_col, ascending=True)
    )
    # Statewide All-Students rate for the same year = the reference line.
    state_all = df[
        (df["ORG_TYPE"] == "State")
        & (df["STU_GRP"] == "All Students")
        & (df["SY"] == latest_sy)
    ][pct_col]
    ma_rate = float(state_all.iloc[0]) if not state_all.empty and pd.notna(state_all.iloc[0]) else None

    if not grp.empty:
        st.markdown(
            f"**LEHS {area_label} course participation by student group — "
            f"SY {sy_label(latest_sy)}**"
        )
        grp = grp.assign(label=grp[pct_col].map(lambda x: f"{x:.0%}"))
        fig = px.bar(grp, x=pct_col, y="STU_GRP", orientation="h", text="label")
        fig.update_traces(marker_color=LEHS_GOLD, textposition="outside", cliponaxis=False)
        if ma_rate is not None:
            fig.add_vline(
                x=ma_rate, line_dash="dash", line_color=LEHS_NAVY,
                annotation_text=f"MA rate ({ma_rate:.0%})", annotation_position="top",
            )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_tickformat=".0%", xaxis_title=x_axis_label,
            yaxis_title="", height=max(340, 30 * len(grp)),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"ca_grp_{key_slug}")

    # Short trend — LEHS vs Massachusetts, All Students, when >1 year exists.
    lehs_all = (
        lehs[lehs["STU_GRP"] == "All Students"][["SY", pct_col]]
        .dropna().sort_values("SY")
    )
    if len(lehs_all) > 1:
        state_all_yrs = (
            df[(df["ORG_TYPE"] == "State") & (df["STU_GRP"] == "All Students")]
            [["SY", pct_col]].dropna().sort_values("SY")
        )
        rows = []
        for scope, frame in [("LEHS", lehs_all), ("Massachusetts", state_all_yrs)]:
            if not frame.empty:
                rows.append(frame.assign(Scope=scope))
        if rows:
            trend = pd.concat(rows, ignore_index=True)
            trend = trend.assign(label=trend[pct_col].map(lambda x: f"{x:.0%}"))
            fig = px.line(
                trend.sort_values(["Scope", "SY"]),
                x="SY", y=pct_col, color="Scope", markers=True, text="label",
                color_discrete_map={"LEHS": LEHS_GOLD, "Massachusetts": STATE_COLOR},
            )
            fig.update_traces(textposition="top center", textfont=dict(size=10))
            fig.update_layout(
                **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                yaxis_title=f"% taking any {area_label.lower()} course",
                xaxis_title="School Year",
            )
            st.plotly_chart(fig, use_container_width=True, key=f"ca_trend_{key_slug}")


col_cs, col_arts = st.columns(2)
with col_cs:
    st.subheader("Computer science (DLCS)")
    _course_access_block(
        "dlcs_course_taking", "ALL_GRADES_PCT",
        area_label="computer-science", key_slug="dlcs",
        x_axis_label="% taking ≥1 digital-literacy / CS course",
    )
with col_arts:
    st.subheader("Arts")
    _course_access_block(
        "arts_course_taking", "ALL_GRDS_PCT",
        area_label="arts", key_slug="arts",
        x_axis_label="% taking ≥1 arts course",
    )

st.caption(
    "An access lens, not an outcome: these bars show how many students *enroll "
    "in* a computer-science or arts course, by group. Small subgroups (e.g. "
    "American Indian / Alaska Native, often single-digit counts) are omitted "
    "here to avoid over-reading a few students; download the data below for the "
    "full breakdown."
)

st.divider()

# ---------------------------------------------------------------------------
# Advanced Course Completion — DESE's measure of HS course rigor: % of 11th &
# 12th graders who completed an advanced course (AP, IB, dual enrollment,
# Project Lead The Way, etc.) in any subject. Broader than AP alone.
# ---------------------------------------------------------------------------

st.header("Advanced Course Completion")
st.caption(
    "DESE counts a student as completing an *advanced course* if they finished "
    "an AP, IB, dual-enrollment, or Project Lead The Way course (or one of "
    "several other state-recognized rigorous options). This is broader than "
    "AP alone — it captures the full set of \"college-rigor\" experiences "
    "across all 11th and 12th graders."
)

adv = load_dataset("advanced_course_completion")
if not adv.empty:
    lehs_adv = adv[
        (adv["ORG_CODE"] == LEHS_SCHOOL_CODE) & (adv["STU_GRP"] == "All Students")
    ].sort_values("SY")
    dist_adv = adv[
        (adv["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (adv["ORG_TYPE"] == "District")
        & (adv["STU_GRP"] == "All Students")
    ].sort_values("SY")
    state_adv = adv[
        (adv["ORG_TYPE"] == "State") & (adv["STU_GRP"] == "All Students")
    ].sort_values("SY")

    if not lehs_adv.empty:
        latest_adv = lehs_adv.iloc[-1]
        prior_adv = lehs_adv.iloc[-2] if len(lehs_adv) > 1 else None
        latest_sy_adv = int(latest_adv["SY"])

        c1, c2 = st.columns(2)
        with c1:
            comp_delta = ""
            if prior_adv is not None and pd.notna(prior_adv["ADV_COMP_PCT"]):
                d = (latest_adv["ADV_COMP_PCT"] - prior_adv["ADV_COMP_PCT"]) * 100
                comp_delta = f"{d:+.1f} pts vs SY {sy_label(int(prior_adv['SY']))}"
            st.metric(
                f"Completed any advanced course (SY {sy_label(latest_sy_adv)})",
                f"{latest_adv['ADV_COMP_PCT']:.0%}" if pd.notna(latest_adv["ADV_COMP_PCT"]) else "—",
                comp_delta,
            )
        with c2:
            st.metric(
                "Of 11th + 12th grade students",
                f"{int(latest_adv['G11_G12_CNT']):,}" if pd.notna(latest_adv["G11_G12_CNT"]) else "—",
            )

        # Trend: LEHS vs Lynn district vs MA state
        trend_rows = []
        for scope_name, frame in [("LEHS", lehs_adv), ("Lynn District", dist_adv), ("Massachusetts", state_adv)]:
            sub = frame[["SY", "ADV_COMP_PCT"]].dropna().copy()
            if not sub.empty:
                sub["Scope"] = scope_name
                trend_rows.append(sub)
        if trend_rows:
            trend_df = pd.concat(trend_rows, ignore_index=True)
            trend_df["label"] = trend_df["ADV_COMP_PCT"].apply(lambda x: f"{x:.0%}")
            fig = px.line(
                trend_df.sort_values(["Scope", "SY"]),
                x="SY", y="ADV_COMP_PCT", color="Scope", markers=True, text="label",
                color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District": LEHS_NAVY, "Massachusetts": "#455A64"},
            )
            fig.update_traces(textposition="top center", textfont=dict(size=10))
            fig.update_layout(
                **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                yaxis_title="% of 11–12 graders completing an advanced course",
                xaxis_title="School Year",
            )
            st.plotly_chart(fig, use_container_width=True)

        # By subject area — where is LEHS rigor strong vs weak?
        SUBJ_AREA_COLS = {
            "ADV_ELA_PCT":   "English Language Arts",
            "ADV_MATH_PCT":  "Math",
            "ADV_SCI_PCT":   "Science",
            "ADV_HSS_PCT":   "History & Social Science",
            "ADV_CIS_PCT":   "Computer & Info Sciences",
            "ADV_ART_PCT":   "Arts",
            "ADV_OTHER_PCT": "Other",
        }
        subj_rows = []
        for col, label in SUBJ_AREA_COLS.items():
            val = latest_adv.get(col)
            if pd.notna(val):
                subj_rows.append({"Subject area": label, "Pct": val})
        if subj_rows:
            st.markdown(f"**By subject area — LEHS SY {sy_label(latest_sy_adv)}**")
            subj_df = pd.DataFrame(subj_rows).sort_values("Pct", ascending=True)
            subj_df["label"] = subj_df["Pct"].apply(lambda x: f"{x:.0%}")
            fig = px.bar(
                subj_df, x="Pct", y="Subject area", orientation="h", text="label",
            )
            fig.update_traces(marker_color=LEHS_NAVY, textposition="outside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                xaxis_title="% of 11–12 graders completing an advanced course in that area",
                yaxis_title="",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "A student can complete advanced courses in multiple subject areas, "
                "so the per-area percentages don't sum to the overall completion rate."
            )

st.divider()

# ---------------------------------------------------------------------------
# MassCore Completion
# ---------------------------------------------------------------------------

st.header("MassCore Completion Rate")
st.caption(
    "MassCore is MA's recommended program of study (4 yrs English, 4 yrs math, "
    "3 lab science, 3 history, 2 yrs same world language, 1 arts, 5 core electives). "
    "Completion is a strong proxy for college readiness."
)

mc = masscore[masscore["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
mc["STU_GRP"] = mc["STU_GRP"].astype(str).str.replace("\xa0", " ")
mc_groups = mc[mc["STU_GRP"].isin([
    "All Students", "English Learners", "Hispanic or Latino",
    "Black or African American", "White", "Low Income", "High Needs",
])].copy()

if not mc_groups.empty:
    fig = px.line(
        mc_groups.sort_values("SY"), x="SY", y="PCT_COMPL_MASSCORE",
        color="STU_GRP", markers=True,
        color_discrete_map={
            "All Students":               LEHS_NAVY,
            "English Learners":           SUBGROUP_PALETTE["English Learner"],
            "Hispanic or Latino":         SUBGROUP_PALETTE["Hispanic/Latino"],
            "Black or African American":  SUBGROUP_PALETTE["African American/Black"],
            "White":                      SUBGROUP_PALETTE["White"],
            "Low Income":                 SUBGROUP_PALETTE["Low Income"],
            "High Needs":                 SUBGROUP_PALETTE["High Needs"],
        },
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="MassCore Completion Rate")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "The near-zero dips in SY 2020-21 (0.2%) and SY 2022-23 (5.5%) reflect "
        "pandemic-era disruption to MassCore course completion and reporting, "
        "not a real collapse in college-prep coursework — completion returned "
        "to its usual ~22-25% range in the surrounding years. Treat those two "
        "years as not comparable."
    )

st.divider()

# ---------------------------------------------------------------------------
# SAT — full performance dataset (takers, RW, Math) for LEHS + Lynn + state.
# Lynn shifted to school-day SAT in SY 2024-25, which spikes the takers count
# and depresses average scores because the testing pool now includes
# non-college-bound students who previously opted out. Surface that inline.
# ---------------------------------------------------------------------------

st.header("SAT Performance")

sat_perf = load_dataset("sat_performance")
if not sat_perf.empty:
    lehs_sat = sat_perf[
        (sat_perf["ORG_CODE"] == LEHS_SCHOOL_CODE) & (sat_perf["STU_GRP"] == "All Students")
    ].sort_values("SY")
    dist_sat = sat_perf[
        (sat_perf["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (sat_perf["ORG_TYPE"] == "District")
        & (sat_perf["STU_GRP"] == "All Students")
    ].sort_values("SY")
    state_sat = sat_perf[
        (sat_perf["ORG_TYPE"] == "State") & (sat_perf["STU_GRP"] == "All Students")
    ].sort_values("SY")

    if not lehs_sat.empty:
        latest_sat = lehs_sat.iloc[-1]
        prior_sat = lehs_sat.iloc[-2] if len(lehs_sat) > 1 else None
        latest_sy_sat = int(latest_sat["SY"])

        c1, c2, c3 = st.columns(3)
        with c1:
            takers_delta = ""
            if prior_sat is not None and pd.notna(prior_sat["TAKEN_CNT"]):
                d = int(latest_sat["TAKEN_CNT"]) - int(prior_sat["TAKEN_CNT"])
                takers_delta = f"{d:+,} vs SY {sy_label(int(prior_sat['SY']))}"
            st.metric(
                f"Test takers (SY {sy_label(latest_sy_sat)})",
                f"{int(latest_sat['TAKEN_CNT']):,}" if pd.notna(latest_sat["TAKEN_CNT"]) else "—",
                takers_delta,
                delta_color="off",
            )
        with c2:
            rw_delta = ""
            if prior_sat is not None and pd.notna(prior_sat["READ_WRITE_SCORE"]):
                d = latest_sat["READ_WRITE_SCORE"] - prior_sat["READ_WRITE_SCORE"]
                rw_delta = f"{d:+.0f} pts vs SY {sy_label(int(prior_sat['SY']))}"
            st.metric(
                "Reading & Writing — mean",
                f"{latest_sat['READ_WRITE_SCORE']:.0f}" if pd.notna(latest_sat["READ_WRITE_SCORE"]) else "—",
                rw_delta,
                delta_color="off",
            )
        with c3:
            m_delta = ""
            if prior_sat is not None and pd.notna(prior_sat["MATH_SCORE"]):
                d = latest_sat["MATH_SCORE"] - prior_sat["MATH_SCORE"]
                m_delta = f"{d:+.0f} pts vs SY {sy_label(int(prior_sat['SY']))}"
            st.metric(
                "Math — mean",
                f"{latest_sat['MATH_SCORE']:.0f}" if pd.notna(latest_sat["MATH_SCORE"]) else "—",
                m_delta,
                delta_color="off",
            )

        # Lynn moved to school-day SAT in SY 2024-25 — surface that context now
        # if the latest year shows the characteristic takers-up-scores-down signature.
        if prior_sat is not None:
            t_now, t_prev = latest_sat.get("TAKEN_CNT"), prior_sat.get("TAKEN_CNT")
            if pd.notna(t_now) and pd.notna(t_prev) and t_prev > 0 and t_now / t_prev >= 2.0:
                st.warning(
                    f"**SY {sy_label(latest_sy_sat)} is a school-day SAT year for Lynn Public Schools** — "
                    f"all eligible LEHS juniors tested during the school day rather than opting in. "
                    f"The takers count {int(t_prev):,} → {int(t_now):,} jump (and the corresponding score "
                    f"drop) reflects a wider testing pool, not a quality change."
                )

        # Trend: LEHS vs Lynn district vs MA state, both subjects
        trend_rows = []
        for scope_name, frame in [("LEHS", lehs_sat), ("Lynn District", dist_sat), ("Massachusetts", state_sat)]:
            for col, subj in [("READ_WRITE_SCORE", "Reading & Writing"), ("MATH_SCORE", "Math")]:
                sub = frame[["SY", col]].dropna().copy()
                if sub.empty:
                    continue
                sub = sub.rename(columns={col: "Score"})
                sub["Scope"] = scope_name
                sub["Subject"] = subj
                trend_rows.append(sub)

        if trend_rows:
            trend_df = pd.concat(trend_rows, ignore_index=True)
            for subj in ["Reading & Writing", "Math"]:
                sub_trend = trend_df[trend_df["Subject"] == subj]
                if sub_trend.empty:
                    continue
                st.markdown(f"**{subj} — trend by scope**")
                fig = px.line(
                    sub_trend.sort_values(["Scope", "SY"]),
                    x="SY", y="Score", color="Scope", markers=True,
                    color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District": LEHS_NAVY, "Massachusetts": "#455A64"},
                )
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_title=f"Mean {subj} score",
                    xaxis_title="School Year",
                    yaxis_range=[300, 650],
                )
                st.plotly_chart(fig, use_container_width=True)

        # Subgroup breakdown — latest year
        sub = sat_perf[
            (sat_perf["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (sat_perf["SY"] == latest_sy_sat)
            & (sat_perf["STU_GRP"] != "All Students")
        ].dropna(subset=["READ_WRITE_SCORE", "MATH_SCORE"], how="all").copy()
        if not sub.empty:
            st.markdown(f"**LEHS SAT scores by student group — SY {sy_label(latest_sy_sat)}**")
            sub_long = sub.melt(
                id_vars=["STU_GRP", "TAKEN_CNT"],
                value_vars=["READ_WRITE_SCORE", "MATH_SCORE"],
                var_name="Subject", value_name="Score",
            ).dropna(subset=["Score"])
            sub_long["Subject"] = sub_long["Subject"].map(
                {"READ_WRITE_SCORE": "Reading & Writing", "MATH_SCORE": "Math"}
            )
            sub_long["label"] = sub_long.apply(
                lambda r: f"{r['Score']:.0f} (n={int(r['TAKEN_CNT'])})" if pd.notna(r["TAKEN_CNT"]) else f"{r['Score']:.0f}",
                axis=1,
            )
            rw_order = (
                sub_long[sub_long["Subject"] == "Reading & Writing"]
                .sort_values("Score")["STU_GRP"]
                .tolist()
            )
            fig = px.bar(
                sub_long, x="Score", y="STU_GRP", color="Subject",
                orientation="h", barmode="group", text="label",
                color_discrete_map={"Reading & Writing": "#1976D2", "Math": "#D32F2F"},
                category_orders={"STU_GRP": rw_order},
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_title="Mean SAT score (200–800 scale)",
                yaxis_title="",
                xaxis_range=[200, 800],
                height=max(380, 28 * sub_long["STU_GRP"].nunique()),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.caption(sat_methodology_note())

st.divider()

# (AP "LEHS vs LCHS" section moved out: Lynn Tech and the alternative
# academies don't run comparable AP programs, so a Lynn-HS comparison was
# always going to be lopsided. AP equity belongs in school-to-school
# context — see Compare > Lynn Schools for the scorecard view.)

# ---------------------------------------------------------------------------
# Pathway program participation
# ---------------------------------------------------------------------------

st.header("Pathway Programs")
st.caption(
    "CTE (Career Technical Education), Early College, and Innovation Career "
    "Pathways are designated programs that give HS students a head start on "
    "post-secondary credits and career exploration."
)

if not pathways.empty:
    p = pathways[pathways["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    if not p.empty:
        # The file lists, per pathway, both a pathway-summary row and its
        # individual sub-program rows (and the labels drift year to year). The
        # pathway-level total is always the largest count within each
        # (SY, PATHWAY) group, so take the max to get one clean number per
        # pathway per year without summing sub-programs.
        p["PROGRAM_CNT"] = pd.to_numeric(p["PROGRAM_CNT"], errors="coerce")
        PATHWAY_LABELS = {
            "Early College": "Early College",
            "Career Technical Education (Chapter 74 Programs)": "Career Tech Ed (Ch. 74)",
            "After Dark": "After Dark (evening CTE)",
        }
        pw = p[p["PATHWAY"].isin(PATHWAY_LABELS)].copy()
        pw["Pathway"] = pw["PATHWAY"].map(PATHWAY_LABELS)
        pw_totals = (
            pw.groupby(["SY", "Pathway"], as_index=False)["PROGRAM_CNT"].max()
            .rename(columns={"PROGRAM_CNT": "Students"})
            .dropna(subset=["Students"])
        )
        if not pw_totals.empty:
            pw_totals["Students"] = pw_totals["Students"].astype(int)
            st.subheader("LEHS students in designated pathways, by year")
            fig = px.bar(
                pw_totals.sort_values(["SY", "Pathway"]),
                x="SY", y="Students", color="Pathway", barmode="group",
                text="Students",
                color_discrete_map={
                    "Early College": LEHS_NAVY,
                    "Career Tech Ed (Ch. 74)": LEHS_GOLD,
                    "After Dark (evening CTE)": "#7B9E89",
                },
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT, yaxis_title="Students enrolled",
                xaxis_title="School Year", legend_title="Pathway",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Counts are students enrolled in each designated pathway. Early "
                "College is by far the largest at LEHS and has roughly doubled "
                "since SY 2021-22. The Chapter 74 career-tech programs are "
                "delivered through the after-school \"After Dark\" model, so "
                "those two bars count the same students."
            )
    else:
        st.info("No LEHS pathways enrollment data (program may not be designated here).")

# Early College specifically — participants by partner college over time
if not ec_part.empty:
    ec_lehs = ec_part[
        (ec_part["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (ec_part["STU_GRP"] == "All Students")
    ].copy()
    if not ec_lehs.empty:
        st.subheader("Early College participation — by partner college")
        ec_lehs["ALL_CNT"] = pd.to_numeric(ec_lehs["ALL_CNT"], errors="coerce")
        # Each student is reported in both a Fall and a Spring term; use the
        # Fall snapshot (fall back to Spring when a year has no Fall row) so we
        # count participants once rather than summing the two terms.
        ec_lehs["_per_rank"] = ec_lehs["PERIOD"].map({"Fall": 0, "Spring": 1})
        ec_snap = (
            ec_lehs.sort_values("_per_rank")
            .groupby(["SY", "CEEB_NAME"], as_index=False)
            .first()
        )
        ec_snap["Partner"] = ec_snap["CEEB_NAME"].replace(
            {"No Data": "Partner not reported"}
        )
        ec_snap = ec_snap.dropna(subset=["ALL_CNT"])
        if not ec_snap.empty:
            ec_snap["ALL_CNT"] = ec_snap["ALL_CNT"].astype(int)
            fig = px.bar(
                ec_snap.sort_values(["SY", "Partner"]),
                x="SY", y="ALL_CNT", color="Partner", barmode="stack",
                text="ALL_CNT",
                color_discrete_sequence=[LEHS_NAVY, LEHS_GOLD, "#9AA7B8"],
            )
            fig.update_traces(textposition="inside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT, yaxis_title="Students participating",
                xaxis_title="School Year", legend_title="Partner college",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Lynn English partners with North Shore Community College and "
                "Salem State University so students can earn college credit "
                "while still in high school. Participation has grown steadily, "
                "from about 50 students in SY 2020-21 to more than 330 in "
                "SY 2023-24. (The earliest year predates the named partnerships.)"
            )

st.divider()

# ---------------------------------------------------------------------------
# Early college credits earned — by partner CEEB
# ---------------------------------------------------------------------------

st.header("Early College Credits — Lynn District")
st.caption(
    "Above is *participation* (any rows = participating). This section is the "
    "*credit volume*: how many college credits Lynn HS students actually "
    "earn each year, broken out by partner CEEB college. Source: "
    "*Early College Credits* dataset."
)

early_credits = load_dataset("early_college_credits")
if not early_credits.empty:
    ec_lynn = early_credits[early_credits["DIST_CODE"] == "01630000"].copy()
    ec_lynn["EARNED_CREDIT_CNT"] = pd.to_numeric(ec_lynn["EARNED_CREDIT_CNT"], errors="coerce")
    ec_lynn["REG_CREDITS_CNT"] = pd.to_numeric(ec_lynn["REG_CREDITS_CNT"], errors="coerce")
    ec_lynn["STU_CNT"] = pd.to_numeric(ec_lynn["STU_CNT"], errors="coerce")

    # Filter to All Students rows, latest year
    ec_all = ec_lynn[ec_lynn["STU_GRP"] == "All Students"].copy()
    if not ec_all.empty:
        latest_ec = int(ec_all["SY"].max())
        ec_latest = ec_all[ec_all["SY"] == latest_ec].copy()
        # Sum across periods if both Fall and Spring present
        ec_agg = (
            ec_latest.groupby("CEEB_NAME", as_index=False)
                     .agg(STU_CNT=("STU_CNT", "sum"),
                          REG_CREDITS_CNT=("REG_CREDITS_CNT", "sum"),
                          EARNED_CREDIT_CNT=("EARNED_CREDIT_CNT", "sum"))
                     .dropna(subset=["EARNED_CREDIT_CNT"])
                     .sort_values("EARNED_CREDIT_CNT")
        )
        if not ec_agg.empty:
            st.subheader(f"Credits earned by partner college (SY {latest_ec - 1}-{str(latest_ec)[-2:]})")
            ec_agg["pass_rate"] = ec_agg["EARNED_CREDIT_CNT"] / ec_agg["REG_CREDITS_CNT"]
            fig = px.bar(
                ec_agg, y="CEEB_NAME", x="EARNED_CREDIT_CNT", orientation="h",
                color="pass_rate", color_continuous_scale="Greens",
                hover_data={"STU_CNT": True, "REG_CREDITS_CNT": True, "pass_rate": ":.0%"},
                text=ec_agg["EARNED_CREDIT_CNT"].astype(int).astype(str),
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                height=max(280, 36 * len(ec_agg)),
                xaxis_title="Credits earned",
                xaxis_range=[0, ec_agg["EARNED_CREDIT_CNT"].max() * 1.15],
                yaxis_title="",
                coloraxis_colorbar=dict(title="Pass rate"),
            )
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Early-college credit data not available yet.")

st.divider()

# ---------------------------------------------------------------------------
# College + career outcomes — what happens to Lynn graduates?
# ---------------------------------------------------------------------------

st.header("What happens to Lynn graduates? — Outcome breakdown")
st.caption(
    "DESE's *College and Career Outcomes* dataset tracks each Lynn-district "
    "HS cohort one year out: where they enrolled (in-state public/private "
    "2-yr/4-yr, out-of-state), whether they were employed, or whether their "
    "outcome is missing/unknown."
)

cco = load_dataset("college_career_outcomes")
if not cco.empty:
    cco_lynn = cco[cco["DIST_CODE"] == "01630000"].copy()
    cco_lynn["OUTCOME_CNT"] = pd.to_numeric(cco_lynn["OUTCOME_CNT"], errors="coerce")
    cco_lynn["GRAD_CNT"] = pd.to_numeric(cco_lynn["GRAD_CNT"], errors="coerce")

    if not cco_lynn.empty:
        latest_cco_year = int(cco_lynn["HS_GRAD_YEAR"].max())
        # Pick the row where OUTCOME_YEAR matches HS_GRAD_YEAR (one year out view)
        snap = cco_lynn[
            (cco_lynn["HS_GRAD_YEAR"] == latest_cco_year)
            & (cco_lynn["OUTCOME_YEAR"] == latest_cco_year)
        ].copy()

        if not snap.empty:
            # Drop the Total Postsecondary aggregate (it's the sum of the
            # itemized in-state public/private + out-of-state rows) so the
            # bar chart isn't doubled.
            itemized = snap[~snap["OUTCOME_TYPE"].isin(["Total Postsecondary Enrollment"])].copy()
            itemized = itemized.sort_values("OUTCOME_CNT", ascending=True)
            grad_total = int(snap["GRAD_CNT"].iloc[0])
            itemized["pct_of_cohort"] = itemized["OUTCOME_CNT"] / grad_total
            itemized["label"] = itemized.apply(
                lambda r: (
                    f"{int(r['OUTCOME_CNT']):,} "
                    f"({r['pct_of_cohort']:.0%})"
                ), axis=1,
            )

            st.subheader(
                f"{latest_cco_year} Lynn district cohort — {grad_total:,} grads"
            )
            color_map_outcome = {
                "Total Missing":          "#90A4AE",
                "In-State Public 4-Year": "#1976D2",
                "In-State Public 2-Year": "#42A5F5",
                "In-State Private":       LEHS_NAVY,
                "Out-of-State":           "#7B1FA2",
                "Total Employed":         "#388E3C",
            }
            fig = px.bar(
                itemized, y="OUTCOME_TYPE", x="OUTCOME_CNT", orientation="h",
                color="OUTCOME_TYPE", color_discrete_map=color_map_outcome,
                text="label",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_title="Graduates",
                yaxis_title="",
                showlegend=False,
                height=380,
            )
            st.plotly_chart(fig, use_container_width=True)

            missing_pct = float(
                itemized.loc[itemized["OUTCOME_TYPE"] == "Total Missing", "pct_of_cohort"].iloc[0]
            ) if (itemized["OUTCOME_TYPE"] == "Total Missing").any() else None
            if missing_pct is not None and missing_pct > 0.25:
                st.warning(
                    f"**Note:** {missing_pct:.0%} of the cohort has no "
                    f"reportable outcome (not enrolled in any tracked "
                    f"institution, no W-2 earnings, or simply unmatched). "
                    f"That suppression bites hardest at the bottom of the "
                    f"pipeline — students with missing outcomes are "
                    f"disproportionately likely to be disconnected."
                )
else:
    st.info("College/career outcomes data not available yet.")

st.divider()

# ---------------------------------------------------------------------------
# Where Lynn grads land (IPEDS / College Scorecard)
# ---------------------------------------------------------------------------

st.header("Where Lynn grads land — destination college profiles")
st.caption(
    "Top colleges Lynn graduates enroll in, with institutional data from the "
    "federal College Scorecard / IPEDS. Source: scripts/05_download_ipeds.py."
)

ipeds = load_dataset("ipeds_destinations")
if ipeds.empty:
    st.info(
        "Destination college data not yet populated. The ingest scaffold is "
        "at scripts/05_download_ipeds.py — it queries College Scorecard's "
        "free API; rate-limited demo key may return empty."
    )
else:
    display_cols = {
        "INSTITUTION": "Institution",
        "STATE": "State",
        "SECTOR": "Sector",
        "GRAD_RATE_150": "Grad rate (150%)",
        "COST_IN_STATE": "In-state cost",
        "COST_OUT_STATE": "Out-of-state cost",
        "PELL_PCT": "% Pell recipients",
        "BLACK_PCT": "% Black",
        "HISP_PCT": "% Hispanic",
        "WHITE_PCT": "% White",
        "ASIAN_PCT": "% Asian",
    }
    have = [c for c in display_cols if c in ipeds.columns]
    display = ipeds[have].rename(columns=display_cols).copy()
    for c in ["Grad rate (150%)", "% Pell recipients", "% Black", "% Hispanic",
              "% White", "% Asian"]:
        if c in display.columns:
            display[c] = display[c].apply(
                lambda x: f"{x:.0%}" if pd.notna(x) and isinstance(x, (int, float)) else "—"
            )
    for c in ["In-state cost", "Out-of-state cost"]:
        if c in display.columns:
            display[c] = display[c].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) and isinstance(x, (int, float)) else "—"
            )
    st.dataframe(display, use_container_width=True, hide_index=True, height=420)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'AP performance': ap,
        'AP participation': load_dataset("ap_participation"),
        'MassCore completion': masscore,
        'Pathways enrollment': pathways,
        'Early College participation': ec_part,
        'DLCS (computer science) course taking': load_dataset("dlcs_course_taking"),
        'Arts course taking': load_dataset("arts_course_taking"),
        'IPEDS destinations': ipeds,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

