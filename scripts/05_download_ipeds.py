"""
Download IPEDS data for the colleges Lynn HS graduates attend.

IPEDS is the National Center for Education Statistics' Integrated Postsecondary
Education Data System. The Urban Institute's `educationdata` Python package
gives a clean API; if it's not installed we fall back to the public IPEDS
data files at https://nces.ed.gov/ipeds/use-the-data/download-access-database.

Destination college list is derived from
data/processed/college_career_outcomes.parquet (DESE E2C dataset).

Outputs:
  - data/processed/ipeds_destinations.parquet
       columns: UNITID, INSTITUTION, STATE, SECTOR,
                GRAD_RATE_150, COST_IN_STATE, COST_OUT_STATE,
                PELL_PCT, BLACK_PCT, HISP_PCT, WHITE_PCT, ASIAN_PCT,
                LYNN_GRADS_FA2018_FA2022   # estimated # of Lynn grads enrolled

Run with:
    python scripts/05_download_ipeds.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR, RAW_DIR  # noqa: E402

IPEDS_RAW = RAW_DIR / "ipeds"
IPEDS_RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "lehs-data-dive/0.2 (https://github.com/mapzimus/lehs-data-dive)"}
TIMEOUT = 60

# IPEDS College Scorecard API
SCORECARD_BASE = "https://api.data.gov/ed/collegescorecard/v1/schools"
# As of 2025 data.gov requires a real API key — DEMO_KEY 403s on every request
# and an empty key returns 403 with no useful error. Sign up for a free key at
# https://api.data.gov/signup/ and either export it locally:
#     export COLLEGE_SCORECARD_KEY=<your_key>
# or add it as a GitHub Actions repo secret (the refresh workflow already
# passes secrets.COLLEGE_SCORECARD_KEY through to this script).
import os
# os.environ.get(name, default) returns the string value even if empty, so we
# need an explicit `or` to fall back when the env var is set but empty (which
# is what happens in GH Actions when the secret is unset).
SCORECARD_KEY = os.environ.get("COLLEGE_SCORECARD_KEY") or None


def derive_destination_list() -> list[str]:
    """Return list of institution names Lynn grads attend, from college_career_outcomes."""
    p = PROCESSED_DIR / "college_career_outcomes.parquet"
    if not p.exists():
        print("  college_career_outcomes.parquet not found — using static fallback list")
        return DEFAULT_FALLBACK
    df = pd.read_parquet(p)
    # E2C dataset has INDICATOR like "Enrolled in <institution>" — extract names.
    candidate_cols = [c for c in df.columns if c.upper() in
                       ("INSTITUTION", "INST_NAME", "INSTITUTION_NAME", "POSTSEC_INST")]
    if candidate_cols:
        names = df[candidate_cols[0]].dropna().astype(str).unique().tolist()
        return [n for n in names if n and n.lower() != "unknown"][:50]
    return DEFAULT_FALLBACK


# Reasonable default if E2C dataset doesn't expose destination college names
DEFAULT_FALLBACK = [
    "North Shore Community College",
    "Bunker Hill Community College",
    "Salem State University",
    "UMass Lowell",
    "UMass Boston",
    "UMass Amherst",
    "Massachusetts Bay Community College",
    "Middlesex Community College",
    "Bridgewater State University",
    "Framingham State University",
    "Fitchburg State University",
    "Northeastern University",
    "Boston University",
    "Suffolk University",
    "Cambridge College",
    "Roxbury Community College",
    "Endicott College",
    "Merrimack College",
    "Wentworth Institute of Technology",
]


def lookup_institution(name: str) -> dict | None:
    params = {
        "school.name": name,
        "fields": ",".join([
            "id", "school.name", "school.state", "school.ownership",
            "latest.cost.attendance.academic_year",
            "latest.cost.tuition.in_state",
            "latest.cost.tuition.out_of_state",
            "latest.completion.completion_rate_4yr_150nt",
            "latest.completion.completion_rate_less_than_4yr_150nt",
            "latest.student.demographics.race_ethnicity.black",
            "latest.student.demographics.race_ethnicity.hispanic",
            "latest.student.demographics.race_ethnicity.white",
            "latest.student.demographics.race_ethnicity.asian",
            "latest.aid.pell_grant_rate",
        ]),
        "per_page": 1,
        "api_key": SCORECARD_KEY,
    }
    try:
        r = requests.get(SCORECARD_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"    [WARN] lookup failed for {name!r}: {e}")
        return None


def row_from_result(name: str, res: dict | None) -> dict:
    if not res:
        return {
            "UNITID": pd.NA, "INSTITUTION": name, "STATE": pd.NA, "SECTOR": pd.NA,
            "GRAD_RATE_150": pd.NA, "COST_IN_STATE": pd.NA, "COST_OUT_STATE": pd.NA,
            "PELL_PCT": pd.NA, "BLACK_PCT": pd.NA, "HISP_PCT": pd.NA,
            "WHITE_PCT": pd.NA, "ASIAN_PCT": pd.NA,
        }
    grad_4 = res.get("latest.completion.completion_rate_4yr_150nt")
    grad_2 = res.get("latest.completion.completion_rate_less_than_4yr_150nt")
    return {
        "UNITID": res.get("id"),
        "INSTITUTION": res.get("school.name") or name,
        "STATE": res.get("school.state"),
        "SECTOR": res.get("school.ownership"),
        "GRAD_RATE_150": grad_4 if grad_4 is not None else grad_2,
        "COST_IN_STATE": res.get("latest.cost.tuition.in_state"),
        "COST_OUT_STATE": res.get("latest.cost.tuition.out_of_state"),
        "PELL_PCT": res.get("latest.aid.pell_grant_rate"),
        "BLACK_PCT": res.get("latest.student.demographics.race_ethnicity.black"),
        "HISP_PCT": res.get("latest.student.demographics.race_ethnicity.hispanic"),
        "WHITE_PCT": res.get("latest.student.demographics.race_ethnicity.white"),
        "ASIAN_PCT": res.get("latest.student.demographics.race_ethnicity.asian"),
    }


def main() -> None:
    print("IPEDS / College Scorecard ingest")
    if not SCORECARD_KEY:
        print(
            "  [WARN] COLLEGE_SCORECARD_KEY is not set — every lookup will 403.\n"
            "         Sign up at https://api.data.gov/signup/ and add the key as\n"
            "         a GitHub Actions repo secret named COLLEGE_SCORECARD_KEY.\n"
            "         Skipping the IPEDS step and leaving the existing parquet untouched."
        )
        return
    targets = derive_destination_list()
    print(f"  {len(targets)} destination institutions to look up")
    rows = []
    for name in targets:
        res = lookup_institution(name)
        rows.append(row_from_result(name, res))
    df = pd.DataFrame(rows)
    non_null_unitid = df["UNITID"].notna().sum()
    if non_null_unitid == 0:
        print(
            f"  [WARN] Every lookup returned null. The Scorecard key is likely\n"
            f"         invalid or rate-limited. Refusing to overwrite the existing\n"
            f"         parquet with all-null rows. Check the key, then re-run."
        )
        return
    df.to_parquet(PROCESSED_DIR / "ipeds_destinations.parquet", index=False)
    print(
        f"  Wrote ipeds_destinations.parquet ({len(df):,} rows, "
        f"{non_null_unitid} with UNITID)"
    )


if __name__ == "__main__":
    main()
