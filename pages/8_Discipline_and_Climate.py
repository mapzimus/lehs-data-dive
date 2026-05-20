"""Section 8 — Discipline, Climate & Safety."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE
from utils.data_loader import get_dart_indicator, load_dataset
from utils.interpret import sy_label

LCHS_COLOR = LEHS_GOLD

st.set_page_config(page_title="Discipline & Climate | LEHS", page_icon="⚖️", layout="wide")
sidebar_attribution()

st.title("Discipline, Climate & Safety")
st.markdown(
    "Out-of-school suspension rates and chronic absenteeism for LEHS vs. Lynn "
    "Classical, by student group where available. Same district, same city — "
    "differences isolate school-level effects."
)

attendance = load_dataset("student_attendance")
if attendance.empty:
    st.info("Attendance data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Suspension rate (from DART) — LEHS vs LCHS
# ---------------------------------------------------------------------------

st.header("Out-of-School Suspension Rate")

susp_lehs = get_dart_indicator(LEHS_SCHOOL_CODE, "Students suspended out-of-school at least once")
susp_lchs = get_dart_indicator(LCHS_SCHOOL_CODE, "Students suspended out-of-school at least once")

if not susp_lehs.empty:
    latest = susp_lehs.iloc[-1]
    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric(f"LEHS suspended at least once (SY {sy_label(latest['SY'])})",
                  f"{latest['VALUE']:.1f}%")
        if not susp_lchs.empty:
            latest_lchs = susp_lchs.iloc[-1]
            st.metric(f"LCHS (SY {sy_label(latest_lchs['SY'])})",
                      f"{latest_lchs['VALUE']:.1f}%")
    with c2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=susp_lehs["SY"], y=susp_lehs["VALUE"],
            mode="lines+markers", name="Lynn English",
            line=dict(color=LEHS_NAVY, width=3),
        ))
        if not susp_lchs.empty:
            fig.add_trace(go.Scatter(
                x=susp_lchs["SY"], y=susp_lchs["VALUE"],
                mode="lines+markers", name="Lynn Classical",
                line=dict(color=LCHS_COLOR, width=2, dash="dash"),
            ))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="% suspended at least once")
        st.plotly_chart(fig, use_container_width=True)

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

att = attendance[attendance["ORG_CODE"].isin([LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE])].copy()
att["STU_GRP"] = att["STU_GRP"].astype(str).str.replace("\xa0", " ")
att["PCT_CHRON_ABS_10"] = pd.to_numeric(att["PCT_CHRON_ABS_10"], errors="coerce")
att["School"] = att["ORG_CODE"].map({LEHS_SCHOOL_CODE: "Lynn English", LCHS_SCHOOL_CODE: "Lynn Classical"})

# Overall trend — LEHS vs LCHS
all_stu = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "FY")].sort_values("SY")
if not all_stu.empty:
    fig = px.line(
        all_stu, x="SY", y="PCT_CHRON_ABS_10", color="School", markers=True,
        color_discrete_map={"Lynn English": LEHS_NAVY, "Lynn Classical": LCHS_COLOR},
        title="Chronic absenteeism — Lynn English vs. Lynn Classical (all students)",
    )
    fig.update_traces(selector=dict(name="Lynn Classical"),
                      line=dict(dash="dash", width=2))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                      yaxis_title="% Chronically Absent (10%+ missed)")
    st.plotly_chart(fig, use_container_width=True)

# By subgroup — LEHS only (LCHS comparison on subgroups would clutter the chart)
priority = ["All Students", "English Learners", "Hispanic or Latino",
            "Black or African American", "Asian", "White", "Low Income",
            "Students with Disabilities", "High Needs"]
lehs_att = att[att["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
sub_g = lehs_att[(lehs_att["STU_GRP"].isin(priority)) & (lehs_att["ATTEND_PERIOD"] == "FY")].copy()

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
        title="LEHS chronic absenteeism by student group",
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="% Chronically Absent")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Attendance rate trend — LEHS vs LCHS
# ---------------------------------------------------------------------------

st.header("Attendance Rate")
att_rate = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "FY")].copy()
att_rate["ATTEND_RATE"] = pd.to_numeric(att_rate["ATTEND_RATE"], errors="coerce")
if not att_rate.empty:
    fig = px.line(
        att_rate.sort_values("SY"), x="SY", y="ATTEND_RATE", color="School",
        markers=True,
        color_discrete_map={"Lynn English": LEHS_NAVY, "Lynn Classical": LCHS_COLOR},
        title="Attendance rate — Lynn English vs. Lynn Classical",
    )
    fig.update_traces(selector=dict(name="Lynn Classical"),
                      line=dict(dash="dash", width=2))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                      yaxis_title="Attendance rate")
    st.plotly_chart(fig, use_container_width=True)

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

