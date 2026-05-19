"""
Section 10 — Lynn District & Sibling Schools.

The *closest* peer comparison: LEHS vs. its sibling Lynn HS (Classical, Tech,
Frederick Douglass, Harold Durgin) — same district, same policies, same student
pool. Differences here isolate school-level effects rather than city-level
demographics.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import (
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    LYNN_SIBLING_HS,
)
from utils.data_loader import load_dataset

st.set_page_config(
    page_title="Lynn District & Siblings | LEHS", page_icon="🏛️", layout="wide"
)

st.title("Lynn District & Sibling Schools")
st.markdown(
    "**This is the most analytically powerful peer view.** Lynn's high schools "
    "share the same district, same policies, and draw from the same student pool. "
    "Differences between them isolate school-level practices rather than "
    "city-level factors."
)

SIBLING_CODES = [c for c in LYNN_SIBLING_HS.values() if c]

# Color map: LEHS in gold, others muted
SIBLING_COLORS = {
    "01630510": LEHS_GOLD,                  # LEHS
    "01630505": LEHS_NAVY,                  # Classical
    "01630605": SUBGROUP_PALETTE["Asian"],  # Lynn Tech
    "01630575": SUBGROUP_PALETTE["Hispanic/Latino"],  # Frederick Douglass
    "01630525": SUBGROUP_PALETTE["African American/Black"],  # Harold Durgin
}

NAME_OVERRIDES = {
    "01630510": "Lynn English High",
    "01630505": "Lynn Classical",
    "01630605": "Lynn Tech",
    "01630575": "Frederick Douglass",
    "01630525": "Harold Durgin",
}

st.divider()

# ===========================================================================
# DISTRICT-WIDE LYNN PUBLIC SCHOOLS
# ===========================================================================

st.header("Lynn Public Schools — District Snapshot")

enrollment = load_dataset("enrollment_demographics")
if enrollment.empty:
    st.warning("Data pipeline not yet run.")
    st.stop()

district = enrollment[
    (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE)
    & (enrollment["ORG_TYPE"] == "District")
].sort_values("SY")

if not district.empty:
    current = district.iloc[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Lynn PS Enrollment", f"{int(current['TOTAL_CNT']):,}")
    with c2:
        st.metric("% English Learners", f"{current['EL_PCT']:.0%}")
    with c3:
        st.metric("% Low Income", f"{current['LI_PCT']:.0%}")
    with c4:
        st.metric("% Hispanic/Latino", f"{current['HL_PCT']:.0%}")
    with c5:
        st.metric("Schools in District", "22")

    st.markdown("**District enrollment trend**")
    fig = px.line(district, x="SY", y="TOTAL_CNT", markers=True)
    fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year", height=300)
    st.plotly_chart(fig, width="stretch")

st.divider()

# ===========================================================================
# LYNN HIGH SCHOOLS — SIDE BY SIDE
# ===========================================================================

st.header("Lynn High Schools — Side by Side")
st.markdown(
    "Comparison across Lynn's five high schools that report MCAS data: "
    "**Lynn English** (the focus), **Lynn Classical**, **Lynn Tech** "
    "(vocational), **Frederick Douglass Collegiate Academy** (alternative), "
    "and **Harold Durgin Success Academy** (alternative)."
)

siblings = enrollment[enrollment["ORG_CODE"].isin(SIBLING_CODES)].copy()
siblings["School"] = siblings["ORG_CODE"].map(NAME_OVERRIDES)

# ---------------------------------------------------------------------------
# Most-recent scorecard
# ---------------------------------------------------------------------------

st.subheader("Latest Year Scorecard")

latest_year = int(siblings["SY"].max())
latest = siblings[siblings["SY"] == latest_year].set_index("School")
scorecard_cols = {
    "TOTAL_CNT": "Total Enrollment",
    "EL_PCT": "% ELL",
    "LI_PCT": "% Low Income",
    "SWD_PCT": "% SPED",
    "HN_PCT": "% High Needs",
    "HL_PCT": "% Hispanic/Latino",
    "FE_PCT": "% Female",
}
scorecard = latest[list(scorecard_cols.keys())].rename(columns=scorecard_cols)
for col in scorecard.columns:
    if col == "Total Enrollment":
        scorecard[col] = scorecard[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
    else:
        scorecard[col] = scorecard[col].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")

def highlight_lehs(row):
    if row.name == "Lynn English High":
        return ["background-color: #FFF4D6"] * len(row)
    return [""] * len(row)

st.dataframe(scorecard.style.apply(highlight_lehs, axis=1), width="stretch")
st.caption(f"School year {latest_year}. LEHS highlighted in gold.")

# ---------------------------------------------------------------------------
# Enrollment trends - small multiples
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

st.subheader(f"Demographic Composition ({latest_year})")

demo_cols = ["EL_PCT", "LI_PCT", "SWD_PCT", "HL_PCT", "BAA_PCT"]
demo_labels = {
    "EL_PCT": "% ELL",
    "LI_PCT": "% Low Income",
    "SWD_PCT": "% SPED",
    "HL_PCT": "% Hispanic/Latino",
    "BAA_PCT": "% Black/African American",
}

demo_long = latest.reset_index().melt(
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

st.divider()

# ===========================================================================
# MCAS GRADE 10 COMPARISON
# ===========================================================================

st.header("MCAS Grade 10 — Lynn HS Comparison")

mcas = load_dataset("mcas_achievement")
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
        fig = px.line(
            sub, x="SY", y="M_PLUS_E_PCT", color="School",
            color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
            markers=True,
        )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="% Meeting + Exceeding",
            xaxis_title="School Year",
        )
        st.plotly_chart(fig, width="stretch")

st.divider()

# ===========================================================================
# GRADUATION RATES
# ===========================================================================

st.header("4-Year Graduation Rates — Lynn HS Comparison")

grad = load_dataset("graduation_rates")
grad_lynn = grad[
    (grad["ORG_CODE"].isin(SIBLING_CODES))
    & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
    & (grad["STU_GRP"] == "All Students")
].copy()
grad_lynn["School"] = grad_lynn["ORG_CODE"].map(NAME_OVERRIDES)

if grad_lynn.empty:
    st.info("No graduation data yet.")
else:
    fig = px.line(
        grad_lynn.sort_values("SY"),
        x="SY", y="GRAD_PCT", color="School",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
        markers=True,
    )
    fig.update_layout(
        **DEFAULT_LAYOUT,
        yaxis_tickformat=".0%",
        yaxis_title="4-Year Graduation Rate",
        xaxis_title="Cohort Year",
    )
    st.plotly_chart(fig, width="stretch")

    # Side-by-side latest year
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
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", xaxis_title="")
    st.plotly_chart(fig, width="stretch")

st.divider()

# ===========================================================================
# KEY ANALYTICAL QUESTION
# ===========================================================================

st.subheader("Key Analytical Question")
st.markdown(
    """
**When student populations are similar (or after controlling for them), what's
different about the schools' outcomes?**

The Lynn HS sibling comparison isolates school-level practices from city-level
demographic factors. Use the ELL Pipeline page to drill into how each Lynn HS
serves English Learners specifically — Lynn Tech, the alternative academies, and
the two comprehensive HS may all show different patterns despite operating
under the same district leadership.
"""
)
