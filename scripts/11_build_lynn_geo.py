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
from utils.precise_sources import (  # noqa: E402
    fetch_precise_ap,
    fetch_precise_staff_race,
)

GIS_DIR = RAW_DIR / "gis"
WEB_CRS = "EPSG:4326"  # plotly mapbox wants lat/lon
PROJ_CRS = "EPSG:26986"  # MA State Plane (meters), for simplification

# Geometry simplification tolerance (in meters in PROJ_CRS) for statewide
# polygon layers. 50m is invisible at MA-statewide zoom and shrinks file
# size dramatically (10x+ reduction common). For Lynn close-up layers we
# keep full precision.
SIMPLIFY_TOL_STATEWIDE = 50


def simplify_for_web(gdf: gpd.GeoDataFrame, tolerance_m: int = SIMPLIFY_TOL_STATEWIDE) -> gpd.GeoDataFrame:
    """Simplify polygons in projected meters, then return in web CRS."""
    if gdf.crs is None:
        return gdf
    projected = gdf.to_crs(PROJ_CRS).copy()
    projected.geometry = projected.geometry.simplify(tolerance_m, preserve_topology=True)
    return projected.to_crs(WEB_CRS)

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

    # EJScreen (env-justice) — tract-level rollup of EPA block-group indicators
    ej_path = PROCESSED_DIR / "ejscreen_lynn.parquet"
    if ej_path.exists():
        ej = pd.read_parquet(ej_path)
        if not ej.empty and "GEOID" in ej.columns:
            ej["GEOID"] = ej["GEOID"].astype(str).str.zfill(11)
            ej_keep = [c for c in ["GEOID", "ENV_INDEX", "DEMO_INDEX", "EJ_INDEX_PM25",
                                    "PM25", "OZONE", "DSLPM", "PRE1960_HOUSING"]
                       if c in ej.columns]
            out = out.merge(ej[ej_keep].drop_duplicates("GEOID"),
                            on="GEOID", how="left")

    # CDC PLACES — pivot health measures to columns, tract-level
    places_path = PROCESSED_DIR / "places_lynn.parquet"
    if places_path.exists():
        pl = pd.read_parquet(places_path)
        if not pl.empty and {"GEOID", "MEASUREID", "DATA_VALUE"}.issubset(pl.columns):
            pl["GEOID"] = pl["GEOID"].astype(str).str.zfill(11)
            # Keep a curated handful of the most useful indicators
            wanted = {
                "CASTHMA":  "asthma_pct",
                "MHLTH":    "mental_distress_pct",
                "OBESITY":  "obesity_pct",
                "CSMOKING": "smoking_pct",
                "BPHIGH":   "high_bp_pct",
                "DIABETES": "diabetes_pct",
                "LPA":      "no_leisure_phys_pct",
            }
            pl_sub = pl[pl["MEASUREID"].isin(wanted)].copy()
            if not pl_sub.empty:
                pivot = pl_sub.pivot_table(
                    index="GEOID", columns="MEASUREID",
                    values="DATA_VALUE", aggfunc="first",
                ).reset_index()
                pivot = pivot.rename(columns=wanted)
                out = out.merge(pivot, on="GEOID", how="left")

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


# Year range we expose per metric in the year-keyed schema. The map app
# binds a slider to this range. Years outside it fall back to "latest".
# Extended back to 1994 so enrollment trends can show the long view; most
# other metrics only have data from 2017+, slider degrades gracefully.
YEAR_KEYED_RANGE = list(range(1994, 2027))  # SY 1994 through SY 2026

# Student-group filter schema. DESE's STU_GRP strings → short codes baked
# into the column names. The map app uses these codes when looking up
# `metric__group` properties.
GROUP_CODE_MAP = {
    "Hispanic or Latino":          "hl",
    "Black or African American":   "baa",
    "Asian":                       "as",
    "White":                       "wh",
    "English Learners":            "ell",
    "English Learner":             "ell",
    "Former English Learners":     "fmrell",
    "Low Income":                  "li",
    "Students with Disabilities":  "swd",
    "High Needs":                  "hn",
}


def _pivot_group_keyed(df: pd.DataFrame, value_col: str, base_name: str,
                        sy_col: str = "SY", id_col: str = "DIST_CODE",
                        grp_col: str = "STU_GRP") -> pd.DataFrame:
    """Pivot long → wide on STU_GRP. Latest year only.

    Output cols: {base_name}__{group_code} where group_code is one of the
    short codes in GROUP_CODE_MAP. Skips 'All Students' (already the base
    column).
    """
    if df.empty:
        return pd.DataFrame()
    sub = df.copy()
    # Unicode-normalize STU_GRP labels
    sub[grp_col] = sub[grp_col].astype(str).str.replace("\xa0", " ", regex=False)
    sub[sy_col] = pd.to_numeric(sub[sy_col], errors="coerce")
    sub = sub.dropna(subset=[sy_col])
    sub = sub[sub[grp_col].isin(GROUP_CODE_MAP)]
    if sub.empty:
        return pd.DataFrame()
    latest = sub.sort_values(sy_col).groupby([id_col, grp_col]).tail(1)
    pivot = latest.pivot_table(
        index=id_col, columns=grp_col, values=value_col, aggfunc="first",
    )
    pivot.columns = [f"{base_name}__{GROUP_CODE_MAP[c]}" for c in pivot.columns]
    return pivot.reset_index()


def _pivot_year_keyed(df: pd.DataFrame, value_cols: list[str],
                       sy_col: str = "SY", id_col: str = "DIST_CODE") -> pd.DataFrame:
    """Pivot long → wide with columns named `{value_col}__{year}`."""
    if df.empty:
        return pd.DataFrame()
    sub = df[df[sy_col].astype(int).isin(YEAR_KEYED_RANGE)].copy()
    if sub.empty:
        return pd.DataFrame()
    sub[sy_col] = sub[sy_col].astype(int)
    pivot = sub.pivot_table(
        index=id_col, columns=sy_col, values=value_cols, aggfunc="first",
    )
    pivot.columns = [
        f"{(c[0] if isinstance(c, tuple) else c)}__{int(c[1] if isinstance(c, tuple) else c)}"
        for c in pivot.columns
    ]
    return pivot.reset_index()


def _build_district_metrics_table() -> pd.DataFrame:
    """
    Join every available district-level metric from the raw E2C CSVs into a
    single wide DataFrame keyed by DIST_CODE.

    The schema includes BOTH:
      - Latest-year columns (e.g. EL_PCT, grad_4yr) — used by side panel,
        popups, and the choropleth when no year is selected
      - Year-keyed columns (e.g. EL_PCT__2017, EL_PCT__2018, …, EL_PCT__2026)
        — used by the year slider + animation to show how values change

    Year-keyed coverage spans 2017-2026 for the metrics where year-keying
    is analytically valuable (demographics, MCAS, graduation, per-pupil,
    AP). Stable-over-time metrics (class size, teacher in-field) stay
    latest-year only to keep file size manageable.
    """
    e2c_raw = RAW_DIR / "e2c_hub"

    # ─── 1. Enrollment / demographics ─────────────────────────────────────────
    enr = pd.read_csv(e2c_raw / "enrollment_demographics.csv", low_memory=False)
    enr["DIST_CODE"] = enr["DIST_CODE"].astype(str).str.zfill(8)
    enr_d = enr[(enr["ORG_TYPE"] == "District") & (enr["SY"] == enr["SY"].max())]
    enr_cols = ["DIST_CODE", "DIST_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT",
                "HN_PCT", "HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT",
                "SWD_PCT", "FLNE_PCT", "FE_PCT"]
    out = enr_d[[c for c in enr_cols if c in enr_d.columns]].copy()

    # ─── 2. Graduation rates (4-yr + 5-yr All Students) ───────────────────────
    grad = pd.read_csv(e2c_raw / "graduation_rates.csv", low_memory=False)
    grad["DIST_CODE"] = grad["DIST_CODE"].astype(str).str.zfill(8)
    grad_4yr = grad[
        (grad["STU_GRP"] == "All Students")
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        & (grad["ORG_TYPE"] == "District")
    ].sort_values("SY").groupby("DIST_CODE").tail(1)[["DIST_CODE", "GRAD_PCT", "DRPOUT_PCT"]]
    grad_4yr = grad_4yr.rename(columns={"GRAD_PCT": "grad_4yr", "DRPOUT_PCT": "dropout_pct"})
    out = out.merge(grad_4yr, on="DIST_CODE", how="left")

    grad_5yr = grad[
        (grad["STU_GRP"] == "All Students")
        & (grad["GRAD_RATE_TYPE"] == "5-Year Adjusted Cohort Graduation Rate")
        & (grad["ORG_TYPE"] == "District")
    ].sort_values("SY").groupby("DIST_CODE").tail(1)[["DIST_CODE", "GRAD_PCT"]]
    grad_5yr = grad_5yr.rename(columns={"GRAD_PCT": "grad_5yr"})
    out = out.merge(grad_5yr, on="DIST_CODE", how="left")

    # ─── 3. MCAS grade 10 (district, all students) ────────────────────────────
    mcas = pd.read_csv(e2c_raw / "mcas_achievement.csv", low_memory=False)
    mcas["DIST_CODE"] = mcas["DIST_CODE"].astype(str).str.zfill(8)
    mcas["TEST_GRADE"] = mcas["TEST_GRADE"].astype(str)
    g10 = mcas[
        (mcas["TEST_GRADE"] == "10")
        & (mcas["STU_GRP"] == "All Students")
        & (mcas["ORG_TYPE"].isin(["Public School District", "Charter District"]))
    ].sort_values("SY").groupby(["DIST_CODE", "SUBJECT_CODE"]).tail(1)
    g10_pivot = g10.pivot_table(
        index="DIST_CODE", columns="SUBJECT_CODE", values="M_PLUS_E_PCT", aggfunc="first"
    ).reset_index()
    g10_pivot.columns = ["DIST_CODE"] + [f"mcas_g10_{c.lower()}_me" for c in g10_pivot.columns[1:]]
    out = out.merge(g10_pivot, on="DIST_CODE", how="left")

    # Grade 3-8 average M+E (across grades, all students)
    g38 = mcas[
        (mcas["TEST_GRADE"].isin(["03", "04", "05", "06", "07", "08", "3", "4", "5", "6", "7", "8"]))
        & (mcas["STU_GRP"] == "All Students")
        & (mcas["ORG_TYPE"].isin(["Public School District", "Charter District"]))
    ].copy()
    if not g38.empty:
        latest_g38_sy = g38["SY"].max()
        g38_latest = g38[g38["SY"] == latest_g38_sy]
        g38_avg = (g38_latest.groupby(["DIST_CODE", "SUBJECT_CODE"])["M_PLUS_E_PCT"]
                    .mean().reset_index()
                    .pivot_table(index="DIST_CODE", columns="SUBJECT_CODE",
                                  values="M_PLUS_E_PCT", aggfunc="first").reset_index())
        g38_avg.columns = ["DIST_CODE"] + [f"mcas_g38_{c.lower()}_me" for c in g38_avg.columns[1:]]
        out = out.merge(g38_avg, on="DIST_CODE", how="left")

    # ─── 4. Attendance (chronic absenteeism, district) ────────────────────────
    att_path = e2c_raw / "student_attendance.csv"
    if att_path.exists():
        att = pd.read_csv(att_path, low_memory=False)
        att["DIST_CODE"] = att["DIST_CODE"].astype(str).str.zfill(8)
        att_d = att[
            (att["STU_GRP"] == "All Students")
            & (att["ORG_TYPE"] == "District")
            & (att.get("ATTEND_PERIOD", "FY") == "FY")
        ].sort_values("SY").groupby("DIST_CODE").tail(1)
        if "PCT_CHRON_ABS_10" in att_d.columns:
            att_d = att_d[["DIST_CODE", "PCT_CHRON_ABS_10"]].rename(
                columns={"PCT_CHRON_ABS_10": "chronic_absent_pct"}
            )
            att_d["chronic_absent_pct"] = pd.to_numeric(att_d["chronic_absent_pct"], errors="coerce")
            out = out.merge(att_d, on="DIST_CODE", how="left")

    # ─── 5. AP performance (district aggregate — % scoring 3+) ────────────────
    # `ap_pct_3plus` is sourced at FULL PRECISION from DESE 787a-3wen via the SODA
    # JSON API (utils.precise_sources). The CSV bulk export rounds PCT_3_5 to the
    # nearest 10%; the JSON resource API returns the raw value. `precise_ap` is
    # fetched once here and reused by the year-keyed and group-keyed AP blocks below.
    precise_ap = fetch_precise_ap()
    ap_path = e2c_raw / "ap_performance.csv"
    ap = None
    if ap_path.exists():
        ap = pd.read_csv(ap_path, low_memory=False)
        ap["DIST_CODE"] = ap["DIST_CODE"].astype(str).str.zfill(8)
        # tests_taken is an integer count (not display-rounded) — keep it from the CSV.
        ap_d = ap[
            (ap["ORG_TYPE"] == "District")
            & (ap["STU_GRP"] == "All Students")
            & (ap["SUBJ_CAT"].astype(str).str.lower() == "all subjects")
        ].sort_values("SY").groupby("DIST_CODE").tail(1)
        if "TESTS_TAKEN" in ap_d.columns:
            ap_d = ap_d.copy()
            ap_d["ap_tests_taken"] = pd.to_numeric(ap_d["TESTS_TAKEN"], errors="coerce")
            out = out.merge(ap_d[["DIST_CODE", "ap_tests_taken"]], on="DIST_CODE", how="left")
    if not precise_ap.empty and "ap_pct_3plus" in precise_ap.columns:
        out = out.merge(precise_ap[["DIST_CODE", "ap_pct_3plus"]], on="DIST_CODE", how="left")
    elif ap is not None and "PCT_3_5" in ap.columns:
        # Fallback: rounded CSV value only if SODA was unreachable.
        ap_base = ap[
            (ap["ORG_TYPE"] == "District")
            & (ap["STU_GRP"] == "All Students")
            & (ap["SUBJ_CAT"].astype(str).str.lower() == "all subjects")
        ].sort_values("SY").groupby("DIST_CODE").tail(1).copy()
        ap_base["ap_pct_3plus"] = pd.to_numeric(ap_base["PCT_3_5"], errors="coerce")
        out = out.merge(ap_base[["DIST_CODE", "ap_pct_3plus"]], on="DIST_CODE", how="left")

    # ─── 6. MassCore completion ───────────────────────────────────────────────
    mc_path = e2c_raw / "masscore_completion.csv"
    if mc_path.exists():
        mc = pd.read_csv(mc_path, low_memory=False)
        mc["DIST_CODE"] = mc["DIST_CODE"].astype(str).str.zfill(8)
        mc_d = mc[
            (mc["ORG_TYPE"] == "District")
            & (mc["STU_GRP"] == "All Students")
        ].sort_values("SY").groupby("DIST_CODE").tail(1)
        if "PCT_COMPL_MASSCORE" in mc_d.columns:
            mc_d = mc_d[["DIST_CODE", "PCT_COMPL_MASSCORE"]].rename(
                columns={"PCT_COMPL_MASSCORE": "masscore_pct"}
            )
            out = out.merge(mc_d, on="DIST_CODE", how="left")

    # ─── 7. Finance (per-pupil by category) ───────────────────────────────────
    # IND_CAT="Expenditures Per Pupil" + IND_SUBCAT picks the category.
    # IND_CAT="Total Expenditures" gives the total district spend (not per-pupil).
    dexp = pd.read_csv(e2c_raw / "district_expenditures.csv", low_memory=False)
    dexp["DIST_CODE"] = dexp["DIST_CODE"].astype(str).str.zfill(8)
    dexp["IND_VALUE"] = pd.to_numeric(dexp["IND_VALUE"], errors="coerce")
    pp_all = dexp[dexp["IND_CAT"] == "Expenditures Per Pupil"]

    pp_total = pp_all[pp_all["IND_SUBCAT"] == "Total Expenditures"].sort_values("SY") \
        .groupby("DIST_CODE").tail(1)[["DIST_CODE", "IND_VALUE"]].rename(
            columns={"IND_VALUE": "per_pupil"}
        )
    out = out.merge(pp_total, on="DIST_CODE", how="left")

    pp_teachers = pp_all[pp_all["IND_SUBCAT"] == "Teachers"].sort_values("SY") \
        .groupby("DIST_CODE").tail(1)[["DIST_CODE", "IND_VALUE"]].rename(
            columns={"IND_VALUE": "per_pupil_teachers"}
        )
    out = out.merge(pp_teachers, on="DIST_CODE", how="left")

    pp_admin = pp_all[pp_all["IND_SUBCAT"] == "Administration"].sort_values("SY") \
        .groupby("DIST_CODE").tail(1)[["DIST_CODE", "IND_VALUE"]].rename(
            columns={"IND_VALUE": "per_pupil_admin"}
        )
    out = out.merge(pp_admin, on="DIST_CODE", how="left")

    pp_pupil_svc = pp_all[pp_all["IND_SUBCAT"] == "Pupil Services"].sort_values("SY") \
        .groupby("DIST_CODE").tail(1)[["DIST_CODE", "IND_VALUE"]].rename(
            columns={"IND_VALUE": "per_pupil_pupil_services"}
        )
    out = out.merge(pp_pupil_svc, on="DIST_CODE", how="left")

    # ─── 8. Staffing (teacher diversity, district level) ──────────────────────
    sr_path = e2c_raw / "staffing_race_gender.csv"
    if sr_path.exists():
        sr = pd.read_csv(sr_path, low_memory=False)
        sr["DIST_CODE"] = sr["DIST_CODE"].astype(str).str.zfill(8)
        all_staff = sr[
            (sr["ORG_TYPE"] == "District")
            & (sr["JOBCLASS_CAT"] == "All")
            & (sr["JOBCLASS"] == "All")
        ].sort_values("SY").groupby("DIST_CODE").tail(1)
        keep_sr = ["DIST_CODE", "FTE_TOTAL", "WH_PCT", "HL_PCT", "BAA_PCT", "AS_PCT", "FE_PCT"]
        keep_sr = [c for c in keep_sr if c in all_staff.columns]
        all_staff = all_staff[keep_sr].rename(columns={
            "FTE_TOTAL": "staff_fte_total",
            "WH_PCT": "staff_white_pct",
            "HL_PCT": "staff_hispanic_pct",
            "BAA_PCT": "staff_black_pct",
            "AS_PCT": "staff_asian_pct",
            "FE_PCT": "staff_female_pct",
        })
        out = out.merge(all_staff, on="DIST_CODE", how="left")

    # Override the three staff race shares with FULL-PRECISION, headcount-weighted
    # all-staff values from DESE fz9c-2g33 via SODA (utils.precise_sources). The
    # CSV's WH/HL/BAA_PCT above are rounded to the nearest 10%. staff_fte_total,
    # staff_female_pct and staff_asian_pct keep their CSV values (no gender, and
    # we only override the three race shares carried in the academic geojson).
    precise_staff = fetch_precise_staff_race()
    if not precise_staff.empty:
        out = out.merge(precise_staff, on="DIST_CODE", how="left", suffixes=("", "__precise"))
        for col in ("staff_white_pct", "staff_hispanic_pct", "staff_black_pct"):
            pc = f"{col}__precise"
            if pc in out.columns:
                out[col] = out[pc].combine_first(out[col]) if col in out.columns else out[pc]
                out = out.drop(columns=pc)

    # ─── 9. Teacher data — student:teacher ratio + experienced % + in-field % ─
    td_path = e2c_raw / "teacher_data.csv"
    if td_path.exists():
        td = pd.read_csv(td_path, low_memory=False)
        td["DIST_CODE"] = td["DIST_CODE"].astype(str).str.zfill(8)
        td_d = td[
            (td["ORG_TYPE"] == "District")
            & (td["SUBJECT"].astype(str).str.lower() == "all teachers")
        ].sort_values("SY").groupby("DIST_CODE").tail(1)
        cols_avail = [c for c in ["TCHR_LIC_PCT", "STU_TCHR_RATIO", "EXP_TCHR_PCT", "TCHR_INFLD_PCT"]
                       if c in td_d.columns]
        if cols_avail:
            keep = td_d[["DIST_CODE"] + cols_avail].copy()
            # stu_tchr_ratio comes as "11.7 to 1" — extract the number
            if "STU_TCHR_RATIO" in keep.columns:
                keep["stu_tchr_ratio"] = pd.to_numeric(
                    keep["STU_TCHR_RATIO"].astype(str).str.extract(r"([\d.]+)")[0],
                    errors="coerce",
                )
                keep = keep.drop(columns=["STU_TCHR_RATIO"])
            keep = keep.rename(columns={
                "TCHR_LIC_PCT":    "teacher_licensed_pct",
                "EXP_TCHR_PCT":    "teacher_experienced_pct",
                "TCHR_INFLD_PCT":  "teacher_infield_pct",
            })
            out = out.merge(keep, on="DIST_CODE", how="left")

    # ─── 9b. Plans of HS Graduates (next-step destinations) ───────────────────
    plans_path = e2c_raw / "plans_of_graduates.csv"
    if plans_path.exists():
        plans = pd.read_csv(plans_path, low_memory=False)
        plans["DIST_CODE"] = plans["DIST_CODE"].astype(str).str.zfill(8)
        plans_d = plans[plans["ORG_TYPE"] == "District"].sort_values("SY") \
            .groupby("DIST_CODE").tail(1)
        if "COLL_4YRPUB_PCT" in plans_d.columns:
            plans_d = plans_d.copy()
            for col in ["COLL_4YRPRV_PCT", "COLL_4YRPUB_PCT", "COLL_2YRPRV_PCT",
                          "COLL_2YRPUB_PCT", "PSTSEC_PCT", "WORK_PCT", "MILITARY_PCT"]:
                plans_d[col] = pd.to_numeric(plans_d.get(col), errors="coerce")
            plans_d["pct_4yr_college"] = (
                plans_d["COLL_4YRPRV_PCT"].fillna(0) + plans_d["COLL_4YRPUB_PCT"].fillna(0)
            )
            plans_d["pct_2yr_college"] = (
                plans_d["COLL_2YRPRV_PCT"].fillna(0) + plans_d["COLL_2YRPUB_PCT"].fillna(0)
            )
            plans_d["pct_any_college"] = (
                plans_d["pct_4yr_college"] + plans_d["pct_2yr_college"]
                + plans_d["PSTSEC_PCT"].fillna(0)
            )
            plans_d["pct_work_after_hs"] = plans_d["WORK_PCT"]
            plans_d["pct_military"] = plans_d["MILITARY_PCT"]
            keep_plans = ["DIST_CODE", "pct_4yr_college", "pct_2yr_college",
                           "pct_any_college", "pct_work_after_hs", "pct_military"]
            out = out.merge(plans_d[keep_plans], on="DIST_CODE", how="left")

    # ─── 9c. Attendance rate (overall, not just chronic) ──────────────────────
    if att_path.exists() and "ATTEND_RATE" in pd.read_csv(att_path, nrows=1, low_memory=False).columns:
        att_full = pd.read_csv(att_path, low_memory=False)
        att_full["DIST_CODE"] = att_full["DIST_CODE"].astype(str).str.zfill(8)
        att_r = att_full[
            (att_full["STU_GRP"] == "All Students")
            & (att_full["ORG_TYPE"] == "District")
            & (att_full.get("ATTEND_PERIOD", "FY") == "FY")
        ].sort_values("SY").groupby("DIST_CODE").tail(1)
        att_r = att_r[["DIST_CODE", "ATTEND_RATE"]].rename(
            columns={"ATTEND_RATE": "attendance_rate"}
        )
        att_r["attendance_rate"] = pd.to_numeric(att_r["attendance_rate"], errors="coerce")
        out = out.merge(att_r, on="DIST_CODE", how="left")

    # ─── 10. Staff retention rate ─────────────────────────────────────────────
    ret_path = e2c_raw / "staff_retention.csv"
    if ret_path.exists():
        ret = pd.read_csv(ret_path, low_memory=False)
        ret["DIST_CODE"] = ret["DIST_CODE"].astype(str).str.zfill(8)
        # "All staff" rollup
        ret_d = ret[
            (ret["ORG_TYPE"] == "District")
            & (ret["STAFF_DESC"].astype(str).str.lower().isin(["all staff", "teachers"]))
        ].sort_values("SY").groupby(["DIST_CODE", "STAFF_DESC"]).tail(1)
        # Pick "Teachers" first if available, else "All staff"
        teachers_ret = ret_d[ret_d["STAFF_DESC"].astype(str).str.lower() == "teachers"][
            ["DIST_CODE", "RETND_PCT"]].rename(columns={"RETND_PCT": "teacher_retention_pct"})
        out = out.merge(teachers_ret, on="DIST_CODE", how="left")

    # Ensure all-numeric for the metric columns
    metric_cols = [c for c in out.columns if c not in ("DIST_CODE", "DIST_NAME")]
    for c in metric_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # ─── YEAR-KEYED COLUMNS ───────────────────────────────────────────────────
    # For the metrics that change meaningfully over time (demographics, MCAS,
    # graduation, AP, per-pupil), emit additional columns named like
    # EL_PCT__2017, EL_PCT__2018, ..., EL_PCT__2026. These power the map's
    # year slider + slideshow. Latest-year columns above remain so popups
    # and the side panel keep working without year-awareness.
    yk_frames: list[pd.DataFrame] = []

    # Enrollment demographics — year-keyed
    enr_yk_cols = ["TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT", "HL_PCT",
                    "BAA_PCT", "AS_PCT", "WH_PCT", "SWD_PCT", "FLNE_PCT"]
    enr_all = enr[(enr["ORG_TYPE"] == "District")].copy()
    enr_all["SY"] = pd.to_numeric(enr_all["SY"], errors="coerce")
    enr_all = enr_all.dropna(subset=["SY"])
    enr_yk = _pivot_year_keyed(enr_all, enr_yk_cols)
    if not enr_yk.empty:
        yk_frames.append(enr_yk)

    # Graduation — 4-yr only by year (5-yr lags by a year)
    grad_yk_source = grad[
        (grad["STU_GRP"] == "All Students")
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        & (grad["ORG_TYPE"] == "District")
    ].copy()
    grad_yk_source["SY"] = pd.to_numeric(grad_yk_source["SY"], errors="coerce")
    grad_yk_source = grad_yk_source.dropna(subset=["SY"]).rename(
        columns={"GRAD_PCT": "grad_4yr", "DRPOUT_PCT": "dropout_pct"}
    )
    grad_yk = _pivot_year_keyed(grad_yk_source, ["grad_4yr", "dropout_pct"])
    if not grad_yk.empty:
        yk_frames.append(grad_yk)

    # MCAS Grade 10 — by year, by subject
    g10_yk_source = mcas[
        (mcas["TEST_GRADE"] == "10")
        & (mcas["STU_GRP"] == "All Students")
        & (mcas["ORG_TYPE"].isin(["Public School District", "Charter District"]))
    ].copy()
    g10_yk_source["SY"] = pd.to_numeric(g10_yk_source["SY"], errors="coerce")
    if not g10_yk_source.empty:
        for subj in ["ELA", "MATH", "SCI"]:
            sub = g10_yk_source[g10_yk_source["SUBJECT_CODE"] == subj][
                ["DIST_CODE", "SY", "M_PLUS_E_PCT"]
            ].copy()
            sub = sub.rename(columns={"M_PLUS_E_PCT": f"mcas_g10_{subj.lower()}_me"})
            sub_yk = _pivot_year_keyed(sub, [f"mcas_g10_{subj.lower()}_me"])
            if not sub_yk.empty:
                yk_frames.append(sub_yk)

    # AP % scoring 3+ by year — full precision from SODA (precise_ap, fetched in
    # Section 5). Falls back to the rounded CSV pivot only if SODA was unreachable.
    if not precise_ap.empty:
        ap_yk_cols = ["DIST_CODE"] + [
            c for c in precise_ap.columns
            if c.startswith("ap_pct_3plus__") and c.split("__")[1].isdigit()
        ]
        if len(ap_yk_cols) > 1:
            yk_frames.append(precise_ap[ap_yk_cols].copy())
    elif ap_path.exists():
        ap_yk_source = ap[
            (ap["ORG_TYPE"] == "District")
            & (ap["STU_GRP"] == "All Students")
            & (ap["SUBJ_CAT"].astype(str).str.lower() == "all subjects")
        ][["DIST_CODE", "SY", "PCT_3_5"]].copy()
        ap_yk_source["SY"] = pd.to_numeric(ap_yk_source["SY"], errors="coerce")
        ap_yk_source = ap_yk_source.rename(columns={"PCT_3_5": "ap_pct_3plus"})
        ap_yk = _pivot_year_keyed(ap_yk_source, ["ap_pct_3plus"])
        if not ap_yk.empty:
            yk_frames.append(ap_yk)

    # Per-pupil total + teachers — by year
    pp_yk_source = dexp[
        (dexp["IND_CAT"] == "Expenditures Per Pupil")
        & (dexp["IND_SUBCAT"].isin(["Total Expenditures", "Teachers"]))
    ].copy()
    pp_yk_source["SY"] = pd.to_numeric(pp_yk_source["SY"], errors="coerce")
    if not pp_yk_source.empty:
        for subcat, alias in [("Total Expenditures", "per_pupil"),
                               ("Teachers", "per_pupil_teachers")]:
            sub = pp_yk_source[pp_yk_source["IND_SUBCAT"] == subcat][
                ["DIST_CODE", "SY", "IND_VALUE"]
            ].copy().rename(columns={"IND_VALUE": alias})
            sub_yk = _pivot_year_keyed(sub, [alias])
            if not sub_yk.empty:
                yk_frames.append(sub_yk)

    # Merge all year-keyed frames into out
    for frame in yk_frames:
        out = out.merge(frame, on="DIST_CODE", how="left")

    # ─── GROUP-KEYED COLUMNS ─────────────────────────────────────────────────
    # For outcome metrics where the student-group breakdown is analytically
    # meaningful, emit `metric__hl`, `metric__baa`, `metric__ell`, etc.
    # (latest year only — combining year × group would balloon column count).
    gk_frames: list[pd.DataFrame] = []

    # MCAS Grade 10 by group (3 subjects)
    g10_grp_source = mcas[
        (mcas["TEST_GRADE"] == "10")
        & (mcas["ORG_TYPE"].isin(["Public School District", "Charter District"]))
    ].copy()
    for subj in ["ELA", "MATH", "SCI"]:
        s = g10_grp_source[g10_grp_source["SUBJECT_CODE"] == subj][
            ["DIST_CODE", "SY", "STU_GRP", "M_PLUS_E_PCT"]
        ]
        gk = _pivot_group_keyed(s, "M_PLUS_E_PCT", f"mcas_g10_{subj.lower()}_me")
        if not gk.empty:
            gk_frames.append(gk)

    # Graduation rate by group (4-yr cohort)
    grad_grp_source = grad[
        (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        & (grad["ORG_TYPE"] == "District")
    ][["DIST_CODE", "SY", "STU_GRP", "GRAD_PCT"]]
    gk = _pivot_group_keyed(grad_grp_source, "GRAD_PCT", "grad_4yr")
    if not gk.empty:
        gk_frames.append(gk)

    # AP scoring 3+ by group — full precision from SODA (precise_ap). Falls back
    # to the rounded CSV pivot only if SODA was unreachable.
    if not precise_ap.empty:
        ap_gk_cols = ["DIST_CODE"] + [
            c for c in precise_ap.columns
            if c.startswith("ap_pct_3plus__") and not c.split("__")[1].isdigit()
        ]
        if len(ap_gk_cols) > 1:
            gk_frames.append(precise_ap[ap_gk_cols].copy())
    elif ap_path.exists():
        ap_grp_source = ap[
            (ap["ORG_TYPE"] == "District")
            & (ap["SUBJ_CAT"].astype(str).str.lower() == "all subjects")
        ][["DIST_CODE", "SY", "STU_GRP", "PCT_3_5"]]
        gk = _pivot_group_keyed(ap_grp_source, "PCT_3_5", "ap_pct_3plus")
        if not gk.empty:
            gk_frames.append(gk)

    # Chronic absenteeism by group
    if att_path.exists():
        att_grp_source = pd.read_csv(att_path, low_memory=False)
        att_grp_source["DIST_CODE"] = att_grp_source["DIST_CODE"].astype(str).str.zfill(8)
        att_grp_source = att_grp_source[
            (att_grp_source["ORG_TYPE"] == "District")
            & (att_grp_source.get("ATTEND_PERIOD", "FY") == "FY")
        ][["DIST_CODE", "SY", "STU_GRP", "PCT_CHRON_ABS_10"]]
        gk = _pivot_group_keyed(att_grp_source, "PCT_CHRON_ABS_10", "chronic_absent_pct")
        if not gk.empty:
            gk_frames.append(gk)

    # Merge all group-keyed frames into out
    for frame in gk_frames:
        out = out.merge(frame, on="DIST_CODE", how="left")

    # Coerce all derived columns to numeric
    derived_cols = [c for c in out.columns if "__" in c]
    for c in derived_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    return out


def load_ma_districts_with_metrics() -> gpd.GeoDataFrame:
    """MassGIS CCUV districts (Charter / Vocational / Collaborative / Union)
    only — these are the "special" overlay districts. Regular town/regional
    academic district polygons come from build_ma_academic_districts() via
    a town-dissolve method since MassGIS doesn't publish them as a shapefile.
    """
    dist = gpd.read_file(DISTRICTS_SHP).to_crs(WEB_CRS)
    dist["ORG8CODE"] = dist["ORG8CODE"].astype(str).str.zfill(8)
    dist["TYPE"] = dist["TYPE"].astype(str)

    metrics = _build_district_metrics_table()
    metrics = metrics.rename(columns={"DIST_CODE": "ORG8CODE"})
    return dist.merge(metrics, on="ORG8CODE", how="left")


# Regional *secondary* (7-12 / 9-12) districts share every member town with
# that town's own K-8 district, which always operates more schools. The
# dominant-district town-dissolve below therefore assigns them no town and drops
# them entirely — even though they are real, operating districts with full DESE
# metrics. (K-12 regionals like Nashoba survive because their member towns have
# no separate elementary district, so the regional *is* dominant.) We add the
# secondary regionals back explicitly as the union of their member-town polygons
# — which is exactly how a regional district's footprint is defined. Member
# towns verified against DESE t8td-gens enrollment + district directories; see
# ma-education-atlas/scripts/analysis/regional_hs_gap.md. Add new ones here if a
# secondary regional district would otherwise be missed by the dissolve.
REGIONAL_SECONDARY_MEMBERS: dict[str, list[str]] = {
    "06400000": ["CONCORD", "CARLISLE"],                          # Concord-Carlisle
    "06950000": ["LINCOLN", "SUDBURY"],                           # Lincoln-Sudbury
    "06600000": ["BREWSTER", "EASTHAM", "ORLEANS", "WELLFLEET"],  # Nauset
    "06900000": ["NORFOLK", "WRENTHAM", "PLAINVILLE"],            # King Philip
    "07050000": ["BOXFORD", "TOPSFIELD", "MIDDLETON"],            # Masconomet
    "07300000": ["NORTHBOROUGH", "SOUTHBOROUGH"],                 # Northboro-Southboro (Algonquin)
    "07630000": ["SOMERSET", "BERKLEY"],                          # Somerset Berkley (9-12)
}

# Orphan towns: tiny rural towns with NO public school of their own, so the
# dominant-school dissolve (step 2) assigns them no district and drops them ->
# a see-through hole on the map. They DO belong to a real (usually regional)
# district that already wins its seat town; assign each one here so it joins that
# district's dissolve. TOWN (upper) -> DIST_CODE.
#
# Resolved authoritatively via the US Census Geocoder (coordinates ->
# Unified/Secondary/Elementary School District layers, preferring the layer that
# matches an existing district AND is contiguous), each verified geographically
# contiguous with its district's group polygon. To regenerate/extend: geocode the
# town centroid and take the matching district. For split towns, use whichever of
# the elementary/secondary districts is contiguous — e.g. Monroe's HS district
# (North Adams) is non-contiguous, so it's assigned to its K-8 elementary district
# (Florida) instead. With Monroe assigned, every MA town now maps to a district.
ORPHAN_TOWN_DISTRICT: dict[str, str] = {
    "MONROE": "00980000",                                            # Florida (K-8; Monroe HS tuitions to North Adams)
    "TYRINGHAM": "01500000",                                         # Lee
    "STOCKBRIDGE": "06180000", "WEST STOCKBRIDGE": "06180000",       # Berkshire Hills
    "GOSHEN": "06320000",                                            # Chesterfield-Goshen
    "CUMMINGTON": "06350000", "PERU": "06350000",                    # Central Berkshire
    "WASHINGTON": "06350000", "WINDSOR": "06350000",                 # Central Berkshire
    "SANDISFIELD": "06620000",                                       # Farmington River Reg
    "BLANDFORD": "06720000", "MIDDLEFIELD": "06720000",              # Gateway
    "MONTGOMERY": "06720000", "RUSSELL": "06720000",                 # Gateway
    "NEW ASHFORD": "07150000",                                       # Mount Greylock
    "HAWLEY": "07170000", "HEATH": "07170000", "PLAINFIELD": "07170000",  # Mohawk Trail
    "PHILLIPSTON": "07200000",                                       # Narragansett
    "WENDELL": "07280000",                                           # New Salem-Wendell
    "ASHBY": "07350000",                                             # North Middlesex
    "LEYDEN": "07500000",                                            # Pioneer Valley
    "ALFORD": "07650000", "MONTEREY": "07650000",                    # Southern Berkshire
    "MOUNT WASHINGTON": "07650000",                                  # Southern Berkshire
    "GRANVILLE": "07660000", "TOLLAND": "07660000",                  # Southwick-Tolland-Granville
    "AQUINNAH": "07740000",                                          # Up-Island Regional
}


def build_ma_academic_districts() -> gpd.GeoDataFrame:
    """
    Build polygons for the regular town/regional academic school districts.

    MassGIS publishes 'SCHOOLDISTRICTS_CCUV_POLY' which contains ONLY charters,
    vocational/technical regional districts, collaboratives, and historic
    superintendency unions — NOT the regular academic districts. Regular
    districts in MA are defined as "the union of the towns the district
    serves," but MassGIS does not publish that union as a polygon file.

    So we build it ourselves:
      1. From SCHOOLS_PT, filter to regular public schools (drop Private,
         Charter, Voc/Tech, Special Ed)
      2. For each town, find the dominant DIST_CODE across its public schools
      2b. Assign "orphan" towns (no school of their own) to their real district
          via ORPHAN_TOWN_DISTRICT, so they aren't dropped to a map hole
      3. Dissolve the town polygons by that DIST_CODE → ~250 academic districts
      3b. Add regional *secondary* districts the dominant-dissolve can't capture
          (REGIONAL_SECONDARY_MEMBERS), as the union of their member towns
      4. Join the full district metrics table (40+ indicators)

    Result: ma_academic_districts.geojson — the polygon file no one else has.
    """
    schools = gpd.read_file(SCHOOLS_SHP)
    towns = gpd.read_file(TOWNS_SHP).to_crs(WEB_CRS)

    # Filter to schools that belong to regular academic districts.
    # Exclude charters, voc-techs, private, special-ed (those are special districts).
    keep_types = {"Public Elementary", "Public Middle", "Public Secondary",
                  "Public Other", "Public Unknown"}
    public = schools[schools["TYPE_DESC"].isin(keep_types)].copy()
    public["DIST_CODE"] = public["DIST_CODE"].astype(str).str.zfill(8)

    # Dominant district per town (the one with the most public schools).
    dom = (public.groupby(["TOWN", "DIST_CODE"]).size()
                  .reset_index(name="n")
                  .sort_values(["TOWN", "n"], ascending=[True, False])
                  .groupby("TOWN").head(1)
                  .reset_index(drop=True))

    # Join the dominant district code onto the towns shapefile (towns w/o
    # public schools in this file will get NaN — typically tiny rural towns
    # that send students to regional districts; they're assigned below).
    towns_with_dist = towns.merge(dom[["TOWN", "DIST_CODE"]], on="TOWN", how="left")

    # Orphan towns: no school of their own -> NaN above, but they belong to a real
    # district (it wins its seat town separately). Fill from the Census-verified
    # crosswalk so they join that district's dissolve instead of becoming a hole.
    orphan = towns_with_dist["DIST_CODE"].isna()
    towns_with_dist.loc[orphan, "DIST_CODE"] = (
        towns_with_dist.loc[orphan, "TOWN"].str.upper().map(ORPHAN_TOWN_DISTRICT)
    )

    # Drop towns we still couldn't map (no schools + not a known orphan, e.g.
    # Monroe — sends to a non-contiguous district; stays a labeled hole downstream)
    towns_with_dist = towns_with_dist.dropna(subset=["DIST_CODE"])

    # Dissolve town polygons by DIST_CODE
    academic = towns_with_dist[["DIST_CODE", "geometry"]].dissolve(by="DIST_CODE").reset_index()

    # Add regional secondary districts the dominant-dissolve drops (see
    # REGIONAL_SECONDARY_MEMBERS). Each is the union of its member-town polygons,
    # so it overlaps its towns' K-8 districts — geographically correct, since a
    # 7-12 regional and its members' elementary districts cover the same ground.
    have = set(academic["DIST_CODE"])
    towns_u = towns.assign(TOWN_U=towns["TOWN"].str.upper())
    extra = []
    for code, members in REGIONAL_SECONDARY_MEMBERS.items():
        if code in have:
            continue
        sub = towns_u[towns_u["TOWN_U"].isin([m.upper() for m in members])]
        if sub.empty:
            print(f"  [!] {code}: no member towns matched, skipping")
            continue
        extra.append({"DIST_CODE": code, "geometry": sub.geometry.union_all()})
    if extra:
        academic = pd.concat(
            [academic, gpd.GeoDataFrame(extra, geometry="geometry", crs=academic.crs)],
            ignore_index=True,
        )

    # Join district metrics
    metrics = _build_district_metrics_table()
    metrics["DIST_CODE"] = metrics["DIST_CODE"].astype(str).str.zfill(8)
    academic = academic.merge(metrics, on="DIST_CODE", how="left")

    # Display name for the map label + search index. Defaults to the DESE
    # DIST_NAME; a few regionals get a friendlier alias so their common name is
    # searchable (e.g. Northboro-Southboro is known as Algonquin Regional).
    DISPLAY_OVERRIDES = {"07300000": "Northboro-Southboro (Algonquin)"}
    if "DIST_NAME" in academic.columns:
        academic["dist_display"] = [
            DISPLAY_OVERRIDES.get(c, n)
            for c, n in zip(academic["DIST_CODE"], academic["DIST_NAME"])
        ]

    # Flag Lynn
    academic["is_lynn"] = academic["DIST_CODE"] == "01630000"

    return academic




def load_ma_municipalities() -> gpd.GeoDataFrame:
    """
    All 351 MA municipalities as polygons, with:
      - is_gateway: bool — whether this is one of the 26 Gateway Cities
      - is_lynn:    bool — whether this is Lynn itself
      - county, pop_2020 — context
      - 25+ joined district-level DESE metrics where the town's primary
        school district can be identified by name match. Multi-town
        regional districts and charter districts won't match.
    """
    towns = gpd.read_file(TOWNS_SHP).to_crs(WEB_CRS)

    gateway_upper = {c.upper() for c in GATEWAY_CITIES}
    towns["is_gateway"] = towns["TOWN"].isin(gateway_upper)
    towns["is_lynn"] = towns["TOWN"] == "LYNN"

    if "POP2020" in towns.columns:
        towns["pop_2020"] = pd.to_numeric(towns["POP2020"], errors="coerce")

    towns["town_display"] = towns["TOWN"].str.title()

    # Pull the full district metrics table and join by name
    metrics = _build_district_metrics_table()
    metrics["DIST_NAME_upper"] = metrics["DIST_NAME"].astype(str).str.upper()
    result = towns.merge(metrics, left_on="TOWN", right_on="DIST_NAME_upper", how="left")
    return result.drop(columns=["DIST_NAME_upper"], errors="ignore")


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

    print("\nBuilding MA-wide public schools point layer...")
    all_schools = gpd.read_file(SCHOOLS_SHP).to_crs(WEB_CRS)
    keep_public = {"Public Elementary", "Public Middle", "Public Secondary",
                   "Public Other", "Public Unknown", "Public Voc/Tech/Ag Reg'l HS",
                   "Charter"}
    ma_pub = all_schools[all_schools["TYPE_DESC"].isin(keep_public)].copy()
    ma_pub["lon"] = ma_pub.geometry.x
    ma_pub["lat"] = ma_pub.geometry.y
    # Slim the properties before export
    keep_school_cols = {"SCHID", "NAME", "TOWN", "GRADES", "TYPE_DESC",
                        "DIST_NAME", "DIST_CODE", "lat", "lon", "geometry"}
    ma_pub = ma_pub[[c for c in ma_pub.columns if c in keep_school_cols]]
    out = PROCESSED_DIR / "ma_public_schools.geojson"
    ma_pub.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(ma_pub)} MA public+charter schools")
    print(f"     by type: {ma_pub['TYPE_DESC'].value_counts().to_dict()}")
    print(f"     file size: {out.stat().st_size // 1024:,} KB")

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

    print("\nBuilding ACADEMIC districts (town-dissolve from public schools)...")
    academic = build_ma_academic_districts()
    # Keep core metrics (most of the catalog the maps app uses)
    keep_a = {"DIST_CODE", "DIST_NAME", "dist_display", "is_lynn",
              "TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT", "HL_PCT", "BAA_PCT",
              "AS_PCT", "WH_PCT", "SWD_PCT", "FLNE_PCT", "FE_PCT",
              "mcas_g10_ela_me", "mcas_g10_math_me", "mcas_g10_sci_me",
              "mcas_g38_ela_me", "mcas_g38_math_me", "mcas_g38_sci_me",
              "grad_4yr", "grad_5yr", "dropout_pct", "chronic_absent_pct",
              "attendance_rate", "masscore_pct", "ap_pct_3plus",
              "pct_any_college", "pct_4yr_college", "pct_2yr_college",
              "pct_work_after_hs", "pct_military",
              "per_pupil", "per_pupil_teachers", "per_pupil_admin",
              "per_pupil_pupil_services",
              "staff_white_pct", "staff_hispanic_pct", "staff_black_pct",
              "stu_tchr_ratio", "teacher_experienced_pct",
              "teacher_infield_pct", "teacher_retention_pct",
              "geometry"}
    # Year-keyed columns (e.g. EL_PCT__2017, grad_4yr__2024, etc.) are also kept
    # — they power the map's year slider + slideshow.
    academic_yk_cols = {c for c in academic.columns if "__" in c}
    academic = academic[[c for c in academic.columns if c in keep_a or c in academic_yk_cols]]
    academic = simplify_for_web(academic)
    out = PROCESSED_DIR / "ma_academic_districts.geojson"
    academic.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(academic)} academic districts")
    print(f"     {academic['grad_4yr'].notna().sum()} have grad rate")
    print(f"     {academic['per_pupil'].notna().sum()} have per-pupil")
    print(f"     file size: {out.stat().st_size // 1024:,} KB")

    print("\nLoading CCUV special districts (Charter / Vocational / Collab)...")
    ma_districts = load_ma_districts_with_metrics()
    # Add ORG8CODE alias same as DIST_CODE for downstream popup logic
    keep_d = {"ORG8CODE", "NAME", "DIST_NAME", "TYPE", "TOTAL_CNT", "EL_PCT", "LI_PCT",
              "HN_PCT", "HL_PCT", "grad_4yr", "per_pupil", "mcas_g10_ela_me",
              "mcas_g10_math_me", "geometry"}
    ma_districts = ma_districts[[c for c in ma_districts.columns if c in keep_d]]
    ma_districts = simplify_for_web(ma_districts)
    out = PROCESSED_DIR / "ma_districts_metrics.geojson"
    ma_districts.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(ma_districts)} CCUV districts")
    print(f"     by TYPE: {ma_districts['TYPE'].value_counts().to_dict()}")
    print(f"     file size: {out.stat().st_size // 1024:,} KB")

    print("\nLoading MA municipalities (all 351 towns)...")
    ma_munis = load_ma_municipalities()
    # Drop fields not used in popups: AREA_*, SHAPE_*, FOURCOLOR, POP1960-2000, etc.
    keep_m = {"TOWN", "town_display", "TOWN_ID", "COUNTY", "TYPE", "POP2020",
              "pop_2020", "is_gateway", "is_lynn", "DIST_NAME", "DIST_CODE",
              "TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT", "grad_4yr", "per_pupil",
              "geometry"}
    muni_yk_cols = {c for c in ma_munis.columns if "__" in c}
    ma_munis = ma_munis[[c for c in ma_munis.columns if c in keep_m or c in muni_yk_cols]]
    ma_munis = simplify_for_web(ma_munis)
    out = PROCESSED_DIR / "ma_municipalities.geojson"
    ma_munis.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(ma_munis)} municipalities")
    print(f"     {ma_munis['is_gateway'].sum()} flagged as Gateway Cities")
    if "grad_4yr" in ma_munis.columns:
        print(f"     {ma_munis['grad_4yr'].notna().sum()} matched a district by name")
    print(f"     file size: {out.stat().st_size // 1024:,} KB")

    print("\nLoading gateway-city main HS...")
    gateway = load_gateway_main_hs()
    out = PROCESSED_DIR / "gateway_hs.geojson"
    gateway.to_file(out, driver="GeoJSON")
    print(f"  [OK] {out.name}: {len(gateway)} main HS located")

    print("\nDone.")


if __name__ == "__main__":
    main()
