"""Section 8 — Discipline, Climate & Safety."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, STATE_COLOR, SUBGROUP_PALETTE
from utils.constants import (
    GENDER_PALETTE,
    LCHS_SCHOOL_CODE,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)
from utils.data_loader import get_dart_indicator, load_dataset
from utils.interpret import sy_label

# Same-district contrast: LEHS, LCHS, and LVTI (Lynn Tech) are Lynn's three
# largest comprehensive high schools. Comparing them isolates school-level
# effects from city-level demographics.
LVTI_SCHOOL_CODE = "01630605"
LCHS_COLOR = LEHS_GOLD
LVTI_COLOR = "#26A69A"  # teal

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
    fig = px.line(
        all_stu, x="SY", y="PCT_CHRON_ABS_10", color="School", markers=True,
        color_discrete_map={
            "Lynn English": LEHS_NAVY,
            "Lynn Classical": LCHS_COLOR,
            "Lynn Tech": LVTI_COLOR,
        },
    )
    fig.update_traces(selector=dict(name="Lynn Classical"),
                      line=dict(dash="dash", width=2))
    fig.update_traces(selector=dict(name="Lynn Tech"),
                      line=dict(dash="dot", width=2))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                      yaxis_title="% Chronically Absent (10%+ missed)")
    st.plotly_chart(fig, use_container_width=True)

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
    st.plotly_chart(fig, use_container_width=True)

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
    st.image(str(path), caption=caption, use_container_width=True)


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

st.divider()

# ---------------------------------------------------------------------------
# Attendance rate trend — LEHS vs LCHS
# ---------------------------------------------------------------------------

st.header("Attendance Rate")
att_rate = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "End of Year")].copy()
att_rate["ATTEND_RATE"] = pd.to_numeric(att_rate["ATTEND_RATE"], errors="coerce")
if not att_rate.empty:
    fig = px.line(
        att_rate.sort_values("SY"), x="SY", y="ATTEND_RATE", color="School",
        markers=True,
        color_discrete_map={
            "Lynn English": LEHS_NAVY,
            "Lynn Classical": LCHS_COLOR,
            "Lynn Tech": LVTI_COLOR,
        },
    )
    fig.update_traces(selector=dict(name="Lynn Classical"),
                      line=dict(dash="dash", width=2))
    fig.update_traces(selector=dict(name="Lynn Tech"),
                      line=dict(dash="dot", width=2))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                      yaxis_title="Attendance rate")
    st.plotly_chart(fig, use_container_width=True)

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
                st.plotly_chart(fig, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)

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
        fig = px.line(
            tdf, x="SY", y="VALUE", color="Series", markers=True,
            color_discrete_map={
                "Lynn English": LEHS_NAVY,
                "Lynn district": "#90A4AE",
                "Massachusetts": STATE_COLOR,
            },
        )
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
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "The school-wide rate hides large gaps. **Students with disabilities "
            "are suspended at nearly double the all-students rate**, and **boys "
            "are suspended more than twice as often as girls**. These patterns "
            "mirror statewide disproportionality, but the size of the gap is the "
            "local story — it points to where climate and support efforts would "
            "do the most good. (Asian students are shown only where DESE reported "
            "a value; small-count subgroups can be suppressed.)"
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
    ind_pick = st.selectbox(
        "Indicator", options=sorted(disp["INDICATOR"].dropna().unique()), key="disp_ind",
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
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Federal CRDC indicators
# ---------------------------------------------------------------------------

crdc = load_dataset("crdc_discipline")
if not crdc.empty:
    st.header("Federal CRDC indicators")
    st.caption(
        "Biennial federal Civil Rights Data Collection. Captures what DESE doesn't: "
        "school-based arrests, law-enforcement referrals, restraint/seclusion."
    )
    st.dataframe(crdc.head(50), use_container_width=True)
else:
    st.caption(
        "_Federal CRDC school-level discipline data (arrests, law-enforcement "
        "referrals, restraint/seclusion) isn't yet wired in._"
    )

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Student attendance': attendance,
        'Discipline (disaggregated by subgroup)': disagg,
        'Discipline disproportionality': disp,
        'CRDC discipline': crdc,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

