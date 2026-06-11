"""
Section 18 — State Accountability.

Breaks down the one thing a principal or district leader checks first: the DESE
accountability determination. The headline (classification + percentile) lives
in accountability.parquet; this page opens up the layer underneath it — the
per-indicator, per-student-group detail that explains *why* the school landed
where it did, and exactly which targets it missed.

All data here is school-level aggregate (DESE's published accountability files).
No student records.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, data_downloads_panel
from utils.constants import LEHS_SCHOOL_CODE, LYNN_SIBLING_HS
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(page_title="Accountability | LEHS", page_icon="🏛️", layout="wide")
sidebar_attribution()

# Each accountability indicator is scored 0-4 points by DESE; "% of possible"
# rolls those up. Treating 4 as the per-indicator max lets us draw a clean
# "where are we losing points" view without re-deriving DESE's weighting.
MAX_POINTS = 4

st.title("State Accountability")
st.markdown(
    "Every Massachusetts school gets an annual **accountability determination** "
    "from DESE — a classification, a 1–99 percentile, and a *criterion-referenced "
    "target percentage* that rolls up roughly a dozen indicators. This page breaks "
    "that determination down to the indicator-and-student-group level so you can "
    "see **which targets drove the classification**, not just the headline."
)

summary = load_dataset("accountability_summary")
indicators = load_dataset("accountability_indicators")
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

# ---------------------------------------------------------------------------
# Headline classification
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
# DESE joins the low-performing groups with " -"; split back into a clean list.
low_groups = [g.strip(" -").strip() for g in low_groups_raw.split(" -") if g.strip(" -").strip()]

reason_bits = [str(row.get(c) or "").strip()
               for c in ("REASON_OVERALL", "REASON_GROUP", "REASON_GRAD", "REASON_PARTICIPATION")]
reason_bits = [b for b in reason_bits if b and b.lower() != "nan"]

callout = (
    f"**Federal designation: {fed or '—'}.** "
    f"DESE's stated reasons: {'; '.join(reason_bits) if reason_bits else '—'}."
)
if low_groups:
    callout += "\n\nThe **student groups flagged as low-performing** (the ones holding the determination down):\n"
    callout += "\n".join(f"- {g}" for g in low_groups)
st.warning(callout)

st.caption(
    f"October enrollment {int(row['ENROLLMENT']):,} · Title I status: "
    f"{row.get('TITLE_I_STATUS', '—')} · District classification: "
    f"{row.get('DIST_CLASSIFICATION', '—')}. Source: DESE 2025 Accountability "
    "Determinations (school-level aggregate; no student records)."
)

st.divider()

# ---------------------------------------------------------------------------
# Where the points are won and lost
# ---------------------------------------------------------------------------

st.header("Where the points are won and lost")
st.markdown(
    "Each indicator is scored **0–4 points**. The determination weights *All "
    "Students* against the school's *Lowest Performing* 25% of students — so a "
    "school can clear its all-students bar and still be classified on the "
    "strength of its lowest-performing group. Bars at the dashed line earned "
    "full credit; bars near zero are where targets were missed."
)

framework = lehs_ind[lehs_ind["GROUP"].isin(["All Students", "Lowest Performing"])].copy()
framework = framework.dropna(subset=["POINTS"])
if not framework.empty:
    # Preserve report order (Achievement → Growth → completion → EL → additional).
    order = list(dict.fromkeys(lehs_ind["INDICATOR"]))
    framework["INDICATOR"] = pd.Categorical(framework["INDICATOR"], categories=order, ordered=True)
    framework = framework.sort_values("INDICATOR")

    fig = px.bar(
        framework, x="INDICATOR", y="POINTS", color="GROUP", barmode="group",
        color_discrete_map={"All Students": LEHS_NAVY, "Lowest Performing": LEHS_GOLD},
        category_orders={"INDICATOR": order},
    )
    fig.add_hline(y=MAX_POINTS, line_dash="dash", line_color="gray",
                  annotation_text="Max (4 pts)", annotation_position="top right",
                  annotation_font=dict(size=11, color="gray"))
    fig.update_layout(
        **DEFAULT_LAYOUT,
        yaxis=dict(title="Points earned (of 4)", range=[0, 4.4]),
        xaxis_title="",
        legend_title="",
    )
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Indicators sitting at 0 points are the ones to target: each is a place "
        "the school declined year-over-year or fell more than a threshold below "
        "its DESE target."
    )

st.divider()

# ---------------------------------------------------------------------------
# Full indicator breakdown for one student group
# ---------------------------------------------------------------------------

st.header("Indicator detail")

groups_present = [g for g in dict.fromkeys(lehs_ind["GROUP"]) if isinstance(g, str)]
default_idx = groups_present.index("All Students") if "All Students" in groups_present else 0
group_pick = st.selectbox("Student group", groups_present, index=default_idx)

gd = lehs_ind[lehs_ind["GROUP"] == group_pick].copy()


def _fmt_val(v, unit) -> str:
    if pd.isna(v):
        return "—"
    if unit == "pct":
        return f"{v:.1f}%"
    if unit == "sgp":
        return f"{v:.1f}"
    return f"{v:.1f}"  # scaled_score


rows = []
for _, r in gd.iterrows():
    unit = r["UNIT"]
    pts = r["POINTS"]
    rows.append({
        "Category": r["CATEGORY"],
        "Indicator": r["INDICATOR"],
        f"Prior ({'' if pd.isna(r['PRIOR_YEAR']) else int(r['PRIOR_YEAR'])})": _fmt_val(r["PRIOR_VAL"], unit),
        f"Current ({'' if pd.isna(r['CURR_YEAR']) else int(r['CURR_YEAR'])})": _fmt_val(r["CURR_VAL"], unit),
        "Target": _fmt_val(r["TARGET"], unit) if unit != "sgp" else "—",
        "N": "—" if pd.isna(r["N"]) else f"{int(r['N']):,}",
        "Points": "—" if pd.isna(pts) else f"{int(pts)}/4",
        "DESE reason": "" if pd.isna(r["REASON"]) else str(r["REASON"]),
    })
detail = pd.DataFrame(rows)
st.dataframe(detail, use_container_width=True, hide_index=True)
st.caption(
    "Growth indicators are scored on mean SGP bands (no point-in-time target). "
    "A blank row means DESE suppressed that cell — the group was too small to "
    "report — same small-n rule that makes single-subgroup numbers swing."
)

st.divider()

# ---------------------------------------------------------------------------
# One indicator across every student group (equity view)
# ---------------------------------------------------------------------------

st.header("One indicator, every group")
st.markdown(
    "This is the view behind *“low student group performance.”* Pick an "
    "indicator and compare each group's current value against its DESE target."
)

ind_order = list(dict.fromkeys(lehs_ind["INDICATOR"]))
ind_pick = st.selectbox("Indicator", ind_order, index=0)

idf = lehs_ind[(lehs_ind["INDICATOR"] == ind_pick)].copy()
unit = idf["UNIT"].iloc[0] if not idf.empty else "pct"
# Drop the roll-up groups so the bars show actual student populations.
roll_ups = {"All Students", "Lowest Performing", "High Needs"}
plot = idf[~idf["GROUP"].isin(roll_ups)].dropna(subset=["CURR_VAL"]).copy()
plot = plot.sort_values("CURR_VAL")

if plot.empty:
    st.info("No reportable subgroup values for this indicator (cells suppressed).")
else:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=plot["CURR_VAL"], y=plot["GROUP"], orientation="h",
        marker_color=LEHS_NAVY, name="Current",
        text=[_fmt_val(v, unit) for v in plot["CURR_VAL"]], textposition="outside",
        cliponaxis=False,
    ))
    if unit != "sgp" and plot["TARGET"].notna().any():
        fig.add_trace(go.Scatter(
            x=plot["TARGET"], y=plot["GROUP"], mode="markers",
            marker=dict(symbol="line-ns", size=18, color=LEHS_GOLD,
                        line=dict(width=2, color=LEHS_GOLD)),
            name="Target",
        ))
    # All-Students reference, for orientation.
    allrow = idf[idf["GROUP"] == "All Students"]
    if not allrow.empty and pd.notna(allrow.iloc[0]["CURR_VAL"]):
        fig.add_vline(x=float(allrow.iloc[0]["CURR_VAL"]), line_dash="dot",
                      line_color="gray",
                      annotation_text="All Students", annotation_position="top",
                      annotation_font=dict(size=11, color="gray"))
    unit_label = {"pct": "%", "sgp": "mean SGP", "scaled_score": "scaled score"}.get(unit, "")
    fig.update_layout(
        **DEFAULT_LAYOUT,
        title=f"{ind_pick} — by student group (SY {sy_lbl})",
        xaxis_title=unit_label,
        legend_title="",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "The gold tick marks each group's DESE target. Lower-is-better indicators "
        "(dropout, chronic absenteeism) read inversely — a bar past its target is a "
        "*miss*, not a win. The points column in the table above already encodes "
        "the correct direction."
    )

# ---------------------------------------------------------------------------
# Peer context + downloads
# ---------------------------------------------------------------------------

st.divider()
st.header("How LEHS compares")

sib_codes = {c for c in LYNN_SIBLING_HS.values()}
peers = summary[summary["ORG_CODE"].isin(sib_codes)].copy()
if not peers.empty:
    peers = peers.sort_values("PERCENTILE", ascending=False)
    show = peers[["ORG_NAME", "CLASSIFICATION", "PERCENTILE",
                  "CRIT_CURRENT", "CRIT_CUMULATIVE", "FEDERAL_DESIGNATION"]].copy()
    show.columns = ["School", "Classification", "Percentile",
                    f"Annual target % (SY {sy_lbl})", "Cumulative %", "Federal designation"]
    st.dataframe(show, use_container_width=True, hide_index=True)
    st.caption("Lynn's comprehensive + alternative high schools, same district and city.")

data_downloads_panel({
    "Accountability summary (per school)": summary,
    "Accountability indicators (per group)": indicators,
})

page_footer()
