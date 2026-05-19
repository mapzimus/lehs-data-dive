"""
Identify peer schools by inspecting downloaded MCAS data.

Outputs to data/processed/_peer_schools.json:
  - LEHS_SCHOOL_CODE: confirmed code for Lynn English High
  - LYNN_SIBLING_HS:  codes for Classical, Lynn Tech, Fecteau-Leary, Frederick Douglass
  - LYNN_DISTRICT_HS: all Lynn district schools with grade 9-12 enrollment
  - GATEWAY_MAIN_HS:  one main comprehensive HS per gateway city

Rule for "main comprehensive HS in a gateway city":
  - District is the city in question
  - School serves grade 10
  - Among such schools, pick the one with highest grade-10 enrollment

Run AFTER 01_download_e2c.py has produced data/raw/e2c_hub/mcas_achievement.csv
and enrollment_demographics.csv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    GATEWAY_CITIES,
    LYNN_DISTRICT_CODE,
    LYNN_SIBLING_HS,
    PROCESSED_DIR,
    RAW_DIR,
)

MCAS_CSV = RAW_DIR / "e2c_hub" / "mcas_achievement.csv"
ENROLLMENT_CSV = RAW_DIR / "e2c_hub" / "enrollment_demographics.csv"
OUTPUT_JSON = PROCESSED_DIR / "_peer_schools.json"


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find the first column whose name (case-insensitive) matches a candidate."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None


def load_mcas() -> pd.DataFrame:
    if not MCAS_CSV.exists():
        raise FileNotFoundError(
            f"{MCAS_CSV} not found. Run scripts/01_download_e2c.py first."
        )
    return pd.read_csv(MCAS_CSV, low_memory=False)


def identify_lynn_high_schools(mcas: pd.DataFrame) -> dict[str, str]:
    """Find all Lynn schools that serve grade 10."""
    org_code_col = _find_column(mcas, ["org_code", "school_code", "orgcode"])
    school_code_col = _find_column(mcas, ["school_code", "sch_code"]) or org_code_col
    name_col = _find_column(mcas, ["school_name", "org_name", "schoolname"])
    district_code_col = _find_column(mcas, ["district_code", "dist_code", "districtcode"])
    grade_col = _find_column(mcas, ["grade", "test_grade"])

    if not (name_col and school_code_col and grade_col):
        raise RuntimeError(
            f"Could not find expected columns in MCAS. Columns: {list(mcas.columns)}"
        )

    # filter: Lynn district + grade 10
    if district_code_col:
        in_lynn = mcas[district_code_col].astype(str).str.zfill(8) == LYNN_DISTRICT_CODE
    else:
        in_lynn = mcas[school_code_col].astype(str).str.startswith("01630")
    grade10 = mcas[grade_col].astype(str).str.contains("10")

    sub = mcas[in_lynn & grade10][[school_code_col, name_col]].drop_duplicates()
    return dict(zip(sub[name_col], sub[school_code_col].astype(str).str.zfill(8)))


def fuzzy_match_sibling(name: str, lynn_hs: dict[str, str]) -> str | None:
    """Match a sibling-school target name to a DESE name (case-insensitive contains)."""
    target = name.lower()
    for actual_name, code in lynn_hs.items():
        if target in actual_name.lower() or actual_name.lower() in target:
            return code
    return None


def identify_gateway_main_hs(enrollment: pd.DataFrame, mcas: pd.DataFrame) -> dict[str, dict]:
    """For each gateway city, pick the school with the highest grade-10 enrollment."""
    org_code_col = _find_column(mcas, ["org_code", "school_code", "orgcode"])
    name_col = _find_column(mcas, ["school_name", "org_name"])
    district_name_col = _find_column(mcas, ["district_name", "dist_name", "districtname"])
    student_count_col = _find_column(mcas, ["student_count", "tested_count", "n_tested", "students_included"])
    grade_col = _find_column(mcas, ["grade", "test_grade"])

    out: dict[str, dict] = {}
    if not (name_col and district_name_col and grade_col):
        print(f"  warning: missing columns for gateway main-HS detection. cols={list(mcas.columns)[:20]}")
        return out

    grade10 = mcas[grade_col].astype(str).str.contains("10")
    g10 = mcas[grade10]

    for city in GATEWAY_CITIES:
        in_city = g10[district_name_col].astype(str).str.lower() == city.lower()
        city_data = g10[in_city]
        if city_data.empty:
            out[city] = {"name": None, "school_code": None}
            continue
        # pick school with highest student count if available, else first
        if student_count_col and student_count_col in city_data.columns:
            picked = (
                city_data.groupby([name_col, org_code_col])[student_count_col]
                .sum()
                .reset_index()
                .sort_values(student_count_col, ascending=False)
                .iloc[0]
            )
        else:
            picked = city_data[[name_col, org_code_col]].drop_duplicates().iloc[0]
        out[city] = {
            "name": picked[name_col],
            "school_code": str(picked[org_code_col]).zfill(8),
        }
    return out


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading MCAS dataset...")
    mcas = load_mcas()
    print(f"  {len(mcas):,} rows, {len(mcas.columns)} columns")
    print(f"  columns: {list(mcas.columns)[:15]}")

    print("\nIdentifying Lynn district high schools (grade 10)...")
    lynn_hs = identify_lynn_high_schools(mcas)
    for name, code in lynn_hs.items():
        print(f"  {code}  {name}")

    sibling_codes = {}
    for sibling_name in LYNN_SIBLING_HS:
        code = fuzzy_match_sibling(sibling_name, lynn_hs)
        sibling_codes[sibling_name] = code
        status = "[OK]" if code else "[X]"
        print(f"  {status} sibling match: '{sibling_name}' --> {code or 'NOT FOUND'}")

    lehs_code = sibling_codes.get("Lynn English High") or fuzzy_match_sibling(
        "Lynn English", lynn_hs
    )

    print("\nIdentifying main comprehensive HS in each gateway city...")
    gateway_main = identify_gateway_main_hs(None, mcas)
    for city, info in gateway_main.items():
        if info["school_code"]:
            print(f"  {city:15s} --> {info['school_code']}  {info['name']}")
        else:
            print(f"  {city:15s} --> (none found)")

    payload = {
        "lehs_school_code": lehs_code,
        "lynn_district_code": LYNN_DISTRICT_CODE,
        "lynn_district_hs": lynn_hs,
        "lynn_sibling_hs": sibling_codes,
        "gateway_main_hs": gateway_main,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
