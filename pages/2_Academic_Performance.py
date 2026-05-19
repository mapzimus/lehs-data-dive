"""Section 2 — Academic Performance: MCAS trends, growth, subgroup gaps."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(page_title="Academic Performance | LEHS", page_icon="📈", layout="wide")
sidebar_attribution()

st.title("Academic Performance")
st.markdown(
    "MCAS Grade 10 results in English Language Arts, Mathematics, and Science, "
    "with the full achievement-level distribution (Exceeding / Meeting / "
    "Partially Meeting / Not Meeting), subgroup gaps, growth percentiles, "
    "and benchmarks vs. Lynn district and the state."
)

mcas = load_dataset("mcas_achievement")
if mcas.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

# Normalize unicode in STU_GRP
mcas["STU_GRP"] = mcas["STU_GRP"].astype(str).str.replace("\xa0", " ", regex=False)

# Filter sets we'll reuse
lehs = mcas[(mcas["ORG_CODE"] == LEHS_SCHOOL_CODE) & (mcas["TEST_GRADE"] == "10")].copy()
district = mcas[
    (mcas["DIST_CODE"] == LYNN_DISTRICT_CODE)
    & (mcas["ORG_TYPE"] == "District")
    & (mcas["TEST_GRADE"] == "10")
    & (mcas["STU_GRP"] == "All Students")
].copy()
state = mcas[
    (mcas["ORG_TYPE"] == "State")
    & (mcas["TEST_GRADE"] == "10")
    & (mcas["STU_GRP"] == "All Students")
].copy()

if lehs.empty:
    st.error("No LEHS Grade 10 MCAS data found.")
    st.stop()

SUBJECT_MAP = {"ELA": "English Language Arts", "MATH": "Mathematics", "SCI": "Science"}
SUBJECT_COLOR = {"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"}

# ---------------------------------------------------------------------------
# Hero numbers — most recent year, all subjects, full picture
# ---------------------------------------------------------------------------

all_students = lehs[lehs["STU_GRP"] == "All Students"].copy()
latest_year = int(all_students["SY"].max())

st.subheader(f"Grade 10 — At a Glance (SY {sy_label(latest_year)})")

c1, c2, c3, c4 = st.columns(4)
for col, code in zip([c1, c2, c3], ["ELA", "MATH", "SCI"]):
    sub = all_students[(all_students["SUBJECT_CODE"] == code) & (all_students["SY"] == latest_year)]
    if sub.empty:
        continue
    row = sub.iloc[0]
    me_pct = row["M_PLUS_E_PCT"]
    scaled = row["AVG_SCALED_SCORE"]
    students = int(row["STU_CNT"]) if pd.notna(row["STU_CNT"]) else 0
    with col:
        st.metric(
            f"{SUBJECT_MAP[code]} — % M+E",
            f"{me_pct:.0%}" if pd.notna(me_pct) else "—",
            f"Avg scaled: {scaled:.0f}  ·  n = {students:,}" if pd.notna(scaled) else f"n = {students:,}",
        )

# Achievement percentile (low = struggling vs state)
with c4:
    ela_row = all_students[(all_students["SUBJECT_CODE"] == "ELA") & (all_students["SY"] == latest_year)]
    if not ela_row.empty:
        ach = ela_row.iloc[0].get("ACH_PERCENTILE")
        sgp = ela_row.iloc[0].get("AVG_SGP")
        st.metric(
            "Achievement Percentile (ELA)",
            f"{int(ach)}" if pd.notna(ach) else "—",
            f"SGP (growth): {sgp:.0f}" if pd.notna(sgp) else "",
        )

st.caption(
    "**Achievement percentile** is LEHS's rank vs. all MA schools — 50 = "
    "statewide median, lower numbers = below most schools. **SGP** is growth "
    "vs. academic peers (50 = average annual growth)."
)

st.divider()

# ---------------------------------------------------------------------------
# Trend: All Students % M+E by subject — with inline labels
# ---------------------------------------------------------------------------

st.subheader("Grade 10 % Meeting or Exceeding — All Students by Subject")

trend = all_students.sort_values(["SUBJECT_CODE", "SY"]).copy()
trend["label"] = trend["M_PLUS_E_PCT"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "")

fig = px.line(
    trend, x="SY", y="M_PLUS_E_PCT", color="SUBJECT_CODE",
    color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
    labels={"SUBJECT_CODE": "Subject", "M_PLUS_E_PCT": "% M+E", "SY": "Year"},
)
fig.update_traces(textposition="top center", textfont=dict(size=10))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                   yaxis_title="% Meeting or Exceeding")
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Achievement-level distribution (E / M / PM / NM) for latest year
# ---------------------------------------------------------------------------

st.subheader(f"Full Achievement-Level Distribution (SY {sy_label(latest_year)})")
st.caption(
    "MCAS classifies every student into one of four levels: **E**xceeding, "
    "**M**eeting, **P**artially **M**eeting, or **N**ot **M**eeting expectations. "
    "The headline '% M+E' only shows the top two — this chart shows where "
    "everyone falls."
)

latest = all_students[all_students["SY"] == latest_year]
dist_rows = []
for _, row in latest.iterrows():
    for level, col, color in [
        ("Exceeding",          "E_PCT",  "#1B5E20"),
        ("Meeting",            "M_PCT",  "#388E3C"),
        ("Partially Meeting",  "PM_PCT", "#F57C00"),
        ("Not Meeting",        "NM_PCT", "#D32F2F"),
    ]:
        dist_rows.append({
            "Subject": SUBJECT_MAP.get(row["SUBJECT_CODE"], row["SUBJECT_CODE"]),
            "Level":   level,
            "Pct":     row[col],
            "Count":   row[col.replace("PCT", "CNT")] if col.replace("PCT", "CNT") in row else 0,
        })
dist_df = pd.DataFrame(dist_rows).dropna(subset=["Pct"])
dist_df["label"] = dist_df["Pct"].apply(lambda x: f"{x:.0%}" if x >= 0.05 else "")

fig = px.bar(
    dist_df, y="Subject", x="Pct", color="Level", orientation="h",
    text="label",
    category_orders={"Level": ["Not Meeting", "Partially Meeting", "Meeting", "Exceeding"]},
    color_discrete_map={
        "Exceeding":         "#1B5E20",
        "Meeting":           "#388E3C",
        "Partially Meeting": "#F57C00",
        "Not Meeting":       "#D32F2F",
    },
)
fig.update_traces(textposition="inside", textfont=dict(color="white", size=11))
fig.update_layout(**DEFAULT_LAYOUT, xaxis_tickformat=".0%", xaxis_title="Share of test-takers",
                   yaxis_title="", barmode="stack")
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# LEHS vs Lynn district vs MA state — by subject, latest year
# ---------------------------------------------------------------------------

st.subheader(f"LEHS vs. Lynn District vs. Massachusetts — SY {sy_label(latest_year)}")

bench_rows = []
for code in ["ELA", "MATH", "SCI"]:
    lehs_row = latest[latest["SUBJECT_CODE"] == code]
    dist_row = district[(district["SUBJECT_CODE"] == code) & (district["SY"] == latest_year)]
    state_row = state[(state["SUBJECT_CODE"] == code) & (state["SY"] == latest_year)]
    if not lehs_row.empty:
        bench_rows.append({"Subject": SUBJECT_MAP[code], "Scope": "LEHS",
                           "Pct": lehs_row.iloc[0]["M_PLUS_E_PCT"]})
    if not dist_row.empty:
        bench_rows.append({"Subject": SUBJECT_MAP[code], "Scope": "Lynn District",
                           "Pct": dist_row.iloc[0]["M_PLUS_E_PCT"]})
    if not state_row.empty:
        bench_rows.append({"Subject": SUBJECT_MAP[code], "Scope": "Massachusetts",
                           "Pct": state_row.iloc[0]["M_PLUS_E_PCT"]})

if bench_rows:
    bench_df = pd.DataFrame(bench_rows).dropna(subset=["Pct"])
    bench_df["label"] = bench_df["Pct"].apply(lambda x: f"{x:.0%}")
    fig = px.bar(
        bench_df, x="Subject", y="Pct", color="Scope", barmode="group",
        text="label",
        color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District": LEHS_NAVY,
                            "Massachusetts": "#455A64"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="% Meeting + Exceeding",
                       xaxis_title="")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "LEHS is benchmarked against two natural reference points: the Lynn "
        "district aggregate (which includes Classical, Tech, and other Lynn "
        "schools) and the Massachusetts statewide average."
    )

st.divider()

# ---------------------------------------------------------------------------
# Avg scaled score trend — by subject
# ---------------------------------------------------------------------------

st.subheader("Average Scaled Score Trend")
st.caption(
    "Scaled scores run roughly **440–560**, with **500 = Meeting Expectations**. "
    "Useful for measuring fine-grained year-to-year change."
)

scaled_trend = all_students.dropna(subset=["AVG_SCALED_SCORE"]).copy()
scaled_trend["label"] = scaled_trend["AVG_SCALED_SCORE"].apply(lambda x: f"{x:.0f}")

fig = px.line(
    scaled_trend.sort_values(["SUBJECT_CODE", "SY"]),
    x="SY", y="AVG_SCALED_SCORE", color="SUBJECT_CODE",
    color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
)
fig.update_traces(textposition="top center", textfont=dict(size=10))
fig.add_hline(y=500, line_dash="dash", line_color="gray",
              annotation_text="Meets Expectations (500)", annotation_position="right")
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average scaled score",
                   xaxis_title="School Year")
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Subject-toggleable student-group breakdown
# ---------------------------------------------------------------------------

st.subheader("Student Group Breakdown")

subject_choice = st.radio(
    "Subject",
    options=["ELA", "MATH", "SCI"],
    format_func=lambda c: SUBJECT_MAP[c],
    horizontal=True,
)

groups_of_interest = [
    "All Students",
    "English Learners",
    "Former English Learners",
    "Hispanic or Latino",
    "Black or African American",
    "Asian",
    "White",
    "Low Income",
    "Students with Disabilities",
    "High Needs",
]

sub = lehs[
    (lehs["SUBJECT_CODE"] == subject_choice) & (lehs["STU_GRP"].isin(groups_of_interest))
].sort_values("SY").copy()

color_map = {
    "All Students":               LEHS_NAVY,
    "English Learners":           SUBGROUP_PALETTE["English Learner"],
    "Former English Learners":    SUBGROUP_PALETTE["Former English Learner"],
    "Hispanic or Latino":         SUBGROUP_PALETTE["Hispanic/Latino"],
    "Black or African American":  SUBGROUP_PALETTE["African American/Black"],
    "Asian":                      SUBGROUP_PALETTE["Asian"],
    "White":                      SUBGROUP_PALETTE["White"],
    "Low Income":                 SUBGROUP_PALETTE["Low Income"],
    "Students with Disabilities": SUBGROUP_PALETTE["Students w/ Disabilities"],
    "High Needs":                 SUBGROUP_PALETTE["High Needs"],
}

# Add inline labels for latest year only (avoid clutter)
sub["label"] = ""
latest_sub_idx = sub.sort_values("SY").groupby("STU_GRP").tail(1).index
sub.loc[latest_sub_idx, "label"] = sub.loc[latest_sub_idx, "M_PLUS_E_PCT"].apply(
    lambda x: f"{x:.0%}" if pd.notna(x) else ""
)

fig = px.line(
    sub, x="SY", y="M_PLUS_E_PCT", color="STU_GRP", markers=True,
    color_discrete_map=color_map, text="label",
)
fig.update_traces(textposition="middle right", textfont=dict(size=10))
fig.update_layout(
    **DEFAULT_LAYOUT,
    yaxis_tickformat=".0%",
    yaxis_title=f"{SUBJECT_MAP[subject_choice]} — % M+E",
    xaxis_title="School Year",
)
st.plotly_chart(fig, width="stretch")

# Student-group count table
latest_year_sub = sub[sub["SY"] == sub["SY"].max()].copy()
if not latest_year_sub.empty:
    table = latest_year_sub[[
        "STU_GRP", "STU_CNT", "M_PLUS_E_PCT", "E_PCT", "M_PCT", "PM_PCT", "NM_PCT", "AVG_SCALED_SCORE"
    ]].copy()
    table = table.rename(columns={
        "STU_GRP": "Student group", "STU_CNT": "Tested",
        "M_PLUS_E_PCT": "% M+E", "E_PCT": "% Exceeding",
        "M_PCT": "% Meeting", "PM_PCT": "% Partial", "NM_PCT": "% Not Meet",
        "AVG_SCALED_SCORE": "Avg score",
    })
    table["Tested"] = table["Tested"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
    for c in ["% M+E", "% Exceeding", "% Meeting", "% Partial", "% Not Meet"]:
        table[c] = table[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    table["Avg score"] = table["Avg score"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
    st.markdown(f"**SY {sy_label(latest_year_sub['SY'].max())} — by student group**")
    st.dataframe(table.sort_values("Student group"), width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Achievement gap chart
# ---------------------------------------------------------------------------

st.subheader(f"Achievement Gap — Latest Year ({sy_label(latest_year)})")
st.caption(
    "How each student group performs *relative to LEHS's school-wide average*. "
    "Negative bars = below all-students; positive = above. The magnitude of "
    "negative bars is where school-level intervention has the most leverage."
)

latest_sub = sub[sub["SY"] == sub["SY"].max()].copy()
if not latest_sub.empty and "All Students" in latest_sub["STU_GRP"].values:
    all_value = latest_sub.loc[latest_sub["STU_GRP"] == "All Students", "M_PLUS_E_PCT"].iloc[0]
    latest_sub["Gap"] = latest_sub["M_PLUS_E_PCT"] - all_value
    gap_data = latest_sub[latest_sub["STU_GRP"] != "All Students"].sort_values("Gap")
    gap_data["label"] = gap_data["Gap"].apply(lambda g: f"{g*100:+.1f} pts")

    colors = ["#D32F2F" if g < 0 else "#388E3C" for g in gap_data["Gap"]]
    fig = go.Figure(go.Bar(
        y=gap_data["STU_GRP"],
        x=gap_data["Gap"] * 100,
        orientation="h",
        text=gap_data["label"],
        textposition="outside",
        marker_color=colors,
    ))
    fig.update_layout(
        **DEFAULT_LAYOUT,
        title=f"Gap vs. All Students ({all_value:.0%}) — {SUBJECT_MAP[subject_choice]}",
        xaxis_title="Percentage point gap",
    )
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Student Growth Percentile
# ---------------------------------------------------------------------------

st.subheader("Student Growth Percentile (SGP)")
st.caption(
    "SGP measures how much a LEHS student grew academically year-over-year, "
    "compared to other MA students with similar prior MCAS scores. "
    "**50 = statewide median.** Values consistently above 50 = above-typical "
    "growth (school is moving students faster than peers); below 50 = "
    "below-typical."
)

sgp = lehs[(lehs["STU_GRP"] == "All Students") & (lehs["AVG_SGP"].notna())].sort_values("SY").copy()
sgp["label"] = sgp["AVG_SGP"].apply(lambda x: f"{x:.0f}")

if not sgp.empty:
    fig = px.line(
        sgp, x="SY", y="AVG_SGP", color="SUBJECT_CODE",
        color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
    )
    fig.update_traces(textposition="top center", textfont=dict(size=10))
    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                   annotation_text="Statewide median (50)", annotation_position="right")
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average SGP",
                       xaxis_title="School Year", yaxis_range=[0, 100])
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No SGP data available for LEHS in this dataset.")

st.divider()

# ---------------------------------------------------------------------------
# Participation rate trend
# ---------------------------------------------------------------------------

st.subheader("Participation Rate — Who actually takes the test?")
st.caption(
    "DESE requires 95%+ participation for full accountability credit. Schools "
    "missing this threshold face additional accountability review."
)

part = all_students.dropna(subset=["STU_PART_PCT"]).sort_values(["SUBJECT_CODE", "SY"]).copy()
part["label"] = part["STU_PART_PCT"].apply(lambda x: f"{x:.0%}")

fig = px.line(
    part, x="SY", y="STU_PART_PCT", color="SUBJECT_CODE",
    color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
)
fig.update_traces(textposition="bottom center", textfont=dict(size=10))
fig.add_hline(y=0.95, line_dash="dash", line_color="#D32F2F",
              annotation_text="DESE threshold (95%)", annotation_position="right")
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Participation rate",
                   xaxis_title="School Year", yaxis_range=[0.5, 1.05])
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Number of students tested per year
# ---------------------------------------------------------------------------

st.subheader("Number of Grade-10 Students Tested per Year")

counts = all_students.dropna(subset=["STU_CNT"]).sort_values(["SUBJECT_CODE", "SY"]).copy()
counts["label"] = counts["STU_CNT"].apply(lambda x: f"{int(x):,}")

fig = px.line(
    counts, x="SY", y="STU_CNT", color="SUBJECT_CODE",
    color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
)
fig.update_traces(textposition="top center", textfont=dict(size=9))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students tested",
                   xaxis_title="School Year")
st.plotly_chart(fig, width="stretch")

st.caption(
    "**Why this matters:** small subgroup counts trigger DESE suppression "
    "rules (cells with < 10 students are blanked). The Grade-10 cohort size "
    "drives how much subgroup detail you can actually see."
)
