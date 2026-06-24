"""Section 2 — Academic Performance: MCAS trends, growth, subgroup gaps.

The dashboard's most-viewed section, organized as tabs:

  • Overview — all three subjects side by side: headline rates, the full
    achievement-level snapshot, benchmarks vs. Lynn district & Massachusetts,
    and the gap-to-state trend. The "how is the school doing" view.
  • ELA / Math / Science — one identically-structured deep dive per subject:
    subject hero, trend, distribution-over-time, subgroup gaps, growth (SGP,
    where the state reports it), and the participation/cohort health metrics.

Read MCAS in two halves: **achievement** (where students land) and **growth**
(how fast they improve). MCAS was waived in spring 2020, so no point is 2020.
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
    year_axis,
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
from utils.stats import compare_proportions, wilson_ci_from_pct

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
    "grade-level expectations — in English, Math, and Science. The **Overview** tab "
    "compares all three subjects at a glance; each **subject tab** is the full deep "
    "dive. Read every chart in two halves: **achievement** (where students *land*) "
    "and **growth** (how fast they're *improving*) — different, equally important stories."
)
with st.expander("📖 What the MCAS terms mean"):
    st.markdown(
        "- **Achievement level** — every student lands in one of four bands: "
        "Exceeding, Meeting, Partially Meeting, or Not Meeting grade-level expectations.\n"
        "- **% M+E** — the share **M**eeting *or* **E**xceeding (the top two levels). The headline number.\n"
        "- **Scaled score** — a 440–560 score where **500 = Meeting**. Compare a subject to its own 500 line, not across subjects.\n"
        "- **Achievement percentile** — LEHS's *rank* against every MA school (1–99). A rank, not a score; 50 = the statewide median.\n"
        "- **SGP (Student Growth Percentile)** — how fast students grew vs. peers who started at the same place. **50 = a typical year.** See each subject's Growth section.\n"
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

all_students = lehs[lehs["STU_GRP"] == "All Students"].copy()
latest_year = int(all_students["SY"].max())

# Subgroups + colors — shared by every subject's deep-dive renderer.
GROUPS_OF_INTEREST = [
    "All Students", "Female", "Male", "English Learners", "Former English Learners",
    "Hispanic or Latino", "Black or African American", "Asian", "White",
    "Low Income", "Students with Disabilities", "High Needs",
]
SUBGROUP_COLOR_MAP = {
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


# ===========================================================================
# OVERVIEW — all three subjects side by side
# ===========================================================================

def render_overview() -> None:
    # --- Hero tiles ---
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
            _verdict += ". Open a subject tab above for the full deep dive."
            st.caption(_verdict)

    st.divider()

    # --- % M+E trend by subject ---
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
        st.plotly_chart(year_axis(fig), use_container_width=True)
        st.caption(
            "MCAS was waived in spring 2020 and modified in 2021 — those years "
            "show fewer data points and shouldn't be read as a real trend break."
        )
        st.divider()

    # --- Full achievement-level snapshot (all subjects) ---
    st.subheader(f"Full Achievement-Level Distribution (SY {sy_label(latest_year)})")
    st.caption(
        "MCAS classifies every student into one of four levels: **E**xceeding, "
        "**M**eeting, **P**artially **M**eeting, or **N**ot **M**eeting expectations. "
        "Headline '% M+E' only shows the top two — this view shows where everyone falls. "
        "Each subject tab shows how its distribution has shifted year by year."
    )
    latest = all_students[all_students["SY"] == latest_year]
    dist_rows = []
    for _, row in latest.iterrows():
        for level, col in [
            ("Exceeding", "E_PCT"), ("Meeting", "M_PCT"),
            ("Partially Meeting", "PM_PCT"), ("Not Meeting", "NM_PCT"),
        ]:
            dist_rows.append({
                "Subject": SUBJECT_MAP.get(row["SUBJECT_CODE"], row["SUBJECT_CODE"]),
                "Level": level, "Pct": row[col],
            })
    dist_df = pd.DataFrame(dist_rows).dropna(subset=["Pct"])
    dist_df["label"] = dist_df["Pct"].apply(lambda x: f"{x:.0%}" if x >= 0.05 else "")
    fig = px.bar(
        dist_df, y="Subject", x="Pct", color="Level", orientation="h", text="label",
        category_orders={"Level": ["Not Meeting", "Partially Meeting", "Meeting", "Exceeding"]},
        color_discrete_map=ACH_LEVEL_COLORS,
    )
    fig.update_traces(textposition="inside", textfont=dict(color="#1f2a44", size=11))
    fig.update_layout(**DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                      xaxis_title="Share of test-takers", yaxis_title="", barmode="stack")
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

    # --- Benchmarks: LEHS vs Lynn vs MA (all subjects) ---
    st.subheader(f"LEHS vs. Lynn district vs. Massachusetts — SY {sy_label(latest_year)}")
    bench_rows = []
    for code in ["ELA", "MATH", "SCI"]:
        lehs_row = latest[latest["SUBJECT_CODE"] == code]
        dist_row = district[(district["SUBJECT_CODE"] == code) & (district["SY"] == latest_year)]
        state_row = state[(state["SUBJECT_CODE"] == code) & (state["SY"] == latest_year)]
        for label, row_df in [("LEHS", lehs_row), ("Lynn district", dist_row), ("Massachusetts", state_row)]:
            if row_df.empty:
                continue
            r = row_df.iloc[0]
            pct = r["M_PLUS_E_PCT"]
            n = r.get("STU_CNT")
            lo, hi = wilson_ci_from_pct(pct, n)
            bench_rows.append({
                "Subject": SUBJECT_MAP[code], "Scope": label, "Pct": pct,
                "n": int(n) if pd.notna(n) else None, "ci_lo": lo, "ci_hi": hi,
            })
    if bench_rows:
        bench_df = pd.DataFrame(bench_rows).dropna(subset=["Pct"])
        bench_df["label"] = bench_df["Pct"].apply(lambda x: f"{x:.0%}")
        bench_df["err_minus"] = (bench_df["Pct"] - bench_df["ci_lo"]).clip(lower=0)
        bench_df["err_plus"] = (bench_df["ci_hi"] - bench_df["Pct"]).clip(lower=0)
        fig = px.bar(
            bench_df, x="Subject", y="Pct", color="Scope", barmode="group", text="label",
            category_orders={"Scope": ["LEHS", "Lynn district", "Massachusetts"]},
            color_discrete_map={"LEHS": LEHS_GOLD, "Lynn district": LEHS_NAVY, "Massachusetts": STATE_COLOR},
            error_y="err_plus", error_y_minus="err_minus", custom_data=["n"],
        )
        fig.update_traces(
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.1%}<br>n = %{customdata[0]:,}<extra></extra>",
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                          yaxis_title="% Meeting + Exceeding", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Three natural benchmarks: LEHS, the Lynn district aggregate, and the "
            "Massachusetts statewide average. **The thin lines are a 95% confidence "
            "range — the band the true rate likely sits in. LEHS's is wider because "
            "it rests on far fewer students, so a small gap vs. the state may not be "
            "meaningful.**"
        )
        st.page_link("pages/Lynn_Schools.py",
                     label="Compare LEHS to Classical, Tech & the academies → Lynn Schools")

    # --- LEHS gap to MA over time (all subjects) ---
    if HAS_HISTORY:
        st.markdown("**LEHS Gap to Massachusetts — Over Time**")
        st.caption("How far LEHS has been from the statewide average each year, by subject.")
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
                    color_discrete_map={SUBJECT_MAP[c]: SUBJECT_COLOR[c] for c in ["ELA", "MATH", "SCI"]},
                    markers=True,
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray",
                              annotation_text="MA average (0)", annotation_position="right")
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="+.0%",
                                  yaxis_title="LEHS minus MA (percentage points)",
                                  xaxis_title="School Year")
                st.plotly_chart(year_axis(fig), use_container_width=True)

    st.info(
        "**Want the detail?** Each subject tab above carries the same structure: "
        "subject hero → distribution over time → subgroup gaps → growth (SGP) → "
        "participation & cohort health."
    )


# ===========================================================================
# SUBJECT DEEP DIVE — identical structure for ELA / Math / Science
# ===========================================================================

def render_subject(code: str) -> None:
    subj = SUBJECT_MAP[code]
    has_sgp = code in ("ELA", "MATH")
    subj_all = all_students[all_students["SUBJECT_CODE"] == code].sort_values("SY").copy()
    if subj_all.empty:
        st.info(f"No Grade-10 {subj} data for LEHS.")
        return
    s_latest_year = int(subj_all["SY"].max())
    latest_row = subj_all[subj_all["SY"] == s_latest_year].iloc[0]

    # --- Subject hero ---
    st.subheader(f"{subj} — Grade 10, SY {sy_label(s_latest_year)}")
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        v = latest_row["M_PLUS_E_PCT"]
        st.metric("% Meeting + Exceeding", f"{v:.0%}" if pd.notna(v) else "—")
    with h2:
        sc = latest_row.get("AVG_SCALED_SCORE")
        st.metric("Avg scaled score", f"{sc:.0f}" if pd.notna(sc) else "—",
                  help="440–560 scale; 500 = Meeting Expectations.")
    with h3:
        ach = latest_row.get("ACH_PERCENTILE")
        st.metric("Achievement percentile", f"{int(ach)}" if pd.notna(ach) else "—",
                  help="Rank vs. every MA school; 50 = statewide median.")
    with h4:
        if has_sgp:
            sg = latest_row.get("AVG_SGP")
            st.metric("Growth (SGP)", f"{sg:.0f}" if pd.notna(sg) else "—",
                      help="50 = a typical year of growth vs. academic peers.")
        else:
            st.metric("Growth (SGP)", "—", help="Grade-10 Science has no state growth score.")
    n = latest_row.get("STU_CNT")
    if pd.notna(n):
        st.caption(f"Based on **{int(n):,}** Grade-10 students tested in SY {sy_label(s_latest_year)}.")

    # --- Trend: % M+E and average scaled score ---
    if HAS_HISTORY:
        st.markdown(f"**% Meeting or Exceeding — {subj}, Over Time**")
        trend = subj_all.copy()
        trend["label"] = trend["M_PLUS_E_PCT"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "")
        fig = px.line(trend, x="SY", y="M_PLUS_E_PCT", markers=True, text="label")
        fig.update_traces(line=dict(color=SUBJECT_COLOR[code], width=3),
                          marker=dict(size=8), textposition="top center", textfont=dict(size=10))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                          yaxis_title="% Meeting or Exceeding", xaxis_title="School Year")
        st.plotly_chart(year_axis(fig), use_container_width=True)

        st.markdown(f"**Average Scaled Score — {subj}, Over Time**")
        st.caption("Scaled scores run **440–560**, with **500 = Meeting Expectations**.")
        scaled_trend = subj_all.dropna(subset=["AVG_SCALED_SCORE"]).copy()
        if not scaled_trend.empty:
            scaled_trend["label"] = scaled_trend["AVG_SCALED_SCORE"].apply(lambda x: f"{x:.0f}")
            fig = px.line(scaled_trend, x="SY", y="AVG_SCALED_SCORE", markers=True, text="label")
            fig.update_traces(line=dict(color=SUBJECT_COLOR[code], width=3),
                              marker=dict(size=8), textposition="top center", textfont=dict(size=10))
            fig.add_hline(y=500, line_dash="dash", line_color="gray",
                          annotation_text="Meets Expectations (500)", annotation_position="right")
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average scaled score",
                              xaxis_title="School Year")
            st.plotly_chart(year_axis(fig), use_container_width=True)

    st.divider()

    # --- Distribution over time ---
    st.markdown(f"**Achievement-Level Distribution Over Time — {subj}**")
    st.caption(
        "All four levels, plotted year by year. Watch the **Not Meeting** band — "
        "shrinking it is the school's hardest-and-most-meaningful challenge."
    )
    dist_yearly = subj_all.dropna(subset=["E_PCT", "M_PCT", "PM_PCT", "NM_PCT"]).sort_values("SY")
    if not dist_yearly.empty:
        dist_long = dist_yearly.melt(
            id_vars="SY", value_vars=["E_PCT", "M_PCT", "PM_PCT", "NM_PCT"],
            var_name="Level", value_name="Pct",
        )
        dist_long["Level"] = dist_long["Level"].map(
            {"E_PCT": "Exceeding", "M_PCT": "Meeting", "PM_PCT": "Partially Meeting", "NM_PCT": "Not Meeting"}
        )
        fig = px.bar(
            dist_long, x="SY", y="Pct", color="Level", barmode="stack",
            category_orders={"Level": ["Not Meeting", "Partially Meeting", "Meeting", "Exceeding"]},
            color_discrete_map=ACH_LEVEL_COLORS,
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                          yaxis_title="Share of test-takers", xaxis_title="School Year")
        st.plotly_chart(year_axis(fig), use_container_width=True)

    st.divider()

    # --- Subgroup performance ---
    st.markdown(f"**Subgroup Performance — {subj}**")
    st.caption(
        "Where the headline number hides everything: how each student group is doing, "
        "how the gaps to school-wide have moved, and where the disparities are "
        "statistically real vs. small-cohort noise."
    )
    sub = lehs[(lehs["SUBJECT_CODE"] == code) & (lehs["STU_GRP"].isin(GROUPS_OF_INTEREST))].sort_values("SY").copy()
    sub["label"] = ""
    if not sub.empty:
        latest_sub_idx = sub.sort_values("SY").groupby("STU_GRP").tail(1).index
        sub.loc[latest_sub_idx, "label"] = sub.loc[latest_sub_idx, "M_PLUS_E_PCT"].apply(
            lambda x: f"{x:.0%}" if pd.notna(x) else ""
        )

    if HAS_HISTORY:
        st.markdown(f"*% M+E Trend by Student Group*")
        fig = px.line(sub, x="SY", y="M_PLUS_E_PCT", color="STU_GRP", markers=True,
                      color_discrete_map=SUBGROUP_COLOR_MAP, text="label")
        fig.update_traces(textposition="middle right", textfont=dict(size=10))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                          yaxis_title=f"{subj} — % M+E", xaxis_title="School Year")
        st.plotly_chart(year_axis(fig), use_container_width=True)
    else:
        latest_year_sub = sub[sub["SY"] == sub["SY"].max()].copy()
        if not latest_year_sub.empty:
            bar = latest_year_sub.dropna(subset=["M_PLUS_E_PCT"]).sort_values("M_PLUS_E_PCT").copy()
            bar["label"] = bar["M_PLUS_E_PCT"].apply(lambda x: f"{x:.0%}")
            fig = px.bar(bar, x="M_PLUS_E_PCT", y="STU_GRP", orientation="h",
                         color="STU_GRP", color_discrete_map=SUBGROUP_COLOR_MAP, text="label")
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(**DEFAULT_LAYOUT, xaxis_tickformat=".0%",
                              xaxis_title=f"{subj} — % M+E", yaxis_title="",
                              xaxis_range=[0, max(bar["M_PLUS_E_PCT"].max() * 1.18, 0.1)],
                              showlegend=False, height=max(360, 32 * len(bar)))
            st.plotly_chart(fig, use_container_width=True)

    # Gap to school-wide over time
    if HAS_HISTORY and not sub.empty:
        st.markdown("*Gap to School-Wide Average — Over Time*")
        st.caption("Each line = one subgroup's gap to the LEHS school-wide rate, year by year.")
        all_by_year = (sub[sub["STU_GRP"] == "All Students"][["SY", "M_PLUS_E_PCT"]]
                       .rename(columns={"M_PLUS_E_PCT": "all_pct"}))
        gap_long = (sub[sub["STU_GRP"] != "All Students"][["SY", "STU_GRP", "M_PLUS_E_PCT"]]
                    .merge(all_by_year, on="SY", how="inner"))
        gap_long["gap"] = gap_long["M_PLUS_E_PCT"] - gap_long["all_pct"]
        gap_long = gap_long.dropna(subset=["gap"])
        if not gap_long.empty:
            fig = px.line(gap_long.sort_values("SY"), x="SY", y="gap", color="STU_GRP",
                          markers=True, color_discrete_map=SUBGROUP_COLOR_MAP)
            fig.add_hline(y=0, line_dash="dash", line_color="gray",
                          annotation_text="School-wide (0 gap)", annotation_position="right")
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="+.0%",
                              yaxis_title="Gap to school-wide (pp)", xaxis_title="School Year")
            st.plotly_chart(year_axis(fig), use_container_width=True)

    # Latest-year gap with significance
    st.markdown(f"*Latest-Year Achievement Gap — SY {sy_label(s_latest_year)}*")
    st.caption(
        "**Red = this group scores meaningfully below the school-wide rate; green = "
        "meaningfully above; gray = the difference could be chance.** Stars show "
        "confidence (`*` p<0.05, `**` p<0.01, `***` p<0.001, two-proportion z-test)."
    )
    st.page_link("pages/14_Data_Literacy.py", label="New to statistical significance? → Data 101")
    latest_sub = sub[sub["SY"] == sub["SY"].max()].copy() if not sub.empty else pd.DataFrame()
    if not latest_sub.empty and "All Students" in latest_sub["STU_GRP"].values:
        all_row = latest_sub[latest_sub["STU_GRP"] == "All Students"].iloc[0]
        all_value = all_row["M_PLUS_E_PCT"]
        all_n = all_row.get("STU_CNT")
        all_k = int(round(all_value * all_n)) if pd.notna(all_value) and pd.notna(all_n) else None
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
            lambda r: pd.Series(_gap_stats(r)), axis=1)
        gap_data = gap_data.sort_values("Gap")
        gap_data["label"] = gap_data.apply(
            lambda r: f"{r['Gap']*100:+.1f} pts {r['stars']}" if pd.notna(r["Gap"]) else "", axis=1)

        def _bar_color(row):
            if not row["significant"]:
                return "#C2CCD9"
            return "#E08E8E" if row["Gap"] < 0 else "#74C476"

        colors = gap_data.apply(_bar_color, axis=1).tolist()
        fig = go.Figure(go.Bar(
            y=gap_data["STU_GRP"], x=gap_data["Gap"] * 100, orientation="h",
            text=gap_data["label"], textposition="outside", marker_color=colors,
            customdata=gap_data[["STU_CNT", "effect"]].values,
            hovertemplate="<b>%{y}</b><br>Gap: %{x:.1f} pts<br>n = %{customdata[0]:,}<br>Effect size: %{customdata[1]}<extra></extra>",
            cliponaxis=False,
        ))
        fig.update_layout(**DEFAULT_LAYOUT,
                          xaxis_title=f"Percentage point gap vs. school-wide ({all_value:.0%})")
        st.plotly_chart(fig, use_container_width=True)

    # Subgroup detail table
    if not sub.empty:
        latest_year_sub = sub[sub["SY"] == sub["SY"].max()].copy()
        if not latest_year_sub.empty:
            st.markdown(f"*Subgroup Detail Table — SY {sy_label(latest_year_sub['SY'].max())}*")
            table = latest_year_sub[[
                "STU_GRP", "STU_CNT", "M_PLUS_E_PCT", "E_PCT", "M_PCT", "PM_PCT", "NM_PCT", "AVG_SCALED_SCORE"
            ]].copy()
            table = table.rename(columns={
                "STU_GRP": "Student group", "STU_CNT": "Tested", "M_PLUS_E_PCT": "% M+E",
                "E_PCT": "% Exceeding", "M_PCT": "% Meeting", "PM_PCT": "% Partial",
                "NM_PCT": "% Not Meet", "AVG_SCALED_SCORE": "Avg score",
            })
            table["Tested"] = table["Tested"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
            for c in ["% M+E", "% Exceeding", "% Meeting", "% Partial", "% Not Meet"]:
                table[c] = table[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
            table["Avg score"] = table["Avg score"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
            st.dataframe(table.sort_values("Student group"), use_container_width=True, hide_index=True)
            st.caption("DESE suppresses any group under 10 students; small-count rows swing widely year to year.")

    if code == "ELA":
        st.caption("For the full English-Learner journey — proficiency growth, reclassification, and former-EL outcomes:")
        st.page_link("pages/3_ELL_Pipeline.py", label="English Learners pipeline →")

    st.divider()

    # --- Growth (SGP) ---
    st.markdown(f"**🌱 Growth — Student Growth Percentile (SGP), {subj}**")
    if not has_sgp:
        st.info(
            "Grade-10 **Science** has no Student Growth Percentile in the state's "
            "data — SGP is reported for ELA and Math only. See those tabs for growth."
        )
    else:
        st.info(
            "**SGP answers a different question than the scores above.** Achievement is "
            "*where* students are now; growth is *how fast* they're improving. **50 = a "
            "typical year, 70 = faster than 70% of similar students.** A school can be "
            "low on achievement yet near-typical on growth — students arrived behind but "
            "are learning at a normal pace."
        )
        sgp = lehs[(lehs["STU_GRP"] == "All Students") & (lehs["AVG_SGP"].notna())].sort_values("SY").copy()
        if sgp.empty:
            st.caption("SGP data not available for LEHS in this dataset.")
        else:
            # 3-way SGP trend
            def _sgp_series(frame, scope):
                s = frame[(frame["SUBJECT_CODE"] == code) & (frame["AVG_SGP"].notna())][["SY", "AVG_SGP"]]
                s = with_year_gaps(s, "AVG_SGP")
                s["Scope"] = scope
                return s

            sgp3 = pd.concat([
                _sgp_series(lehs[lehs["STU_GRP"] == "All Students"], "LEHS"),
                _sgp_series(district, "Lynn district"),
                _sgp_series(state, "Massachusetts"),
            ], ignore_index=True)
            if sgp3["AVG_SGP"].notna().any():
                st.markdown(f"*Growth Over Time — LEHS vs. Lynn vs. Massachusetts*")
                fig = px.line(sgp3, x="SY", y="AVG_SGP", color="Scope", markers=True,
                              color_discrete_map={"LEHS": LEHS_GOLD, "Lynn district": LEHS_NAVY, "Massachusetts": STATE_COLOR})
                # connectgaps=True bridges the 2020 COVID gap so the line runs
                # 2019→2021 instead of visibly breaking (per the 618 audit).
                fig.update_traces(connectgaps=True, line=dict(width=3), marker=dict(size=8))
                fig.add_hline(y=50, line_dash="dash", line_color="gray",
                              annotation_text="Typical growth (50)", annotation_position="right")
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Average SGP",
                                  xaxis_title="School Year", yaxis_range=[0, 100])
                st.plotly_chart(year_axis(fig), use_container_width=True)
                st.caption(
                    "**The typical student grows at 50, so the Massachusetts line sits "
                    "near 50 every year.** The lines break at 2020 (MCAS waived); 2021 "
                    "used a COVID-era baseline, so read that point as directional."
                )

            # SGP by student group heatmap
            _heat_groups = [
                "All Students", "High Needs", "Low Income", "English Learners",
                "Hispanic or Latino", "Female", "Male", "Students with Disabilities",
                "Black or African American", "Asian",
            ]
            _hsub = lehs[(lehs["SUBJECT_CODE"] == code) & (lehs["STU_GRP"].isin(_heat_groups)) & (lehs["AVG_SGP"].notna())]
            if not _hsub.empty:
                _pivot = _hsub.pivot_table(index="STU_GRP", columns="SY", values="AVG_SGP", aggfunc="mean")
                _pivot = _pivot.reindex(columns=list(MCAS_YEARS))
                _last = _pivot.apply(lambda r: r.dropna().iloc[-1] if r.notna().any() else float("nan"), axis=1)
                _pivot = _pivot.loc[_last.sort_values(ascending=False).index]
                st.markdown(f"*Growth by Student Group, Year by Year*")
                fig = year_heatmap(
                    _pivot, colorscale=[[0.0, "#E89B9B"], [0.5, "#F2F2F2"], [1.0, "#9CCFC4"]],
                    zmid=50, zmin=20, zmax=70, value_fmt="{:.0f}", colorbar_title="SGP",
                    height=max(320, 36 * len(_pivot)),
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(
                    "Read **down a column** to compare groups within a year, **across a "
                    "row** for a group's path. Coral = below typical growth (50), teal = "
                    "above; 2020 is blank. Small groups (Asian, Black ~40 students) swing "
                    "on a few kids — read those rows as rough."
                )

            # SGP vs Gateway peers (this subject)
            peer_sgp = mcas[
                (mcas["TEST_GRADE"] == "10") & (mcas["STU_GRP"] == "All Students")
                & (mcas["AVG_SGP"].notna()) & (mcas["ORG_TYPE"] == "School")
                & (mcas["SUBJECT_CODE"] == code)
            ].copy()
            if not peer_sgp.empty:
                peer_year = int(peer_sgp["SY"].max())
                peer_sgp = peer_sgp[peer_sgp["SY"] == peer_year].copy()
                st.markdown(f"*LEHS vs. Gateway-Peer High Schools — SY {sy_label(peer_year)}*")
                st.caption(
                    "Each dot is one comprehensive high school in a Massachusetts Gateway "
                    "city. LEHS is highlighted in gold; the dashed line marks the statewide "
                    "median (50). Faster growth = right."
                )
                peer_sgp["is_lehs"] = peer_sgp["ORG_CODE"] == LEHS_SCHOOL_CODE
                peer_sgp["Subject"] = subj
                fig = px.strip(
                    peer_sgp, x="AVG_SGP", y="Subject", color="is_lehs",
                    color_discrete_map={True: LEHS_GOLD, False: GATEWAY_PEER_COLOR},
                    hover_data={"ORG_NAME": True, "AVG_SGP": True, "STU_CNT": True, "is_lehs": False, "Subject": False},
                    stripmode="overlay",
                )
                fig.update_traces(marker=dict(size=11, line=dict(width=1, color=LEHS_NAVY)), jitter=0.25)
                lehs_dots = peer_sgp[peer_sgp["is_lehs"]]
                if not lehs_dots.empty:
                    fig.add_trace(go.Scatter(
                        x=lehs_dots["AVG_SGP"], y=lehs_dots["Subject"], mode="markers+text",
                        marker=dict(size=18, color=LEHS_GOLD, line=dict(width=2, color=LEHS_NAVY)),
                        text=["LEHS"] * len(lehs_dots), textposition="top center",
                        textfont=dict(color=LEHS_NAVY, size=11), hoverinfo="skip", showlegend=False,
                    ))
                fig.add_vline(x=50, line_dash="dash", line_color="gray",
                              annotation_text="State median", annotation_position="top")
                fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Average SGP",
                                  yaxis_title="", xaxis_range=[0, 100], showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                st.page_link("pages/11_Gateway_Peer_Comparison.py",
                             label="See the full Gateway-city peer ranking →")

            # SGP by subgroup (this subject), latest year
            sgp_sub = lehs[
                (lehs["STU_GRP"].isin(GROUPS_OF_INTEREST)) & (lehs["SUBJECT_CODE"] == code)
                & (lehs["AVG_SGP"].notna()) & (lehs["SY"] == lehs["SY"].max())
            ].copy()
            if not sgp_sub.empty:
                st.markdown(f"*SGP by Student Group — SY {sy_label(int(sgp_sub['SY'].max()))}*")
                st.caption(
                    "Growth percentile by subgroup. **All Students** is the reference; "
                    "bars at 50 indicate that group grew at the same rate as their academic "
                    "peers statewide."
                )
                fig = px.bar(sgp_sub.sort_values("AVG_SGP"), x="AVG_SGP", y="STU_GRP",
                             orientation="h", text="AVG_SGP", color_discrete_sequence=[SUBJECT_COLOR[code]])
                fig.update_traces(textposition="outside", cliponaxis=False, texttemplate="%{text:.0f}")
                fig.add_vline(x=50, line_dash="dash", line_color="gray",
                              annotation_text="Statewide median", annotation_position="top right")
                fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Average SGP", yaxis_title="",
                                  xaxis_range=[0, 100], height=max(360, 28 * sgp_sub["STU_GRP"].nunique()))
                st.plotly_chart(fig, use_container_width=True)

        st.caption(sgp_methodology_note())

    st.divider()

    # --- Health metrics (this subject) ---
    st.markdown(f"**Reading These Results — Participation, Cohort Size & Ranking ({subj})**")

    ach_trend = subj_all.dropna(subset=["ACH_PERCENTILE"]).copy()
    if not ach_trend.empty:
        st.markdown("*Achievement Percentile — Rank vs. All MA Schools*")
        if HAS_HISTORY:
            ach_trend["label"] = ach_trend["ACH_PERCENTILE"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "")
            fig = px.line(ach_trend.sort_values("SY"), x="SY", y="ACH_PERCENTILE", markers=True, text="label")
            fig.update_traces(line=dict(color=SUBJECT_COLOR[code], width=3), marker=dict(size=8),
                              textposition="top center", textfont=dict(size=10))
            fig.add_hline(y=50, line_dash="dash", line_color="gray",
                          annotation_text="Statewide median", annotation_position="right")
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Achievement percentile",
                              xaxis_title="School Year", yaxis_range=[0, 100])
            st.plotly_chart(year_axis(fig), use_container_width=True)
        else:
            v = ach_trend[ach_trend["SY"] == ach_trend["SY"].max()].iloc[0]["ACH_PERCENTILE"]
            st.metric(f"Achievement percentile (SY {sy_label(int(ach_trend['SY'].max()))})",
                      f"{int(v)}" if pd.notna(v) else "—")

    part = subj_all.dropna(subset=["STU_PART_PCT"]).sort_values("SY").copy()
    if not part.empty:
        st.markdown("*Participation Rate — Who actually takes the test?*")
        st.caption("DESE requires 95%+ participation for full accountability credit.")
        if HAS_HISTORY:
            part["label"] = part["STU_PART_PCT"].apply(lambda x: f"{x:.0%}")
            fig = px.line(part, x="SY", y="STU_PART_PCT", markers=True, text="label")
            fig.update_traces(line=dict(color=SUBJECT_COLOR[code], width=3), marker=dict(size=8),
                              textposition="bottom center", textfont=dict(size=10))
            fig.add_hline(y=0.95, line_dash="dash", line_color="#D32F2F",
                          annotation_text="DESE threshold (95%)", annotation_position="right")
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Participation rate",
                              xaxis_title="School Year", yaxis_range=[0.5, 1.05])
            st.plotly_chart(year_axis(fig), use_container_width=True)
        else:
            v = part[part["SY"] == part["SY"].max()].iloc[0]["STU_PART_PCT"]
            st.metric(f"{subj} participation", f"{v:.0%}",
                      delta="below 95%" if v < 0.95 else "meets 95%",
                      delta_color="inverse" if v < 0.95 else "normal")

    counts = subj_all.dropna(subset=["STU_CNT"]).sort_values("SY").copy()
    if not counts.empty:
        st.markdown("*Grade-10 Cohort Size Tested per Year*")
        st.caption("Drives how much subgroup detail you can see — DESE suppresses any subgroup cell under 10 students.")
        if HAS_HISTORY:
            counts["label"] = counts["STU_CNT"].apply(lambda x: f"{int(x):,}")
            fig = px.line(counts, x="SY", y="STU_CNT", markers=True, text="label")
            fig.update_traces(line=dict(color=SUBJECT_COLOR[code], width=3), marker=dict(size=8),
                              textposition="top center", textfont=dict(size=9))
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students tested", xaxis_title="School Year")
            st.plotly_chart(year_axis(fig), use_container_width=True)
        else:
            st.metric(f"{subj} tested", f"{int(counts[counts['SY'] == counts['SY'].max()].iloc[0]['STU_CNT']):,}")


# ===========================================================================
# TABS
# ===========================================================================

tab_over, tab_ela, tab_math, tab_sci = st.tabs(["Overview", "ELA", "Math", "Science"])
with tab_over:
    render_overview()
with tab_ela:
    render_subject("ELA")
with tab_math:
    render_subject("MATH")
with tab_sci:
    render_subject("SCI")

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'LEHS Grade-10 MCAS': lehs,
        'Lynn district Grade-10 MCAS': district,
        'Massachusetts Grade-10 MCAS': state,
    })
except NameError:
    pass
