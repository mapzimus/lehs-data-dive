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
