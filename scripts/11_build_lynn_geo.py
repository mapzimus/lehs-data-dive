"""
Build processed GeoJSON files ready for the dashboard maps.

Inputs (all from data/raw/gis/, produced by scripts/09_download_massgis.py):
  - schools_pt/Schools/SCHOOLS_PT.shp       — 2,448 MA public schools
  - school_districts/SCHOOLDISTRICTS_CCUV_POLY.shp — 150 district boundaries
  - towns/TOWNSSURVEY_POLYM.shp             — 351 MA towns
  - tracts_ma/tl_2024_25_tract.shp          — 1,620 MA census tracts

Outputs (data/processed/, all in EPSG:4326 WGS84 for plotly mapbox):
  - lynn_schools.geojson         — Lynn district + Lynn Tech schools w/ DESE attributes
  - lynn_tracts.geojson          — census tracts within Lynn town boundary
  - lynn_town.geojson            — Lynn town outline + neighboring towns
  - ma_districts_metrics.geojson — all MA districts + joined DESE metrics
  - ma_municipalities.geojson    — all 351 MA towns w/ gateway/Lynn flags + joined district metrics
  - gateway_hs.geojson           — main HS in each gateway city (legacy, for compatibility)

Run with:
    python scripts/11_build_lynn_geo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    GATEWAY_CITIES,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
    RAW_DIR,
)

GIS_DIR = RAW_DIR / "gis"
WEB_CRS = "EPSG:4326"  # plotly mapbox wants lat/lon

SCHOOLS_SHP = GIS_DIR / "schools_pt" / "Schools" / "SCHOOLS_PT.shp"
DISTRICTS_SHP = GIS_DIR / "school_districts" / "SCHOOLDISTRICTS_CCUV_POLY.shp"
TOWNS_SHP = GIS_DIR / "towns" / "TOWNSSURVEY_POLYM.shp"
TRACTS_SHP = GIS_DIR / "tracts_ma" / "tl_2024_25_tract.shp"


def load_lynn_town() -> gpd.GeoDataFrame:
    """Lynn town polygon + immediate neighbors for context."""
    towns = gpd.read_file(TOWNS_SHP).to_crs(WEB_CRS)
    neighbors = ["LYNN", "SWAMPSCOTT", "SAUGUS", "PEABODY", "NAHANT", "LYNNFIELD"]
    return towns[towns["TOWN"].isin(neighbors)].copy()


def load_lynn_schools() -> gpd.GeoDataFrame:
    """All schools located in Lynn town, with attributes."""
    s = gpd.read_file(SCHOOLS_SHP).to_crs(WEB_CRS)
    lynn = s[s["TOWN"].str.upper() == "LYNN"].copy()
    # Add explicit lat/lon columns for easy access in plotly
    lynn["lon"] = lynn.geometry.x
    lynn["lat"] = lynn.geometry.y
    # Standardize DIST_CODE to zero-padded 8-char for matching with our data
    lynn["DIST_CODE_8"] = lynn["DIST_CODE"].astype(str).str.zfill(8) if "DIST_CODE" in lynn.columns else ""
    return lynn


def join_enrollment_to_lynn_schools(lynn_schools: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Attach the latest enrollment-demographics row for each school by name match."""
    enr_path = PROCESSED_DIR / "enrollment_demographics.parquet"
    if not enr_path.exists():
        return lynn_schools
    enr = pd.read_parquet(enr_path)
    enr["ORG_CODE"] = enr["ORG_CODE"].astype(str).str.zfill(8)
    latest = enr.sort_values("SY").groupby("ORG_CODE").tail(1)
    keep_cols = ["ORG_CODE", "ORG_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "SWD_PCT",
                 "HN_PCT", "HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT", "MNHL_PCT"]
    latest = latest[[c for c in keep_cols if c in latest.columns]]
    # Lynn schools shapefile uses SCHID — we don't have a direct join key.
    # Fall back to fuzzy name match.
    lynn = lynn_schools.copy()
    lynn["NAME_lower"] = lynn["NAME"].str.lower().str.strip()
    latest["ORG_NAME_lower"] = latest["ORG_NAME"].str.lower().str.strip()
    merged = lynn.merge(
        latest,
        left_on="NAME_lower", right_on="ORG_NAME_lower", how="left",
    ).drop(columns=["NAME_lower", "ORG_NAME_lower"])
    return gpd.GeoDataFrame(merged, geometry=lynn.geometry.values, crs=lynn.crs)


def _load_acs_table(table_name: str) -> pd.DataFrame:
    """Load one Census ACS JSON file as a DataFrame keyed by GEOID."""
    path = RAW_DIR / "gis" / "census_acs" / f"{table_name}.json"
    if not path.exists():
        return pd.DataFrame()
    payload = json.loads(path.read_text())
    rows = payload["data"]
    header = rows[0]
    df = pd.DataFrame(rows[1:], columns=header)
    # GEOID = state + county + tract (11 chars)
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    # Convert variable columns to numeric (matches both B##### and C##### Census codes)
    var_cols = [c for c in df.columns if (c.startswith("B") or c.startswith("C")) and c.endswith("E")]
    df[var_cols] = df[var_cols].apply(pd.to_numeric, errors="coerce")
    # Apply alias mapping
    alias = payload.get("alias_map", {})
    df = df.rename(columns=alias)
    return df


def join_acs_to_tracts(tracts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Join all available Census ACS tables to the Lynn tracts by GEOID."""
    out = tracts.copy()
    out["GEOID"] = out["GEOID"].astype(str)

    # Income
    inc = _load_acs_table("median_household_income")
    if not inc.empty:
        out = out.merge(inc[["GEOID", "median_household_income"]], on="GEOID", how="left")

    # Foreign-born
    pob = _load_acs_table("place_of_birth")
    if not pob.empty:
        pob["foreign_born_pct"] = pob["foreign_born_total"] / pob["pop_total"].replace(0, pd.NA)
        out = out.merge(pob[["GEOID", "pop_total", "foreign_born_pct"]], on="GEOID", how="left")

    # Education attainment
    edu = _load_acs_table("educational_attainment")
    if not edu.empty:
        edu["bachelors_or_higher_pct"] = (
            (edu["bachelors"] + edu["masters"] + edu["professional"] + edu["doctorate"])
            / edu["edu_pop_25plus"].replace(0, pd.NA)
        )
        out = out.merge(edu[["GEOID", "bachelors_or_higher_pct"]], on="GEOID", how="left")

    # Housing burden
    hb = _load_acs_table("housing_burden")
    if not hb.empty:
        hb["severe_burden_pct"] = (
            (hb["rent_burden_30_35"] + hb["rent_burden_35_40"]
             + hb["rent_burden_40_50"] + hb["rent_burden_50plus"])
            / hb["renter_total"].replace(0, pd.NA)
        )
        out = out.merge(hb[["GEOID", "renter_total", "severe_burden_pct"]],
                        on="GEOID", how="left")

    # Language — dominant non-English language per tract
    lang = _load_acs_table("language_spoken_at_home")
    if not lang.empty:
        # All "lang_*" columns except total + english-only
        lang_cols = [c for c in lang.columns
                     if c.startswith("lang_")
                     and c not in ("lang_total", "lang_english_only")]
        if lang_cols:
            lang["non_english_total"] = lang[lang_cols].sum(axis=1)
            lang["non_english_pct"] = lang["non_english_total"] / lang["lang_total"].replace(0, pd.NA)
            # Dominant non-English language: column name of max value
            # Handle all-NA rows safely
            lang_vals = lang[lang_cols].fillna(0)
            max_vals = lang_vals.max(axis=1)
            lang["dominant_non_english_count"] = max_vals
            # idxmax with all-zeros gives column 0; mask those out
            dominant = lang_vals.idxmax(axis=1).str.replace("lang_", "")
            lang["dominant_non_english"] = dominant.where(max_vals > 0)
            # Hide for tracts with very few non-English speakers (< 20 total)
            lang.loc[lang["non_english_total"] < 20, "dominant_non_english"] = None
            out = out.merge(
                lang[["GEOID", "lang_total", "non_english_pct", "dominant_non_english",
                      "dominant_non_english_count"]],
                on="GEOID", how="left",
            )

    return out


def load_lynn_tracts(lynn_town: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Census tracts whose centroid falls inside Lynn town boundary, with ACS data joined."""
    tracts = gpd.read_file(TRACTS_SHP).to_crs(WEB_CRS)
    essex = tracts[tracts["COUNTYFP"] == "009"].copy()
    essex_projected = essex.to_crs("EPSG:26986")
    lynn_projected = lynn_town[lynn_town["TOWN"] == "LYNN"].to_crs("EPSG:26986")
    lynn_poly = lynn_projected.geometry.union_all()
    essex["_centroid"] = essex_projected.geometry.centroid
    mask = essex["_centroid"].within(lynn_poly)
    essex_in_lynn = essex[mask].drop(columns=["_centroid"]).copy()
    # Attach ACS data
    essex_in_lynn = join_acs_to_tracts(essex_in_lynn)
    return essex_in_lynn


def load_ma_districts_with_metrics() -> gpd.GeoDataFrame:
    """MA school district polygons + DESE per-district metrics.

    Reads from RAW (unfiltered) E2C CSVs so we get ALL ~400 districts statewide,
    not just the 26 we filtered to in data/processed/.
    """
    dist = gpd.read_file(DISTRICTS_SHP).to_crs(WEB_CRS)
    dist["ORG8CODE"] = dist["ORG8CODE"].astype(str).str.zfill(8)
    dist["TYPE"] = dist["TYPE"].astype(str)

    e2c_raw = RAW_DIR / "e2c_hub"

    # Enrollment (district-level only)
    enr = pd.read_csv(e2c_raw / "enrollment_demographics.csv", low_memory=False)
    enr["DIST_CODE"] = enr["DIST_CODE"].astype(str).str.zfill(8)
    enr["ORG_CODE"] = enr["ORG_CODE"].astype(str).str.zfill(8) if "ORG_CODE" in enr.columns else ""
    dist_enr = enr[
        (enr["ORG_TYPE"] == "District") & (enr["SY"] == enr["SY"].max())
    ][["DIST_CODE", "DIST_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT", "HL_PCT"]]
    dist_enr = dist_enr.rename(columns={"DIST_CODE": "ORG8CODE"})

    # Graduation rate
    grad = pd.read_csv(e2c_raw / "graduation_rates.csv", low_memory=False)
    grad["DIST_CODE"] = grad["DIST_CODE"].astype(str).str.zfill(8)
    grad_d = grad[
        (grad["STU_GRP"] == "All Students")
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        & (grad["ORG_TYPE"] == "District")
    ].sort_values("SY").groupby("DIST_CODE").tail(1)
    grad_d = grad_d[["DIST_CODE", "GRAD_PCT"]].rename(columns={"DIST_CODE": "ORG8CODE", "GRAD_PCT": "grad_4yr"})

    # District per-pupil
    dist_exp = pd.read_csv(e2c_raw / "district_expenditures.csv", low_memory=False)
    dist_exp["DIST_CODE"] = dist_exp["DIST_CODE"].astype(str).str.zfill(8)
    dist_exp["IND_VALUE"] = pd.to_numeric(dist_exp["IND_VALUE"], errors="coerce")
    pp = dist_exp[
        dist_exp["IND_SUBCAT"].str.contains("Total Expenditures", case=False, na=False)
    ].sort_values("SY").groupby("DIST_CODE").tail(1)[["DIST_CODE", "IND_VALUE"]]
    pp = pp.rename(columns={"DIST_CODE": "ORG8CODE", "IND_VALUE": "per_pupil"})

    out = dist.merge(dist_enr, on="ORG8CODE", how="left") \
              .merge(grad_d, on="ORG8CODE", how="left") \
              .merge(pp, on="ORG8CODE", how="left")
    return out


def load_ma_municipalities() -> gpd.GeoDataFrame:
    """
    All 351 MA municipalities as polygons, with:
      - is_gateway: bool, whether it's one of the 26 Gateway Cities
      - is_lynn: bool, whether this is Lynn itself
      - county: county name
      - pop_2020: population
      - joined district metrics where the town's primary school district
        can be identified (grad rate, per-pupil, % ELL, etc.)
    """
    towns = gpd.read_file(TOWNS_SHP).to_crs(WEB_CRS)

    # Gateway flag
    gateway_upper = {c.upper() for c in GATEWAY_CITIES}
    towns["is_gateway"] = towns["TOWN"].isin(gateway_upper)
    towns["is_lynn"] = towns["TOWN"] == "LYNN"

    # Friendlier population column
    if "POP2020" in towns.columns:
        towns["pop_2020"] = pd.to_numeric(towns["POP2020"], errors="coerce")

    # Title-case town names for display
    towns["town_display"] = towns["TOWN"].str.title()

    # Try to join the primary school district's DESE metrics via name match.
    # MA towns and districts aren't strictly 1:1, but for most municipalities
    # the district name contains or equals the town name.
    e2c_raw = RAW_DIR / "e2c_hub"
    if (e2c_raw / "enrollment_demographics.csv").exists():
        enr = pd.read_csv(e2c_raw / "enrollment_demographics.csv", low_memory=False)
        enr["DIST_CODE"] = enr["DIST_CODE"].astype(str).str.zfill(8)
        enr_d = enr[
            (enr["ORG_TYPE"] == "District") & (enr["SY"] == enr["SY"].max())
        ][["DIST_CODE", "DIST_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT"]]
        # Match: where DIST_NAME == town name (case-insensitive)
        enr_d["DIST_NAME_upper"] = enr_d["DIST_NAME"].astype(str).str.upper()
        towns_with_dist = towns.merge(
            enr_d, left_on="TOWN", right_on="DIST_NAME_upper", how="left",
        )

        # Add grad rate
        grad = pd.read_csv(e2c_raw / "graduation_rates.csv", low_memory=False)
        grad["DIST_CODE"] = grad["DIST_CODE"].astype(str).str.zfill(8)
        grad_d = grad[
            (grad["STU_GRP"] == "All Students")
            & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
            & (grad["ORG_TYPE"] == "District")
        ].sort_values("SY").groupby("DIST_CODE").tail(1)
        grad_d = grad_d[["DIST_CODE", "GRAD_PCT"]].rename(columns={"GRAD_PCT": "grad_4yr"})
        towns_with_dist = towns_with_dist.merge(grad_d, on="DIST_CODE", how="left")

        # Add per-pupil
        dexp = pd.read_csv(e2c_raw / "district_expenditures.csv", low_memory=False)
        dexp["DIST_CODE"] = dexp["DIST_CODE"].astype(str).str.zfill(8)
        dexp["IND_VALUE"] = pd.to_numeric(dexp["IND_VALUE"], errors="coerce")
        pp = dexp[
            dexp["IND_SUBCAT"].astype(str).str.contains("Total Expenditures", case=False, na=False)
        ].sort_values("SY").groupby("DIST_CODE").tail(1)[["DIST_CODE", "IND_VALUE"]].rename(
            columns={"IND_VALUE": "per_pupil"}
        )
        towns_with_dist = towns_with_dist.merge(pp, on="DIST_CODE", how="left")

        # Drop helper col
        towns_with_dist = towns_with_dist.drop(columns=["DIST_NAME_upper"], errors="ignore")
        return towns_with_dist

    return towns


def load_gateway_main_hs() -> gpd.GeoDataFrame:
    """One row per gateway-city main HS, with coordinates."""
    schools = gpd.read_file(SCHOOLS_SHP).to_crs(WEB_CRS)

    # Read our peer-schools manifest for the school codes
    peers_path = PROCESSED_DIR / "_peer_schools.json"
    if not peers_path.exists():
        return gpd.GeoDataFrame(columns=["geometry"], crs=WEB_CRS)
    peers = json.loads(peers_path.read_text())

    rows = []
    schools["NAME_lower"] = schools["NAME"].str.lower().str.strip()
    for city, info in peers["gateway_main_hs"].items():
        name = info.get("name")
        if not name:
            continue
        match = schools[schools["NAME_lower"] == name.lower().strip()]
        if match.empty:
            # try fuzzy
            match = schools[
                schools["TOWN"].str.upper() == city.upper()
            ]
            match = match[match["NAME"].str.contains(name.split()[0], case=False, na=False)]
        if match.empty:
            continue
        row = match.iloc[0].to_dict()
        row["city"] = city
        row["school_code_dese"] = info.get("school_code")
        row["lon"] = match.iloc[0].geometry.x
        row["lat"] = match.iloc[0].geometry.y
        rows.append(row)

    if not rows:
        return gpd.GeoDataFrame(columns=["geometry"], crs=WEB_CRS)
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=WEB_CRS)
    return gdf


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Lynn town + neighbors...")
    lynn_town = load_lynn_town()
    out = PROCESSED_DIR / "lynn_town.geojson"
    lynn_town.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(lynn_town)} polygons")

    print("\nLoading Lynn schools...")
    lynn_schools = load_lynn_schools()
    print(f"  found {len(lynn_schools)} schools in Lynn (incl. private + charter)")
    lynn_schools = join_enrollment_to_lynn_schools(lynn_schools)
    out = PROCESSED_DIR / "lynn_schools.geojson"
    lynn_schools.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(lynn_schools)} schools with attributes")

    print("\nLoading Lynn census tracts...")
    lynn_tracts = load_lynn_tracts(lynn_town)
    out = PROCESSED_DIR / "lynn_tracts.geojson"
    lynn_tracts.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(lynn_tracts)} tracts inside Lynn")

    print("\nLoading MA school districts + DESE metrics...")
    ma_districts = load_ma_districts_with_metrics()
    out = PROCESSED_DIR / "ma_districts_metrics.geojson"
    ma_districts.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(ma_districts)} districts")
    has_grad = ma_districts["grad_4yr"].notna().sum()
    has_pp = ma_districts["per_pupil"].notna().sum()
    print(f"     {has_grad} have grad rate, {has_pp} have per-pupil")

    print("\nLoading MA municipalities (all 351 towns)...")
    ma_munis = load_ma_municipalities()
    out = PROCESSED_DIR / "ma_municipalities.geojson"
    ma_munis.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(ma_munis)} municipalities")
    print(f"     {ma_munis['is_gateway'].sum()} flagged as Gateway Cities")
    if "grad_4yr" in ma_munis.columns:
        print(f"     {ma_munis['grad_4yr'].notna().sum()} matched a district by name")

    print("\nLoading gateway-city main HS...")
    gateway = load_gateway_main_hs()
    out = PROCESSED_DIR / "gateway_hs.geojson"
    gateway.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(gateway)} main HS located")

    print("\nDone.")


if __name__ == "__main__":
    main()
