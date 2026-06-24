"""Section 6 — Teachers & Workforce."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE, year_axis
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset

# Per Max's editorial direction: this page is LEHS-focused. School-to-school
# teacher comparison (LEHS vs Classical vs Tech) lives in
# pages/Lynn_Schools.py (Compare group), where it can be done properly
# across all 5 Lynn high schools.

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

def _pct_teachers_of_color(teachers_row_df: pd.DataFrame) -> float | None:
    if teachers_row_df.empty:
        return None
    nonwhite = sum(pd.to_numeric(teachers_row_df[c], errors="coerce").fillna(0).sum()
                   for c in ["AIAN_CNT","AS_CNT","BAA_CNT","HL_CNT","MNHL_CNT","NHPI_CNT"])
    tot = pd.to_numeric(teachers_row_df["FTE_TOTAL"], errors="coerce").sum()
    return (nonwhite / tot) if tot > 0 else None

c1, c2, c3, c4 = st.columns(4)
with c1:
    total_fte = pd.to_numeric(all_staff["FTE_TOTAL"], errors="coerce").sum() if not all_staff.empty else 0
    st.metric(f"LEHS Total Staff FTE ({latest_year})", f"{total_fte:,.0f}")
with c2:
    teacher_fte = pd.to_numeric(teachers["FTE_TOTAL"], errors="coerce").sum() if not teachers.empty else 0
    st.metric("LEHS Teacher FTE", f"{teacher_fte:,.0f}")
with c3:
    enr = enrollment[(enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE) & (enrollment["SY"] == latest_year)]
    if not enr.empty and teacher_fte > 0:
        ratio = enr.iloc[0]["TOTAL_CNT"] / teacher_fte
        st.metric("Student:Teacher Ratio", f"{ratio:.1f}:1")
with c4:
    lehs_pct_color = _pct_teachers_of_color(teachers)
    if lehs_pct_color is not None:
        st.metric("LEHS % Teachers of Color", f"{lehs_pct_color:.0%}")

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
    # Teacher shares are computed from FTE COUNTS, not the staffing dataset's
    # *_PCT columns — those are unreliable (they read ~0 even when the counts
    # are non-zero, which is what made it look like LEHS had zero Black teachers:
    # BAA_CNT is 4 FTE but BAA_PCT is 0.0). Student shares use the enrollment
    # *_PCT columns, which are correct.
    _tfte = pd.to_numeric(teach_row.get("FTE_TOTAL", 0), errors="coerce") or 0
    groups = [
        ("Hispanic/Latino",          "HL_CNT",   "HL_PCT"),
        ("African American/Black",   "BAA_CNT",  "BAA_PCT"),
        ("Asian",                    "AS_CNT",   "AS_PCT"),
        ("White",                    "WH_CNT",   "WH_PCT"),
        ("Multi-Race",               "MNHL_CNT", "MNHL_PCT"),
    ]
    rows = []
    for label, teach_cnt_col, stu_col in groups:
        _cnt = pd.to_numeric(teach_row.get(teach_cnt_col, 0), errors="coerce") or 0
        rows.append({
            "Group": label,
            "LEHS Teachers": (_cnt / _tfte) if _tfte else 0,
            "LEHS Students": pd.to_numeric(stu.get(stu_col, 0), errors="coerce") or 0,
        })
    diversity_df = pd.DataFrame(rows)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="LEHS Students", x=diversity_df["Group"],
                         y=diversity_df["LEHS Students"], marker_color=LEHS_GOLD))
    fig.add_trace(go.Bar(name="LEHS Teachers", x=diversity_df["Group"],
                         y=diversity_df["LEHS Teachers"], marker_color=LEHS_NAVY))
    fig.update_layout(**DEFAULT_LAYOUT, barmode="group", yaxis_tickformat=".0%",
                       yaxis_title="Share")
    st.plotly_chart(fig, use_container_width=True)

    # Representation gap callout
    hl_gap = diversity_df.loc[diversity_df["Group"] == "Hispanic/Latino", "LEHS Students"].iloc[0] - \
             diversity_df.loc[diversity_df["Group"] == "Hispanic/Latino", "LEHS Teachers"].iloc[0]
    if hl_gap > 0.2:
        st.warning(
            f"**Representation gap**: Hispanic/Latino students make up "
            f"{diversity_df.loc[diversity_df['Group']=='Hispanic/Latino','LEHS Students'].iloc[0]:.0%} "
            f"of LEHS enrollment, but only "
            f"{diversity_df.loc[diversity_df['Group']=='Hispanic/Latino','LEHS Teachers'].iloc[0]:.0%} "
            f"of teachers identify the same way — a "
            f"**{hl_gap*100:.0f}-point gap**."
        )

st.divider()

# ---------------------------------------------------------------------------
# Teacher diversity trend over time
# ---------------------------------------------------------------------------

st.header("Teacher Diversity Trend Over Time")

teachers_all_years = lehs_staff[lehs_staff["JOBCLASS"].astype(str).str.lower() == "teacher"].copy()
if not teachers_all_years.empty:
    teachers_all_years = teachers_all_years.sort_values("SY")
    # Shares from FTE COUNTS (the *_PCT columns are unreliable — see the chart above).
    _fte_y = pd.to_numeric(teachers_all_years["FTE_TOTAL"], errors="coerce")
    label_map = {
        "HL_CNT": "Hispanic/Latino", "BAA_CNT": "African American/Black",
        "AS_CNT": "Asian", "WH_CNT": "White", "MNHL_CNT": "Multi-Race",
    }
    for cnt_col in label_map:
        teachers_all_years[cnt_col + "_sh"] = (
            pd.to_numeric(teachers_all_years[cnt_col], errors="coerce") / _fte_y
        )
    div_long = teachers_all_years.melt(
        id_vars="SY",
        value_vars=[c + "_sh" for c in label_map],
        var_name="Group", value_name="Pct",
    )
    div_long["Group"] = div_long["Group"].str.replace("_sh", "", regex=False).map(label_map)
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
    st.plotly_chart(year_axis(fig), use_container_width=True)
    st.caption(
        "Shares are computed from FTE head counts. A caveat on the categories: "
        "DESE's source coding folded some Black/African American staff into the "
        "Multi-Race or Native American buckets in certain earlier years, so a "
        "single-year dip for a small group can reflect a coding change rather "
        "than real turnover — read the trend, not any one point."
    )

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
                "% In-field for subject":   "#74C476",
                "% Properly licensed":      LEHS_GOLD,
            },
        )
        fig.update_traces(textposition="top center")
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share")
        st.plotly_chart(year_axis(fig), use_container_width=True)

        # By race/ethnicity — uses the separate teacher_experience_infield
        # dataset, which disaggregates Experienced and In-Field rates by
        # teacher race rather than by subject.
        tei = load_dataset("teacher_experience_infield")
        if not tei.empty:
            tei_lynn = tei[tei["DIST_CODE"] == "01630000"].copy()
            tei_lynn["IND_PCT"] = pd.to_numeric(tei_lynn["IND_PCT"], errors="coerce")
            tei_lynn = tei_lynn.dropna(subset=["IND_PCT"])
            if not tei_lynn.empty:
                latest_tei_year = int(tei_lynn["SY"].max())
                tei_latest = tei_lynn[tei_lynn["SY"] == latest_tei_year].copy()
                tei_latest = tei_latest[tei_latest["RACE_ETH"] != "All Educators"]
                if not tei_latest.empty:
                    st.subheader(
                        f"Experienced + In-Field by teacher race/ethnicity — "
                        f"Lynn District (SY {latest_tei_year})"
                    )
                    st.caption(
                        "Same two indicators, broken out by educator "
                        "race/ethnicity. Useful for spotting whether the "
                        "newer-teacher / out-of-field burden falls "
                        "disproportionately on educators of color."
                    )
                    tei_latest["label"] = tei_latest["IND_PCT"].apply(
                        lambda x: f"{x:.1f}%"
                    )
                    fig = px.bar(
                        tei_latest.sort_values(["IND", "IND_PCT"]),
                        x="IND_PCT", y="RACE_ETH", color="IND",
                        barmode="group", orientation="h", text="label",
                        color_discrete_map={
                            "Experienced Teachers": LEHS_NAVY,
                            "In-Field Teachers":    "#74C476",
                        },
                    )
                    fig.update_traces(textposition="outside", cliponaxis=False)
                    fig.update_layout(
                        **DEFAULT_LAYOUT,
                        xaxis_title="% of teachers in group",
                        xaxis_ticksuffix="%",
                        yaxis_title="",
                        legend_title="",
                    )
                    fig.update_xaxes(range=[0, 110])
                    st.plotly_chart(fig, use_container_width=True)

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
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_layout(**DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                                  xaxis_range=[0, 1.12],
                                  xaxis_title="% teachers with subject licensure",
                                  yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

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
                st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Student support staff — counselors, psychologists, social workers, nurses.
# The 618 audit flagged that "counselor" was undifferentiated; DESE's JOBCLASS
# field distinguishes the roles, so break them out.
# ---------------------------------------------------------------------------

st.header("Student Support Staff — by Role")
st.caption(
    "\"Counselor\" covers several distinct roles. DESE's staffing file separates "
    "school (guidance) counselors, adjustment counselors, school psychologists, "
    "social workers, and nurses — each a different lever for student support. "
    "FTE for the latest reported year."
)

SUPPORT_ROLE_MAP = {
    "School Counselor":                                     "School Counselor (guidance)",
    "School Adjustment Counselor -- Non-Special Education": "School Adjustment Counselor",
    "School Adjustment Counselor -- Special Education":     "School Adjustment Counselor",
    "School Psychologist -- Non-Special Education":         "School Psychologist",
    "School Psychologist -- Special Education":             "School Psychologist",
    "School Social Worker -- Non-Special Education":        "School Social Worker",
    "School Social Worker -- Special Education":            "School Social Worker",
    "School Nurse -- Non-Special Education":                "School Nurse",
    "School Nurse -- Special Education":                    "School Nurse",
    "School Nurse Leader":                                  "School Nurse",
    "Speech Pathologist":                                  "Speech / OT / PT therapist",
    "Occupational Therapist":                              "Speech / OT / PT therapist",
    "Physical Therapist":                                  "Speech / OT / PT therapist",
}

_staff_latest = lehs_staff[lehs_staff["SY"] == latest_year].copy()
_support = _staff_latest[_staff_latest["JOBCLASS"].isin(SUPPORT_ROLE_MAP)].copy()
if not _support.empty:
    _support["Role"] = _support["JOBCLASS"].map(SUPPORT_ROLE_MAP)
    _support["FTE_TOTAL"] = pd.to_numeric(_support["FTE_TOTAL"], errors="coerce")
    role_fte = (
        _support.groupby("Role", as_index=False)["FTE_TOTAL"].sum()
                .dropna(subset=["FTE_TOTAL"])
    )
    role_fte = role_fte[role_fte["FTE_TOTAL"] > 0].sort_values("FTE_TOTAL")
    if not role_fte.empty:
        role_fte["label"] = role_fte["FTE_TOTAL"].apply(lambda x: f"{x:.1f} FTE")
        fig = px.bar(
            role_fte, x="FTE_TOTAL", y="Role", orientation="h", text="label",
            color_discrete_sequence=[LEHS_NAVY],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(
            **DEFAULT_LAYOUT, xaxis_title=f"FTE at LEHS (SY {latest_year})",
            yaxis_title="", xaxis_range=[0, role_fte["FTE_TOTAL"].max() * 1.25],
        )
        st.plotly_chart(fig, use_container_width=True)

        # Students-per-counselor context using the guidance-counselor FTE.
        _enr_l = enrollment[
            (enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE) & (enrollment["SY"] == latest_year)
        ]
        _gc = role_fte.loc[role_fte["Role"] == "School Counselor (guidance)", "FTE_TOTAL"].sum()
        if not _enr_l.empty and _gc:
            _students = pd.to_numeric(_enr_l.iloc[0]["TOTAL_CNT"], errors="coerce")
            if pd.notna(_students) and _students:
                st.caption(
                    f"That's about **{_students / _gc:,.0f} students per school "
                    f"counselor** at LEHS — the American School Counselor "
                    f"Association recommends 250:1."
                )
else:
    st.caption("Student-support role detail isn't available for LEHS this year.")

st.divider()

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Staffing (race/gender)': staffing,
        'Enrollment & demographics': enrollment,
    })
except NameError:
    pass

