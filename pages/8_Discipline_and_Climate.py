"""Section 8 — Discipline, Climate & Safety."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE, PROCESSED_DIR
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
all_stu = att[(att["STU_GRP"] == "All Students") & (att["ATTEND_PERIOD"] == "FY")].sort_values("SY")
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

st.info(
    "**Privacy note.** Individual student addresses are never shown. All "
    "maps below are aggregated — KDE density surfaces, 100m/150m grid "
    "cells, hexbins, or statistical distributions. Cells with fewer than "
    "the minimum count are filtered out. The full identifying analysis is "
    "held privately and is not part of the public dashboard. See *Where "
    "Our Students Live* (sidebar) for the residential-pattern view."
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
    "When read against the [Lynn page](/Lynn_City) (Neighborhoods tab — "
    "Census ACS demographics by tract), this also separates *distance "
    "effects* from *neighborhood demographic effects*."
)

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
if disp.empty or disp["GROUP_RATE"].dropna().empty:
    st.info(
        "Disaggregated discipline data not yet populated — the ingest scaffold "
        "is in place (scripts/03_download_dese_statereport.py) but the SSDR "
        "HTML parser still needs year-specific tuning to extract per-group "
        "values from the page tables. Risk ratios will populate once that lands."
    )
else:
    org_options = disp[["ORG_CODE", "ORG_NAME"]].drop_duplicates().to_dict("records")
    org_pick = st.selectbox(
        "School / district",
        options=org_options,
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

st.header("Federal CRDC indicators")
st.caption(
    "Biennial federal Civil Rights Data Collection. Captures what DESE doesn't: "
    "school-based arrests, law-enforcement referrals, restraint/seclusion. "
    "Most recent release at script-write time was SY 2017-18. See the new "
    "Federal CRDC page (sidebar) for the full deep-dive once data is wired in."
)

crdc = load_dataset("crdc_discipline")
if crdc.empty:
    st.info(
        "CRDC bulk archive downloaded to data/raw/crdc/ — per-school row "
        "extraction is a follow-up. See scripts/04_download_crdc.py."
    )
else:
    st.dataframe(crdc.head(50), use_container_width=True)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Student attendance': attendance,
        'Discipline disproportionality': disp,
        'CRDC discipline': crdc,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

