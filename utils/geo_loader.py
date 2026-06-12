"""Cached GeoJSON loaders for the dashboard maps."""

from __future__ import annotations

import json

import geopandas as gpd
import streamlit as st

from utils.constants import PROCESSED_DIR


@st.cache_data(show_spinner=False)
def load_geojson(name: str) -> dict:
    """Load a processed GeoJSON as a plain dict (for plotly choropleth_mapbox)."""
    path = PROCESSED_DIR / f"{name}.geojson"
    if not path.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(path.read_text())


@st.cache_data(show_spinner=False)
def load_geodataframe(name: str) -> gpd.GeoDataFrame:
    """Load a processed GeoJSON as a GeoDataFrame."""
    path = PROCESSED_DIR / f"{name}.geojson"
    if not path.exists():
        return gpd.GeoDataFrame()
    return gpd.read_file(path)


# ---------------------------------------------------------------------------
# Census tract → neighborhood crosswalk (curated).
#
# Assignments are APPROXIMATE: vernacular neighborhoods don't align with
# tract boundaries. Each tract carries the dominant neighborhood name plus
# a confidence flag; low-confidence labels render with "approx." so charts
# never overstate precision. Source: assets/curated/lynn_tract_neighborhoods.csv
# (centroid-checked against recognized Lynn neighborhood geography).
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def load_tract_neighborhoods():
    """Crosswalk DataFrame: GEOID, TRACTCE, NAMELSAD, neighborhood, confidence, notes."""
    import pandas as pd

    from utils.constants import ASSETS_DIR

    path = ASSETS_DIR / "curated" / "lynn_tract_neighborhoods.csv"
    if not path.exists():
        return pd.DataFrame(
            columns=["GEOID", "TRACTCE", "NAMELSAD", "neighborhood", "confidence", "notes"]
        )
    return pd.read_csv(path, dtype={"GEOID": str, "TRACTCE": str})


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
