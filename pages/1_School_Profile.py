"""Section 1 — School Profile: demographics, enrollment trends, headline metrics."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.charts import DEFAULT_LAYOUT, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label, yoy_delta

st.set_page_config(page_title="School Profile | LEHS", page_icon="📊", layout="wide")

st.title("Lynn English High School — Profile")
st.markdown(
    "Demographics, enrollment trends, and headline metrics. Data goes back to "
    "the 1992-93 school year and updates annually as DESE releases new figures."
)

enrollment = load_dataset("enrollment_demographics")
if enrollment.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

lehs = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY").copy()
if lehs.empty:
    st.error(f"No rows for LEHS school code {LEHS_SCHOOL_CODE}")
    st.stop()

current = lehs.iloc[-1]
prior = lehs.iloc[-2] if len(lehs) > 1 else None

# ---------------------------------------------------------------------------
# Hero metrics
# ---------------------------------------------------------------------------

st.subheader(f"At a Glance — School Year {sy_label(current['SY'])}")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric(
        "Total Enrollment",
        f"{int(current['TOTAL_CNT']):,}",
        yoy_delta(current["TOTAL_CNT"], prior["TOTAL_CNT"], "students") if prior is not None else "",
    )
with c2:
    st.metric(
        "% English Learners",
        f"{current['EL_PCT']:.0%}",
        yoy_delta(current["EL_PCT"] * 100, prior["EL_PCT"] * 100, "pts") if prior is not None else "",
    )
with c3:
    st.metric(
        "% Low Income",
        f"{current['LI_PCT']:.0%}",
        yoy_delta(current["LI_PCT"] * 100, prior["LI_PCT"] * 100, "pts") if prior is not None else "",
    )
with c4:
    st.metric(
        "% Students w/ Disabilities",
        f"{current['SWD_PCT']:.0%}",
        yoy_delta(current["SWD_PCT"] * 100, prior["SWD_PCT"] * 100, "pts") if prior is not None else "",
    )
with c5:
    st.metric(
        "% High Needs",
        f"{current['HN_PCT']:.0%}",
        yoy_delta(current["HN_PCT"] * 100, prior["HN_PCT"] * 100, "pts") if prior is not None else "",
    )

st.divider()

# ---------------------------------------------------------------------------
# Total enrollment trend
# ---------------------------------------------------------------------------

st.subheader("Total Enrollment Over Time")

fig = px.line(
    lehs,
    x="SY",
    y="TOTAL_CNT",
    markers=True,
    title="Lynn English High School — total enrollment by school year",
)
fig.update_traces(line=dict(color=LEHS_NAVY, width=3), marker=dict(size=7))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year")
st.plotly_chart(fig, width="stretch")

peak_year = lehs.loc[lehs["TOTAL_CNT"].idxmax()]
trough_year = lehs.loc[lehs["TOTAL_CNT"].idxmin()]
st.caption(
    f"Enrollment peaked at {int(peak_year['TOTAL_CNT']):,} students in "
    f"SY {int(peak_year['SY'])} and reached its lowest at {int(trough_year['TOTAL_CNT']):,} "
    f"in SY {int(trough_year['SY'])}."
)

st.divider()

# ---------------------------------------------------------------------------
# Demographics — current year donut + race/ethnicity trend
# ---------------------------------------------------------------------------

col_a, col_b = st.columns([1, 2])

with col_a:
    st.subheader("Race / Ethnicity")
    race_data = pd.DataFrame({
        "Group": [
            "Hispanic/Latino", "African American/Black", "Asian", "White",
            "Multi-Race", "Native American", "Native Hawaiian/PI",
        ],
        "Pct": [
            current["HL_PCT"], current["BAA_PCT"], current["AS_PCT"], current["WH_PCT"],
            current["MNHL_PCT"], current["AIAN_PCT"], current["NHPI_PCT"],
        ],
    })
    race_data = race_data[race_data["Pct"] > 0]
    fig = px.pie(
        race_data, names="Group", values="Pct", hole=0.5,
        color="Group",
        color_discrete_map={
            "Hispanic/Latino":         SUBGROUP_PALETTE["Hispanic/Latino"],
            "African American/Black":  SUBGROUP_PALETTE["African American/Black"],
            "Asian":                   SUBGROUP_PALETTE["Asian"],
            "White":                   SUBGROUP_PALETTE["White"],
            "Multi-Race":              SUBGROUP_PALETTE["Multi-Race, Non-Hispanic/Latino"],
        },
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(**DEFAULT_LAYOUT, showlegend=False)
    st.plotly_chart(fig, width="stretch")

with col_b:
    st.subheader("Race / Ethnicity Composition Over Time")
    race_long = lehs.melt(
        id_vars=["SY"],
        value_vars=["HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT", "MNHL_PCT"],
        var_name="Group",
        value_name="Pct",
    )
    label_map = {
        "HL_PCT": "Hispanic/Latino",
        "BAA_PCT": "African American/Black",
        "AS_PCT": "Asian",
        "WH_PCT": "White",
        "MNHL_PCT": "Multi-Race",
    }
    race_long["Group"] = race_long["Group"].map(label_map)
    race_long = race_long.dropna(subset=["Pct"])
    fig = px.area(
        race_long, x="SY", y="Pct", color="Group",
        color_discrete_map={
            "Hispanic/Latino":        SUBGROUP_PALETTE["Hispanic/Latino"],
            "African American/Black": SUBGROUP_PALETTE["African American/Black"],
            "Asian":                  SUBGROUP_PALETTE["Asian"],
            "White":                  SUBGROUP_PALETTE["White"],
            "Multi-Race":             SUBGROUP_PALETTE["Multi-Race, Non-Hispanic/Latino"],
        },
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share")
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Selected populations trend (ELL, Low Income, SPED, High Needs)
# ---------------------------------------------------------------------------

st.subheader("Selected Populations Over Time")

pop_long = lehs.melt(
    id_vars=["SY"],
    value_vars=["EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT", "FLNE_PCT"],
    var_name="Group",
    value_name="Pct",
)
pop_labels = {
    "EL_PCT":  "English Learner",
    "LI_PCT":  "Low Income",
    "SWD_PCT": "Students w/ Disabilities",
    "HN_PCT":  "High Needs",
    "FLNE_PCT":"First Lang Not English",
}
pop_long["Group"] = pop_long["Group"].map(pop_labels)
pop_long = pop_long.dropna(subset=["Pct"])

fig = px.line(
    pop_long, x="SY", y="Pct", color="Group", markers=True,
    color_discrete_map={
        "English Learner":          SUBGROUP_PALETTE["English Learner"],
        "Low Income":               SUBGROUP_PALETTE["Low Income"],
        "Students w/ Disabilities": SUBGROUP_PALETTE["Students w/ Disabilities"],
        "High Needs":               SUBGROUP_PALETTE["High Needs"],
        "First Lang Not English":   "#0277BD",
    },
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share of Students")
st.plotly_chart(fig, width="stretch")

st.caption(
    "Lynn English serves a high-needs, English-Learner-rich student body. The "
    "share of students classified as Low Income, ELL, and First Language Not "
    "English has grown substantially since the early 2000s."
)

st.divider()

# ---------------------------------------------------------------------------
# Grade-level enrollment
# ---------------------------------------------------------------------------

st.subheader(f"Grade-Level Enrollment ({sy_label(current['SY'])})")

grade_data = pd.DataFrame({
    "Grade": ["9", "10", "11", "12"],
    "Students": [current["G9_CNT"], current["G10_CNT"], current["G11_CNT"], current["G12_CNT"]],
})

fig = go.Figure(go.Bar(
    x=grade_data["Grade"],
    y=grade_data["Students"],
    text=grade_data["Students"].astype(int),
    textposition="outside",
    marker_color=LEHS_NAVY,
))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="Grade")
st.plotly_chart(fig, width="stretch")

if current["G9_CNT"] < current["G12_CNT"]:
    drop = (current["G12_CNT"] - current["G9_CNT"]) / current["G12_CNT"]
    st.caption(
        f"Grade 9 enrollment is {drop:.0%} smaller than grade 12 — could reflect "
        f"shrinking incoming cohorts or attrition between grades. See the "
        f"Success After HS page for 9-to-10 promotion rate analysis."
    )
