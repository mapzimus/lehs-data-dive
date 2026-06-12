"""Section 11 — Gateway Peer Comparison: LEHS vs. 25 gateway-city main HS."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    GATEWAY_PEER_COLOR,
    LEHS_GOLD,
    LEHS_NAVY,
    data_downloads_panel,
)
from utils.constants import (
    LCHS_SCHOOL_CODE,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)
from utils.data_loader import load_dataset
from utils.interpret import percentile_phrase, vs_peer

st.set_page_config(
    page_title="Gateway Peer Comparison | LEHS", page_icon="🏙️", layout="wide"
)
sidebar_attribution()

st.title("Gateway Peer Comparison")
st.markdown(
    "LEHS benchmarked against the main comprehensive high school in each of "
    "the other 25 Massachusetts Gateway Cities — similar urban contexts and "
    "demographic profiles. The two scatters below also break Lynn out into "
    "four separate points — **LEHS**, **Lynn Classical**, **Lynn Tech**, and "
    "**Lynn Public Schools as a district** — so you can see how the school "
    "compares to its same-city siblings and to the district aggregate, not "
    "only to the other 25 cities."
)

# Load the peer-schools manifest
peer_file = PROCESSED_DIR / "_peer_schools.json"
if not peer_file.exists():
    st.info("Peer comparison data is temporarily unavailable. Please check back later.")
    st.stop()
peers = json.loads(peer_file.read_text())
gateway_main = peers["gateway_main_hs"]

# Build city -> school_code dict
city_to_school = {
    city: info["school_code"] for city, info in gateway_main.items() if info.get("school_code")
}
school_to_city = {v: k for k, v in city_to_school.items()}
gateway_codes = list(city_to_school.values())

# The manifest picked Classical (01630505) as Lynn's "main HS" slot because it
# edged out LEHS on cumulative enrollment — so `gateway_codes` (from the
# manifest) contains Classical for Lynn, NOT LEHS. This page exists to
# benchmark LEHS, so LEHS must be in the frame too. We keep Classical as the
# manifest's Lynn slot (it's a real same-city sibling) and ADD LEHS + LVTI on
# top, so Lynn is represented by LEHS as the focus plus Classical/Tech/district
# as siblings. LVTI doesn't have a named constant in utils/constants yet —
# defined inline.
LVTI_SCHOOL_CODE = "01630605"
# Lynn's same-city siblings shown as their own dots so the reader can see how
# LEHS stacks against Lynn Classical and Lynn Tech inside the gateway peer
# cloud, not only against the 25 other cities' main HS.
EXTRA_LYNN_HS = [LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE, LVTI_SCHOOL_CODE]
scorecard_codes = list(dict.fromkeys(gateway_codes + EXTRA_LYNN_HS))

# "One main HS per city" pool used by the Demographically-Similar Peers
# section: the 25 OTHER gateway cities' main HS, plus LEHS standing in as
# Lynn's representative (NOT Classical, which is only the manifest's enrollment-
# weighted pick). Classical/Tech/the LPS-district aggregate are deliberately
# excluded so we don't surface LEHS's own same-city siblings as "similar peers".
similar_peer_codes = list(dict.fromkeys(
    [c for c in gateway_codes if c != LCHS_SCHOOL_CODE] + [LEHS_SCHOOL_CODE]
))

# Labels used in the scorecard + scatter — disambiguate the four Lynn rows
# from each other and from "Lynn" the district name DESE reports under.
LYNN_SCHOOL_LABELS = {
    LEHS_SCHOOL_CODE: "Lynn — LEHS",
    LCHS_SCHOOL_CODE: "Lynn — Classical",
    LVTI_SCHOOL_CODE: "Lynn — Tech",
}
LPS_DISTRICT_ROW_KEY = "01630000_DIST"   # synthetic ORG_CODE used in scorecard only
LPS_DISTRICT_LABEL   = "Lynn — LPS district"

enrollment = load_dataset("enrollment_demographics")
dart = load_dataset("dart_success_after_hs")
grad = load_dataset("graduation_rates")
ap_perf = load_dataset("ap_performance")
school_exp = load_dataset("school_expenditures")
dist_exp = load_dataset("district_expenditures")
acct = load_dataset("accountability_summary")

if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Build the scorecard panel
# ---------------------------------------------------------------------------

st.header("Latest-Year Scorecard")

latest_enr_year = int(enrollment["SY"].max())

# Enrollment + demographics
enr = enrollment[
    (enrollment["ORG_CODE"].isin(scorecard_codes)) & (enrollment["SY"] == latest_enr_year)
].copy()
scorecard = enr[[
    "ORG_CODE", "ORG_NAME", "DIST_NAME",
    "TOTAL_CNT", "EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT", "HL_PCT",
]].rename(columns={
    "TOTAL_CNT": "Enrollment",
    "EL_PCT": "% English Learner(s)",
    "LI_PCT": "% Low Income",
    "SWD_PCT": "% SPED",
    "HN_PCT": "% High Needs",
    "HL_PCT": "% Hispanic/Latino",
})
scorecard["City"] = scorecard.apply(
    lambda r: LYNN_SCHOOL_LABELS.get(r["ORG_CODE"], r["DIST_NAME"]),
    axis=1,
)

# Add DART indicators: graduation, immediate college, FAFSA.
# DART stores percent values as 0-100 (e.g., 81.5 for an 81.5% rate). Normalize
# to 0-1 here so every downstream `:.0%` formatter (scorecard + scatter axes)
# renders correctly. Without this, formatters multiply by another 100 and
# values display as "8150%". All current pivot_dart callers ask for percent
# indicators; if a non-percent indicator is added later, add a flag.
def pivot_dart(indicator: str, label: str) -> pd.DataFrame:
    sub = dart[
        (dart["ORG_CODE"].isin(scorecard_codes))
        & (dart["INDICATOR"] == indicator)
        & (dart["STU_GRP"] == "All Students")
    ].copy()
    sub["VALUE"] = pd.to_numeric(sub["VALUE"], errors="coerce") / 100.0
    latest = sub.sort_values("SY").groupby("ORG_CODE").tail(1)
    return latest[["ORG_CODE", "VALUE"]].rename(columns={"VALUE": label})


# 4-year graduation rate — canonical source is graduation_rates (the OFFICIAL
# 4-Year ADJUSTED COHORT rate DESE publishes), NOT DART's "4-year cohort
# graduation rate" (which tracks the un-adjusted "4-Year Graduation Rate"
# lineage and runs ~3-4 pts higher/lower year to year). graduation_rates has a
# per-school row for every gateway main HS (ORG_TYPE == "School"), so every
# city + LEHS shares the same official definition. This also matches the LPS
# district synthetic row below, which already reads graduation_rates.
def grad_4yr_official() -> pd.DataFrame:
    """Latest 4-Year Adjusted Cohort grad rate per scorecard school (0-1)."""
    if grad.empty:
        return pd.DataFrame(columns=["ORG_CODE", "4yr Grad Rate"])
    sub = grad[
        (grad["ORG_CODE"].isin(scorecard_codes))
        & (grad["ORG_TYPE"] == "School")
        & (grad["STU_GRP"] == "All Students")
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
    ].copy()
    sub["GRAD_PCT"] = pd.to_numeric(sub["GRAD_PCT"], errors="coerce")
    latest = sub.dropna(subset=["GRAD_PCT"]).sort_values("SY").groupby("ORG_CODE").tail(1)
    return latest[["ORG_CODE", "GRAD_PCT"]].rename(columns={"GRAD_PCT": "4yr Grad Rate"})


# AP "scoring 3+" — canonical source is ap_performance PCT_3_5 (the share of AP
# EXAMS scoring 3+, exam-weighted, All Subjects), NOT DART's "Jr/Sr AP test
# takers scoring 3 or above" (a per-STUDENT rate). The two answer different
# questions and differ by ~5-15 pts; the exam-weighted figure is what the
# College & Career page's by-group AP chart already uses, so sourcing it here
# keeps the whole app on one AP definition. PCT_3_5 is already 0-1.
def ap_exams_3plus() -> pd.DataFrame:
    """Latest % of AP exams scoring 3+ per scorecard school (0-1)."""
    if ap_perf.empty:
        return pd.DataFrame(columns=["ORG_CODE", "% AP exams 3+"])
    sub = ap_perf[
        (ap_perf["ORG_CODE"].isin(scorecard_codes))
        & (ap_perf["SUBJ"] == "All Subjects")
        & (ap_perf["STU_GRP"] == "All Students")
    ].copy()
    sub["PCT_3_5"] = pd.to_numeric(sub["PCT_3_5"], errors="coerce")
    latest = sub.dropna(subset=["PCT_3_5"]).sort_values("SY").groupby("ORG_CODE").tail(1)
    return latest[["ORG_CODE", "PCT_3_5"]].rename(columns={"PCT_3_5": "% AP exams 3+"})


grad_4yr = grad_4yr_official()
immediate = pivot_dart(
    "Students enrolled in postsecondary education in the immediate fall after high school graduation",
    "Immediate College",
)
fafsa = pivot_dart("Grade 12 students who completed FAFSA", "% FAFSA")
chronic = pivot_dart(
    "Chronically absent rate (% of students absent 10% or more each year)", "% Chronic Absence",
)
ap_3plus = ap_exams_3plus()

for d in [grad_4yr, immediate, fafsa, chronic, ap_3plus]:
    scorecard = scorecard.merge(d, on="ORG_CODE", how="left")

# Per-pupil spending (latest)
if not school_exp.empty:
    sp = school_exp[
        (school_exp["ORG_CODE"].isin(scorecard_codes))
        & (school_exp["IND_CAT"] == "Total A+B+C")
        & (school_exp["IND_SUBCAT"] == "Total Expenditures")
    ].copy()
    sp["IND_VALUE"] = pd.to_numeric(sp["IND_VALUE"], errors="coerce")
    sp_latest = sp.sort_values("SY").groupby("ORG_CODE").tail(1)[["ORG_CODE", "IND_VALUE"]]
    sp_latest = sp_latest.rename(columns={"IND_VALUE": "$ Per Pupil"})
    scorecard = scorecard.merge(sp_latest, on="ORG_CODE", how="left")

# State accountability: overall classification + 1-99 percentile, latest year
# per school. Joined on ORG_CODE; rows with no accountability record (e.g. the
# synthetic LPS-district row added below) simply stay blank.
if not acct.empty and {"ORG_CODE", "CLASSIFICATION", "PERCENTILE"}.issubset(acct.columns):
    acct_latest = acct.sort_values("SY").groupby("ORG_CODE").tail(1)
    scorecard = scorecard.merge(
        acct_latest[["ORG_CODE", "CLASSIFICATION", "PERCENTILE"]].rename(
            columns={"CLASSIFICATION": "State Classification", "PERCENTILE": "Acct %ile"}
        ),
        on="ORG_CODE", how="left",
    )
else:
    scorecard["State Classification"] = pd.NA
    scorecard["Acct %ile"] = pd.NA

# ---------------------------------------------------------------------------
# LPS-district synthetic row — same column shape as the school rows above
# but built from district-level datasets so the gateway scatters can show
# Lynn-as-district alongside Lynn-as-LEHS / LCHS / LVTI.
# ---------------------------------------------------------------------------

def _build_lps_district_row() -> pd.DataFrame | None:
    """Return a 1-row DataFrame matching scorecard's column set for LPS."""
    dist_enr = enrollment[
        (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (enrollment["ORG_TYPE"] == "District")
        & (enrollment["SY"] == latest_enr_year)
    ]
    if dist_enr.empty:
        return None
    d = dist_enr.iloc[0]
    row: dict = {
        "ORG_CODE":          LPS_DISTRICT_ROW_KEY,
        "ORG_NAME":          "Lynn Public Schools",
        "DIST_NAME":         "Lynn",
        "City":              LPS_DISTRICT_LABEL,
        "Enrollment":        d.get("TOTAL_CNT"),
        "% English Learner(s)": d.get("EL_PCT"),
        "% Low Income":      d.get("LI_PCT"),
        "% SPED":            d.get("SWD_PCT"),
        "% High Needs":      d.get("HN_PCT"),
        "% Hispanic/Latino": d.get("HL_PCT"),
    }

    # NOTE: dart_success_after_hs is SCHOOL-level only in our extract — it has no
    # district aggregate row and no ORG_TYPE column — so most DART indicators have
    # no district-grain value to show here. The one district metric we can source
    # honestly is the 4-year grad rate, which graduation_rates publishes as a real
    # district row (ORG_TYPE == "District").
    def _dist_grad_4yr() -> float | None:
        if grad.empty:
            return None
        # Use the exact 4-Year ADJUSTED COHORT type — same official definition as
        # the per-school rows above. A bare "4-Year" contains-match would also
        # catch the un-adjusted "4-Year Graduation Rate" and silently pick
        # whichever sorted last, mixing two definitions in one column.
        sub = grad[
            (grad["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (grad["ORG_TYPE"] == "District")
            & (grad["STU_GRP"] == "All Students")
            & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        ].copy()
        if sub.empty:
            return None
        sub["GRAD_PCT"] = pd.to_numeric(sub["GRAD_PCT"], errors="coerce")
        latest = sub.dropna(subset=["GRAD_PCT"]).sort_values("SY").tail(1)
        return float(latest["GRAD_PCT"].iloc[0]) if not latest.empty else None

    row["4yr Grad Rate"]     = _dist_grad_4yr()
    # The remaining indicators are only published per-school in our DART extract,
    # so the district aggregate row leaves them blank rather than fabricating a value.
    # (AP % of exams at district grain is intentionally left blank too — keeps the
    # district row from mixing an exam-weighted school metric with a district one.)
    row["Immediate College"] = None
    row["% FAFSA"]           = None
    row["% Chronic Absence"] = None
    row["% AP exams 3+"]     = None

    # District per-pupil spending — district_expenditures table has its own
    # "Per Pupil" / "Total Expenditures" rows.
    if not dist_exp.empty:
        pp = dist_exp[
            (dist_exp["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (dist_exp["IND_CAT"].astype(str).str.contains("Per Pupil", case=False, na=False))
            & (dist_exp["IND_SUBCAT"].astype(str).str.contains("Total Expenditures", case=False, na=False))
        ].copy()
        if not pp.empty:
            pp["IND_VALUE"] = pd.to_numeric(pp["IND_VALUE"], errors="coerce")
            latest_pp = pp.sort_values("SY").tail(1)
            row["$ Per Pupil"] = float(latest_pp["IND_VALUE"].iloc[0]) if not latest_pp.empty else None

    return pd.DataFrame([row])


lps_row = _build_lps_district_row()
if lps_row is not None and not lps_row.empty:
    scorecard = pd.concat([scorecard, lps_row], ignore_index=True)

# Categorical role used by the scatter color logic + the highlight helper.
def _lynn_role(org_code: str) -> str:
    if org_code == LEHS_SCHOOL_CODE:
        return "LEHS"
    if org_code == LCHS_SCHOOL_CODE:
        return "Lynn Classical"
    if org_code == LVTI_SCHOOL_CODE:
        return "Lynn Tech"
    if org_code == LPS_DISTRICT_ROW_KEY:
        return "LPS district"
    return "Other Gateway HS"


scorecard["lynn_role"] = scorecard["ORG_CODE"].apply(_lynn_role)

# ---------------------------------------------------------------------------
# "Where LEHS sits" — one-glance ranks on headline metrics, computed across
# the one-HS-per-city pool (25 other gateway main HS + LEHS for Lynn) so each
# rank is a true city-to-city position. Ranks sort by value (1 = highest) with
# no better/worse framing — direction depends on the metric, and the full
# distribution is in the table just below.
# ---------------------------------------------------------------------------
_summary_pool = scorecard[scorecard["ORG_CODE"].isin(similar_peer_codes)]


def _lehs_rank_line(col: str, friendly: str) -> str | None:
    """'**Friendly:** 86% — ranks 12 of 26' line, or None where data is missing."""
    if col not in _summary_pool.columns:
        return None
    vals = pd.to_numeric(_summary_pool[col], errors="coerce")
    lehs_vals = vals[_summary_pool["ORG_CODE"] == LEHS_SCHOOL_CODE]
    valid = vals.dropna()
    if lehs_vals.empty or pd.isna(lehs_vals.iloc[0]) or valid.empty:
        return None
    lehs_val = float(lehs_vals.iloc[0])
    rank = int((valid > lehs_val).sum()) + 1
    return f"**{friendly}:** {lehs_val:.0%} — {percentile_phrase(rank, len(valid))}."


_rank_lines = [
    ln for ln in (
        _lehs_rank_line("% Chronic Absence", "Chronic absence"),
        _lehs_rank_line("4yr Grad Rate", "4-year graduation rate"),
        _lehs_rank_line("% English Learner(s)", "English-learner share"),
        _lehs_rank_line("% AP exams 3+", "AP exams scoring 3+"),
    ) if ln
]
if _rank_lines:
    st.info(
        "**Where LEHS sits among the gateway-city main high schools** "
        "(one school per city; rank 1 = highest value; the school count "
        "shrinks where a school doesn't publish a metric):\n\n"
        + "\n".join(f"- {ln}" for ln in _rank_lines)
    )

scorecard = scorecard.sort_values("Enrollment", ascending=False)

# ---------------------------------------------------------------------------
# Demographic-range filter — applies to the TABLE only. Complements (does not
# replace) the z-score similar-peers section below: both sliders default to
# the full observed range, so the default view is unchanged; narrowing either
# range trims the table to schools inside both windows. Rows missing a value
# drop out only once a range is narrowed.
# ---------------------------------------------------------------------------
scorecard_view = scorecard
_el_pct = pd.to_numeric(scorecard["% English Learner(s)"], errors="coerce") * 100
_li_pct = pd.to_numeric(scorecard["% Low Income"], errors="coerce") * 100
if _el_pct.notna().any() and _li_pct.notna().any():
    _el_lo, _el_hi = int(np.floor(_el_pct.min())), int(np.ceil(_el_pct.max()))
    _li_lo, _li_hi = int(np.floor(_li_pct.min())), int(np.ceil(_li_pct.max()))
    # st.slider requires max > min — degenerate when every school shares a value.
    if _el_hi <= _el_lo:
        _el_hi = _el_lo + 1
    if _li_hi <= _li_lo:
        _li_hi = _li_lo + 1
    st.markdown(
        "**Filter the table to demographically-similar schools** — narrow "
        "either range to keep only schools inside both windows. Defaults "
        "show every row."
    )
    _fc1, _fc2 = st.columns(2)
    with _fc1:
        el_range = st.slider(
            "% English Learner", min_value=_el_lo, max_value=_el_hi,
            value=(_el_lo, _el_hi), step=1, format="%d%%",
            key="scorecard_el_range",
        )
    with _fc2:
        li_range = st.slider(
            "% Low Income", min_value=_li_lo, max_value=_li_hi,
            value=(_li_lo, _li_hi), step=1, format="%d%%",
            key="scorecard_li_range",
        )
    if el_range != (_el_lo, _el_hi) or li_range != (_li_lo, _li_hi):
        _mask = (
            _el_pct.between(el_range[0], el_range[1])
            & _li_pct.between(li_range[0], li_range[1])
        )
        scorecard_view = scorecard[_mask.fillna(False)]
        st.caption(
            f"Showing **{len(scorecard_view)}** of {len(scorecard)} rows with "
            f"% English Learner in {el_range[0]}–{el_range[1]}% and % low "
            f"income in {li_range[0]}–{li_range[1]}%. Rows missing either "
            "value are hidden while a filter is active."
        )

display_cols = [
    "City", "ORG_NAME", "Enrollment", "% English Learner(s)", "% Low Income", "% High Needs",
    "% Hispanic/Latino", "4yr Grad Rate", "Immediate College", "% FAFSA",
    "% AP exams 3+", "% Chronic Absence", "$ Per Pupil",
    "State Classification", "Acct %ile",
]
display = scorecard_view[display_cols].rename(columns={"ORG_NAME": "School"}).copy()

# Format
for col in ["% English Learner(s)", "% Low Income", "% High Needs", "% Hispanic/Latino",
            "4yr Grad Rate", "Immediate College", "% FAFSA", "% AP exams 3+", "% Chronic Absence"]:
    display[col] = display[col].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
display["Enrollment"] = display["Enrollment"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
display["$ Per Pupil"] = display["$ Per Pupil"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
display["Acct %ile"] = display["Acct %ile"].apply(lambda x: f"{int(x)}" if pd.notna(x) else "—")
display["State Classification"] = display["State Classification"].apply(
    lambda x: str(x) if pd.notna(x) and str(x).strip() else "—"
)

# Highlight Lynn rows. LEHS gets the strongest tint, the same-district
# siblings + the LPS-district row get a lighter shade so the eye still
# groups them as "Lynn" without confusing them with LEHS itself.
def highlight_lehs_row(row):
    city = str(row["City"])
    if city == "Lynn — LEHS":
        return ["background-color: #FFF4D6"] * len(row)   # gold-cream
    if city in ("Lynn — Classical", "Lynn — Tech", LPS_DISTRICT_LABEL):
        return ["background-color: #F2F6FA"] * len(row)   # very pale navy
    return [""] * len(row)

st.dataframe(display.style.apply(highlight_lehs_row, axis=1),
             use_container_width=True, hide_index=True)
st.caption(
    f"School year {latest_enr_year}. LEHS row highlighted in gold; Lynn "
    "Classical, Lynn Tech, and the LPS-district aggregate are tinted "
    "pale-navy so all four Lynn rows are easy to find among the 25 "
    "other gateway-city rows."
)
st.caption(
    "**Metric definitions.** **4yr Grad Rate** is the official DESE 4-Year "
    "*Adjusted Cohort* Graduation Rate (from the graduation-rates file), the "
    "same definition for every school and the LPS district row. **% AP exams "
    "3+** is the share of *AP exams* scoring 3 or higher (exam-weighted, all "
    "subjects), not a per-student rate. **$ Per Pupil** mixes two DESE "
    "accounting universes: the school high-school rows are *school-level* "
    "per-pupil spending (school_expenditures), while the **LPS district** row "
    "is *district-level*, all-in per-pupil spending (district_expenditures), "
    "which is normally several thousand dollars higher because it carries "
    "district-wide costs the school-level figure excludes — so compare school "
    "rows to school rows, and read the LPS row as the district total. "
    "**State Classification / Acct %ile** come from DESE's most recent "
    "accountability file: the classification is the state's overall "
    "determination for the school, and the percentile (1–99) places it among "
    "schools statewide serving similar grades. Rows without a school-level "
    "accountability record (e.g., the LPS-district aggregate) show —."
)

# ---------------------------------------------------------------------------
# Plain-language callouts: where LEHS lands vs. the gateway-city median on a
# couple of headline outcomes. Comparison is one-HS-per-city (the 25 other
# cities' main HS + LEHS standing in for Lynn) so the median/rank is a true
# city-to-city benchmark, not skewed by Lynn's Classical/Tech/district rows.
# Scorecard metrics are stored as 0-1 fractions; ×100 puts them in "pts".
# ---------------------------------------------------------------------------
peer_pool = scorecard[scorecard["ORG_CODE"].isin(similar_peer_codes)].copy()


def _lehs_callout(col: str, friendly: str, higher_is_better: bool = True) -> str | None:
    """Return a one-sentence 'LEHS is N pts above/below the gateway median,
    ranking k of N' phrase for a percent column, or None if data is missing."""
    series = pd.to_numeric(peer_pool[col], errors="coerce").dropna()
    lehs_vals = peer_pool.loc[peer_pool["ORG_CODE"] == LEHS_SCHOOL_CODE, col]
    if series.empty or lehs_vals.empty or pd.isna(lehs_vals.iloc[0]):
        return None
    lehs_val = float(lehs_vals.iloc[0])
    median = float(series.median())
    # vs_peer expects same units; convert fractions → percentage points.
    gap = vs_peer(lehs_val * 100, median * 100, unit="pts", peer_name="gateway-city median")
    # Rank: 1 = best. For "higher is better" metrics, more is better.
    ordered = series.sort_values(ascending=not higher_is_better)
    rank = int((ordered.reset_index(drop=True).values == lehs_val).argmax()) + 1
    rank_phrase = percentile_phrase(rank, len(series))
    return (
        f"On **{friendly}**, LEHS sits at **{lehs_val:.0%}** — {gap}, and "
        f"{rank_phrase} gateway-city main high schools."
    )


callouts = [
    _lehs_callout("4yr Grad Rate", "the 4-year graduation rate", higher_is_better=True),
    _lehs_callout("Immediate College", "students heading straight to college", higher_is_better=True),
]
callouts = [c for c in callouts if c]
if callouts:
    st.markdown("#### How LEHS compares, in plain language")
    for c in callouts:
        st.markdown("- " + c)
    st.caption(
        "“Gateway-city median” = the middle value across the 26 gateway cities "
        "(one main high school each, LEHS representing Lynn). Half the cities "
        "land above it, half below."
    )

st.divider()

# ---------------------------------------------------------------------------
# Scatter: per-pupil spending vs. graduation rate
# ---------------------------------------------------------------------------

st.header("Where does LEHS fall? Per-Pupil Spending vs. Outcomes")

# Color + marker per role. LEHS = gold star (biggest), LCHS = gold-outlined
# navy circle, LVTI = teal diamond, LPS-district = navy square; the 25 other
# gateway main-HS share the pale-grey cloud.
ROLE_STYLE = {
    "LEHS":             dict(color=LEHS_GOLD, symbol="star",          size=20, line_color=LEHS_NAVY, line_width=2),
    "Lynn Classical":   dict(color=LEHS_NAVY, symbol="circle",        size=14, line_color=LEHS_GOLD, line_width=2),
    "Lynn Tech":        dict(color="#26A69A", symbol="diamond",       size=14, line_color=LEHS_NAVY, line_width=1),
    "LPS district":     dict(color=LEHS_NAVY, symbol="square",        size=14, line_color="#FFFFFF", line_width=1),
    "Other Gateway HS": dict(color=GATEWAY_PEER_COLOR, symbol="circle", size=9, line_color="#FFFFFF", line_width=0),
}
ROLE_ORDER = ["Other Gateway HS", "LPS district", "Lynn Tech", "Lynn Classical", "LEHS"]


def _lynn_scatter(df: pd.DataFrame, x_col: str, y_col: str,
                  x_title: str, y_title: str,
                  x_tickformat: str, y_tickformat: str) -> go.Figure:
    """Scatter with one trace per lynn_role so each Lynn dot can have its own
    marker shape/size, plus an OLS trendline fit to ALL points."""
    fig = go.Figure()
    # Plot Other first so Lynn dots paint on top
    for role in ROLE_ORDER:
        sub = df[df["lynn_role"] == role]
        if sub.empty:
            continue
        style = ROLE_STYLE[role]
        # Show city labels for the four Lynn points; suppress for the 25
        # other cities (they declutter into the trendline).
        is_lynn = role != "Other Gateway HS"
        fig.add_trace(go.Scatter(
            x=sub[x_col], y=sub[y_col],
            mode="markers+text" if is_lynn else "markers",
            name=role,
            marker=dict(
                color=style["color"], symbol=style["symbol"], size=style["size"],
                line=dict(color=style["line_color"], width=style["line_width"]),
            ),
            text=sub["City"] if is_lynn else None,
            textposition="top center", textfont=dict(size=10, color=LEHS_NAVY),
            hovertemplate=(
                "<b>%{text}</b><br>" + x_title + ": %{x}<br>" + y_title + ": %{y}<extra></extra>"
                if is_lynn else
                "<b>%{customdata}</b><br>" + x_title + ": %{x}<br>" + y_title + ": %{y}<extra></extra>"
            ),
            customdata=sub["City"] if not is_lynn else None,
        ))
    # Trendline fit to ALL points
    try:
        valid = df.dropna(subset=[x_col, y_col])
        if len(valid) >= 3:
            xs = pd.to_numeric(valid[x_col], errors="coerce")
            ys = pd.to_numeric(valid[y_col], errors="coerce")
            m, b = np.polyfit(xs, ys, 1)
            x_fit = pd.Series([xs.min(), xs.max()])
            fig.add_trace(go.Scatter(
                x=x_fit, y=m * x_fit + b,
                mode="lines", name="OLS fit",
                line=dict(color="#90A4AE", width=2, dash="dash"),
                showlegend=False, hoverinfo="skip",
            ))
    except (TypeError, ValueError):
        pass
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_tickformat=x_tickformat,
        yaxis_tickformat=y_tickformat,
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


st.subheader("Per-pupil spending vs. 4-year graduation rate")
scatter_df = scorecard.dropna(subset=["$ Per Pupil", "4yr Grad Rate"]).copy()
if not scatter_df.empty:
    st.plotly_chart(
        _lynn_scatter(scatter_df, "$ Per Pupil", "4yr Grad Rate",
                       "$ per pupil", "4-year graduation rate",
                       "$,.0f", ".0%"),
        use_container_width=True,
    )

st.subheader("English-learner share vs. 4-year graduation rate")
scatter_df2 = scorecard.dropna(subset=["% English Learner(s)", "4yr Grad Rate"]).copy()
if not scatter_df2.empty:
    st.plotly_chart(
        _lynn_scatter(scatter_df2, "% English Learner(s)", "4yr Grad Rate",
                       "% English Learners", "4-year graduation rate",
                       ".0%", ".0%"),
        use_container_width=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Algorithmically-similar peer subset
# ---------------------------------------------------------------------------

st.header("Demographically-Similar Peers")
st.caption(
    "Rather than a hand-picked peer list, find the schools whose **demographic "
    "profile** is closest to LEHS in normalized feature space. Distance is "
    "Euclidean across the five demographic dimensions below, each z-score "
    "normalized so no single feature dominates. Note: similarity is computed "
    "against the 25 other gateway-city main HS (one school per city) — Lynn "
    "Classical, Lynn Tech, and the LPS-district aggregate are excluded here "
    "even though they appear as their own dots in the scatters above."
)

similarity_features = ["% English Learner(s)", "% Low Income", "% High Needs",
                        "% Hispanic/Latino", "Enrollment"]

# Build a clean numeric matrix — restricted to the gateway main-HS set
# (one school per city, LEHS standing in for Lynn), so we don't pick LEHS's
# same-district siblings or the LPS-district synthetic row as "similar peers".
sim_df = scorecard[scorecard["ORG_CODE"].isin(similar_peer_codes)][
    ["ORG_CODE", "City", "ORG_NAME"] + similarity_features
].copy()
sim_df = sim_df.dropna(subset=similarity_features)

if (
    not sim_df.empty
    and (sim_df["ORG_CODE"] == LEHS_SCHOOL_CODE).any()
):
    # Z-score normalize each feature so that, e.g., enrollment in students
    # doesn't drown out ELL fraction.
    X = sim_df[similarity_features].astype(float).to_numpy()
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=0)
    sd_safe = np.where(sd == 0, 1.0, sd)
    Z = (X - mu) / sd_safe

    lehs_idx = sim_df.index[sim_df["ORG_CODE"] == LEHS_SCHOOL_CODE][0]
    lehs_pos = sim_df.index.get_loc(lehs_idx)
    distances = np.sqrt(((Z - Z[lehs_pos]) ** 2).sum(axis=1))
    sim_df = sim_df.assign(_distance=distances)
    # Keep LEHS + 5 closest peers (excluding LEHS itself)
    closest = sim_df.sort_values("_distance").head(6)

    # Merge full scorecard so the display table has outcomes too
    closest_full = scorecard[scorecard["ORG_CODE"].isin(closest["ORG_CODE"])].copy()
    closest_full = closest_full.merge(
        closest[["ORG_CODE", "_distance"]], on="ORG_CODE", how="left",
    ).sort_values("_distance")

    show_cols = ["City", "ORG_NAME", "_distance"] + similarity_features + [
        "4yr Grad Rate", "Immediate College", "% FAFSA", "% AP exams 3+", "% Chronic Absence",
    ]
    show = closest_full[show_cols].rename(columns={
        "ORG_NAME": "School", "_distance": "Similarity (lower = more similar)",
    }).copy()
    show["Similarity (lower = more similar)"] = show["Similarity (lower = more similar)"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "—"
    )
    for col in ["% English Learner(s)", "% Low Income", "% High Needs", "% Hispanic/Latino",
                 "4yr Grad Rate", "Immediate College", "% FAFSA", "% AP exams 3+", "% Chronic Absence"]:
        if col in show.columns:
            show[col] = show[col].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    show["Enrollment"] = show["Enrollment"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
    st.dataframe(show.style.apply(highlight_lehs_row, axis=1),
                 use_container_width=True, hide_index=True)

    # Plain-language explanation of who landed in the top-5
    others = closest_full[closest_full["ORG_CODE"] != LEHS_SCHOOL_CODE]["City"].tolist()
    if others:
        st.markdown(
            "**Closest peers by demographic similarity:** "
            + " · ".join(f"**{c}**" for c in others)
            + ". Differences in outcomes across these schools are the "
            "most informative — same kinds of students, different "
            "institutional responses."
        )
    st.caption(
        "Limitation: similarity is computed only across the 26 gateway-city "
        "main HS in the data panel. A future iteration could draw from "
        "all-MA enrollment for a wider 'similar conditions' peer set."
    )

# ---------------------------------------------------------------------------
# Cross-link + downloads + footer
# ---------------------------------------------------------------------------

crosslink_callout(
    "**Raw peer metrics here; the state's weighted determination there.** "
    "This page lines up unadjusted rates across the gateway-city main high "
    "schools. The Accountability page shows how DESE weighs those same "
    "outcomes — achievement, growth, attendance, graduation — into Lynn "
    "English's official classification, criterion-referenced score, and "
    "statewide percentile.",
    url_path="Accountability",
    label="State Accountability →",
)

data_downloads_panel({
    "Latest-year scorecard (gateway main HS + Lynn rows)": scorecard,
    "Enrollment & demographics": enrollment,
    "DART success-after-HS indicators": dart,
    "Graduation rates": grad,
    "AP performance": ap_perf,
    "Accountability summary": acct,
})

page_footer()

