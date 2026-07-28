"""Section 2b — Courses & Academics: passing rates, course access, AP, SAT.

Everything academic that is *not* MCAS, gathered here from the former
Academic Performance page (Grade 9 course passing, grade retention) and from
College & Career (AP, SAT, advanced coursework, MassCore, course access) so
the MCAS page can be solely MCAS. Ordered as a story: are students passing
their classes → who gets access to rigorous coursework → how the AP program
is doing → SAT → who gets held back.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    GATEWAY_PEER_COLOR,
    LEHS_GOLD,
    LEHS_NAVY,
    STATE_COLOR,
    SUBGROUP_PALETTE,
    data_downloads_panel,
    span_years,
    with_year_gaps,
)
from utils.constants import AP_SCORE_COLORS, LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE, SUBJECT_PALETTE
from utils.data_loader import load_dataset
from utils.interpret import sat_methodology_note, sy_label
from utils.stats import subgroup_summary_md

st.set_page_config(page_title="Courses & Academics | LEHS", page_icon="📚", layout="wide")
sidebar_attribution()

# Federal CRDC matches on SCHOOL_NAME (string) — the CRDC public-use file has
# no DESE ORG_CODE. These constants + helper drive the advanced-course-
# offerings section (rolled in from the former Civil Rights Data page).
LEHS_CRDC_NAME = "Lynn English High"


def _lehs_row(df: pd.DataFrame) -> "pd.Series | None":
    if df.empty or "SCHOOL_NAME" not in df.columns:
        return None
    hit = df[df["SCHOOL_NAME"].astype(str).str.strip() == LEHS_CRDC_NAME]
    return hit.iloc[0] if not hit.empty else None


st.title("Courses & Academics")
st.markdown(
    "How students are doing in their **courses** — the day-to-day classwork "
    "rather than the state test: Grade 9 passing rates, who gets access to "
    "computer-science, arts, and advanced coursework, AP results and "
    "participation, SAT scores, and grade retention."
)
st.page_link(
    "pages/2_Academic_Performance.py",
    label="Looking for state test results? → MCAS",
)
st.page_link(
    "pages/College_Career_Beyond.py",
    label="Pathways, Early College, FAFSA & graduate outcomes → College & Career",
)

ap = load_dataset("ap_performance")
masscore = load_dataset("masscore_completion")
g9 = load_dataset("grade9_passing")

if g9.empty and ap.empty and masscore.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

st.divider()

# ===========================================================================
# 1. GRADE 9 ON-TRACK — course passing (4sut-78p8)
# ===========================================================================
# Research treats "on-track" freshman year — passing your courses and earning
# enough credits to be promoted to grade 10 — as one of the single strongest
# predictors of on-time graduation. This dataset reports the share of grade-9
# students passing each subject, plus an "All Subjects" rollup per org/year.

st.header("📗 Grade 9 On-Track — Course Passing")
st.caption(
    "Freshman-year course passing is one of the strongest early predictors of "
    "on-time graduation: students who pass their classes and stay on pace in "
    "grade 9 graduate at far higher rates. Each bar is the share of LEHS "
    "grade-9 students passing that subject. **All Subjects** is DESE's combined "
    "on-track rollup. Source: DESE Education-to-Career (Grade 9 Course Passing)."
)

if g9.empty:
    st.info("Grade-9 course-passing data is temporarily unavailable.")
else:
    g9["PASS_PCT"] = pd.to_numeric(g9["PASS_PCT"], errors="coerce")
    g9_lehs_all = g9[
        (g9["ORG_CODE"] == LEHS_SCHOOL_CODE) & (g9["STU_GRP"] == "All Students")
    ].copy()

    if g9_lehs_all.empty:
        st.info("No LEHS grade-9 course-passing rows found.")
    else:
        g9_latest = int(g9_lehs_all["SY"].max())

        # --- (a) Latest-year passing by subject — horizontal bar ---
        st.markdown(f"**Passing Rate by Subject — All Students, SY {sy_label(g9_latest)}**")
        bar = (
            g9_lehs_all[g9_lehs_all["SY"] == g9_latest]
            .dropna(subset=["PASS_PCT"])
            .copy()
        )
        if not bar.empty:
            # Put the All-Subjects rollup at the top, the rest sorted by rate.
            bar["_is_all"] = bar["SUBJ"] == "All Subjects"
            bar = bar.sort_values(["_is_all", "PASS_PCT"], ascending=[True, True])
            bar["label"] = bar["PASS_PCT"].apply(lambda x: f"{x:.0%}")
            bar["color"] = bar["_is_all"].map({True: LEHS_GOLD, False: LEHS_NAVY})
            fig = go.Figure(go.Bar(
                x=bar["PASS_PCT"], y=bar["SUBJ"], orientation="h",
                text=bar["label"], textposition="outside",
                marker_color=bar["color"].tolist(),
                customdata=bar[["G09_CNT"]].values,
                hovertemplate="<b>%{y}</b><br>Passing: %{x:.1%}<br>"
                              "Grade-9 students: %{customdata[0]:,.0f}<extra></extra>",
                cliponaxis=False,
            ))
            fig.update_layout(
                **DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                xaxis_title="Share of grade-9 students passing", yaxis_title="",
                xaxis_range=[0, min(1.08, max(bar["PASS_PCT"].max() * 1.15, 0.1))],
                height=max(320, 42 * len(bar)),
            )
            st.plotly_chart(fig, width="stretch")
            st.caption(
                "Gold = DESE's combined **All Subjects** on-track rate; navy = "
                "individual subjects. A passing rate well below the others flags "
                "the subject where freshmen most often fall off track."
            )

        # --- (b) Overall on-track trend (All Subjects rollup) vs benchmarks ---
        g9_roll_lehs = g9_lehs_all[g9_lehs_all["SUBJ"] == "All Subjects"]
        if not g9_roll_lehs.empty:
            st.markdown("**Overall On-Track Rate Over Time — All Subjects**")
            g9_dist = g9[
                (g9["DIST_CODE"] == LYNN_DISTRICT_CODE)
                & (g9["ORG_TYPE"] == "District")
                & (g9["STU_GRP"] == "All Students")
                & (g9["SUBJ"] == "All Subjects")
            ]
            g9_state = g9[
                (g9["ORG_TYPE"] == "State")
                & (g9["STU_GRP"] == "All Students")
                & (g9["SUBJ"] == "All Subjects")
            ]
            frames = []
            for name, d in [
                ("Lynn English", g9_roll_lehs),
                ("Lynn district", g9_dist),
                ("Massachusetts", g9_state),
            ]:
                if not d.empty:
                    t = with_year_gaps(d[["SY", "PASS_PCT"]].dropna(subset=["PASS_PCT"]), "PASS_PCT")
                    t["Series"] = name
                    frames.append(t)
            if frames:
                tdf = pd.concat(frames, ignore_index=True)
                fig = px.line(
                    tdf, x="SY", y="PASS_PCT", color="Series", markers=True,
                    color_discrete_map={"Lynn English": LEHS_GOLD,
                                        "Lynn district": LEHS_NAVY,
                                        "Massachusetts": STATE_COLOR},
                )
                fig.update_traces(connectgaps=False)
                fig.update_layout(
                    **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                    yaxis_title="% of grade-9 students passing all subjects",
                    xaxis_title="School Year", yaxis_range=[0, 1.02],
                )
                st.plotly_chart(fig, width="stretch")
                st.caption(
                    "LEHS (gold) vs. the Lynn district and statewide on-track "
                    "rate. The spring-2020 point reflects pandemic-era grading "
                    "(many districts adopted pass/no-pass), so read it as an "
                    "anomaly, not a real spike."
                )

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
        st.plotly_chart(fig, width="stretch", key=f"ca_grp_{key_slug}")

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
            st.plotly_chart(fig, width="stretch", key=f"ca_trend_{key_slug}")


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

crosslink_callout(
    "Advanced-coursework completion is one of the indicators DESE rolls into a "
    "school's accountability score, so the access and pass-rate gaps above feed "
    "directly into how LEHS is rated.",
    "Accountability",
    "See the Accountability page",
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
                color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District": LEHS_NAVY, "Massachusetts": STATE_COLOR},
            )
            fig.update_traces(textposition="top center", textfont=dict(size=10))
            fig.update_layout(
                **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                yaxis_title="% of 11–12 graders completing an advanced course",
                xaxis_title="School Year",
            )
            st.plotly_chart(fig, width="stretch")

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
            st.plotly_chart(fig, width="stretch")
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

if masscore.empty:
    st.info("MassCore completion data is temporarily unavailable.")
else:
    mc = masscore[masscore["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    mc["STU_GRP"] = mc["STU_GRP"].astype(str).str.replace("\xa0", " ")
    mc_groups = mc[mc["STU_GRP"].isin([
        "All Students", "English Learners", "Hispanic or Latino",
        "Black or African American", "White", "Low Income", "High Needs",
    ])].copy()

    if not mc_groups.empty:
        # Insert explicit NaN rows for any skipped year (esp. the 2020 COVID gap) so
        # the lines BREAK there rather than drawing straight across — paired with
        # connectgaps=False below.
        mc_plot = with_year_gaps(
            mc_groups, "PCT_COMPL_MASSCORE", group_col="STU_GRP",
            years=span_years(mc_groups),
        )
        fig = px.line(
            mc_plot.sort_values("SY"), x="SY", y="PCT_COMPL_MASSCORE",
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
        fig.update_traces(connectgaps=False)
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                           yaxis_title="MassCore Completion Rate")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "The near-zero dips in SY 2020-21 (0.2%) and SY 2022-23 (5.5%) reflect "
            "pandemic-era disruption to MassCore course completion and reporting, "
            "not a real collapse in college-prep coursework — completion returned "
            "to its usual ~22-25% range in the surrounding years. Treat those two "
            "years as not comparable."
        )

st.divider()

# ---------------------------------------------------------------------------
# AP Performance
# ---------------------------------------------------------------------------

st.header("Advanced Placement Performance")
st.caption(
    "AP courses are college-level classes taken in high school; a year-end "
    "exam score of **3 or higher** (out of 5) is what most colleges accept "
    "for credit. This section covers how many exams LEHS students take, in "
    "what subjects, and how they score — overall and by student group."
)

if ap.empty:
    st.info("AP performance data is temporarily unavailable.")
else:
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
            st.plotly_chart(fig, width="stretch")

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
                color_discrete_map=AP_SCORE_COLORS,
            )
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Tests")
            st.plotly_chart(fig, width="stretch")
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
        st.plotly_chart(fig, width="stretch")

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
            st.plotly_chart(fig, width="stretch")
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
                st.plotly_chart(fig, width="stretch")

    # -----------------------------------------------------------------------
    # AP access vs. success — who is *in the room* vs. who *succeeds*. For each
    # student group, contrast the group's share of AP test-takers with its share of
    # overall enrollment (a representation gap), and overlay the group's % scoring
    # 3+. Test-taker counts come from ap_participation; group enrollment from
    # enrollment_demographics (race groups via PCT × total, EL/Low-Income/SWD via
    # their published _CNT columns); pass rate from ap_performance PCT_3_5.
    # -----------------------------------------------------------------------

    st.subheader("AP access vs. success — who's in the room, and who succeeds")
    st.caption(
        "Two different equity questions sit side by side here. **Access**: does a "
        "group take AP exams in proportion to its share of the school? A group whose "
        "share of test-takers trails its share of enrollment is under-represented in "
        "AP. **Success**: of the exams a group does sit, how many score 3+ "
        "(college-credit-eligible)? Closing the access gap and the success gap are "
        "distinct levers."
    )

    ap_part_eq = load_dataset("ap_participation")
    enr_eq = load_dataset("enrollment_demographics")
    if ap_part_eq.empty or enr_eq.empty:
        st.info("AP-participation or enrollment data is temporarily unavailable.")
    else:
        ap_part_lehs = ap_part_eq[ap_part_eq["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
        ap_part_lehs["STU_GRP"] = ap_part_lehs["STU_GRP"].astype(str).str.replace("\xa0", " ")
        ap_part_lehs["SY"] = pd.to_numeric(ap_part_lehs["SY"], errors="coerce")
        ap_part_lehs["TEST_TAKERS_CNT"] = pd.to_numeric(ap_part_lehs["TEST_TAKERS_CNT"], errors="coerce")

        enr_lehs = enr_eq[enr_eq["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
        enr_lehs["SY"] = pd.to_numeric(enr_lehs["SY"], errors="coerce")

        if not ap_part_lehs.dropna(subset=["SY"]).empty and not enr_lehs.dropna(subset=["SY"]).empty:
            # Pin to the latest year that exists in BOTH files so shares are
            # apples-to-apples (the enrollment file can lead AP participation by a year).
            eq_year = int(min(ap_part_lehs["SY"].max(), enr_lehs["SY"].max()))
            part_y = ap_part_lehs[ap_part_lehs["SY"] == eq_year]
            enr_y = enr_lehs[enr_lehs["SY"] == eq_year]

            all_takers = part_y[part_y["STU_GRP"] == "All Students"]["TEST_TAKERS_CNT"]
            total_takers = float(all_takers.iloc[0]) if not all_takers.empty and pd.notna(all_takers.iloc[0]) else None

            if total_takers and total_takers > 0 and not enr_y.empty:
                enr_row = enr_y.iloc[0]
                total_enr = pd.to_numeric(enr_row.get("TOTAL_CNT"), errors="coerce")

                # Group → (test-taker STU_GRP label, enrollment count). Race groups
                # derive a count from PCT × total; population groups use their _CNT.
                def _enr_cnt(pct_col=None, cnt_col=None):
                    if cnt_col is not None:
                        return pd.to_numeric(enr_row.get(cnt_col), errors="coerce")
                    p = pd.to_numeric(enr_row.get(pct_col), errors="coerce")
                    if pd.isna(p) or pd.isna(total_enr):
                        return float("nan")
                    return p * total_enr

                EQ_GROUPS = [
                    ("Hispanic or Latino",          _enr_cnt(pct_col="HL_PCT")),
                    ("Black or African American",   _enr_cnt(pct_col="BAA_PCT")),
                    ("Asian",                       _enr_cnt(pct_col="AS_PCT")),
                    ("White",                       _enr_cnt(pct_col="WH_PCT")),
                    ("English Learners",            _enr_cnt(cnt_col="EL_CNT")),
                    ("Low Income",                  _enr_cnt(cnt_col="LI_CNT")),
                    ("Students with Disabilities",  _enr_cnt(cnt_col="SWD_CNT")),
                ]

                # Pass rate (PCT_3_5) per group, All Subjects, same year — reuse the
                # already-loaded ap performance frame.
                pass_lookup = ap[
                    (ap["ORG_CODE"] == LEHS_SCHOOL_CODE)
                    & (ap["SUBJ"] == "All Subjects")
                    & (pd.to_numeric(ap["SY"], errors="coerce") == eq_year)
                ].copy()
                pass_lookup["STU_GRP"] = pass_lookup["STU_GRP"].astype(str).str.replace("\xa0", " ")
                pass_lookup["PCT_3_5"] = pd.to_numeric(pass_lookup["PCT_3_5"], errors="coerce")

                eq_rows = []
                for grp, enr_cnt in EQ_GROUPS:
                    takers = part_y[part_y["STU_GRP"] == grp]["TEST_TAKERS_CNT"]
                    takers_n = float(takers.iloc[0]) if not takers.empty and pd.notna(takers.iloc[0]) else None
                    if takers_n is None or pd.isna(enr_cnt) or float(enr_cnt) <= 0:
                        continue
                    pr = pass_lookup[pass_lookup["STU_GRP"] == grp]["PCT_3_5"]
                    pr_val = float(pr.iloc[0]) if not pr.empty and pd.notna(pr.iloc[0]) else None
                    eq_rows.append({
                        "Group": grp,
                        "Share of AP test-takers": takers_n / total_takers,
                        "Share of enrollment": float(enr_cnt) / float(total_enr) if pd.notna(total_enr) and total_enr else float("nan"),
                        "Test-takers (n)": int(takers_n),
                        "Pass rate (3+)": pr_val,
                    })

                eq_df = pd.DataFrame(eq_rows)
                if not eq_df.empty:
                    # Access view: share of test-takers vs share of enrollment.
                    eq_share = eq_df.sort_values("Share of enrollment", ascending=True)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name="Share of enrollment", x=eq_share["Group"],
                        y=eq_share["Share of enrollment"], marker_color=LEHS_GOLD,
                    ))
                    fig.add_trace(go.Bar(
                        name="Share of AP test-takers", x=eq_share["Group"],
                        y=eq_share["Share of AP test-takers"], marker_color=LEHS_NAVY,
                    ))
                    fig.update_layout(
                        **DEFAULT_LAYOUT, barmode="group", yaxis_tickformat=".0%",
                        yaxis_title="Share", xaxis_title="",
                        title=f"Who's in the AP room vs. who's enrolled — SY {sy_label(eq_year)}",
                    )
                    st.plotly_chart(fig, width="stretch")
                    st.caption(
                        "A bar where *share of AP test-takers* (navy) sits below "
                        "*share of enrollment* (gold) flags a group under-represented "
                        "among AP test-takers. Shares of test-takers are of unique "
                        "students sitting ≥1 AP exam; group enrollment counts for race "
                        "groups are derived from DESE's rounded percentage of total "
                        "enrollment, so treat them as close approximations."
                    )

                    # Success view: % scoring 3+ per group, with N shown and small-n
                    # caution. Use the Wilson-CI subgroup summary so the reader sees
                    # how wide the uncertainty is for the smaller groups.
                    succ = eq_df.dropna(subset=["Pass rate (3+)"]).copy()
                    if not succ.empty:
                        succ = succ.sort_values("Pass rate (3+)", ascending=True)
                        succ["label"] = succ.apply(
                            lambda r: f"{r['Pass rate (3+)']:.0%} (n={int(r['Test-takers (n)'])})",
                            axis=1,
                        )
                        fig = px.bar(
                            succ, x="Pass rate (3+)", y="Group", orientation="h",
                            text="label",
                        )
                        fig.update_traces(marker_color=LEHS_NAVY, textposition="outside",
                                          cliponaxis=False)
                        fig.update_layout(
                            **DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                            xaxis_title="% of exams scoring 3+ (college-credit-eligible)",
                            yaxis_title="", xaxis_range=[0, 1.12],
                            height=max(320, 32 * len(succ)),
                            title=f"AP success by group — SY {sy_label(eq_year)}",
                        )
                        st.plotly_chart(fig, width="stretch")

                        # Wilson CIs + gap test vs All Students. Add the All-Students
                        # reference row so the gap test has a baseline to compare to.
                        all_pr = pass_lookup[pass_lookup["STU_GRP"] == "All Students"]["PCT_3_5"]
                        summ = succ[["Group", "Pass rate (3+)", "Test-takers (n)"]].rename(
                            columns={"Group": "STU_GRP", "Pass rate (3+)": "pct",
                                     "Test-takers (n)": "n"}
                        )
                        if not all_pr.empty and pd.notna(all_pr.iloc[0]):
                            summ = pd.concat([
                                pd.DataFrame([{
                                    "STU_GRP": "All Students",
                                    "pct": float(all_pr.iloc[0]),
                                    "n": int(total_takers),
                                }]),
                                summ,
                            ], ignore_index=True)
                        md = subgroup_summary_md(
                            summ, group_col="STU_GRP", pct_col="pct", n_col="n",
                            reference_group="All Students",
                            title=f"AP pass rate (3+) with 95% Wilson CIs — SY {sy_label(eq_year)}",
                        )
                        if md:
                            st.markdown(md)
                        st.caption(
                            "Confidence intervals widen sharply for groups with only a "
                            "handful of test-takers (e.g. English Learners, Students "
                            "with Disabilities), so read those point estimates with "
                            "care — n is shown on every bar. Pass rate here is exam-"
                            "weighted (% of *exams* scoring 3+), while n is unique "
                            "test-takers."
                        )

st.divider()

# (AP "LEHS vs LCHS" section moved out: Lynn Tech and the alternative
# academies don't run comparable AP programs, so a Lynn-HS comparison was
# always going to be lopsided. AP equity belongs in school-to-school
# context — see Compare > Lynn Schools for the scorecard view.)

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
        # Break the line across any skipped year (notably 2020) instead of
        # interpolating a smooth segment across the COVID gap.
        m = with_year_gaps(m, "Count", group_col="Measure", years=span_years(lehs_ap))
        fig = px.line(m, x="SY", y="Count", color="Measure", markers=True,
                      color_discrete_map={"Test-takers": LEHS_NAVY, "Exams taken": LEHS_GOLD})
        fig.update_traces(connectgaps=False)
        fig.update_layout(**DEFAULT_LAYOUT,
                          title="AP participation at Lynn English over time",
                          yaxis_title="Students / exams", xaxis_title="School Year")
        st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Advanced course offerings & access (federal CRDC) — what each Lynn school
# actually OFFERS (AP/IB/gatekeeper courses) is a civil-rights measure of
# equitable access. Rolled in from the former Civil Rights Data page.
# ---------------------------------------------------------------------------

st.header("Advanced course offerings & access")
st.caption(
    "Whether each Lynn school offers AP, IB, and gatekeeper advanced courses, "
    "plus how many students are enrolled in AP, from the 2021-22 federal CRDC "
    "(U.S. Dept. of Education, Office for Civil Rights — civilrightsdata.ed.gov). "
    "What a school *offers* is a civil-rights measure of equitable access to "
    "college-level coursework. **Caveat:** the CRDC public-use file applies "
    "small random perturbations and suppresses very small cells to protect "
    "student privacy, so counts are approximate."
)

crdc_offerings = load_dataset("crdc_offerings")
if crdc_offerings.empty:
    st.info("Course-offering (CRDC) data is unavailable in the current build.")
else:
    off = crdc_offerings.copy()
    for c in ("AP_COURSE_COUNT", "AP_ENROLLED_TOTAL"):
        if c in off.columns:
            off[c] = pd.to_numeric(off[c], errors="coerce")

    lehs_o = _lehs_row(off)
    if lehs_o is not None:
        c1, c2, c3 = st.columns(3)
        ap_courses = lehs_o.get("AP_COURSE_COUNT")
        ap_enr = lehs_o.get("AP_ENROLLED_TOTAL")
        c1.metric("LEHS — distinct AP courses",
                  f"{int(ap_courses)}" if pd.notna(ap_courses) else "—")
        c2.metric("LEHS — students enrolled in AP",
                  f"{int(ap_enr):,}" if pd.notna(ap_enr) else "—")
        offered = [lbl for lbl, col in (("IB", "IB_OFFERED"), ("Calculus", "CALC_OFFERED"),
                                        ("Physics", "PHYSICS_OFFERED"),
                                        ("Geometry", "GEO_OFFERED"),
                                        ("Algebra II", "ALGEBRA_II_OFFERED"))
                   if str(lehs_o.get(col)).strip().lower() == "yes"]
        c3.metric("LEHS — advanced courses offered",
                  f"{len(offered) + (1 if str(lehs_o.get('AP_OFFERED')).lower() == 'yes' else 0)}")

    # AP enrollment across the district's high schools.
    ap_df = off[off["AP_ENROLLED_TOTAL"].notna() & (off["AP_ENROLLED_TOTAL"] > 0)].copy()
    if not ap_df.empty:
        ap_df = ap_df.sort_values("AP_ENROLLED_TOTAL", ascending=True)
        colors = [LEHS_NAVY if n == LEHS_CRDC_NAME else GATEWAY_PEER_COLOR
                  for n in ap_df["SCHOOL_NAME"]]
        fig = go.Figure(go.Bar(
            x=ap_df["AP_ENROLLED_TOTAL"], y=ap_df["SCHOOL_NAME"], orientation="h",
            marker_color=colors,
            text=[f"{int(v):,}" for v in ap_df["AP_ENROLLED_TOTAL"]],
            textposition="auto",
        ))
        fig.update_layout(**DEFAULT_LAYOUT,
                          title="Students enrolled in AP — Lynn high schools (2021-22)",
                          xaxis_title="AP-enrolled students")
        st.plotly_chart(fig, width="stretch")

    # Offering matrix (Yes/No) for the schools that offer any advanced course.
    flag_cols = ["AP_OFFERED", "IB_OFFERED", "CALC_OFFERED", "PHYSICS_OFFERED",
                 "GEO_OFFERED", "ALGEBRA_II_OFFERED"]
    have_flags = [c for c in flag_cols if c in off.columns]
    matrix = off[off[have_flags].apply(
        lambda r: (r.astype(str).str.lower() == "yes").any(), axis=1)]
    if not matrix.empty:
        nice = {"AP_OFFERED": "AP", "IB_OFFERED": "IB", "CALC_OFFERED": "Calculus",
                "PHYSICS_OFFERED": "Physics", "GEO_OFFERED": "Geometry",
                "ALGEBRA_II_OFFERED": "Algebra II"}
        show = matrix[["SCHOOL_NAME"] + have_flags].rename(columns={"SCHOOL_NAME": "School", **nice})
        st.markdown("**Advanced-course offering matrix**")
        st.dataframe(show, width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# SAT — full performance dataset (takers, RW, Math) for LEHS + Lynn + state.
# Lynn shifted to school-day SAT in SY 2024-25, which spikes the takers count
# and depresses average scores because the testing pool now includes
# non-college-bound students who previously opted out. Surface that inline.
# ---------------------------------------------------------------------------

st.header("SAT Performance")
st.caption(
    "The SAT is the college-admissions test most students take in their junior "
    "year. Each section (Reading & Writing, Math) is scored 200–800. Lynn's "
    "move to school-day testing changed *who* takes it — keep that in mind "
    "when reading the trend below."
)

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
                # Reindex per scope so any skipped year (incl. 2020) is an
                # explicit NaN and the line breaks rather than spanning the gap.
                sub_trend = with_year_gaps(
                    sub_trend, "Score", group_col="Scope",
                    years=span_years(sub_trend),
                )
                fig = px.line(
                    sub_trend.sort_values(["Scope", "SY"]),
                    x="SY", y="Score", color="Scope", markers=True,
                    color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District": LEHS_NAVY, "Massachusetts": STATE_COLOR},
                )
                fig.update_traces(connectgaps=False)
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_title=f"Mean {subj} score",
                    xaxis_title="School Year",
                    yaxis_range=[300, 650],
                )
                st.plotly_chart(fig, width="stretch")

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
                color_discrete_map=SUBJECT_PALETTE,
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
            st.plotly_chart(fig, width="stretch")

        st.caption(sat_methodology_note())

st.divider()

# ---------------------------------------------------------------------------
# Grade retention (c8ur-ajfv) — share of students held back / repeating a grade
# ---------------------------------------------------------------------------

st.header("Grade Retention")
st.caption(
    "The share of students held back to repeat a grade — rare in Massachusetts, "
    "but a meaningful signal of where students struggle to keep pace. LEHS vs "
    "Lynn district vs the statewide rate, all students."
)

retention_g = load_dataset("grade_retention")
if retention_g.empty:
    st.info("Grade-retention data is temporarily unavailable.")
else:
    rg = retention_g[retention_g["STU_GRP"] == "All Students"].copy()
    series = {
        "Lynn English": rg[rg["ORG_CODE"] == LEHS_SCHOOL_CODE],
        "Lynn district": rg[(rg["DIST_CODE"] == LYNN_DISTRICT_CODE) & (rg["ORG_TYPE"] == "District")],
        "Massachusetts": rg[rg["ORG_TYPE"] == "State"],
    }
    frames = []
    for name, d in series.items():
        if not d.empty:
            t = d[["SY", "RET_ALL_PCT"]].copy()
            t["Series"] = name
            frames.append(t)
    if frames:
        rdf = pd.concat(frames, ignore_index=True).dropna(subset=["RET_ALL_PCT"]).sort_values("SY")
        fig = px.line(rdf, x="SY", y="RET_ALL_PCT", color="Series", markers=True,
                      color_discrete_map={"Lynn English": LEHS_GOLD,
                                          "Lynn district": LEHS_NAVY,
                                          "Massachusetts": STATE_COLOR})
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".1%",
                          yaxis_title="% of students retained", xaxis_title="School Year")
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Downloads + footer
# ---------------------------------------------------------------------------

data_downloads_panel({
    "Grade 9 course passing": g9,
    "DLCS (computer science) course taking": load_dataset("dlcs_course_taking"),
    "Arts course taking": load_dataset("arts_course_taking"),
    "Advanced course completion": adv,
    "MassCore completion": masscore,
    "AP performance": ap,
    "AP participation": ap_part,
    "Enrollment & demographics": load_dataset("enrollment_demographics"),
    "SAT performance": sat_perf,
    "Grade retention": retention_g,
    "CRDC offerings": crdc_offerings,
})

page_footer()
