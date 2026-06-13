"""Student & Community Wellbeing — proxy signals (absenteeism, support staff, community health)."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, csv_download, data_downloads_panel, with_year_gaps, span_years
from utils.constants import LEHS_SCHOOL_CODE, LEHS_NAVY, LEHS_GOLD, STATE_COLOR
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(page_title="Wellbeing | LEHS", page_icon="🌱", layout="wide")
sidebar_attribution()

# ASCA's recommended student-to-counselor ratio — the national benchmark we
# hold the CRDC counselor FTE against.
ASCA_RATIO = 250
LEHS_CRDC_NAME = "Lynn English High"

# Adult, neighborhood-level CDC PLACES measures most relevant to mental health.
# We checked which exist in places_lynn before curating: "Mental health not
# good among adults" is NOT published for Lynn tracts, so the closest analog
# ("Frequent mental distress among adults") stands in its place.
PLACES_MH_MEASURES = [
    "Depression among adults",
    "Frequent mental distress among adults",
    "Lack of social and emotional support among adults",
    "Loneliness among adults",
    "Short sleep duration among adults",
]

# ---------------------------------------------------------------------------
# 1. Title + honest framing
# ---------------------------------------------------------------------------

st.title("🌱 Student & Community Wellbeing")
st.markdown(
    "Massachusetts doesn't publish a school-level student wellbeing survey in "
    "this pipeline, so this page assembles the closest available signals — each "
    "labeled for what it is. None of the sections below is a direct measure of "
    "Lynn English students' mental health. They are **proxies**: attendance "
    "(an engagement signal), the staff a school employs to support students, "
    "and the adult health profile of the neighborhoods students live in."
)
st.markdown(
    "A youth health/risk-behavior survey (e.g., MYRBS) would fill this gap "
    "directly. It isn't in the data pipeline yet — see "
    "[What We Don't Know](/Data_Gaps) for what the dashboard can and can't show."
)

# ---------------------------------------------------------------------------
# 2. Forward-compatible: a future youth-survey ingest lights up automatically.
# ---------------------------------------------------------------------------

youth = load_dataset("youth_health")

if not youth.empty:
    st.header("Massachusetts youth mental health (statewide)")
    st.warning(
        "**This is Massachusetts statewide data — NOT Lynn or LEHS students.** "
        "It comes from the CDC's Youth Risk Behavior Survey (YRBSS), which is "
        "suppressed below the state level for privacy, so a Lynn-specific number "
        "isn't available (see [What We Don't Know](/Data_Gaps)). It's shown here "
        "as the broader context for the teens this community is raising."
    )
    tot = youth[youth["GROUP"] == "Total"].copy()
    tot["VALUE"] = pd.to_numeric(tot["VALUE"], errors="coerce")
    if not tot.empty:
        fig = px.line(
            tot.sort_values("SY"), x="SY", y="VALUE", color="TOPIC", markers=True,
            labels={"SY": "Survey year", "VALUE": "% of MA high-schoolers",
                    "TOPIC": "Indicator"},
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_ticksuffix="%",
                          title="MA high-school students reporting each indicator (YRBS, biennial)")
        st.plotly_chart(fig, width="stretch")
        src = str(youth["SOURCE"].iloc[0]) if "SOURCE" in youth.columns else ""
        st.caption(f"Source: {src}. The survey runs every two years (2019, 2021, 2023).")
    st.divider()
else:
    st.info(
        "Direct youth-survey data (e.g., MYRBS) is not yet available in this "
        "pipeline. Until it is, the sections below are **proxy signals only** — "
        "see [What We Don't Know](/Data_Gaps)."
    )

# ---------------------------------------------------------------------------
# 3. Engagement proxy — chronic absenteeism (LEHS trend)
# ---------------------------------------------------------------------------

st.header("Engagement proxy — chronic absenteeism")
st.caption(
    "**Proxy, not a mental-health measure.** Chronic absenteeism is DESE's "
    "share of students missing 10%+ of enrolled days (~18 days in a 180-day "
    "year). It's a recognized engagement signal — sustained absence predicts "
    "disengagement and dropout — but it does not measure how students feel."
)

attendance = load_dataset("student_attendance")
abs_lehs = pd.DataFrame()
if not attendance.empty:
    att = attendance.copy()
    att["STU_GRP"] = att["STU_GRP"].astype(str).str.replace("\xa0", " ", regex=False)
    att["PCT_CHRON_ABS_10"] = pd.to_numeric(att["PCT_CHRON_ABS_10"], errors="coerce")
    abs_lehs = att[
        (att["ATTEND_PERIOD"] == "End of Year")
        & (att["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (att["STU_GRP"] == "All Students")
    ][["SY", "PCT_CHRON_ABS_10"]].sort_values("SY")

if not abs_lehs.empty:
    latest = abs_lehs.iloc[-1]
    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric(
            f"LEHS chronically absent (SY {sy_label(latest['SY'])})",
            f"{latest['PCT_CHRON_ABS_10'] * 100:.0f}%",
        )
    with c2:
        plot = with_year_gaps(abs_lehs, "PCT_CHRON_ABS_10", years=span_years(abs_lehs))
        fig = px.line(plot, x="SY", y="PCT_CHRON_ABS_10", markers=True)
        fig.update_traces(connectgaps=False, line=dict(color=LEHS_NAVY, width=3))
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="% chronically absent (10%+ missed)",
            xaxis_title="School year (ending)",
        )
        st.plotly_chart(fig, width="stretch")
    st.caption(
        "Line breaks at the 2020 COVID gap rather than drawing across it. "
        "End-of-year snapshot, All Students."
    )
else:
    st.info("Attendance data is unavailable in the current build.")

st.divider()

# ---------------------------------------------------------------------------
# 4. School support staff (CRDC) — ratios + ASCA benchmark
# ---------------------------------------------------------------------------

st.header("School support staff")
st.caption(
    "**Capacity, not outcomes.** The people a school employs to support "
    "students. Counts come from the federal Civil Rights Data Collection "
    "(CRDC) — the same source the Discipline & Climate page uses."
)

staffing = load_dataset("crdc_staffing")
ratio_df = pd.DataFrame()
counselor_ratio = None
if not staffing.empty:
    lehs_staff = staffing[
        staffing["SCHOOL_NAME"].astype(str).str.strip() == LEHS_CRDC_NAME
    ]
    if not lehs_staff.empty:
        row = lehs_staff.iloc[0]
        enroll = pd.to_numeric(pd.Series([row.get("STUDENT_ENROLLMENT")]), errors="coerce").iloc[0]

        roles = [
            ("Counselor", "COUNSELOR_FTE"),
            ("Nurse", "NURSE_FTE"),
            ("Social worker", "SOCIAL_WORKER_FTE"),
            ("Psychologist", "PSYCHOLOGIST_FTE"),
        ]
        rows = []
        for label, col in roles:
            fte = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
            # Guard div-by-zero / missing: a 0 or NaN FTE yields no ratio.
            ratio = (enroll / fte) if (pd.notna(fte) and fte > 0 and pd.notna(enroll)) else None
            rows.append({"Role": label, "FTE": fte, "Students per staff": ratio})
        ratio_df = pd.DataFrame(rows)
        cr = ratio_df.loc[ratio_df["Role"] == "Counselor", "Students per staff"]
        counselor_ratio = cr.iloc[0] if not cr.empty else None

if not ratio_df.empty:
    cols = st.columns(len(ratio_df))
    for col_ui, (_, r) in zip(cols, ratio_df.iterrows()):
        val = r["Students per staff"]
        col_ui.metric(
            f"Students per {r['Role'].lower()}",
            f"{val:,.0f}" if pd.notna(val) else "n/a",
        )

    if counselor_ratio is not None:
        verdict = "above" if counselor_ratio > ASCA_RATIO else "at or below"
        st.markdown(
            f"At roughly **{counselor_ratio:,.0f} students per counselor**, LEHS "
            f"is {verdict} the **ASCA recommended {ASCA_RATIO}:1** ratio "
            f"({counselor_ratio:,.0f} vs the recommended {ASCA_RATIO}:1)."
        )

    bar_df = ratio_df.dropna(subset=["Students per staff"]).copy()
    if not bar_df.empty:
        fig = px.bar(
            bar_df.sort_values("Students per staff"),
            x="Students per staff", y="Role", orientation="h", text="Students per staff",
        )
        fig.update_traces(marker_color=LEHS_NAVY, texttemplate="%{text:,.0f}",
                          textposition="outside", cliponaxis=False)
        fig.add_vline(
            x=ASCA_RATIO, line_dash="dash", line_color=LEHS_GOLD,
            annotation_text=f"ASCA {ASCA_RATIO}:1", annotation_position="top",
        )
        fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Students per FTE",
                          yaxis_title="")
        st.plotly_chart(fig, width="stretch")

    st.caption(
        "Source: CRDC 2021-22 public-use file. That was a pandemic-recovery "
        "year, and CRDC counts are statistically perturbed in the public file "
        "to protect privacy, so treat these ratios as approximate. The ASCA "
        "benchmark applies to counselors specifically."
    )
else:
    st.info("CRDC staffing data is unavailable in the current build.")

st.divider()

# ---------------------------------------------------------------------------
# 5. Community health context (CDC PLACES) — ADULT, tract-level
# ---------------------------------------------------------------------------

st.header("Community health context")
st.warning(
    "**This is ADULT, neighborhood-level data — NOT a measure of LEHS "
    "students.** The figures below are CDC PLACES model-based estimates of "
    "adult prevalence, averaged across Lynn's census tracts. They describe the "
    "community LEHS students live in, not the students themselves."
)

places = load_dataset("places_lynn")
places_avg = pd.DataFrame()
present_measures = []
if not places.empty:
    p = places.copy()
    p["DATA_VALUE"] = pd.to_numeric(p["DATA_VALUE"], errors="coerce")
    # Only keep curated mental-health-relevant measures that actually exist.
    present_measures = [m for m in PLACES_MH_MEASURES if m in set(p["MEASURE"])]
    sub = p[p["MEASURE"].isin(present_measures)]
    if not sub.empty:
        places_avg = (
            sub.groupby("MEASURE", as_index=False)["DATA_VALUE"]
            .mean()
            .rename(columns={"DATA_VALUE": "Tract-average prevalence (%)"})
            .sort_values("Tract-average prevalence (%)")
        )

if not places_avg.empty:
    fig = px.bar(
        places_avg, x="Tract-average prevalence (%)", y="MEASURE",
        orientation="h", text="Tract-average prevalence (%)",
    )
    fig.update_traces(marker_color=STATE_COLOR, texttemplate="%{text:.1f}%",
                      textposition="outside", cliponaxis=False)
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_title="Adult prevalence, Lynn tract average (%)",
        yaxis_title="",
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Source: CDC PLACES (model-based small-area estimates), simple mean of "
        "Lynn census-tract values per measure. Adults only — included as "
        "community context, never as a student outcome."
    )
else:
    st.info("CDC PLACES community-health data is unavailable in the current build.")

st.divider()

# ---------------------------------------------------------------------------
# 6. Crosslinks
# ---------------------------------------------------------------------------

crosslink_callout(
    "Why isn't there direct student wellbeing data here? See what the dashboard "
    "can and can't show.",
    "Data_Gaps",
    "What we don't know →",
)
st.markdown(
    "Related view: [Discipline & Climate](/Discipline_and_Climate) covers "
    "attendance and discipline together in more depth."
)

# ---------------------------------------------------------------------------
# 7. Downloads + footer
# ---------------------------------------------------------------------------

data_downloads_panel({
    "Chronic absenteeism (LEHS, all students)": abs_lehs,
    "Support-staff ratios (CRDC 2021-22)": ratio_df,
    "Community health context (CDC PLACES, adult)": places_avg,
})

page_footer()
