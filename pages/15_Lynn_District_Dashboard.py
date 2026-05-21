"""Section 19 — Lynn District Dashboard: LPS as a whole, not just LEHS."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import GATEWAY_CITIES, LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(
    page_title="Lynn District Dashboard | LEHS", page_icon="🏛️", layout="wide"
)
sidebar_attribution()

st.title("Lynn Public Schools — District Dashboard")
st.markdown(
    "A district-wide view of Lynn Public Schools (LPS) — the system that includes "
    "LEHS, Classical, Tech, and all elementary and middle schools. "
    "Shows district-level trends across enrollment, finance, MCAS, and graduation."
)

enrollment = load_dataset("enrollment_demographics")
grad = load_dataset("graduation_rates")
mcas = load_dataset("mcas_achievement")
attendance = load_dataset("student_attendance")
dist_exp = load_dataset("district_expenditures")

if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# Filter to Lynn district-level rows
district = enrollment[
    (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE) & (enrollment["ORG_TYPE"] == "District")
].sort_values("SY")

if district.empty:
    st.warning("No Lynn district-level enrollment rows found.")
    st.stop()

current = district.iloc[-1]
prior = district.iloc[-2] if len(district) > 1 else None

# ---------------------------------------------------------------------------
# Headline
# ---------------------------------------------------------------------------

st.header(f"Lynn Public Schools — School Year {sy_label(current['SY'])}")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Total Enrollment", f"{int(current['TOTAL_CNT']):,}")
with c2:
    st.metric("% English Learners", f"{current['EL_PCT']:.0%}")
with c3:
    st.metric("% Low Income", f"{current['LI_PCT']:.0%}")
with c4:
    st.metric("% High Needs", f"{current['HN_PCT']:.0%}")
with c5:
    st.metric("% Hispanic/Latino", f"{current['HL_PCT']:.0%}")

st.divider()

# ---------------------------------------------------------------------------
# District enrollment + demographics trend
# ---------------------------------------------------------------------------

st.header("District Enrollment Over Time")
fig = px.line(district, x="SY", y="TOTAL_CNT", markers=True)
fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year")
st.plotly_chart(fig, use_container_width=True)

st.header("Selected Populations Trend (District-wide)")
long = district.melt(
    id_vars="SY",
    value_vars=["EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT", "FLNE_PCT"],
    var_name="Group", value_name="Pct",
)
label_map = {
    "EL_PCT": "English Learner", "LI_PCT": "Low Income",
    "SWD_PCT": "Students w/ Disabilities", "HN_PCT": "High Needs",
    "FLNE_PCT": "First Lang Not English",
}
long["Group"] = long["Group"].map(label_map)
long = long.dropna(subset=["Pct"])

fig = px.line(
    long, x="SY", y="Pct", color="Group", markers=True,
    color_discrete_map={
        "English Learner":          SUBGROUP_PALETTE["English Learner"],
        "Low Income":               SUBGROUP_PALETTE["Low Income"],
        "Students w/ Disabilities": SUBGROUP_PALETTE["Students w/ Disabilities"],
        "High Needs":               SUBGROUP_PALETTE["High Needs"],
        "First Lang Not English":   "#0277BD",
    },
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# District MCAS performance
# ---------------------------------------------------------------------------

st.header("Lynn District MCAS Performance")

district_mcas = mcas[
    (mcas["DIST_CODE"] == LYNN_DISTRICT_CODE)
    & (mcas["ORG_TYPE"] == "District")
    & (mcas["STU_GRP"] == "All Students")
].copy()

if not district_mcas.empty:
    # Show grade 10 trends by subject
    g10 = district_mcas[district_mcas["TEST_GRADE"] == "10"].sort_values("SY")
    if not g10.empty:
        st.subheader("Grade 10 — All Students, by Subject")
        fig = px.line(
            g10, x="SY", y="M_PLUS_E_PCT", color="SUBJECT_CODE",
            markers=True,
            color_discrete_map={"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"},
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                           yaxis_title="% Meeting + Exceeding")
        st.plotly_chart(fig, use_container_width=True)

    # Show grades 3-8 trends
    elem_mcas = district_mcas[district_mcas["TEST_GRADE"].astype(str).isin(["03", "04", "05", "06", "07", "08"])].copy()
    if not elem_mcas.empty:
        st.subheader("Grades 3-8 — Average % M+E (across grades)")
        avg = elem_mcas.groupby(["SY", "SUBJECT_CODE"])["M_PLUS_E_PCT"].mean().reset_index()
        fig = px.line(
            avg, x="SY", y="M_PLUS_E_PCT", color="SUBJECT_CODE",
            markers=True,
            color_discrete_map={"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"},
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                           yaxis_title="Avg % M+E across grades")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# District graduation
# ---------------------------------------------------------------------------

st.header("Lynn District Graduation Rate")

district_grad = grad[
    (grad["DIST_CODE"] == LYNN_DISTRICT_CODE)
    & (grad["ORG_TYPE"] == "District")
    & (grad["STU_GRP"] == "All Students")
    & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
].sort_values("SY")

if not district_grad.empty:
    fig = px.line(district_grad, x="SY", y="GRAD_PCT", markers=True)
    fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="4-yr Graduation Rate",
                       xaxis_title="Cohort Year")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# District attendance / chronic absence
# ---------------------------------------------------------------------------

st.header("Lynn District Attendance")

district_att = attendance[
    (attendance["DIST_CODE"] == LYNN_DISTRICT_CODE)
    & (attendance["ORG_TYPE"] == "District")
    & (attendance["STU_GRP"] == "All Students")
    & (attendance["ATTEND_PERIOD"] == "FY")
].sort_values("SY")

if not district_att.empty:
    district_att["PCT_CHRON_ABS_10"] = pd.to_numeric(district_att["PCT_CHRON_ABS_10"], errors="coerce")
    fig = px.line(district_att, x="SY", y="PCT_CHRON_ABS_10", markers=True)
    fig.update_traces(line=dict(color="#F57C00", width=3))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="% Chronically Absent (10%+ missed)")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# District finance
# ---------------------------------------------------------------------------

st.header("Lynn District Finance")

if not dist_exp.empty:
    d = dist_exp[dist_exp["DIST_CODE"] == LYNN_DISTRICT_CODE].copy()
    d["IND_VALUE"] = pd.to_numeric(d["IND_VALUE"], errors="coerce")

    # Per-pupil expenditure trend (note: the "Total Expenditures" sub-category in
    # this dataset is the per-pupil total, not the district-wide budget)
    pp = d[
        (d["IND_CAT"].astype(str).str.contains("Per Pupil", case=False, na=False))
        & (d["IND_SUBCAT"].astype(str).str.contains("Total Expenditures", case=False, na=False))
    ].sort_values("SY")
    if not pp.empty:
        latest_t = pp.iloc[-1]
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric(f"Per-pupil expenditure (FY {int(latest_t['SY'])})",
                      f"${latest_t['IND_VALUE']:,.0f}")
        fig = px.line(pp, x="SY", y="IND_VALUE", markers=True)
        fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="$,.0f",
                           yaxis_title="$ per pupil", xaxis_title="Fiscal Year")
        with c2:
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Lynn vs. Gateway median vs. State median — small multiples
# ---------------------------------------------------------------------------

st.header("Lynn vs. Gateway Cities median vs. State median")
st.caption(
    "Each panel: Lynn (navy line) compared to the median of the 26 MA Gateway "
    "Cities (gold) and the state-wide median (grey). Latest 8 years."
)

@st.cache_data(show_spinner=False)
def _gateway_codes() -> set[str]:
    """Return DIST_CODE set for the 26 Gateway-city districts.

    Resolves from enrollment_demographics where DIST_NAME matches a Gateway
    city name. Falls back to just LYNN if matching fails.
    """
    if enrollment.empty:
        return {LYNN_DISTRICT_CODE}
    by_name = enrollment[
        enrollment["DIST_NAME"].isin([f"{c} Public Schools" for c in GATEWAY_CITIES] + GATEWAY_CITIES)
        & (enrollment["ORG_TYPE"] == "District")
    ]
    return set(by_name["DIST_CODE"].dropna().unique())


def _small_multiple(df: pd.DataFrame, value_col: str, title: str, ytick: str = ".0%") -> go.Figure:
    """Three-line chart: Lynn, Gateway median, State median."""
    if df.empty:
        return None
    df = df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=[value_col, "SY"])
    if df.empty:
        return None

    gw_codes = _gateway_codes()
    lynn_line = df[df["DIST_CODE"] == LYNN_DISTRICT_CODE].groupby("SY")[value_col].mean().reset_index()
    gw_line = df[df["DIST_CODE"].isin(gw_codes)].groupby("SY")[value_col].median().reset_index()
    state_line = df.groupby("SY")[value_col].median().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=state_line["SY"], y=state_line[value_col],
                              mode="lines", name="State median",
                              line=dict(color="#9E9E9E", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=gw_line["SY"], y=gw_line[value_col],
                              mode="lines+markers", name="Gateway median",
                              line=dict(color=LEHS_GOLD, width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=lynn_line["SY"], y=lynn_line[value_col],
                              mode="lines+markers", name="Lynn",
                              line=dict(color=LEHS_NAVY, width=3)))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=ytick,
                      title=title, yaxis_title="", xaxis_title="SY")
    return fig


col_a, col_b = st.columns(2)

# Grad 4yr — districts
if not grad.empty:
    g4 = grad[(grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
              & (grad["ORG_TYPE"] == "District")
              & (grad["STU_GRP"] == "All Students")][["SY", "DIST_CODE", "GRAD_PCT"]]
    g4["GRAD_PCT"] = pd.to_numeric(g4["GRAD_PCT"], errors="coerce")
    if g4["GRAD_PCT"].max() and g4["GRAD_PCT"].max() > 1.5:  # already in 0-100
        g4["GRAD_PCT"] = g4["GRAD_PCT"] / 100.0
    fig = _small_multiple(g4, "GRAD_PCT", "4-yr graduation rate")
    if fig:
        with col_a:
            st.plotly_chart(fig, use_container_width=True)

# Chronic absenteeism — districts
if not attendance.empty:
    a = attendance[(attendance["ORG_TYPE"] == "District")
                   & (attendance["STU_GRP"] == "All Students")
                   & (attendance["ATTEND_PERIOD"] == "FY")][["SY", "DIST_CODE", "PCT_CHRON_ABS_10"]]
    fig = _small_multiple(a, "PCT_CHRON_ABS_10", "Chronic absenteeism")
    if fig:
        with col_b:
            st.plotly_chart(fig, use_container_width=True)

# MCAS G10 ELA — districts
if not mcas.empty:
    m_g10 = mcas[(mcas["TEST_GRADE"].astype(str) == "10")
                 & (mcas["SUBJECT_CODE"] == "ELA")
                 & (mcas["STU_GRP"] == "All Students")
                 & (mcas["ORG_TYPE"] == "District")
                 ][["SY", "DIST_CODE", "M_PLUS_E_PCT"]]
    m_g10["M_PLUS_E_PCT"] = pd.to_numeric(m_g10["M_PLUS_E_PCT"], errors="coerce")
    if m_g10["M_PLUS_E_PCT"].max() and m_g10["M_PLUS_E_PCT"].max() > 1.5:
        m_g10["M_PLUS_E_PCT"] = m_g10["M_PLUS_E_PCT"] / 100.0
    fig = _small_multiple(m_g10, "M_PLUS_E_PCT", "MCAS Grade 10 ELA — % M+E")
    if fig:
        with col_a:
            st.plotly_chart(fig, use_container_width=True)

# MCAS G10 Math
if not mcas.empty:
    m_g10m = mcas[(mcas["TEST_GRADE"].astype(str) == "10")
                  & (mcas["SUBJECT_CODE"] == "MATH")
                  & (mcas["STU_GRP"] == "All Students")
                  & (mcas["ORG_TYPE"] == "District")
                  ][["SY", "DIST_CODE", "M_PLUS_E_PCT"]]
    m_g10m["M_PLUS_E_PCT"] = pd.to_numeric(m_g10m["M_PLUS_E_PCT"], errors="coerce")
    if m_g10m["M_PLUS_E_PCT"].max() and m_g10m["M_PLUS_E_PCT"].max() > 1.5:
        m_g10m["M_PLUS_E_PCT"] = m_g10m["M_PLUS_E_PCT"] / 100.0
    fig = _small_multiple(m_g10m, "M_PLUS_E_PCT", "MCAS Grade 10 Math — % M+E")
    if fig:
        with col_b:
            st.plotly_chart(fig, use_container_width=True)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Enrollment & demographics': enrollment,
        'Graduation rates': grad,
        'MCAS achievement': mcas,
        'Student attendance': attendance,
        'District expenditures': dist_exp,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

