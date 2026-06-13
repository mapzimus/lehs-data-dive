"""Lynn High School Options — LEHS, Classical, LVTI, and Douglass side by side."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, csv_download, data_downloads_panel, with_year_gaps, span_years
from utils.constants import (LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE, LYNN_SIBLING_HS,
                             LEHS_NAVY, LEHS_GOLD, STATE_COLOR, LYNN_SIBLING_COLOR, LVTI_COLOR)
from utils.data_loader import load_dataset

st.set_page_config(page_title="Lynn HS Options | LEHS", page_icon="🏫", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# The four Lynn public high schools a family chooses among.
# Codes verified against DESE datasets 2026-06-13. KIPP Academy Lynn is a
# Commonwealth charter and is NOT in these district datasets (see caveat below).
# ---------------------------------------------------------------------------

SCHOOLS = {
    "01630510": "Lynn English",
    "01630505": "Classical",
    "01630605": "Lynn Tech (LVTI)",
    "01630575": "Fredrick Douglass",
}
# Stable display order — focus school (LEHS) first.
SCHOOL_ORDER = ["Lynn English", "Classical", "Lynn Tech (LVTI)", "Fredrick Douglass"]
SCHOOL_COLORS = {"Lynn English": LEHS_GOLD, "Classical": LEHS_NAVY,
                 "Lynn Tech (LVTI)": LVTI_COLOR, "Fredrick Douglass": LYNN_SIBLING_COLOR}


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _norm_grp(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize the NBSP that DESE embeds in some STU_GRP labels."""
    if not df.empty and "STU_GRP" in df.columns:
        df = df.copy()
        df["STU_GRP"] = df["STU_GRP"].astype(str).str.replace("\xa0", " ")
    return df


def _latest_slice(df: pd.DataFrame) -> pd.DataFrame:
    """Rows for our four schools at the max SY present in this dataset."""
    if df.empty or "ORG_CODE" not in df.columns:
        return pd.DataFrame()
    sub = df[df["ORG_CODE"].astype(str).isin(SCHOOLS)].copy()
    if sub.empty or "SY" not in sub.columns:
        return sub
    sub["SY"] = _num(sub["SY"])
    return sub[sub["SY"] == sub["SY"].max()].copy()


# ---------------------------------------------------------------------------
# Load + reduce each source to a per-school latest-year value keyed by ORG_CODE.
# ---------------------------------------------------------------------------

enroll = load_dataset("enrollment_demographics")
acct = load_dataset("accountability_summary")
mcas = _norm_grp(load_dataset("mcas_achievement"))
grad = _norm_grp(load_dataset("graduation_rates"))
ap = _norm_grp(load_dataset("ap_participation"))

# Enrollment + demographic profile (percentages stored as 0-1 fractions).
enr_latest = _latest_slice(enroll)
enr_year = int(enr_latest["SY"].max()) if not enr_latest.empty else None

# Accountability (SY 2025 only — no SY filter needed, all rows are 2025).
acct_sub = acct[acct["ORG_CODE"].astype(str).isin(SCHOOLS)].copy() if not acct.empty else pd.DataFrame()

# MCAS grade-10, All Students, ELA + Math, latest year.
mcas_g10 = pd.DataFrame()
if not mcas.empty:
    m = mcas[
        (mcas["ORG_CODE"].astype(str).isin(SCHOOLS))
        & (mcas["TEST_GRADE"].astype(str) == "10")
        & (mcas["STU_GRP"] == "All Students")
        & (mcas["SUBJECT_CODE"].isin(["ELA", "MATH"]))
    ].copy()
    m["SY"] = _num(m["SY"])
    if not m.empty:
        m = m[m["SY"] == m["SY"].max()]
        m["M_PLUS_E_PCT"] = _num(m["M_PLUS_E_PCT"])
        mcas_g10 = m
mcas_year = int(mcas_g10["SY"].max()) if not mcas_g10.empty else None

# Graduation — 4-year adjusted cohort, All Students, latest year.
grad_latest = pd.DataFrame()
if not grad.empty:
    g = grad[
        (grad["ORG_CODE"].astype(str).isin(SCHOOLS))
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        & (grad["STU_GRP"] == "All Students")
    ].copy()
    g["SY"] = _num(g["SY"])
    if not g.empty:
        g = g[g["SY"] == g["SY"].max()]
        g["GRAD_PCT"] = _num(g["GRAD_PCT"])
        grad_latest = g
grad_year = int(grad_latest["SY"].max()) if not grad_latest.empty else None

# AP participation — test-takers, All Students, latest year.
ap_latest = pd.DataFrame()
if not ap.empty:
    a = ap[(ap["ORG_CODE"].astype(str).isin(SCHOOLS)) & (ap["STU_GRP"] == "All Students")].copy()
    a["SY"] = _num(a["SY"])
    if not a.empty:
        a = a[a["SY"] == a["SY"].max()]
        a["TEST_TAKERS_CNT"] = _num(a["TEST_TAKERS_CNT"])
        ap_latest = a
ap_year = int(ap_latest["SY"].max()) if not ap_latest.empty else None

# ---------------------------------------------------------------------------
# Page header + framing
# ---------------------------------------------------------------------------

st.title("🏫 Lynn High School Options")
st.markdown(
    "These are the public high schools a Lynn family chooses among, shown side by "
    "side on the same outcome metrics. **Lynn English** and **Classical** are the two "
    "large comprehensive high schools. **Lynn Tech (LVTI)** is a career/technical school "
    "with a different mission — its program mix and selective-ish admissions shape every "
    "comparison below, so read its numbers in that light. **Fredrick Douglass Collegiate "
    "Academy** is a smaller alternative academy; its small enrollment makes rate-based "
    "metrics (graduation, MCAS) noisier year to year."
)
st.caption(
    "Figures are the most recent year published per dataset (years differ slightly by "
    "metric — each is labeled). Percentages from DESE are shown as percentages here."
)

st.info(
    "**KIPP Academy Lynn is not shown here.** As a Commonwealth charter school, KIPP "
    "Academy Lynn is governed and reported separately from Lynn Public Schools and does "
    "not appear in the DESE district datasets behind this dashboard. We do not estimate "
    "or fabricate its numbers — a family weighing KIPP should consult its DESE school "
    "profile directly."
)

# ---------------------------------------------------------------------------
# Scorecard table — one row per school, LEHS first.
# ---------------------------------------------------------------------------

st.header("Scorecard")
st.caption("One row per school. Each metric uses the latest year available in its source dataset.")

DASH = "—"


def _pct(frac) -> str:
    return f"{frac * 100:.0f}%" if pd.notna(frac) else DASH


rows = []
for code in SCHOOLS:  # dict preserves insertion order → LEHS first
    name = SCHOOLS[code]
    row = {"School": name}

    e = enr_latest[enr_latest["ORG_CODE"].astype(str) == code]
    row["Enrollment"] = f"{int(_num(e['TOTAL_CNT']).iloc[0]):,}" if not e.empty and pd.notna(_num(e["TOTAL_CNT"]).iloc[0]) else DASH
    row["% English Learners"] = _pct(_num(e["EL_PCT"]).iloc[0]) if not e.empty else DASH
    row["% Low Income"] = _pct(_num(e["LI_PCT"]).iloc[0]) if not e.empty else DASH
    row["% SWD"] = _pct(_num(e["SWD_PCT"]).iloc[0]) if not e.empty else DASH

    ac = acct_sub[acct_sub["ORG_CODE"].astype(str) == code]
    row["State classification"] = str(ac["CLASSIFICATION"].iloc[0]) if not ac.empty and pd.notna(ac["CLASSIFICATION"].iloc[0]) else DASH
    pct = _num(ac["PERCENTILE"]).iloc[0] if not ac.empty else None
    row["State %ile"] = f"{int(pct)}" if pct is not None and pd.notna(pct) else DASH

    mm = mcas_g10[mcas_g10["ORG_CODE"].astype(str) == code]
    ela = mm[mm["SUBJECT_CODE"] == "ELA"]["M_PLUS_E_PCT"]
    mat = mm[mm["SUBJECT_CODE"] == "MATH"]["M_PLUS_E_PCT"]
    row["MCAS ELA % M+E"] = _pct(ela.iloc[0]) if not ela.empty else DASH
    row["MCAS Math % M+E"] = _pct(mat.iloc[0]) if not mat.empty else DASH

    gg = grad_latest[grad_latest["ORG_CODE"].astype(str) == code]
    row["4-yr Grad %"] = _pct(_num(gg["GRAD_PCT"]).iloc[0]) if not gg.empty else DASH

    aa = ap_latest[ap_latest["ORG_CODE"].astype(str) == code]
    row["AP test-takers"] = f"{int(_num(aa['TEST_TAKERS_CNT']).iloc[0]):,}" if not aa.empty and pd.notna(_num(aa["TEST_TAKERS_CNT"]).iloc[0]) else DASH

    rows.append(row)

scorecard = pd.DataFrame(rows)
st.dataframe(scorecard, width="stretch", hide_index=True)

# Note which schools are absent from which sources (data-availability, not a judgment).
missing_notes = []
present_acct = set(acct_sub["ORG_CODE"].astype(str)) if not acct_sub.empty else set()
for code, name in SCHOOLS.items():
    if code not in present_acct:
        missing_notes.append(f"{name} is not in the SY{int(acct['SY'].max()) if not acct.empty else ''} accountability summary")
if grad_latest.empty or set(SCHOOLS) - set(grad_latest["ORG_CODE"].astype(str)):
    absent = [SCHOOLS[c] for c in SCHOOLS if grad_latest.empty or c not in set(grad_latest["ORG_CODE"].astype(str))]
    if absent:
        missing_notes.append(f"No published 4-year graduation rate for {', '.join(absent)}")
if ap_latest.empty or set(SCHOOLS) - set(ap_latest["ORG_CODE"].astype(str)):
    absent = [SCHOOLS[c] for c in SCHOOLS if ap_latest.empty or c not in set(ap_latest["ORG_CODE"].astype(str))]
    if absent:
        missing_notes.append(f"No AP participation reported for {', '.join(absent)}")
if missing_notes:
    st.caption("Data availability: " + "; ".join(missing_notes) + ". Blank cells (—) mean the metric is not published for that school.")

# ---------------------------------------------------------------------------
# Headline grouped bar charts
# ---------------------------------------------------------------------------

st.header("Headline metrics")


def _ordered(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by our fixed school order so colors/positions stay stable."""
    df = df.copy()
    df["School"] = pd.Categorical(df["School"], categories=SCHOOL_ORDER, ordered=True)
    return df.sort_values("School")


def _bar(df: pd.DataFrame, y: str, title: str, fmt: str, yrange=None, color="School", barmode="group"):
    fig = px.bar(df, x="School", y=y, color=color, title=title,
                 color_discrete_map=SCHOOL_COLORS, text=df[y].map(lambda v: fmt.format(v) if pd.notna(v) else ""))
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(**DEFAULT_LAYOUT, height=330, showlegend=(color != "School"),
                      xaxis_title=None, legend_title_text="")
    if yrange:
        fig.update_yaxes(range=yrange)
    return fig


c1, c2 = st.columns(2)

# MCAS ELA + Math (grade 10, % meeting or exceeding).
with c1:
    if not mcas_g10.empty:
        md = mcas_g10.copy()
        md["School"] = md["ORG_CODE"].astype(str).map(SCHOOLS)
        md["Pct"] = md["M_PLUS_E_PCT"] * 100
        md["Subject"] = md["SUBJECT_CODE"].map({"ELA": "ELA", "MATH": "Math"})
        md = _ordered(md)
        fig = px.bar(md, x="School", y="Pct", color="Subject", barmode="group",
                     title=f"MCAS grade 10 — % meeting/exceeding (SY{mcas_year})",
                     color_discrete_map={"ELA": LEHS_NAVY, "Math": LEHS_GOLD},
                     text=md["Pct"].map("{:.0f}%".format))
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(**DEFAULT_LAYOUT, height=330, xaxis_title=None,
                          yaxis_title="% M+E", legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    else:
        st.caption("No grade-10 MCAS data available.")

# 4-year graduation rate.
with c2:
    if not grad_latest.empty:
        gd = grad_latest.copy()
        gd["School"] = gd["ORG_CODE"].astype(str).map(SCHOOLS)
        gd["Pct"] = _num(gd["GRAD_PCT"]) * 100
        gd = _ordered(gd)
        st.plotly_chart(
            _bar(gd, "Pct", f"4-year graduation rate (SY{grad_year})", "{:.0f}%", yrange=[0, 105]),
            width="stretch",
        )
        st.caption("Douglass's small cohort is not published here; LVTI's near-100% reflects its CTE cohort.")
    else:
        st.caption("No graduation-rate data available.")

c3, c4 = st.columns(2)

# Demographic profile — grouped by school across a few shared measures.
with c3:
    if not enr_latest.empty:
        ed = enr_latest.copy()
        ed["School"] = ed["ORG_CODE"].astype(str).map(SCHOOLS)
        long = []
        for label, col in [("% English Learners", "EL_PCT"), ("% Low Income", "LI_PCT"), ("% SWD", "SWD_PCT")]:
            for _, r in ed.iterrows():
                long.append({"School": r["School"], "Measure": label, "Pct": _num(pd.Series([r[col]])).iloc[0] * 100})
        ld = _ordered(pd.DataFrame(long))
        fig = px.bar(ld, x="Measure", y="Pct", color="School", barmode="group",
                     title=f"Student population profile (SY{enr_year})",
                     color_discrete_map=SCHOOL_COLORS, category_orders={"School": SCHOOL_ORDER})
        fig.update_layout(**DEFAULT_LAYOUT, height=330, xaxis_title=None,
                          yaxis_title="% of students", legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    else:
        st.caption("No enrollment/demographic data available.")

# AP test-takers (counts).
with c4:
    if not ap_latest.empty:
        ad = ap_latest.copy()
        ad["School"] = ad["ORG_CODE"].astype(str).map(SCHOOLS)
        ad["Takers"] = _num(ad["TEST_TAKERS_CNT"])
        ad = _ordered(ad)
        st.plotly_chart(
            _bar(ad, "Takers", f"AP test-takers (SY{ap_year})", "{:.0f}"),
            width="stretch",
        )
        st.caption("Counts, not rates — larger schools naturally field more AP test-takers.")
    else:
        st.caption("No AP participation data available.")

# ---------------------------------------------------------------------------
# Demographic / mission context — neutral, factual, no recommendations.
# ---------------------------------------------------------------------------

st.caption(
    "Reading these together: the four schools serve different student populations and "
    "missions. Lynn Tech (LVTI) admits students into a career/technical program and is "
    "structured around CTE pathways, so its enrollment mix and outcome rates are not a "
    "like-for-like match to the two comprehensive high schools. Fredrick Douglass "
    "Collegiate Academy operates as a small alternative academy, which makes its "
    "rate-based metrics statistically noisier and means some state measures are not "
    "published for it. These differences are context for the numbers above, not a "
    "ranking — no single school here is 'best,' and the right fit depends on a student's "
    "goals and program needs."
)

# ---------------------------------------------------------------------------
# Cross-links
# ---------------------------------------------------------------------------

crosslink_callout(
    "Want the deeper state-accountability view for LEHS specifically?",
    "Accountability",
    "See State Accountability →",
)
st.markdown(
    "Looking beyond Lynn? The [Gateway Peer Comparison](/Gateway_Peer_Comparison) page "
    "puts LEHS next to the main high schools of other Massachusetts Gateway Cities — "
    "districts with similar demographics and challenges."
)

# ---------------------------------------------------------------------------
# Data downloads + footer
# ---------------------------------------------------------------------------

data_downloads_panel({"Lynn HS options scorecard": scorecard})

page_footer()
