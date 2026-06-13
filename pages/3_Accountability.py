"""
Section 18 — State Accountability.

Breaks down the one thing a principal or district leader checks first: the DESE
accountability determination. The thin headline (classification + percentile)
lives in accountability.parquet; this page opens the layer underneath it —
how the score is built, where LEHS sits statewide, what next year's targets
require, the long-run trend behind each indicator, and how LEHS compares to its
district, the state, and its peers.

All data is school-level aggregate (DESE's published accountability workbooks).
No student records.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    csv_download,
    data_downloads_panel,
    with_year_gaps,
)
from utils.constants import (
    ACCT_GROUP_TO_STU_GRP,
    GATEWAY_PEER_COLOR,
    LEHS_GOLD,
    LEHS_NAVY,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    LYNN_SIBLING_COLOR,
    LYNN_SIBLING_HS,
    STATE_COLOR,
)
from utils.data_loader import load_dataset
from utils.interpret import (
    chronic_absenteeism_methodology_note,
    sgp_methodology_note,
    sy_label,
)
from utils.url_state import qp_selectbox

st.set_page_config(page_title="Accountability | LEHS", page_icon="🏛️", layout="wide")
sidebar_attribution()

MAX_POINTS = 4  # DESE scores each indicator 0-4.
STATE_CODE = "00000000"

# Scopes shown on the long-view trend lines, with house colors.
_SCOPE = {LEHS_SCHOOL_CODE: "Lynn English", LYNN_DISTRICT_CODE: "Lynn District",
          STATE_CODE: "Massachusetts"}
_SCOPE_COLORS = {"Lynn English": LEHS_GOLD, "Lynn District": LEHS_NAVY,
                 "Massachusetts": STATE_COLOR}

# Per-indicator weights DESE applies (high school), for the "how the score is
# built" explainer. Lowest-Performing has no HS-completion or ELP weight.
ACCT_WEIGHTS_HS = {
    "All Students":      {"Achievement": 40, "Growth": 20, "HS completion": 20,
                          "EL progress": 10, "Additional": 10},
    "Lowest Performing": {"Achievement": 67.5, "Growth": 22.5, "Additional": 10},
}

UNIT_LABEL = {"pct": "%", "sgp": "mean SGP", "scaled_score": "scaled score"}


def _fmt_val(v, unit) -> str:
    if pd.isna(v):
        return "—"
    return f"{v:.1f}%" if unit == "pct" else f"{v:.1f}"


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

summary = load_dataset("accountability_summary")
indicators = load_dataset("accountability_indicators")
targets = load_dataset("accountability_targets")
pctl = load_dataset("accountability_percentiles")
bench = load_dataset("accountability_benchmarks")

st.title("State Accountability")
st.markdown(
    "Every Massachusetts school gets an annual **accountability determination** "
    "from DESE — a classification, a 1–99 percentile, and a *criterion-referenced "
    "target percentage* that rolls up roughly a dozen indicators. This page breaks "
    "that down to the indicator-and-student-group level: how the score is built, "
    "where LEHS sits statewide, what next year's targets require, the long-run "
    "trend behind each indicator, and how LEHS compares to its district and the state."
)

if summary.empty or indicators.empty:
    st.info(
        "Detailed accountability data isn't built yet. Run "
        "`python scripts/19_download_accountability_detail.py` then "
        "`python scripts/16_process_dese_profiles.py`."
    )
    st.stop()

lehs = summary[summary["ORG_CODE"] == LEHS_SCHOOL_CODE]
lehs_ind = indicators[indicators["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
if lehs.empty or lehs_ind.empty:
    st.info("No accountability rows for Lynn English High in the current build.")
    st.stop()

row = lehs.iloc[-1]
sy = int(row["SY"])
sy_lbl = sy_label(sy)
ind_order = list(dict.fromkeys(lehs_ind["INDICATOR"]))

# ---------------------------------------------------------------------------
# 2. Headline determination
# ---------------------------------------------------------------------------

st.header(f"LEHS determination — SY {sy_lbl}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Classification", str(row["CLASSIFICATION"]))
c2.metric("Accountability percentile (1–99)", f"{row['PERCENTILE']:.0f}")
c3.metric(
    f"Annual target progress (SY {sy_lbl})",
    f"{row['CRIT_CURRENT']:.0f}%",
    delta=(None if pd.isna(row.get("CRIT_PRIOR"))
           else f"{row['CRIT_CURRENT'] - row['CRIT_PRIOR']:.0f} pp vs {sy - 1}"),
    delta_color="normal",
)
c4.metric("Cumulative target progress", f"{row['CRIT_CUMULATIVE']:.0f}%")

fed = str(row.get("FEDERAL_DESIGNATION") or "").strip()
low_groups_raw = str(row.get("LOW_PERFORMING_GROUPS") or "").strip()
low_groups = [g.strip(" -").strip() for g in low_groups_raw.split(" -") if g.strip(" -").strip()]
reason_bits = [str(row.get(c) or "").strip()
               for c in ("REASON_OVERALL", "REASON_GROUP", "REASON_GRAD", "REASON_PARTICIPATION")]
reason_bits = [b for b in reason_bits if b and b.lower() != "nan"]

callout = (f"**Federal designation: {fed or '—'}.** "
           f"DESE's stated reasons: {'; '.join(reason_bits) if reason_bits else '—'}.")
if low_groups:
    callout += "\n\nThe **student groups flagged as low-performing** (the ones holding the determination down):\n"
    callout += "\n".join(f"- {g}" for g in low_groups)
st.warning(callout)

st.caption(
    f"October enrollment {int(row['ENROLLMENT']):,} · Title I status: "
    f"{row.get('TITLE_I_STATUS', '—')} · District classification: "
    f"{row.get('DIST_CLASSIFICATION', '—')}. Source: DESE {sy} Accountability "
    "Determinations (school-level aggregate; no student records)."
)

# ---------------------------------------------------------------------------
# 3. How the score is built
# ---------------------------------------------------------------------------

with st.expander("How the score is built — weights, the 75% bar, and LEHS's math"):
    st.markdown(
        "DESE scores each indicator **0–4 points**, weights them, and converts the "
        "weighted total into a *criterion-referenced target percentage* (0–100%). "
        "Two populations are scored separately and the school takes the **higher** "
        "of the two as its annual figure:"
    )
    cats = ["Achievement", "Growth", "HS completion", "EL progress", "Additional"]
    wt = pd.DataFrame(
        [{"Population": pop, **{c: (f"{w[c]:g}%" if c in w else "—") for c in cats}}
         for pop, w in ACCT_WEIGHTS_HS.items()]
    )
    st.dataframe(wt, width="stretch", hide_index=True)
    st.markdown(
        f"- **Cumulative** progress = last year × 40% + this year × 60% "
        f"(LEHS: {sy-1} {row['CRIT_PRIOR']:.0f}% × 40% + {sy} {row['CRIT_CURRENT']:.0f}% "
        f"× 60% ≈ **{row['CRIT_CUMULATIVE']:.0f}%**).\n"
        f"- A school reaching a **cumulative ≥ 75%** is considered to be *meeting "
        f"targets*. LEHS is at **{row['CRIT_CUMULATIVE']:.0f}%**, which — combined "
        f"with sitting among the lowest-performing 10% of schools — is why it "
        f"carries the **{fed or 'CSI'}** designation."
    )

st.divider()

# ---------------------------------------------------------------------------
# 4. Where the points are won and lost
# ---------------------------------------------------------------------------

st.header("Where the points are won and lost")
st.markdown(
    "Each indicator is scored **0–4 points**. The determination weighs *All "
    "Students* against the school's *Lowest Performing* 25% of students — so a "
    "school can clear its all-students bar and still be classified on the strength "
    "of its lowest-performing group. Bars at the dashed line earned full credit; "
    "bars near zero are where targets were missed."
)
framework = lehs_ind[lehs_ind["GROUP"].isin(["All Students", "Lowest Performing"])].dropna(subset=["POINTS"]).copy()
if not framework.empty:
    framework["INDICATOR"] = pd.Categorical(framework["INDICATOR"], categories=ind_order, ordered=True)
    framework = framework.sort_values("INDICATOR")
    fig = px.bar(framework, x="INDICATOR", y="POINTS", color="GROUP", barmode="group",
                 color_discrete_map={"All Students": LEHS_NAVY, "Lowest Performing": LEHS_GOLD},
                 category_orders={"INDICATOR": ind_order})
    fig.add_hline(y=MAX_POINTS, line_dash="dash", line_color="gray",
                  annotation_text="Max (4 pts)", annotation_position="top right",
                  annotation_font=dict(size=11, color="gray"))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis=dict(title="Points earned (of 4)", range=[0, 4.4]),
                      xaxis_title="", legend_title="")
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Indicators sitting at 0 points are the ones to target: each is a place the "
        "school declined year-over-year or fell more than a threshold below its DESE target."
    )

st.divider()

# ---------------------------------------------------------------------------
# 5. Statewide percentile context
# ---------------------------------------------------------------------------

st.header("Where LEHS sits statewide")
if pctl.empty:
    st.info("Percentile data not built — run scripts/19 + 16.")
else:
    lehs_p = pctl[(pctl["ORG_CODE"] == LEHS_SCHOOL_CODE) & (pctl["SOURCE"] == "school")
                  & (pctl["COMPONENT_YEAR"] == sy)].copy()
    bars = lehs_p[lehs_p["INDICATOR"].isin(ind_order)].dropna(subset=["PERCENTILE"]).copy()
    if not bars.empty:
        bars["INDICATOR"] = pd.Categorical(bars["INDICATOR"], categories=ind_order, ordered=True)
        bars = bars.sort_values("INDICATOR")
        fig = go.Figure(go.Bar(
            x=bars["PERCENTILE"], y=bars["INDICATOR"], orientation="h",
            marker_color=LEHS_NAVY, text=[f"{int(p)}" for p in bars["PERCENTILE"]],
            textposition="outside", cliponaxis=False,
        ))
        fig.add_vline(x=50, line_dash="dash", line_color="gray",
                      annotation_text="State median (50)", annotation_position="top",
                      annotation_font=dict(size=11, color="gray"))
        fig.update_layout(**DEFAULT_LAYOUT, title=f"LEHS statewide percentile by indicator (SY {sy_lbl})",
                          xaxis=dict(title="Percentile (1 = lowest, 99 = highest)", range=[0, 100]),
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Percentiles are built on a **3-year weighted average** (15% two years "
            "ago / 25% last year / 60% this year), so they lag a single year's swing. "
            "The story: LEHS sits near the **statewide floor on achievement** yet "
            "**markedly higher on growth** — students arrive far behind but gain "
            "ground at a more typical rate."
        )
    # Subgroup overall percentiles
    sub_p = pctl[(pctl["ORG_CODE"] == LEHS_SCHOOL_CODE) & (pctl["SOURCE"] == "student_group")
                 & (pctl["INDICATOR"] == "Overall (weighted)")].dropna(subset=["PERCENTILE"])
    if not sub_p.empty:
        show = sub_p[["GROUP", "PERCENTILE"]].copy()
        show["PERCENTILE"] = show["PERCENTILE"].astype(int)
        show.columns = ["Student group", "Overall percentile (1–99)"]
        st.markdown("**Overall percentile by student group**")
        st.dataframe(show, width="stretch", hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# 6. The path out of CSI — next-year targets
# ---------------------------------------------------------------------------

st.header("The path out — what next year has to look like")
if targets.empty:
    st.info("Targets data not built — run scripts/19 + 16.")
else:
    st.markdown(
        "DESE sets a specific target for each indicator and student group, and an "
        "annual step toward it. Gold tick = this year's target; open diamond = next "
        "year's. The gap between LEHS's current value and the tick is the lift required."
    )
    tabs = st.tabs(["All Students", "Lowest Performing"])
    for tab, grp in zip(tabs, ["All Students", "Lowest Performing"]):
        with tab:
            tg = targets[(targets["ORG_CODE"] == LEHS_SCHOOL_CODE) & (targets["GROUP"] == grp)].copy()
            cur = lehs_ind[lehs_ind["GROUP"] == grp][["INDICATOR", "CURR_VAL", "UNIT", "POINTS"]]
            merged = tg.merge(cur, on="INDICATOR", how="left", suffixes=("", "_ind"))
            merged = merged.dropna(subset=["TARGET_LATEST"])
            if merged.empty:
                st.info(f"No published targets for {grp}.")
                continue
            for unit, ulabel in [("scaled_score", "Achievement (scaled score)"), ("pct", "Rates (%)")]:
                part = merged[merged["UNIT"] == unit].copy()
                part = part[part["CURR_VAL"].notna() | part["TARGET_LATEST"].notna()]
                if part.empty:
                    continue
                part = part.sort_values("INDICATOR")
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=part["CURR_VAL"], y=part["INDICATOR"], orientation="h",
                    marker_color=LEHS_NAVY, name=f"Current ({sy})",
                    text=[_fmt_val(v, unit) for v in part["CURR_VAL"]],
                    textposition="outside", cliponaxis=False,
                ))
                fig.add_trace(go.Scatter(
                    x=part["TARGET_LATEST"], y=part["INDICATOR"], mode="markers",
                    marker=dict(symbol="line-ns", size=20, color=LEHS_GOLD, line=dict(width=2, color=LEHS_GOLD)),
                    name="Target (this year)",
                ))
                fig.add_trace(go.Scatter(
                    x=part["TARGET_PLUS1"], y=part["INDICATOR"], mode="markers",
                    marker=dict(symbol="diamond-open", size=11, color=LEHS_GOLD, line=dict(width=2, color=LEHS_GOLD)),
                    name="Target (next year)",
                ))
                fig.update_layout(**DEFAULT_LAYOUT, title=ulabel, xaxis_title=UNIT_LABEL[unit],
                                  legend_title="", height=80 + 46 * len(part))
                st.plotly_chart(fig, width="stretch")

            # Table
            tbl = []
            for _, r in merged.sort_values("INDICATOR").iterrows():
                u = r["UNIT"]
                met = "" if pd.isna(r.get("POINTS")) else ("✅" if r["POINTS"] >= 3 else "❌")
                req = (None if pd.isna(r["CURR_VAL"]) or pd.isna(r["TARGET_PLUS1"])
                       else r["TARGET_PLUS1"] - r["CURR_VAL"])
                tbl.append({
                    "Indicator": r["INDICATOR"],
                    f"Current ({sy})": _fmt_val(r["CURR_VAL"], u),
                    f"Target ({int(r['TARGET_LATEST_YEAR'])})": _fmt_val(r["TARGET_LATEST"], u),
                    "Met?": met,
                    f"Target ({int(r['TARGET_PLUS1_YEAR'])})": _fmt_val(r["TARGET_PLUS1"], u),
                    "Required change": ("—" if req is None else f"{req:+.1f}"),
                    "Path": ("" if pd.isna(r.get("PATH")) or not r.get("PATH") else str(r["PATH"])),
                })
            st.dataframe(pd.DataFrame(tbl), width="stretch", hide_index=True)
    st.caption(
        "Growth (SGP) has no point-in-time target — it's scored on percentile bands. "
        "For **dropout** and **chronic absenteeism**, lower is better, so the target "
        "sits *below* the current value and a negative required change is the goal. "
        "DESE's `# Included` counts are denominators, not shown here."
    )

st.divider()

# ---------------------------------------------------------------------------
# 7. Indicator trends — the long view
# ---------------------------------------------------------------------------

# indicator -> trend source. scale "frac" => stored 0-1, multiply by 100.
_TREND_SOURCES = {
    "ELA Achievement":     dict(ds="mcas_achievement", val="AVG_SCALED_SCORE", scale="score",
                                subj="ELA", grade="10", by_group=True, ytitle="Avg scaled score", note=None),
    "Math Achievement":    dict(ds="mcas_achievement", val="AVG_SCALED_SCORE", scale="score",
                                subj="MATH", grade="10", by_group=True, ytitle="Avg scaled score", note=None),
    "ELA Growth":          dict(ds="mcas_achievement", val="AVG_SGP", scale="sgp",
                                subj="ELA", grade="10", by_group=True, ytitle="Mean SGP", note="sgp"),
    "Math Growth":         dict(ds="mcas_achievement", val="AVG_SGP", scale="sgp",
                                subj="MATH", grade="10", by_group=True, ytitle="Mean SGP", note="sgp"),
    "4-Year Graduation":   dict(ds="graduation_rates", val="GRAD_PCT", scale="frac",
                                grad_type="4-Year Adjusted Cohort Graduation Rate", by_group=True,
                                ytitle="% graduating", note=None),
    "Annual Dropout":      dict(ds="dropout", val="DRPOUT_PCT_ALL", scale="frac",
                                by_group=True, ytitle="% dropout", note=None),
    "Chronic Absenteeism": dict(ds="student_attendance", val="PCT_CHRON_ABS_10", scale="frac",
                                period="End of Year", by_group=True, ytitle="% chronically absent",
                                note="chronic"),
    "Advanced Coursework": dict(ds="advanced_course_completion", val="ADV_COMP_PCT", scale="frac",
                                by_group=True, ytitle="% completing", note=None),
    "ELP Progress":        dict(ds="el_access", val="RE1_PCT", scale="frac",
                                grade="HS", by_group=False, ytitle="% making progress (RE1)", note=None),
}


def _load_trend(indicator: str, acct_group: str) -> pd.DataFrame:
    spec = _TREND_SOURCES.get(indicator)
    if spec is None:
        return pd.DataFrame()
    d = load_dataset(spec["ds"]).copy()
    if d.empty or "ORG_CODE" not in d.columns:
        return pd.DataFrame()
    d["ORG_CODE"] = d["ORG_CODE"].astype(str).str.zfill(8)
    d = d[d["ORG_CODE"].isin(_SCOPE)]
    if "subj" in spec:
        d = d[d["SUBJECT_CODE"] == spec["subj"]]
    if "grade" in spec and "TEST_GRADE" in d.columns:
        d = d[d["TEST_GRADE"].astype(str) == spec["grade"]]
    if "grade" in spec and "GRADE" in d.columns:
        d = d[d["GRADE"].astype(str) == spec["grade"]]
    if "period" in spec and "ATTEND_PERIOD" in d.columns:
        d = d[d["ATTEND_PERIOD"] == spec["period"]]
    if "grad_type" in spec:
        d = d[d["GRAD_RATE_TYPE"] == spec["grad_type"]]
    if spec["by_group"] and "STU_GRP" in d.columns:
        stu = ACCT_GROUP_TO_STU_GRP.get(acct_group)
        d["STU_GRP"] = d["STU_GRP"].astype(str).str.replace("\xa0", " ", regex=False)
        d = d[d["STU_GRP"] == stu]
    d = d.copy()
    d["Scope"] = d["ORG_CODE"].map(_SCOPE)
    mult = 100 if spec["scale"] == "frac" else 1
    d["VALUE"] = pd.to_numeric(d[spec["val"]], errors="coerce") * mult
    d["SY"] = pd.to_numeric(d["SY"], errors="coerce")
    return d.dropna(subset=["VALUE", "SY"])[["SY", "Scope", "VALUE"]]


st.header("Indicator trends — the long view")
trend_groups = [g for g in ACCT_GROUP_TO_STU_GRP if g in lehs_ind["GROUP"].values]
tc1, tc2 = st.columns(2)
ti = tc1.selectbox("Indicator", list(_TREND_SOURCES.keys()), index=0, key="trend_ind")
tg_spec = _TREND_SOURCES[ti]
if tg_spec["by_group"]:
    tgrp = tc2.selectbox("Student group", trend_groups, key="trend_grp",
                         index=trend_groups.index("All Students") if "All Students" in trend_groups else 0)
else:
    tc2.markdown("&nbsp;")
    tgrp = "All Students"
    tc2.caption("This indicator (ACCESS) is reported for English Learners only, not by subgroup.")

tdf = _load_trend(ti, tgrp)
if tdf.empty:
    st.info("No trend rows for this indicator / group combination.")
else:
    years = tuple(range(int(tdf["SY"].min()), int(tdf["SY"].max()) + 1))
    gapped = with_year_gaps(tdf, "VALUE", group_col="Scope", years=years)
    fig = px.line(gapped, x="SY", y="VALUE", color="Scope", markers=True,
                  color_discrete_map=_SCOPE_COLORS)
    fig.update_traces(connectgaps=False)
    # Target overlays (LEHS, for the selected group)
    if not targets.empty:
        tt = targets[(targets["ORG_CODE"] == LEHS_SCHOOL_CODE) & (targets["GROUP"] == tgrp)
                     & (targets["INDICATOR"] == ti)]
        if not tt.empty and tg_spec["scale"] != "sgp":
            t1 = tt.iloc[0]
            if pd.notna(t1["TARGET_LATEST"]):
                fig.add_hline(y=float(t1["TARGET_LATEST"]), line_dash="dash", line_color=LEHS_GOLD,
                              annotation_text=f"{int(t1['TARGET_LATEST_YEAR'])} target",
                              annotation_position="bottom right", annotation_font=dict(size=10, color=LEHS_GOLD))
            if pd.notna(t1["TARGET_PLUS1"]):
                fig.add_hline(y=float(t1["TARGET_PLUS1"]), line_dash="dot", line_color=LEHS_GOLD,
                              annotation_text=f"{int(t1['TARGET_PLUS1_YEAR'])} target",
                              annotation_position="top right", annotation_font=dict(size=10, color=LEHS_GOLD))
    fig.update_layout(**DEFAULT_LAYOUT, title=f"{ti} — {tgrp}", yaxis_title=tg_spec["ytitle"],
                      xaxis_title="School Year", legend_title="")
    st.plotly_chart(fig, width="stretch")
    note = tg_spec.get("note")
    if note == "sgp":
        st.caption(sgp_methodology_note())
    elif note == "chronic":
        st.caption(chronic_absenteeism_methodology_note())
    st.caption(
        "Trend values come from DESE's underlying assessment / outcome datasets, "
        "which can differ slightly from the accountability snapshot (year vintage, "
        "cohort definition). For the combined EL+Former-EL group, *English Learners* "
        "is shown as the nearest published series. The 2020 COVID gap breaks the line."
    )

st.divider()

# ---------------------------------------------------------------------------
# 8. Indicator detail (with state / district / percentile columns)
# ---------------------------------------------------------------------------

st.header("Indicator detail")
groups_present = [g for g in dict.fromkeys(lehs_ind["GROUP"]) if isinstance(g, str)]
default_idx = groups_present.index("All Students") if "All Students" in groups_present else 0
group_pick = qp_selectbox("Student group", groups_present, index=default_idx, key="detail_grp")
gd = lehs_ind[lehs_ind["GROUP"] == group_pick].copy()

# Benchmarks for this group
state_b = bench[(bench["ORG_TYPE"] == "State") & (bench["GROUP"] == group_pick)] if not bench.empty else pd.DataFrame()
dist_b = bench[(bench["ORG_CODE"] == LYNN_DISTRICT_CODE) & (bench["GROUP"] == group_pick)] if not bench.empty else pd.DataFrame()
pctl_g = pctl[(pctl["ORG_CODE"] == LEHS_SCHOOL_CODE) & (pctl["COMPONENT_YEAR"] == sy)
              & (pctl["GROUP"] == group_pick)] if not pctl.empty else pd.DataFrame()


def _bench_val(frame, indicator):
    if frame.empty:
        return float("nan")
    r = frame[frame["INDICATOR"] == indicator]
    return float(r["CURR_VAL"].iloc[0]) if not r.empty and pd.notna(r["CURR_VAL"].iloc[0]) else float("nan")


def _pctl_val(indicator):
    if pctl_g.empty:
        return None
    r = pctl_g[pctl_g["INDICATOR"] == indicator]
    return None if r.empty or pd.isna(r["PERCENTILE"].iloc[0]) else int(r["PERCENTILE"].iloc[0])


rows = []
for _, r in gd.iterrows():
    unit = r["UNIT"]
    pc = _pctl_val(r["INDICATOR"])
    rows.append({
        "Category": r["CATEGORY"],
        "Indicator": r["INDICATOR"],
        f"Prior ({'' if pd.isna(r['PRIOR_YEAR']) else int(r['PRIOR_YEAR'])})": _fmt_val(r["PRIOR_VAL"], unit),
        f"Current ({'' if pd.isna(r['CURR_YEAR']) else int(r['CURR_YEAR'])})": _fmt_val(r["CURR_VAL"], unit),
        "Target": _fmt_val(r["TARGET"], unit) if unit != "sgp" else "—",
        "Lynn dist.": _fmt_val(_bench_val(dist_b, r["INDICATOR"]), unit),
        "State": _fmt_val(_bench_val(state_b, r["INDICATOR"]), unit),
        "State %ile": "—" if pc is None else str(pc),
        "N": "—" if pd.isna(r["N"]) else f"{int(r['N']):,}",
        "Points": "—" if pd.isna(r["POINTS"]) else f"{int(r['POINTS'])}/4",
        "DESE reason": "" if pd.isna(r["REASON"]) else str(r["REASON"]),
    })
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
st.caption(
    "Growth indicators are scored on mean SGP bands (no point-in-time target). "
    "A blank cell means DESE suppressed it — the group was too small to report. "
    "State / Lynn-district values are the matching HS-level aggregates."
)

st.divider()

# ---------------------------------------------------------------------------
# 9. One indicator, every group (equity view)
# ---------------------------------------------------------------------------

st.header("One indicator, every group")
st.markdown(
    "This is the view behind *“low student group performance.”* Pick an indicator "
    "and compare each group's current value against its DESE target, with state and "
    "district reference lines."
)
ind_pick = qp_selectbox("Indicator", ind_order, index=0, key="equity_ind")
idf = lehs_ind[lehs_ind["INDICATOR"] == ind_pick].copy()
unit = idf["UNIT"].iloc[0] if not idf.empty else "pct"
roll_ups = {"All Students", "Lowest Performing", "High Needs"}
plot = idf[~idf["GROUP"].isin(roll_ups)].dropna(subset=["CURR_VAL"]).sort_values("CURR_VAL")

if plot.empty:
    st.info("No reportable subgroup values for this indicator (cells suppressed).")
else:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=plot["CURR_VAL"], y=plot["GROUP"], orientation="h", marker_color=LEHS_NAVY,
        name="Current", text=[_fmt_val(v, unit) for v in plot["CURR_VAL"]],
        textposition="outside", cliponaxis=False,
    ))
    if unit != "sgp" and plot["TARGET"].notna().any():
        fig.add_trace(go.Scatter(
            x=plot["TARGET"], y=plot["GROUP"], mode="markers",
            marker=dict(symbol="line-ns", size=18, color=LEHS_GOLD, line=dict(width=2, color=LEHS_GOLD)),
            name="Target",
        ))
    allrow = idf[idf["GROUP"] == "All Students"]
    if not allrow.empty and pd.notna(allrow.iloc[0]["CURR_VAL"]):
        fig.add_vline(x=float(allrow.iloc[0]["CURR_VAL"]), line_dash="dot", line_color="gray",
                      annotation_text="LEHS All Students", annotation_position="top",
                      annotation_font=dict(size=10, color="gray"))
    sv = _bench_val(bench[(bench["ORG_TYPE"] == "State") & (bench["GROUP"] == "All Students")] if not bench.empty else pd.DataFrame(), ind_pick)
    dv = _bench_val(bench[(bench["ORG_CODE"] == LYNN_DISTRICT_CODE) & (bench["GROUP"] == "All Students")] if not bench.empty else pd.DataFrame(), ind_pick)
    if pd.notna(sv):
        fig.add_vline(x=sv, line_dash="dash", line_color=STATE_COLOR,
                      annotation_text="State", annotation_position="bottom",
                      annotation_font=dict(size=10, color=STATE_COLOR))
    if pd.notna(dv):
        fig.add_vline(x=dv, line_dash="dot", line_color=LYNN_SIBLING_COLOR,
                      annotation_text="Lynn dist.", annotation_position="bottom",
                      annotation_font=dict(size=10, color=LYNN_SIBLING_COLOR))
    fig.update_layout(**DEFAULT_LAYOUT, title=f"{ind_pick} — by student group (SY {sy_lbl})",
                      xaxis_title=UNIT_LABEL[unit], legend_title="")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Gold tick = each group's DESE target. Lower-is-better indicators (dropout, "
        "chronic absenteeism) read inversely — a bar past its target is a *miss*. "
        "The points column in the detail table encodes the correct direction."
    )

st.divider()

# ---------------------------------------------------------------------------
# 10. LEHS vs Lynn district vs Massachusetts — all indicators
# ---------------------------------------------------------------------------

st.header("LEHS vs Lynn district vs Massachusetts")
if bench.empty:
    st.info("Benchmark data not built — run scripts/19 + 16.")
else:
    comp_rows = []
    le_all = lehs_ind[lehs_ind["GROUP"] == "All Students"].set_index("INDICATOR")
    st_all = bench[(bench["ORG_TYPE"] == "State") & (bench["GROUP"] == "All Students")].set_index("INDICATOR")
    ds_all = bench[(bench["ORG_CODE"] == LYNN_DISTRICT_CODE) & (bench["GROUP"] == "All Students")].set_index("INDICATOR")
    for ind in ind_order:
        if ind not in le_all.index:
            continue
        u = le_all.loc[ind, "UNIT"]
        lev = le_all.loc[ind, "CURR_VAL"]
        sv = st_all.loc[ind, "CURR_VAL"] if ind in st_all.index else float("nan")
        dv = ds_all.loc[ind, "CURR_VAL"] if ind in ds_all.index else float("nan")
        delta = (lev - sv) if (pd.notna(lev) and pd.notna(sv)) else float("nan")
        comp_rows.append({
            "Indicator": ind, "LEHS": _fmt_val(lev, u), "Lynn district": _fmt_val(dv, u),
            "Massachusetts": _fmt_val(sv, u),
            "LEHS − State": "—" if pd.isna(delta) else f"{delta:+.1f}",
        })
    comp = pd.DataFrame(comp_rows)
    st.dataframe(comp, width="stretch", hide_index=True)
    st.caption(
        "Units differ by indicator (scaled scores vs %), so this is a table, not a "
        "single chart. For achievement, a negative *LEHS − State* means LEHS trails; "
        "for dropout / chronic absenteeism, a negative gap is *good* (LEHS lower)."
    )

st.divider()

# ---------------------------------------------------------------------------
# 11. How LEHS compares — peers
# ---------------------------------------------------------------------------

st.header("How LEHS compares")

# Percentile strip across all peer schools.
strip = summary.dropna(subset=["PERCENTILE"]).copy()
if not strip.empty:
    sib_codes = set(LYNN_SIBLING_HS.values())

    def _cat(code):
        if code == LEHS_SCHOOL_CODE:
            return "Lynn English"
        return "Lynn sibling" if code in sib_codes else "Gateway peer"

    strip["Cat"] = strip["ORG_CODE"].map(_cat)
    fig = go.Figure()
    for cat, color in [("Gateway peer", GATEWAY_PEER_COLOR), ("Lynn sibling", LYNN_SIBLING_COLOR)]:
        s = strip[strip["Cat"] == cat]
        if not s.empty:
            fig.add_trace(go.Scatter(
                x=s["PERCENTILE"], y=[cat] * len(s), mode="markers",
                marker=dict(size=10, color=color, opacity=0.7), name=cat,
                text=s["ORG_NAME"], hovertemplate="%{text}: %{x}<extra></extra>",
            ))
    le = strip[strip["ORG_CODE"] == LEHS_SCHOOL_CODE]
    if not le.empty:
        fig.add_trace(go.Scatter(
            x=le["PERCENTILE"], y=["Lynn English"], mode="markers+text",
            marker=dict(size=16, color=LEHS_GOLD, symbol="diamond", line=dict(width=1, color="#7a5b00")),
            text=["LEHS"], textposition="top center", name="Lynn English",
            hovertemplate="LEHS: %{x}<extra></extra>",
        ))
    fig.update_layout(**DEFAULT_LAYOUT, title="Accountability percentile — LEHS among its peers",
                      xaxis=dict(title="Percentile (1–99)", range=[0, 100]), legend_title="",
                      height=320)
    st.plotly_chart(fig, width="stretch")
    st.caption("Every peer school in the dataset, plotted by its 2025 accountability percentile.")

# Sibling table
peers = summary[summary["ORG_CODE"].isin(set(LYNN_SIBLING_HS.values()))].copy()
if not peers.empty:
    peers = peers.sort_values("PERCENTILE", ascending=False)
    show = peers[["ORG_NAME", "CLASSIFICATION", "PERCENTILE", "CRIT_CURRENT",
                  "CRIT_CUMULATIVE", "FEDERAL_DESIGNATION"]].copy()
    show.columns = ["School", "Classification", "Percentile",
                    f"Annual target % (SY {sy_lbl})", "Cumulative %", "Federal designation"]
    st.dataframe(show, width="stretch", hide_index=True)
    st.caption("Lynn's comprehensive + alternative high schools — same district and city.")

st.divider()

# ---------------------------------------------------------------------------
# 12 + 13. Downloads, methodology, cross-links
# ---------------------------------------------------------------------------

data_downloads_panel({
    "Accountability summary (per school)": summary,
    "Accountability indicators (per group)": indicators,
    "Targets & next-year increments": targets,
    "Statewide percentiles": pctl,
    "State + district benchmarks": bench,
})

with st.expander("Methodology & sources"):
    st.markdown(
        "**Sources** — five DESE accountability workbooks (school-level aggregate, "
        "no student records), from doe.mass.edu/accountability/lists-tools:\n"
        "- *accountability-data* — classification, percentile, criterion-referenced %s\n"
        "- *criterion-referenced-percentage* — per-indicator × group detail (HS sheet "
        "for schools; MSHS sheet for the state + district benchmarks)\n"
        "- *accountability-targets* — baselines + this/next-year targets & increments\n"
        "- *school-percentile* / *student-group-percentile* — the 3-year-weighted "
        "(15/25/60) percentile build-up\n\n"
        "**Scoring** — each indicator earns 0–4 points; weighted by the table at the "
        "top, separately for *All Students* and the *Lowest Performing* 25%, and the "
        "higher result becomes the annual criterion-referenced %. **Units**: scaled "
        "scores (~400–600), % rates (0–100), or mean SGP (1–99). Suppressed small-n "
        "cells and implausible placeholder scaled scores are blanked. Some indicators "
        "lag a year (graduation, dropout, extended engagement)."
    )

st.markdown(
    "**These indicators are built from data explored elsewhere in this dashboard:** "
    "[📊 MCAS](/Academic_Performance) · "
    "[🎓 Success After HS (grad / dropout)](/Success_After_HS) · "
    "[🏫 Discipline & Climate (absence)](/Discipline_and_Climate) · "
    "[🌐 English Learners (ELP progress)](/ELL_Pipeline) · "
    "[🧭 Courses & Academics (advanced coursework)](/Courses_and_Academics)"
)

page_footer()
