"""Section 6 — Teachers & Workforce."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset

st.set_page_config(page_title="Teachers & Workforce | LEHS", page_icon="👩‍🏫", layout="wide")
sidebar_attribution()

st.title("Teachers & Workforce")
st.markdown(
    "Teacher diversity, FTE counts, and student-support staffing — drawn from "
    "DESE's Staffing by Race/Ethnicity and Gender dataset."
)

staffing = load_dataset("staffing_race_gender")
enrollment = load_dataset("enrollment_demographics")
if staffing.empty:
    st.warning("Data pipeline not yet run.")
    st.stop()

lehs_staff = staffing[staffing["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
if lehs_staff.empty:
    st.error("No LEHS staffing data found.")
    st.stop()

# ---------------------------------------------------------------------------
# Headline FTE counts
# ---------------------------------------------------------------------------

st.header("Staff Headcount (FTE)")

latest_year = int(lehs_staff["SY"].max())
latest = lehs_staff[lehs_staff["SY"] == latest_year]

# JOBCLASS is the specific role; JOBCLASS_CAT is the category
all_staff = latest[latest["JOBCLASS_CAT"] == "All Staff"]
teachers = latest[latest["JOBCLASS"].astype(str).str.lower() == "teacher"]

c1, c2, c3, c4 = st.columns(4)
with c1:
    total_fte = pd.to_numeric(all_staff["FTE_TOTAL"], errors="coerce").sum() if not all_staff.empty else 0
    st.metric(f"Total Staff FTE ({latest_year})", f"{total_fte:,.0f}")
with c2:
    teacher_fte = pd.to_numeric(teachers["FTE_TOTAL"], errors="coerce").sum() if not teachers.empty else 0
    st.metric("Teacher FTE", f"{teacher_fte:,.0f}")
with c3:
    # Student-teacher ratio
    enr = enrollment[(enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE) & (enrollment["SY"] == latest_year)]
    if not enr.empty and teacher_fte > 0:
        ratio = enr.iloc[0]["TOTAL_CNT"] / teacher_fte
        st.metric("Student:Teacher Ratio", f"{ratio:.1f}:1")
with c4:
    # Diversity quick stat
    if not teachers.empty:
        nonwhite = sum(pd.to_numeric(teachers[c], errors="coerce").fillna(0).sum()
                       for c in ["AIAN_CNT","AS_CNT","BAA_CNT","HL_CNT","MNHL_CNT","NHPI_CNT"])
        tot = pd.to_numeric(teachers["FTE_TOTAL"], errors="coerce").sum()
        if tot > 0:
            st.metric("% Teachers of Color", f"{nonwhite/tot:.0%}")

st.divider()

# ---------------------------------------------------------------------------
# Teacher diversity vs. student body — the representation gap
# ---------------------------------------------------------------------------

st.header("Teacher Diversity vs. Student Body")
st.caption(
    "Research consistently shows representation matters: students of color "
    "perform better when they have teachers who share their racial/ethnic "
    "background. This chart compares the share of LEHS teachers in each "
    "racial/ethnic group to the share of LEHS students in that group."
)

if not teachers.empty and not enr.empty:
    teach_row = teachers.iloc[0]
    stu = enr.iloc[0]
    groups = [
        ("Hispanic/Latino",          "HL_PCT",   "HL_PCT"),
        ("African American/Black",   "BAA_PCT",  "BAA_PCT"),
        ("Asian",                    "AS_PCT",   "AS_PCT"),
        ("White",                    "WH_PCT",   "WH_PCT"),
        ("Multi-Race",               "MNHL_PCT", "MNHL_PCT"),
    ]
    rows = []
    for label, teach_col, stu_col in groups:
        rows.append({
            "Group": label,
            "Teachers": pd.to_numeric(teach_row.get(teach_col, 0), errors="coerce") or 0,
            "Students": pd.to_numeric(stu.get(stu_col, 0), errors="coerce") or 0,
        })
    diversity_df = pd.DataFrame(rows)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Teachers", x=diversity_df["Group"], y=diversity_df["Teachers"],
                         marker_color=LEHS_NAVY))
    fig.add_trace(go.Bar(name="Students", x=diversity_df["Group"], y=diversity_df["Students"],
                         marker_color=LEHS_GOLD))
    fig.update_layout(**DEFAULT_LAYOUT, barmode="group", yaxis_tickformat=".0%",
                       yaxis_title="Share")
    st.plotly_chart(fig, width="stretch")

    # Gap callout
    hl_gap = diversity_df.loc[diversity_df["Group"] == "Hispanic/Latino", "Students"].iloc[0] - \
             diversity_df.loc[diversity_df["Group"] == "Hispanic/Latino", "Teachers"].iloc[0]
    if hl_gap > 0.2:
        st.warning(
            f"**Representation gap**: Hispanic/Latino students make up "
            f"{diversity_df.loc[diversity_df['Group']=='Hispanic/Latino','Students'].iloc[0]:.0%} "
            f"of LEHS enrollment, but only "
            f"{diversity_df.loc[diversity_df['Group']=='Hispanic/Latino','Teachers'].iloc[0]:.0%} "
            f"of teachers identify the same way — a "
            f"**{hl_gap*100:.0f}-point gap**."
        )

st.divider()

# ---------------------------------------------------------------------------
# Staff composition by job classification
# ---------------------------------------------------------------------------

st.header("Staff Composition by Role")

key_roles = latest[latest["JOBCLASS_CAT"].isin([
    "Administrators", "Instructional Staff", "Instructional Support Staff",
    "Instructional Support and Special Education Shared Staff",
    "Medical/Health Services", "Office/Clerical/Administrative Support",
    "Paraprofessional",
])].copy()

if not key_roles.empty:
    role_summary = (
        key_roles.groupby("JOBCLASS_CAT")["FTE_TOTAL"]
        .apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
        .reset_index()
        .sort_values("FTE_TOTAL", ascending=True)
    )
    fig = px.bar(role_summary, x="FTE_TOTAL", y="JOBCLASS_CAT", orientation="h",
                 color_discrete_sequence=[LEHS_NAVY])
    fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="FTE", yaxis_title="")
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Teacher diversity trend over time
# ---------------------------------------------------------------------------

st.header("Teacher Diversity Trend Over Time")

teachers_all_years = lehs_staff[lehs_staff["JOBCLASS"].astype(str).str.lower() == "teacher"].copy()
if not teachers_all_years.empty:
    teachers_all_years = teachers_all_years.sort_values("SY")
    div_long = teachers_all_years.melt(
        id_vars="SY",
        value_vars=["HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT", "MNHL_PCT"],
        var_name="Group", value_name="Pct",
    )
    label_map = {
        "HL_PCT": "Hispanic/Latino", "BAA_PCT": "African American/Black",
        "AS_PCT": "Asian", "WH_PCT": "White", "MNHL_PCT": "Multi-Race",
    }
    div_long["Group"] = div_long["Group"].map(label_map)
    div_long["Pct"] = pd.to_numeric(div_long["Pct"], errors="coerce")
    div_long = div_long.dropna(subset=["Pct"])

    fig = px.line(
        div_long, x="SY", y="Pct", color="Group", markers=True,
        color_discrete_map={
            "Hispanic/Latino":        SUBGROUP_PALETTE["Hispanic/Latino"],
            "African American/Black": SUBGROUP_PALETTE["African American/Black"],
            "Asian":                  SUBGROUP_PALETTE["Asian"],
            "White":                  SUBGROUP_PALETTE["White"],
            "Multi-Race":             SUBGROUP_PALETTE["Multi-Race, Non-Hispanic/Latino"],
        },
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="Share of teachers")
    st.plotly_chart(fig, width="stretch")

st.divider()

st.subheader("Data not yet here")
st.markdown(
    """
The following teacher/workforce indicators require DESE Profiles statereport bulk
downloads (not on E2C Hub) and will be added once `scripts/02_download_dese_profiles.py`
is filled in:

- **Teacher retention rate** year-over-year
- **Years of experience** distribution (0-3, 4-9, 10+)
- **% In-field** by subject (teaching with subject-specific licensure)
- **Counselor / Nurse / Psychologist / Social Worker ratios** per 100 students
- **Class size** by subject (ELA, Math, Science)
- **Educator pipeline** (Teach Mass): MTEL pass rates for new hires
"""
)
