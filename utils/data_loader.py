"""
Cached data loaders for the Streamlit app.

Loads Parquet files from data/processed/ with `@st.cache_data` so the app
doesn't re-read the same files on every interaction.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.constants import PROCESSED_DIR


@st.cache_data(show_spinner=False)
def load_lehs_master() -> pd.DataFrame:
    """LEHS-only panel: one row per year, all metrics joined."""
    path = PROCESSED_DIR / "lehs_master.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_gateway_hs_panel() -> pd.DataFrame:
    """Panel of all gateway-city main HS x year x metric."""
    path = PROCESSED_DIR / "gateway_hs_panel.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_lynn_schools_panel() -> pd.DataFrame:
    """Panel of all Lynn district schools (including LEHS, Classical, Tech)."""
    path = PROCESSED_DIR / "lynn_schools_panel.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_lynn_sibling_hs() -> pd.DataFrame:
    """Lynn high schools only: LEHS, Classical, Tech, Fecteau-Leary, Frederick Douglass."""
    df = load_lynn_schools_panel()
    if df.empty:
        return df
    # filter by grade range or by school name list — implementation depends on schema
    return df


@st.cache_data(show_spinner=False)
def load_dataset(name: str) -> pd.DataFrame:
    """Load any processed Parquet file by stem name."""
    path = PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def get_dart_indicator(
    org_codes: list[str] | tuple[str, ...] | str,
    indicator: str,
    student_group: str = "All Students",
) -> pd.DataFrame:
    """Pull a single DART indicator for one or more schools.

    Returns DataFrame with SY, ORG_CODE, ORG_NAME, VALUE columns.
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
