"""
Section 12 — Cross-Topic Explorer: correlation discovery across domains.

The novel analytical layer no DESE tool provides.
"""

import json

import pandas as pd
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import (
    csv_download,
    peer_dot_scatter,
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
    "(one main high school per city, with Lynn English representing Lynn). "
    "The scatter plots break Lynn out into four colored dots — **LEHS** "
    "(gold star), **Lynn Classical**, **Lynn Tech**, and **Lynn Public Schools "
    "as a district** — against the grey gateway-peer cloud, so you can see how "
    "LEHS lands next to its same-city siblings and the district aggregate."
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

# ORG_CODEs for Lynn's same-city rows shown as their own colored dots in every
# scatter (Change: peer-dot scatters). LEHS is the focus, LCHS/LVTI are the
# same-district sibling high schools, and the Lynn district aggregate gets a
# synthetic row built from district-level files (see _build_lps_district_row).
LVTI_SCHOOL_CODE = "01630605"          # Lynn Vocational Technical Institute (Lynn Tech)
LYNN_DISTRICT_ROW_KEY = "01630000_DIST"  # synthetic ORG_CODE for the LPS-district row


def _peer_role(org_code: str) -> str:
    """Map an ORG_CODE to the role label peer_dot_scatter colors on."""
    from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE
    if org_code == LEHS_SCHOOL_CODE:
        return "LEHS"
    if org_code == LCHS_SCHOOL_CODE:
        return "Lynn Classical"
    if org_code == LVTI_SCHOOL_CODE:
        return "Lynn Tech"
    if org_code == LYNN_DISTRICT_ROW_KEY:
        return "Lynn district"
    return "Other Gateway HS"


@st.cache_data(show_spinner=False)
def build_master_panel() -> pd.DataFrame:
    """Wide panel: rows = (school_code, year), cols = key metrics from all sources.

    Beyond the 25 other gateway-city main HS + LEHS (Lynn's representative point),
    the panel ALSO carries Lynn Classical (LCHS), Lynn Tech (LVTI), and a
    synthetic Lynn-district aggregate row so every scatter can show all four Lynn
    dots against the gateway-peer cloud. A `peer_role` column tags each row.
    """
    from utils.constants import (
        LCHS_SCHOOL_CODE,
        LEHS_SCHOOL_CODE,
        LYNN_DISTRICT_CODE,
    )
    peers = json.loads((PROCESSED_DIR / "_peer_schools.json").read_text())
    gateway_codes = [
        info["school_code"] for info in peers["gateway_main_hs"].values()
        if info.get("school_code")
    ]
    # The manifest's "Lynn" slot is Classical (01630505) — it only edged out LEHS
    # on cumulative enrollment. Swap it for LEHS so LEHS is the gateway-cloud
    # member representing Lynn; Classical/Tech/district are then ADDED back as
    # their own separately-colored dots (not part of the "one HS per city" cloud).
    gateway_codes = [c for c in gateway_codes if c != LCHS_SCHOOL_CODE]
    if LEHS_SCHOOL_CODE not in gateway_codes:
        gateway_codes.append(LEHS_SCHOOL_CODE)
    # School-level codes we pull real (SY, ORG_CODE) rows for: the gateway cloud
    # plus Lynn's two sibling HS. The district aggregate is synthesized separately.
    school_codes = list(dict.fromkeys(
        gateway_codes + [LCHS_SCHOOL_CODE, LVTI_SCHOOL_CODE]
    ))

    # 1) Enrollment + demographics
    enr = load_dataset("enrollment_demographics")
    enr = enr[enr["ORG_CODE"].isin(school_codes)].copy()
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
    dart = dart[(dart["ORG_CODE"].isin(school_codes)) & (dart["STU_GRP"] == "All Students")].copy()
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
    sp = sp[sp["ORG_CODE"].isin(school_codes)].copy()
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
            (grad["ORG_CODE"].isin(school_codes))
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
            (ap["ORG_CODE"].isin(school_codes))
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

    # 6) Synthetic Lynn-district aggregate rows — one per SY — built from the
    # DISTRICT-grain files (enrollment_demographics ORG_TYPE=="District",
    # graduation_rates ORG_TYPE=="District", district_expenditures). This is the
    # same approach Gateway_Peer_Comparison._build_lps_district_row uses, lifted
    # to a multi-year panel so the district point appears in every scatter. DART
    # indicators are SCHOOL-grain only in our extract, so the district rows leave
    # those metrics NaN rather than fabricating values.
    dist_rows = _build_lynn_district_rows(LYNN_DISTRICT_CODE)
    if dist_rows is not None and not dist_rows.empty:
        panel = pd.concat([panel, dist_rows], ignore_index=True)

    # Tag every row with its peer role (drives the colored dots in scatters).
    panel["peer_role"] = panel["ORG_CODE"].apply(_peer_role)
    return panel


@st.cache_data(show_spinner=False)
def _build_lynn_district_rows(lynn_district_code: str) -> pd.DataFrame:
    """Multi-year synthetic Lynn-district rows matching the panel column shape.

    Demographics from enrollment_demographics (District grain), the 4-Year
    Adjusted Cohort grad rate from graduation_rates (District grain), and
    per-pupil from district_expenditures. Everything DART-only is left NaN.
    Returns an empty frame if the district enrollment rows aren't present.
    """
    enr = load_dataset("enrollment_demographics")
    dist_enr = enr[
        (enr["DIST_CODE"] == lynn_district_code)
        & (enr["ORG_TYPE"] == "District")
    ].copy()
    if dist_enr.empty:
        return pd.DataFrame()

    rows = dist_enr.rename(columns={
        "TOTAL_CNT": "Enrollment",
        "EL_PCT": "ELL_pct", "LI_PCT": "LowIncome_pct",
        "SWD_PCT": "SPED_pct", "HN_PCT": "HighNeeds_pct",
        "HL_PCT": "Hispanic_pct", "BAA_PCT": "Black_pct",
        "AS_PCT": "Asian_pct", "WH_PCT": "White_pct",
        "FLNE_PCT": "FirstLangNotEnglish_pct",
    })
    keep = ["SY", "Enrollment", "ELL_pct", "LowIncome_pct", "SPED_pct",
            "HighNeeds_pct", "Hispanic_pct", "Black_pct", "Asian_pct",
            "White_pct", "FirstLangNotEnglish_pct"]
    rows = rows[[c for c in keep if c in rows.columns]].copy()
    rows["ORG_CODE"] = LYNN_DISTRICT_ROW_KEY
    rows["ORG_NAME"] = "Lynn Public Schools"
    rows["DIST_NAME"] = "Lynn"

    # District 4-Year Adjusted Cohort grad rate (official, 0-1), per year.
    grad = load_dataset("graduation_rates")
    if not grad.empty:
        g = grad[
            (grad["DIST_CODE"] == lynn_district_code)
            & (grad["ORG_TYPE"] == "District")
            & (grad["STU_GRP"] == "All Students")
            & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        ].copy()
        if not g.empty:
            g["GradRate_4yr"] = pd.to_numeric(g["GRAD_PCT"], errors="coerce")
            rows = rows.merge(
                g[["SY", "GradRate_4yr"]].dropna(subset=["GradRate_4yr"]),
                on="SY", how="left",
            )

    # District per-pupil (district_expenditures has its own Per Pupil rows). NOTE
    # this is district-level all-in spending, several $k higher than the school-
    # level PerPupil on the HS rows — read the district dot as the district total.
    de = load_dataset("district_expenditures")
    if not de.empty:
        d = de[
            (de["DIST_CODE"] == lynn_district_code)
            & (de["IND_CAT"].astype(str).str.contains("Per Pupil", case=False, na=False))
            & (de["IND_SUBCAT"].astype(str).str.contains("Total Expenditures", case=False, na=False))
        ].copy()
        if not d.empty:
            d["PerPupil"] = pd.to_numeric(d["IND_VALUE"], errors="coerce")
            d = d.groupby("SY", as_index=False)["PerPupil"].mean()
            rows = rows.merge(d, on="SY", how="left")

    return rows


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
    static_cols = ["ORG_CODE", "ORG_NAME", "DIST_NAME", "peer_role"]
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
if "peer_role" not in latest.columns:
    latest["peer_role"] = latest["ORG_CODE"].apply(_peer_role)

# Disambiguate the four Lynn rows from each other and from "Lynn" the district
# name in chart labels. `City` is the district name (used in tables); `School`
# is the unambiguous per-point display label used on scatter text + tooltips.
_ROLE_LABEL = {
    "LEHS": "Lynn English",
    "Lynn Classical": "Lynn Classical",
    "Lynn Tech": "Lynn Tech",
    "Lynn district": "Lynn (district)",
}
latest["School"] = latest.apply(
    lambda r: _ROLE_LABEL.get(r["peer_role"], r["City"]),
    axis=1,
)

# One-HS-per-city cross-section (LEHS standing in for Lynn) for the statistics-
# only "Strongest Relationships" scan. The extra Lynn rows — Classical, Tech,
# the district aggregate — are shown as their own DOTS in the scatters below but
# excluded from this scan so they don't triple-weight Lynn or break the
# "26 gateway-city HS" framing the scan reports.
latest_gateway = latest[latest["peer_role"].isin(["LEHS", "Other Gateway HS"])].copy()

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


_top_pairs = strongest_pairs(latest_gateway, tuple(NUMERIC_COLS))
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

# Each tuple: (x_col, y_col, question, "why a principal cares" caption).
# Deliberately picks *non-obvious* cross-domain questions — the goal is to
# surface relationships that aren't near-tautologies (FAFSA → immediate college)
# and that a principal could actually act on. Every column is verified to exist
# in the panel below; a pair referencing a missing column is skipped, not fatal.
curated_pairs = [
    ("PerPupil", "GradRate_4yr",
     "Does per-pupil spending move graduation?",
     "If the dots are a flat cloud, spending more per student barely predicts "
     "who graduates — outcomes ride on how money is used, not how much there is."),
    ("PerPupil", "SGP_Math",
     "Does per-pupil spending buy faster math growth?",
     "Growth percentiles ask whether students gain ground year to year. A flat "
     "cloud says extra dollars alone don't accelerate learning."),
    ("ELL_pct", "SGP_ELA",
     "Do schools with more English learners show weaker ELA growth?",
     "Growth (not raw scores) controls for starting point — if it's flat, "
     "high-ELL schools are growing students just as fast despite lower snapshots."),
    ("ChronicAbsence", "SGP_Math",
     "Does chronic absence track with slower math growth?",
     "Kids who aren't in the room can't gain ground — a downward slope says "
     "attendance is an academic-growth lever, not just a compliance number."),
    ("Promotion_9to10", "College_4yr",
     "Does getting 9th graders to 10th grade predict 4-year college enrollment?",
     "9th grade is the make-or-break year; this asks whether keeping freshmen "
     "on track pays off all the way to a four-year college seat."),
    ("AP_exams_3plus", "College_4yr",
     "Do strong AP exam results track with 4-year college enrollment?",
     "AP *exams scoring 3+* is real college-level mastery, not just sitting in "
     "the class — a steep slope says rigor up front feeds four-year enrollment."),
    ("LowIncome_pct", "MassCore",
     "Do higher-poverty schools enroll fewer students in the full college-prep course load?",
     "MassCore is the course sequence colleges expect. A downward slope flags an "
     "access gap a principal can close with scheduling and counseling."),
    ("Suspension_pct", "Dropout",
     "Does the suspension rate track with the dropout rate?",
     "The discipline-to-dropout pipeline in one chart: where more students are "
     "suspended, do more eventually leave? An upward slope is a retention warning."),
    ("AvgTeacherSalary", "GradRate_4yr",
     "Does paying teachers more track with higher graduation?",
     "Tests whether teacher pay — a budget lever districts control — shows up in "
     "graduation outcomes across comparable urban schools."),
]

for x, y, question, why in curated_pairs:
    if x not in latest.columns or y not in latest.columns:
        continue
    sub = latest[["City", "School", "peer_role", x, y]].dropna(subset=[x, y])
    if len(sub) < 5:
        continue
    stats = pearson(sub, x, y)
    with st.expander(f"{question}  ·  r = {stats['r']:+.2f}  ({interpret_r(stats['r'])})"):
        st.caption(f"**Why a principal cares:** {why}")
        fig = peer_dot_scatter(
            sub, x, y,
            role_col="peer_role", label_col="School",
            x_label=axis_label(x), y_label=axis_label(y),
            x_tickformat=axis_tickformat(x), y_tickformat=axis_tickformat(y),
        )
        st.plotly_chart(fig, width="stretch", key=f"corr_curated_{x}_{y}")
        st.caption(
            f"Pearson r = {stats['r']:+.3f} (p = {stats['p']:.3f}, n = {stats['n']}). "
            f"**Caveat:** correlation across {stats['n']} gateway-city high schools "
            f"(plus Lynn's sibling schools and district) doesn't establish cause."
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
    data = latest[["ORG_CODE", "City", "School", "peer_role", x_var, y_var]].dropna(
        subset=[x_var, y_var]
    )
else:
    data = panel[["SY", "ORG_CODE", "DIST_NAME", "peer_role", x_var, y_var]].dropna(
        subset=[x_var, y_var]
    ).copy()
    data["City"] = data["DIST_NAME"]
    data["School"] = data.apply(
        lambda r: _ROLE_LABEL.get(r["peer_role"], r["City"]),
        axis=1,
    )

if len(data) >= 3:
    fig = peer_dot_scatter(
        data, x_var, y_var,
        role_col="peer_role", label_col="School",
        x_label=axis_label(x_var), y_label=axis_label(y_var),
        x_tickformat=axis_tickformat(x_var), y_tickformat=axis_tickformat(y_var),
    )
    st.plotly_chart(fig, width="stretch", key="corr_custom_explorer")

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

x_side = panel_for_lag[["SY", "ORG_CODE", "ORG_NAME", "DIST_NAME", "peer_role", x_var_lag]].rename(
    columns={x_var_lag: "x_val"}
).dropna(subset=["x_val", "SY"])
y_side = panel_for_lag[["SY", "ORG_CODE", y_var_lag]].rename(
    columns={y_var_lag: "y_val", "SY": "SY_target"}
).dropna(subset=["y_val", "SY_target"])

# join condition: y_side.SY_target == x_side.SY + lag
x_side["SY_target"] = x_side["SY"] + lag_years
lagged = x_side.merge(y_side, on=["SY_target", "ORG_CODE"], how="inner")
# Per-point label disambiguates the four Lynn rows and shows the year jump.
# Named-role points (the Lynn dots) get this drawn on the chart; the grey
# gateway cloud only shows it on hover (peer_dot_scatter handles that).
lagged["School"] = (
    lagged.apply(
        lambda r: _ROLE_LABEL.get(r["peer_role"], (r["DIST_NAME"] or "")),
        axis=1,
    )
    + " " + lagged["SY"].astype(str) + " -> " + lagged["SY_target"].astype(str)
)

if len(lagged) >= 5:
    fig = peer_dot_scatter(
        lagged, "x_val", "y_val",
        role_col="peer_role", label_col="School",
        x_label=f"{axis_label(x_var_lag)} — year Y",
        y_label=f"{axis_label(y_var_lag)} — year Y + {lag_years}",
        x_tickformat=axis_tickformat(x_var_lag),
        y_tickformat=axis_tickformat(y_var_lag),
    )
    st.plotly_chart(fig, width="stretch", key="corr_lagged")

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
st.caption(
    "Combine multiple indicators into a single ranked score. Each slider weights "
    "one metric; weights are normalized so only their *relative* sizes matter. "
    "Metrics where lower is better (chronic absence, suspension, dropout) are "
    "framed as positive sliders — turning one up rewards schools with *less* of "
    "it. Ranked across the one-main-HS-per-city gateway set, with LEHS standing "
    "in for Lynn."
)

# Metric registry for the composite index. Each entry: a slider label, the panel
# column, the +1/-1 DIRECTION (-1 = lower-is-better, so the z-score is negated so
# the slider still *feels* positive), the grouping expander, and a preset-key
# default weight per preset. Only metrics whose column exists in the panel are
# offered, so SAT/MassCore/etc. degrade gracefully if a column is ever absent.
# MCAS ELA and MCAS Math are SEPARATE entries — the owner's explicit ask.
COMPOSITE_GROUPS = [
    "Academic achievement",
    "Growth",
    "Persistence & engagement",
    "College & career",
]
# (key, label, column, direction, group)
COMPOSITE_METRICS = [
    ("mcas_ela",   "MCAS ELA (meeting/exceeding)", "MCAS_G10_ELA",  +1, "Academic achievement"),
    ("mcas_math",  "MCAS Math (meeting/exceeding)", "MCAS_G10_Math", +1, "Academic achievement"),
    ("sat_math",   "SAT Math",                     "SAT_Math",      +1, "Academic achievement"),
    ("sat_read",   "SAT Reading",                  "SAT_Reading",   +1, "Academic achievement"),
    ("sgp_ela",    "Growth (SGP) — ELA",           "SGP_ELA",       +1, "Growth"),
    ("sgp_math",   "Growth (SGP) — Math",          "SGP_Math",      +1, "Growth"),
    ("chronic",    "Low chronic absence",          "ChronicAbsence", -1, "Persistence & engagement"),
    ("attend",     "High attendance",              "AttendanceRate", +1, "Persistence & engagement"),
    ("suspend",    "Low suspension",               "Suspension_pct", -1, "Persistence & engagement"),
    ("dropout",    "Low dropout",                  "Dropout",        -1, "Persistence & engagement"),
    ("grad",       "4-year graduation",            "GradRate_4yr",   +1, "College & career"),
    ("masscore",   "MassCore completion",          "MassCore",       +1, "College & career"),
    ("ap3",        "AP exams scoring 3+",          "AP_exams_3plus", +1, "College & career"),
    ("fafsa",      "FAFSA completion",             "FAFSA",          +1, "College & career"),
    ("immediate",  "Immediate college",            "ImmediateCollege", +1, "College & career"),
    ("col4yr",     "4-year college enrollment",    "College_4yr",    +1, "College & career"),
    ("persist",    "College persistence",          "CollegePersist", +1, "College & career"),
]
# Drop metrics whose column isn't in the panel (graceful degradation).
COMPOSITE_METRICS = [m for m in COMPOSITE_METRICS if m[2] in latest_gateway.columns]

# Presets seed slider defaults. Keys are metric keys; any metric not listed in a
# preset defaults to 0. "Balanced" mirrors the old five-slider default intent.
COMPOSITE_PRESETS: dict[str, dict[str, float]] = {
    "Balanced": {
        "grad": 0.30, "persist": 0.20, "mcas_math": 0.15, "mcas_ela": 0.15,
        "chronic": 0.10, "ap3": 0.10,
    },
    "Academic only": {
        "mcas_ela": 0.30, "mcas_math": 0.30, "sat_math": 0.20, "sat_read": 0.20,
    },
    "Equity-weighted (growth)": {
        "sgp_ela": 0.40, "sgp_math": 0.40, "chronic": 0.10, "attend": 0.10,
    },
    "College-going": {
        "grad": 0.20, "masscore": 0.15, "ap3": 0.15, "fafsa": 0.10,
        "immediate": 0.15, "col4yr": 0.15, "persist": 0.10,
    },
    "Engagement & climate": {
        "chronic": 0.30, "attend": 0.25, "suspend": 0.25, "dropout": 0.20,
    },
}

_preset = st.radio(
    "Preset", list(COMPOSITE_PRESETS.keys()), horizontal=True,
    key="composite_preset",
    help="Pick a starting point, then fine-tune the sliders below.",
)

# When the preset changes, reseed every slider's session_state so the sliders
# below pick up the preset's defaults. We track the last-applied preset so a
# manual slider tweak isn't immediately overwritten on the next rerun.
_slider_keys = {m[0]: f"composite_w_{m[0]}" for m in COMPOSITE_METRICS}
if st.session_state.get("_composite_last_preset") != _preset:
    preset_weights = COMPOSITE_PRESETS[_preset]
    for mkey, skey in _slider_keys.items():
        st.session_state[skey] = float(preset_weights.get(mkey, 0.0))
    st.session_state["_composite_last_preset"] = _preset

st.subheader("Adjust weights")
weights: dict[str, float] = {}
_metrics_by_group = {g: [m for m in COMPOSITE_METRICS if m[4] == g] for g in COMPOSITE_GROUPS}
for group in COMPOSITE_GROUPS:
    group_metrics = _metrics_by_group[group]
    if not group_metrics:
        continue
    # Expand the group that the active preset actually weights, so the user sees
    # where its weight lives without hunting.
    any_weighted = any(
        st.session_state.get(_slider_keys[m[0]], 0.0) > 0 for m in group_metrics
    )
    with st.expander(group, expanded=any_weighted):
        cols = st.columns(min(len(group_metrics), 4))
        for i, (mkey, label, col, direction, _grp) in enumerate(group_metrics):
            with cols[i % len(cols)]:
                weights[mkey] = st.slider(
                    label, 0.0, 1.0, step=0.05, key=_slider_keys[mkey],
                )

total_weight = sum(weights.values())
st.metric("Total weight (before normalizing)", f"{total_weight:.2f}")

if total_weight > 0:
    _direction = {m[0]: m[3] for m in COMPOSITE_METRICS}
    _column = {m[0]: m[2] for m in COMPOSITE_METRICS}
    active = {k: w for k, w in weights.items() if w > 0}

    def z(col: str) -> pd.Series:
        """Z-score a panel column over the one-HS-per-city cross-section."""
        if col not in latest_gateway.columns:
            return pd.Series(0.0, index=latest_gateway.index)
        x = latest_gateway[col].dropna()
        if x.std() == 0 or len(x) < 2:
            return pd.Series(0.0, index=latest_gateway.index)
        return (latest_gateway[col] - x.mean()) / x.std()

    # Weighted z-sum. Each metric's z-score is multiplied by its direction so
    # lower-is-better metrics (chronic absence, suspension, dropout) contribute
    # positively when the school has LESS of them. Missing values are tracked so
    # we can exclude schools missing >25% of the weighted metrics.
    idx = latest_gateway.index
    score = pd.Series(0.0, index=idx)
    missing_weight = pd.Series(0.0, index=idx)
    for mkey, w in active.items():
        col = _column[mkey]
        zc = z(col) * _direction[mkey]
        present = latest_gateway[col].notna() if col in latest_gateway.columns else pd.Series(False, index=idx)
        score = score + w * zc.fillna(0)
        missing_weight = missing_weight + w * (~present).astype(float)

    active_total = sum(active.values())
    latest_gateway = latest_gateway.copy()
    latest_gateway["SuccessIndex"] = score / active_total
    # Exclude schools missing more than 25% of the weighted metrics (by weight)
    # — ranking them on a quarter-empty score would mislead. They render as "—".
    _missing_frac = missing_weight / active_total
    latest_gateway.loc[_missing_frac > 0.25, "SuccessIndex"] = pd.NA

    n_excluded = int((_missing_frac > 0.25).sum())

    # LEHS is the gateway-cloud member representing Lynn; label its row so it
    # can't be confused with the Lynn district.
    ranked_src = latest_gateway[["City", "ORG_NAME", "SuccessIndex", "peer_role"]].dropna(
        subset=["SuccessIndex"]
    ).sort_values("SuccessIndex", ascending=False).reset_index(drop=True)
    ranked_src["Rank"] = ranked_src.index + 1
    ranked_src["City"] = ranked_src.apply(
        lambda r: "Lynn — LEHS" if r["peer_role"] == "LEHS" else r["City"],
        axis=1,
    )
    ranked = ranked_src[["Rank", "City", "ORG_NAME", "SuccessIndex"]].copy()
    ranked["SuccessIndex"] = ranked["SuccessIndex"].round(2)

    def highlight_lehs_row(row):
        return ["background-color: #FFF4D6" if row["City"] == "Lynn — LEHS" else "" for _ in row]

    st.dataframe(ranked.style.apply(highlight_lehs_row, axis=1),
                 width="stretch", hide_index=True)

    _bits = [
        f"**{len(active)} metric(s) weighted** ({', '.join(m[1] for m in COMPOSITE_METRICS if m[0] in active)})."
    ]
    if n_excluded:
        _bits.append(
            f"{n_excluded} school(s) missing more than 25% of the weighted "
            f"metrics were excluded (shown as — / dropped from the ranking)."
        )
    st.caption(" ".join(_bits))

    lehs_row = ranked[ranked["City"] == "Lynn — LEHS"]
    if not lehs_row.empty:
        st.success(
            f"**LEHS ranks #{int(lehs_row.iloc[0]['Rank'])} of {len(ranked)} "
            f"gateway-city main HS** on this composite index."
        )
else:
    st.info("Set at least one slider above 0 to build a composite score.")

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

