"""
Cached data loaders for the Streamlit app.

Loads Parquet files from data/processed/ with `@st.cache_data` so the app
doesn't re-read the same files on every interaction.

IMPORTANT: the cache is keyed on each file's modification time + size (see
`_parquet_sig`), so when a processed parquet is refreshed/rebuilt the cache
auto-invalidates on the next run. Without this, st.cache_data would keep
serving the previously-loaded DataFrame until a full app reboot (it does not
watch the file on disk) — which silently masked a data rebuild once before.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from utils.constants import PROCESSED_DIR


def _parquet_sig(path: Path) -> int:
    """File fingerprint (mtime-ns + size) used as part of the cache key.

    When the parquet is rebuilt, this value changes, so the cached read below
    misses and reloads fresh — no manual reboot / cache-clear required.
    """
    try:
        s = path.stat()
        return hash((s.st_mtime_ns, s.st_size))
    except OSError:
        return 0


@st.cache_data(show_spinner=False)
def _read_parquet_cached(path_str: str, sig: int) -> pd.DataFrame:
    # `sig` participates in the cache key (do NOT prefix with underscore, or
    # st.cache_data would ignore it). It changes whenever the file changes.
    return pd.read_parquet(path_str)


def _load(path: Path) -> pd.DataFrame:
    """Read a processed parquet, cached but auto-busting on file change."""
    if not path.exists():
        return pd.DataFrame()
    return _read_parquet_cached(str(path), _parquet_sig(path))


def load_lehs_master() -> pd.DataFrame:
    """LEHS-only panel: one row per year, all metrics joined."""
    return _load(PROCESSED_DIR / "lehs_master.parquet")


def load_gateway_hs_panel() -> pd.DataFrame:
    """Panel of all gateway-city main HS x year x metric."""
    return _load(PROCESSED_DIR / "gateway_hs_panel.parquet")


def load_lynn_schools_panel() -> pd.DataFrame:
    """Panel of all Lynn district schools (including LEHS, Classical, Tech)."""
    return _load(PROCESSED_DIR / "lynn_schools_panel.parquet")


def load_lynn_sibling_hs() -> pd.DataFrame:
    """Lynn high schools only: LEHS, Classical, Tech, Fecteau-Leary, Frederick Douglass."""
    df = load_lynn_schools_panel()
    if df.empty:
        return df
    # filter by grade range or by school name list — implementation depends on schema
    return df


def load_dataset(name: str) -> pd.DataFrame:
    """Load any processed Parquet file by stem name."""
    return _load(PROCESSED_DIR / f"{name}.parquet")


def get_dart_indicator(
    org_codes: list[str] | tuple[str, ...] | str,
    indicator: str,
    student_group: str = "All Students",
) -> pd.DataFrame:
    """Pull a single DART indicator for one or more schools.

    Returns DataFrame with SY, ORG_CODE, ORG_NAME, VALUE columns. Not cached
    itself — the expensive parquet read it depends on is cached in `_load`,
    and the filtering here is cheap, so this stays fresh after a data refresh.
    """
    df = load_dataset("dart_success_after_hs")
    if df.empty:
        return df
    if isinstance(org_codes, str):
        org_codes = [org_codes]
    sub = df[
        df["ORG_CODE"].isin(org_codes)
        & (df["INDICATOR"] == indicator)
        & (df["STU_GRP"] == student_group)
    ].copy()
    sub["VALUE"] = pd.to_numeric(sub["VALUE"], errors="coerce")
    return sub[["SY", "ORG_CODE", "ORG_NAME", "VALUE", "STU_CNT"]].sort_values("SY")
