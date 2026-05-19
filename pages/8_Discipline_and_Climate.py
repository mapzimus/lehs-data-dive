"""Section 8 — Discipline, Climate & Safety."""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import get_dart_indicator, load_dataset
from utils.interpret import sy_label

st.set_page_config(page_title="Discipline & Climate | LEHS", page_icon="⚖️", layout="wide")
sidebar_attribution()

st.title("Discipline, Climate & Safety")
st.markdown(
    "Out-of-school suspension rates and chronic absenteeism for LEHS, by "
    "student group where available. More granular discipline data (race × "
    "disability × gender) is collected federally by the Civil Rights Data "
    "Collection and at the state level — see Methodology for sources."
)

attendance = load_dataset("student_attendance")
if attendance.empty:
    st.info("Attendance data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Suspension rate (from DART)
# ---------------------------------------------------------------------------

st.header("Out-of-School Suspension Rate")

susp = get_dart_indicator(LEHS_SCHOOL_CODE, "Students suspended out-of-school at least once")
if not susp.empty:
    latest = susp.iloc[-1]
    c1, c2 = st.columns([1, 3])
    with c1:
        # DART value is in 0-100 percent form, not 0-1 fraction
        st.metric(f"Suspended at least once (SY {sy_label(latest['SY'])})",
                  f"{latest['VALUE']:.1f}%")
    fig = px.line(susp, x="SY", y="VALUE", markers=True)
    fig.update_traces(line=dict(color="#D32F2F", width=3))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".1%",
                       yaxis_title="% suspended at least once")
    with c2:
        st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Chronic absenteeism — overall and by group
# ---------------------------------------------------------------------------

st.header("Chronic Absenteeism")
st.caption(
    "DESE defines 'chronically absent' as missing 10% or more of enrolled days "
    "(~18 days in a typical 180-day year). Strong predictor of dropout and "
    "of low college-going rates."
)

att = attendance[attendance["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
att["STU_GRP"] = att["STU_GRP"].astype(str).str.replace("\xa0", " ")
att["PCT_CHRON_ABS_10"] = pd.to_numeric(att["PCT_CHRON_ABS_10"], errors="coerce")

# Overall trend
all_stu = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "FY")].sort_values("SY")
if not all_stu.empty:
    fig = px.line(all_stu, x="SY", y="PCT_CHRON_ABS_10", markers=True)
    fig.update_traces(line=dict(color="#F57C00", width=3))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="% Chronically Absent (10%+ missed)",
                       title="LEHS chronic absenteeism — all students")
    st.plotly_chart(fig, width="stretch")

# By subgroup
priority = ["All Students", "English Learners", "Hispanic or Latino",
            "Black or African American", "Asian", "White", "Low Income",
            "Students with Disabilities", "High Needs"]
sub_g = att[(att["STU_GRP"].isin(priority)) & (att["ATTEND_PERIOD"] == "FY")].copy()

if not sub_g.empty:
    fig = px.line(
        sub_g.sort_values("SY"), x="SY", y="PCT_CHRON_ABS_10", color="STU_GRP",
        markers=True,
        color_discrete_map={
            "All Students":               LEHS_NAVY,
            "English Learners":           SUBGROUP_PALETTE["English Learner"],
            "Hispanic or Latino":         SUBGROUP_PALETTE["Hispanic/Latino"],
            "Black or African American":  SUBGROUP_PALETTE["African American/Black"],
            "Asian":                      SUBGROUP_PALETTE["Asian"],
            "White":                      SUBGROUP_PALETTE["White"],
            "Low Income":                 SUBGROUP_PALETTE["Low Income"],
            "Students with Disabilities": SUBGROUP_PALETTE["Students w/ Disabilities"],
            "High Needs":                 SUBGROUP_PALETTE["High Needs"],
        },
        title="Chronic absenteeism by student group",
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="% Chronically Absent")
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Attendance rate trend
# ---------------------------------------------------------------------------

st.header("Attendance Rate")
att_rate = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "FY")].copy()
att_rate["ATTEND_RATE"] = pd.to_numeric(att_rate["ATTEND_RATE"], errors="coerce")
if not att_rate.empty:
    fig = px.line(att_rate.sort_values("SY"), x="SY", y="ATTEND_RATE", markers=True)
    fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="Attendance rate")
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# What's missing
# ---------------------------------------------------------------------------

st.subheader("Going deeper — what's possible next")
st.markdown(
    """
The bigger discipline picture lives in two places this dashboard doesn't yet
pull from. When those layers are added, expect:

- **Suspensions by race × ELL × SPED** — disproportionality analysis (from
  DESE Profiles statereport).
- **In-school suspensions** vs. out-of-school, expulsions counts.
- **Federal CRDC** (Civil Rights Data Collection): school-based arrests,
  restraint and seclusion, bullying incidents by basis.
- **VOCAL Survey** student-reported climate, belonging, safety, engagement
  for years LEHS participates.
"""
)
