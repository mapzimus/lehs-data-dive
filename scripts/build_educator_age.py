"""
Build the Lynn/LEHS slice of DESE's **Educators by Age** dataset (a4b4-k49f) —
the share of each org's educator FTE that falls in each age band, by job
category. Pulled from the SODA JSON API at full precision and peer-filtered to
the LEHS + Lynn + 26-gateway + State universe (see utils/gap_sources.py),
exactly like scripts/build_gap_datasets.py.

Writes data/processed/educators_by_age.parquet (all job_cat/job_name rows kept;
the page surfaces the All/All rollup). The *_pct columns are 0-1 fractions of
FTE in each age band:
    UND_26_PCT  BTWN_26_32_PCT  BTWN_33_40_PCT  BTWN_41_48_PCT
    BTWN_49_56_PCT  BTWN_57_64_PCT  OVR_64_PCT
The ALL-educators rollup is the row where JOB_CAT == 'All' AND JOB_NAME == 'All'
(DESE's literal label, same convention as the staffing dataset).

Derived columns added for convenience:
    NEAR_RETIRE_PCT = BTWN_57_64_PCT + OVR_64_PCT   (workforce nearing retirement)

Re-runnable and additive: only educators_by_age.parquet is touched, and a fetch
that fails soft leaves any existing file untouched. Run:
    python scripts/build_educator_age.py
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

DATASET_ID = "a4b4-k49f"
SELECT = (
    "dist_code,dist_name,org_code,org_name,org_type,sy,job_cat,job_name,fte_cnt,"
    "und_26_pct,btwn_26_32_pct,btwn_33_40_pct,btwn_41_48_pct,btwn_49_56_pct,"
    "btwn_57_64_pct,ovr_64_pct"
)

# The age-band share columns, oldest→youngest split-out used for the derived
# near-retirement column (DESE bands; *_pct are 0-1 fractions of FTE).
NEAR_RETIRE_COLS = ["BTWN_57_64_PCT", "OVR_64_PCT"]


def build_educators_by_age(codes) -> pd.DataFrame:
    df = pull(DATASET_ID, SELECT, codes["districts"], has_org_type=True)
    df = canon_peer(df, codes)
    if df.empty:
        return df
    # gap_sources.STRING_COLS doesn't list job_cat/job_name, so tidy() would
    # coerce these label columns to NaN floats. Preserve the raw strings
    # (canon_peer keeps the original index) and restore them after tidy. We must
    # not edit utils/ (shared across parallel agents), so fix it locally here.
    job_cols = df[["job_cat", "job_name"]].astype("string")
    df = tidy(df)
    df["JOB_CAT"] = job_cols["job_cat"].values
    df["JOB_NAME"] = job_cols["job_name"].values
    # Workforce nearing retirement = the two oldest bands combined.
    df["NEAR_RETIRE_PCT"] = (
        pd.to_numeric(df["BTWN_57_64_PCT"], errors="coerce").fillna(0)
        + pd.to_numeric(df["OVR_64_PCT"], errors="coerce").fillna(0)
    ).round(4)
    return df


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_peer_codes()
    print(f"Peer universe: {len(codes['schools'])} schools, "
          f"{len(codes['districts'])} districts (+State).\n")

    print(f"Pulling educators-by-age ({DATASET_ID}) from DESE SODA (full precision)…")
    df = build_educators_by_age(codes)
    out = PROCESSED_DIR / "educators_by_age.parquet"
    if df.empty:
        print("  [skip] educators_by_age: empty fetch — existing file left untouched")
        return 1

    df.to_parquet(out, index=False)
    has_lynn = "yes" if (df["DIST_CODE"] == LYNN_DISTRICT_CODE).any() else "NO"
    has_lehs = "yes" if (df["ORG_CODE"] == LEHS_SCHOOL_CODE).any() else "NO"
    years = f"{int(df['SY'].min())}–{int(df['SY'].max())}"
    rollup = df[(df["JOB_CAT"] == "All") & (df["JOB_NAME"] == "All")]
    print(f"  [OK] educators_by_age  {len(df):,} rows  "
          f"Lynn={has_lynn}  LEHS={has_lehs}  SY {years}")
    print(f"       All/All rollup rows: {len(rollup):,} "
          f"(LEHS rollup years: {sorted(rollup[rollup['ORG_CODE']==LEHS_SCHOOL_CODE]['SY'].dropna().astype(int).tolist())})")
    print(f"\nWritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
