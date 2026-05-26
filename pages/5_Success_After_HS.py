"""Section 5 — Success After High School.

The whole pipeline: 9th-grade cohort entry → graduation → postsecondary
enrollment → persistence → degree completion → earnings. Folds in the
former Cohort Tracking content so visitors see one connected story.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import get_dart_indicator, load_dataset

st.set_page_config(page_title="Success After HS | LEHS", page_icon="🏆", layout="wide")
sidebar_attribution()

st.title("Success After High School")
st.markdown(
    "**The headline question every parent, teacher, and school committee "
    "member asks: of every 100 9th-graders who walk into LEHS, how many "
    "graduate, how many enroll in college, and how many are still there "
    "a year later?** This page follows the full pipeline from 9th-grade "
    "entry through degree completion and into the workforce."
)

dart = load_dataset("dart_success_after_hs")
grad = load_dataset("graduation_rates")
prog = load_dataset("student_progression_hs_to_postsec")
if dart.empty or grad.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Cohort funnel — the hero. Of every 100 9th-graders, how many reach each
# stage? This used to be a separate "Cohort Tracking" page; folded in here
# because it's the same Success story.
# ---------------------------------------------------------------------------

YEAR2_INDICATOR = "Student progression from high school through second year of postsecondary education"
DEGREE_INDICATOR = "Student progression from high school through postsecondary degree completion"

cohort_n = grad_n = enr_n = pers_n = None
latest_cohort = None

if not prog.empty:
    prog["DIST_CODE"] = prog["DIST_CODE"].astype(str).str.zfill(8)
    prog["ORG_CODE"] = prog["ORG_CODE"].astype(str).str.zfill(8)
    lehs_prog = prog[prog["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    lehs_y2_all = lehs_prog[
        (lehs_prog["INDICATOR"] == YEAR2_INDICATOR) & (lehs_prog["STU_GRP"] == "All Students")
    ].sort_values("COHORTYR")

    if not lehs_y2_all.empty:
        latest = lehs_y2_all.iloc[-1]
        latest_cohort = int(latest["COHORTYR"])
        cohort_n = int(latest["COHORT_CNT"])
        grad_n = int(latest["GRAD_CNT"]) if pd.notna(latest["GRAD_CNT"]) else 0
        enr_n = int(latest["IMMEDIATEENR_CNT"]) if pd.notna(latest["IMMEDIATEENR_CNT"]) else 0
        pers_n = int(latest["PERSIST_CNT"]) if pd.notna(latest["PERSIST_CNT"]) else 0

if cohort_n:
    st.header(f"The Cohort Funnel — {latest_cohort - 4}–{latest_cohort} Class")
    st.caption(
        f"All Students who entered LEHS as 9th-graders before the SY "
        f"{latest_cohort - 1}-{str(latest_cohort)[-2:]} graduation, tracked "
        f"through their second year of college."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Entered 9th grade", f"{cohort_n:,}", "baseline cohort")
    with c2:
        st.metric("Graduated high school", f"{grad_n:,}",
                  f"{grad_n / cohort_n:.0%} of cohort", delta_color="off")
    with c3:
        st.metric("Enrolled in college", f"{enr_n:,}",
                  f"{enr_n / cohort_n:.0%} of cohort", delta_color="off")
    with c4:
        st.metric("Still enrolled year 2", f"{pers_n:,}",
                  f"{pers_n / cohort_n:.0%} of cohort", delta_color="off")

    stages = ["Entered 9th grade", "Graduated", "Enrolled in college", "Persisted to year 2"]
    counts = [cohort_n, grad_n, enr_n, pers_n]
    pcts = [c / cohort_n for c in counts]
    labels = [f"{c:,}<br>({p:.0%})" for c, p in zip(counts, pcts)]

    fig = go.Figure(
        go.Funnel(
            y=stages, x=counts, text=labels, textposition="inside",
            textfont=dict(color="white", size=14),
            marker=dict(color=[LEHS_NAVY, "#1E3A6F", "#2F559A", LEHS_GOLD]),
            connector=dict(line=dict(color="#B0BEC5", width=1)),
        )
    )
    fig.update_layout(**DEFAULT_LAYOUT, height=360)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"**The headline number:** of every 100 LEHS 9th-graders, "
        f"~{round(grad_n / cohort_n * 100)} graduate, "
        f"~{round(enr_n / cohort_n * 100)} enroll in college, and only "
        f"**~{round(pers_n / cohort_n * 100)} are still in college a year later**."
    )

    st.divider()

# ---------------------------------------------------------------------------
# Pipeline metrics — headline DART indicators
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

# ---------------------------------------------------------------------------
# Where the pipeline leaks — subgroup cohort progression (from cohort tracking)
# ---------------------------------------------------------------------------

if not prog.empty and latest_cohort is not None:
    st.header(f"Where the Pipeline Leaks — by Subgroup ({latest_cohort - 4}–{latest_cohort} Cohort)")
    st.caption(
        "The headline numbers above hide within-school disparities. Same cohort, "
        "broken out by subgroup. Bar length = share of that subgroup's 9th-grade "
        "entrants who reach each stage. Empty bars are DESE-suppressed (cell <10 students)."
    )

    sub_groups = lehs_prog[
        (lehs_prog["INDICATOR"] == YEAR2_INDICATOR)
        & (lehs_prog["COHORTYR"] == latest_cohort)
        & (lehs_prog["STU_GRP"] != "All Students")
    ].copy()
    sub_groups = sub_groups.assign(
        grad_pct=lambda d: d["GRAD_CNT"] / d["COHORT_CNT"],
        enr_pct=lambda d: d["IMMEDIATEENR_CNT"] / d["COHORT_CNT"],
        pers_pct=lambda d: d["PERSIST_CNT"] / d["COHORT_CNT"],
    )
    sub_groups = sub_groups[sub_groups["COHORT_CNT"] >= 10].copy()
    sub_groups = sub_groups.sort_values("pers_pct", ascending=True, na_position="first")

    if not sub_groups.empty:
        stage_labels = {
            "grad_pct": "Graduated",
            "enr_pct": "Enrolled in college",
            "pers_pct": "Persisted to year 2",
        }
        stage_colors = {
            "Graduated": "#90A4AE",
            "Enrolled in college": "#2F559A",
            "Persisted to year 2": LEHS_GOLD,
        }
        melted = sub_groups.melt(
            id_vars=["STU_GRP", "COHORT_CNT"],
            value_vars=["grad_pct", "enr_pct", "pers_pct"],
            var_name="stage", value_name="pct",
        )
        melted["stage"] = melted["stage"].map(stage_labels)

        fig = px.bar(
            melted, x="pct", y="STU_GRP", color="stage", barmode="group",
            orientation="h", color_discrete_map=stage_colors,
            category_orders={"stage": ["Graduated", "Enrolled in college", "Persisted to year 2"]},
            text=melted["pct"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else ""),
        )
        fig.update_traces(textposition="outside", textfont=dict(size=10), cliponaxis=False)
        fig.update_layout(
            **DEFAULT_LAYOUT,
            height=max(360, 28 * len(sub_groups)),
            xaxis_tickformat=".0%",
            xaxis_range=[0, 1.1],
            xaxis_title="Share of 9th-grade entrants reaching each stage",
            yaxis_title="",
            legend_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Surface the widest gap
        if not sub_groups["pers_pct"].dropna().empty:
            top_row = sub_groups.iloc[-1]
            bot_row = sub_groups.iloc[0]
            top_pct = top_row["pers_pct"]
            bot_pct = bot_row["pers_pct"]
            if pd.notna(top_pct) and pd.notna(bot_pct):
                st.markdown(
                    f"**The widest gap:** {top_row['STU_GRP']} students persist to "
                    f"college year 2 at **{top_pct:.0%}**, while "
                    f"{bot_row['STU_GRP']} students persist at **{bot_pct:.0%}** "
                    f"— a **{(top_pct - bot_pct) * 100:.0f}-point** spread."
                )

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
# Multi-cohort trend (from cohort tracking) — long view of the pipeline
# ---------------------------------------------------------------------------

if not prog.empty and 'lehs_y2_all' in dir() and not lehs_y2_all.empty:
    st.header("Pipeline Trend — Multiple 9th-grade Cohorts")
    st.caption(
        "Each line is a stage of the pipeline as it has moved over time. "
        "Cohorts graduating 2020–2024 were disrupted as 8th–10th graders; "
        "expect noisier patterns for those years."
    )

    trend_all = lehs_prog[
        (lehs_prog["INDICATOR"] == YEAR2_INDICATOR) & (lehs_prog["STU_GRP"] == "All Students")
    ].sort_values("COHORTYR").copy()
    trend_all["grad_pct"] = trend_all["GRAD_CNT"] / trend_all["COHORT_CNT"]
    trend_all["enr_pct"] = trend_all["IMMEDIATEENR_CNT"] / trend_all["COHORT_CNT"]
    trend_all["pers_pct"] = trend_all["PERSIST_CNT"] / trend_all["COHORT_CNT"]

    trend_long = trend_all.melt(
        id_vars=["COHORTYR"],
        value_vars=["grad_pct", "enr_pct", "pers_pct"],
        var_name="stage", value_name="pct",
    ).dropna(subset=["pct"])
    trend_long["stage"] = trend_long["stage"].map({
        "grad_pct": "Graduated",
        "enr_pct": "Enrolled in college",
        "pers_pct": "Persisted to year 2",
    })

    fig = px.line(
        trend_long, x="COHORTYR", y="pct", color="stage", markers=True,
        color_discrete_map={
            "Graduated":            "#90A4AE",
            "Enrolled in college":  "#2F559A",
            "Persisted to year 2":  LEHS_GOLD,
        },
        category_orders={"stage": ["Graduated", "Enrolled in college", "Persisted to year 2"]},
    )
    fig.update_layout(
        **DEFAULT_LAYOUT,
        yaxis_tickformat=".0%",
        yaxis_title="Share of 9th-grade cohort",
        xaxis_title="Graduation cohort year",
        legend_title="",
    )
    if not trend_long.empty:
        fig.update_yaxes(range=[0, max(trend_long["pct"].max() * 1.1, 1.0)])
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------------------------
    # Six-year degree completion
    # ---------------------------------------------------------------------------

    st.subheader("Degree Completion — 6-Year View")
    st.caption(
        "Following cohorts six years past HS graduation: how many actually "
        "completed a 2-yr or 4-yr degree?"
    )

    lehs_deg = lehs_prog[
        (lehs_prog["INDICATOR"] == DEGREE_INDICATOR) & (lehs_prog["STU_GRP"] == "All Students")
    ].sort_values("COHORTYR")

    if not lehs_deg.empty:
        latest_deg = lehs_deg.iloc[-1]
        deg_year = int(latest_deg["COHORTYR"])
        deg_pct = latest_deg["OBTAINDEGREE_PCT"]
        if pd.notna(deg_pct):
            st.metric(
                f"Obtained a postsecondary degree ({deg_year - 4}–{deg_year} cohort)",
                f"{deg_pct:.0%}",
                help="Share of the 9th-grade cohort that completed a 2-yr or 4-yr degree within ~6 years of HS graduation.",
            )

        deg_trend = lehs_deg.dropna(subset=["OBTAINDEGREE_PCT"]).copy()
        if len(deg_trend) >= 2:
            fig = px.line(deg_trend, x="COHORTYR", y="OBTAINDEGREE_PCT", markers=True)
            fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat=".0%",
                yaxis_title="Share of cohort obtaining a degree",
                xaxis_title="Cohort year",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("6-year degree-completion data not available for LEHS yet.")

    st.divider()

# ---------------------------------------------------------------------------
# Earnings of HS graduates by industry (district-level)
# ---------------------------------------------------------------------------

st.header("Earnings of Lynn HS Graduates — Industry View")
st.caption(
    "DESE's *Average Earnings of HS Graduates by Industry* dataset follows "
    "every Lynn-district HS graduate's W-2 earnings by NAICS industry. "
    "Reported at the district level, so this includes graduates of LEHS, "
    "Classical, Tech, and the alternative HS combined."
)

earnings = load_dataset("earnings_by_industry")
if not earnings.empty:
    e_lynn = earnings[earnings["DIST_CODE"] == "01630000"].copy()
    e_lynn["AVG_EARNINGS"] = pd.to_numeric(e_lynn["AVG_EARNINGS"], errors="coerce")
    e_lynn["EMP_CNT"] = pd.to_numeric(e_lynn["EMP_CNT"], errors="coerce")
    e_lynn["GRAD_CNT"] = pd.to_numeric(e_lynn["GRAD_CNT"], errors="coerce")

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
            fig = px.line(headline, x="HS_GRAD_YEAR", y="AVG_EARNINGS", markers=True)
            fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat="$,.0f",
                yaxis_title="Average wages in grad year",
                xaxis_title="High-school graduation cohort",
            )
            st.plotly_chart(fig, use_container_width=True)

    if not e_lynn.empty:
        latest_year_e = e_lynn["HS_GRAD_YEAR"].max()
        industries = e_lynn[
            (e_lynn["HS_GRAD_YEAR"] == latest_year_e)
            & (e_lynn["EARNINGS_YEAR"] == latest_year_e)
            & (e_lynn["NAICS_DESC"] != "All Students")
            & (e_lynn["EMP_CNT"].notna())
        ].sort_values("EMP_CNT", ascending=True)
        if not industries.empty:
            st.subheader(
                f"Where the cohort works — {int(latest_year_e)} graduates "
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
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_title="Number of graduates employed",
                xaxis_range=[0, industries["EMP_CNT"].max() * 1.18],
                yaxis_title="",
                coloraxis_colorbar=dict(title="Avg $/yr"),
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Earnings data not yet loaded.")

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

with st.expander("How to read this page · methodology"):
    st.markdown(
        """
- **Cohort** means the group of students who first entered 9th grade together,
  not the graduating class. A 2023 cohort started 9th grade around 2019.
- **Immediate enrollment** is in college the fall immediately after HS graduation.
- **Persisted to year 2** = still enrolled in college one year after immediate
  enrollment. Strongest single predictor of degree completion.
- **Stage percentages** in the cohort funnel are always relative to the original
  9th-grade cohort, not to the previous stage.
- **DESE suppression**: cells under 10 students are blanked.
- **Source**: MA DESE Education-to-Career Hub — DART (Success After HS),
  Graduation Rates, Student Progression HS→Postsec, Plans of Graduates,
  Earnings by Industry.
"""
    )

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'DART (Success After HS)': dart,
        'Graduation rates': grad,
        'Plans of graduates': plans,
        'Cohort progression (9th-grade → degree)': prog,
    })
except NameError:
    pass
