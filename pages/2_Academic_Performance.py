"""Section 2 — Academic Performance: MCAS trends, growth, subgroup gaps.

This is the dashboard's most-viewed section. Lead with the headline numbers,
then the full distribution, then benchmarks, then deep subgroup analysis
(the most analytically valuable view), then growth, then health metrics.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset
from utils.interpret import sgp_methodology_note, sy_label

st.set_page_config(page_title="Academic Performance | LEHS", page_icon="📈", layout="wide")
sidebar_attribution()

st.title("Academic Performance")
st.markdown(
    "MCAS Grade 10 results in English Language Arts, Mathematics, and Science — "
    "headline rates, the full achievement-level distribution, multi-year subgroup "
    "gaps, growth percentiles, and benchmarks vs. Lynn district and Massachusetts."
)

mcas = load_dataset("mcas_achievement")
if mcas.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# Normalize subgroup labels — DESE emits both singular and plural forms across
# years for some subgroups; collapse to one canonical form so filters and
# color maps work consistently. NBSP is also stripped because it sneaks in.
mcas["STU_GRP"] = mcas["STU_GRP"].astype(str).str.replace("\xa0", " ", regex=False)
SUBGROUP_CANONICAL = {
    "English Learner":          "English Learners",
    "Former English Learner":   "Former English Learners",
}
mcas["STU_GRP"] = mcas["STU_GRP"].replace(SUBGROUP_CANONICAL)

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

# ===========================================================================
# 1. HERO — most recent year, all subjects, growth percentile
# ===========================================================================

all_students = lehs[lehs["STU_GRP"] == "All Students"].copy()
latest_year = int(all_students["SY"].max())

st.header(f"At a Glance — Grade 10, SY {sy_label(latest_year)}")

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
    "statewide median, lower = below most schools. **SGP** is growth vs. "
    "academic peers — 50 = average annual growth, higher = LEHS moves "
    "students faster than peer schools."
)

st.divider()

# ===========================================================================
# 2. % MEETING+EXCEEDING — multi-year trend per subject
# ===========================================================================

st.header("% Meeting or Exceeding — Trend by Subject")

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
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "MCAS was waived in spring 2020 and modified in 2021 — those years "
    "show fewer data points and shouldn't be read as a real trend break."
)

# ---------------------------------------------------------------------------
# Avg scaled score trend — same data, different lens
# ---------------------------------------------------------------------------

st.subheader("Average Scaled Score Trend")
st.caption(
    "Scaled scores run roughly **440–560**, with **500 = Meeting Expectations**. "
    "Useful for measuring fine-grained year-to-year change that gets compressed "
    "in the M+E percentage view above."
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
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===========================================================================
# 3. FULL ACHIEVEMENT-LEVEL DISTRIBUTION — latest year + multi-year stacked
# ===========================================================================

st.header(f"Full Achievement-Level Distribution (SY {sy_label(latest_year)})")
st.caption(
    "MCAS classifies every student into one of four levels: **E**xceeding, "
    "**M**eeting, **P**artially **M**eeting, or **N**ot **M**eeting expectations. "
    "Headline '% M+E' only shows the top two — this view shows where everyone falls."
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
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Distribution evolution over time — per subject
# ---------------------------------------------------------------------------

st.subheader("How the Distribution Has Shifted Over Time")
st.caption(
    "Same four levels, plotted year by year per subject. Watch the **Not "
    "Meeting** band — shrinking it is the school's hardest-and-most-meaningful "
    "challenge."
)

dist_subject_choice = st.radio(
    "Subject",
    options=["ELA", "MATH", "SCI"],
    format_func=lambda c: SUBJECT_MAP[c],
    horizontal=True,
    key="dist_subj",
)

dist_yearly = all_students[all_students["SUBJECT_CODE"] == dist_subject_choice].copy()
dist_yearly = dist_yearly.dropna(subset=["E_PCT", "M_PCT", "PM_PCT", "NM_PCT"]).sort_values("SY")

if not dist_yearly.empty:
    dist_long = dist_yearly.melt(
        id_vars="SY",
        value_vars=["E_PCT", "M_PCT", "PM_PCT", "NM_PCT"],
        var_name="Level",
        value_name="Pct",
    )
    level_map = {"E_PCT": "Exceeding", "M_PCT": "Meeting",
                 "PM_PCT": "Partially Meeting", "NM_PCT": "Not Meeting"}
    dist_long["Level"] = dist_long["Level"].map(level_map)
    fig = px.bar(
        dist_long, x="SY", y="Pct", color="Level",
        category_orders={"Level": ["Not Meeting", "Partially Meeting", "Meeting", "Exceeding"]},
        color_discrete_map={
            "Exceeding":         "#1B5E20",
            "Meeting":           "#388E3C",
            "Partially Meeting": "#F57C00",
            "Not Meeting":       "#D32F2F",
        },
        barmode="stack",
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="Share of test-takers", xaxis_title="School Year")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===========================================================================
# 4. BENCHMARKS — LEHS vs Lynn district vs Massachusetts (latest year)
# ===========================================================================

st.header(f"LEHS vs. Lynn district vs. Massachusetts — SY {sy_label(latest_year)}")

from utils.stats import wilson_ci_from_pct  # noqa: E402

bench_rows = []
for code in ["ELA", "MATH", "SCI"]:
    lehs_row = latest[latest["SUBJECT_CODE"] == code]
    dist_row = district[(district["SUBJECT_CODE"] == code) & (district["SY"] == latest_year)]
    state_row = state[(state["SUBJECT_CODE"] == code) & (state["SY"] == latest_year)]
    for label, row_df in [
        ("LEHS", lehs_row),
        ("Lynn district", dist_row),
        ("Massachusetts", state_row),
    ]:
        if row_df.empty:
            continue
        r = row_df.iloc[0]
        pct = r["M_PLUS_E_PCT"]
        n = r.get("STU_CNT")
        lo, hi = wilson_ci_from_pct(pct, n)
        bench_rows.append({
            "Subject": SUBJECT_MAP[code], "Scope": label, "Pct": pct,
            "n": int(n) if pd.notna(n) else None,
            "ci_lo": lo, "ci_hi": hi,
        })

if bench_rows:
    bench_df = pd.DataFrame(bench_rows).dropna(subset=["Pct"])
    bench_df["label"] = bench_df["Pct"].apply(lambda x: f"{x:.0%}")
    bench_df["err_minus"] = (bench_df["Pct"] - bench_df["ci_lo"]).clip(lower=0)
    bench_df["err_plus"] = (bench_df["ci_hi"] - bench_df["Pct"]).clip(lower=0)
    fig = px.bar(
        bench_df, x="Subject", y="Pct", color="Scope", barmode="group",
        text="label",
        category_orders={"Scope": ["LEHS", "Lynn district", "Massachusetts"]},
        color_discrete_map={
            "LEHS":          LEHS_GOLD,
            "Lynn district": LEHS_NAVY,
            "Massachusetts": "#455A64",
        },
        error_y="err_plus",
        error_y_minus="err_minus",
        custom_data=["n"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>%{fullData.name}: %{y:.1%}<br>"
            "n = %{customdata[0]:,}<extra></extra>"
        ),
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="% Meeting + Exceeding",
                       xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Three natural benchmarks: LEHS, the Lynn district aggregate, and the "
        "Massachusetts statewide average. Error bars are 95% Wilson confidence "
        "intervals — narrower for the larger denominators. For school-to-school "
        "MCAS comparison with Lynn Classical, Tech, and the alternative academies, "
        "see [Lynn District](/Lynn_District) (LEHS vs Siblings tab)."
    )

# ---------------------------------------------------------------------------
# LEHS gap to MA over time — multi-year benchmark
# ---------------------------------------------------------------------------

st.subheader("LEHS Gap to Massachusetts — Over Time")
st.caption(
    "How far LEHS has been from the statewide average each year. A flat or "
    "shrinking gap means LEHS is keeping pace or catching up; a widening gap "
    "means the school is falling behind."
)

gap_rows = []
for code in ["ELA", "MATH", "SCI"]:
    lehs_subj = all_students[all_students["SUBJECT_CODE"] == code][["SY", "M_PLUS_E_PCT"]].copy()
    state_subj = state[state["SUBJECT_CODE"] == code][["SY", "M_PLUS_E_PCT"]].copy()
    state_subj = state_subj.rename(columns={"M_PLUS_E_PCT": "MA"})
    merged = lehs_subj.merge(state_subj, on="SY", how="inner")
    merged["gap"] = merged["M_PLUS_E_PCT"] - merged["MA"]
    merged["Subject"] = SUBJECT_MAP[code]
    gap_rows.append(merged)

if gap_rows:
    gap_df = pd.concat(gap_rows, ignore_index=True).dropna(subset=["gap"])
    if not gap_df.empty:
        fig = px.line(
            gap_df.sort_values("SY"), x="SY", y="gap", color="Subject",
            color_discrete_map={
                SUBJECT_MAP["ELA"]: SUBJECT_COLOR["ELA"],
                SUBJECT_MAP["MATH"]: SUBJECT_COLOR["MATH"],
                SUBJECT_MAP["SCI"]: SUBJECT_COLOR["SCI"],
            },
            markers=True,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray",
                      annotation_text="MA average (0)", annotation_position="right")
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="+.0%",
                           yaxis_title="LEHS minus MA (percentage points)",
                           xaxis_title="School Year")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===========================================================================
# 5. SUBGROUP BREAKDOWN — toggleable + multi-year + gap evolution
# ===========================================================================

st.header("Subgroup Performance")
st.caption(
    "Where the headline number hides everything: how each student group is "
    "doing, how the gaps to school-wide have moved, and where the disparities "
    "are statistically real vs. small-cohort noise."
)

subject_choice = st.radio(
    "Subject",
    options=["ELA", "MATH", "SCI"],
    format_func=lambda c: SUBJECT_MAP[c],
    horizontal=True,
    key="subgroup_subj",
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

# Inline labels for latest year only (avoid clutter)
sub["label"] = ""
latest_sub_idx = sub.sort_values("SY").groupby("STU_GRP").tail(1).index
sub.loc[latest_sub_idx, "label"] = sub.loc[latest_sub_idx, "M_PLUS_E_PCT"].apply(
    lambda x: f"{x:.0%}" if pd.notna(x) else ""
)

st.subheader(f"% M+E Trend — {SUBJECT_MAP[subject_choice]}, by Student Group")
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
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# NEW — Gap-to-school-wide evolution over time
# ---------------------------------------------------------------------------

st.subheader(f"Gap to School-Wide Average — Over Time, {SUBJECT_MAP[subject_choice]}")
st.caption(
    "Each line = one subgroup's gap (in percentage points) to the LEHS "
    "school-wide rate, plotted year by year. **Lines moving up toward zero** "
    "means the gap is shrinking. Lines below zero = subgroup performs below "
    "school-wide; lines above = subgroup performs above."
)

if not sub.empty:
    all_by_year = (
        sub[sub["STU_GRP"] == "All Students"][["SY", "M_PLUS_E_PCT"]]
        .rename(columns={"M_PLUS_E_PCT": "all_pct"})
    )
    gap_long = (
        sub[sub["STU_GRP"] != "All Students"]
        [["SY", "STU_GRP", "M_PLUS_E_PCT"]]
        .merge(all_by_year, on="SY", how="inner")
    )
    gap_long["gap"] = gap_long["M_PLUS_E_PCT"] - gap_long["all_pct"]
    gap_long = gap_long.dropna(subset=["gap"])

    if not gap_long.empty:
        fig = px.line(
            gap_long.sort_values("SY"), x="SY", y="gap", color="STU_GRP",
            markers=True, color_discrete_map=color_map,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray",
                      annotation_text="School-wide (0 gap)", annotation_position="right")
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat="+.0%",
            yaxis_title="Gap to school-wide (pp)",
            xaxis_title="School Year",
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Latest-year achievement gap with statistical significance markers
# ---------------------------------------------------------------------------

st.subheader(f"Latest-Year Achievement Gap — SY {sy_label(latest_year)}, {SUBJECT_MAP[subject_choice]}")
st.caption(
    "Bars are marked with statistical-significance flags (`*` p<0.05, `**` p<0.01, "
    "`***` p<0.001) from a two-proportion z-test against the school-wide rate. "
    "Gray bars = gap not distinguishable from noise."
)

from utils.stats import compare_proportions  # noqa: E402

latest_sub = sub[sub["SY"] == sub["SY"].max()].copy()
if not latest_sub.empty and "All Students" in latest_sub["STU_GRP"].values:
    all_row = latest_sub[latest_sub["STU_GRP"] == "All Students"].iloc[0]
    all_value = all_row["M_PLUS_E_PCT"]
    all_n = all_row.get("STU_CNT")
    all_k = (
        int(round(all_value * all_n))
        if pd.notna(all_value) and pd.notna(all_n) else None
    )
    latest_sub["Gap"] = latest_sub["M_PLUS_E_PCT"] - all_value

    def _gap_stats(row):
        n = row.get("STU_CNT")
        pct = row["M_PLUS_E_PCT"]
        if pd.isna(n) or pd.isna(pct) or all_k is None or pd.isna(all_n):
            return ("", "", False)
        k = int(round(pct * n))
        test = compare_proportions(int(k), int(n), int(all_k), int(all_n))
        return (test.stars, test.magnitude, test.significant)

    gap_data = latest_sub[latest_sub["STU_GRP"] != "All Students"].copy()
    gap_data[["stars", "effect", "significant"]] = gap_data.apply(
        lambda r: pd.Series(_gap_stats(r)), axis=1,
    )
    gap_data = gap_data.sort_values("Gap")
    gap_data["label"] = gap_data.apply(
        lambda r: (
            f"{r['Gap']*100:+.1f} pts {r['stars']}"
            if pd.notna(r["Gap"]) else ""
        ),
        axis=1,
    )

    def _bar_color(row):
        if not row["significant"]:
            return "#B0BEC5"
        return "#D32F2F" if row["Gap"] < 0 else "#388E3C"

    colors = gap_data.apply(_bar_color, axis=1).tolist()
    fig = go.Figure(go.Bar(
        y=gap_data["STU_GRP"],
        x=gap_data["Gap"] * 100,
        orientation="h",
        text=gap_data["label"],
        textposition="outside",
        marker_color=colors,
        customdata=gap_data[["STU_CNT", "effect"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>Gap: %{x:.1f} pts<br>"
            "n = %{customdata[0]:,}<br>"
            "Effect size: %{customdata[1]}<extra></extra>"
        ),
        cliponaxis=False,
    ))
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_title=f"Percentage point gap vs. school-wide ({all_value:.0%})",
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Subgroup detail table
# ---------------------------------------------------------------------------

latest_year_sub = sub[sub["SY"] == sub["SY"].max()].copy()
if not latest_year_sub.empty:
    st.subheader(f"Subgroup Detail Table — SY {sy_label(latest_year_sub['SY'].max())}, {SUBJECT_MAP[subject_choice]}")
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
    st.dataframe(table.sort_values("Student group"), use_container_width=True, hide_index=True)

st.divider()

# ===========================================================================
# 6. GROWTH — SGP by subject and (where available) by subgroup
# ===========================================================================

st.header("Student Growth Percentile (SGP)")
st.caption(
    "SGP measures how much a LEHS student grew academically year-over-year, "
    "compared to other MA students with similar prior MCAS scores. "
    "**50 = statewide median.** A subject consistently above 50 = the school "
    "moves students faster than peers; below 50 = slower."
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
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average SGP — All Students",
                       xaxis_title="School Year", yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------------------------
    # SGP vs. peers — where does LEHS sit in the Gateway HS distribution?
    # Most school-level SGP coverage in this dataset is SY 2024+, so the
    # peer-comparison view is anchored to the latest year.
    # ---------------------------------------------------------------------------
    peer_sgp = mcas[
        (mcas["TEST_GRADE"] == "10")
        & (mcas["STU_GRP"] == "All Students")
        & (mcas["AVG_SGP"].notna())
        & (mcas["ORG_TYPE"] == "School")
        & (mcas["SUBJECT_CODE"].isin(["ELA", "MATH"]))
        & (mcas["SY"] == mcas[mcas["AVG_SGP"].notna() & (mcas["ORG_TYPE"] == "School")]["SY"].max())
    ].copy()
    if not peer_sgp.empty:
        peer_year = int(peer_sgp["SY"].max())
        st.subheader(f"LEHS vs. Gateway-Peer High Schools — SY {sy_label(peer_year)}")
        st.caption(
            "Each dot is one comprehensive high school in a Massachusetts "
            "Gateway city. LEHS is highlighted in gold; the dashed line "
            "marks the statewide median (50). Faster growth = right."
        )
        peer_sgp["is_lehs"] = peer_sgp["ORG_CODE"] == LEHS_SCHOOL_CODE
        peer_sgp["Subject"] = peer_sgp["SUBJECT_CODE"].map({"ELA": "ELA", "MATH": "Math"})
        # plot strip + LEHS marker overlay so LEHS pops visually
        fig = px.strip(
            peer_sgp.sort_values("Subject"),
            x="AVG_SGP", y="Subject", color="is_lehs",
            color_discrete_map={True: LEHS_GOLD, False: "#B0BEC5"},
            hover_data={"ORG_NAME": True, "AVG_SGP": True, "STU_CNT": True, "is_lehs": False, "Subject": False},
            stripmode="overlay",
        )
        fig.update_traces(marker=dict(size=11, line=dict(width=1, color="#455A64")), jitter=0.25)
        # overlay the LEHS dot a second time at larger size so it isn't lost in the swarm
        lehs_dots = peer_sgp[peer_sgp["is_lehs"]]
        if not lehs_dots.empty:
            fig.add_trace(go.Scatter(
                x=lehs_dots["AVG_SGP"], y=lehs_dots["Subject"],
                mode="markers+text",
                marker=dict(size=18, color=LEHS_GOLD, line=dict(width=2, color=LEHS_NAVY)),
                text=["LEHS"] * len(lehs_dots),
                textposition="top center", textfont=dict(color=LEHS_NAVY, size=11),
                hoverinfo="skip", showlegend=False,
            ))
        fig.add_vline(x=50, line_dash="dash", line_color="gray",
                      annotation_text="State median", annotation_position="top")
        fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Average SGP",
                          yaxis_title="", xaxis_range=[0, 100], showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # SGP by subgroup — latest year, ELA + Math only (SCI SGP often sparse)
    sgp_sub = lehs[
        (lehs["STU_GRP"].isin(groups_of_interest))
        & (lehs["SUBJECT_CODE"].isin(["ELA", "MATH"]))
        & (lehs["AVG_SGP"].notna())
        & (lehs["SY"] == lehs["SY"].max())
    ].copy()
    if not sgp_sub.empty:
        st.subheader(f"SGP by Student Group — SY {sy_label(int(sgp_sub['SY'].max()))}")
        st.caption(
            "Growth percentile broken out by subgroup. **All Students** is the "
            "reference; bars at 50 indicate that subgroup grew at the same rate "
            "as their academic peers statewide."
        )
        sgp_sub["Subject"] = sgp_sub["SUBJECT_CODE"].map({"ELA": "ELA", "MATH": "Math"})
        fig = px.bar(
            sgp_sub.sort_values(["Subject", "AVG_SGP"]),
            x="AVG_SGP", y="STU_GRP", color="Subject",
            orientation="h", barmode="group",
            color_discrete_map={"ELA": SUBJECT_COLOR["ELA"], "Math": SUBJECT_COLOR["MATH"]},
            text=sgp_sub["AVG_SGP"].round(0).astype(int).astype(str),
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.add_vline(x=50, line_dash="dash", line_color="gray",
                      annotation_text="Statewide median",
                      annotation_position="top right")
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_title="Average SGP", yaxis_title="",
            xaxis_range=[0, 100],
            height=max(360, 28 * sgp_sub["STU_GRP"].nunique()),
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("SGP data not available for LEHS in this dataset.")

st.caption(sgp_methodology_note())

st.divider()

# ===========================================================================
# 7. HEALTH METRICS — participation, cohort size, achievement-percentile trend
# ===========================================================================

st.header("Test Health Metrics")

# Achievement percentile trend
ach_trend = all_students.dropna(subset=["ACH_PERCENTILE"]).copy()
if not ach_trend.empty:
    st.subheader("LEHS Achievement Percentile — Rank vs. All MA Schools")
    st.caption(
        "Percentile rank of LEHS against every MA public school on MCAS. "
        "50 = at the statewide median. A rising line = LEHS is gaining "
        "ground relative to peer schools statewide; falling = losing ground."
    )
    ach_trend["label"] = ach_trend["ACH_PERCENTILE"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "")
    fig = px.line(
        ach_trend.sort_values(["SUBJECT_CODE", "SY"]),
        x="SY", y="ACH_PERCENTILE", color="SUBJECT_CODE",
        color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
    )
    fig.update_traces(textposition="top center", textfont=dict(size=10))
    fig.add_hline(y=50, line_dash="dash", line_color="gray",
                  annotation_text="Statewide median", annotation_position="right")
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Achievement percentile",
                      xaxis_title="School Year", yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

# Participation rate
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
st.plotly_chart(fig, use_container_width=True)

# Cohort size
st.subheader("Grade-10 Cohort Size Tested per Year")
st.caption(
    "Drives how much subgroup detail you can actually see — DESE suppresses "
    "any subgroup cell with fewer than 10 students."
)

counts = all_students.dropna(subset=["STU_CNT"]).sort_values(["SUBJECT_CODE", "SY"]).copy()
counts["label"] = counts["STU_CNT"].apply(lambda x: f"{int(x):,}")

fig = px.line(
    counts, x="SY", y="STU_CNT", color="SUBJECT_CODE",
    color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
)
fig.update_traces(textposition="top center", textfont=dict(size=9))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students tested",
                   xaxis_title="School Year")
st.plotly_chart(fig, use_container_width=True)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'MCAS achievement': mcas,
    })
except NameError:
    pass
