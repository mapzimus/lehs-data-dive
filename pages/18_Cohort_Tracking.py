"""Section 20 — Cohort Tracking: 9th grade through college persistence."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import (
    LCHS_SCHOOL_CODE,
    LEHS_SCHOOL_CODE,
    LYNN_SIBLING_HS,
)
from utils.data_loader import load_dataset

st.set_page_config(
    page_title="Cohort Tracking | LEHS", page_icon="🎓", layout="wide"
)
sidebar_attribution()

st.title("Cohort Tracking — From 9th Grade to College Persistence")
st.markdown(
    "**The headline question every parent, teacher, and school committee member "
    "asks: of every 100 9th-graders who walk into LEHS, how many graduate, how "
    "many enroll in college, and how many are still there a year later?**"
)
st.markdown(
    "DESE publishes this longitudinal *student progression* dataset for every "
    "MA high school, but it doesn't appear on most school report cards. This "
    "page surfaces it — the full pipeline, broken out by subgroup, with "
    "multi-year trends so you can see where pandemic disruption hit hardest."
)

prog = load_dataset("student_progression_hs_to_postsec")
if prog.empty:
    st.info(
        "Cohort progression data not yet loaded. Run "
        "`python scripts/refresh_all.py` to populate."
    )
    st.stop()

YEAR2_INDICATOR = "Student progression from high school through second year of postsecondary education"
DEGREE_INDICATOR = "Student progression from high school through postsecondary degree completion"

# Sanitize: ensure DIST_CODE and ORG_CODE are 8-char zero-padded strings
prog["DIST_CODE"] = prog["DIST_CODE"].astype(str).str.zfill(8)
prog["ORG_CODE"] = prog["ORG_CODE"].astype(str).str.zfill(8)

lehs = prog[prog["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
if lehs.empty:
    st.error(
        f"No cohort progression rows found for LEHS (ORG_CODE {LEHS_SCHOOL_CODE})."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Headline funnel — most recent year-2 cohort, All Students
# ---------------------------------------------------------------------------

lehs_y2_all = lehs[
    (lehs["INDICATOR"] == YEAR2_INDICATOR) & (lehs["STU_GRP"] == "All Students")
].sort_values("COHORTYR")

if lehs_y2_all.empty:
    st.warning("No year-2 progression data for LEHS All Students.")
    st.stop()

latest = lehs_y2_all.iloc[-1]
latest_cohort = int(latest["COHORTYR"])

st.divider()
st.subheader(f"LEHS Class — {latest_cohort - 4}–{latest_cohort} Cohort")
st.caption(
    f"All Students, entered LEHS as 9th-graders four years before the SY "
    f"{latest_cohort - 1}-{str(latest_cohort)[-2:]} cohort graduation. "
    f"Tracked through their second year of college (~{latest_cohort + 1}-"
    f"{str(latest_cohort + 2)[-2:]})."
)

cohort_n = int(latest["COHORT_CNT"])
grad_n = int(latest["GRAD_CNT"]) if pd.notna(latest["GRAD_CNT"]) else 0
enr_n = int(latest["IMMEDIATEENR_CNT"]) if pd.notna(latest["IMMEDIATEENR_CNT"]) else 0
pers_n = int(latest["PERSIST_CNT"]) if pd.notna(latest["PERSIST_CNT"]) else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Entered 9th grade", f"{cohort_n:,}", "the baseline cohort")
with c2:
    st.metric(
        "Graduated high school",
        f"{grad_n:,}",
        f"{grad_n / cohort_n:.0%} of cohort",
        delta_color="off",
    )
with c3:
    st.metric(
        "Enrolled in college (immediate)",
        f"{enr_n:,}",
        f"{enr_n / cohort_n:.0%} of cohort",
        delta_color="off",
    )
with c4:
    st.metric(
        "Still enrolled in year 2",
        f"{pers_n:,}",
        f"{pers_n / cohort_n:.0%} of cohort",
        delta_color="off",
    )

# Funnel chart
stages = ["Entered 9th grade", "Graduated", "Enrolled in college", "Persisted to year 2"]
counts = [cohort_n, grad_n, enr_n, pers_n]
pcts = [c / cohort_n for c in counts]
labels = [f"{c:,}<br>({p:.0%})" for c, p in zip(counts, pcts)]

fig = go.Figure(
    go.Funnel(
        y=stages,
        x=counts,
        text=labels,
        textposition="inside",
        textfont=dict(color="white", size=14),
        marker=dict(color=[LEHS_NAVY, "#1E3A6F", "#2F559A", LEHS_GOLD]),
        connector=dict(line=dict(color="#B0BEC5", width=1)),
    )
)
fig.update_layout(**DEFAULT_LAYOUT, height=380, margin=dict(l=20, r=20, t=30, b=30))
st.plotly_chart(fig, use_container_width=True)

st.markdown(
    f"**The headline number:** of every 100 LEHS 9th-graders, "
    f"~{round(grad_n / cohort_n * 100)} graduate, "
    f"~{round(enr_n / cohort_n * 100)} enroll in college, "
    f"and only **~{round(pers_n / cohort_n * 100)} are still in college a year later**."
)

st.divider()

# ---------------------------------------------------------------------------
# Subgroup breakdown — same cohort, broken out
# ---------------------------------------------------------------------------

st.subheader(f"Where the Pipeline Leaks — by Subgroup, {latest_cohort - 4}–{latest_cohort} Cohort")
st.caption(
    "The headline numbers above hide enormous within-school disparities. "
    "Below: the same cohort, broken out by subgroup. Bar length = share of "
    "that subgroup's 9th-grade entrants who reach each stage. Empty bars are "
    "DESE-suppressed (cell <10 students)."
)

# Pull all subgroups for the latest cohort
sub_groups = lehs[
    (lehs["INDICATOR"] == YEAR2_INDICATOR)
    & (lehs["COHORTYR"] == latest_cohort)
    & (lehs["STU_GRP"] != "All Students")
].copy()

# Compute % for each stage relative to cohort_cnt of THAT subgroup
sub_groups = sub_groups.assign(
    grad_pct=lambda d: d["GRAD_CNT"] / d["COHORT_CNT"],
    enr_pct=lambda d: d["IMMEDIATEENR_CNT"] / d["COHORT_CNT"],
    pers_pct=lambda d: d["PERSIST_CNT"] / d["COHORT_CNT"],
)

# Keep only subgroups with at least 10 students (DESE suppression threshold)
sub_groups = sub_groups[sub_groups["COHORT_CNT"] >= 10].copy()

# Order subgroups by persistence rate (descending) for readability — the
# "highest-performing" subgroups go on top so the gap to ELL/HL is visually obvious.
sub_groups = sub_groups.sort_values("pers_pct", ascending=True, na_position="first")

# Wide-format for stacked bars
melted = sub_groups.melt(
    id_vars=["STU_GRP", "COHORT_CNT"],
    value_vars=["grad_pct", "enr_pct", "pers_pct"],
    var_name="stage",
    value_name="pct",
)
stage_labels = {
    "grad_pct": "Graduated",
    "enr_pct": "Enrolled in college",
    "pers_pct": "Persisted to year 2",
}
stage_colors = {
    "Graduated": "#90A4AE",
    "Enrolled in college": "#2F559A",
    "Persisted to year 2": LEHS_GOLD,
}
melted["stage"] = melted["stage"].map(stage_labels)

fig = px.bar(
    melted,
    x="pct",
    y="STU_GRP",
    color="stage",
    barmode="group",
    orientation="h",
    color_discrete_map=stage_colors,
    category_orders={"stage": ["Graduated", "Enrolled in college", "Persisted to year 2"]},
    text=melted["pct"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else ""),
)
fig.update_traces(textposition="outside", textfont=dict(size=10))
fig.update_layout(
    **DEFAULT_LAYOUT,
    height=max(360, 28 * len(sub_groups)),
    xaxis_tickformat=".0%",
    xaxis_title="Share of 9th-grade entrants reaching each stage",
    yaxis_title="",
    legend_title="",
)
fig.update_xaxes(range=[0, 1.1])
st.plotly_chart(fig, use_container_width=True)

# Pinpoint the largest gap
if not sub_groups["pers_pct"].dropna().empty:
    top_row = sub_groups.iloc[-1]
    bot_row = sub_groups.iloc[0]
    top_grp = top_row["STU_GRP"]
    bot_grp = bot_row["STU_GRP"]
    top_pct = top_row["pers_pct"]
    bot_pct = bot_row["pers_pct"]
    if pd.notna(top_pct) and pd.notna(bot_pct):
        st.markdown(
            f"**The widest gap:** {top_grp} students persist to college year 2 at "
            f"**{top_pct:.0%}**, while {bot_grp} students persist at "
            f"**{bot_pct:.0%}** — a **{(top_pct - bot_pct) * 100:.0f}-percentage-point** spread."
        )

st.divider()

# ---------------------------------------------------------------------------
# Multi-cohort trend
# ---------------------------------------------------------------------------

st.subheader("Trend Over Multiple Cohorts")
st.caption(
    "Each line shows how a single stage of the pipeline has moved over time. "
    "Cohorts graduating 2020–2024 were disrupted as 8th–10th graders; "
    "expect noisier patterns for those years."
)

trend_all = lehs[
    (lehs["INDICATOR"] == YEAR2_INDICATOR) & (lehs["STU_GRP"] == "All Students")
].sort_values("COHORTYR").copy()
trend_all["grad_pct"] = trend_all["GRAD_CNT"] / trend_all["COHORT_CNT"]
trend_all["enr_pct"] = trend_all["IMMEDIATEENR_CNT"] / trend_all["COHORT_CNT"]
trend_all["pers_pct"] = trend_all["PERSIST_CNT"] / trend_all["COHORT_CNT"]

trend_long = trend_all.melt(
    id_vars=["COHORTYR"],
    value_vars=["grad_pct", "enr_pct", "pers_pct"],
    var_name="stage",
    value_name="pct",
).dropna(subset=["pct"])
trend_long["stage"] = trend_long["stage"].map(stage_labels)

fig = px.line(
    trend_long,
    x="COHORTYR",
    y="pct",
    color="stage",
    markers=True,
    color_discrete_map=stage_colors,
    category_orders={"stage": ["Graduated", "Enrolled in college", "Persisted to year 2"]},
)
fig.update_layout(
    **DEFAULT_LAYOUT,
    yaxis_tickformat=".0%",
    yaxis_title="Share of 9th-grade cohort",
    xaxis_title="Graduation cohort year",
    legend_title="",
)
fig.update_yaxes(range=[0, max(trend_long["pct"].max() * 1.1, 1.0)])
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# LEHS vs Lynn sibling high schools — latest cohort
# ---------------------------------------------------------------------------

st.subheader(f"LEHS vs. Lynn Sibling High Schools — {latest_cohort - 4}–{latest_cohort} Cohort")
st.caption(
    "Same-district, same-policies comparison. Differences here isolate "
    "school-level effects rather than city-level demographics. Hover for counts."
)

sibling_codes = list(LYNN_SIBLING_HS.values())
siblings = prog[
    prog["ORG_CODE"].isin(sibling_codes)
    & (prog["INDICATOR"] == YEAR2_INDICATOR)
    & (prog["STU_GRP"] == "All Students")
    & (prog["COHORTYR"] == latest_cohort)
].copy()

if not siblings.empty:
    siblings = siblings.assign(
        grad_pct=lambda d: d["GRAD_CNT"] / d["COHORT_CNT"],
        enr_pct=lambda d: d["IMMEDIATEENR_CNT"] / d["COHORT_CNT"],
        pers_pct=lambda d: d["PERSIST_CNT"] / d["COHORT_CNT"],
    )
    # Only schools with enough students to be meaningful
    siblings = siblings[siblings["COHORT_CNT"] >= 20].sort_values("pers_pct")

    melted_s = siblings.melt(
        id_vars=["ORG_NAME", "COHORT_CNT"],
        value_vars=["grad_pct", "enr_pct", "pers_pct"],
        var_name="stage",
        value_name="pct",
    )
    melted_s["stage"] = melted_s["stage"].map(stage_labels)

    fig = px.bar(
        melted_s,
        x="pct",
        y="ORG_NAME",
        color="stage",
        barmode="group",
        orientation="h",
        color_discrete_map=stage_colors,
        category_orders={"stage": ["Graduated", "Enrolled in college", "Persisted to year 2"]},
        text=melted_s["pct"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else ""),
        hover_data={"COHORT_CNT": True},
    )
    fig.update_traces(textposition="outside", textfont=dict(size=10))
    fig.update_layout(
        **DEFAULT_LAYOUT,
        height=max(280, 60 * len(siblings)),
        xaxis_tickformat=".0%",
        xaxis_title="Share of 9th-grade entrants reaching each stage",
        yaxis_title="",
        legend_title="",
    )
    fig.update_xaxes(range=[0, 1.1])
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No sibling-school cohort data for this year.")

st.divider()

# ---------------------------------------------------------------------------
# Six-year degree completion (longest available cohort)
# ---------------------------------------------------------------------------

st.subheader("Degree Completion — 6-Year View")
st.caption(
    "DESE publishes a separate indicator that follows cohorts through "
    "postsecondary degree completion (six years after high-school graduation). "
    "Below: the most recent LEHS cohort with enough elapsed time for completion data."
)

lehs_deg = lehs[
    (lehs["INDICATOR"] == DEGREE_INDICATOR) & (lehs["STU_GRP"] == "All Students")
].sort_values("COHORTYR")

if not lehs_deg.empty:
    latest_deg = lehs_deg.iloc[-1]
    deg_year = int(latest_deg["COHORTYR"])
    deg_pct = latest_deg["OBTAINDEGREE_PCT"]
    if pd.notna(deg_pct):
        st.metric(
            f"Obtained a postsecondary degree ({deg_year - 4}–{deg_year} cohort)",
            f"{deg_pct:.0%}",
            help="Share of the 9th-grade cohort that completed a 2-yr or 4-yr degree within ~6 years of HS graduation.",
        )

    deg_trend = lehs_deg.dropna(subset=["OBTAINDEGREE_PCT"]).copy()
    if len(deg_trend) >= 2:
        fig = px.line(
            deg_trend,
            x="COHORTYR",
            y="OBTAINDEGREE_PCT",
            markers=True,
        )
        fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="Share of cohort obtaining a degree",
            xaxis_title="Cohort year",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No 6-year degree-completion data available for LEHS yet.")

st.divider()

# ---------------------------------------------------------------------------
# Methodology + downloads
# ---------------------------------------------------------------------------

with st.expander("ℹ️ How to read this page · methodology"):
    st.markdown(
        """
- **Cohort** means *the group of students who first entered 9th grade together*,
  not the graduating class. A 2023 cohort started 9th grade around 2019.
- **Immediate enrollment** is in college the fall *immediately after* HS graduation.
- **Persisted to year 2** = still enrolled in college one year after immediate enrollment.
  This is the strongest single predictor of degree completion.
- **Stage percentages** are always relative to the original 9th-grade cohort,
  not to the previous stage. So `graduated` × `enrolled-of-grads` ≠ `enrolled-of-cohort`.
- **DESE suppression**: cells under 10 students are blanked. Small subgroups
  (e.g., Nonbinary, American Indian/Alaska Native) may have missing rows.
- **Source**: MA DESE Education-to-Career Hub,
  *Student Progression from High School through Postsecondary Education*.
        """
    )

from utils.charts import data_downloads_panel
data_downloads_panel({
    "LEHS cohort progression (year 2 & degree)": lehs,
    "Lynn sibling schools — latest cohort": siblings if 'siblings' in dir() and not siblings.empty else pd.DataFrame(),
})

page_footer()
