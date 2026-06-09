"""Section 6 — Teachers & Workforce."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label

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
    st.metric(f"LEHS Total Staff FTE (SY {sy_label(latest_year)})", f"{total_fte:,.0f}")
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
    # Teacher shares are computed from the precise head counts (_CNT / FTE_TOTAL)
    # rather than DESE's rounded 1-decimal _PCT columns — otherwise small groups
    # collapse to 10%/0%/80% and the bars misrepresent the real mix. Student
    # shares already carry precise _PCT values, so those stay as published.
    teach_fte_total = pd.to_numeric(teach_row.get("FTE_TOTAL", 0), errors="coerce") or 0
    groups = [
        ("Hispanic/Latino",          "HL_CNT",   "HL_PCT"),
        ("African American/Black",   "BAA_CNT",  "BAA_PCT"),
        ("Asian",                    "AS_CNT",   "AS_PCT"),
        ("White",                    "WH_CNT",   "WH_PCT"),
        ("Multi-Race",               "MNHL_CNT", "MNHL_PCT"),
    ]
    rows = []
    for label, teach_cnt_col, stu_col in groups:
        teach_cnt = pd.to_numeric(teach_row.get(teach_cnt_col, 0), errors="coerce") or 0
        teach_share = (teach_cnt / teach_fte_total) if teach_fte_total else 0
        rows.append({
            "Group": label,
            "LEHS Teachers": teach_share,
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
    st.plotly_chart(fig, use_container_width=True)

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
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Teacher retention — at Lynn district level (staff_retention dataset)
# ---------------------------------------------------------------------------

st.header("Teacher Retention Rate")
st.caption(
    "Share of teachers in the Lynn district who returned the following year. "
    "DESE reports retention both district-wide and school-by-school; we show "
    "the district-wide rate here so it covers every Lynn teacher, not just one "
    "building."
)

retention = load_dataset("staff_retention")
if not retention.empty:
    # Filter to the District-level row. Without ORG_TYPE == "District" the
    # contains("Teacher") + iloc[-1] selection lands on an individual school row
    # (e.g. LEHS, ~90%) while still being labelled the Lynn district rate.
    lynn_ret = retention[
        (retention["DIST_CODE"] == "01630000")
        & (retention["ORG_TYPE"] == "District")
        & (retention["STAFF_DESC"].astype(str).str.contains("Teacher", case=False, na=False))
    ].copy()
    lynn_ret["RETND_PCT"] = pd.to_numeric(lynn_ret["RETND_PCT"], errors="coerce")
    lynn_ret["RETND_CNT"] = pd.to_numeric(lynn_ret["RETND_CNT"], errors="coerce")
    lynn_ret["TOT_CNT"] = pd.to_numeric(lynn_ret["TOT_CNT"], errors="coerce")
    lynn_ret = lynn_ret.dropna(subset=["RETND_PCT"]).sort_values("SY")
    # DESE's published RETND_PCT is rounded to a single decimal (0.8 / 0.9),
    # which would make this a coarse two-step line. Compute the precise rate
    # from the counts so the latest year reads 83% (1148/1377), not 80%.
    lynn_ret["RETND_RATE"] = lynn_ret["RETND_CNT"] / lynn_ret["TOT_CNT"]

    if not lynn_ret.empty:
        latest_ret = lynn_ret.iloc[-1]
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric(
                f"Lynn district teacher retention (SY {sy_label(int(latest_ret['SY']))})",
                f"{latest_ret['RETND_RATE']:.0%}",
                f"{int(latest_ret['RETND_CNT'])} of {int(latest_ret['TOT_CNT'])} teachers",
            )
        lynn_ret["label"] = lynn_ret["RETND_RATE"].apply(lambda x: f"{x:.0%}")
        fig = px.line(lynn_ret, x="SY", y="RETND_RATE", markers=True, text="label")
        fig.update_traces(line=dict(color=LEHS_NAVY, width=3), textposition="top center")
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                          yaxis_title="% teachers returning the next year")
        with c2:
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Staff attendance (2hei-cc7k, SY2025) — staff present vs scheduled days
# ---------------------------------------------------------------------------

st.header("Staff Attendance")
st.caption(
    "DESE's staff-attendance rate: the share of scheduled days staff were "
    "present (SY 2024-25, the only year DESE has published). Staff absence is a "
    "direct driver of lost instructional time and substitute coverage."
)

staff_attend = load_dataset("teacher_attendance")
if staff_attend.empty:
    st.info("Staff-attendance data is temporarily unavailable.")
else:
    def _sa_rate(df, grp):
        r = df[df["STAFF_GRP"] == grp]["STAFF_ATTEND_RATE"]
        return float(r.iloc[0]) if not r.empty else None

    lehs_sa = staff_attend[staff_attend["ORG_CODE"] == LEHS_SCHOOL_CODE]
    lynn_sa = staff_attend[(staff_attend["DIST_CODE"] == LYNN_DISTRICT_CODE)
                           & (staff_attend["ORG_TYPE"] == "District")]

    c1, c2, c3 = st.columns(3)
    for col, grp, label in [(c1, "Teachers", "LEHS teachers"),
                            (c2, "Administrators", "LEHS administrators"),
                            (c3, "All Staff", "LEHS all staff")]:
        v = _sa_rate(lehs_sa, grp)
        col.metric(label, f"{v:.1%}" if v is not None else "—")

    rows = []
    for grp in ["Teachers", "Administrators", "All Staff"]:
        rows.append({"Staff group": grp, "Series": "Lynn English", "Rate": _sa_rate(lehs_sa, grp)})
        rows.append({"Staff group": grp, "Series": "Lynn district", "Rate": _sa_rate(lynn_sa, grp)})
    bar = pd.DataFrame(rows).dropna(subset=["Rate"])
    if not bar.empty:
        fig = px.bar(bar, x="Staff group", y="Rate", color="Series", barmode="group",
                     color_discrete_map={"Lynn English": LEHS_GOLD, "Lynn district": LEHS_NAVY})
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                          yaxis_title="Attendance rate", xaxis_title="",
                          yaxis_range=[0.8, 1.0])
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

        # Plain-language callout: the experienced-teacher share has fallen sharply.
        exp_series = td_lynn.dropna(subset=["EXP_TCHR_PCT"]).sort_values("SY")
        if len(exp_series) >= 2:
            exp_latest = exp_series.iloc[-1]
            exp_latest_yr = int(exp_latest["SY"])
            # Compare against the value ~4 years earlier (fall back to earliest available).
            earlier = exp_series[exp_series["SY"] <= exp_latest_yr - 4]
            exp_start = earlier.iloc[-1] if not earlier.empty else exp_series.iloc[0]
            exp_start_yr = int(exp_start["SY"])
            drop_pts = (exp_start["EXP_TCHR_PCT"] - exp_latest["EXP_TCHR_PCT"]) * 100
            span_yrs = exp_latest_yr - exp_start_yr
            if drop_pts >= 5 and span_yrs > 0:
                st.warning(
                    f"**Experience is eroding fast.** The share of Lynn teachers "
                    f"with 3+ years of experience fell from "
                    f"**{exp_start['EXP_TCHR_PCT']:.0%}** in SY {sy_label(exp_start_yr)} "
                    f"to **{exp_latest['EXP_TCHR_PCT']:.0%}** in SY {sy_label(exp_latest_yr)} "
                    f"— down about **{drop_pts:.0f} points in {span_yrs} years**. A wave of "
                    f"newer teachers can signal heavy turnover and a thinner bench of "
                    f"veteran mentors."
                )

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
                            "In-Field Teachers":    "#388E3C",
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

        # In-field by SUBJECT (LEHS-level if rows exist). Pin to the latest year
        # that actually has non-null subject rows — the global max SY often has
        # the subject rows present but TCHR_INFLD_PCT blank, which would render
        # an empty chart with no explanation.
        lehs_by_subj = teacher_data[
            (teacher_data["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (teacher_data["SUBJECT"].astype(str).str.lower() != "all teachers")
        ].copy()
        lehs_by_subj["TCHR_INFLD_PCT"] = pd.to_numeric(lehs_by_subj["TCHR_INFLD_PCT"], errors="coerce")
        subj_with_data = lehs_by_subj.dropna(subset=["TCHR_INFLD_PCT"])
        latest_subj_year = int(subj_with_data["SY"].max()) if not subj_with_data.empty else None
        if latest_subj_year:
            sub = lehs_by_subj[lehs_by_subj["SY"] == latest_subj_year].copy()
            sub = sub.dropna(subset=["TCHR_INFLD_PCT"]).sort_values("TCHR_INFLD_PCT")
            if not sub.empty:
                st.subheader(f"% In-Field by subject at LEHS (SY {sy_label(latest_subj_year)})")
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
        else:
            st.caption(
                "DESE does not publish a school-level in-field rate broken out by "
                "subject for LEHS, so no by-subject chart is shown here. The "
                "district-wide *% In-field for subject* line above reflects the "
                "available figure."
            )

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
        # LEHS doesn't teach every DESE subject category (e.g. the CH74-* career
        # pathways, Geography, Human Services). Those come back as 0.0 and just
        # clutter the chart — keep only subjects that actually have classes.
        by_subj = by_subj[by_subj["AVG_CLSS_CNT"] > 0]
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
# CRDC support-staff ratios (counselors, nurses, social workers, psychologists)
# ---------------------------------------------------------------------------

st.header("Support-staff ratios (federal CRDC)")
st.caption(
    "Counselor / nurse / social-worker / psychologist FTE per 100 students. "
    "Source: federal CRDC, most recent release at script-write was SY 2017-18. "
    "Compare against ASCA recommendation of 1 counselor per 250 students."
)

crdc_staff = load_dataset("crdc_staffing")
if crdc_staff.empty:
    st.info(
        "CRDC staffing data not yet wired in — bulk archive is at "
        "data/raw/crdc/, parsing is a follow-up. See scripts/04_download_crdc.py."
    )
else:
    cols = [c for c in ["COUNSELOR_FTE", "NURSE_FTE", "SOCIAL_WORKER_FTE",
                         "PSYCHOLOGIST_FTE", "LAW_ENFORCEMENT_FTE"]
            if c in crdc_staff.columns]
    if cols:
        st.dataframe(crdc_staff[["SCHOOL_NAME", "STUDENT_ENROLLMENT"] + cols].head(30),
                     use_container_width=True)

# ---------------------------------------------------------------------------
# Educator age profile (educators_by_age, a4b4-k49f) — workforce aging / pipeline
# ---------------------------------------------------------------------------

st.header("Educator Age Profile")
st.caption(
    "How LEHS's educator workforce splits across age bands, from DESE's "
    "*Educators by Age* dataset (E2C, a4b4-k49f). The headline uses the "
    "all-educators rollup. Two numbers frame the talent pipeline: the **near-"
    "retirement share** (ages 57-64 plus 65+), which signals how much "
    "experience may walk out the door soon, and the **under-26 share**, the "
    "newest entrants refilling it. Shares are of full-time-equivalent (FTE) "
    "staff and sum to ~100% across the bands."
)

educ_age = load_dataset("educators_by_age")
if educ_age.empty:
    st.info("Educator-age data is temporarily unavailable.")
else:
    age_roll = educ_age[
        (educ_age["JOB_CAT"].astype(str) == "All")
        & (educ_age["JOB_NAME"].astype(str) == "All")
    ].copy()
    # Prefer LEHS school-level; fall back to the Lynn district rollup if the
    # school-level rows are sparse/absent.
    lehs_age = age_roll[age_roll["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    if not lehs_age.empty:
        scope_df, scope_label = lehs_age, "Lynn English High"
    else:
        scope_df = age_roll[
            (age_roll["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (age_roll["ORG_TYPE"] == "District")
        ].copy()
        scope_label = "Lynn district"

    scope_df = scope_df.dropna(subset=["SY"])
    if scope_df.empty:
        st.info("No educator-age rollup rows found for LEHS or the Lynn district.")
    else:
        # Age bands in order, with the two oldest flagged as "near retirement".
        AGE_BANDS = [
            ("UND_26_PCT",      "Under 26",  False),
            ("BTWN_26_32_PCT",  "26-32",     False),
            ("BTWN_33_40_PCT",  "33-40",     False),
            ("BTWN_41_48_PCT",  "41-48",     False),
            ("BTWN_49_56_PCT",  "49-56",     False),
            ("BTWN_57_64_PCT",  "57-64",     True),
            ("OVR_64_PCT",      "65+",       True),
        ]
        latest_age_year = int(scope_df["SY"].max())
        row = scope_df[scope_df["SY"] == latest_age_year].iloc[0]

        band_rows = []
        for col, label, near_retire in AGE_BANDS:
            band_rows.append({
                "Age band": label,
                "Share": pd.to_numeric(row.get(col), errors="coerce"),
                "Near retirement": near_retire,
            })
        band_df = pd.DataFrame(band_rows).dropna(subset=["Share"])

        near_retire_share = pd.to_numeric(row.get("NEAR_RETIRE_PCT"), errors="coerce")
        under26_share = pd.to_numeric(row.get("UND_26_PCT"), errors="coerce")

        c1, c2, c3 = st.columns(3)
        with c1:
            fte = pd.to_numeric(row.get("FTE_CNT"), errors="coerce")
            st.metric(
                f"{scope_label} educator FTE (SY {sy_label(latest_age_year)})",
                f"{fte:,.0f}" if pd.notna(fte) else "—",
            )
        with c2:
            st.metric(
                "Near retirement (57+)",
                f"{near_retire_share:.0%}" if pd.notna(near_retire_share) else "—",
            )
        with c3:
            st.metric(
                "Under 26",
                f"{under26_share:.0%}" if pd.notna(under26_share) else "—",
            )

        if not band_df.empty:
            # Highlight the two near-retirement bands in gold against navy.
            colors = [LEHS_GOLD if nr else LEHS_NAVY for nr in band_df["Near retirement"]]
            band_df["label"] = band_df["Share"].apply(lambda x: f"{x:.0%}")
            fig = go.Figure(
                go.Bar(
                    x=band_df["Age band"], y=band_df["Share"],
                    marker_color=colors, text=band_df["label"],
                    textposition="outside",
                )
            )
            fig.update_layout(
                **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                yaxis_title="Share of educator FTE", xaxis_title="Age band",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Gold bars are the near-retirement bands (57-64 and 65+)."
            )

        # Plain-language workforce-aging / pipeline callout.
        if pd.notna(near_retire_share) and pd.notna(under26_share):
            if near_retire_share >= under26_share:
                st.warning(
                    f"**An aging bench.** At {scope_label}, "
                    f"**{near_retire_share:.0%}** of educators are 57 or older "
                    f"and could retire within several years, while only "
                    f"**{under26_share:.0%}** are under 26 to backfill them "
                    f"(SY {sy_label(latest_age_year)}). When the near-retirement "
                    f"share outweighs the youngest entrants, the experienced "
                    f"core can thin faster than the pipeline refills it."
                )
            else:
                st.info(
                    f"**A younger-leaning workforce.** At {scope_label}, "
                    f"**{under26_share:.0%}** of educators are under 26 versus "
                    f"**{near_retire_share:.0%}** at 57 or older "
                    f"(SY {sy_label(latest_age_year)}) — the entry pipeline is "
                    f"currently larger than the near-retirement group, though a "
                    f"younger staff can also mean less veteran experience."
                )

st.divider()

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Staffing (race/gender)': staffing,
        'Enrollment & demographics': enrollment,
        'Staff attendance': load_dataset("teacher_attendance"),
        'Educators by age': load_dataset("educators_by_age"),
        'CRDC staffing': crdc_staff,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

