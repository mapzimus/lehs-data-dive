"""
Identify peer schools by inspecting downloaded MCAS data.

Outputs to data/processed/_peer_schools.json:
  - lehs_school_code:  confirmed code for Lynn English High
  - lynn_district_hs:  every school in Lynn with any grade-9-12 MCAS rows
  - lynn_sibling_hs:   resolved codes for Classical, Lynn Tech, Fecteau-Leary,
                       Frederick Douglass, Harold Durgin Success Academy
  - gateway_main_hs:   for each gateway city, the school with highest grade-10
                       STU_CNT (excluding district rows) — i.e., the main
                       comprehensive HS

Rules:
  - Only ORG_TYPE in ("Public School", "Charter School") — never district rows
  - "Main HS" = highest sum of STU_CNT in grade 10 across all years/subjects
  - Sibling matching: require name overlap on a distinctive word (not just "Lynn")

Run AFTER 01_download_e2c.py has produced data/raw/e2c_hub/mcas_achievement.csv.
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
    PROCESSED_DIR,
    RAW_DIR,
)

MCAS_CSV = RAW_DIR / "e2c_hub" / "mcas_achievement.csv"
OUTPUT_JSON = PROCESSED_DIR / "_peer_schools.json"

SCHOOL_ORG_TYPES = ("Public School", "Charter School")

# Sibling target -> distinctive keywords that MUST appear in the school name
# (avoids matching the bare district "Lynn" row when looking for Lynn English)
SIBLING_TARGETS = {
    "Lynn English High":                     ["english"],
    "Classical High (Lynn)":                 ["classical"],
    "Lynn Vocational Technical Institute":   ["vocational", "technical", "lynn tech"],
    "Fecteau-Leary Junior/Senior HS":        ["fecteau", "leary"],
    "Fredrick Douglass Collegiate Academy":  ["douglass"],
    "Harold Durgin Success Academy":         ["durgin"],
}


def load_mcas_min() -> pd.DataFrame:
    """Load only the columns we need from MCAS (faster than full load)."""
    if not MCAS_CSV.exists():
        raise FileNotFoundError(f"{MCAS_CSV} not found. Run scripts/01_download_e2c.py first.")
    return pd.read_csv(
        MCAS_CSV,
        usecols=[
            "SY", "DIST_CODE", "DIST_NAME", "ORG_CODE", "ORG_NAME",
            "ORG_TYPE", "TEST_GRADE", "STU_CNT",
        ],
        dtype={"DIST_CODE": str, "ORG_CODE": str, "TEST_GRADE": str},
        low_memory=False,
    )


def normalize_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Zero-pad 8-digit codes."""
    df = df.copy()
    df["DIST_CODE"] = df["DIST_CODE"].fillna("").str.zfill(8)
    df["ORG_CODE"] = df["ORG_CODE"].fillna("").str.zfill(8)
    return df


def lynn_district_high_schools(mcas: pd.DataFrame) -> dict[str, str]:
    """All Lynn schools with any high-school grade (9-12) MCAS data.

    Includes grades 9, 10, 11, 12 — Fecteau-Leary may serve different grades
    than the main HS, so we cast a wide net.
    """
    hs_grades = mcas["TEST_GRADE"].astype(str).isin(["09", "10", "11", "12", "9", "10", "11", "12"])
    in_lynn = mcas["DIST_CODE"] == LYNN_DISTRICT_CODE
    is_school = mcas["ORG_TYPE"].isin(SCHOOL_ORG_TYPES)
    sub = mcas[hs_grades & in_lynn & is_school][["ORG_CODE", "ORG_NAME"]].drop_duplicates()
    return dict(zip(sub["ORG_NAME"], sub["ORG_CODE"]))


def lynn_all_schools(mcas: pd.DataFrame) -> dict[str, str]:
    """Every Lynn district school (any grade)."""
    in_lynn = mcas["DIST_CODE"] == LYNN_DISTRICT_CODE
    is_school = mcas["ORG_TYPE"].isin(SCHOOL_ORG_TYPES)
    sub = mcas[in_lynn & is_school][["ORG_CODE", "ORG_NAME"]].drop_duplicates()
    return dict(zip(sub["ORG_NAME"], sub["ORG_CODE"]))


def lynn_tech_lookup(mcas: pd.DataFrame) -> tuple[str, str] | None:
    """Lynn Vocational Technical Institute may be its own district outside
    the Lynn Public Schools district code. Find it statewide by name."""
    is_school = mcas["ORG_TYPE"].isin(SCHOOL_ORG_TYPES)
    name_match = mcas["ORG_NAME"].str.contains("Lynn Vocational", case=False, na=False)
    sub = mcas[is_school & name_match][["ORG_CODE", "ORG_NAME", "DIST_NAME"]].drop_duplicates()
    if sub.empty:
        return None
    row = sub.iloc[0]
    return row["ORG_NAME"], row["ORG_CODE"]


def fuzzy_match_sibling(keywords: list[str], schools: dict[str, str]) -> tuple[str, str] | None:
    """Pick the school whose name contains ALL the distinctive keywords (case-insensitive)."""
    for name, code in schools.items():
        name_lower = name.lower()
        if all(kw.lower() in name_lower for kw in keywords):
            return name, code
    # Fallback: any keyword match
    for name, code in schools.items():
        name_lower = name.lower()
        if any(kw.lower() in name_lower for kw in keywords):
            return name, code
    return None


def identify_gateway_main_hs(mcas: pd.DataFrame) -> dict[str, dict]:
    """For each gateway city, pick the school with the highest grade-10 STU_CNT
    (summed across years and subjects), restricted to actual school rows."""
    is_school = mcas["ORG_TYPE"].isin(SCHOOL_ORG_TYPES)
    is_g10 = mcas["TEST_GRADE"].astype(str).isin(["10"])
    g10_schools = mcas[is_school & is_g10].copy()
    g10_schools["STU_CNT"] = pd.to_numeric(g10_schools["STU_CNT"], errors="coerce").fillna(0)

    out: dict[str, dict] = {}
    for city in GATEWAY_CITIES:
        in_city = g10_schools["DIST_NAME"].astype(str).str.lower() == city.lower()
        sub = g10_schools[in_city]
        if sub.empty:
            out[city] = {"name": None, "school_code": None, "district_code": None, "total_stu_cnt": 0}
            continue
        ranked = (
            sub.groupby(["ORG_NAME", "ORG_CODE", "DIST_CODE"])["STU_CNT"]
            .sum()
            .reset_index()
            .sort_values("STU_CNT", ascending=False)
        )
        top = ranked.iloc[0]
        out[city] = {
            "name": top["ORG_NAME"],
            "school_code": top["ORG_CODE"],
            "district_code": top["DIST_CODE"],
            "total_stu_cnt": int(top["STU_CNT"]),
            "runner_up": ranked.iloc[1].to_dict() if len(ranked) > 1 else None,
        }
    return out


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading MCAS dataset (relevant columns only)...")
    mcas = load_mcas_min()
    mcas = normalize_codes(mcas)
    print(f"  {len(mcas):,} rows loaded")

    print("\n--- Lynn district schools (HS grades 9-12) ---")
    lynn_hs = lynn_district_high_schools(mcas)
    for name, code in sorted(lynn_hs.items(), key=lambda x: x[1]):
        print(f"  {code}  {name}")

    print("\n--- Lynn district: all schools ---")
    lynn_all = lynn_all_schools(mcas)
    print(f"  {len(lynn_all)} total Lynn schools")

    # Lynn Tech may live outside the Lynn district code
    tech_match = lynn_tech_lookup(mcas)
    if tech_match:
        print(f"\n--- Lynn Vocational Technical Institute (statewide search) ---")
        print(f"  {tech_match[1]}  {tech_match[0]}")

    print("\n--- Sibling school matching ---")
    sibling_codes: dict[str, dict | None] = {}
    # Combine Lynn district HS + Lynn Tech (if found elsewhere) for matching pool
    candidates = dict(lynn_hs)
    if tech_match:
        candidates[tech_match[0]] = tech_match[1]

    for sibling_name, keywords in SIBLING_TARGETS.items():
        match = fuzzy_match_sibling(keywords, candidates)
        if match:
            actual_name, code = match
            sibling_codes[sibling_name] = {"name": actual_name, "school_code": code}
            print(f"  [OK]  {sibling_name:50s} -> {code}  {actual_name}")
        else:
            sibling_codes[sibling_name] = None
            print(f"  [X]   {sibling_name:50s} -> NOT FOUND")

    lehs = sibling_codes.get("Lynn English High")
    lehs_code = lehs["school_code"] if lehs else None

    print("\n--- Gateway city main HS (by grade-10 enrollment) ---")
    gateway_main = identify_gateway_main_hs(mcas)
    for city, info in gateway_main.items():
        if info["school_code"]:
            ru = info.get("runner_up")
            ru_str = f"  (runner-up: {ru['ORG_NAME']}, n={int(ru['STU_CNT'])})" if ru else ""
            print(f"  {city:15s} -> {info['school_code']}  {info['name']}  (n={info['total_stu_cnt']:,}){ru_str}")
        else:
            print(f"  {city:15s} -> (none found with grade-10 data)")

    payload = {
        "lehs_school_code": lehs_code,
        "lynn_district_code": LYNN_DISTRICT_CODE,
        "lynn_district_hs": lynn_hs,
        "lynn_all_schools": lynn_all,
        "lynn_sibling_hs": sibling_codes,
        "gateway_main_hs": gateway_main,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\nWrote: {OUTPUT_JSON}")
    print(f"\nLEHS school code: {lehs_code}")


if __name__ == "__main__":
    main()
