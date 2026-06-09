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
from utils.charts import (
    DEFAULT_LAYOUT,
    LEHS_GOLD,
    LEHS_NAVY,
    MCAS_YEARS,
    SUBGROUP_PALETTE,
    with_year_gaps,
    year_heatmap,
)
from utils.constants import (
    GATEWAY_PEER_COLOR,
    GENDER_PALETTE,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    STATE_COLOR,
)
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

st.divider()
st.header("📊 MCAS Results — Grade 10")
st.markdown(
    "MCAS is the state's annual test. Every Grade-10 student is sorted into one of "
    "four levels — **Exceeding, Meeting, Partially Meeting,** or **Not Meeting** "
    "grade-level expectations — in English, Math, and Science. Read this section in "
    "two halves: **achievement** (where students *land*) and **growth** (how fast "
    "they're *improving*). They tell different — and equally important — stories."
)
with st.expander("📖 What the MCAS terms mean"):
    st.markdown(
        "- **Achievement level** — every student lands in one of four bands: "
        "Exceeding, Meeting, Partially Meeting, or Not Meeting grade-level expectations.\n"
        "- **% M+E** — the share **M**eeting *or* **E**xceeding (the top two levels). The headline number.\n"
        "- **Scaled score** — a 440–560 score where **500 = Meeting**. Compare a subject to its own 500 line, not across subjects.\n"
        "- **Achievement percentile** — LEHS's *rank* against every MA school (1–99). A rank, not a score; 50 = the statewide median.\n"
        "- **SGP (Student Growth Percentile)** — how fast students grew vs. peers who started at the same place. **50 = a typical year.** See the Growth section.\n"
        "- **Participation** — the share of enrolled students who actually tested (% M+E counts non-testers against the school).\n"
        "- **The 2020 gap** — MCAS was waived in spring 2020, so there is no 2020 data point anywhere on this page."
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

# LEHS has Grade-10 MCAS for 2019 and 2021-2025 (no 2020 — MCAS was waived
# that spring). HAS_HISTORY stays as a cheap defensive contract for the trend
# sections; the single-year fallbacks remain in case a future filter ever
# narrows the data again.
N_YEARS = lehs["SY"].nunique()
HAS_HISTORY = N_YEARS >= 3

SUBJECT_MAP = {"ELA": "English Language Arts", "MATH": "Mathematics", "SCI": "Science"}
SUBJECT_COLOR = {"ELA": "#6BAED6", "MATH": "#E08E8E", "SCI": "#74C476"}
# Achievement-level palette — defined once, reused by both distribution charts.
ACH_LEVEL_COLORS = {
    "Exceeding":         "#4CA66B",  # medium green
    "Meeting":           "#A8D5BA",  # light green
    "Partially Meeting": "#F6C177",  # pastel amber
    "Not Meeting":       "#E08E8E",  # pastel coral
}

# ===========================================================================
# 1. HERO — most recent year, all subjects, growth percentile
# ===========================================================================

all_students = lehs[lehs["STU_GRP"] == "All Students"].copy()
latest_year = int(all_students["SY"].max())

st.subheader(f"At a Glance — Grade 10, SY {sy_label(latest_year)}")

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
            delta_color="off",
        )

with c4:
    ela_row = all_students[(all_students["SUBJECT_CODE"] == "ELA") & (all_students["SY"] == latest_year)]
    if not ela_row.empty:
        ach = ela_row.iloc[0].get("ACH_PERCENTILE")
        sgp = ela_row.iloc[0].get("AVG_SGP")
        st.metric(
            "Achievement Percentile (ELA)",
            f"{int(ach)}" if pd.notna(ach) else "—",
            f"SGP (growth): {sgp:.0f}" if pd.notna(sgp) else None,
            delta_color="off",
        )

st.caption(
    "**% M+E** = the share of students Meeting or Exceeding expectations — the "
    "top two of MCAS's four levels. **Achievement percentile** is LEHS's rank "
    "vs. all MA schools — 50 = statewide median, lower = below most schools. "
    "**SGP** is growth vs. academic peers — 50 = average annual growth, higher "
    "= LEHS moves students faster than peer schools."
)

# Plain-language verdict tying the hero tiles together for non-analysts.
_v_ela = all_students[(all_students["SUBJECT_CODE"] == "ELA") & (all_students["SY"] == latest_year)]
_v_state = state[(state["SUBJECT_CODE"] == "ELA") & (state["SY"] == latest_year)]
if not _v_ela.empty and not _v_state.empty:
    _vl = _v_ela.iloc[0]["M_PLUS_E_PCT"]
    _vs = _v_state.iloc[0]["M_PLUS_E_PCT"]
    _vach = _v_ela.iloc[0].get("ACH_PERCENTILE")
    if pd.notna(_vl) and pd.notna(_vs):
        _verdict = (
            f"**In plain terms:** in SY {sy_label(latest_year)}, **{_vl:.0%}** of LEHS "
            f"10th-graders met or exceeded expectations in ELA, "
            f"{'below' if _vl < _vs else 'above'} the statewide **{_vs:.0%}**"
        )
        if pd.notna(_vach):
            _verdict += f", placing LEHS near the **{int(_vach)}th percentile** of MA schools"
        _verdict += ". Subject-by-subject detail is below."
        st.caption(_verdict)

st.divider()

# ===========================================================================
# 2. % MEETING+EXCEEDING — multi-year trend per subject (HAS_HISTORY only)
# ===========================================================================

if HAS_HISTORY:
    st.subheader("% Meeting or Exceeding — Trend by Subject")

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

    st.markdown("**Average Scaled Score Trend**")
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

st.subheader(f"Full Achievement-Level Distribution (SY {sy_label(latest_year)})")
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
    color_discrete_map=ACH_LEVEL_COLORS,
)
fig.update_traces(textposition="inside", textfont=dict(color="#1f2a44", size=11))
fig.update_layout(**DEFAULT_LAYOUT, xaxis_tickformat=".0%", xaxis_title="Share of test-takers",
                   yaxis_title="", barmode="stack")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Distribution evolution over time — per subject
# ---------------------------------------------------------------------------

st.markdown("**How the Distribution Has Shifted Over Time**")
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
        color_discrete_map=ACH_LEVEL_COLORS,
        barmode="stack",
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                       yaxis_title="Share of test-takers", xaxis_title="School Year")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===========================================================================
# 4. BENCHMARKS — LEHS vs Lynn district vs Massachusetts (latest year)
# ===========================================================================

st.subheader(f"LEHS vs. Lynn district vs. Massachusetts — SY {sy_label(latest_year)}")

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
            "Massachusetts": STATE_COLOR,
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
        "Massachusetts statewide average. **The thin lines are a 95% confidence "
        "range — the band the true rate likely sits in. LEHS's is wider because "
        "it rests on far fewer students, so a small gap vs. the state may not be "
        "meaningful.**"
    )
    st.page_link(
        "pages/Lynn_Schools.py",
        label="Compare LEHS to Classical, Tech & the academies → Lynn Schools",
    )

# ---------------------------------------------------------------------------
# LEHS gap to MA over time — multi-year benchmark
# ---------------------------------------------------------------------------

if HAS_HISTORY:
    st.markdown("**LEHS Gap to Massachusetts — Over Time**")
    st.caption(
        "How far LEHS has been from the statewide average each year."
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

st.subheader("Subgroup Performance")
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
    "Female",
    "Male",
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
    "Female":                     GENDER_PALETTE["Female"],
    "Male":                       GENDER_PALETTE["Male"],
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

if HAS_HISTORY:
    st.markdown(f"**% M+E Trend — {SUBJECT_MAP[subject_choice]}, by Student Group**")
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
else:
    # Single-year fallback: horizontal bar of every subgroup's M+E.
    latest_year_sub = sub[sub["SY"] == sub["SY"].max()].copy()
    if not latest_year_sub.empty:
        st.markdown(
            f"**% M+E by Student Group — {SUBJECT_MAP[subject_choice]}, "
            f"SY {sy_label(int(latest_year_sub['SY'].max()))}**"
        )
        bar = latest_year_sub.dropna(subset=["M_PLUS_E_PCT"]).sort_values("M_PLUS_E_PCT").copy()
        bar["label"] = bar["M_PLUS_E_PCT"].apply(lambda x: f"{x:.0%}")
        fig = px.bar(
            bar, x="M_PLUS_E_PCT", y="STU_GRP", orientation="h",
            color="STU_GRP", color_discrete_map=color_map,
            text="label",
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_tickformat=".0%",
            xaxis_title=f"{SUBJECT_MAP[subject_choice]} — % M+E",
            yaxis_title="",
            xaxis_range=[0, max(bar["M_PLUS_E_PCT"].max() * 1.18, 0.1)],
            showlegend=False,
            height=max(360, 32 * len(bar)),
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Gap-to-school-wide evolution over time  (HAS_HISTORY only)
# ---------------------------------------------------------------------------

if HAS_HISTORY:
    st.markdown(f"**Gap to School-Wide Average — Over Time, {SUBJECT_MAP[subject_choice]}**")
    st.caption(
        "Each line = one subgroup's gap to the LEHS school-wide rate, "
        "plotted year by year."
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

st.markdown(f"**Latest-Year Achievement Gap — SY {sy_label(latest_year)}, {SUBJECT_MAP[subject_choice]}**")
st.caption(
    "**Red = this group scores meaningfully below the school-wide rate; green = "
    "meaningfully above; gray = the difference is small enough it could be chance.** "
    "Stars show how confident we are (`*` p<0.05, `**` p<0.01, `***` p<0.001, from a "
    "two-proportion z-test vs. the school-wide rate)."
)
st.page_link("pages/14_Data_Literacy.py", label="New to statistical significance? → Data 101")

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
            return "#C2CCD9"
        return "#E08E8E" if row["Gap"] < 0 else "#74C476"

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
    st.markdown(f"**Subgroup Detail Table — SY {sy_label(latest_year_sub['SY'].max())}, {SUBJECT_MAP[subject_choice]}**")
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
    st.caption(
        "Groups with a small **Tested** count swing widely from year to year — "
        "read those rows with caution. DESE suppresses any group under 10 students."
    )

st.caption(
    "For the full English-Learner journey — proficiency growth, "
    "reclassification, and former-EL outcomes:"
)
st.page_link("pages/3_ELL_Pipeline.py", label="English Learners pipeline →")

st.divider()

# ===========================================================================
# 6. GROWTH — SGP by subject and (where available) by subgroup
# ===========================================================================

st.subheader("🌱 Growth — Student Growth Percentile (SGP)")
st.info(
    "**SGP answers a different question than the scores above.** Achievement is "
    "*where* students are now; growth is *how fast* they're improving. SGP takes "
    "students who scored like this one last year and ranks this student's gain "
    "against them — **50 = a typical year, 70 = faster than 70% of similar "
    "students**. A school can be low on achievement yet near-typical on growth: "
    "students arrived behind but are learning at a normal pace. Watch for that here."
)

sgp_subj = st.radio(
    "Subject",
    options=["ELA", "MATH"],
    format_func=lambda c: SUBJECT_MAP[c],
    horizontal=True,
    key="sgp_subj",
)
st.caption(
    "Grade-10 Science has no growth score in the state's data, so SGP covers "
    "English and Math only."
)

sgp = lehs[(lehs["STU_GRP"] == "All Students") & (lehs["AVG_SGP"].notna())].sort_values("SY").copy()
sgp["label"] = sgp["AVG_SGP"].apply(lambda x: f"{x:.0f}")

if not sgp.empty:
    # --- 3-way SGP trend: LEHS vs Lynn district vs Massachusetts (all 6 years) ---
    def _sgp_series(frame, scope):
        s = frame[(frame["SUBJECT_CODE"] == sgp_subj) & (frame["AVG_SGP"].notna())][["SY", "AVG_SGP"]]
        s = with_year_gaps(s, "AVG_SGP")
        s["Scope"] = scope
        return s

    sgp3 = pd.concat([
        _sgp_series(lehs[lehs["STU_GRP"] == "All Students"], "LEHS"),
        _sgp_series(district, "Lynn district"),
        _sgp_series(state, "Massachusetts"),
    ], ignore_index=True)

    if sgp3["AVG_SGP"].notna().any():
        st.markdown(f"**Growth Over Time — {SUBJECT_MAP[sgp_subj]}: LEHS vs. Lynn vs. Massachusetts**")
        scope_colors = {"LEHS": LEHS_GOLD, "Lynn district": LEHS_NAVY, "Massachusetts": STATE_COLOR}
        fig = px.line(
            sgp3, x="SY", y="AVG_SGP", color="Scope", markers=True,
            color_discrete_map=scope_colors,
        )
        # Real data stays broken at the 2020 NaN (no fake dot) — markers + solid line only on measured years.
        fig.update_traces(connectgaps=False, line=dict(width=3), marker=dict(size=8))
        # Dashed bridge across the COVID gap: connect 2019 -> 2021 per series so the trend reads as
        # continuous, but dashed (not solid) to signal that 2020 was never measured.
        for scope, color in scope_colors.items():
            seg = sgp3[(sgp3["Scope"] == scope) & (sgp3["SY"].isin([2019, 2021]))].sort_values("SY")
            if len(seg) == 2 and seg["AVG_SGP"].notna().all():
                fig.add_trace(go.Scatter(
                    x=seg["SY"], y=seg["AVG_SGP"], mode="lines",
                    line=dict(color=color, width=3, dash="dot"),
                    showlegend=False, hoverinfo="skip",
                ))
        fig.add_hline(y=50, line_dash="dash", line_color="gray",
                      annotation_text="Typical growth (50)", annotation_position="right")
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average SGP",
                          xaxis_title="School Year", yaxis_range=[0, 100])
        # Mark 2020 on the axis with an asterisk (see footnote) — the year stays on the axis but
        # carries no test; pinning every year as a tick keeps the labels from auto-thinning.
        fig.update_xaxes(
            tickmode="array",
            tickvals=list(MCAS_YEARS),
            ticktext=[f"{y}*" if y == 2020 else str(y) for y in MCAS_YEARS],
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "**By definition the typical student grows at 50, so the Massachusetts "
            "line sits near 50 every year.** LEHS (gold) and the Lynn district (navy) "
            "in the 40s means students here grow a little slower than similar "
            "students statewide — but nowhere near as far back as the achievement "
            "gap implies. The dashed segment bridges 2020\\*, when MCAS was waived, so "
            "read it as a connector rather than a measured trend; 2021 used a COVID-era "
            "baseline, so treat that point as directional."
        )
        st.caption(
            "\\*2020 — no MCAS was administered statewide (COVID-19), so no growth "
            "score exists for that year."
        )

    # --- SGP by student group, year by year (heatmap) ---
    _heat_groups = [
        "All Students", "High Needs", "Low Income", "English Learners",
        "Hispanic or Latino", "Female", "Male", "Students with Disabilities",
        "Black or African American", "Asian",
    ]
    _hsub = lehs[
        (lehs["SUBJECT_CODE"] == sgp_subj)
        & (lehs["STU_GRP"].isin(_heat_groups))
        & (lehs["AVG_SGP"].notna())
    ]
    if not _hsub.empty:
        _pivot = _hsub.pivot_table(index="STU_GRP", columns="SY", values="AVG_SGP", aggfunc="mean")
        _pivot = _pivot.reindex(columns=list(MCAS_YEARS))
        _last = _pivot.apply(lambda r: r.dropna().iloc[-1] if r.notna().any() else float("nan"), axis=1)
        _pivot = _pivot.loc[_last.sort_values(ascending=False).index]
        st.markdown(f"**Growth by Student Group, Year by Year — {SUBJECT_MAP[sgp_subj]}**")
        fig = year_heatmap(
            _pivot,
            colorscale=[[0.0, "#E89B9B"], [0.5, "#F2F2F2"], [1.0, "#9CCFC4"]],
            zmid=50, zmin=20, zmax=70, value_fmt="{:.0f}", colorbar_title="SGP",
            height=max(320, 36 * len(_pivot)),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Read **down a column** to compare groups within a year, **across a "
            "row** for a group's path. Coral = below typical growth (50), teal = "
            "above; 2020 is blank (no MCAS). Small groups (Asian, Black ~40 "
            "students) swing on a few kids — read those rows as rough."
        )

    # ---------------------------------------------------------------------------
    # SGP vs. peers — where does LEHS sit in the Gateway HS distribution?
    # Peers report all six years; anchored to the latest year for a clean snapshot.
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
        st.markdown(f"**LEHS vs. Gateway-Peer High Schools — SY {sy_label(peer_year)}**")
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
            color_discrete_map={True: LEHS_GOLD, False: GATEWAY_PEER_COLOR},
            hover_data={"ORG_NAME": True, "AVG_SGP": True, "STU_CNT": True, "is_lehs": False, "Subject": False},
            stripmode="overlay",
        )
        fig.update_traces(marker=dict(size=11, line=dict(width=1, color=LEHS_NAVY)), jitter=0.25)
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
        st.page_link(
            "pages/11_Gateway_Peer_Comparison.py",
            label="See the full Gateway-city peer ranking →",
        )

    # SGP by subgroup — latest year, ELA + Math only (SCI SGP often sparse)
    sgp_sub = lehs[
        (lehs["STU_GRP"].isin(groups_of_interest))
        & (lehs["SUBJECT_CODE"].isin(["ELA", "MATH"]))
        & (lehs["AVG_SGP"].notna())
        & (lehs["SY"] == lehs["SY"].max())
    ].copy()
    if not sgp_sub.empty:
        st.markdown(f"**SGP by Student Group — SY {sy_label(int(sgp_sub['SY'].max()))}**")
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
            text="AVG_SGP",
        )
        fig.update_traces(textposition="outside", cliponaxis=False, texttemplate="%{text:.0f}")
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

st.subheader("Reading These Results — Participation, Cohort Size & Ranking")

# Achievement percentile — trend if HAS_HISTORY, bar tiles otherwise
ach_trend = all_students.dropna(subset=["ACH_PERCENTILE"]).copy()
if not ach_trend.empty:
    st.markdown("**LEHS Achievement Percentile — Rank vs. All MA Schools**")
    st.caption(
        "Percentile rank of LEHS against every MA public school on MCAS. "
        "50 = at the statewide median."
    )
    if HAS_HISTORY:
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
    else:
        latest_ach = ach_trend[ach_trend["SY"] == ach_trend["SY"].max()].copy()
        latest_ach["Subject"] = latest_ach["SUBJECT_CODE"].map(SUBJECT_MAP)
        fig = px.bar(
            latest_ach.sort_values("Subject"),
            x="Subject", y="ACH_PERCENTILE",
            color="SUBJECT_CODE", color_discrete_map=SUBJECT_COLOR,
            text="ACH_PERCENTILE",
        )
        fig.update_traces(textposition="outside", cliponaxis=False, showlegend=False, texttemplate="%{text:.0f}")
        fig.add_hline(y=50, line_dash="dash", line_color="gray",
                      annotation_text="Statewide median", annotation_position="right")
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_title="",
            yaxis_title=f"Achievement percentile (SY {sy_label(int(ach_trend['SY'].max()))})",
            yaxis_range=[0, 100], showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

# Participation rate
st.markdown("**Participation Rate — Who actually takes the test?**")
st.caption("DESE requires 95%+ participation for full accountability credit.")

part = all_students.dropna(subset=["STU_PART_PCT"]).sort_values(["SUBJECT_CODE", "SY"]).copy()
part["label"] = part["STU_PART_PCT"].apply(lambda x: f"{x:.0%}")

if HAS_HISTORY:
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
else:
    pcols = st.columns(3)
    for col, code in zip(pcols, ["ELA", "MATH", "SCI"]):
        prow = part[(part["SUBJECT_CODE"] == code) & (part["SY"] == part["SY"].max())]
        if not prow.empty:
            v = prow.iloc[0]["STU_PART_PCT"]
            with col:
                st.metric(f"{SUBJECT_MAP[code]} participation", f"{v:.0%}",
                          delta="below 95%" if v < 0.95 else "meets 95%",
                          delta_color="inverse" if v < 0.95 else "normal")

# Cohort size
st.markdown("**Grade-10 Cohort Size Tested per Year**")
st.caption(
    "Drives how much subgroup detail you can actually see — DESE suppresses "
    "any subgroup cell with fewer than 10 students."
)

counts = all_students.dropna(subset=["STU_CNT"]).sort_values(["SUBJECT_CODE", "SY"]).copy()
counts["label"] = counts["STU_CNT"].apply(lambda x: f"{int(x):,}")

if HAS_HISTORY:
    fig = px.line(
        counts, x="SY", y="STU_CNT", color="SUBJECT_CODE",
        color_discrete_map=SUBJECT_COLOR, markers=True, text="label",
    )
    fig.update_traces(textposition="top center", textfont=dict(size=9))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students tested",
                       xaxis_title="School Year")
    st.plotly_chart(fig, use_container_width=True)
else:
    ccols = st.columns(3)
    for col, code in zip(ccols, ["ELA", "MATH", "SCI"]):
        crow = counts[(counts["SUBJECT_CODE"] == code) & (counts["SY"] == counts["SY"].max())]
        if not crow.empty:
            n = int(crow.iloc[0]["STU_CNT"])
            with col:
                st.metric(f"{SUBJECT_MAP[code]} tested", f"{n:,}")

st.divider()

# ---------------------------------------------------------------------------
# Grade retention (c8ur-ajfv) — share of students held back / repeating a grade
# ---------------------------------------------------------------------------

st.header("Grade Retention")
st.caption(
    "The share of students held back to repeat a grade — rare in Massachusetts, "
    "but a meaningful signal of where students struggle to keep pace. LEHS vs "
    "Lynn district vs the statewide rate, all students."
)

retention_g = load_dataset("grade_retention")
if retention_g.empty:
    st.info("Grade-retention data is temporarily unavailable.")
else:
    rg = retention_g[retention_g["STU_GRP"] == "All Students"].copy()
    series = {
        "Lynn English": rg[rg["ORG_CODE"] == LEHS_SCHOOL_CODE],
        "Lynn district": rg[(rg["DIST_CODE"] == LYNN_DISTRICT_CODE) & (rg["ORG_TYPE"] == "District")],
        "Massachusetts": rg[rg["ORG_TYPE"] == "State"],
    }
    frames = []
    for name, d in series.items():
        if not d.empty:
            t = d[["SY", "RET_ALL_PCT"]].copy()
            t["Series"] = name
            frames.append(t)
    if frames:
        rdf = pd.concat(frames, ignore_index=True).dropna(subset=["RET_ALL_PCT"]).sort_values("SY")
        fig = px.line(rdf, x="SY", y="RET_ALL_PCT", color="Series", markers=True,
                      color_discrete_map={"Lynn English": LEHS_GOLD,
                                          "Lynn district": LEHS_NAVY,
                                          "Massachusetts": STATE_COLOR})
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".1%",
                          yaxis_title="% of students retained", xaxis_title="School Year")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===========================================================================
# 8. GRADE 9 ON-TRACK — course passing (4sut-78p8)
# ===========================================================================
# Research treats "on-track" freshman year — passing your courses and earning
# enough credits to be promoted to grade 10 — as one of the single strongest
# predictors of on-time graduation. This dataset reports the share of grade-9
# students passing each subject, plus an "All Subjects" rollup per org/year.

st.header("📗 Grade 9 On-Track — Course Passing")
st.caption(
    "Freshman-year course passing is one of the strongest early predictors of "
    "on-time graduation: students who pass their classes and stay on pace in "
    "grade 9 graduate at far higher rates. Each bar is the share of LEHS "
    "grade-9 students passing that subject. **All Subjects** is DESE's combined "
    "on-track rollup. Source: DESE Education-to-Career (Grade 9 Course Passing)."
)

g9 = load_dataset("grade9_passing")
if g9.empty:
    st.info("Grade-9 course-passing data is temporarily unavailable.")
else:
    g9["PASS_PCT"] = pd.to_numeric(g9["PASS_PCT"], errors="coerce")
    g9_lehs_all = g9[
        (g9["ORG_CODE"] == LEHS_SCHOOL_CODE) & (g9["STU_GRP"] == "All Students")
    ].copy()

    if g9_lehs_all.empty:
        st.info("No LEHS grade-9 course-passing rows found.")
    else:
        g9_latest = int(g9_lehs_all["SY"].max())

        # --- (a) Latest-year passing by subject — horizontal bar ---
        st.markdown(f"**Passing Rate by Subject — All Students, SY {sy_label(g9_latest)}**")
        bar = (
            g9_lehs_all[g9_lehs_all["SY"] == g9_latest]
            .dropna(subset=["PASS_PCT"])
            .copy()
        )
        if not bar.empty:
            # Put the All-Subjects rollup at the top, the rest sorted by rate.
            bar["_is_all"] = bar["SUBJ"] == "All Subjects"
            bar = bar.sort_values(["_is_all", "PASS_PCT"], ascending=[True, True])
            bar["label"] = bar["PASS_PCT"].apply(lambda x: f"{x:.0%}")
            bar["color"] = bar["_is_all"].map({True: LEHS_GOLD, False: LEHS_NAVY})
            fig = go.Figure(go.Bar(
                x=bar["PASS_PCT"], y=bar["SUBJ"], orientation="h",
                text=bar["label"], textposition="outside",
                marker_color=bar["color"].tolist(),
                customdata=bar[["G09_CNT"]].values,
                hovertemplate="<b>%{y}</b><br>Passing: %{x:.1%}<br>"
                              "Grade-9 students: %{customdata[0]:,.0f}<extra></extra>",
                cliponaxis=False,
            ))
            fig.update_layout(
                **DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                xaxis_title="Share of grade-9 students passing", yaxis_title="",
                xaxis_range=[0, min(1.08, max(bar["PASS_PCT"].max() * 1.15, 0.1))],
                height=max(320, 42 * len(bar)),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Gold = DESE's combined **All Subjects** on-track rate; navy = "
                "individual subjects. A passing rate well below the others flags "
                "the subject where freshmen most often fall off track."
            )

        # --- (b) Overall on-track trend (All Subjects rollup) vs benchmarks ---
        g9_roll_lehs = g9_lehs_all[g9_lehs_all["SUBJ"] == "All Subjects"]
        if not g9_roll_lehs.empty:
            st.markdown("**Overall On-Track Rate Over Time — All Subjects**")
            g9_dist = g9[
                (g9["DIST_CODE"] == LYNN_DISTRICT_CODE)
                & (g9["ORG_TYPE"] == "District")
                & (g9["STU_GRP"] == "All Students")
                & (g9["SUBJ"] == "All Subjects")
            ]
            g9_state = g9[
                (g9["ORG_TYPE"] == "State")
                & (g9["STU_GRP"] == "All Students")
                & (g9["SUBJ"] == "All Subjects")
            ]
            frames = []
            for name, d in [
                ("Lynn English", g9_roll_lehs),
                ("Lynn district", g9_dist),
                ("Massachusetts", g9_state),
            ]:
                if not d.empty:
                    t = with_year_gaps(d[["SY", "PASS_PCT"]].dropna(subset=["PASS_PCT"]), "PASS_PCT")
                    t["Series"] = name
                    frames.append(t)
            if frames:
                tdf = pd.concat(frames, ignore_index=True)
                fig = px.line(
                    tdf, x="SY", y="PASS_PCT", color="Series", markers=True,
                    color_discrete_map={"Lynn English": LEHS_GOLD,
                                        "Lynn district": LEHS_NAVY,
                                        "Massachusetts": STATE_COLOR},
                )
                fig.update_traces(connectgaps=False)
                fig.update_layout(
                    **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                    yaxis_title="% of grade-9 students passing all subjects",
                    xaxis_title="School Year", yaxis_range=[0, 1.02],
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(
                    "LEHS (gold) vs. the Lynn district and statewide on-track "
                    "rate. The spring-2020 point reflects pandemic-era grading "
                    "(many districts adopted pass/no-pass), so read it as an "
                    "anomaly, not a real spike."
                )

st.divider()

# ===========================================================================
# 9. MCAS ALTERNATE ASSESSMENT — performance levels (ks7h-2kdy)
# ===========================================================================
# The MCAS-Alt is a portfolio assessment for the small number of students with
# the most significant cognitive disabilities, who can't take the standard
# MCAS even with accommodations. Levels: Progressing / Emerging / Awareness /
# Incomplete. The tested group at any one school is tiny (~10 at LEHS), so this
# is indicative context, not a rate to compare precisely.

st.header("🧩 MCAS Alternate Assessment")
st.caption(
    "The MCAS-Alt is a portfolio assessment for the small group of students "
    "with the most significant cognitive disabilities, who take it in place of "
    "the standard MCAS. Each student is rated **Progressing, Emerging, "
    "Awareness,** or **Incomplete**. **The tested group at LEHS is very small "
    "(~10 students), so read this as indicative of how these students are "
    "served — not as a precise rate.** Source: DESE Education-to-Career "
    "(MCAS Alternate Assessment)."
)

alt = load_dataset("mcas_alt")
if alt.empty:
    st.info("MCAS Alternate Assessment data is temporarily unavailable.")
else:
    alt_lehs = alt[alt["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
    if alt_lehs.empty:
        st.info("No LEHS MCAS-Alt rows found.")
    else:
        alt_latest = int(alt_lehs["SY"].max())
        st.markdown(f"**Performance-Level Distribution — SY {sy_label(alt_latest)}**")

        ALT_LEVELS = [
            ("Progressing", "PROG_PCT", "#4CA66B"),
            ("Emerging",    "EMRG_PCT", "#A8D5BA"),
            ("Awareness",   "AWR_PCT",  "#F6C177"),
            ("Incomplete",  "INCOMPLT_PCT", "#E08E8E"),
        ]
        alt_cur = alt_lehs[alt_lehs["SY"] == alt_latest].copy()
        rows = []
        for _, r in alt_cur.iterrows():
            n = pd.to_numeric(r.get("TOT_STU_CNT"), errors="coerce")
            for level, col, _color in ALT_LEVELS:
                rows.append({
                    "Subject": r["SUBJ"],
                    "Level": level,
                    "Pct": pd.to_numeric(r.get(col), errors="coerce"),
                    "n": int(n) if pd.notna(n) else None,
                })
        alt_df = pd.DataFrame(rows).dropna(subset=["Pct"])

        if alt_df.empty:
            st.info("MCAS-Alt performance levels are suppressed for LEHS this year.")
        else:
            alt_df["label"] = alt_df["Pct"].apply(lambda x: f"{x:.0%}" if x >= 0.08 else "")
            fig = px.bar(
                alt_df, y="Subject", x="Pct", color="Level", orientation="h",
                text="label",
                category_orders={
                    "Level": ["Incomplete", "Awareness", "Emerging", "Progressing"],
                    "Subject": sorted(alt_df["Subject"].unique()),
                },
                color_discrete_map={lvl: c for lvl, _col, c in ALT_LEVELS},
                custom_data=["n"],
            )
            fig.update_traces(
                textposition="inside", textfont=dict(color="#1f2a44", size=11),
                hovertemplate="<b>%{y}</b> — %{fullData.name}<br>%{x:.0%}<br>"
                              "tested: n = %{customdata[0]:,}<extra></extra>",
            )
            fig.update_layout(
                **DEFAULT_LAYOUT, xaxis_tickformat=".0%", barmode="stack",
                xaxis_title="Share of tested students", yaxis_title="",
            )
            st.plotly_chart(fig, use_container_width=True)
            _n_note = alt_cur["TOT_STU_CNT"].dropna()
            _n_txt = (f"about {int(_n_note.min())}–{int(_n_note.max())}"
                      if not _n_note.empty else "very few")
            st.caption(
                f"**Progressing** is the top level on the MCAS-Alt. With only "
                f"{_n_txt} students tested per subject, a single student moves "
                "the percentage by ~10 points — treat this as a portrait of a "
                "handful of students, not a school-wide statistic."
            )

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'LEHS Grade-10 MCAS': lehs,
        'Lynn district Grade-10 MCAS': district,
        'Massachusetts Grade-10 MCAS': state,
        'Grade retention': load_dataset("grade_retention"),
        'Grade 9 course passing': load_dataset("grade9_passing"),
        'MCAS Alternate Assessment': load_dataset("mcas_alt"),
    })
except NameError:
    pass
