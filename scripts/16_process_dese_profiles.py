"""
Process the xlsx files scraped from DESE Profiles statereport into the
processed-data parquet layer.

Each statereport xlsx has the same shape:
  row 0 = report title (e.g. "2025 Accountability Report")
  row 1 = column headers
  row 2+ = data, one row per district or school

This script normalizes that into tidy parquet files filtered to our peer
set (Lynn district + 26 Gateway-city districts, plus their schools).

Run after scripts/02_download_dese_profiles.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import LYNN_DISTRICT_CODE, PROCESSED_DIR, RAW_DIR  # noqa: E402

DESE_PROFILES_RAW = RAW_DIR / "dese_profiles"


def _peer_district_codes() -> set[str]:
    peers_path = PROCESSED_DIR / "_peer_schools.json"
    if not peers_path.exists():
        return {LYNN_DISTRICT_CODE}
    peers = json.loads(peers_path.read_text())
    out = {LYNN_DISTRICT_CODE}
    for info in (peers.get("gateway_main_hs") or {}).values():
        if info.get("district_code"):
            out.add(info["district_code"])
    return out


def _peer_school_codes() -> set[str]:
    peers_path = PROCESSED_DIR / "_peer_schools.json"
    if not peers_path.exists():
        return set()
    peers = json.loads(peers_path.read_text())
    out: set[str] = set()
    # Lynn district schools
    for code in (peers.get("lynn_all_schools") or {}).values():
        out.add(str(code).zfill(8))
    # Gateway main HS
    for info in (peers.get("gateway_main_hs") or {}).values():
        if info.get("school_code"):
            out.add(str(info["school_code"]).zfill(8))
    return out


def _load_statereport_xlsx(path: Path) -> tuple[str, pd.DataFrame]:
    """Read a statereport xlsx. Returns (report_title, dataframe-with-headers)."""
    raw = pd.read_excel(path, header=None, dtype=str)
    title = str(raw.iloc[0, 0]).strip()
    headers = [str(c).strip() for c in raw.iloc[1].tolist()]
    data = raw.iloc[2:].copy()
    data.columns = headers
    data = data.dropna(how="all").reset_index(drop=True)
    return title, data


def process_accountability() -> None:
    """ESSA accountability — district + school level → one parquet, filtered."""
    dist_xlsx = DESE_PROFILES_RAW / "accountability_district.xlsx"
    sch_xlsx = DESE_PROFILES_RAW / "accountability_school.xlsx"
    if not dist_xlsx.exists() or not sch_xlsx.exists():
        print("  [SKIP] accountability — run scripts/02_download_dese_profiles.py first")
        return

    title_d, df_d = _load_statereport_xlsx(dist_xlsx)
    title_s, df_s = _load_statereport_xlsx(sch_xlsx)
    print(f"  district report: {title_d!r}  ({len(df_d):,} rows)")
    print(f"  school   report: {title_s!r}  ({len(df_s):,} rows)")

    # Year inferred from the title — both titles share the year.
    year = "".join(c for c in title_d if c.isdigit())[:4]
    sy_int = int(year) if year else None

    # Normalize district frame
    df_d = df_d.rename(columns={
        "District Name": "ORG_NAME",
        "District Code": "ORG_CODE",
        "Overall Classification": "CLASSIFICATION",
        "Reason for Classification": "REASON",
        "Cumulative Progress Toward Improvement Targets (%)": "PROGRESS_PCT",
    })
    df_d["ORG_TYPE"] = "District"
    df_d["DIST_CODE"] = df_d["ORG_CODE"].astype(str).str.zfill(8)
    df_d["PERCENTILE"] = pd.NA  # not published at district level

    # Normalize school frame
    df_s = df_s.rename(columns={
        "School Name": "ORG_NAME",
        "School Code": "ORG_CODE",
        "Overall Classification": "CLASSIFICATION",
        "Reason for Classification": "REASON",
        "Accountability Percentile (1-99)": "PERCENTILE",
        "Cumulative Progress Toward Improvement Targets (%)": "PROGRESS_PCT",
    })
    df_s["ORG_TYPE"] = "School"
    df_s["ORG_CODE"] = df_s["ORG_CODE"].astype(str).str.zfill(8)
    # School code's first 4 digits are the LEA/district id (DESE convention),
    # then zero-padded to 8.
    df_s["DIST_CODE"] = df_s["ORG_CODE"].str[:4].str.ljust(8, "0")

    # Filter to peer set
    district_codes = _peer_district_codes()
    school_codes = _peer_school_codes()

    df_d_filt = df_d[df_d["DIST_CODE"].isin(district_codes)].copy()
    df_s_filt = df_s[df_s["ORG_CODE"].isin(school_codes)].copy()

    cols = ["ORG_CODE", "ORG_NAME", "ORG_TYPE", "DIST_CODE",
            "CLASSIFICATION", "REASON", "PERCENTILE", "PROGRESS_PCT"]
    combined = pd.concat([df_d_filt[cols], df_s_filt[cols]], ignore_index=True)
    combined["SY"] = sy_int
    combined["PERCENTILE"] = pd.to_numeric(combined["PERCENTILE"], errors="coerce")
    combined["PROGRESS_PCT"] = pd.to_numeric(combined["PROGRESS_PCT"], errors="coerce")

    out_path = PROCESSED_DIR / "accountability.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"  [OK] -> {out_path.name}  ({len(combined):,} rows; "
          f"{len(df_d_filt)} districts + {len(df_s_filt)} schools)")


def main() -> None:
    print("Processing DESE Profiles statereport xlsx files...")
    print(f"  raw input dir:    {DESE_PROFILES_RAW}")
    print(f"  processed output: {PROCESSED_DIR}")
    print()

    process_accountability()

    print()
    print("Done.")


if __name__ == "__main__":
    main()
