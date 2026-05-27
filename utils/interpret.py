"""
Plain-language interpretation helpers.

Functions take metric values and return short narrative strings to display
alongside charts. This is what differentiates the dashboard from a raw data
dump.
"""

from __future__ import annotations


def sy_label(sy: int) -> str:
    """Convert a single SY integer (e.g. 2026) to academic-year label '2025-26'."""
    try:
        sy = int(sy)
    except (TypeError, ValueError):
        return ""
    return f"{sy - 1}-{str(sy)[-2:]}"


def yoy_delta(current: float, previous: float, unit: str = "pts") -> str:
    """Year-over-year change phrase: 'up 3.2 pts vs. last year' or similar."""
    if previous is None or current is None:
        return ""
    diff = current - previous
    if abs(diff) < 0.1:
        return "essentially unchanged from last year"
    direction = "up" if diff > 0 else "down"
    return f"{direction} {abs(diff):.1f} {unit} vs. last year"


def vs_peer(lehs_value: float, peer_avg: float, unit: str = "pts", peer_name: str = "peer average") -> str:
    """Comparison phrase: 'LEHS is 4.1 pts above the gateway peer average.'"""
    if lehs_value is None or peer_avg is None:
        return ""
    diff = lehs_value - peer_avg
    if abs(diff) < 0.5:
        return f"essentially at the {peer_name}"
    direction = "above" if diff > 0 else "below"
    return f"{abs(diff):.1f} {unit} {direction} the {peer_name}"


def percentile_phrase(rank: int, total: int) -> str:
    """'ranks 8th of 26 gateway-city high schools' style phrase."""
    if rank is None or total is None:
        return ""
    return f"ranks {rank} of {total}"


def trend_phrase(values: list[float], unit: str = "pts") -> str:
    """Multi-year trend description."""
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return ""
    first, last = clean[0], clean[-1]
    diff = last - first
    if abs(diff) < 0.5:
        return f"largely flat over the period (~{first:.1f} → {last:.1f})"
    direction = "rising" if diff > 0 else "falling"
    return f"{direction} from {first:.1f} to {last:.1f} ({diff:+.1f} {unit})"


# ---------------------------------------------------------------------------
# Methodology-break notes for charts that cross known DESE methodology
# changes. Returned text is meant to drop into st.caption() under a chart.
# ---------------------------------------------------------------------------


def sgp_methodology_note() -> str:
    """Note for any chart showing AVG_SGP across years.

    DESE changed SGP from median to mean starting SY 2018, and used a
    COVID-baseline SGP for SY 2019-2021 (cohort-referenced thereafter).
    """
    return (
        "**About SGP (Student Growth Percentile):** measures a student's growth "
        "vs. academic peers who scored similarly the prior year — 50 = average "
        "growth, higher = faster growth. DESE reports AVG_SGP as the median in "
        "SY 2017 and as the mean from SY 2018 onward, and the SY 2019–2021 "
        "values use a COVID-era baseline. Treat trend lines across those years "
        "as directional rather than precise."
    )


def chronic_absenteeism_methodology_note() -> str:
    """Note for any chart showing PCT_CHRON_ABS_10 / PCT_CHRON_ABS_20."""
    return (
        "**Chronic absenteeism** is DESE's accountability measure: the share "
        "of students who missed **10% or more of enrolled school days** in a "
        "given year (about 18 days in a 180-day calendar). It includes both "
        "excused and unexcused absences. A separate ≥20% threshold is also "
        "published for students missing roughly a month or more."
    )


def sat_methodology_note() -> str:
    """Note for any chart showing SAT scores across multiple years.

    Two known discontinuities: (1) the College Board redesigned the SAT in
    2016, so DESE switched to a single Reading & Writing scaled score in
    SY 2017 — pre-2017 rows have only a Math score; (2) when a district
    expands to a school-day universal-SAT model, the takers count jumps and
    average scores typically drop because the testing population now
    includes students who would not have self-selected into the test.
    """
    return (
        "**About SAT scores:** the test was redesigned in 2016; from SY 2017 "
        "onward DESE reports a single combined Reading & Writing score plus "
        "Math (each scaled 200–800), and pre-2017 rows show Math only. When "
        "the **takers count jumps sharply** (e.g., a school-day SAT mandate), "
        "scores typically fall: the testing pool now includes students who "
        "previously opted out, not because the school got worse."
    )
