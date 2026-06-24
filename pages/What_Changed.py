"""What Changed This Year — biggest year-over-year movers for LEHS."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.briefing import build_briefing_pdf
from utils.charts import DEFAULT_LAYOUT, csv_download, data_downloads_panel
from utils.constants import LEHS_SCHOOL_CODE, LEHS_NAVY, LEHS_GOLD, STATE_COLOR
from utils.data_loader import load_dataset
from utils.interpret import sy_label, yoy_delta

st.set_page_config(page_title="What Changed | LEHS", page_icon="🆕", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# Headline metric catalog. Each entry pulls ONE comparable "All Students"
# number per year for LEHS. `is_pct` values are stored in the parquets as
# fractions (0–1), so they get scaled to 0–100 for display. `good_direction`
# is +1 when a rise is favorable and -1 when a fall is favorable (chronic
# absenteeism + dropout — lower is better).
# ---------------------------------------------------------------------------


def _norm(series: pd.Series) -> pd.Series:
    """Strip the NBSP variants DESE ships in some STU_GRP labels."""
    return series.astype(str).str.replace("\xa0", " ", regex=False).str.strip()


def _series(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Reduce a pre-filtered frame to one clean (SY, value) row per year."""
    if df.empty or value_col not in df.columns:
        return pd.DataFrame(columns=["SY", "value"])
    out = pd.DataFrame(
        {
            "SY": pd.to_numeric(df["SY"], errors="coerce"),
            "value": pd.to_numeric(df[value_col], errors="coerce"),
        }
    )
    out = out.dropna(subset=["SY", "value"])
    out["SY"] = out["SY"].astype(int)
    # If a year somehow has multiple rows, keep the last (most-recent) one.
    return out.drop_duplicates(subset=["SY"], keep="last").sort_values("SY")


def _mcas(subject: str) -> pd.DataFrame:
    df = load_dataset("mcas_achievement")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (df["TEST_GRADE"] == "10")
        & (df["SUBJECT_CODE"] == subject)
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _series(sub, "M_PLUS_E_PCT")


def _grad() -> pd.DataFrame:
    df = load_dataset("graduation_rates")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    # Exact match on the standard 4-year rate: "contains 4" would also pull the
    # 4-Year Adjusted Cohort rate and double every year.
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (df["GRAD_RATE_TYPE"] == "4-Year Graduation Rate")
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _series(sub, "GRAD_PCT")


def _chronic_abs() -> pd.DataFrame:
    df = load_dataset("student_attendance")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (df["ATTEND_PERIOD"] == "End of Year")
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _series(sub, "PCT_CHRON_ABS_10")


def _ap_takers() -> pd.DataFrame:
    df = load_dataset("ap_participation")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _series(sub, "TEST_TAKERS_CNT")


def _dropout() -> pd.DataFrame:
    df = load_dataset("dropout")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _series(sub, "DRPOUT_PCT_ALL")


def _enroll(value_col: str) -> pd.DataFrame:
    df = load_dataset("enrollment_demographics")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[df["ORG_CODE"] == LEHS_SCHOOL_CODE]
    return _series(sub, value_col)


# (label, loader, unit, is_pct, good_direction)
METRICS = [
    ("MCAS Gr.10 ELA — % meeting/exceeding", lambda: _mcas("ELA"), "pts", True, +1),
    ("MCAS Gr.10 Math — % meeting/exceeding", lambda: _mcas("MATH"), "pts", True, +1),
    ("MCAS Gr.10 Science — % meeting/exceeding", lambda: _mcas("SCI"), "pts", True, +1),
    ("4-year graduation rate", _grad, "pts", True, +1),
    ("Chronic absenteeism (≥10% of days)", _chronic_abs, "pts", True, -1),
    ("AP test takers", _ap_takers, "students", False, +1),
    ("Dropout rate", _dropout, "pts", True, -1),
    ("Total enrollment", lambda: _enroll("TOTAL_CNT"), "students", False, +1),
    ("English learners (% of enrollment)", lambda: _enroll("EL_PCT"), "pts", True, 0),
    ("Low-income (% of enrollment)", lambda: _enroll("LI_PCT"), "pts", True, 0),
]


def build_movers() -> pd.DataFrame:
    """Latest year-over-year move per metric. Skips metrics with <2 years."""
    rows = []
    for label, loader, unit, is_pct, good_dir in METRICS:
        s = loader()
        if len(s) < 2:
            continue
        latest, prior = s.iloc[-1], s.iloc[-2]
        scale = 100.0 if is_pct else 1.0
        latest_val = latest["value"] * scale
        prior_val = prior["value"] * scale
        delta = latest_val - prior_val
        # Favorability: a move in the good_direction sign is favorable; a metric
        # with good_dir == 0 (context-only, e.g. demographics) is neutral.
        if good_dir == 0 or abs(delta) < (0.05 if is_pct else 0.5):
            favorable = None
        else:
            favorable = (delta > 0) == (good_dir > 0)
        rows.append(
            {
                "Metric": label,
                "latest_year": int(latest["SY"]),
                "Latest": latest_val,
                "Prior": prior_val,
                "Change": delta,
                "unit": unit,
                "is_pct": is_pct,
                "favorable": favorable,
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.reindex(out["Change"].abs().sort_values(ascending=False).index)
        out = out.reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# 1. Title + intro
# ---------------------------------------------------------------------------

st.title("🆕 What Changed This Year")
st.markdown(
    "This page is a living snapshot of the **biggest year-over-year movements** "
    "at Lynn English High (LEHS) across the major public datasets. Each metric "
    "compares the **latest two available years** for *All Students*. Because "
    "different datasets update on different schedules, the \"latest year\" is "
    "**not the same for every metric** — each row is labeled with its own year."
)

with st.container(border=True):
    st.markdown("**📄 School Committee briefing** — a one-page PDF of LEHS's headline numbers.")
    try:
        st.download_button("⬇ Download briefing (PDF)", data=build_briefing_pdf(),
                           file_name="lehs_briefing.pdf", mime="application/pdf",
                           key="dl_briefing")
    except Exception as e:
        st.caption(f"Briefing PDF temporarily unavailable: {e}")

movers = build_movers()

if movers.empty:
    st.info(
        "Year-over-year comparison needs at least two data years; "
        "not enough data is loaded yet."
    )
    st.stop()


def _fmt_val(v: float, is_pct: bool) -> str:
    return f"{v:.1f}%" if is_pct else f"{v:,.0f}"


def _direction_label(row) -> str:
    if row["favorable"] is None:
        if abs(row["Change"]) < (0.05 if row["is_pct"] else 0.5):
            return "— little change"
        return "— context metric"
    arrow = "▲" if row["Change"] > 0 else "▼"
    word = "improved" if row["favorable"] else "worsened"
    return f"{arrow} {word}"


# ---------------------------------------------------------------------------
# 2./3. Summary table
# ---------------------------------------------------------------------------

st.subheader("Biggest movers, latest year over prior year")

table = pd.DataFrame(
    {
        "Metric": movers["Metric"],
        "Latest year": movers["latest_year"].map(sy_label),
        "Latest": [
            _fmt_val(v, p) for v, p in zip(movers["Latest"], movers["is_pct"])
        ],
        "Prior": [
            _fmt_val(v, p) for v, p in zip(movers["Prior"], movers["is_pct"])
        ],
        "Change": [
            f"{c:+.1f}{'%' if p else ''}" if p else f"{c:+,.0f}"
            for c, p in zip(movers["Change"], movers["is_pct"])
        ],
        "Direction": [_direction_label(r) for _, r in movers.iterrows()],
    }
)
st.dataframe(table, width="stretch", hide_index=True)

# Plain-language line for the single largest move.
_top = movers.iloc[0]
st.caption(
    f"Largest move: **{_top['Metric']}** is "
    f"{yoy_delta(_top['Latest'], _top['Prior'], unit=_top['unit'])} "
    f"({sy_label(_top['latest_year'])})."
)

# ---------------------------------------------------------------------------
# 4. Diverging bar chart
# ---------------------------------------------------------------------------

st.subheader("Year-over-year change by metric")

chart_df = movers.copy()
# Plot favorable moves in LEHS navy, unfavorable in gold, neutral/context grey.
chart_df["bar_color"] = chart_df["favorable"].map(
    {True: LEHS_NAVY, False: LEHS_GOLD}
).fillna(STATE_COLOR)
# Horizontal bars read top-to-bottom; reverse so the biggest mover sits on top.
chart_df = chart_df.iloc[::-1]

fig = px.bar(
    chart_df,
    x="Change",
    y="Metric",
    orientation="h",
)
fig.update_traces(
    marker_color=list(chart_df["bar_color"]),
    hovertemplate="%{y}<br>Change: %{x:+.1f}<extra></extra>",
)
fig.add_vline(x=0, line_width=1, line_color="#9AA6B5")
fig.update_layout(**DEFAULT_LAYOUT)
fig.update_layout(
    height=max(280, 42 * len(chart_df)),
    xaxis_title="Change vs. prior year (percentage points, or count)",
    yaxis_title="",
)
st.plotly_chart(fig, width="stretch")
st.caption(
    "Navy = favorable move · gold = unfavorable move · grey = context metric "
    "(demographic share, no inherent good/bad direction). "
    "Percentage-based metrics are in points; counts are raw numbers."
)

# ---------------------------------------------------------------------------
# 5. Neutral framing + crosslink
# ---------------------------------------------------------------------------

st.caption(
    "These are **point-in-time snapshots** comparing two years, not multi-year "
    "trends — a single-year move can reflect a one-off cohort, a methodology "
    "change, or normal variation. See the **Methodology** page for how each "
    "metric is defined and which years are available."
)
crosslink_callout(
    "These shifts roll up into the state's annual accountability determination.",
    "Accountability",
    "See State Accountability →",
)

# ---------------------------------------------------------------------------
# 6. Downloads + footer
# ---------------------------------------------------------------------------

dl = movers[["Metric", "latest_year", "Latest", "Prior", "Change", "unit"]].copy()
dl = dl.rename(columns={"latest_year": "Latest_SY"})
data_downloads_panel({"Year-over-year movers (LEHS)": dl})

page_footer()
