"""
Download US Census ACS 5-year data at the **place** (city) level for Lynn, MA.

This is the city-wide pull that backs `pages/Lynn_City.py`. The
tract-level pull at scripts/10_download_census_acs.py covers Lynn's 22 census
tracts; this script gets the rolled-up city statistics, plus the deeper
tables that aren't published at tract level (e.g., country-of-birth detail,
fine-grained language splits).

Lynn is Census place 37000 in state 25 (MA).

Outputs to data/processed/:
  - lynn_city_stats.parquet        — wide one-row dataframe of headline stats
  - lynn_birthplaces.parquet       — long: country-of-birth → count
  - lynn_languages.parquet         — long: detailed language group → count
  - lynn_industries.parquet        — long: industry → employed count
  - lynn_commute.parquet           — long: commute mode → count
  - lynn_age_pyramid.parquet       — long: age band × sex → count

Run with:
    python scripts/14_download_lynn_city_stats.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR, RAW_DIR  # noqa: E402

ACS_YEAR = 2024  # 2020-2024 ACS 5-year (released Jan 29, 2026); requires CENSUS_API_KEY
ACS_STATE = "25"
ACS_PLACE = "37490"  # Lynn city, MA (verified via Census API place lookup)

OUT_RAW = RAW_DIR / "gis" / "census_acs_place"
OUT_RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "lehs-data-dive/0.2 (github.com/mapzimus/lehs-data-dive)"}
TIMEOUT = 60
API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()
API_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
PROFILE_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5/profile"
SUBJECT_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5/subject"


def fetch(base: str, variables: list[str], desc: str) -> list[list]:
    var_str = ",".join(["NAME"] + variables)
    params = {
        "get": var_str,
        "for": f"place:{ACS_PLACE}",
        "in": f"state:{ACS_STATE}",
    }
    if API_KEY:
        params["key"] = API_KEY
    print(f"  {desc} ({len(variables)} vars)")
    try:
        r = requests.get(base, params=params, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"    [WARN] HTTP {r.status_code}: {r.text[:200]}")
            return []
        return r.json()
    except Exception as e:
        print(f"    [WARN] {e}")
        return []


def _to_dict(rows: list[list]) -> dict:
    if not rows or len(rows) < 2:
        return {}
    return dict(zip(rows[0], rows[1]))


# ---------------------------------------------------------------------------
# Census label -> variable code resolution
# ---------------------------------------------------------------------------
# ACS variable codes are renumbered between vintages whenever Census inserts
# rows into a table (DP05 gained detailed ancestry rows in 2023 and more in
# 2024, so "DP05_0038E" went from Black-alone to "White!!Egyptian"). Every
# table below is keyed by its Census *label* instead, and the codes are looked
# up from that vintage's groups/{TABLE}.json at run time. A label Census has
# reworded fails loudly rather than silently pulling a neighbouring row.

_GROUP_CACHE: dict[str, dict] = {}


def _norm_label(label: str) -> str:
    # Income labels carry the vintage ("IN 2024 INFLATION-ADJUSTED DOLLARS")
    # and detail-table labels end each level with ":" — drop both.
    label = re.sub(r"\(IN \d{4} INFLATION-ADJUSTED DOLLARS\)",
                   "(IN INFLATION-ADJUSTED DOLLARS)", label)
    return label.replace(":!!", "!!").rstrip(":")


def resolve(base: str, table: str, labels: dict[str, str]) -> dict[str, str]:
    """Map {Census label: our name} to {variable code: our name} for this vintage."""
    if table not in _GROUP_CACHE:
        r = requests.get(f"{base}/groups/{table}.json", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        _GROUP_CACHE[table] = r.json()["variables"]
    # Estimate codes end in "E", percent codes in "PE"; skip annotation/MOE codes.
    index = {_norm_label(v["label"]): code
             for code, v in _GROUP_CACHE[table].items() if code.endswith("E")}
    out, missing = {}, []
    for label, name in labels.items():
        code = index.get(_norm_label(label))
        if code is None:
            missing.append(label)
        else:
            out[code] = name
    if missing:
        raise SystemExit(
            f"ACS {ACS_YEAR} {table}: no variable with label(s) {missing}. "
            f"Census reworded the table — check {base}/groups/{table}.json "
            f"and update the label map."
        )
    return out


# ---------------------------------------------------------------------------
# Headline city stats from the Profile tables (one-stop) + selected detail
# ---------------------------------------------------------------------------

_INC = "Estimate!!INCOME AND BENEFITS (IN 2024 INFLATION-ADJUSTED DOLLARS)"
_POV = "Percent!!PERCENTAGE OF FAMILIES AND PEOPLE WHOSE INCOME IN THE PAST 12 MONTHS IS BELOW THE POVERTY LEVEL"
_BUILT = "Estimate!!YEAR STRUCTURE BUILT!!Total housing units"

DP_LABELS = {
    # DP05 — Demographics
    "DP05": {
        "Estimate!!SEX AND AGE!!Total population": "pop_total",
        "Estimate!!SEX AND AGE!!Total population!!Male": "pop_male",
        "Estimate!!SEX AND AGE!!Total population!!Female": "pop_female",
        "Estimate!!SEX AND AGE!!Total population!!Median age (years)": "median_age",
        "Estimate!!RACE!!Total population!!One race!!White": "white_alone",
        "Estimate!!RACE!!Total population!!One race!!Black or African American": "black_alone",
        "Estimate!!RACE!!Total population!!One race!!American Indian and Alaska Native": "amerindian_alone",
        "Estimate!!RACE!!Total population!!One race!!Asian": "asian_alone",
        "Estimate!!RACE!!Total population!!One race!!Native Hawaiian and Other Pacific Islander": "nhpi_alone",
        "Estimate!!RACE!!Total population!!One race!!Some Other Race": "other_alone",
        "Estimate!!RACE!!Total population!!Two or More Races": "two_or_more",
        "Estimate!!HISPANIC OR LATINO AND RACE!!Total population!!Hispanic or Latino (of any race)": "hispanic_any_race",
        "Estimate!!HISPANIC OR LATINO AND RACE!!Total population!!Not Hispanic or Latino!!White alone": "white_alone_nh",
    },
    # DP02 — Social
    "DP02": {
        "Estimate!!HOUSEHOLDS BY TYPE!!Total households": "households_total",
        "Estimate!!HOUSEHOLDS BY TYPE!!Total households!!Married-couple household": "married_couple_fam",
        "Estimate!!HOUSEHOLDS BY TYPE!!Total households!!Female householder, no spouse/partner present": "single_mom_family",
        "Estimate!!HOUSEHOLDS BY TYPE!!Total households!!Average household size": "avg_household_size",
        "Percent!!EDUCATIONAL ATTAINMENT!!Population 25 years and over!!Bachelor's degree or higher": "bachelors_or_higher_pct",
        "Percent!!EDUCATIONAL ATTAINMENT!!Population 25 years and over!!Graduate or professional degree": "graduate_degree_pct",
        "Estimate!!U.S. CITIZENSHIP STATUS!!Foreign-born population": "foreign_born_total",
        "Estimate!!U.S. CITIZENSHIP STATUS!!Foreign-born population!!Naturalized U.S. citizen": "foreign_born_naturalized",
        "Percent!!LANGUAGE SPOKEN AT HOME!!Population 5 years and over!!Language other than English": "lang_other_than_english_pct",
        "Percent!!LANGUAGE SPOKEN AT HOME!!Population 5 years and over!!Spanish": "spanish_pct",
    },
    # DP03 — Economic
    "DP03": {
        "Estimate!!EMPLOYMENT STATUS!!Population 16 years and over": "pop_16plus",
        "Estimate!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force": "labor_force",
        "Estimate!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force!!Civilian labor force!!Unemployed": "unemployed",
        "Percent!!EMPLOYMENT STATUS!!Civilian labor force!!Unemployment Rate": "unemployment_rate",
        f"{_INC}!!Total households!!Median household income (dollars)": "median_household_income",
        f"{_INC}!!Total households!!Mean household income (dollars)": "mean_household_income",
        f"{_INC}!!Per capita income (dollars)": "per_capita_income",
        "Percent!!HEALTH INSURANCE COVERAGE!!Civilian noninstitutionalized population!!With health insurance coverage": "with_health_insurance_pct",
        f"{_POV}!!All people": "pov_rate_all_pct",
        f"{_POV}!!All people!!Under 18 years": "pov_rate_kids_under_18_pct",
    },
    # DP04 — Housing. The year-built bins are the 2024 schema (2020+, 2010-19);
    # Census re-bins these as new decades start, so Lynn_City.py reads the same names.
    "DP04": {
        "Estimate!!HOUSING OCCUPANCY!!Total housing units": "housing_units_total",
        "Estimate!!HOUSING OCCUPANCY!!Total housing units!!Occupied housing units": "occupied_housing_units",
        "Estimate!!HOUSING OCCUPANCY!!Total housing units!!Vacant housing units": "vacant_housing_units",
        "Estimate!!HOUSING TENURE!!Occupied housing units!!Owner-occupied": "owner_occupied",
        "Estimate!!HOUSING TENURE!!Occupied housing units!!Renter-occupied": "renter_occupied",
        "Estimate!!VALUE!!Owner-occupied units!!Median (dollars)": "median_home_value",
        "Estimate!!GROSS RENT!!Occupied units paying rent!!Median (dollars)": "median_gross_rent",
        f"{_BUILT}!!Built 2020 or later": "built_2020_or_later",
        f"{_BUILT}!!Built 2010 to 2019": "built_2010_to_2019",
        f"{_BUILT}!!Built 2000 to 2009": "built_2000_to_2009",
        f"{_BUILT}!!Built 1990 to 1999": "built_1990_to_1999",
        f"{_BUILT}!!Built 1980 to 1989": "built_1980_to_1989",
        f"{_BUILT}!!Built 1970 to 1979": "built_1970_to_1979",
        f"{_BUILT}!!Built 1960 to 1969": "built_1960_to_1969",
        f"{_BUILT}!!Built 1950 to 1959": "built_1950_to_1959",
        f"{_BUILT}!!Built 1940 to 1949": "built_1940_to_1949",
        f"{_BUILT}!!Built 1939 or earlier": "built_1939_or_earlier",
    },
}


def fetch_headline() -> pd.DataFrame:
    dp_vars: dict[str, str] = {}
    for table, labels in DP_LABELS.items():
        dp_vars.update(resolve(PROFILE_BASE, table, labels))
    # Census API caps `get` at 50 variables; chunk into batches.
    all_keys = list(dp_vars.keys())
    chunks = [all_keys[i:i + 40] for i in range(0, len(all_keys), 40)]
    merged: dict = {}
    name_val = None
    for i, ch in enumerate(chunks, 1):
        rows = fetch(PROFILE_BASE, ch, f"Profile DP* (chunk {i}/{len(chunks)})")
        d = _to_dict(rows)
        if not d:
            continue
        name_val = name_val or d.get("NAME")
        merged.update({k: v for k, v in d.items() if k != "NAME"})
    if not merged:
        return pd.DataFrame()
    out = {alias: merged.get(var) for var, alias in dp_vars.items()}
    out["place_name"] = name_val
    out["acs_year"] = ACS_YEAR
    for k in list(out):
        v = out[k]
        if isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit():
            out[k] = float(v) if "." in v else int(v)
    return pd.DataFrame([out])


# ---------------------------------------------------------------------------
# Birthplaces (B05006) — top countries for foreign-born population
# ---------------------------------------------------------------------------

_FB = "Estimate!!Total"
_LA = f"{_FB}!!Americas!!Latin America"

# Rows whose name contains "total" are regional roll-ups; Lynn_City.py keeps
# them out of the country chart by that substring.
B05006_LABELS = {
    _FB: "Foreign-born total",
    f"{_FB}!!Europe": "Europe (total)",
    f"{_FB}!!Asia": "Asia (total)",
    f"{_FB}!!Africa": "Africa (total)",
    f"{_FB}!!Oceania": "Oceania (total)",
    f"{_FB}!!Americas": "Americas (total)",
    _LA: "Latin America (total)",
    f"{_LA}!!Caribbean": "  Caribbean (total)",
    f"{_LA}!!Central America": "  Central America (total)",
    f"{_LA}!!South America": "  South America (total)",
    # Caribbean specific
    f"{_LA}!!Caribbean!!Bahamas": "Bahamas",
    f"{_LA}!!Caribbean!!Barbados": "Barbados",
    f"{_LA}!!Caribbean!!Cuba": "Cuba",
    f"{_LA}!!Caribbean!!Dominican Republic": "Dominican Republic",
    f"{_LA}!!Caribbean!!Haiti": "Haiti",
    f"{_LA}!!Caribbean!!Jamaica": "Jamaica",
    # Central America specific
    f"{_LA}!!Central America!!Belize": "Belize",
    f"{_LA}!!Central America!!Costa Rica": "Costa Rica",
    f"{_LA}!!Central America!!El Salvador": "El Salvador",
    f"{_LA}!!Central America!!Guatemala": "Guatemala",
    f"{_LA}!!Central America!!Honduras": "Honduras",
    f"{_LA}!!Central America!!Mexico": "Mexico",
    f"{_LA}!!Central America!!Nicaragua": "Nicaragua",
    f"{_LA}!!Central America!!Panama": "Panama",
    # South America specific
    f"{_LA}!!South America!!Argentina": "Argentina",
    f"{_LA}!!South America!!Brazil": "Brazil",
    f"{_LA}!!South America!!Chile": "Chile",
    f"{_LA}!!South America!!Colombia": "Colombia",
    f"{_LA}!!South America!!Ecuador": "Ecuador",
    f"{_LA}!!South America!!Peru": "Peru",
    # Asia — major Lynn communities
    f"{_FB}!!Asia!!Eastern Asia!!China": "China (incl. HK + Taiwan)",
    f"{_FB}!!Asia!!South Central Asia!!India": "India",
    f"{_FB}!!Asia!!South Eastern Asia!!Cambodia": "Cambodia",
    f"{_FB}!!Asia!!South Eastern Asia!!Philippines": "Philippines",
    f"{_FB}!!Asia!!South Eastern Asia!!Vietnam": "Vietnam",
    # Africa — specific (Lynn has a notable Western Africa community)
    f"{_FB}!!Africa!!Western Africa!!Cabo Verde": "Cabo Verde",
    f"{_FB}!!Africa!!Western Africa!!Ghana": "Ghana",
    f"{_FB}!!Africa!!Western Africa!!Nigeria": "Nigeria",
    f"{_FB}!!Africa!!Eastern Africa!!Ethiopia": "Ethiopia",
    f"{_FB}!!Africa!!Eastern Africa!!Somalia": "Somalia",
}


def fetch_birthplaces() -> pd.DataFrame:
    b05006_vars = resolve(API_BASE, "B05006", B05006_LABELS)
    rows = fetch(API_BASE, sorted(b05006_vars), "B05006 — place of birth detail")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["country", "count"])
    records = []
    for var, label in b05006_vars.items():
        v = d.get(var)
        if v is None:
            continue
        try:
            cnt = int(v)
        except (TypeError, ValueError):
            continue
        if cnt > 0:
            records.append({"country": label, "count": cnt})
    df = pd.DataFrame(records)
    return df.sort_values("count", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Detailed languages (C16001 — collapsed but more detail than DP02)
# ---------------------------------------------------------------------------

# Lynn_City.py finds the total row by "Total" and English by "English".
C16001_LABELS = {
    "Estimate!!Total": "Total (pop 5+)",
    "Estimate!!Total!!Speak only English": "Speak only English",
    "Estimate!!Total!!Spanish": "Spanish",
    "Estimate!!Total!!French, Haitian, or Cajun": "French, Haitian Creole, or Cajun",
    "Estimate!!Total!!German or other West Germanic languages": "German or other West Germanic",
    "Estimate!!Total!!Russian, Polish, or other Slavic languages": "Russian, Polish, or other Slavic",
    "Estimate!!Total!!Other Indo-European languages": "Other Indo-European",
    "Estimate!!Total!!Korean": "Korean",
    "Estimate!!Total!!Chinese (incl. Mandarin, Cantonese)": "Chinese (incl. Mandarin, Cantonese)",
    "Estimate!!Total!!Vietnamese": "Vietnamese",
    "Estimate!!Total!!Tagalog (incl. Filipino)": "Tagalog (incl. Filipino)",
    "Estimate!!Total!!Other Asian and Pacific Island languages": "Other Asian or Pacific Island",
    "Estimate!!Total!!Arabic": "Arabic",
    "Estimate!!Total!!Other and unspecified languages": "Other and unspecified",
}


def fetch_languages() -> pd.DataFrame:
    c16001_vars = resolve(API_BASE, "C16001", C16001_LABELS)
    rows = fetch(API_BASE, list(c16001_vars), "C16001 — language spoken at home")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["language", "count"])
    records = []
    for var, lbl in c16001_vars.items():
        v = d.get(var)
        if v is None:
            continue
        try:
            cnt = int(v)
        except (TypeError, ValueError):
            continue
        records.append({"language": lbl, "count": cnt})
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Industries (S2403) and commute (S0801)
# ---------------------------------------------------------------------------

_EMP = "Estimate!!Total!!Civilian employed population 16 years and over"

# Top-level industry rows only; the table also nests sub-industries under
# several of these, which must not be summed alongside their parents.
S2403_LABELS = {
    f"{_EMP}!!Agriculture, forestry, fishing and hunting, and mining": "Agriculture, forestry, fishing, hunting, mining",
    f"{_EMP}!!Construction": "Construction",
    f"{_EMP}!!Manufacturing": "Manufacturing",
    f"{_EMP}!!Wholesale trade": "Wholesale trade",
    f"{_EMP}!!Retail trade": "Retail trade",
    f"{_EMP}!!Transportation and warehousing, and utilities": "Transportation, warehousing, utilities",
    f"{_EMP}!!Information": "Information",
    f"{_EMP}!!Finance and insurance, and real estate and rental and leasing": "Finance, insurance, real estate",
    f"{_EMP}!!Professional, scientific, and management, and administrative and waste management services": "Professional, scientific, mgmt, admin, waste mgmt",
    f"{_EMP}!!Educational services, and health care and social assistance": "Educational services, healthcare, social assistance",
    f"{_EMP}!!Arts, entertainment, and recreation, and accommodation and food services": "Arts, entertainment, accommodation, food services",
    f"{_EMP}!!Other services, except public administration": "Other services (except public administration)",
    f"{_EMP}!!Public administration": "Public administration",
}


def fetch_industries() -> pd.DataFrame:
    s2403_vars = resolve(SUBJECT_BASE, "S2403", S2403_LABELS)
    rows = fetch(SUBJECT_BASE, list(s2403_vars),
                  "S2403 — civilian employed by industry")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["industry", "employed"])
    recs = []
    for var, lbl in s2403_vars.items():
        v = d.get(var)
        if v is None:
            continue
        try:
            n = int(float(v))
        except (TypeError, ValueError):
            continue
        recs.append({"industry": lbl, "employed": n})
    return pd.DataFrame(recs).sort_values("employed", ascending=False).reset_index(drop=True)


_MODE = "Estimate!!Total!!Workers 16 years and over!!MEANS OF TRANSPORTATION TO WORK"

# Mutually exclusive modes (they sum to ~100%); "Car, truck, or van" itself is
# the parent of drove-alone + carpooled and is left out.
S0801_LABELS = {
    f"{_MODE}!!Car, truck, or van!!Drove alone": "Drove alone (car/truck/van)",
    f"{_MODE}!!Car, truck, or van!!Carpooled": "Carpooled",
    f"{_MODE}!!Public transportation": "Public transportation",
    f"{_MODE}!!Walked": "Walked",
    f"{_MODE}!!Bicycle": "Bicycle",
    f"{_MODE}!!Taxi or ride-hailing services, motorcycle, or other means": "Taxi, ride-hailing, motorcycle, other",
    f"{_MODE}!!Worked from home": "Worked from home",
    "Estimate!!Total!!Workers 16 years and over who did not work from home!!TRAVEL TIME TO WORK!!Mean travel time to work (minutes)": "Mean travel time to work (min)",
}


def fetch_commute() -> pd.DataFrame:
    s0801_vars = resolve(SUBJECT_BASE, "S0801", S0801_LABELS)
    rows = fetch(SUBJECT_BASE, list(s0801_vars),
                  "S0801 — commute to work")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["mode", "pct_or_min"])
    recs = []
    for var, lbl in s0801_vars.items():
        v = d.get(var)
        if v is None:
            continue
        try:
            n = float(v)
        except (TypeError, ValueError):
            continue
        recs.append({"mode": lbl, "pct_or_min": n})
    return pd.DataFrame(recs)


# ---------------------------------------------------------------------------
# Age pyramid (S0101 — population by 5-year band × sex)
# ---------------------------------------------------------------------------

S0101_BANDS = [
    ("0-4",     ("S0101_C03_002E", "S0101_C05_002E")),
    ("5-9",     ("S0101_C03_003E", "S0101_C05_003E")),
    ("10-14",   ("S0101_C03_004E", "S0101_C05_004E")),
    ("15-19",   ("S0101_C03_005E", "S0101_C05_005E")),
    ("20-24",   ("S0101_C03_006E", "S0101_C05_006E")),
    ("25-29",   ("S0101_C03_007E", "S0101_C05_007E")),
    ("30-34",   ("S0101_C03_008E", "S0101_C05_008E")),
    ("35-39",   ("S0101_C03_009E", "S0101_C05_009E")),
    ("40-44",   ("S0101_C03_010E", "S0101_C05_010E")),
    ("45-49",   ("S0101_C03_011E", "S0101_C05_011E")),
    ("50-54",   ("S0101_C03_012E", "S0101_C05_012E")),
    ("55-59",   ("S0101_C03_013E", "S0101_C05_013E")),
    ("60-64",   ("S0101_C03_014E", "S0101_C05_014E")),
    ("65-69",   ("S0101_C03_015E", "S0101_C05_015E")),
    ("70-74",   ("S0101_C03_016E", "S0101_C05_016E")),
    ("75-79",   ("S0101_C03_017E", "S0101_C05_017E")),
    ("80-84",   ("S0101_C03_018E", "S0101_C05_018E")),
    ("85+",     ("S0101_C03_019E", "S0101_C05_019E")),
]


def fetch_age_pyramid() -> pd.DataFrame:
    vars_list = []
    for _, pair in S0101_BANDS:
        vars_list.extend(pair)
    rows = fetch(SUBJECT_BASE, vars_list, "S0101 — age pyramid")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["band", "sex", "count"])
    recs = []
    for band, (male_var, female_var) in S0101_BANDS:
        for sex, var in (("Male", male_var), ("Female", female_var)):
            v = d.get(var)
            try:
                n = int(float(v)) if v is not None else None
            except ValueError:
                n = None
            if n is not None:
                recs.append({"band": band, "sex": sex, "count": n})
    return pd.DataFrame(recs)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Lynn city ACS pull (year {ACS_YEAR})")
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
        print("Without a key, this script exits gracefully and leaves existing")
        print("processed Lynn city ACS parquet files untouched.")
        print()
        return

    headline = fetch_headline()
    bp = fetch_birthplaces()
    langs = fetch_languages()
    ind = fetch_industries()
    com = fetch_commute()
    age = fetch_age_pyramid()

    headline.to_parquet(PROCESSED_DIR / "lynn_city_stats.parquet", index=False)
    bp.to_parquet(PROCESSED_DIR / "lynn_birthplaces.parquet", index=False)
    langs.to_parquet(PROCESSED_DIR / "lynn_languages.parquet", index=False)
    ind.to_parquet(PROCESSED_DIR / "lynn_industries.parquet", index=False)
    com.to_parquet(PROCESSED_DIR / "lynn_commute.parquet", index=False)
    age.to_parquet(PROCESSED_DIR / "lynn_age_pyramid.parquet", index=False)

    for name, df in [("headline", headline), ("birthplaces", bp),
                      ("languages", langs), ("industries", ind),
                      ("commute", com), ("age_pyramid", age)]:
        print(f"  Wrote lynn_{name} ({len(df):,} rows, {len(df.columns)} cols)")


if __name__ == "__main__":
    main()
