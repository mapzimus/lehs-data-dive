"""Section 4 — College & Career Readiness."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import get_dart_indicator, load_dataset

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
for col, ind, label in zip(
    cols,
    [
        "Jr/Sr enrolled in one or more AP / IB courses",
        "Jr/Sr AP test takers scoring 3 or above",
        "High school graduates who completed MassCore",
        "Grade 12 students who completed FAFSA",
    ],
    ["% Juniors/Seniors in AP/IB", "% AP test-takers scoring 3+",
     "% Completed MassCore", "% Completed FAFSA"],
):
    sub = get_dart_indicator(LEHS_SCHOOL_CODE, ind)
    if not sub.empty:
        v = sub.iloc[-1]["VALUE"]
        with col:
            st.metric(label, f"{v:.0%}" if v <= 1 else f"{v:.1f}")

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
    latest = ap_lehs[(ap_lehs["SY"] == latest_year) & (ap_lehs["SUBJ_CAT"] != "All AP Tests")].copy()

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
        fig = px.bar(
            score_long, x="SY", y="Count", color="Score", barmode="stack",
            color_discrete_map={
                "1": "#D32F2F", "2": "#F57C00", "3": "#FBC02D",
                "4": "#388E3C", "5": "#1976D2",
            },
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
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# SAT averages
# ---------------------------------------------------------------------------

st.header("SAT Average Scores")
sat_math = get_dart_indicator(LEHS_SCHOOL_CODE, "SAT average score - Mathematics")
sat_read = get_dart_indicator(LEHS_SCHOOL_CODE, "SAT average score - Reading")

if not sat_math.empty or not sat_read.empty:
    sat = pd.concat([
        sat_math.assign(Subject="Math"),
        sat_read.assign(Subject="Reading"),
    ])
    fig = px.line(
        sat.sort_values("SY"), x="SY", y="VALUE", color="Subject", markers=True,
        color_discrete_map={"Math": "#D32F2F", "Reading": "#1976D2"},
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average score")
    st.plotly_chart(fig, width="stretch")

st.divider()

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
        pathway_cols = [c for c in p.columns if "TOTAL" in c.upper() and "PCT" not in c.upper()]
        if pathway_cols:
            display_p = p[["SY"] + pathway_cols[:8]].sort_values("SY")
            # Drop columns that are entirely null for LEHS
            display_p = display_p.dropna(axis=1, how="all")
            st.dataframe(display_p, width="stretch", hide_index=True)
    else:
        st.info("No LEHS pathways enrollment data (program may not be designated here).")

# Early College specifically
if not ec_part.empty:
    ec_lehs = ec_part[ec_part["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    if not ec_lehs.empty:
        st.subheader("Early College participation")
        # Drop noisy/empty columns: CEEB_CODE is null at the school level here,
        # and the raw DESE columns aren't user friendly
        drop_cols = ["CEEB_CODE", "DIST_CODE", "ORG_CODE", "ORG_TYPE"]
        ec_display = ec_lehs.drop(columns=[c for c in drop_cols if c in ec_lehs.columns])
        ec_display = ec_display.dropna(axis=1, how="all")
        ec_display = ec_display.sort_values("SY", ascending=False) if "SY" in ec_display else ec_display
        st.dataframe(ec_display, width="stretch", hide_index=True)
