"""Cached GeoJSON loaders for the dashboard maps."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from utils.constants import ASSETS_DIR, PROCESSED_DIR


def _file_sig(path: Path) -> tuple[int, int]:
    """File fingerprint used to invalidate cached GeoJSON/CSV reads."""
    try:
        s = path.stat()
        return (s.st_mtime_ns, s.st_size)
    except OSError:
        return (0, 0)


@st.cache_data(show_spinner=False)
def _read_geojson_cached(path_str: str, sig: tuple[int, int]) -> dict:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _read_geodataframe_cached(path_str: str, sig: tuple[int, int]) -> gpd.GeoDataFrame:
    return gpd.read_file(path_str)


@st.cache_data(show_spinner=False)
def _read_tract_neighborhoods_cached(path_str: str, sig: tuple[int, int]) -> pd.DataFrame:
    return pd.read_csv(path_str, dtype={"GEOID": str, "TRACTCE": str})


def load_geojson(name: str) -> dict:
    """Load a processed GeoJSON as a plain dict, auto-refreshing on file change."""
    path = PROCESSED_DIR / f"{name}.geojson"
    if not path.exists():
        return {"type": "FeatureCollection", "features": []}
    return _read_geojson_cached(str(path), _file_sig(path))


def load_geodataframe(name: str) -> gpd.GeoDataFrame:
    """Load a processed GeoJSON as a GeoDataFrame, auto-refreshing on file change."""
    path = PROCESSED_DIR / f"{name}.geojson"
    if not path.exists():
        return gpd.GeoDataFrame()
    return _read_geodataframe_cached(str(path), _file_sig(path))


# ---------------------------------------------------------------------------
# Census tract → neighborhood crosswalk (curated).
#
# Assignments are APPROXIMATE: vernacular neighborhoods don't align with
# tract boundaries. Each tract carries the dominant neighborhood name plus
# a confidence flag; low-confidence labels render with "approx." so charts
# never overstate precision. Source: assets/curated/lynn_tract_neighborhoods.csv
# (centroid-checked against recognized Lynn neighborhood geography).
# ---------------------------------------------------------------------------


def load_tract_neighborhoods():
    """Crosswalk DataFrame: GEOID, TRACTCE, NAMELSAD, neighborhood, confidence, notes."""
    path = ASSETS_DIR / "curated" / "lynn_tract_neighborhoods.csv"
    if not path.exists():
        return pd.DataFrame(
            columns=["GEOID", "TRACTCE", "NAMELSAD", "neighborhood", "confidence", "notes"]
        )
    return _read_tract_neighborhoods_cached(str(path), _file_sig(path))


def _tract_number(namelsad: str) -> str:
    """'Census Tract 2061' / '... , Lynn city, Massachusetts' / '2061' → '2061'."""
    s = str(namelsad)
    for tok in s.replace(",", " ").split():
        if tok.replace(".", "").isdigit():
            return tok
    return s


def tract_display_label(namelsad: str) -> str:
    """Public-facing label: 'West Lynn (Tract 2057)'.

    Low-confidence assignments get 'approx.'; unknown tracts fall back to
    the bare tract number so nothing ever renders as a raw NAMELSAD string.
    """
    xwalk = load_tract_neighborhoods()
    num = _tract_number(namelsad)
    row = xwalk[xwalk["NAMELSAD"].map(_tract_number) == num]
    if row.empty:
        return f"Tract {num}"
    hood = row.iloc[0]["neighborhood"]
    if row.iloc[0]["confidence"] == "low":
        return f"{hood}, approx. (Tract {num})"
    return f"{hood} (Tract {num})"
