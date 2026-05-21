"""Section 5 — Success After High School: graduation, college enrollment, persistence."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE
from utils.data_loader import get_dart_indicator, load_dataset

st.set_page_config(page_title="Success After HS | LEHS", page_icon="🏆", layout="wide")
sidebar_attribution()

st.title("Success After High School")
st.markdown(
    "Graduation cohorts, postsecondary enrollment by institution type, and "
    "college persistence to the second year — drawn from DESE's DART: Success "
    "After High School data."
)

dart = load_dataset("dart_success_after_hs")
grad = load_dataset("graduation_rates")
if dart.empty or grad.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------------------------

st.header("Headline Pipeline Metrics")

metrics_to_show = [
    ("4-year cohort graduation rate", "4-Year Grad Rate", "pct"),
    ("9th to 10th grade promotion rate (first-time 9th graders only)", "9-10 Promotion", "pct"),
    ("Annual dropout rate", "Annual Dropout", "pct"),
    ("Students enrolled in postsecondary education in the immediate fall after high school graduation",
     "Immediate College Enrollment", "pct"),
    ("College students persistently enrolled in postsecondary education for the first two years",
     "College Persistence (yr 2)", "pct"),
    ("Grade 12 students who completed FAFSA", "FAFSA Completed", "pct"),
]

cols = st.columns(3)
for i, (ind, label, fmt) in enumerate(metrics_to_show):
    sub = get_dart_indicator(LEHS_SCHOOL_CODE, ind)
    if sub.empty:
        continue
    latest = sub.iloc[-1]
    prior = sub.iloc[-2] if len(sub) > 1 else None
    val = latest["VALUE"]
    # DART percentage indicators are stored as 0-100 (e.g., 81.5 for 81.5%),
    # not 0-1 fractions
    if fmt == "pct":
        display = f"{val:.1f}%"
    else:
        display = f"{val:,.0f}"
    delta = ""
    if prior is not None and pd.notna(prior["VALUE"]):
        diff = val - prior["VALUE"]
        unit = "pts" if fmt == "pct" else ""
        delta = f"{diff:+.1f} {unit} vs SY {int(prior['SY'])}"
    with cols[i % 3]:
        st.metric(label, display, delta)

st.divider()

# ---------------------------------------------------------------------------
# Graduation rate trend by student group
# ---------------------------------------------------------------------------

st.header("4-Year Graduation Rate by Student Group")

g = grad[
    (grad["ORG_CODE"] == LEHS_SCHOOL_CODE)
    & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
].copy()
g["STU_GRP"] = g["STU_GRP"].astype(str).str.replace("\xa0", " ")

priority_groups = [
    "All Students",
    "English Learner", "English Learners", "Former English Learners",
    "Hispanic or Latino", "Black or African American", "Asian", "White",
    "Low Income", "Students with Disabilities", "High Needs",
]
g_focus = g[g["STU_GRP"].isin(priority_groups)].copy()

if not g_focus.empty:
    color_map_grad = {
        "All Students":                LEHS_NAVY,
        "English Learners":            SUBGROUP_PALETTE["English Learner"],
        "English Learner":             SUBGROUP_PALETTE["English Learner"],
        "Former English Learners":     SUBGROUP_PALETTE["Former English Learner"],
        "Hispanic or Latino":          SUBGROUP_PALETTE["Hispanic/Latino"],
        "Black or African American":   SUBGROUP_PALETTE["African American/Black"],
        "Asian":                       SUBGROUP_PALETTE["Asian"],
        "White":                       SUBGROUP_PALETTE["White"],
        "Low Income":                  SUBGROUP_PALETTE["Low Income"],
        "Students with Disabilities":  SUBGROUP_PALETTE["Students w/ Disabilities"],
        "High Needs":                  SUBGROUP_PALETTE["High Needs"],
    }
    fig = px.line(
        g_focus.sort_values("SY"), x="SY", y="GRAD_PCT", color="STU_GRP",
        markers=True, color_discrete_map=color_map_grad,
    )
    fig.update_layout(
        **DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="4-Year Grad Rate",
        xaxis_title="Cohort Year",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 4-year vs 5-year graduation comparison
# ---------------------------------------------------------------------------

st.header("4-Year vs. 5-Year Cohort Graduation")
st.caption(
    "The 5-year rate gives students an extra year — for ELL and SPED students "
    "especially, this often shows meaningful additional graduations."
)

g_both = grad[
    (grad["ORG_CODE"] == LEHS_SCHOOL_CODE)
    & (grad["STU_GRP"] == "All Students")
    & (grad["GRAD_RATE_TYPE"].isin([
        "4-Year Adjusted Cohort Graduation Rate",
        "5-Year Adjusted Cohort Graduation Rate",
    ]))
].copy()

if not g_both.empty:
    fig = px.line(
        g_both.sort_values("SY"), x="SY", y="GRAD_PCT", color="GRAD_RATE_TYPE",
        markers=True,
        color_discrete_map={
            "4-Year Adjusted Cohort Graduation Rate": LEHS_NAVY,
            "5-Year Adjusted Cohort Graduation Rate": LEHS_GOLD,
        },
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Grad Rate")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# LEHS vs LCHS — 4-year graduation rate (Lynn's two main HS side-by-side)
# ---------------------------------------------------------------------------

st.header("LEHS vs. Lynn Classical — 4-Year Graduation Rate")
st.caption(
    "Lynn's two comprehensive high schools side-by-side. Same district, "
    "same policies, overlapping catchments — meaningful differences in "
    "graduation rate isolate school-level effects rather than city-level "
    "demographics."
)

g_both_schools = grad[
    (grad["ORG_CODE"].isin([LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE]))
    & (grad["STU_GRP"] == "All Students")
    & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
].copy()
g_both_schools["School"] = g_both_schools["ORG_CODE"].map({
    LEHS_SCHOOL_CODE: "LEHS",
    LCHS_SCHOOL_CODE: "LCHS",
})

if not g_both_schools.empty:
    fig = px.line(
        g_both_schools.sort_values("SY"), x="SY", y="GRAD_PCT", color="School",
        markers=True,
        color_discrete_map={"LEHS": LEHS_GOLD, "LCHS": "#1A8FE3"},
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="4-Year Graduation Rate",
                       xaxis_title="Cohort Year")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Both-school graduation rate data not available.")

st.divider()

# ---------------------------------------------------------------------------
# Postsecondary enrollment pathway
# ---------------------------------------------------------------------------

st.header("Where do LEHS graduates go?")

immediate = get_dart_indicator(LEHS_SCHOOL_CODE, "Students enrolled in postsecondary education in the immediate fall after high school graduation")
two_year = get_dart_indicator(LEHS_SCHOOL_CODE, "High school graduates enrolled in 2-year postsecondary education")
four_year = get_dart_indicator(LEHS_SCHOOL_CODE, "High school graduates enrolled in 4-year postsecondary education")
persist = get_dart_indicator(LEHS_SCHOOL_CODE, "College students persistently enrolled in postsecondary education for the first two years")

pathway = pd.concat([
    immediate.assign(Indicator="Any college (immediate)"),
    two_year.assign(Indicator="2-year college"),
    four_year.assign(Indicator="4-year college"),
    persist.assign(Indicator="Persisted 2 years"),
])

if not pathway.empty:
    # DART VALUE is 0-100; chart in raw percent and label axis explicitly
    fig = px.line(
        pathway.sort_values("SY"), x="SY", y="VALUE", color="Indicator",
        markers=True,
        color_discrete_map={
            "Any college (immediate)": LEHS_NAVY,
            "2-year college":          "#1976D2",
            "4-year college":          "#388E3C",
            "Persisted 2 years":       LEHS_GOLD,
        },
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="% of cohort",
                       yaxis_ticksuffix="%", yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "**Indicator definitions** — "
        "**Any college (immediate)**: % of HS graduates who enrolled in any "
        "postsecondary institution the fall directly after graduation. "
        "**2-year / 4-year college**: subsets of the above, by institution type. "
        "**Persisted 2 years**: of the students who enrolled in college, the % "
        "who were still enrolled in their second fall semester (i.e., didn't drop "
        "out after year one). Persistence is a strong predictor of degree "
        "completion."
    )

st.divider()

# ---------------------------------------------------------------------------
# Plans of HS Graduates
# ---------------------------------------------------------------------------

st.header("Self-Reported Plans of Graduates")
st.caption("From end-of-year surveys of departing seniors.")

plans = load_dataset("plans_of_graduates")
plans_lehs = plans[plans["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY").copy()

if not plans_lehs.empty:
    plan_cols = {
        "COLL_4YRPUB_PCT": "4-yr Public College",
        "COLL_4YRPRV_PCT": "4-yr Private College",
        "COLL_2YRPUB_PCT": "2-yr Public College",
        "COLL_2YRPRV_PCT": "2-yr Private College",
        "WORK_PCT":        "Work",
        "MILITARY_PCT":    "Military",
        "APPREN_PCT":      "Apprenticeship",
        "OTHER_PLANS_PCT": "Other",
        "UNKNWN_PLANS_PCT":"Unknown",
    }
    plans_long = plans_lehs.melt(
        id_vars="SY", value_vars=list(plan_cols.keys()),
        var_name="Plan", value_name="Pct",
    )
    plans_long["Plan"] = plans_long["Plan"].map(plan_cols)
    plans_long = plans_long.dropna(subset=["Pct"])

    fig = px.area(
        plans_long, x="SY", y="Pct", color="Plan",
        groupnorm=None,
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share of seniors")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Earnings of HS graduates by industry (district-level)
# ---------------------------------------------------------------------------

st.header("Earnings of Lynn HS Graduates — Industry View")
st.caption(
    "DESE's *Average Earnings of HS Graduates by Industry* dataset follows "
    "every Lynn-district HS graduate's W-2 earnings by NAICS industry. "
    "Reported at the district level, so this includes graduates of LEHS, "
    "LCHS, Lynn Tech, and the alternative HS combined."
)

earnings = load_dataset("earnings_by_industry")
if not earnings.empty:
    e_lynn = earnings[earnings["DIST_CODE"] == "01630000"].copy()
    e_lynn["AVG_EARNINGS"] = pd.to_numeric(e_lynn["AVG_EARNINGS"], errors="coerce")
    e_lynn["EMP_CNT"] = pd.to_numeric(e_lynn["EMP_CNT"], errors="coerce")
    e_lynn["GRAD_CNT"] = pd.to_numeric(e_lynn["GRAD_CNT"], errors="coerce")

    # "All Students" row is total-across-industries; pull it out for headline
    headline = e_lynn[
        (e_lynn["NAICS_DESC"] == "All Students")
        & (e_lynn["HS_GRAD_YEAR"] == e_lynn["EARNINGS_YEAR"])
    ].dropna(subset=["AVG_EARNINGS"]).sort_values("HS_GRAD_YEAR")

    if not headline.empty:
        latest = headline.iloc[-1]
        prior = headline.iloc[-2] if len(headline) > 1 else None
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric(
                f"Avg earnings in year of HS graduation "
                f"({int(latest['HS_GRAD_YEAR'])} cohort)",
                f"${latest['AVG_EARNINGS']:,.0f}",
                (f"${latest['AVG_EARNINGS']-prior['AVG_EARNINGS']:+,.0f} "
                 f"vs {int(prior['HS_GRAD_YEAR'])}") if prior is not None else "",
                delta_color="off",
            )
            st.caption(
                f"Earned by **{int(latest['EMP_CNT']):,}** of "
                f"{int(latest['GRAD_CNT']):,} graduates with reported wages."
            )
        with c2:
            fig = px.line(
                headline, x="HS_GRAD_YEAR", y="AVG_EARNINGS", markers=True,
            )
            fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat="$,.0f",
                yaxis_title="Average wages in grad year",
                xaxis_title="High-school graduation cohort",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Industry breakdown — latest cohort
    if not e_lynn.empty:
        latest_year = e_lynn["HS_GRAD_YEAR"].max()
        industries = e_lynn[
            (e_lynn["HS_GRAD_YEAR"] == latest_year)
            & (e_lynn["EARNINGS_YEAR"] == latest_year)
            & (e_lynn["NAICS_DESC"] != "All Students")
            & (e_lynn["EMP_CNT"].notna())
        ].sort_values("EMP_CNT", ascending=True)
        if not industries.empty:
            st.subheader(
                f"Where the cohort works — {int(latest_year)} graduates "
                f"with reported wages in their grad year"
            )
            st.caption(
                "Industries with too few graduates (<6) are suppressed by "
                "DESE. The chart below shows only those above that threshold."
            )
            industries["earnings_label"] = industries["AVG_EARNINGS"].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
            )
            fig = px.bar(
                industries, y="NAICS_DESC", x="EMP_CNT", orientation="h",
                color="AVG_EARNINGS", color_continuous_scale="Greens",
                text=industries["EMP_CNT"].astype(int).astype(str) + " grads",
                hover_data={"AVG_EARNINGS": ":$,.0f", "GRAD_CNT": True},
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_title="Number of graduates employed",
                yaxis_title="",
                coloraxis_colorbar=dict(title="Avg $/yr"),
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Earnings data not yet loaded.")

st.divider()

# ---------------------------------------------------------------------------
# Early warning chain
# ---------------------------------------------------------------------------

st.header("Early Warning Chain")
st.caption(
    "These four indicators form a cascade: a student who chronically misses 9th "
    "grade is unlikely to be promoted, less likely to graduate on time, and far "
    "less likely to enroll in college. Tracking them together highlights where "
    "interventions have leverage."
)

chain_indicators = [
    ("Chronically absent rate (% of students absent 10% or more each year)", "Chronic Absence"),
    ("9th to 10th grade promotion rate (first-time 9th graders only)", "9-10 Promotion"),
    ("4-year cohort graduation rate", "4-yr Graduation"),
    ("Students enrolled in postsecondary education in the immediate fall after high school graduation",
     "Immediate College"),
]

chain_df = pd.concat([
    get_dart_indicator(LEHS_SCHOOL_CODE, ind).assign(Stage=label)
    for ind, label in chain_indicators
])

if not chain_df.empty:
    fig = px.line(
        chain_df.sort_values("SY"), x="SY", y="VALUE", color="Stage", markers=True,
        color_discrete_map={
            "Chronic Absence":      "#D32F2F",
            "9-10 Promotion":       "#F57C00",
            "4-yr Graduation":      LEHS_NAVY,
            "Immediate College":    "#388E3C",
        },
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Rate (%)",
                       yaxis_ticksuffix="%", yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'DART (Success After HS)': dart,
        'Graduation rates': grad,
        'Plans of graduates': plans,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

