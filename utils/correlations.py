"""
Correlation Lab helpers — used by pages/Correlation_Lab.py.

Cross-domain correlation analysis across the master panel.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from scipy import stats


def pearson(df: pd.DataFrame, x: str, y: str) -> dict:
    """Pearson r, p-value, n for two columns. Drops NaN rows pairwise."""
    sub = df[[x, y]].dropna()
    if len(sub) < 3:
        return {"r": np.nan, "p": np.nan, "n": len(sub)}
    r, p = stats.pearsonr(sub[x], sub[y])
    return {"r": r, "p": p, "n": len(sub)}


def spearman(df: pd.DataFrame, x: str, y: str) -> dict:
    """Spearman rank correlation."""
    sub = df[[x, y]].dropna()
    if len(sub) < 3:
        return {"rho": np.nan, "p": np.nan, "n": len(sub)}
    rho, p = stats.spearmanr(sub[x], sub[y])
    return {"rho": rho, "p": p, "n": len(sub)}


def correlation_matrix(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Pairwise Pearson r for a set of columns. Use for heatmaps."""
    return df[cols].corr()


def regression_line(df: pd.DataFrame, x: str, y: str) -> dict:
    """OLS regression: y = m*x + b. Returns slope, intercept, r-squared."""
    sub = df[[x, y]].dropna()
    if len(sub) < 3:
        return {"slope": np.nan, "intercept": np.nan, "r_squared": np.nan, "n": len(sub)}
    slope, intercept, r, p, se = stats.linregress(sub[x], sub[y])
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r ** 2,
        "p_value": p,
        "std_err": se,
        "n": len(sub),
    }


def interpret_r(r: float) -> str:
    """Plain-language description of correlation strength."""
    if np.isnan(r):
        return "insufficient data"
    abs_r = abs(r)
    direction = "positive" if r >= 0 else "negative"
    if abs_r < 0.10:
        return f"essentially no correlation ({direction})"
    if abs_r < 0.30:
        return f"weak {direction} correlation"
    if abs_r < 0.50:
        return f"moderate {direction} correlation"
    if abs_r < 0.70:
        return f"strong {direction} correlation"
    return f"very strong {direction} correlation"
