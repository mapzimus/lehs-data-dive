"""
Download US Census ACS 5-year (most recent) data for Lynn (Essex County, MA).

Tables we pull (tract-level):
  - B19013 — Median household income
  - B17001 — Poverty status (count of children below poverty)
  - B05002 — Place of birth (% foreign-born)
  - B15003 — Educational attainment for population 25+
  - B16001 — Language spoken at home for population 5+ (THE big one for ELL story)
  - B25070 — Gross rent as % of household income (housing burden)

Lynn is in Essex County, MA: state FIPS 25, county FIPS 009.
We pull ALL tracts in Essex County, then filter to Lynn tracts via tract-name match
(Lynn tracts are 2031-2074 in Essex County).

API: data.census.gov — REQUIRES A FREE API KEY (instant signup):
  https://api.census.gov/data/key_signup.html
Set the key as environment variable CENSUS_API_KEY before running this script.
Without a key the script exits gracefully — the rest of the dashboard works fine,
just without tract-level Census overlays.

Outputs to data/raw/gis/census_acs/
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import RAW_DIR  # noqa: E402

ACS_YEAR = 2023  # most recent ACS 5-year as of 2026 (covers 2019-2023)
ACS_STATE = "25"  # MA
ACS_COUNTY = "009"  # Essex County (where Lynn is)

OUT_DIR = RAW_DIR / "gis" / "census_acs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "lehs-data-dive/0.1 (github.com/mapzimus/lehs-data-dive)"
HEADERS = {"User-Agent": USER_AGENT}

API_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()


def fetch(variables: list[str], description: str) -> list[list]:
    """Fetch ACS variables for all tracts in Essex County."""
    var_str = ",".join(["NAME"] + variables)
    params = {
        "get": var_str,
        "for": "tract:*",
        "in": f"state:{ACS_STATE}+county:{ACS_COUNTY}",
    }
    if API_KEY:
        params["key"] = API_KEY
    print(f"  {description}")
    r = requests.get(API_BASE, params=params, headers=HEADERS, timeout=60)
    if r.status_code != 200 or "text/html" in r.headers.get("content-type", ""):
        snippet = r.text[:200].replace("\n", " ")
        print(f"  [X] HTTP {r.status_code} (likely missing/invalid key): {snippet}")
        return []
    try:
        data = r.json()
    except Exception as e:
        print(f"  [X] failed to parse JSON: {e}")
        return []
    print(f"  [OK] got {len(data)-1} rows")
    return data


# Variables to pull per table (with friendly aliases)
TABLES = {
    "median_household_income": {
        "vars": ["B19013_001E"],
        "alias_map": {"B19013_001E": "median_household_income"},
    },
    "poverty_under_18": {
        # B17001: poverty status, broken out by age & sex
        # Total below poverty under 18 = sum of male+female 6yr-cohort cells
        "vars": ["B17001_004E", "B17001_005E", "B17001_006E", "B17001_007E", "B17001_008E", "B17001_009E",
                 "B17001_018E", "B17001_019E", "B17001_020E", "B17001_021E", "B17001_022E", "B17001_023E",
                 "B17001_001E"],
        "alias_map": {},
    },
    "place_of_birth": {
        # B05002_001E = total, B05002_013E = foreign-born
        "vars": ["B05002_001E", "B05002_013E"],
        "alias_map": {"B05002_001E": "pop_total", "B05002_013E": "foreign_born_total"},
    },
    "educational_attainment": {
        # B15003_001E = total 25+, _022E = bachelor's, _023E = master's, _024E = professional, _025E = doctorate
        "vars": ["B15003_001E", "B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E"],
        "alias_map": {
            "B15003_001E": "edu_pop_25plus",
            "B15003_022E": "bachelors",
            "B15003_023E": "masters",
            "B15003_024E": "professional",
            "B15003_025E": "doctorate",
        },
    },
    "language_spoken_at_home": {
        # C16001 — collapsed language groups, available at tract level.
        # (B16001 is suppressed at tract resolution by Census.)
        "vars": [
            "C16001_001E",  # total pop 5+
            "C16001_002E",  # English only
            "C16001_003E",  # Spanish (Spanish + Spanish Creole)
            "C16001_006E",  # French, Haitian, or Cajun
            "C16001_009E",  # German or other West Germanic
            "C16001_012E",  # Russian, Polish, or other Slavic
            "C16001_015E",  # Other Indo-European (incl Portuguese, Greek, Persian, Hindi)
            "C16001_018E",  # Korean
            "C16001_021E",  # Chinese (incl Mandarin, Cantonese)
            "C16001_024E",  # Vietnamese
            "C16001_027E",  # Tagalog (incl Filipino)
            "C16001_030E",  # Other Asian and Pacific Island (incl Khmer, Lao, Thai)
            "C16001_033E",  # Arabic
            "C16001_036E",  # Other & unspecified
        ],
        "alias_map": {
            "C16001_001E": "lang_total",
            "C16001_002E": "lang_english_only",
            "C16001_003E": "lang_spanish",
            "C16001_006E": "lang_french_haitian_cajun",
            "C16001_009E": "lang_german_west_germanic",
            "C16001_012E": "lang_russian_polish_slavic",
            "C16001_015E": "lang_other_indo_european",
            "C16001_018E": "lang_korean",
            "C16001_021E": "lang_chinese",
            "C16001_024E": "lang_vietnamese",
            "C16001_027E": "lang_tagalog",
            "C16001_030E": "lang_other_asian_pacific",
            "C16001_033E": "lang_arabic",
            "C16001_036E": "lang_other_unspecified",
        },
    },
    "housing_burden": {
        # B25070 — gross rent as % of household income (renter households)
        # _001E total, _007E = 30-34.9%, _008E = 35-39.9%, _009E = 40-49.9%, _010E = 50%+
        "vars": ["B25070_001E", "B25070_007E", "B25070_008E", "B25070_009E", "B25070_010E"],
        "alias_map": {
            "B25070_001E": "renter_total",
            "B25070_007E": "rent_burden_30_35",
            "B25070_008E": "rent_burden_35_40",
            "B25070_009E": "rent_burden_40_50",
            "B25070_010E": "rent_burden_50plus",
        },
    },
}


def main() -> None:
    if not API_KEY:
        print("=" * 70)
        print("WARNING: CENSUS_API_KEY environment variable not set.")
        print("=" * 70)
        print()
        print("Get a free key (instant, requires email):")
        print("  https://api.census.gov/data/key_signup.html")
        print()
        print("Then set it in your shell before re-running this script:")
        print("  PowerShell:  $env:CENSUS_API_KEY = 'YOUR_KEY_HERE'")
        print("  Bash:        export CENSUS_API_KEY=YOUR_KEY_HERE")
        print()
        print("Without a key, this script will exit gracefully.")
        print("The rest of the dashboard works fine — only the tract-level")
        print("Census overlays in Lynn Maps Equity will be empty.")
        print()
        sys.exit(0)

    print(f"Pulling ACS {ACS_YEAR} 5-year data for Essex County, MA...")
    print(f"Target dir: {OUT_DIR}\n")
    for table_name, spec in TABLES.items():
        out_file = OUT_DIR / f"{table_name}.json"
        if out_file.exists():
            print(f"-> {table_name}: SKIP (already exists)")
            continue
        print(f"-> {table_name}: {len(spec['vars'])} variables")
        data = fetch(spec["vars"], table_name)
        if not data:
            continue
        out_file.write_text(json.dumps({
            "table": table_name,
            "year": ACS_YEAR,
            "state": ACS_STATE,
            "county": ACS_COUNTY,
            "alias_map": spec["alias_map"],
            "data": data,
        }, indent=2))
        print(f"  [OK] wrote {out_file}")
    print("\nDone.")


if __name__ == "__main__":
    main()
