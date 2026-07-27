"""
Download DESE Profiles statereport disaggregated discipline data.

The E2C Hub gives us discipline rates by single dimension at a time, but the
race × disability × gender × ELL cross-tabs live only on DESE's Profiles
statereport (profiles.doe.mass.edu/statereport/ssdr.aspx — School Safety and
Discipline Report).

Strategy:
  1. Try the bulk-download endpoint for the SSDR report for each year + Lynn
     district + LEHS/LCHS/Tech school codes.
  2. If the endpoint 404s or returns HTML, fall back to a schema-valid empty
     parquet so dashboard pages don't crash. Log the gap clearly so a future
     run can fix the URL.
  3. Compute risk ratios (group rate / all-students rate) for disproportionality
     analysis.

Outputs:
  - data/processed/discipline_disaggregated.parquet
       columns: SY, ORG_CODE, ORG_NAME, DIM (race/ell/sped/gender), GROUP, INDICATOR, VALUE
  - data/processed/discipline_disproportionality.parquet
       columns: SY, ORG_CODE, DIM, GROUP, INDICATOR, GROUP_RATE, ALL_RATE, RISK_RATIO

Run with:
    python scripts/03_download_dese_statereport.py
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    EARLIEST_YEAR,
    CURRENT_SCHOOL_YEAR,
    LCHS_SCHOOL_CODE,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
    RAW_DIR,
)

RAW = RAW_DIR / "dese_statereport"
RAW.mkdir(parents=True, exist_ok=True)

# DESE Profiles statereport endpoint. Each `reportId` corresponds to one report
# in their dropdown. ssdr.aspx is the School Safety + Discipline Report.
# These endpoints accept GET parameters and return either CSV or HTML.
SSDR_URL = "https://profiles.doe.mass.edu/statereport/ssdr.aspx"
TIMEOUT = 30

HEADERS = {"User-Agent": "lehs-data-dive/0.2 (https://github.com/mapzimus/lehs-data-dive)"}

ORG_CODES = {
    LEHS_SCHOOL_CODE: "Lynn English High",
    LCHS_SCHOOL_CODE: "Lynn Classical High",
    "01630605": "Lynn Vocational Technical Institute",
    LYNN_DISTRICT_CODE: "Lynn Public Schools",
}

# Indicators we care about
INDICATORS = [
    "In-School Suspension Rate",
    "Out-of-School Suspension Rate",
    "Expulsion Rate",
    "Emergency Removal Rate",
]

# Disaggregation dimensions and groups
DIMS = {
    "race":   ["African American/Black", "Asian", "Hispanic/Latino", "White",
               "Multi-Race, Non-Hispanic/Latino"],
    "ell":    ["English Learner", "Non-English Learner"],
    "sped":   ["Students w/ Disabilities", "Non-Disabled"],
    "gender": ["Female", "Male"],
}


def fetch_year(org_code: str, sy: int) -> pd.DataFrame | None:
    """Return a long-form DF for one (org, year), or None if endpoint failed."""
    params = {"orgCode": org_code, "fyCode": sy, "reportType": 16, "fycode": sy}
    try:
        r = requests.get(SSDR_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        text = r.text
    except Exception as e:
        print(f"    [WARN] fetch failed for {org_code} SY{sy}: {e}")
        return None
    # The page typically returns HTML with tables; if a CSV link is present we
    # could follow it. For now: try to parse any tables present.
    try:
        tables = pd.read_html(StringIO(text))
    except ValueError:
        return None
    if not tables:
        return None
    # The DESE pages structure their data in multiple tables; we just stash
    # the largest as a sentinel that something came back. Real parsing
    # requires inspecting the actual HTML and is left to a follow-up run.
    biggest = max(tables, key=lambda t: t.size)
    biggest = biggest.copy()
    biggest["ORG_CODE"] = org_code
    biggest["SY"] = sy
    return biggest


def build_empty_disaggregated() -> pd.DataFrame:
    rows = []
    for sy in range(EARLIEST_YEAR, CURRENT_SCHOOL_YEAR + 1):
        for org_code, org_name in ORG_CODES.items():
            for indicator in INDICATORS:
                # "All Students" baseline row
                rows.append({
                    "SY": sy, "ORG_CODE": org_code, "ORG_NAME": org_name,
                    "DIM": "all", "GROUP": "All Students",
                    "INDICATOR": indicator, "VALUE": pd.NA,
                })
                for dim, groups in DIMS.items():
                    for g in groups:
                        rows.append({
                            "SY": sy, "ORG_CODE": org_code, "ORG_NAME": org_name,
                            "DIM": dim, "GROUP": g,
                            "INDICATOR": indicator, "VALUE": pd.NA,
                        })
    return pd.DataFrame(rows)


def build_disproportionality(disagg: pd.DataFrame) -> pd.DataFrame:
    if disagg.empty:
        return disagg
    base = (disagg[disagg["DIM"] == "all"]
            [["SY", "ORG_CODE", "INDICATOR", "VALUE"]]
            .rename(columns={"VALUE": "ALL_RATE"}))
    grouped = disagg[disagg["DIM"] != "all"].copy()
    out = grouped.merge(base, on=["SY", "ORG_CODE", "INDICATOR"], how="left")
    out = out.rename(columns={"VALUE": "GROUP_RATE"})
    out["RISK_RATIO"] = pd.to_numeric(out["GROUP_RATE"], errors="coerce") / \
                       pd.to_numeric(out["ALL_RATE"], errors="coerce")
    return out[["SY", "ORG_CODE", "ORG_NAME", "DIM", "GROUP",
                "INDICATOR", "GROUP_RATE", "ALL_RATE", "RISK_RATIO"]]


def main() -> None:
    print("DESE Profiles statereport — disaggregated discipline ingest")
    fetched_any = False
    for sy in range(EARLIEST_YEAR, CURRENT_SCHOOL_YEAR + 1):
        for org_code in ORG_CODES:
            df = fetch_year(org_code, sy)
            if df is not None and not df.empty:
                fetched_any = True
                out = RAW / f"ssdr_{org_code}_SY{sy}.parquet"
                df.to_parquet(out, index=False)
                print(f"    [OK] saved {out.name}")

    if not fetched_any:
        print("\n  No live data returned from the statereport endpoint.")

    # The REAL processed discipline parquets are built from the E2C SODA
    # dataset (2kca-w7rq) by scripts/build_gap_datasets.py. Only scaffold
    # schema-valid empty files when they don't exist yet (first bootstrap) —
    # overwriting real data with an all-NA placeholder broke the Discipline
    # page after a full refresh (found 2026-07).
    disagg_path = PROCESSED_DIR / "discipline_disaggregated.parquet"
    dispro_path = PROCESSED_DIR / "discipline_disproportionality.parquet"
    if disagg_path.exists() and dispro_path.exists():
        print("  Processed discipline parquets already exist — leaving them for")
        print("  build_gap_datasets.py to rebuild from the E2C SODA source.")
        return

    disagg = build_empty_disaggregated()
    disagg.to_parquet(disagg_path, index=False)
    print(f"  Wrote discipline_disaggregated.parquet ({len(disagg):,} rows)")

    dispro = build_disproportionality(disagg)
    dispro.to_parquet(dispro_path, index=False)
    print(f"  Wrote discipline_disproportionality.parquet ({len(dispro):,} rows)")


if __name__ == "__main__":
    main()
