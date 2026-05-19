"""Section 1 — School Profile: demographics, enrollment trends, headline metrics."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label, yoy_delta

st.set_page_config(page_title="School Profile | LEHS", page_icon="📊", layout="wide")
sidebar_attribution()

st.title("Lynn English High School — Profile")
st.markdown(
    "Demographics, enrollment trends, and headline metrics for LEHS, going "
    "back to the 1992–93 school year."
)

enrollment = load_dataset("enrollment_demographics")
if enrollment.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

lehs = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY").copy()
district = enrollment[
    (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE) & (enrollment["ORG_TYPE"] == "District")
].sort_values("SY").copy()

if lehs.empty:
    st.error(f"No rows for LEHS school code {LEHS_SCHOOL_CODE}")
    st.stop()

current = lehs.iloc[-1]
prior = lehs.iloc[-2] if len(lehs) > 1 else None
oldest = lehs.iloc[0]
# A year that fully populates demographic columns
first_with_demos = lehs.dropna(subset=["HL_PCT"]).iloc[0] if not lehs.dropna(subset=["HL_PCT"]).empty else oldest

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
# Long-term transformation
# ---------------------------------------------------------------------------

st.subheader("How LEHS has changed since 1992")
st.caption(
    "The school today is not the school 30 years ago. These long-term deltas "
    "show how dramatically the student population has shifted in one generation."
)

c1, c2, c3, c4 = st.columns(4)


def long_term_metric(col, label: str, fmt: str = ".0%"):
    if col not in lehs.columns:
        return
    sub = lehs.dropna(subset=[col])
    if len(sub) < 2:
        return
    first = sub.iloc[0]
    last = sub.iloc[-1]
    diff_pts = (last[col] - first[col]) * 100
    direction = "+" if diff_pts >= 0 else ""
    val_now = f"{last[col]:{fmt}}" if isinstance(last[col], (int, float)) else "—"
    delta = f"{direction}{diff_pts:.0f} pts since SY {sy_label(first['SY'])}"
    return val_now, delta


with c1:
    res = long_term_metric("HL_PCT", "% Hispanic/Latino")
    if res:
        st.metric("% Hispanic/Latino", res[0], res[1])
with c2:
    res = long_term_metric("FLNE_PCT", "% First Lang Not English")
    if res:
        st.metric("% First Lang Not English", res[0], res[1])
with c3:
    res = long_term_metric("LI_PCT", "% Low Income")
    if res:
        st.metric("% Low Income", res[0], res[1])
with c4:
    res = long_term_metric("WH_PCT", "% White")
    if res:
        st.metric("% White", res[0], res[1])

st.divider()

# ---------------------------------------------------------------------------
# Total enrollment trend
# ---------------------------------------------------------------------------

st.subheader("Total Enrollment Over Time")

fig = px.line(
    lehs, x="SY", y="TOTAL_CNT", markers=True,
)
fig.update_traces(
    line=dict(color=LEHS_NAVY, width=3),
    marker=dict(size=8),
    text=lehs["TOTAL_CNT"].apply(lambda v: f"{int(v):,}" if pd.notna(v) else ""),
    textposition="top center",
    mode="lines+markers+text",
    textfont=dict(size=10, color=LEHS_NAVY),
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year",
                   title="Lynn English High School — total enrollment by school year")
st.plotly_chart(fig, width="stretch")

peak_year = lehs.loc[lehs["TOTAL_CNT"].idxmax()]
trough_year = lehs.loc[lehs["TOTAL_CNT"].idxmin()]
st.caption(
    f"Enrollment peaked at **{int(peak_year['TOTAL_CNT']):,}** students in "
    f"SY {sy_label(peak_year['SY'])} and reached its lowest at "
    f"**{int(trough_year['TOTAL_CNT']):,}** in SY {sy_label(trough_year['SY'])}."
)

st.divider()

# ---------------------------------------------------------------------------
# LEHS vs Lynn district — same-year comparison
# ---------------------------------------------------------------------------

st.subheader(f"LEHS vs. Lynn Public Schools district ({sy_label(current['SY'])})")

if not district.empty:
    d_current = district.iloc[-1]
    compare = pd.DataFrame({
        "Indicator": ["% Hispanic/Latino", "% English Learners", "% Low Income",
                       "% High Needs", "% First Lang Not English", "% Students w/ Disabilities"],
        "LEHS":     [current["HL_PCT"], current["EL_PCT"], current["LI_PCT"],
                     current["HN_PCT"], current["FLNE_PCT"], current["SWD_PCT"]],
        "Lynn District (all schools)": [d_current["HL_PCT"], d_current["EL_PCT"], d_current["LI_PCT"],
                                          d_current["HN_PCT"], d_current["FLNE_PCT"], d_current["SWD_PCT"]],
    })
    long = compare.melt(id_vars="Indicator", var_name="Scope", value_name="Pct").dropna()
    fig = px.bar(
        long, x="Indicator", y="Pct", color="Scope", barmode="group",
        text=long["Pct"].apply(lambda x: f"{x:.0%}"),
        color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District (all schools)": LEHS_NAVY},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                       xaxis_title="")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "LEHS specifically tends to have **higher ELL, FLNE, and Hispanic/Latino "
        "share** than the district as a whole — because the district also includes "
        "Lynn Classical, Lynn Tech, and 19+ elementary/middle schools with different "
        "demographic mixes."
    )

st.divider()

# ---------------------------------------------------------------------------
# Race/ethnicity — current snapshot + composition over time
# ---------------------------------------------------------------------------

st.subheader(f"Race / Ethnicity — {sy_label(current['SY'])}")

col_a, col_b = st.columns([1, 2])

with col_a:
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
    race_data = race_data[race_data["Pct"] > 0].sort_values("Pct", ascending=False)
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
    fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
    fig.update_layout(**DEFAULT_LAYOUT, showlegend=False)
    st.plotly_chart(fig, width="stretch")

with col_b:
    st.markdown("**Composition over time**")
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
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                       xaxis_title="School Year")
    st.plotly_chart(fig, width="stretch")

# Detailed race table
st.markdown("**Detailed race/ethnicity counts and shares (latest year)**")
total = current["TOTAL_CNT"]
race_table = pd.DataFrame({
    "Group": ["Hispanic/Latino", "African American/Black", "Asian", "White",
              "Multi-Race", "Native American", "Native Hawaiian/PI"],
    "%":     [current["HL_PCT"], current["BAA_PCT"], current["AS_PCT"], current["WH_PCT"],
              current["MNHL_PCT"], current["AIAN_PCT"], current["NHPI_PCT"]],
})
race_table["Approx. students"] = (race_table["%"] * total).round().astype("Int64")
race_table = race_table.sort_values("%", ascending=False)
race_table["%"] = race_table["%"].apply(lambda x: f"{x:.1%}")
race_table["Approx. students"] = race_table["Approx. students"].apply(
    lambda x: f"{int(x):,}" if pd.notna(x) else "—"
)
st.dataframe(race_table, width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Gender breakdown
# ---------------------------------------------------------------------------

st.subheader("Gender Breakdown Over Time")

gender_long = lehs.melt(
    id_vars=["SY"],
    value_vars=["FE_PCT", "MA_PCT", "NB_PCT"] if "NB_PCT" in lehs.columns else ["FE_PCT", "MA_PCT"],
    var_name="Gender", value_name="Pct",
).dropna(subset=["Pct"])
gender_long["Gender"] = gender_long["Gender"].map({
    "FE_PCT": "Female", "MA_PCT": "Male", "NB_PCT": "Non-binary",
})
fig = px.area(
    gender_long, x="SY", y="Pct", color="Gender",
    color_discrete_map={"Female": "#D81B60", "Male": "#1E88E5", "Non-binary": "#FFC107"},
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                   xaxis_title="School Year")
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Selected populations trend
# ---------------------------------------------------------------------------

st.subheader("Selected Populations Over Time")
st.caption(
    "Five key student-group classifications that drive resource allocation, "
    "accountability calculations, and federal/state programmatic support."
)

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
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share of Students",
                   xaxis_title="School Year")
st.plotly_chart(fig, width="stretch")

# Special pull-out: ELL trajectory
ell_with_data = lehs.dropna(subset=["EL_PCT"])
if len(ell_with_data) >= 2:
    first_ell = ell_with_data.iloc[0]
    last_ell = ell_with_data.iloc[-1]
    st.markdown(
        f"**ELL share trajectory:** {first_ell['EL_PCT']:.0%} in SY "
        f"{sy_label(first_ell['SY'])} → **{last_ell['EL_PCT']:.0%}** in SY "
        f"{sy_label(last_ell['SY'])}  "
        f"*(+{(last_ell['EL_PCT'] - first_ell['EL_PCT']) * 100:.0f} percentage points)*."
    )

st.divider()

# ---------------------------------------------------------------------------
# Grade-level enrollment + grade-by-race breakdown
# ---------------------------------------------------------------------------

st.subheader(f"Grade-Level Enrollment ({sy_label(current['SY'])})")

grade_data = pd.DataFrame({
    "Grade": ["9", "10", "11", "12"],
    "Students": [current["G9_CNT"], current["G10_CNT"], current["G11_CNT"], current["G12_CNT"]],
})

fig = go.Figure(go.Bar(
    x=grade_data["Grade"],
    y=grade_data["Students"],
    text=grade_data["Students"].apply(lambda v: f"{int(v):,}" if pd.notna(v) else ""),
    textposition="outside",
    marker_color=LEHS_NAVY,
))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="Grade")
st.plotly_chart(fig, width="stretch")

# Pull-out: 9-12 attrition narrative
total_hs = sum(current[c] for c in ["G9_CNT", "G10_CNT", "G11_CNT", "G12_CNT"]
                if pd.notna(current[c]))
if pd.notna(current["G9_CNT"]) and pd.notna(current["G12_CNT"]):
    if current["G9_CNT"] < current["G12_CNT"]:
        narrowing = (current["G12_CNT"] - current["G9_CNT"]) / current["G12_CNT"]
        narrative = (
            f"Grade 9 enrollment is **{narrowing:.0%} smaller** than grade 12 — "
            f"could reflect shrinking incoming cohorts. See **Success After HS** "
            f"for 9th-to-10th promotion rates and attrition analysis."
        )
    else:
        narrowing = (current["G9_CNT"] - current["G12_CNT"]) / current["G9_CNT"]
        narrative = (
            f"Grade 9 enrollment is **{narrowing:.0%} larger** than grade 12 — "
            f"the standard funneling pattern (some students leave before "
            f"graduation). See **Success After HS** for cohort-tracked attrition."
        )
    st.caption(narrative)

st.divider()

# ---------------------------------------------------------------------------
# Enrollment by selected populations — counts, not just percentages
# ---------------------------------------------------------------------------

st.subheader(f"Selected populations — count and share ({sy_label(current['SY'])})")

pop_counts = pd.DataFrame({
    "Group": ["English Learners", "First Lang Not English", "Low Income",
              "Students w/ Disabilities", "High Needs"],
    "Count": [current.get("EL_CNT"), current.get("FLNE_CNT"), current.get("LI_CNT"),
              current.get("SWD_CNT"), current.get("HN_CNT")],
    "Share": [current.get("EL_PCT"), current.get("FLNE_PCT"), current.get("LI_PCT"),
              current.get("SWD_PCT"), current.get("HN_PCT")],
})
pop_counts = pop_counts.dropna(subset=["Count"])
pop_counts["Count"] = pop_counts["Count"].astype(int)
pop_counts["Display"] = pop_counts.apply(
    lambda r: f"{r['Count']:,} ({r['Share']:.0%})", axis=1
)

fig = go.Figure(go.Bar(
    y=pop_counts["Group"],
    x=pop_counts["Count"],
    text=pop_counts["Display"],
    textposition="outside",
    orientation="h",
    marker_color=LEHS_GOLD,
))
fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Students", yaxis_title="",
                   xaxis_range=[0, pop_counts["Count"].max() * 1.25])
st.plotly_chart(fig, width="stretch")
