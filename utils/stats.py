"""Lightweight statistical helpers for proportion comparisons.

DESE reports school-level percentages without uncertainty bands. For a
school of 50 students, a 5-percentage-point year-over-year change is
mostly noise; for a school of 500, it's a real signal. Mixing those
together — which the report cards do — leads readers to mis-rank
schools and to mis-read year-over-year drift.

These helpers compute:
  * Wilson 95% confidence interval for a single proportion.
  * Two-proportion z-test (p-value + effect size) for subgroup gaps.

Both wrap `statsmodels` directly so we get vetted implementations instead
of rolling our own. The functions are intentionally NaN-tolerant so they
can be applied row-wise across DESE data where small subgroups are blanked.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import (
    proportion_confint,
    proportions_ztest,
)

ALPHA = 0.05  # 95 % CI


def wilson_ci(k: float | int | None, n: float | int | None,
              alpha: float = ALPHA) -> tuple[float, float] | tuple[float, float]:
    """Return the Wilson 95% CI for a proportion k/n, or (nan, nan) if invalid.

    Wilson (vs. normal-approximation) handles small n and edge values near
    0 or 1 without going outside [0, 1].
    """
    if k is None or n is None:
        return (float("nan"), float("nan"))
    try:
        k_int = int(round(float(k)))
        n_int = int(round(float(n)))
    except (TypeError, ValueError):
        return (float("nan"), float("nan"))
    if n_int <= 0 or k_int < 0 or k_int > n_int:
        return (float("nan"), float("nan"))
    lo, hi = proportion_confint(count=k_int, nobs=n_int, alpha=alpha, method="wilson")
    return float(lo), float(hi)


def wilson_ci_from_pct(pct: float | None, n: float | int | None,
                        alpha: float = ALPHA) -> tuple[float, float]:
    """Same as wilson_ci, but given the proportion (0-1) and n instead of count + n.

    Useful for DESE rows that publish *_PCT but not the underlying count.
    """
    if pct is None or n is None:
        return (float("nan"), float("nan"))
    try:
        p = float(pct)
        n_int = int(round(float(n)))
    except (TypeError, ValueError):
        return (float("nan"), float("nan"))
    if not (0.0 <= p <= 1.0) or n_int <= 0:
        return (float("nan"), float("nan"))
    k = int(round(p * n_int))
    return wilson_ci(k, n_int, alpha=alpha)


@dataclass
class GapTest:
    """Result of comparing two proportions."""

    delta: float          # p2 - p1, in proportion units (e.g. 0.05 = 5 pts)
    p_value: float        # two-sided z-test p-value
    cohens_h: float       # standardized effect size; 0.2/0.5/0.8 = small/med/large
    significant: bool     # True if p_value < alpha (default 0.05)

    @property
    def stars(self) -> str:
        """APA-style p-value flag: '' / '*' / '**' / '***'."""
        if math.isnan(self.p_value):
            return ""
        if self.p_value < 0.001:
            return "***"
        if self.p_value < 0.01:
            return "**"
        if self.p_value < 0.05:
            return "*"
        return ""

    @property
    def magnitude(self) -> str:
        """Plain-English label for |Cohen's h|."""
        h = abs(self.cohens_h)
        if math.isnan(h):
            return ""
        if h < 0.2:
            return "negligible"
        if h < 0.5:
            return "small"
        if h < 0.8:
            return "medium"
        return "large"


def _bad() -> GapTest:
    return GapTest(
        delta=float("nan"),
        p_value=float("nan"),
        cohens_h=float("nan"),
        significant=False,
    )


def compare_proportions(k1: float, n1: float, k2: float, n2: float,
                         alpha: float = ALPHA) -> GapTest:
    """Two-proportion z-test plus Cohen's h effect size.

    Group 2 is the *reference* (the "vs." group): delta = p2 - p1, so a
    positive delta means group 2 is higher. Returns a GapTest with NaN
    fields if any input is missing or invalid.
    """
    try:
        k1 = float(k1); n1 = float(n1)
        k2 = float(k2); n2 = float(n2)
    except (TypeError, ValueError):
        return _bad()
    if any(math.isnan(v) for v in (k1, n1, k2, n2)):
        return _bad()
    if n1 <= 0 or n2 <= 0 or k1 < 0 or k2 < 0 or k1 > n1 or k2 > n2:
        return _bad()

    p1 = k1 / n1
    p2 = k2 / n2
    # 2-proportion z-test (pooled)
    try:
        z, p_val = proportions_ztest(
            count=[int(round(k1)), int(round(k2))],
            nobs=[int(round(n1)), int(round(n2))],
            alternative="two-sided",
        )
    except Exception:
        # statsmodels can blow up on degenerate inputs (e.g., both p = 0)
        p_val = float("nan")

    # Cohen's h
    try:
        h = 2 * math.asin(math.sqrt(p2)) - 2 * math.asin(math.sqrt(p1))
    except ValueError:
        h = float("nan")

    return GapTest(
        delta=p2 - p1,
        p_value=p_val if isinstance(p_val, (int, float)) and not math.isnan(p_val) else float("nan"),
        cohens_h=h,
        significant=isinstance(p_val, (int, float)) and not math.isnan(p_val) and p_val < alpha,
    )


def add_wilson_ci_columns(
    df: pd.DataFrame,
    pct_col: str,
    n_col: str,
    out_prefix: str = "ci",
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Return a copy of df with two extra columns: {out_prefix}_lo, {out_prefix}_hi.

    Vectorized via apply — fine for the dataframe sizes used in the app
    (low thousands of rows). For larger frames consider a numpy-vectorized
    Wilson formula.
    """
    out = df.copy()
    ci = out.apply(
        lambda row: wilson_ci_from_pct(row.get(pct_col), row.get(n_col), alpha=alpha),
        axis=1,
    )
    out[f"{out_prefix}_lo"] = ci.map(lambda t: t[0])
    out[f"{out_prefix}_hi"] = ci.map(lambda t: t[1])
    return out


def subgroup_summary_md(
    df: pd.DataFrame,
    group_col: str,
    pct_col: str,
    n_col: str,
    reference_group: str = "All Students",
    *,
    group_order: list[str] | None = None,
    title: str = "Latest year — point estimates with 95% Wilson CIs",
    show_gap_test: bool = True,
    pct_format: str = ".0%",
) -> str:
    """Build a markdown summary block for a small set of subgroups.

    For each row in `df`: shows percentage, 95% Wilson CI, and n. If
    `show_gap_test`, also runs a two-proportion z-test for each non-
    reference group against `reference_group` and reports the gap, effect
    size, and significance.

    Returns markdown ready to drop into `st.markdown(...)`. NaN rows
    are skipped cleanly.
    """
    if df.empty:
        return ""
    work = df.copy()
    if group_order is not None:
        order_map = {g: i for i, g in enumerate(group_order)}
        work = work.assign(_ord=work[group_col].map(order_map).fillna(99)) \
                   .sort_values("_ord")

    ref_row = work[work[group_col] == reference_group]
    if not ref_row.empty:
        ref_pct = float(ref_row.iloc[0][pct_col])
        ref_n = float(ref_row.iloc[0][n_col])
        ref_k = int(round(ref_pct * ref_n)) if not math.isnan(ref_pct) and not math.isnan(ref_n) else None
    else:
        ref_pct = ref_n = ref_k = None

    lines = [f"**{title}**", ""]
    for _, row in work.iterrows():
        g = row[group_col]
        pct = row[pct_col]
        n = row[n_col]
        if pd.isna(pct) or pd.isna(n) or float(n) <= 0:
            continue
        lo, hi = wilson_ci_from_pct(float(pct), float(n))
        pct_s = f"{pct:{pct_format}}"
        lo_s = f"{lo:{pct_format}}" if not math.isnan(lo) else "—"
        hi_s = f"{hi:{pct_format}}" if not math.isnan(hi) else "—"
        line = f"- **{g}**: {pct_s} (95% CI {lo_s}–{hi_s}, n = {int(n):,})"
        if (
            show_gap_test
            and g != reference_group
            and ref_k is not None
            and ref_n is not None
        ):
            k = int(round(float(pct) * float(n)))
            test = compare_proportions(int(k), int(n), int(ref_k), int(ref_n))
            if test.stars:
                # compare_proportions returns delta = p_ref - p_group, so a
                # positive delta means group is BELOW reference.
                gap_pts = test.delta * 100
                direction = "above" if gap_pts < 0 else "below"
                line += (
                    f" — {abs(gap_pts):.0f} pp {direction} *{reference_group}* "
                    f"({test.magnitude} effect, {test.stars})"
                )
        lines.append(line)
    return "\n".join(lines)


def margin_phrase(test: GapTest, group_low: str, group_high: str,
                   unit_label: str = "pts") -> str:
    """Short plain-language summary of a GapTest, suitable for a chart caption.

    Example output:
        "Gap of 12 pts (large effect, p < 0.001)."
    """
    if math.isnan(test.delta) or math.isnan(test.p_value):
        return ""
    pts = test.delta * 100  # convert proportion to pp
    direction = group_high if pts >= 0 else group_low
    sig = f"p < 0.001" if test.p_value < 0.001 else f"p = {test.p_value:.3f}"
    return (
        f"{abs(pts):.0f} {unit_label} gap favoring {direction}; "
        f"{test.magnitude} effect ({sig})."
    )
