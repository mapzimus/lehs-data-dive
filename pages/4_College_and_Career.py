"""Section 4 — College & Career Readiness."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE
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
        fig = px.bar(
            score_long, x="SY", y="Count", color="Score", barmode="stack",
            color_discrete_map={
                "1": "#D32F2F", "2": "#F57C00", "3": "#FBC02D",
                "4": "#388E3C", "5": "#1976D2",
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
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# LEHS vs LCHS — AP equity (% of juniors/seniors taking AP tests)
# ---------------------------------------------------------------------------

st.header("AP Participation — LEHS vs. Lynn Classical")
st.caption(
    "AP access is a leading indicator of college readiness. Comparing "
    "Lynn's two comprehensive HS side-by-side isolates school-level "
    "decisions about course offerings + recruitment from city-level "
    "demographics."
)

ap_compare = ap[
    (ap["ORG_CODE"].isin([LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE]))
    & (ap["STU_GRP"] == "All Students")
    & (ap["SUBJ_CAT"].astype(str).str.lower() == "all subjects")
].copy()
ap_compare["School"] = ap_compare["ORG_CODE"].map({
    LEHS_SCHOOL_CODE: "LEHS",
    LCHS_SCHOOL_CODE: "LCHS",
})
ap_compare["PCT_3_5"] = pd.to_numeric(ap_compare["PCT_3_5"], errors="coerce")
ap_compare["TESTS_TAKEN"] = pd.to_numeric(ap_compare["TESTS_TAKEN"], errors="coerce")

if not ap_compare.empty:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**AP tests taken (volume)**")
        fig = px.line(
            ap_compare.sort_values("SY"), x="SY", y="TESTS_TAKEN", color="School",
            markers=True,
            color_discrete_map={"LEHS": LEHS_GOLD, "LCHS": "#1A8FE3"},
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Tests taken")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**% AP tests scoring 3 or higher**")
        fig = px.line(
            ap_compare.sort_values("SY"), x="SY", y="PCT_3_5", color="School",
            markers=True,
            color_discrete_map={"LEHS": LEHS_GOLD, "LCHS": "#1A8FE3"},
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="% scoring 3+")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("AP comparison data not available.")

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
            st.dataframe(display_p, use_container_width=True, hide_index=True)
    else:
        st.info("No LEHS pathways enrollment data (program may not be designated here).")

# Early College specifically
if not ec_part.empty:
    ec_lehs = ec_part[ec_part["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    if not ec_lehs.empty:
        st.subheader("Early College participation")
        drop_cols = ["CEEB_CODE", "DIST_CODE", "ORG_CODE", "ORG_TYPE"]
        ec_display = ec_lehs.drop(columns=[c for c in drop_cols if c in ec_lehs.columns])
        ec_display = ec_display.dropna(axis=1, how="all")
        ec_display = ec_display.sort_values("SY", ascending=False) if "SY" in ec_display else ec_display
        st.dataframe(ec_display, use_container_width=True, hide_index=True)

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
        'MassCore completion': masscore,
        'Pathways enrollment': pathways,
        'Early College participation': ec_part,
        'IPEDS destinations': ipeds,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

