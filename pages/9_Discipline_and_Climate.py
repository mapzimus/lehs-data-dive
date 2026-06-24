"""Section 8 — Discipline, Climate & Safety."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    LEHS_GOLD,
    LEHS_NAVY,
    STATE_COLOR,
    SUBGROUP_PALETTE,
    data_downloads_panel,
    span_years,
    with_year_gaps,
    year_axis,
)
from utils.constants import (
    GENDER_PALETTE,
    LCHS_SCHOOL_CODE,
    LEHS_SCHOOL_CODE,
    LVTI_COLOR,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)
from utils.data_loader import get_dart_indicator, load_dataset
from utils.interpret import sy_label
from utils.url_state import qp_selectbox

# Same-district contrast: LEHS, LCHS, and LVTI (Lynn Tech) are Lynn's three
# largest comprehensive high schools. Comparing them isolates school-level
# effects from city-level demographics. LVTI_COLOR (Lynn Tech teal) now comes
# from utils.constants so a rebrand is one edit.
LVTI_SCHOOL_CODE = "01630605"
LCHS_COLOR = LEHS_GOLD

# Federal CRDC matches on SCHOOL_NAME (string) — the CRDC public-use file has
# no DESE ORG_CODE. Used by the "Discipline, disaggregated (federal CRDC)"
# section near the end of this page (rolled in from the former Civil Rights
# Data page).
LEHS_CRDC_NAME = "Lynn English High"

st.set_page_config(page_title="Discipline & Climate | LEHS", page_icon="⚖️", layout="wide")
sidebar_attribution()

st.title("Discipline, Climate & Safety")
st.markdown(
    "Out-of-school suspension rates and chronic absenteeism at LEHS, with "
    "by-subgroup breakdowns and same-district contrast against Lynn Classical "
    "and Lynn Tech where the data supports it."
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
susp_lvti = get_dart_indicator(LVTI_SCHOOL_CODE, "Students suspended out-of-school at least once")

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
        if not susp_lvti.empty:
            latest_lvti = susp_lvti.iloc[-1]
            st.metric(f"Lynn Tech (SY {sy_label(latest_lvti['SY'])})",
                      f"{latest_lvti['VALUE']:.1f}%")
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
        if not susp_lvti.empty:
            fig.add_trace(go.Scatter(
                x=susp_lvti["SY"], y=susp_lvti["VALUE"],
                mode="lines+markers", name="Lynn Tech",
                line=dict(color=LVTI_COLOR, width=2, dash="dot"),
            ))
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_title="% suspended at least once",
            yaxis_ticksuffix="%",
        )
        year_axis(fig)
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

att = attendance[attendance["ORG_CODE"].isin(
    [LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE, LVTI_SCHOOL_CODE]
)].copy()
att["STU_GRP"] = att["STU_GRP"].astype(str).str.replace("\xa0", " ")
att["PCT_CHRON_ABS_10"] = pd.to_numeric(att["PCT_CHRON_ABS_10"], errors="coerce")
att["School"] = att["ORG_CODE"].map({
    LEHS_SCHOOL_CODE: "Lynn English",
    LCHS_SCHOOL_CODE: "Lynn Classical",
    LVTI_SCHOOL_CODE: "Lynn Tech",
})

# Overall trend — LEHS vs LCHS vs Lynn Tech
# ATTEND_PERIOD only ever contains "March" / "End of Year" — use the
# end-of-year (full-year) snapshot rather than the nonexistent "FY" literal.
all_stu = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "End of Year")].sort_values("SY")
if not all_stu.empty:
    # Break each school's line at any missing year (incl. the 2020 COVID gap).
    all_stu = with_year_gaps(
        all_stu, "PCT_CHRON_ABS_10", group_col="School", years=span_years(all_stu)
    )
    fig = px.line(
        all_stu, x="SY", y="PCT_CHRON_ABS_10", color="School", markers=True,
        color_discrete_map={
            "Lynn English": LEHS_NAVY,
            "Lynn Classical": LCHS_COLOR,
            "Lynn Tech": LVTI_COLOR,
        },
    )
    fig.update_traces(connectgaps=False)
    fig.update_traces(selector=dict(name="Lynn Classical"),
                      line=dict(dash="dash", width=2))
    fig.update_traces(selector=dict(name="Lynn Tech"),
                      line=dict(dash="dot", width=2))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                      yaxis_title="% Chronically Absent (10%+ missed)")
    year_axis(fig)
    st.plotly_chart(fig, width="stretch")

# By subgroup — LEHS only (LCHS comparison on subgroups would clutter the chart)
priority = ["All Students", "English Learners", "Hispanic or Latino",
            "Black or African American", "Asian", "White", "Low Income",
            "Students with Disabilities", "High Needs"]
lehs_att = att[att["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
sub_g = lehs_att[(lehs_att["STU_GRP"].isin(priority)) & (lehs_att["ATTEND_PERIOD"] == "End of Year")].copy()

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
    year_axis(fig)
    st.plotly_chart(fig, width="stretch")

    # ---------------------------------------------------------------------------
    # Latest year — chronic absence rates with 95% Wilson CIs by subgroup
    # ---------------------------------------------------------------------------
    # Attendance data has no STU_CNT column. We compute denominators from the
    # enrollment file: subgroup-specific counts where available, otherwise from
    # PCT * TOTAL_CNT for race groups.

    enrollment = load_dataset("enrollment_demographics")
    SUBGROUP_TO_ENR = {
        "All Students":               ("TOTAL_CNT", None),
        "English Learners":           ("EL_CNT",   None),
        "Low Income":                 ("LI_CNT",   None),
        "Students with Disabilities": ("SWD_CNT",  None),
        "High Needs":                 ("HN_CNT",   None),
        "Hispanic or Latino":         (None, "HL_PCT"),
        "Black or African American":  (None, "BAA_PCT"),
        "Asian":                      (None, "AS_PCT"),
        "White":                      (None, "WH_PCT"),
    }

    if not enrollment.empty:
        latest_att_year = int(sub_g["SY"].max())
        enr_row = enrollment[
            (enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (enrollment["SY"] == latest_att_year)
        ]
        if not enr_row.empty:
            enr_row = enr_row.iloc[0]
            total = pd.to_numeric(enr_row.get("TOTAL_CNT"), errors="coerce")
            rows_for_summary = []
            for group, (cnt_col, pct_col) in SUBGROUP_TO_ENR.items():
                # Pull the chronic-absence pct for that group in latest year
                pct_row = sub_g[
                    (sub_g["STU_GRP"] == group)
                    & (sub_g["SY"] == latest_att_year)
                ]
                if pct_row.empty:
                    continue
                pct = pd.to_numeric(pct_row.iloc[0]["PCT_CHRON_ABS_10"], errors="coerce")
                if pd.isna(pct):
                    continue
                # Estimate the denominator
                if cnt_col and cnt_col in enr_row.index:
                    n = pd.to_numeric(enr_row[cnt_col], errors="coerce")
                elif pct_col and pct_col in enr_row.index and pd.notna(total):
                    n = float(enr_row[pct_col]) * float(total)
                else:
                    continue
                if pd.isna(n) or n <= 0:
                    continue
                rows_for_summary.append({
                    "STU_GRP": group,
                    "pct": pct,
                    "n": int(round(n)),
                })

            if rows_for_summary:
                from utils.stats import subgroup_summary_md  # noqa: E402
                summary_df = pd.DataFrame(rows_for_summary)
                md = subgroup_summary_md(
                    summary_df,
                    group_col="STU_GRP",
                    pct_col="pct",
                    n_col="n",
                    reference_group="All Students",
                    group_order=priority,
                    title=(
                        f"SY {latest_att_year - 1}-{str(latest_att_year)[-2:]} "
                        f"chronic absence — point estimates with 95% Wilson CIs"
                    ),
                )
                if md:
                    st.markdown(md)
                    st.caption(
                        "Denominators for race/ethnicity rows are estimated from "
                        "enrollment percentages × total enrollment. EL / LI / "
                        "SWD / HN counts come directly from DESE."
                    )

st.divider()

# ---------------------------------------------------------------------------
# Geographic distribution of chronic absenteeism (original research)
# ---------------------------------------------------------------------------

st.header("Where the Absence Comes From — Geographic Analysis")
st.markdown(
    "The headline absenteeism rate is one number for the whole school. This "
    "analysis — **original geospatial research by Maxwell Howe** combining "
    "LEHS student addresses with daily attendance records — answers the "
    "harder question: *which neighborhoods drive that number, and how "
    "strongly does distance from school predict whether a student shows up?*"
)

st.caption(
    "Source: LEHS student addresses (Lynn Public Schools, provided via a data "
    "request) combined with daily attendance records. All maps below are "
    "aggregated — KDE density surfaces, 100m/150m grid cells, hexbins, or "
    "statistical distributions — not individual locations. See *Where Our "
    "Students Live* (sidebar) for the residential-pattern view."
)

_RESEARCH_IMG_DIR = PROCESSED_DIR / "lehs_research"


def _research_image(slug: str, caption: str = "") -> None:
    path = _RESEARCH_IMG_DIR / f"{slug}.png"
    if not path.exists():
        st.caption(f"_(image not yet generated: {slug}.png)_")
        return
    st.image(str(path), caption=caption, width="stretch")


st.subheader("Does distance from school predict absence?")
st.markdown(
    "Spoiler: **yes** — but the relationship is non-linear, with the largest "
    "effect appearing in specific distance bands rather than uniformly."
)

_research_image(
    "distance_histogram",
    "Distribution of how far LEHS students live from the school. Most "
    "students live within 1-2 miles, with a long tail.",
)
_research_image(
    "absence_vs_distance_gam",
    "Absence rate vs. distance to school (GAM-smoothed). Reveals a "
    "non-linear pattern that simple linear regression would miss.",
)

c1, c2 = st.columns(2)
with c1:
    _research_image(
        "absence_by_distance_band",
        "Mean absence rate by distance band "
        "(0-0.25, 0.25-0.5, 0.5-1, 1-2, 2-3, 3+ miles).",
    )
with c2:
    _research_image(
        "absence_by_distance_quintile",
        "Absence rate by distance quintile — same students split into "
        "5 equally-sized groups by distance from school.",
    )

st.subheader("Geographic absenteeism hotspots")
st.markdown(
    "Identifies *regions* of Lynn with concentrated absence rates above "
    "policy thresholds (20%, 30%). Hotspots are shown as aggregated "
    "hexagonal cells, never individual points."
)

_research_image(
    "absenteeism_hotspots_geo",
    "Citywide view of absenteeism hotspots — colored regions where "
    "average absence rates exceed 20% or 30%.",
)

c1, c2 = st.columns(2)
with c1:
    _research_image(
        "hexbin_absenteeism_100m",
        "Hexbin map of average absence rate per 100m hexagonal cell. "
        "Cells with fewer than ~5% student presence are filtered out.",
    )
with c2:
    _research_image(
        "hotspot_hexagons_above_20",
        "Hexagonal cells (100m) where average absence rate > 20% — the "
        "explicit policy-attention hotspots citywide.",
    )

st.markdown(
    "**Implication.** Aggregate absence rates can mask sharply concentrated "
    "geographic patterns. Schools targeting outreach to the highest-absence "
    "neighborhoods get more leverage per dollar than uniform interventions. "
    "When read against the [Lynn page](/Lynn_City?embed=true) (Neighborhoods tab — "
    "Census ACS demographics by tract), this also separates *distance "
    "effects* from *neighborhood demographic effects*."
)

crosslink_callout(
    "**Where students live shapes who shows up.** The geographic absence "
    "patterns above line up with the residential and commute analysis on the "
    "*Where Students Live* page, and with the city's neighborhood demographics "
    "(Census ACS by tract) on the *Lynn* page — read together they separate a "
    "distance effect from a neighborhood-demographic effect.",
    url_path="Where_Students_Live",
    label="Where Students Live →",
)
crosslink_callout(
    "**Lynn neighborhood context.** Tract-level demographics, income, and "
    "housing for the neighborhoods the absence hotspots fall in.",
    url_path="Lynn_City",
    label="Lynn (Neighborhoods) →",
)

st.divider()

# ---------------------------------------------------------------------------
# Attendance rate trend — LEHS vs LCHS
# ---------------------------------------------------------------------------

st.header("Attendance Rate")
att_rate = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "End of Year")].copy()
att_rate["ATTEND_RATE"] = pd.to_numeric(att_rate["ATTEND_RATE"], errors="coerce")
if not att_rate.empty:
    # Break each school's line at any missing year (incl. the 2020 COVID gap).
    att_rate = with_year_gaps(
        att_rate.sort_values("SY"), "ATTEND_RATE",
        group_col="School", years=span_years(att_rate),
    )
    fig = px.line(
        att_rate, x="SY", y="ATTEND_RATE", color="School",
        markers=True,
        color_discrete_map={
            "Lynn English": LEHS_NAVY,
            "Lynn Classical": LCHS_COLOR,
            "Lynn Tech": LVTI_COLOR,
        },
    )
    fig.update_traces(connectgaps=False)
    fig.update_traces(selector=dict(name="Lynn Classical"),
                      line=dict(dash="dash", width=2))
    fig.update_traces(selector=dict(name="Lynn Tech"),
                      line=dict(dash="dot", width=2))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                      yaxis_title="Attendance rate")
    year_axis(fig)
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Student Mobility — churn / intake / stability. Mid-year movement is a
# strong driver of the chronic-absenteeism + academic-disruption story.
# ---------------------------------------------------------------------------

st.header("Student Mobility — Churn, Intake, Stability")
st.caption(
    "**Churn** = % of students who left LEHS mid-year. **Intake** = % who "
    "joined mid-year. **Stability** = % enrolled on both Oct 1 and the last "
    "day of school. High churn means real instructional disruption — teachers "
    "lose students they've built relationships with, and arrivals miss the "
    "first months of context."
)

mobility = load_dataset("student_mobility")
if not mobility.empty:
    lehs_mob = mobility[
        (mobility["ORG_CODE"] == LEHS_SCHOOL_CODE) & (mobility["STU_GRP"] == "All Students")
    ].sort_values("SY")
    dist_mob = mobility[
        (mobility["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (mobility["ORG_TYPE"] == "District")
        & (mobility["STU_GRP"] == "All Students")
    ].sort_values("SY")

    if not lehs_mob.empty:
        latest_mob = lehs_mob.iloc[-1]
        latest_sy_mob = int(latest_mob["SY"])

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                f"Churn (SY {sy_label(latest_sy_mob)})",
                f"{latest_mob['CHURN_PCT']:.0%}" if pd.notna(latest_mob["CHURN_PCT"]) else "—",
                f"{int(latest_mob['CHURN_ENROLL_CNT']):,} students enrolled at some point" if pd.notna(latest_mob["CHURN_ENROLL_CNT"]) else "",
                delta_color="off",
            )
        with c2:
            st.metric(
                "Intake (joined mid-year)",
                f"{latest_mob['INTAKE_PCT']:.0%}" if pd.notna(latest_mob["INTAKE_PCT"]) else "—",
            )
        with c3:
            st.metric(
                "Stability (stayed all year)",
                f"{latest_mob['STAB_PCT']:.0%}" if pd.notna(latest_mob["STAB_PCT"]) else "—",
            )

        # Trend: LEHS vs Lynn district, churn + intake
        trend_rows = []
        for scope_name, frame in [("LEHS", lehs_mob), ("Lynn District", dist_mob)]:
            for col, metric in [("CHURN_PCT", "Churn"), ("INTAKE_PCT", "Intake"), ("STAB_PCT", "Stability")]:
                sub = frame[["SY", col]].dropna().copy()
                if sub.empty:
                    continue
                sub = sub.rename(columns={col: "Pct"})
                sub["Scope"] = scope_name
                sub["Metric"] = metric
                trend_rows.append(sub)

        if trend_rows:
            trend_df = pd.concat(trend_rows, ignore_index=True)
            for metric in ["Churn", "Intake"]:
                sub_trend = trend_df[trend_df["Metric"] == metric]
                if sub_trend.empty:
                    continue
                st.markdown(f"**{metric} rate — LEHS vs. Lynn district**")
                fig = px.line(
                    sub_trend.sort_values(["Scope", "SY"]),
                    x="SY", y="Pct", color="Scope", markers=True,
                    color_discrete_map={"LEHS": LEHS_NAVY, "Lynn District": "#90A4AE"},
                )
                fig.update_traces(selector=dict(name="Lynn District"), line=dict(dash="dash"))
                fig.update_layout(
                    **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                    yaxis_title=f"% {metric.lower()}", xaxis_title="School Year",
                )
                year_axis(fig)
                st.plotly_chart(fig, width="stretch")

        # Subgroup breakdown — latest year, sorted by churn descending
        sub = mobility[
            (mobility["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (mobility["SY"] == latest_sy_mob)
            & (mobility["STU_GRP"] != "All Students")
        ].dropna(subset=["CHURN_PCT"]).copy()
        if not sub.empty:
            st.markdown(f"**Churn rate by student group — SY {sy_label(latest_sy_mob)}**")
            sub = sub.sort_values("CHURN_PCT")
            sub["label"] = sub["CHURN_PCT"].apply(lambda x: f"{x:.0%}")
            fig = px.bar(
                sub, x="CHURN_PCT", y="STU_GRP", orientation="h", text="label",
            )
            fig.update_traces(marker_color=LEHS_NAVY, textposition="outside", cliponaxis=False)
            fig.add_vline(
                x=latest_mob["CHURN_PCT"], line_dash="dash", line_color=LEHS_GOLD,
                annotation_text="All-students rate", annotation_position="top",
            )
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_tickformat=".0%", xaxis_title="% who left mid-year",
                yaxis_title="", height=max(360, 28 * len(sub)),
            )
            st.plotly_chart(fig, width="stretch")

        st.caption(
            "**About these rates:** churn includes any student who was enrolled at "
            "LEHS at some point during the year but had left by year-end. Intake "
            "is the mirror — students who arrived after Oct 1. Both rates use the "
            "full \"enrolled at any point\" denominator. DESE renamed the \"Low "
            "Income\" / \"Economically Disadvantaged\" subgroup twice (2015, 2022), "
            "so subgroup trends across those years should be read cautiously."
        )

st.divider()

# ---------------------------------------------------------------------------
# Disaggregated suspension/expulsion (DESE statereport, by subgroup, 2013-2025)
# ---------------------------------------------------------------------------

st.header("Out-of-School Suspension — Trend and Who It Falls On")
st.caption(
    "DESE's disaggregated discipline file reports four rates — in-school "
    "suspension, **out-of-school suspension (OSS)**, expulsion, and emergency "
    "removal — every year since 2013, broken out by race, English-learner "
    "status, disability, and gender. The charts below focus on OSS, the most "
    "consequential of the four because it removes a student from the building."
)

disagg = load_dataset("discipline_disaggregated")
if disagg.empty:
    st.info("Disaggregated discipline data is temporarily unavailable.")
else:
    disagg = disagg.copy()
    disagg["GROUP"] = disagg["GROUP"].astype(str).str.replace("\xa0", " ")
    disagg["VALUE"] = pd.to_numeric(disagg["VALUE"], errors="coerce")
    OSS = "Out-of-School Suspension Rate"
    STATE_CODE = "00000000"

    # (a) OSS trend — LEHS, with Lynn district + State reference lines.
    oss_all = disagg[(disagg["INDICATOR"] == OSS) & (disagg["DIM"] == "all")].copy()
    trend_frames = []
    for code, name in [(LEHS_SCHOOL_CODE, "Lynn English"),
                       (LYNN_DISTRICT_CODE, "Lynn district"),
                       (STATE_CODE, "Massachusetts")]:
        t = oss_all[oss_all["ORG_CODE"] == code][["SY", "VALUE"]].dropna().copy()
        if not t.empty:
            t["Series"] = name
            trend_frames.append(t)

    if trend_frames:
        tdf = pd.concat(trend_frames, ignore_index=True).sort_values(["Series", "SY"])
        # Break the line at the 2020 COVID gap rather than drawing across it.
        tdf = with_year_gaps(tdf, "VALUE", group_col="Series", years=span_years(tdf))
        fig = px.line(
            tdf, x="SY", y="VALUE", color="Series", markers=True,
            color_discrete_map={
                "Lynn English": LEHS_NAVY,
                "Lynn district": "#90A4AE",
                "Massachusetts": STATE_COLOR,
            },
        )
        fig.update_traces(connectgaps=False)
        fig.update_traces(selector=dict(name="Lynn English"), line=dict(width=3))
        fig.update_traces(selector=dict(name="Lynn district"), line=dict(dash="dash", width=2))
        fig.update_traces(selector=dict(name="Massachusetts"), line=dict(dash="dot", width=2))
        fig.update_layout(
            **DEFAULT_LAYOUT,
            title="Out-of-school suspension rate — LEHS vs. Lynn district vs. state",
            yaxis_tickformat=".0%",
            yaxis_title="% suspended out-of-school",
            xaxis_title="School Year",
        )
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

        st.caption(
            "LEHS ran far above both its district and the state for years — "
            "roughly **31% in 2013**, three to four times the state rate. A "
            "sustained decline brought it down through the late 2010s, and the "
            "**2021 floor (near 0%) reflects the COVID year**, when remote "
            "learning made out-of-school suspension largely moot. The number has "
            "since climbed back toward pre-pandemic territory (**about 9% in "
            "2025**), so the recent rise is partly a return to normal operations "
            "— but it is worth watching, because LEHS again sits above Lynn "
            "district and the state."
        )

    # (b) Latest-year OSS by subgroup — grouped bar.
    latest_disagg_year = int(disagg[disagg["INDICATOR"] == OSS]["SY"].max())
    lehs_oss = disagg[
        (disagg["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (disagg["INDICATOR"] == OSS)
        & (disagg["SY"] == latest_disagg_year)
        & (disagg["DIM"] != "all")
    ].dropna(subset=["VALUE"]).copy()

    # Order subgroups race → ELL → SWD → gender, and color them from the
    # shared subgroup/gender palettes so they read consistently page-to-page.
    SUB_ORDER = [
        "African American/Black", "Asian", "Hispanic/Latino",
        "Multi-Race, Non-Hispanic/Latino", "White",
        "English Learner", "Students w/ Disabilities",
        "Female", "Male",
    ]
    SUB_COLORS = {**SUBGROUP_PALETTE, **GENDER_PALETTE}
    if not lehs_oss.empty:
        lehs_oss["_ord"] = lehs_oss["GROUP"].map(
            {g: i for i, g in enumerate(SUB_ORDER)}
        ).fillna(99)
        lehs_oss = lehs_oss.sort_values("_ord")
        lehs_oss["label"] = lehs_oss["VALUE"].map(lambda v: f"{v:.1%}")

        # All-students reference for the dashed line.
        all_row = disagg[
            (disagg["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (disagg["INDICATOR"] == OSS)
            & (disagg["SY"] == latest_disagg_year)
            & (disagg["DIM"] == "all")
        ]
        all_rate = float(all_row.iloc[0]["VALUE"]) if not all_row.empty else None

        st.markdown(f"**LEHS out-of-school suspension by student group — SY {sy_label(latest_disagg_year)}**")
        fig = px.bar(
            lehs_oss, x="GROUP", y="VALUE", color="GROUP", text="label",
            color_discrete_map=SUB_COLORS,
        )
        fig.update_traces(textposition="outside", cliponaxis=False, showlegend=False)
        if all_rate is not None:
            fig.add_hline(
                y=all_rate, line_dash="dash", line_color=LEHS_GOLD,
                annotation_text=f"All students ({all_rate:.1%})",
                annotation_position="top left",
            )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="% suspended out-of-school",
            xaxis_title="",
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")

        st.caption(
            "The school-wide rate hides large gaps. **Students with disabilities "
            "are suspended at nearly double the all-students rate**, and **boys "
            "are suspended more than twice as often as girls**. These patterns "
            "mirror statewide disproportionality, but the size of the gap is the "
            "local story — it points to where climate and support efforts would "
            "do the most good. (Asian students are shown only where DESE reported "
            "a value; small-count subgroups can be suppressed.)"
        )

        # Suspension-disparity callout — compute each subgroup's OSS rate ratio
        # vs. the school's All-Students rate and flag groups at >=2x. Neutral,
        # factual wording: state the ratio, name DESE as source, no editorial.
        if all_rate is not None and all_rate > 0:
            ratios = []
            for _, r in lehs_oss.iterrows():
                v = pd.to_numeric(r.get("VALUE"), errors="coerce")
                if pd.isna(v):
                    continue
                ratios.append((str(r["GROUP"]), float(v) / all_rate, float(v)))
            flagged = sorted(
                [t for t in ratios if t[1] >= 2.0],
                key=lambda t: t[1], reverse=True,
            )
            if flagged:
                lines = "\n".join(
                    f"- **{g}** — {rate:.1%} ({ratio:.1f}× the all-students rate)"
                    for g, ratio, rate in flagged
                )
                st.warning(
                    f"**Suspension-rate disparity, SY {sy_label(latest_disagg_year)}.** "
                    f"Measured against the LEHS all-students out-of-school "
                    f"suspension rate of **{all_rate:.1%}**, the following "
                    f"student group(s) were suspended at **two or more times** "
                    f"that rate:\n\n{lines}\n\n"
                    "Rate ratios are each group's reported OSS rate divided by "
                    "the all-students rate at the same school and year (DESE "
                    "disaggregated discipline file). Small-count subgroups may "
                    "be suppressed or volatile year to year."
                )
            else:
                st.caption(
                    f"No LEHS student group reached twice the all-students "
                    f"out-of-school suspension rate ({all_rate:.1%}) in "
                    f"SY {sy_label(latest_disagg_year)}; the widest gap that "
                    f"year was {max((t[1] for t in ratios), default=0):.1f}× "
                    "(rate ratios vs. the all-students rate, DESE disaggregated "
                    "discipline file)."
                )

st.divider()

# ---------------------------------------------------------------------------
# Disproportionality view (DESE statereport SSDR)
# ---------------------------------------------------------------------------

st.header("Disproportionality view")
st.caption(
    "Risk ratios compare each subgroup's discipline rate to the all-students "
    "rate at the same school. A ratio >1 means that subgroup is disciplined "
    "more often than average; <1 means less often. Source: DESE statereport "
    "SSDR (School Safety + Discipline Report)."
)

disp = load_dataset("discipline_disproportionality")
if disp.empty:
    st.info("Disproportionality data is temporarily unavailable.")
else:
    org_options = disp[["ORG_CODE", "ORG_NAME"]].drop_duplicates().to_dict("records")
    # Default the picker to Lynn English rather than the first row (State).
    default_org_idx = next(
        (i for i, r in enumerate(org_options) if r["ORG_CODE"] == LEHS_SCHOOL_CODE),
        0,
    )
    org_pick = st.selectbox(
        "School / district",
        options=org_options,
        index=default_org_idx,
        format_func=lambda r: r["ORG_NAME"],
        key="disp_org",
    )
    ind_pick = qp_selectbox(
        "Indicator", sorted(disp["INDICATOR"].dropna().unique()), key="disp_ind",
    )
    sub = disp[(disp["ORG_CODE"] == org_pick["ORG_CODE"])
               & (disp["INDICATOR"] == ind_pick)
               & (disp["RISK_RATIO"].notna())]
    if sub.empty:
        st.info("No values for that combination yet.")
    else:
        fig = px.bar(sub.sort_values(["DIM", "GROUP"]), x="GROUP", y="RISK_RATIO",
                     color="DIM", barmode="group",
                     title=f"{org_pick['ORG_NAME']} — {ind_pick} risk ratios")
        fig.add_hline(y=1.0, line_dash="dash", line_color="#444",
                      annotation_text="All-students baseline")
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Risk ratio (vs. all students)")
        st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Discipline, disaggregated (federal CRDC) — out-of-school suspension counts by
# race, an all-students discipline summary, a disparate-impact check (CRDC
# counts ÷ DESE enrollment denominators), and the full discipline table.
# Rolled in from the former Civil Rights Data page. The CRDC's signature
# feature is its race / disability / English-learner breakdown, captured here.
# ---------------------------------------------------------------------------

st.header("Discipline, disaggregated (federal CRDC)")
st.caption(
    "Out-of-school suspension counts at Lynn English High by student group, "
    "from the 2021-22 federal CRDC (U.S. Dept. of Education, Office for Civil "
    "Rights — civilrightsdata.ed.gov). The federal collection's signature "
    "feature is its race / disability / English-learner breakdown, and it "
    "captures measures DESE does not — school-based arrests, law-enforcement "
    "referrals, restraint/seclusion. **Small-n caution:** these are raw, "
    "privacy-perturbed counts (not rates); the public-use file applies small "
    "random perturbations and suppresses very small cells, so subgroup figures "
    "are approximate and may not sum exactly to totals."
)

crdc = load_dataset("crdc_discipline")
if crdc.empty:
    st.info("Discipline (CRDC) data is unavailable in the current build.")
else:
    disc = crdc.copy()
    metric_cols = ["ISS_COUNT", "OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT",
                   "EXPULSION_COUNT", "ARREST_COUNT", "LE_REFERRAL_COUNT",
                   "RESTRAINT_PHYSICAL", "SECLUSION_COUNT"]
    for c in metric_cols:
        if c in disc.columns:
            disc[c] = pd.to_numeric(disc[c], errors="coerce")

    lehs_d = disc[disc["SCHOOL_NAME"].astype(str).str.strip() == LEHS_CRDC_NAME]
    race = lehs_d[(lehs_d["GROUP_DIM"] == "race")].copy()
    race["TOTAL_OSS"] = race[["OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT"]].sum(axis=1, min_count=1)
    race = race[race["TOTAL_OSS"].fillna(0) > 0].sort_values("TOTAL_OSS")
    if not race.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Suspended once",
                             x=race["OSS_SINGLE_COUNT"], y=race["GROUP"],
                             orientation="h", marker_color=LEHS_NAVY))
        fig.add_trace(go.Bar(name="Suspended more than once",
                             x=race["OSS_MULTIPLE_COUNT"], y=race["GROUP"],
                             orientation="h", marker_color=LEHS_GOLD))
        fig.update_layout(**DEFAULT_LAYOUT, barmode="stack",
                          title="LEHS out-of-school suspensions by race/ethnicity (2021-22)",
                          xaxis_title="Students")
        st.plotly_chart(fig, width="stretch")

    # All-students summary across discipline measures (LEHS).
    tot = lehs_d[lehs_d["GROUP_DIM"] == "total"]
    if not tot.empty:
        row = tot.iloc[0]
        labels = {"ISS_COUNT": "In-school suspension",
                  "OSS_SINGLE_COUNT": "Out-of-school (once)",
                  "OSS_MULTIPLE_COUNT": "Out-of-school (multiple)",
                  "EXPULSION_COUNT": "Expulsions",
                  "ARREST_COUNT": "School-based arrests",
                  "LE_REFERRAL_COUNT": "Referrals to law enforcement"}
        summary = pd.DataFrame(
            {"Measure": list(labels.values()),
             "LEHS students (all groups)": [row.get(k) for k in labels]}
        )
        st.markdown("**LEHS discipline summary — all students**")
        st.dataframe(summary, width="stretch", hide_index=True)

    # --- Disparate-impact check ------------------------------------------
    # CRDC publishes suspension COUNTS only, so rate denominators come from
    # the DESE enrollment file for the same school year (SY 2022 = 2021-22).
    # Estimated subgroup enrollment = DESE share × total enrollment, so the
    # resulting rates and ratios are approximate (see the perturbation
    # caveat at the top of the page). Flag any group whose out-of-school
    # suspension rate is at least 2× the school-wide rate.
    _GROUP_ENR_COLS = {
        "Hispanic/Latino": "HL_PCT",
        "Asian": "AS_PCT",
        "Black/African American": "BAA_PCT",
        "White": "WH_PCT",
        "Two or More Races": "MNHL_PCT",
        "Native Hawaiian/Pacific Islander": "NHPI_PCT",
        "American Indian/Alaska Native": "AIAN_PCT",
        "English Learner": "EL_PCT",
        "Students w/ Disabilities": "SWD_PCT",
    }
    _MIN_GROUP_N = 20  # below this, a one-student swing moves the rate too much

    _enr22 = load_dataset("enrollment_demographics")
    _lehs_enr22 = pd.DataFrame()
    if not _enr22.empty and {"ORG_CODE", "SY"} <= set(_enr22.columns):
        _lehs_enr22 = _enr22[
            (_enr22["ORG_CODE"].astype(str) == LEHS_SCHOOL_CODE)
            & (pd.to_numeric(_enr22["SY"], errors="coerce") == 2022)
        ]

    _oss_cols_ok = {"OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT"} <= set(disc.columns)
    if not tot.empty and not _lehs_enr22.empty and _oss_cols_ok:
        _e = _lehs_enr22.iloc[0]
        _total_n = pd.to_numeric(_e.get("TOTAL_CNT"), errors="coerce")
        _tot_oss = pd.to_numeric(
            tot.iloc[0][["OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT"]],
            errors="coerce",
        ).sum(min_count=1)
        if pd.notna(_total_n) and _total_n > 0 and pd.notna(_tot_oss) and _tot_oss > 0:
            _school_rate = float(_tot_oss) / float(_total_n)
            _flags: list[str] = []
            _checked = 0
            _sub = lehs_d[lehs_d["GROUP_DIM"] != "total"]
            for _, _r in _sub.iterrows():
                _col = _GROUP_ENR_COLS.get(str(_r.get("GROUP", "")).strip())
                if not _col or _col not in _lehs_enr22.columns:
                    continue
                _share = pd.to_numeric(_e.get(_col), errors="coerce")
                if pd.isna(_share):
                    continue
                if _share > 1.5:  # stored as 0-100 rather than a 0-1 fraction
                    _share = _share / 100.0
                _grp_n = float(_share) * float(_total_n)
                if _grp_n < _MIN_GROUP_N:
                    continue  # too small for a stable rate
                _grp_oss = pd.to_numeric(
                    _r[["OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT"]],
                    errors="coerce",
                ).sum(min_count=1)
                if pd.isna(_grp_oss):
                    continue
                _checked += 1
                _ratio_vs_school = (float(_grp_oss) / _grp_n) / _school_rate
                if _ratio_vs_school >= 2.0:
                    _flags.append(
                        f"**{_r['GROUP']}** — {int(_grp_oss)} students suspended "
                        f"out of ≈{_grp_n:,.0f} enrolled "
                        f"(≈{float(_grp_oss) / _grp_n:.1%}), "
                        f"{_ratio_vs_school:.1f}× the school-wide rate"
                    )
            if _flags:
                st.warning(
                    "**Disparate-impact check (2021-22).** The school-wide "
                    f"out-of-school suspension rate was ≈{_school_rate:.1%} "
                    f"({int(_tot_oss)} of {int(_total_n):,} students). The "
                    "following group(s) were suspended at **2× or more** that "
                    "rate:\n\n- " + "\n- ".join(_flags) + "\n\n"
                    "Counts are privacy-perturbed and denominators are "
                    "estimated from DESE enrollment shares, so treat these "
                    "ratios as approximate."
                )
            elif _checked:
                st.caption(
                    f"Disparate-impact check (2021-22): no student group's "
                    f"out-of-school suspension rate exceeds 2× the school-wide "
                    f"rate of ≈{_school_rate:.1%} in this snapshot "
                    f"(groups with fewer than {_MIN_GROUP_N} estimated "
                    f"students are excluded as too small to rate)."
                )

    with st.expander("Full discipline table (all schools × student groups)"):
        st.dataframe(disc, width="stretch", height=400)

st.divider()

# ---------------------------------------------------------------------------
# Annual dropout rate (DESE E2C cmm7-ttbg, 2008-2025)
# ---------------------------------------------------------------------------

st.header("Annual Dropout Rate")
st.caption(
    "The **annual dropout rate** is the share of enrolled students in grades "
    "9-12 who left school during a single year without graduating or "
    "transferring to another program. It is a one-year flow (not the cumulative "
    "or cohort rate), so it tends to be smaller than the headline four-year "
    "figures — but its year-to-year movement is an early-warning signal. "
    "Source: DESE Education-to-Career (Dropout Report)."
)

dropout = load_dataset("dropout")
DROP_STATE_CODE = "00000000"
if dropout.empty:
    st.info("Dropout data is temporarily unavailable.")
else:
    dropout = dropout.copy()
    dropout["STU_GRP"] = dropout["STU_GRP"].astype(str).str.replace("\xa0", " ")
    for _c in ["DRPOUT_PCT_ALL", "DRPOUT_PCT_GRD_09", "DRPOUT_PCT_GRD_10",
               "DRPOUT_PCT_GRD_11", "DRPOUT_PCT_GRD_12"]:
        dropout[_c] = pd.to_numeric(dropout[_c], errors="coerce")

    # (a) Trend — LEHS (All Students) vs Lynn district vs Massachusetts.
    drop_all = dropout[dropout["STU_GRP"] == "All Students"].copy()
    drop_trend_frames = []
    for code, name in [(LEHS_SCHOOL_CODE, "Lynn English"),
                       (LYNN_DISTRICT_CODE, "Lynn district"),
                       (DROP_STATE_CODE, "Massachusetts")]:
        t = drop_all[drop_all["ORG_CODE"] == code][["SY", "DRPOUT_PCT_ALL"]].dropna().copy()
        if not t.empty:
            t["Series"] = name
            drop_trend_frames.append(t)

    if drop_trend_frames:
        dtf = pd.concat(drop_trend_frames, ignore_index=True).sort_values(["Series", "SY"])
        # Break the line at any missing year (incl. the 2020 COVID gap).
        dtf = with_year_gaps(dtf, "DRPOUT_PCT_ALL", group_col="Series", years=span_years(dtf))
        fig = px.line(
            dtf, x="SY", y="DRPOUT_PCT_ALL", color="Series", markers=True,
            color_discrete_map={
                "Lynn English": LEHS_NAVY,
                "Lynn district": "#90A4AE",
                "Massachusetts": STATE_COLOR,
            },
        )
        fig.update_traces(connectgaps=False)
        fig.update_traces(selector=dict(name="Lynn English"), line=dict(width=3))
        fig.update_traces(selector=dict(name="Lynn district"), line=dict(dash="dash", width=2))
        fig.update_traces(selector=dict(name="Massachusetts"), line=dict(dash="dot", width=2))
        fig.update_layout(
            **DEFAULT_LAYOUT,
            title="Annual dropout rate — LEHS vs. Lynn district vs. state",
            yaxis_tickformat=".0%",
            yaxis_title="Annual dropout rate",
            xaxis_title="School Year",
        )
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

        st.caption(
            "LEHS's annual dropout rate has run consistently above both the Lynn "
            "district and the statewide rate — Massachusetts has held near 2% in "
            "recent years, while LEHS has fluctuated several times higher. Single "
            "years can swing sharply because the denominator (one grade-9-to-12 "
            "cohort) is relatively small, so read the multi-year shape rather "
            "than any one point."
        )

    # (b) Latest-year dropout by grade (9-12) — All Students at LEHS.
    lehs_drop = drop_all[drop_all["ORG_CODE"] == LEHS_SCHOOL_CODE].dropna(subset=["DRPOUT_PCT_ALL"])
    if not lehs_drop.empty:
        drop_year = int(lehs_drop["SY"].max())
        grade_row = lehs_drop[lehs_drop["SY"] == drop_year].iloc[0]
        grade_data = []
        for col, label in [("DRPOUT_PCT_GRD_09", "Grade 9"),
                           ("DRPOUT_PCT_GRD_10", "Grade 10"),
                           ("DRPOUT_PCT_GRD_11", "Grade 11"),
                           ("DRPOUT_PCT_GRD_12", "Grade 12")]:
            v = pd.to_numeric(grade_row.get(col), errors="coerce")
            if pd.notna(v):
                grade_data.append({"Grade": label, "Rate": float(v)})
        if grade_data:
            gdf = pd.DataFrame(grade_data)
            gdf["label"] = gdf["Rate"].map(lambda v: f"{v:.1%}")
            st.markdown(f"**LEHS dropout rate by grade — SY {sy_label(drop_year)}**")
            fig = px.bar(gdf, x="Grade", y="Rate", text="label")
            fig.update_traces(marker_color=LEHS_NAVY, textposition="outside",
                              cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat=".0%",
                yaxis_title="Annual dropout rate",
                xaxis_title="",
            )
            st.plotly_chart(fig, width="stretch")
            st.caption(
                "Dropout risk is not spread evenly across grades — it typically "
                "concentrates in the upper grades, where students who have fallen "
                "behind on credits are most likely to leave."
            )

    # (c) Latest-year dropout by student group — LEHS.
    DROP_SUB_PRIORITY = [
        "All Students", "English Learners", "Hispanic or Latino",
        "Black or African American", "Asian", "White",
        "Multi-Race, Not Hispanic or Latino", "Low Income",
        "Economically Disadvantaged", "Students with Disabilities", "High Needs",
        "Female", "Male",
    ]
    DROP_SUB_COLORS = {
        "All Students":                       LEHS_NAVY,
        "English Learners":                   SUBGROUP_PALETTE["English Learner"],
        "Hispanic or Latino":                 SUBGROUP_PALETTE["Hispanic/Latino"],
        "Black or African American":          SUBGROUP_PALETTE["African American/Black"],
        "Asian":                              SUBGROUP_PALETTE["Asian"],
        "White":                              SUBGROUP_PALETTE["White"],
        "Multi-Race, Not Hispanic or Latino": SUBGROUP_PALETTE["Multi-Race, Non-Hispanic/Latino"],
        "Low Income":                         SUBGROUP_PALETTE["Low Income"],
        "Economically Disadvantaged":         SUBGROUP_PALETTE["Economically Disadvantaged"],
        "Students with Disabilities":         SUBGROUP_PALETTE["Students w/ Disabilities"],
        "High Needs":                         SUBGROUP_PALETTE["High Needs"],
        "Female":                             GENDER_PALETTE["Female"],
        "Male":                               GENDER_PALETTE["Male"],
    }
    lehs_drop_sub = dropout[
        (dropout["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (dropout["STU_GRP"].isin(DROP_SUB_PRIORITY))
        & (dropout["STU_GRP"] != "All Students")
    ].dropna(subset=["DRPOUT_PCT_ALL"]).copy()
    if not lehs_drop_sub.empty:
        sub_year = int(lehs_drop_sub["SY"].max())
        lehs_drop_sub = lehs_drop_sub[lehs_drop_sub["SY"] == sub_year].copy()
        lehs_drop_sub["_ord"] = lehs_drop_sub["STU_GRP"].map(
            {g: i for i, g in enumerate(DROP_SUB_PRIORITY)}
        ).fillna(99)
        lehs_drop_sub = lehs_drop_sub.sort_values("_ord")
        lehs_drop_sub["label"] = lehs_drop_sub["DRPOUT_PCT_ALL"].map(lambda v: f"{v:.1%}")

        # All-students reference for the dashed line.
        all_drop_row = drop_all[
            (drop_all["ORG_CODE"] == LEHS_SCHOOL_CODE) & (drop_all["SY"] == sub_year)
        ]
        all_drop_rate = (float(all_drop_row.iloc[0]["DRPOUT_PCT_ALL"])
                         if not all_drop_row.empty else None)

        st.markdown(f"**LEHS dropout rate by student group — SY {sy_label(sub_year)}**")
        fig = px.bar(
            lehs_drop_sub, x="STU_GRP", y="DRPOUT_PCT_ALL", color="STU_GRP",
            text="label", color_discrete_map=DROP_SUB_COLORS,
        )
        fig.update_traces(textposition="outside", cliponaxis=False, showlegend=False)
        if all_drop_rate is not None:
            fig.add_hline(
                y=all_drop_rate, line_dash="dash", line_color=LEHS_GOLD,
                annotation_text=f"All students ({all_drop_rate:.1%})",
                annotation_position="top left",
            )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="Annual dropout rate",
            xaxis_title="",
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "The school-wide rate averages over groups that drop out at very "
            "different rates. English learners and students with disabilities "
            "are usually the most over-represented. Small-count groups may be "
            "suppressed or swing year-to-year, so a single high bar is best read "
            "against the multi-year trend above. (Only groups DESE reported a "
            "value for in this year are shown.)"
        )

st.divider()

# ---------------------------------------------------------------------------
# Instructional days lost to discipline (DESE E2C 3etc-hecr, 2015-2025)
# ---------------------------------------------------------------------------

st.header("Instructional Days Lost to Discipline")
st.caption(
    "For students who were disciplined, DESE reports how many **instructional "
    "days** that discipline cost them, grouped into bands (1 day · 2-3 · 4-7 · "
    "8-10 · more than 10). Longer removals compound academic harm, so the mix "
    "matters as much as the headline discipline count. The percentages below "
    "are the share of **all enrolled students** falling in each band — they sum "
    "to the school's overall discipline rate, not to 100%. Source: DESE "
    "Education-to-Career (Students Disciplined by Days Missed, All Offenses)."
)

days = load_dataset("discipline_days_missed")
if days.empty:
    st.info("Days-missed discipline data is temporarily unavailable.")
else:
    days = days.copy()
    days["STU_GRP"] = days["STU_GRP"].astype(str).str.replace("\xa0", " ")
    DAY_BANDS = [
        ("DAYS_1_PCT", "1 day"),
        ("DAYS_2_3_PCT", "2-3 days"),
        ("DAYS_4_7_PCT", "4-7 days"),
        ("DAYS_8_10_PCT", "8-10 days"),
        ("DAYS_GRTR_10_PCT", "More than 10 days"),
    ]
    for _c, _ in DAY_BANDS:
        days[_c] = pd.to_numeric(days[_c], errors="coerce")
    days["STU_DISCIPL_CNT"] = pd.to_numeric(days["STU_DISCIPL_CNT"], errors="coerce")
    days["STU_CNT"] = pd.to_numeric(days["STU_CNT"], errors="coerce")

    lehs_days = days[
        (days["ORG_CODE"] == LEHS_SCHOOL_CODE) & (days["STU_GRP"] == "All Students")
    ].dropna(subset=[c for c, _ in DAY_BANDS], how="all").copy()

    if lehs_days.empty:
        st.info("No LEHS days-missed rows available yet.")
    else:
        days_year = int(lehs_days["SY"].max())
        drow = lehs_days[lehs_days["SY"] == days_year].iloc[0]
        band_rows = []
        for col, label in DAY_BANDS:
            v = pd.to_numeric(drow.get(col), errors="coerce")
            band_rows.append({"Band": label, "Pct": float(v) if pd.notna(v) else 0.0})
        bdf = pd.DataFrame(band_rows)

        disc_cnt = drow.get("STU_DISCIPL_CNT")
        tot_cnt = drow.get("STU_CNT")
        if pd.notna(disc_cnt) and pd.notna(tot_cnt) and tot_cnt:
            st.markdown(
                f"**SY {sy_label(days_year)}:** {int(disc_cnt):,} of "
                f"{int(tot_cnt):,} LEHS students were disciplined "
                f"(**{disc_cnt / tot_cnt:.1%}** of enrollment)."
            )

        if bdf["Pct"].sum() > 0:
            bdf["label"] = bdf["Pct"].map(lambda v: f"{v:.1%}")
            st.markdown(f"**Share of all LEHS students by days missed — SY {sy_label(days_year)}**")
            fig = px.bar(bdf, x="Band", y="Pct", text="label")
            fig.update_traces(marker_color=LEHS_NAVY, textposition="outside",
                              cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat=".1%",
                yaxis_title="% of all enrolled students",
                xaxis_title="Instructional days lost to discipline",
            )
            st.plotly_chart(fig, width="stretch")

            # Composition among only the disciplined students (bands / discipline rate).
            band_total = bdf["Pct"].sum()
            if band_total > 0:
                comp = bdf.copy()
                comp["Share"] = comp["Pct"] / band_total
                comp["label"] = comp["Share"].map(lambda v: f"{v:.0%}")
                st.markdown(
                    f"**Of disciplined students, how long were they out — "
                    f"SY {sy_label(days_year)}**"
                )
                fig = px.bar(comp, x="Band", y="Share", text="label")
                fig.update_traces(marker_color=LEHS_GOLD, textposition="outside",
                                  cliponaxis=False)
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_tickformat=".0%",
                    yaxis_title="% of disciplined students",
                    xaxis_title="Instructional days lost to discipline",
                )
                st.plotly_chart(fig, width="stretch")
                st.caption(
                    "Re-based to the disciplined students only, this shows the "
                    "severity mix: most discipline at LEHS costs a small number "
                    "of days, but the longest-removal bands (8-10 and 10+ days) "
                    "are where the steepest instructional loss is concentrated. "
                    "(Counts are small in some recent years, so the mix can be "
                    "volatile — read it alongside the discipline rate above.)"
                )

st.divider()

# Chronic absenteeism and the annual dropout rate are both state
# accountability indicators — send readers to the page that scores them.
crosslink_callout(
    "**These show up in the state's accountability scoring.** Chronic "
    "absenteeism and the annual dropout rate are among the indicators "
    "Massachusetts uses to weigh school and district performance. The "
    "Accountability page tracks how LEHS lands on those measures and its "
    "progress toward improvement targets.",
    url_path="Accountability",
    label="State Accountability →",
)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Student attendance': attendance,
        'Discipline (disaggregated by subgroup)': disagg,
        'Discipline disproportionality': disp,
        'Annual dropout rate': dropout,
        'Discipline days missed': days,
        'CRDC discipline': crdc,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

page_footer()

