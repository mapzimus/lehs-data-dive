"""
Section 12 — Cross-Topic Explorer: correlation discovery across domains.

The novel analytical layer no DESE tool provides.
"""

import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    GATEWAY_PEER_COLOR,
    LEHS_GOLD,
    LEHS_NAVY,
    csv_download,
)
from utils.constants import PROCESSED_DIR
from utils.correlations import interpret_r, pearson, regression_line
from utils.data_loader import load_dataset
from utils.url_state import qp_radio, qp_selectbox

st.set_page_config(page_title="Cross-Topic Explorer | LEHS", page_icon="🔬", layout="wide")
sidebar_attribution()

st.title("Cross-Topic Explorer")
st.markdown(
    "Because every dataset lives in the same data model joined on (school, year), "
    "we can ask questions DESE's siloed tools can't. Pick any two metrics "
    "below to explore relationships across the 26 gateway-city high schools "
    "(one main high school per city, with Lynn English representing Lynn)."
)

st.caption(
    "**Note:** Correlation is not causation. Patterns here are starting points "
    "for questions, not proof of cause and effect."
)
st.caption(
    "**A concrete confounder to keep in mind:** the gateway cities differ "
    "sharply in who they enroll — English-learner share and low-income share "
    "vary widely from city to city — and those shared demographics can drive "
    "*both* axes of a scatter at once. Two metrics can look tightly linked "
    "simply because each tracks the same underlying population mix, not "
    "because one moves the other. This tool surfaces patterns worth "
    "investigating; it cannot say what causes them."
)

# ---------------------------------------------------------------------------
# Build the master panel: one row per (school, year) with key indicators
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def build_master_panel() -> pd.DataFrame:
    """Wide panel: rows = (school_code, year), cols = key metrics from all sources."""
    from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE
    peers = json.loads((PROCESSED_DIR / "_peer_schools.json").read_text())
    gateway_codes = [
        info["school_code"] for info in peers["gateway_main_hs"].values()
        if info.get("school_code")
    ]
    # Represent Lynn with LEHS (one school per city). The manifest's "Lynn"
    # slot is Classical (01630505) — it only edged out LEHS on cumulative
    # enrollment — so swap it for LEHS here. Keeping both would double-count
    # Lynn: every scatter would show a Classical dot AND a LEHS dot, and the
    # "26 gateway-city HS" claim would actually be 27 points. Drop Classical,
    # add LEHS, so Lynn contributes exactly one (correctly-labeled) point.
    gateway_codes = [c for c in gateway_codes if c != LCHS_SCHOOL_CODE]
    if LEHS_SCHOOL_CODE not in gateway_codes:
        gateway_codes.append(LEHS_SCHOOL_CODE)

    # 1) Enrollment + demographics
    enr = load_dataset("enrollment_demographics")
    enr = enr[enr["ORG_CODE"].isin(gateway_codes)].copy()
    enr_cols = ["SY", "ORG_CODE", "ORG_NAME", "DIST_NAME",
                "TOTAL_CNT", "EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT",
                "HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT", "FLNE_PCT"]
    base = enr[[c for c in enr_cols if c in enr.columns]].rename(columns={
        "TOTAL_CNT": "Enrollment",
        "EL_PCT": "ELL_pct", "LI_PCT": "LowIncome_pct",
        "SWD_PCT": "SPED_pct", "HN_PCT": "HighNeeds_pct",
        "HL_PCT": "Hispanic_pct", "BAA_PCT": "Black_pct",
        "AS_PCT": "Asian_pct", "WH_PCT": "White_pct",
        "FLNE_PCT": "FirstLangNotEnglish_pct",
    })

    # 2) DART indicators (long → wide)
    dart = load_dataset("dart_success_after_hs")
    dart = dart[(dart["ORG_CODE"].isin(gateway_codes)) & (dart["STU_GRP"] == "All Students")].copy()
    dart["VALUE"] = pd.to_numeric(dart["VALUE"], errors="coerce")

    # NOTE: "4-year cohort graduation rate" and "Jr/Sr AP test takers scoring 3
    # or above" are deliberately NOT sourced from DART here. The canonical
    # 4-year grad rate is DESE's 4-Year *Adjusted Cohort* rate (graduation_rates)
    # and the canonical AP figure is the % of AP *exams* scoring 3+
    # (ap_performance PCT_3_5). Both are merged in below from those files so this
    # page matches the rest of the app's definitions. The 5-year cohort rate
    # stays on DART (no re-sourcing requested for it).
    indicator_aliases = {
        "5-year cohort graduation rate": "GradRate_5yr",
        "9th to 10th grade promotion rate (first-time 9th graders only)": "Promotion_9to10",
        "Annual dropout rate": "Dropout",
        "Chronically absent rate (% of students absent 10% or more each year)": "ChronicAbsence",
        "Student attendance rate": "AttendanceRate",
        "Students suspended out-of-school at least once": "Suspension_pct",
        "Average student growth percentiles (SGP) in ELA": "SGP_ELA",
        "Average student growth percentiles (SGP) in mathematics": "SGP_Math",
        "Grade 10 students meeting or exceeding expectations in ELA": "MCAS_G10_ELA",
        "Grade 10 students meeting or exceeding expectations in mathematics": "MCAS_G10_Math",
        "Jr/Sr enrolled in one or more AP / IB courses": "AP_Enrolled",
        "SAT average score - Mathematics": "SAT_Math",
        "SAT average score - Reading": "SAT_Reading",
        "Grade 12 students who completed FAFSA": "FAFSA",
        "Students enrolled in postsecondary education in the immediate fall after high school graduation": "ImmediateCollege",
        "High school graduates enrolled in 2-year postsecondary education": "College_2yr",
        "High school graduates enrolled in 4-year postsecondary education": "College_4yr",
        "College students persistently enrolled in postsecondary education for the first two years": "CollegePersist",
        "High school graduates who completed MassCore": "MassCore",
    }
    dart_filt = dart[dart["INDICATOR"].isin(indicator_aliases.keys())].copy()
    dart_filt["alias"] = dart_filt["INDICATOR"].map(indicator_aliases)
    dart_wide = dart_filt.pivot_table(
        index=["SY", "ORG_CODE"], columns="alias", values="VALUE", aggfunc="mean"
    ).reset_index()

    # DART stores percent rates/shares as 0-100 (e.g. 84.6 for an 84.6% grad
    # rate), but the demographic *_pct columns above are 0-1 fractions. Put the
    # percent-type DART columns on the same 0-1 scale so a chart mixing, say,
    # ELL share (0-1) and graduation rate doesn't plot one axis 0-1 and the
    # other 0-100. SGP_* (a 0-100 growth percentile) and SAT_* (200-800 scaled
    # scores) are NOT percentages and are left on their native scale. Pearson r
    # is scale-invariant, so this only affects readability, not the statistics.
    DART_PCT_ALIASES = [
        "GradRate_5yr", "Promotion_9to10", "Dropout",
        "ChronicAbsence", "AttendanceRate", "Suspension_pct",
        "MCAS_G10_ELA", "MCAS_G10_Math", "AP_Enrolled",
        "FAFSA", "ImmediateCollege", "College_2yr", "College_4yr",
        "CollegePersist", "MassCore",
    ]
    for col in DART_PCT_ALIASES:
        if col in dart_wide.columns:
            dart_wide[col] = pd.to_numeric(dart_wide[col], errors="coerce") / 100.0

    # 3) Finance: per-pupil + teacher salary
    sp = load_dataset("school_expenditures")
    sp = sp[sp["ORG_CODE"].isin(gateway_codes)].copy()
    sp["IND_VALUE"] = pd.to_numeric(sp["IND_VALUE"], errors="coerce")
    pp = sp[(sp["IND_CAT"] == "Total A+B+C") & (sp["IND_SUBCAT"] == "Total Expenditures")] \
            [["SY", "ORG_CODE", "IND_VALUE"]].rename(columns={"IND_VALUE": "PerPupil"})
    sal = sp[(sp["IND_CAT"] == "Teacher Salaries") & (sp["IND_SUBCAT"] == "Average Teacher Salary")] \
            [["SY", "ORG_CODE", "IND_VALUE"]].rename(columns={"IND_VALUE": "AvgTeacherSalary"})
    t_ratio = sp[(sp["IND_CAT"] == "Teacher Salaries") & (sp["IND_SUBCAT"] == "Teachers per 100 FTE students")] \
            [["SY", "ORG_CODE", "IND_VALUE"]].rename(columns={"IND_VALUE": "TeachersPer100"})

    # 4) Canonical 4-year graduation rate — DESE's official 4-Year ADJUSTED
    # COHORT rate (per gateway main-HS school row), NOT DART's un-adjusted
    # "4-year cohort graduation rate". Keyed on (SY, ORG_CODE) so it joins onto
    # the panel per school-year. GRAD_PCT is already 0-1.
    grad = load_dataset("graduation_rates")
    if not grad.empty:
        gr = grad[
            (grad["ORG_CODE"].isin(gateway_codes))
            & (grad["ORG_TYPE"] == "School")
            & (grad["STU_GRP"] == "All Students")
            & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        ].copy()
        gr["GradRate_4yr"] = pd.to_numeric(gr["GRAD_PCT"], errors="coerce")
        grad_wide = gr[["SY", "ORG_CODE", "GradRate_4yr"]].dropna(subset=["GradRate_4yr"])
    else:
        grad_wide = pd.DataFrame(columns=["SY", "ORG_CODE", "GradRate_4yr"])

    # 5) Canonical AP "scoring 3+" — % of AP EXAMS scoring 3+ (exam-weighted,
    # All Subjects), from ap_performance PCT_3_5 (already 0-1), NOT DART's
    # per-student "Jr/Sr AP test takers scoring 3 or above". Same definition the
    # College & Career page's AP-by-group chart uses.
    ap = load_dataset("ap_performance")
    if not ap.empty:
        apx = ap[
            (ap["ORG_CODE"].isin(gateway_codes))
            & (ap["SUBJ"] == "All Subjects")
            & (ap["STU_GRP"] == "All Students")
        ].copy()
        apx["AP_exams_3plus"] = pd.to_numeric(apx["PCT_3_5"], errors="coerce")
        ap_wide = apx[["SY", "ORG_CODE", "AP_exams_3plus"]].dropna(subset=["AP_exams_3plus"])
    else:
        ap_wide = pd.DataFrame(columns=["SY", "ORG_CODE", "AP_exams_3plus"])

    # Join everything
    panel = base.merge(dart_wide, on=["SY", "ORG_CODE"], how="outer")
    panel = panel.merge(grad_wide, on=["SY", "ORG_CODE"], how="outer")
    panel = panel.merge(ap_wide, on=["SY", "ORG_CODE"], how="outer")
    panel = panel.merge(pp, on=["SY", "ORG_CODE"], how="left")
    panel = panel.merge(sal, on=["SY", "ORG_CODE"], how="left")
    panel = panel.merge(t_ratio, on=["SY", "ORG_CODE"], how="left")
    return panel


panel = build_master_panel()
if panel.empty:
    st.error("Master panel empty.")
    st.stop()

NUMERIC_COLS = sorted([c for c in panel.columns if pd.api.types.is_numeric_dtype(panel[c]) and c != "SY"])

# ---------------------------------------------------------------------------
# Readable axis labels + tick formats. Raw column aliases like "GradRate_4yr"
# or "PerPupil" are fine as keys but unfriendly on a chart axis. AXIS_LABELS
# maps each alias to plain English with its unit; AXIS_TICKFMT gives the
# matching Plotly d3 tick format. Percent-type columns are stored 0-1 (see the
# DART normalization in build_master_panel + the demographic *_pct columns), so
# ".0%" renders them as whole-number percents.
# ---------------------------------------------------------------------------
AXIS_LABELS = {
    # Demographics (0-1 fractions)
    "Enrollment": "Cumulative enrollment (students)",
    "ELL_pct": "English learners (%)",
    "LowIncome_pct": "Low-income students (%)",
    "SPED_pct": "Students with disabilities (%)",
    "HighNeeds_pct": "High-needs students (%)",
    "Hispanic_pct": "Hispanic/Latino students (%)",
    "Black_pct": "Black students (%)",
    "Asian_pct": "Asian students (%)",
    "White_pct": "White students (%)",
    "FirstLangNotEnglish_pct": "First language not English (%)",
    # Outcomes (0-1). Grad rate + AP 3+ are re-sourced from the official files
    # (graduation_rates adjusted cohort / ap_performance exam-weighted); the
    # rest are DART percent rates normalized to 0-1.
    "GradRate_4yr": "4-yr graduation rate — adjusted cohort (%)",
    "GradRate_5yr": "5-yr graduation rate (%)",
    "Promotion_9to10": "9th-to-10th promotion rate (%)",
    "Dropout": "Annual dropout rate (%)",
    "ChronicAbsence": "Chronically absent (%)",
    "AttendanceRate": "Attendance rate (%)",
    "Suspension_pct": "Suspended at least once (%)",
    "MCAS_G10_ELA": "Grade-10 MCAS ELA meeting/exceeding (%)",
    "MCAS_G10_Math": "Grade-10 MCAS math meeting/exceeding (%)",
    "AP_Enrolled": "Juniors/seniors in AP or IB (%)",
    "AP_exams_3plus": "% of AP exams scoring 3+",
    "FAFSA": "Grade-12 FAFSA completion (%)",
    "ImmediateCollege": "Enrolled in college the next fall (%)",
    "College_2yr": "Graduates at a 2-yr college (%)",
    "College_4yr": "Graduates at a 4-yr college (%)",
    "CollegePersist": "Persisted in college 2 years (%)",
    "MassCore": "Completed MassCore (%)",
    # Non-percent DART (native scale)
    "SGP_ELA": "Student growth percentile — ELA",
    "SGP_Math": "Student growth percentile — math",
    "SAT_Math": "SAT math (200–800)",
    "SAT_Reading": "SAT reading (200–800)",
    # Finance ($)
    "PerPupil": "Per-pupil spending ($)",
    "AvgTeacherSalary": "Average teacher salary ($)",
    "TeachersPer100": "Teachers per 100 students",
}

# Columns that are stored as 0-1 fractions and should render as percents.
_PCT_COLS = {
    "ELL_pct", "LowIncome_pct", "SPED_pct", "HighNeeds_pct", "Hispanic_pct",
    "Black_pct", "Asian_pct", "White_pct", "FirstLangNotEnglish_pct",
    "GradRate_4yr", "GradRate_5yr", "Promotion_9to10", "Dropout",
    "ChronicAbsence", "AttendanceRate", "Suspension_pct", "MCAS_G10_ELA",
    "MCAS_G10_Math", "AP_Enrolled", "AP_exams_3plus", "FAFSA", "ImmediateCollege",
    "College_2yr", "College_4yr", "CollegePersist", "MassCore",
}
_DOLLAR_COLS = {"PerPupil", "AvgTeacherSalary"}


def axis_label(col: str) -> str:
    """Plain-English axis title for a panel column (falls back to the alias)."""
    return AXIS_LABELS.get(col, col)


def axis_tickformat(col: str) -> str | None:
    """Plotly d3 tick format matching the column's scale, or None."""
    if col in _PCT_COLS:
        return ".0%"
    if col in _DOLLAR_COLS:
        return "$,.0f"
    return None


# ---------------------------------------------------------------------------
# Latest-year cross-section — one row per school, most recent value per
# metric. Shared by the strongest-pairs scan, the curated correlations, and
# the custom explorer below.
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _latest_per_school(p: pd.DataFrame) -> pd.DataFrame:
    """For each (school, column), take the most recent year that has a value.
    Avoids dropping schools where the very latest row happens to be NaN for
    the indicator of interest."""
    static_cols = ["ORG_CODE", "ORG_NAME", "DIST_NAME"]
    metric_cols = [c for c in p.columns if c not in static_cols + ["SY"]]
    rows = []
    for org_code, grp in p.groupby("ORG_CODE"):
        grp = grp.sort_values("SY")
        row = {"ORG_CODE": org_code}
        for c in static_cols:
            if c in grp.columns and not grp[c].dropna().empty:
                row[c] = grp[c].dropna().iloc[-1]
        for c in metric_cols:
            non_null = grp[c].dropna()
            row[c] = non_null.iloc[-1] if not non_null.empty else None
        rows.append(row)
    out = pd.DataFrame(rows)
    return out


latest = _latest_per_school(panel)
latest["City"] = latest["DIST_NAME"]
latest["is_lehs"] = latest["ORG_CODE"] == "01630510"
# Disambiguate Lynn-the-district from LEHS-the-school in chart labels.
# `City` is the district name (used in tables); `School` is the unambiguous
# display label used on scatter text + tooltips.
latest["School"] = latest.apply(
    lambda r: "Lynn English" if r["is_lehs"] else r["City"],
    axis=1,
)

# ---------------------------------------------------------------------------
# Strongest relationships right now — an O(k²) scan over every numeric metric
# pair on the latest-year cross-section, surfacing the top |r| pairs so the
# reader doesn't have to hunt through the explorer combinatorics by hand.
# ---------------------------------------------------------------------------

st.header("Strongest Relationships Right Now")
st.caption(
    "Every numeric metric pair in the panel, scanned on the latest year per "
    "school. Top 5 by |r|; pairs with |r| < 0.40, fewer than 10 schools, or a "
    "trivial mechanical link are dropped. The confounder note above applies "
    "doubly here — a strong r is a pattern, not a cause."
)

# Pairs that are mechanically or definitionally linked — the same instrument
# in two subjects, near-complements, or part/whole shares of the same total.
# A high |r| inside these groups is true but uninformative, so the scan skips
# them. Pairs where BOTH sides are demographic-composition columns are skipped
# for the same reason: they describe who lives in each city, not anything a
# school does.
_NEAR_DUP_GROUPS = [
    {"GradRate_4yr", "GradRate_5yr", "Dropout"},
    {"MCAS_G10_ELA", "MCAS_G10_Math"},
    {"SGP_ELA", "SGP_Math"},
    {"SAT_Math", "SAT_Reading"},
    {"ChronicAbsence", "AttendanceRate"},
    {"ImmediateCollege", "College_2yr", "College_4yr", "CollegePersist"},
]
_DEMOGRAPHIC_COLS = {
    "Enrollment", "ELL_pct", "LowIncome_pct", "SPED_pct", "HighNeeds_pct",
    "Hispanic_pct", "Black_pct", "Asian_pct", "White_pct",
    "FirstLangNotEnglish_pct",
}


def _is_near_duplicate(a: str, b: str) -> bool:
    if a == b:
        return True
    if a in _DEMOGRAPHIC_COLS and b in _DEMOGRAPHIC_COLS:
        return True
    return any(a in g and b in g for g in _NEAR_DUP_GROUPS)


@st.cache_data(show_spinner=False)
def strongest_pairs(
    latest_df: pd.DataFrame,
    cols: tuple[str, ...],
    min_abs_r: float = 0.40,
    min_n: int = 10,
    top_k: int = 5,
) -> pd.DataFrame:
    """Pearson r for all metric pairs on the latest-year cross-section.

    Cached because the scan is O(k²) over ~30 metrics; it only re-runs when
    the underlying panel changes.
    """
    rows = []
    for i, x in enumerate(cols):
        for y in cols[i + 1:]:
            if _is_near_duplicate(x, y):
                continue
            s = pearson(latest_df, x, y)
            if pd.isna(s["r"]) or abs(s["r"]) < min_abs_r or s["n"] < min_n:
                continue
            rows.append({"x": x, "y": y, "r": s["r"], "n": s["n"]})
    if not rows:
        return pd.DataFrame(columns=["x", "y", "r", "n"])
    out = pd.DataFrame(rows)
    return out.reindex(out["r"].abs().sort_values(ascending=False).index).head(top_k)


_top_pairs = strongest_pairs(latest, tuple(NUMERIC_COLS))
if _top_pairs.empty:
    st.info("No metric pair clears |r| ≥ 0.40 on the current panel.")
else:
    st.dataframe(
        pd.DataFrame({
            "Metric A": _top_pairs["x"].map(axis_label),
            "Metric B": _top_pairs["y"].map(axis_label),
            "Pearson r": _top_pairs["r"].map(lambda v: f"{v:+.2f}"),
            "Direction & strength": _top_pairs["r"].map(interpret_r),
            "n (schools)": _top_pairs["n"].astype(int).to_numpy(),
        }),
        width="stretch", hide_index=True,
    )
    st.caption(
        "Excluded as trivial: self pairs, same-instrument subject pairs "
        "(e.g., MCAS ELA vs. math), near-complements (attendance vs. chronic "
        "absence), part/whole college-going shares, and pairs where both "
        "sides are demographic-composition columns. Recreate any row in the "
        "Custom Correlation Explorer below to see the scatter."
    )

st.divider()

# ---------------------------------------------------------------------------
# Curated correlations
# ---------------------------------------------------------------------------

st.header("Curated Correlations")
st.caption(
    "Cross-domain questions across all 26 gateway-city HS. Each scatter uses "
    "the most recent year for which both metrics are available per school."
)

curated_pairs = [
    ("PerPupil", "GradRate_4yr", "Does per-pupil spending correlate with graduation?"),
    ("PerPupil", "MCAS_G10_Math", "Does per-pupil spending correlate with grade-10 math?"),
    ("ELL_pct", "GradRate_4yr", "How does ELL share relate to graduation?"),
    ("ChronicAbsence", "GradRate_4yr", "Chronic absence vs. graduation"),
    ("Promotion_9to10", "GradRate_4yr", "9-to-10 promotion vs. graduation"),
    ("AP_Enrolled", "ImmediateCollege", "AP enrollment vs. immediate college enrollment"),
    ("FAFSA", "ImmediateCollege", "FAFSA completion vs. immediate college"),
    ("LowIncome_pct", "MCAS_G10_ELA", "Low income share vs. grade-10 ELA"),
    ("AvgTeacherSalary", "GradRate_4yr", "Teacher salary vs. graduation"),
]

for x, y, label in curated_pairs:
    if x not in latest.columns or y not in latest.columns:
        continue
    sub = latest[["City", "School", x, y, "is_lehs"]].dropna()
    if len(sub) < 5:
        continue
    stats = pearson(sub, x, y)
    with st.expander(f"{label}  ·  r = {stats['r']:+.2f}  ({interpret_r(stats['r'])})"):
        sub["highlight"] = sub["is_lehs"].map({True: "LEHS", False: "Other Gateway HS"})
        fig = px.scatter(
            sub, x=x, y=y, text="School", color="highlight",
            color_discrete_map={"LEHS": LEHS_GOLD, "Other Gateway HS": GATEWAY_PEER_COLOR},
            trendline="ols",
            hover_data={"City": True, "School": False, "highlight": False},
        )
        fig.update_traces(textposition="top center", textfont_size=10)
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_title=axis_label(x), yaxis_title=axis_label(y),
            xaxis_tickformat=axis_tickformat(x), yaxis_tickformat=axis_tickformat(y),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            f"Pearson r = {stats['r']:+.3f} (p = {stats['p']:.3f}, n = {stats['n']}). "
            f"**Caveat:** correlation across {stats['n']} gateway-city high schools "
            f"doesn't establish cause."
        )

st.divider()

# ---------------------------------------------------------------------------
# Custom explorer
# ---------------------------------------------------------------------------

st.header("Custom Correlation Explorer")
st.markdown("Pick any two metrics from the panel.")

c1, c2 = st.columns(2)
with c1:
    x_var = qp_selectbox("X variable", NUMERIC_COLS, key="corr_x",
                         index=NUMERIC_COLS.index("PerPupil") if "PerPupil" in NUMERIC_COLS else 0)
with c2:
    y_var = qp_selectbox("Y variable", NUMERIC_COLS, key="corr_y",
                         index=NUMERIC_COLS.index("GradRate_4yr") if "GradRate_4yr" in NUMERIC_COLS else 1)

scope = qp_radio(
    "Scope",
    ["Gateway HS (cross-section, latest year)",
     "All gateway HS x all years (panel)"],
    key="corr_scope",
    horizontal=True,
)

if scope.startswith("Gateway HS (cross"):
    data = latest[["ORG_CODE", "City", "School", x_var, y_var, "is_lehs"]].dropna()
else:
    data = panel[["SY", "ORG_CODE", "DIST_NAME", x_var, y_var]].dropna()
    data["City"] = data["DIST_NAME"]
    data["is_lehs"] = data["ORG_CODE"] == "01630510"
    data["School"] = data.apply(
        lambda r: "Lynn English" if r["is_lehs"] else r["City"],
        axis=1,
    )

if len(data) >= 3:
    data["highlight"] = data["is_lehs"].map({True: "LEHS", False: "Other"})
    fig = px.scatter(
        data, x=x_var, y=y_var, color="highlight",
        color_discrete_map={"LEHS": LEHS_GOLD, "Other": GATEWAY_PEER_COLOR},
        trendline="ols",
        hover_data={"School": True, "City": True, "highlight": False},
    )
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_title=axis_label(x_var), yaxis_title=axis_label(y_var),
        xaxis_tickformat=axis_tickformat(x_var), yaxis_tickformat=axis_tickformat(y_var),
    )
    st.plotly_chart(fig, width="stretch")

    # Download exactly what's plotted: one row per point with the school
    # label(s) and the two selected metrics (plus SY in panel scope).
    _dl_cols = list(dict.fromkeys(
        c for c in ["SY", "School", "City", x_var, y_var] if c in data.columns
    ))
    csv_download(
        data[_dl_cols],
        f"explorer_{x_var}_vs_{y_var}.csv",
        label="⬇ Download this scatter's data (CSV)",
        key="dl_explorer_scatter",
    )

    stats = pearson(data, x_var, y_var)
    reg = regression_line(data, x_var, y_var)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Pearson r", f"{stats['r']:+.3f}")
    with c2: st.metric("p-value", f"{stats['p']:.4f}")
    with c3: st.metric("R²", f"{reg['r_squared']:.3f}")
    with c4: st.metric("n", f"{stats['n']:,}")

    st.caption(f"**Interpretation:** {interpret_r(stats['r'])}")
else:
    st.info("Not enough overlapping data points for these two variables.")

st.divider()

# ---------------------------------------------------------------------------
# Time-lagged within-school correlation
# ---------------------------------------------------------------------------

st.header("Time-Lagged Correlations — Does X today predict Y N years later?")
st.markdown(
    "Pairs the same school's value of metric X in year *Y* with its value of "
    "metric Y in year *Y+lag*. Useful for asking *predictive* questions across "
    "the school cohort lifecycle (e.g., does 9th-grade chronic absenteeism "
    "predict 12th-grade graduation 3 years later?). Each dot is one "
    "(school, base-year) pair across all 26 gateway HS x all years."
)

c1, c2, c3 = st.columns([3, 3, 2])
with c1:
    x_var_lag = st.selectbox(
        "Predictor (X) — measured in base year",
        options=NUMERIC_COLS,
        index=NUMERIC_COLS.index("ChronicAbsence") if "ChronicAbsence" in NUMERIC_COLS else 0,
        key="lag_x",
    )
with c2:
    y_var_lag = st.selectbox(
        "Outcome (Y) — measured in base year + lag",
        options=NUMERIC_COLS,
        index=NUMERIC_COLS.index("GradRate_4yr") if "GradRate_4yr" in NUMERIC_COLS else 1,
        key="lag_y",
    )
with c3:
    lag_years = st.slider("Lag (years)", 0, 6, 3, key="lag_n")

# Build the lagged join: take the panel, shift Y by -lag (so Y becomes value
# at SY+lag for the same school) and merge against X at SY.
panel_for_lag = panel.dropna(subset=["SY", "ORG_CODE"]).copy()
panel_for_lag["SY"] = pd.to_numeric(panel_for_lag["SY"], errors="coerce").astype("Int64")

x_side = panel_for_lag[["SY", "ORG_CODE", "ORG_NAME", "DIST_NAME", x_var_lag]].rename(
    columns={x_var_lag: "x_val"}
).dropna(subset=["x_val", "SY"])
y_side = panel_for_lag[["SY", "ORG_CODE", y_var_lag]].rename(
    columns={y_var_lag: "y_val", "SY": "SY_target"}
).dropna(subset=["y_val", "SY_target"])

# join condition: y_side.SY_target == x_side.SY + lag
x_side["SY_target"] = x_side["SY"] + lag_years
lagged = x_side.merge(y_side, on=["SY_target", "ORG_CODE"], how="inner")
lagged["is_lehs"] = lagged["ORG_CODE"] == "01630510"
lagged["highlight"] = lagged["is_lehs"].map({True: "LEHS", False: "Other"})
# Use "Lynn English" for LEHS rows so the tooltip doesn't read just "Lynn"
# (which would be ambiguous with Lynn the district).
lagged["pair_label"] = (
    lagged.apply(
        lambda r: ("Lynn English" if r["is_lehs"] else (r["DIST_NAME"] or "")),
        axis=1,
    )
    + " " + lagged["SY"].astype(str) + " -> " + lagged["SY_target"].astype(str)
)

if len(lagged) >= 5:
    fig = px.scatter(
        lagged, x="x_val", y="y_val", color="highlight",
        color_discrete_map={"LEHS": LEHS_GOLD, "Other": GATEWAY_PEER_COLOR},
        trendline="ols",
        hover_data=["pair_label"],
        labels={
            "x_val": f"{axis_label(x_var_lag)} — year Y",
            "y_val": f"{axis_label(y_var_lag)} — year Y + {lag_years}",
        },
    )
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_title=f"{axis_label(x_var_lag)} — year Y",
        yaxis_title=f"{axis_label(y_var_lag)} — year Y + {lag_years}",
        xaxis_tickformat=axis_tickformat(x_var_lag),
        yaxis_tickformat=axis_tickformat(y_var_lag),
    )
    st.plotly_chart(fig, width="stretch")

    stats_lag = pearson(lagged, "x_val", "y_val")
    reg_lag = regression_line(lagged, "x_val", "y_val")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Pearson r", f"{stats_lag['r']:+.3f}")
    with m2: st.metric("p-value", f"{stats_lag['p']:.4f}")
    with m3: st.metric("R²", f"{reg_lag['r_squared']:.3f}")
    with m4: st.metric("n pairs", f"{stats_lag['n']:,}")
    st.caption(f"**Interpretation:** {interpret_r(stats_lag['r'])}")
    st.caption(
        f"Each pair = one (school, base-year) observation where both metrics "
        f"exist at year Y and Y + {lag_years}. Lag = 0 collapses to a within-"
        f"year correlation across schools."
    )
    st.caption(
        "⚠️ **These points are not independent.** Each school contributes many "
        "(school, base-year) pairs, so the n above counts repeated measurements "
        "of the same schools — not n separate schools. That pseudo-replication "
        "shrinks the p-value and inflates apparent significance. Read this "
        "section for the **direction and rough strength** of a lead-lag pattern, "
        "not as a formal significance test."
    )
else:
    st.info(
        f"Not enough (school, year) pairs where both {x_var_lag} (year Y) and "
        f"{y_var_lag} (year Y + {lag_years}) are populated. Try a smaller lag "
        f"or different metrics."
    )

st.divider()

# ---------------------------------------------------------------------------
# Composite indices
# ---------------------------------------------------------------------------

st.header("Composite Indices")
st.caption("Combine multiple indicators into a single ranked score.")

st.subheader("Adjust weights")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: w_grad = st.slider("Grad rate", 0.0, 1.0, 0.3, 0.05)
with c2: w_persist = st.slider("College persist", 0.0, 1.0, 0.2, 0.05)
with c3: w_mcas = st.slider("MCAS Math", 0.0, 1.0, 0.2, 0.05)
with c4: w_chronic = st.slider("Low chronic absence", 0.0, 1.0, 0.15, 0.05)
with c5: w_ap = st.slider("AP enroll", 0.0, 1.0, 0.15, 0.05)

total_weight = w_grad + w_persist + w_mcas + w_chronic + w_ap
if total_weight > 0:
    def z(col):
        if col not in latest.columns:
            return pd.Series(0.0, index=latest.index)
        x = latest[col].dropna()
        if x.std() == 0 or len(x) < 2:
            return pd.Series(0.0, index=latest.index)
        return (latest[col] - x.mean()) / x.std()

    latest["SuccessIndex"] = (
        w_grad * z("GradRate_4yr").fillna(0)
        + w_persist * z("CollegePersist").fillna(0)
        + w_mcas * z("MCAS_G10_Math").fillna(0)
        - w_chronic * z("ChronicAbsence").fillna(0)  # NEGATIVE: low absence = higher score
        + w_ap * z("AP_Enrolled").fillna(0)
    ) / total_weight

    # The "Lynn" row in this gateway-cities table represents LEHS (the city's
    # main comprehensive HS in the gateway_main_hs manifest). Disambiguate in
    # the display so the row label can't be confused with the Lynn district.
    ranked_src = latest[["City", "ORG_NAME", "SuccessIndex", "is_lehs"]].dropna(
        subset=["SuccessIndex"]
    ).sort_values("SuccessIndex", ascending=False).reset_index(drop=True)
    ranked_src["Rank"] = ranked_src.index + 1
    ranked_src["City"] = ranked_src.apply(
        lambda r: "Lynn — LEHS" if r["is_lehs"] else r["City"],
        axis=1,
    )
    ranked = ranked_src[["Rank", "City", "ORG_NAME", "SuccessIndex"]].copy()
    ranked["SuccessIndex"] = ranked["SuccessIndex"].round(2)

    def highlight_lehs_row(row):
        return ["background-color: #FFF4D6" if row["City"] == "Lynn — LEHS" else "" for _ in row]

    st.dataframe(ranked.style.apply(highlight_lehs_row, axis=1),
                 width="stretch", hide_index=True)

    lehs_row = ranked[ranked["City"] == "Lynn — LEHS"]
    if not lehs_row.empty:
        st.success(
            f"**LEHS ranks #{int(lehs_row.iloc[0]['Rank'])} of {len(ranked)} "
            f"gateway-city main HS** on this composite index."
        )

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Master gateway-HS panel': panel,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

page_footer()

