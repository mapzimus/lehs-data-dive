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
