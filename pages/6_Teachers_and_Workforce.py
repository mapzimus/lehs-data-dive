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
    "Teacher diversity, FTE counts, retention, experience, in-field rates, "
    "and class size — drawn from DESE's staffing and educator datasets."
)
st.caption(
    "**FTE** = full-time equivalent. One full-time staff member = 1.0 FTE; "
    "a half-time staff member = 0.5 FTE. Sums across people, not headcount."
)

staffing = load_dataset("staffing_race_gender")
enrollment = load_dataset("enrollment_demographics")
if staffing.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
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

# JOBCLASS is the specific role; JOBCLASS_CAT is the category.
# DESE uses the literal "All" (not "All Staff") for the rolled-up row.
all_staff = latest[
    (latest["JOBCLASS_CAT"] == "All") & (latest["JOBCLASS"] == "All")
]
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

# ---------------------------------------------------------------------------
# Teacher retention — at Lynn district level (staff_retention dataset)
# ---------------------------------------------------------------------------

st.header("Teacher Retention Rate")
st.caption(
    "Share of teachers in the Lynn district who returned the following year. "
    "DESE publishes this at district level — school-by-school retention "
    "is not separately released."
)

retention = load_dataset("staff_retention")
if not retention.empty:
    lynn_ret = retention[
        (retention["DIST_CODE"] == "01630000")
        & (retention["STAFF_DESC"].astype(str).str.contains("Teacher", case=False, na=False))
    ].copy()
    lynn_ret["RETND_PCT"] = pd.to_numeric(lynn_ret["RETND_PCT"], errors="coerce")
    lynn_ret = lynn_ret.dropna(subset=["RETND_PCT"]).sort_values("SY")

    if not lynn_ret.empty:
        latest_ret = lynn_ret.iloc[-1]
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric(
                f"Lynn district teacher retention (SY {int(latest_ret['SY'])})",
                f"{latest_ret['RETND_PCT']:.0%}",
                f"{int(latest_ret['RETND_CNT'])} of {int(latest_ret['TOT_CNT'])} teachers",
            )
        lynn_ret["label"] = lynn_ret["RETND_PCT"].apply(lambda x: f"{x:.0%}")
        fig = px.line(lynn_ret, x="SY", y="RETND_PCT", markers=True, text="label")
        fig.update_traces(line=dict(color=LEHS_NAVY, width=3), textposition="top center")
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                          yaxis_title="% teachers returning the next year")
        with c2:
            st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Experienced + In-field teachers (teacher_data, SUBJECT=All Teachers)
# ---------------------------------------------------------------------------

st.header("Experienced + In-Field Teachers — Lynn District")
st.caption(
    "Two key DESE quality indicators: **% Experienced** (teachers with 3+ years), "
    "and **% In-Field** (teachers with subject-specific licensure for the subject "
    "they teach)."
)

teacher_data = load_dataset("teacher_data")
if not teacher_data.empty:
    td_lynn = teacher_data[
        (teacher_data["DIST_CODE"] == "01630000")
        & (teacher_data["ORG_TYPE"] == "District")
        & (teacher_data["SUBJECT"].astype(str).str.lower() == "all teachers")
    ].copy()
    for col in ["EXP_TCHR_PCT", "TCHR_INFLD_PCT", "TCHR_LIC_PCT"]:
        if col in td_lynn.columns:
            td_lynn[col] = pd.to_numeric(td_lynn[col], errors="coerce")
    td_lynn = td_lynn.sort_values("SY")

    if not td_lynn.empty:
        long = td_lynn.melt(
            id_vars="SY",
            value_vars=[c for c in ["EXP_TCHR_PCT", "TCHR_INFLD_PCT", "TCHR_LIC_PCT"]
                        if c in td_lynn.columns],
            var_name="Indicator", value_name="Pct",
        )
        long["Indicator"] = long["Indicator"].map({
            "EXP_TCHR_PCT":   "% Experienced (3+ yrs)",
            "TCHR_INFLD_PCT": "% In-field for subject",
            "TCHR_LIC_PCT":   "% Properly licensed",
        })
        long = long.dropna(subset=["Pct"])
        long["label"] = long["Pct"].apply(lambda x: f"{x:.0%}")
        fig = px.line(
            long, x="SY", y="Pct", color="Indicator", markers=True, text="label",
            color_discrete_map={
                "% Experienced (3+ yrs)":   LEHS_NAVY,
                "% In-field for subject":   "#388E3C",
                "% Properly licensed":      LEHS_GOLD,
            },
        )
        fig.update_traces(textposition="top center")
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share")
        st.plotly_chart(fig, width="stretch")

        # In-field by SUBJECT (LEHS-level if rows exist)
        lehs_by_subj = teacher_data[
            (teacher_data["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (teacher_data["SUBJECT"].astype(str).str.lower() != "all teachers")
        ].copy()
        lehs_by_subj["TCHR_INFLD_PCT"] = pd.to_numeric(lehs_by_subj["TCHR_INFLD_PCT"], errors="coerce")
        latest_subj_year = int(lehs_by_subj["SY"].max()) if not lehs_by_subj.empty else None
        if latest_subj_year:
            sub = lehs_by_subj[lehs_by_subj["SY"] == latest_subj_year].copy()
            sub = sub.dropna(subset=["TCHR_INFLD_PCT"]).sort_values("TCHR_INFLD_PCT")
            if not sub.empty:
                st.subheader(f"% In-Field by subject at LEHS (SY {int(latest_subj_year)})")
                sub["label"] = sub["TCHR_INFLD_PCT"].apply(lambda x: f"{x:.0%}")
                fig = px.bar(
                    sub, y="SUBJECT", x="TCHR_INFLD_PCT", orientation="h", text="label",
                    color_discrete_sequence=[LEHS_NAVY],
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(**DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                                  xaxis_title="% teachers with subject licensure",
                                  yaxis_title="")
                st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Class size by subject (class_size dataset)
# ---------------------------------------------------------------------------

st.header("Average Class Size at LEHS — by Subject")

class_size = load_dataset("class_size")
if not class_size.empty:
    cs_lehs = class_size[class_size["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    cs_lehs["AVG_CLSS_CNT"] = pd.to_numeric(cs_lehs["AVG_CLSS_CNT"], errors="coerce")
    cs_lehs = cs_lehs.dropna(subset=["AVG_CLSS_CNT"])
    latest_cs_year = int(cs_lehs["SY"].max()) if not cs_lehs.empty else None
    if latest_cs_year:
        latest = cs_lehs[cs_lehs["SY"] == latest_cs_year].copy()
        # The "All" subject is the overall avg — pull it out for a callout
        overall = latest[latest["SUBJ"].astype(str).str.lower().isin(["all", "all subjects"])]
        c1, c2 = st.columns([1, 3])
        with c1:
            if not overall.empty:
                st.metric(f"Average class (SY {latest_cs_year})",
                          f"{overall['AVG_CLSS_CNT'].iloc[0]:.1f} students")
            st.metric("State average (SY 2025)", "17.2 students")
        # By subject
        by_subj = latest[~latest["SUBJ"].astype(str).str.lower().isin(["all", "all subjects"])]
        by_subj = by_subj.sort_values("AVG_CLSS_CNT")
        if not by_subj.empty:
            by_subj["label"] = by_subj["AVG_CLSS_CNT"].apply(lambda x: f"{x:.1f}")
            fig = px.bar(
                by_subj, y="SUBJ", x="AVG_CLSS_CNT", orientation="h", text="label",
                color_discrete_sequence=[LEHS_GOLD],
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Avg class size",
                              yaxis_title="")
            with c2:
                st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Still ahead
# ---------------------------------------------------------------------------

with st.expander("Indicators not yet sourced"):
    st.markdown(
        """
A few teacher-quality indicators live in sources we haven't pulled into
the dashboard yet:

- **Counselor / nurse / psychologist / social worker ratios** per 100 students —
  DESE Profiles statereport bulk download
- **MTEL pass rates** for newly-hired teachers — Teach Mass educator-pipeline
  Power BI
- **Years-of-experience distribution** broken into 0–3 / 4–9 / 10+ bands —
  partially derivable from EXP_TCHR_PCT but a finer distribution requires
  the Profiles statereport feed
"""
    )
