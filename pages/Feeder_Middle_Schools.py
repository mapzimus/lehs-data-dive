"""Feeder Middle Schools & Enrollment Outlook — LEHS pipeline and projection."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, csv_download, data_downloads_panel, with_year_gaps, span_years
from utils.constants import LEHS_SCHOOL_CODE, LEHS_NAVY, LEHS_GOLD, STATE_COLOR, LYNN_SIBLING_COLOR
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(page_title="Feeder Schools | LEHS", page_icon="🎒", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# The three Lynn middle schools that feed the district's high schools.
# These appear in enrollment_demographics ONLY — the processed MCAS panel kept
# only Lynn HIGH schools, so Grade-8 MCAS for these feeders is not available
# and is deliberately not shown.
# ---------------------------------------------------------------------------

FEEDERS = {
    "01630405": "Breed Middle",
    "01630420": "Pickering Middle",
    "01630305": "Thurgood Marshall Mid",
}
FEEDER_ORDER = ["Breed Middle", "Pickering Middle", "Thurgood Marshall Mid"]
FEEDER_COLORS = {
    "Breed Middle": LEHS_NAVY,
    "Pickering Middle": LEHS_GOLD,
    "Thurgood Marshall Mid": LYNN_SIBLING_COLOR,
}

# Grades projected forward. LEHS is a pure 9–12 school, so its TOTAL_CNT equals
# the sum of G9–G12 — that lets the cohort model's projected total line up
# directly with the historical TOTAL_CNT line.
HS_GRADES = ["G9_CNT", "G10_CNT", "G11_CNT", "G12_CNT"]
PROJ_YEARS = 3        # roll the model forward this many school years
RATIO_PAIRS = 4       # average progression over this many recent year-pairs
BAND = 0.10           # ±10% illustrative uncertainty band


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


# ---------------------------------------------------------------------------
# Load + slice
# ---------------------------------------------------------------------------

enroll = load_dataset("enrollment_demographics")

feeder_rows = pd.DataFrame()
if not enroll.empty and "ORG_CODE" in enroll.columns:
    feeder_rows = enroll[enroll["ORG_CODE"].astype(str).isin(FEEDERS)].copy()
    feeder_rows["SY"] = _num(feeder_rows["SY"])

lehs = pd.DataFrame()
if not enroll.empty and "ORG_CODE" in enroll.columns:
    lehs = enroll[enroll["ORG_CODE"].astype(str) == LEHS_SCHOOL_CODE].copy()
    lehs["SY"] = _num(lehs["SY"])
    for c in HS_GRADES + ["TOTAL_CNT"]:
        if c in lehs.columns:
            lehs[c] = _num(lehs[c]).fillna(0)
    lehs = lehs.sort_values("SY").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Header + framing
# ---------------------------------------------------------------------------

st.title("🎒 Feeder Middle Schools & Enrollment Outlook")
st.markdown(
    "Before students arrive at Lynn's high schools, they spend their middle-school "
    "years at one of the district's three large middle schools — **Breed**, "
    "**Pickering**, and **Thurgood Marshall**. This page profiles those feeder schools "
    "and then takes a data-driven look at where **Lynn English (LEHS)** enrollment is "
    "heading over the next few years."
)
st.caption(
    "The projection here is a simple **grade-progression model** built on public, "
    "aggregate enrollment counts — not a roster-level forecast. It cannot see individual "
    "students, school choice, or migration. Treat it as a transparent baseline, not a "
    "precise prediction. [What we don't know →](/Data_Gaps)"
)

if feeder_rows.empty and lehs.empty:
    st.warning(
        "Enrollment data is unavailable, so neither the feeder snapshot nor the "
        "projection can be shown right now."
    )
    page_footer()
    st.stop()

# ---------------------------------------------------------------------------
# 1) Feeder snapshot (latest SY)
# ---------------------------------------------------------------------------

st.header("Feeder middle schools — latest snapshot")

feeder_snapshot = pd.DataFrame()
feeder_year = None
if not feeder_rows.empty:
    feeder_year = int(feeder_rows["SY"].max())
    latest = feeder_rows[feeder_rows["SY"] == feeder_year].copy()
    rows = []
    for code in FEEDERS:  # preserve order
        r = latest[latest["ORG_CODE"].astype(str) == code]
        if r.empty:
            continue
        r = r.iloc[0]
        gi = lambda c: int(_num(pd.Series([r.get(c)])).fillna(0).iloc[0])
        pc = lambda c: _num(pd.Series([r.get(c)])).iloc[0]
        rows.append({
            "School": FEEDERS[code],
            "Grade 6": gi("G6_CNT"),
            "Grade 7": gi("G7_CNT"),
            "Grade 8": gi("G8_CNT"),
            "Total enrollment": gi("TOTAL_CNT"),
            "% English Learners": pc("EL_PCT"),
            "% Low Income": pc("LI_PCT"),
            "% SWD": pc("SWD_PCT"),
            "% Hispanic/Latino": pc("HL_PCT"),
        })
    feeder_snapshot = pd.DataFrame(rows)

if feeder_snapshot.empty:
    st.info("No feeder-school enrollment found in the dataset for the latest year.")
else:
    st.caption(
        f"School year {sy_label(feeder_year)} (SY{feeder_year}). Percent figures from DESE "
        "are stored as fractions and shown here as percentages."
    )

    counts_tbl = feeder_snapshot[["School", "Grade 6", "Grade 7", "Grade 8", "Total enrollment"]].copy()
    st.dataframe(
        counts_tbl.style.format({c: "{:,}" for c in ["Grade 6", "Grade 7", "Grade 8", "Total enrollment"]}),
        width="stretch", hide_index=True,
    )

    # Grouped bar of G6/G7/G8 by school.
    long = counts_tbl.melt(
        id_vars="School", value_vars=["Grade 6", "Grade 7", "Grade 8"],
        var_name="Grade", value_name="Students",
    )
    long["School"] = pd.Categorical(long["School"], categories=FEEDER_ORDER, ordered=True)
    long = long.sort_values(["School", "Grade"])
    fig = px.bar(
        long, x="Grade", y="Students", color="School", barmode="group",
        title=f"Current middle-grade enrollment by school (SY{feeder_year})",
        color_discrete_map=FEEDER_COLORS, category_orders={"School": FEEDER_ORDER},
        text="Students",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(**DEFAULT_LAYOUT, height=360, xaxis_title=None,
                      yaxis_title="Students", legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "These Grade-8 students are the near-term pipeline into Lynn's 9th grades. "
        "Note that students choose among **LEHS, Classical, Lynn Tech (LVTI), and Douglass**, "
        "so not all of them feed LEHS specifically."
    )

    # Demographic mini-table (fractions → percentages).
    demo_tbl = feeder_snapshot[
        ["School", "% English Learners", "% Low Income", "% SWD", "% Hispanic/Latino"]
    ].copy()
    st.dataframe(
        demo_tbl.style.format(
            {c: "{:.0%}" for c in ["% English Learners", "% Low Income", "% SWD", "% Hispanic/Latino"]}
        ),
        width="stretch", hide_index=True,
    )
    st.caption(
        "Student-population profile of the three feeder schools. All three serve "
        "high shares of low-income, English-learner, and Hispanic/Latino students — "
        "context for the populations entering Lynn's high schools."
    )

# ---------------------------------------------------------------------------
# 2) LEHS enrollment trend (last ~10 years)
# ---------------------------------------------------------------------------

st.header("LEHS enrollment over time")

if lehs.empty:
    st.info("No LEHS enrollment history available.")
else:
    trend = lehs[lehs["SY"].notna()].copy()
    trend["SY"] = trend["SY"].astype(int)
    recent = trend[trend["SY"] >= trend["SY"].max() - 10].copy()

    # Total enrollment line, with explicit year gaps so any skipped year breaks.
    tot = recent[["SY", "TOTAL_CNT"]].copy()
    tot_gapped = with_year_gaps(tot, "TOTAL_CNT", year_col="SY", years=span_years(tot))
    fig_tot = go.Figure()
    fig_tot.add_trace(go.Scatter(
        x=tot_gapped["SY"], y=tot_gapped["TOTAL_CNT"], mode="lines+markers",
        name="Total enrollment", line=dict(color=LEHS_NAVY, width=3), connectgaps=False,
    ))
    fig_tot.update_layout(**DEFAULT_LAYOUT, height=340, title="LEHS total enrollment",
                          xaxis_title=None, yaxis_title="Students", showlegend=False)
    st.plotly_chart(fig_tot, width="stretch")

    # Grade-level lines G9–G12.
    grade_labels = {"G9_CNT": "Grade 9", "G10_CNT": "Grade 10",
                    "G11_CNT": "Grade 11", "G12_CNT": "Grade 12"}
    grade_colors = {"Grade 9": LEHS_GOLD, "Grade 10": LEHS_NAVY,
                    "Grade 11": LYNN_SIBLING_COLOR, "Grade 12": STATE_COLOR}
    fig_g = go.Figure()
    yrs = span_years(recent)
    for col, label in grade_labels.items():
        sub = recent[["SY", col]].rename(columns={col: "val"})
        sub_g = with_year_gaps(sub, "val", year_col="SY", years=yrs)
        fig_g.add_trace(go.Scatter(
            x=sub_g["SY"], y=sub_g["val"], mode="lines+markers", name=label,
            line=dict(color=grade_colors[label], width=2), connectgaps=False,
        ))
    fig_g.update_layout(**DEFAULT_LAYOUT, height=360, title="LEHS enrollment by grade (G9–G12)",
                        xaxis_title=None, yaxis_title="Students", legend_title_text="")
    st.plotly_chart(fig_g, width="stretch")

    # Factual note on the recent decline.
    if len(trend) >= 2:
        last_two = trend.tail(2)
        y_prev, y_last = int(last_two["SY"].iloc[0]), int(last_two["SY"].iloc[1])
        t_prev = int(last_two["TOTAL_CNT"].iloc[0])
        t_last = int(last_two["TOTAL_CNT"].iloc[1])
        st.caption(
            f"Total LEHS enrollment moved from {t_prev:,} in SY{y_prev} to {t_last:,} in "
            f"SY{y_last} ({t_last - t_prev:+,}). The grade lines show where that change "
            "concentrated — incoming 9th-grade cohorts have been smaller in the most "
            "recent years."
        )

# ---------------------------------------------------------------------------
# 3) LEHS enrollment projection — grade-progression / cohort-survival model
# ---------------------------------------------------------------------------

st.header("LEHS enrollment projection")

proj_table = pd.DataFrame()
ratios = None
g9_incoming = None

# Need enough consecutive year-pairs to estimate progression ratios robustly.
hist = lehs[lehs["SY"].notna()].copy() if not lehs.empty else pd.DataFrame()
if not hist.empty:
    hist["SY"] = hist["SY"].astype(int)
    hist = hist.drop_duplicates(subset="SY").sort_values("SY").set_index("SY")
    years = list(hist.index)
    pairs = [(y, y + 1) for y in years if (y + 1) in hist.index]
else:
    years, pairs = [], []

if len(pairs) < 2:
    st.info(
        "There is not enough consecutive LEHS enrollment history to build a reliable "
        "grade-progression projection, so the projection is skipped. The snapshot and "
        "trend above still reflect the latest available data."
    )
else:
    use_pairs = pairs[-RATIO_PAIRS:]

    def _avg_ratio(num_col: str, den_col: str) -> float:
        vals = []
        for y0, y1 in use_pairs:
            den = hist.loc[y0, den_col]
            if den and den > 0:
                vals.append(hist.loc[y1, num_col] / den)
        return float(np.mean(vals)) if vals else 1.0

    # Year-over-year grade-progression (cohort-survival) ratios.
    r10 = _avg_ratio("G10_CNT", "G9_CNT")   # G10(y+1) / G9(y)
    r11 = _avg_ratio("G11_CNT", "G10_CNT")  # G11(y+1) / G10(y)
    r12 = _avg_ratio("G12_CNT", "G11_CNT")  # G12(y+1) / G11(y)
    ratios = {"G9→G10": r10, "G10→G11": r11, "G11→G12": r12}

    # Incoming G9: hold flat at the recent average of LEHS G9 counts (last 3
    # years). Simple and defensible — the recent average is more robust than
    # any single noisy year, and we do not project the feeders' choice split.
    recent_g9 = [hist.loc[y, "G9_CNT"] for y in years[-3:] if hist.loc[y, "G9_CNT"] > 0]
    g9_incoming = float(np.mean(recent_g9)) if recent_g9 else float(hist.loc[years[-1], "G9_CNT"])

    last_year = years[-1]
    g9 = hist.loc[last_year, "G9_CNT"]
    g10 = hist.loc[last_year, "G10_CNT"]
    g11 = hist.loc[last_year, "G11_CNT"]
    g12 = hist.loc[last_year, "G12_CNT"]

    proj_rows = []
    for i in range(1, PROJ_YEARS + 1):
        new_g10 = g9 * r10
        new_g11 = g10 * r11
        new_g12 = g11 * r12
        new_g9 = g9_incoming
        g9, g10, g11, g12 = new_g9, new_g10, new_g11, new_g12
        total = g9 + g10 + g11 + g12
        proj_rows.append({
            "School year": sy_label(last_year + i),
            "SY": last_year + i,
            "Grade 9": round(g9), "Grade 10": round(g10),
            "Grade 11": round(g11), "Grade 12": round(g12),
            "Projected total": round(total),
        })
    proj_table = pd.DataFrame(proj_rows)

    # ----- Projection chart: historical total + dashed projection + band -----
    hist_total = hist.reset_index()[["SY", "TOTAL_CNT"]].copy()
    hist_recent = hist_total[hist_total["SY"] >= last_year - 10]

    proj_x = [last_year] + list(proj_table["SY"])
    proj_y = [hist.loc[last_year, "TOTAL_CNT"]] + list(proj_table["Projected total"])
    band_hi = [v * (1 + BAND) for v in proj_y]
    band_lo = [v * (1 - BAND) for v in proj_y]

    fig_p = go.Figure()
    # Shaded ±band (drawn first so lines sit on top).
    fig_p.add_trace(go.Scatter(
        x=proj_x + proj_x[::-1], y=band_hi + band_lo[::-1], fill="toself",
        fillcolor="rgba(92,116,166,0.15)", line=dict(width=0),
        name=f"±{int(BAND*100)}% illustrative band", hoverinfo="skip",
    ))
    fig_p.add_trace(go.Scatter(
        x=hist_recent["SY"], y=hist_recent["TOTAL_CNT"], mode="lines+markers",
        name="Historical total", line=dict(color=LEHS_NAVY, width=3),
    ))
    fig_p.add_trace(go.Scatter(
        x=proj_x, y=proj_y, mode="lines+markers", name="Projected total",
        line=dict(color=LEHS_GOLD, width=3, dash="dash"),
    ))
    fig_p.update_layout(**DEFAULT_LAYOUT, height=400,
                        title="LEHS total enrollment — history and 3-year projection",
                        xaxis_title=None, yaxis_title="Students", legend_title_text="")
    st.plotly_chart(fig_p, width="stretch")
    st.caption(
        f"Solid line: actual LEHS total enrollment. Dashed line: grade-progression "
        f"projection. The shaded ±{int(BAND*100)}% band is an **illustrative** sensitivity "
        "range, not a statistical confidence interval."
    )

    # Projection ratios + incoming assumption, stated plainly.
    st.markdown(
        f"**Progression ratios** (averaged over the last {len(use_pairs)} year-pairs): "
        f"Grade 9→10 = **{r10:.2f}**, Grade 10→11 = **{r11:.2f}**, "
        f"Grade 11→12 = **{r12:.2f}**. **Incoming Grade 9** is held at the recent "
        f"3-year average of **{g9_incoming:.0f}** students per year."
    )

    # Small table of projected totals.
    show = proj_table[["School year", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "Projected total"]]
    st.dataframe(
        show.style.format({c: "{:,}" for c in ["Grade 9", "Grade 10", "Grade 11", "Grade 12", "Projected total"]}),
        width="stretch", hide_index=True,
    )

# ---------------------------------------------------------------------------
# 4) Methodology + cross-link
# ---------------------------------------------------------------------------

st.subheader("How the projection works")
st.markdown(
    "This is a **grade-progression (cohort-survival) model**, the simplest standard "
    "approach to short-term enrollment forecasting:\n\n"
    "- For each grade transition, we compute the ratio of next year's grade count to "
    "this year's grade below it (e.g. Grade 10 next year ÷ Grade 9 this year), and "
    "average it over the most recent year-pairs to smooth out noise.\n"
    "- Incoming **Grade 9** is held flat at the recent multi-year average, since the "
    "size of each entering class depends on choices among Lynn's high schools that "
    "this model cannot predict.\n"
    "- We then roll the current grades forward three years.\n\n"
    "Real enrollment depends on **school choice, family migration, housing, and program "
    "or policy changes** that aggregate counts simply cannot see. The numbers above are "
    "a transparent baseline for capacity planning — not a roster-level forecast."
)

crosslink_callout(
    "This projection is a simple model on aggregate counts — see the limits of what the data can tell us.",
    "Data_Gaps", "What we don't know →",
)

# ---------------------------------------------------------------------------
# 5) Data downloads + footer
# ---------------------------------------------------------------------------

data_downloads_panel({
    "Feeder snapshot": feeder_snapshot,
    "LEHS enrollment projection": proj_table,
})

page_footer()
