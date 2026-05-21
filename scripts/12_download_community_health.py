"""
Download EPA EJScreen + CDC PLACES tract-level data for Lynn.

Two community-context layers:
  - EPA EJScreen (env-justice): pollution burden, demographic index, by census
    block group. Restricted to MA, then to Lynn tracts.
  - CDC PLACES: tract-level chronic-disease + behavioral health prevalence
    (asthma, mental distress, obesity, smoking, etc.). Socrata-backed.

Outputs (joined onto lynn_tracts.geojson in 11_build_lynn_geo.py):
  - data/processed/ejscreen_lynn.parquet  (tract-level rollup of block-group data)
  - data/processed/places_lynn.parquet

Run AFTER scripts/10_download_census_acs.py (which gives tract list)
        AND scripts/09_download_massgis.py (which gives Lynn boundary).

Run with:
    python scripts/12_download_community_health.py
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR, RAW_DIR  # noqa: E402

CH_RAW = RAW_DIR / "community_health"
CH_RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "lehs-data-dive/0.2 (https://github.com/mapzimus/lehs-data-dive)"}
TIMEOUT = 120

# Lynn = Essex County (FIPS 25009); narrow further to Lynn city tracts when joining.
ESSEX_COUNTY_FIPS = "25009"
MA_STATE_FIPS = "25"

# EJScreen bulk tract-level file. EPA *removed* EJScreen from its website on
# 2025-02-05 (https://envirodatagov.org/epa-removes-ejscreen-from-its-website/),
# so the original gaftp.epa.gov URLs now 404. We use the Harvard Dataverse
# mirror maintained by the Environment and Law Data (HELD) collection
# (doi:10.7910/DVN/RLR5AX), which preserves EJScreen 2024 v2.32 — the last
# release before removal. Each entry is (url, file_format) where file_format
# is "csv" (plain) or "zip" (zipped CSV).
EJSCREEN_SOURCES = [
    # Harvard Dataverse — EJScreen 2024 Tract StatePct (with state percentiles).
    # 153 MB plain CSV. File ID 10775973 in dataset doi:10.7910/DVN/RLR5AX.
    ("https://dataverse.harvard.edu/api/access/datafile/10775973", "csv"),
    # Fallback: same dataset, "raw values" version without state percentiles
    # (still has the minority/low-income/pollution columns we need).
    ("https://dataverse.harvard.edu/api/access/datafile/10775979", "csv"),
    # Historical EPA URLs — kept in case EPA ever restores them.
    ("https://gaftp.epa.gov/EJScreen/2024/2.32_July_UseMe/EJScreen_2024_Tract_with_AS_CNMI_GU_VI.csv.zip", "zip"),
    ("https://gaftp.epa.gov/EJScreen/2023/2.22_September_UseMe/EJScreen_2023_Tract_StatePct_with_AS_CNMI_GU_VI.csv.zip", "zip"),
]

# CDC PLACES tract-level dataset (Socrata)
PLACES_CSV = (
    "https://chronicdata.cdc.gov/resource/cwsq-ngmh.csv"
    f"?$where=stateabbr='MA' AND countyfips='{ESSEX_COUNTY_FIPS}'"
    "&$limit=50000"
)


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 1000:
        return True
    try:
        print(f"    GET {url}")
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return dest.stat().st_size > 1000
    except Exception as e:
        print(f"    [WARN] {e}")
        return False


def load_lynn_tracts() -> list[str]:
    """Return list of 11-digit tract GEOIDs in Lynn."""
    # The processed lynn_tracts.geojson is built later in the pipeline; for now
    # fall back to Essex County prefix filter, then refine when geo build runs.
    p = PROCESSED_DIR / "lynn_tracts.geojson"
    if p.exists():
        import json
        with open(p) as f:
            fc = json.load(f)
        return [feat["properties"]["GEOID"] for feat in fc["features"]
                if "GEOID" in feat["properties"]]
    return []


def process_ejscreen() -> pd.DataFrame:
    EMPTY_COLS = [
        "GEOID", "ENV_INDEX", "DEMO_INDEX", "EJ_INDEX_PM25",
        "PCT_MINORITY", "PCT_LOW_INC", "PCT_LING_ISO",
        "OZONE", "PM25", "DSLPM", "RSEI_AIR", "PRE1960_HOUSING",
    ]
    raw_path = None
    source_fmt = None
    for url, fmt in EJSCREEN_SOURCES:
        suffix = ".zip" if fmt == "zip" else ".csv"
        dest = CH_RAW / f"ejscreen_ma{suffix}"
        if download(url, dest):
            raw_path = dest
            source_fmt = fmt
            break
    if raw_path is None:
        print("  [SKIP] EJScreen download failed (all sources) — writing empty parquet")
        return pd.DataFrame(columns=EMPTY_COLS)
    try:
        if source_fmt == "zip":
            with zipfile.ZipFile(raw_path) as zf:
                csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
                with zf.open(csv_name) as f:
                    df = pd.read_csv(f, low_memory=False, encoding_errors="replace")
        else:
            df = pd.read_csv(raw_path, low_memory=False, encoding_errors="replace")
    except Exception as e:
        print(f"  [WARN] EJScreen parse failed: {e}")
        return pd.DataFrame(columns=EMPTY_COLS)

    # Filter to MA + harmonize column names. EPA renames cols every release;
    # try common variants.
    state_col = next((c for c in df.columns if c.upper() in ("STATE", "ST_ABBREV", "STATE_NAME")), None)
    geoid_col = next((c for c in df.columns if c.upper() in ("ID", "GEOID", "GEOID20", "TRACTID")), None)
    if state_col:
        df = df[df[state_col].astype(str).isin(["MA", "Massachusetts", "25"])].copy()
    keep_map = {
        geoid_col or "ID": "GEOID",
    }
    for col_target, candidates in [
        ("ENV_INDEX", ["INDEX_SUP", "EJINDEX_PM25", "PCT_MINORITY"]),
        ("DEMO_INDEX", ["DEMOGIDX_2"]),
        ("EJ_INDEX_PM25", ["EJINDEX_PM25", "P_PM25"]),
        ("PCT_MINORITY", ["MINORPCT", "PCT_MINORITY", "PEOPCOLORPCT"]),
        ("PCT_LOW_INC", ["LOWINCPCT", "PCT_LOW_INC"]),
        ("PCT_LING_ISO", ["LINGISOPCT", "PCT_LING_ISO"]),
        ("OZONE", ["OZONE", "P_OZONE"]),
        ("PM25", ["PM25", "P_PM25"]),
        ("DSLPM", ["DSLPM", "P_DSLPM"]),
        ("RSEI_AIR", ["RSEI_AIR"]),
        ("PRE1960_HOUSING", ["PRE1960PCT", "PCT_PRE1960"]),
    ]:
        for c in candidates:
            if c in df.columns:
                keep_map[c] = col_target
                break

    keep_cols = [c for c in keep_map if c and c in df.columns]
    out = df[keep_cols].rename(columns=keep_map)
    if "GEOID" in out.columns:
        out["GEOID"] = out["GEOID"].astype(str).str.zfill(11)
    return out


def process_places() -> pd.DataFrame:
    dest = CH_RAW / "places_ma_essex.csv"
    if not download(PLACES_CSV, dest):
        return pd.DataFrame(columns=[
            "GEOID", "MEASURE", "MEASUREID", "DATA_VALUE", "LOW_CI", "HIGH_CI",
        ])
    try:
        df = pd.read_csv(dest, low_memory=False)
    except Exception as e:
        print(f"  [WARN] PLACES parse failed: {e}")
        return pd.DataFrame()
    # Normalize column names
    rename = {}
    for c in df.columns:
        u = c.upper()
        if u in ("LOCATIONNAME", "TRACTFIPS"):
            rename[c] = "GEOID"
        elif u in ("DATA_VALUE", "DATAVALUE"):
            rename[c] = "DATA_VALUE"
        elif u == "MEASURE":
            rename[c] = "MEASURE"
        elif u == "MEASUREID":
            rename[c] = "MEASUREID"
        elif u in ("LOW_CONFIDENCE_LIMIT", "LOW_CI"):
            rename[c] = "LOW_CI"
        elif u in ("HIGH_CONFIDENCE_LIMIT", "HIGH_CI"):
            rename[c] = "HIGH_CI"
    df = df.rename(columns=rename)
    if "GEOID" in df.columns:
        df["GEOID"] = df["GEOID"].astype(str).str.zfill(11)
    keep = [c for c in ["GEOID", "MEASURE", "MEASUREID", "DATA_VALUE", "LOW_CI", "HIGH_CI"]
            if c in df.columns]
    return df[keep]


def main() -> None:
    print("Community health ingest")

    ejs = process_ejscreen()
    if not ejs.empty and "GEOID" in ejs.columns:
        # Keep only MA tracts (25*)
        ejs = ejs[ejs["GEOID"].astype(str).str.startswith(MA_STATE_FIPS)].copy()
    ejs.to_parquet(PROCESSED_DIR / "ejscreen_lynn.parquet", index=False)
    print(f"  Wrote ejscreen_lynn.parquet ({len(ejs):,} rows)")

    places = process_places()
    places.to_parquet(PROCESSED_DIR / "places_lynn.parquet", index=False)
    print(f"  Wrote places_lynn.parquet ({len(places):,} rows)")


if __name__ == "__main__":
    main()
