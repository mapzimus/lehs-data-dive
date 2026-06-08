"""
Build the Lynn/LEHS slice of DESE's **Student Attrition** report (E2C dataset
``4as3-w39x``) from the Socrata SODA JSON API at full precision.

Attrition = the share of students who were enrolled in a school/district but did
NOT return the following year and did not graduate (they transferred out, moved,
or otherwise left). It complements the *student mobility* (within-year churn)
already surfaced on pages/1_School_Profile.py: mobility is movement DURING a
year, attrition is year-over-year leaving.

Schema (uppercased / coerced by utils.gap_sources.tidy):
    DIST_CODE DIST_NAME ORG_CODE ORG_NAME ORG_TYPE SY STU_GRP
    GRD_ALL   overall attrition rate (0-1: share of enrolled who left)
    G09_PCT G10_PCT G11_PCT   grade-specific attrition rates (HS rows only)

Grain: this dataset reports BOTH District rows and School rows (LEHS school rows
exist; org_type='School'). It has NO statewide ('State') aggregate, so a
Massachusetts benchmark line is not available from this source — the page
caption notes that and the trend compares LEHS to the Lynn district.

Writes data/processed/student_attrition.parquet. Re-runnable and additive: a
fetch that fails soft leaves any existing parquet untouched. Run:
    python scripts/build_attrition.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)
from utils.gap_sources import (  # noqa: E402
    canon_peer,
    load_peer_codes,
    pull,
    tidy,
)

DATASET_ID = "4as3-w39x"
SELECT = (
    "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,"
    "grd_all,g09_pct,g10_pct,g11_pct"
)


def fetch_attrition(codes) -> pd.DataFrame:
    """Server-side peer-filtered pull of the attrition report, tidied."""
    df = pull(DATASET_ID, SELECT, codes["districts"], has_org_type=True)
    return tidy(canon_peer(df, codes))


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_peer_codes()
    print(f"Peer universe: {len(codes['schools'])} schools, "
          f"{len(codes['districts'])} districts.\n")

    print(f"Pulling student attrition ({DATASET_ID}) from DESE SODA (full precision)…")
    df = fetch_attrition(codes)

    out = PROCESSED_DIR / "student_attrition.parquet"
    if df is None or df.empty:
        print("  [skip] student_attrition: empty fetch — existing file left untouched")
        return 1

    df.to_parquet(out, index=False)

    has_lynn = "yes" if (df["DIST_CODE"] == LYNN_DISTRICT_CODE).any() else "NO"
    has_lehs = "yes" if (df["ORG_CODE"] == LEHS_SCHOOL_CODE).any() else "NO"
    years = f"{int(df['SY'].min())}-{int(df['SY'].max())}"
    print(f"  [OK] student_attrition {len(df):>7,} rows  "
          f"Lynn={has_lynn}  LEHS={has_lehs}  SY {years}")
    print(f"\nWritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
