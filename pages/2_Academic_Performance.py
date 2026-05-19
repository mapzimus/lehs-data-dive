"""Section 2 — Academic Performance: MCAS trends, growth, subgroup gaps."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.charts import DEFAULT_LAYOUT, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset

st.set_page_config(page_title="Academic Performance | LEHS", page_icon="📈", layout="wide")

st.title("Academic Performance")
st.markdown(
    "MCAS Grade 10 results in English Language Arts, Mathematics, and Science, "
    "with breakdowns by student group and gap analysis."
)

mcas = load_dataset("mcas_achievement")
if mcas.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

# Filter to LEHS, Grade 10
lehs = mcas[(mcas["ORG_CODE"] == LEHS_SCHOOL_CODE) & (mcas["TEST_GRADE"] == "10")].copy()
if lehs.empty:
    st.error("No LEHS Grade 10 MCAS data found.")
    st.stop()

# Normalize the unicode "non-breaking space" issue in some STU_GRP labels
lehs["STU_GRP"] = lehs["STU_GRP"].str.replace("\xa0", " ", regex=False)

SUBJECT_MAP = {"ELA": "English Language Arts", "MATH": "Mathematics", "SCI": "Science"}

# ---------------------------------------------------------------------------
# Overall trend: All Students, all subjects
# ---------------------------------------------------------------------------

st.subheader("Grade 10 MCAS — All Students (% Meeting or Exceeding)")

all_students = lehs[lehs["STU_GRP"] == "All Students"]
fig = px.line(
    all_students.sort_values(["SUBJECT_CODE", "SY"]),
    x="SY", y="M_PLUS_E_PCT", color="SUBJECT_CODE",
    color_discrete_map={"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"},
    markers=True,
    labels={"SUBJECT_CODE": "Subject", "M_PLUS_E_PCT": "% Meeting + Exceeding", "SY": "Year"},
)
fig.update_layout(
    **DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="% Meeting + Exceeding",
)
st.plotly_chart(fig, width="stretch")

# Headline metrics for most recent year
latest_year = int(all_students["SY"].max())
latest = all_students[all_students["SY"] == latest_year]
c1, c2, c3 = st.columns(3)
for col, code in zip([c1, c2, c3], ["ELA", "MATH", "SCI"]):
    val = latest[latest["SUBJECT_CODE"] == code]["M_PLUS_E_PCT"]
    avg_scale = latest[latest["SUBJECT_CODE"] == code]["AVG_SCALED_SCORE"]
    if not val.empty:
        with col:
            st.metric(
                f"{SUBJECT_MAP[code]} (SY {latest_year})",
                f"{val.iloc[0]:.0%} M+E",
                f"Avg scaled: {avg_scale.iloc[0]:.0f}" if not avg_scale.empty and pd.notna(avg_scale.iloc[0]) else "",
            )

st.divider()

# ---------------------------------------------------------------------------
# Student group breakdown for a chosen subject
# ---------------------------------------------------------------------------

st.subheader("Student Group Breakdown")

subject_choice = st.radio(
    "Subject",
    options=["ELA", "MATH", "SCI"],
    format_func=lambda c: SUBJECT_MAP[c],
    horizontal=True,
)

groups_of_interest = [
    "All Students",
    "English Learners",
    "Former English Learners",
    "Hispanic or Latino",
    "Black or African American",
    "Asian",
    "White",
    "Low Income",
    "Students with Disabilities",
    "High Needs",
]

sub = lehs[
    (lehs["SUBJECT_CODE"] == subject_choice) & (lehs["STU_GRP"].isin(groups_of_interest))
].sort_values("SY").copy()

color_map = {
    "All Students":               LEHS_NAVY,
    "English Learners":           SUBGROUP_PALETTE["English Learner"],
    "Former English Learners":    SUBGROUP_PALETTE["Former English Learner"],
    "Hispanic or Latino":         SUBGROUP_PALETTE["Hispanic/Latino"],
    "Black or African American":  SUBGROUP_PALETTE["African American/Black"],
    "Asian":                      SUBGROUP_PALETTE["Asian"],
    "White":                      SUBGROUP_PALETTE["White"],
    "Low Income":                 SUBGROUP_PALETTE["Low Income"],
    "Students with Disabilities": SUBGROUP_PALETTE["Students w/ Disabilities"],
    "High Needs":                 SUBGROUP_PALETTE["High Needs"],
}

fig = px.line(
    sub, x="SY", y="M_PLUS_E_PCT", color="STU_GRP", markers=True,
    color_discrete_map=color_map,
)
fig.update_layout(
    **DEFAULT_LAYOUT,
    yaxis_tickformat=".0%",
    yaxis_title=f"{SUBJECT_MAP[subject_choice]} — % M+E",
    xaxis_title="School Year",
)
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Achievement gap: how much below 'All Students' is each subgroup?
# ---------------------------------------------------------------------------

st.subheader(f"Achievement Gap — Most Recent Year ({latest_year})")

latest_sub = sub[sub["SY"] == latest_year].copy()
if not latest_sub.empty and "All Students" in latest_sub["STU_GRP"].values:
    all_value = latest_sub.loc[latest_sub["STU_GRP"] == "All Students", "M_PLUS_E_PCT"].iloc[0]
    latest_sub["Gap"] = latest_sub["M_PLUS_E_PCT"] - all_value
    gap_data = latest_sub[latest_sub["STU_GRP"] != "All Students"].sort_values("Gap")

    colors = ["#D32F2F" if g < 0 else "#388E3C" for g in gap_data["Gap"]]
    fig = go.Figure(go.Bar(
        y=gap_data["STU_GRP"],
        x=gap_data["Gap"] * 100,
        orientation="h",
        text=[f"{g*100:+.1f} pts" for g in gap_data["Gap"]],
        textposition="outside",
        marker_color=colors,
    ))
    fig.update_layout(
        **DEFAULT_LAYOUT,
        title=f"Gap vs. All Students ({all_value:.0%}) — {SUBJECT_MAP[subject_choice]}",
        xaxis_title="Percentage point gap",
    )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Negative bars indicate subgroups performing below the school-wide average. "
        "The size of the gap reveals where school-level interventions might focus."
    )

st.divider()

# ---------------------------------------------------------------------------
# Growth percentile trends (SGP)
# ---------------------------------------------------------------------------

st.subheader("Student Growth Percentile (SGP)")
st.caption(
    "SGP measures how much a student grew compared to academic peers (others "
    "with similar prior MCAS scores). 50 = median growth statewide. Values above "
    "50 indicate above-typical growth."
)

sgp = lehs[
    (lehs["STU_GRP"] == "All Students")
    & (lehs["AVG_SGP"].notna())
].sort_values("SY")

if not sgp.empty:
    fig = px.line(
        sgp, x="SY", y="AVG_SGP", color="SUBJECT_CODE",
        color_discrete_map={"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"},
        markers=True,
    )
    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                   annotation_text="Statewide median (50)", annotation_position="right")
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average SGP", xaxis_title="School Year")
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No SGP data available for LEHS in this dataset.")
