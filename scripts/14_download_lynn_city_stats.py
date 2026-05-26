"""
Download US Census ACS 5-year data at the **place** (city) level for Lynn, MA.

This is the city-wide pull that backs `pages/18_Lynn_Overview.py`. The
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
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR, RAW_DIR  # noqa: E402

ACS_YEAR = 2023
ACS_STATE = "25"
ACS_PLACE = "37490"  # Lynn city, MA (verified via Census API place lookup)

OUT_RAW = RAW_DIR / "gis" / "census_acs_place"
OUT_RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "lehs-data-dive/0.2 (github.com/mapzimus/lehs-data-dive)"}
TIMEOUT = 60
API_KEY = os.environ.get("CENSUS_API_KEY", "").strip() or "d15d12991cd2df124d8c3c00f1ffab7effd3389b"
API_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
PROFILE_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5/profile"
SUBJECT_BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5/subject"


def fetch(base: str, variables: list[str], desc: str) -> list[list]:
    var_str = ",".join(["NAME"] + variables)
    params = {
        "get": var_str,
        "for": f"place:{ACS_PLACE}",
        "in": f"state:{ACS_STATE}",
        "key": API_KEY,
    }
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
# Headline city stats from the Profile tables (one-stop) + selected detail
# ---------------------------------------------------------------------------

DP_VARS = {
    # DP05 — Demographics
    # NOTE: race/ethnicity codes are the 2023 ACS DP05 schema. The table was
    # restructured between 2019 and 2023 (more detailed tribal/ancestry rows
    # inserted), so most race codes shifted. White/Black/AIAN-alone kept their
    # 2019 numbers, everything else moved. Verify against
    # https://api.census.gov/data/2023/acs/acs5/profile/variables.json before
    # bumping to a future ACS vintage.
    "DP05_0001E": "pop_total",
    "DP05_0002E": "pop_male",
    "DP05_0003E": "pop_female",
    "DP05_0018E": "median_age",
    "DP05_0037E": "white_alone",
    "DP05_0038E": "black_alone",
    "DP05_0039E": "amerindian_alone",
    "DP05_0047E": "asian_alone",
    "DP05_0055E": "nhpi_alone",
    "DP05_0035E": "two_or_more",
    "DP05_0076E": "hispanic_any_race",
    "DP05_0082E": "white_alone_nh",
    # DP02 — Social
    "DP02_0001E": "households_total",
    "DP02_0006E": "married_couple_fam",
    "DP02_0010E": "single_mom_family",
    "DP02_0016E": "avg_household_size",
    "DP02_0066E": "bachelors_or_higher_pct",
    "DP02_0068E": "graduate_degree_pct",
    "DP02_0095E": "foreign_born_total",
    "DP02_0096E": "foreign_born_naturalized",
    "DP02_0114E": "lang_other_than_english_pct",  # % age 5+ speaking lang other than english
    "DP02_0116E": "spanish_pct",
    # DP03 — Economic
    "DP03_0001E": "pop_16plus",
    "DP03_0002E": "labor_force",
    "DP03_0005E": "unemployed",
    "DP03_0009PE": "unemployment_rate",   # percent
    "DP03_0062E": "median_household_income",
    "DP03_0063E": "mean_household_income",
    "DP03_0086E": "per_capita_income",
    "DP03_0096PE": "with_health_insurance_pct",
    "DP03_0119PE": "pov_rate_all_pct",
    "DP03_0128PE": "pov_rate_kids_under_18_pct",
    # DP04 — Housing
    "DP04_0001E": "housing_units_total",
    "DP04_0002E": "occupied_housing_units",
    "DP04_0003E": "vacant_housing_units",
    "DP04_0046E": "owner_occupied",
    "DP04_0047E": "renter_occupied",
    "DP04_0089E": "median_home_value",
    "DP04_0134E": "median_gross_rent",
    "DP04_0017E": "built_2014_or_later",
    "DP04_0018E": "built_2010_to_2013",
    "DP04_0019E": "built_2000_to_2009",
    "DP04_0020E": "built_1990_to_1999",
    "DP04_0021E": "built_1980_to_1989",
    "DP04_0022E": "built_1970_to_1979",
    "DP04_0023E": "built_1960_to_1969",
    "DP04_0024E": "built_1950_to_1959",
    "DP04_0025E": "built_1940_to_1949",
    "DP04_0026E": "built_1939_or_earlier",
}


def fetch_headline() -> pd.DataFrame:
    # Census API caps `get` at 50 variables; chunk into batches.
    all_keys = list(DP_VARS.keys())
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
    out = {alias: merged.get(var) for var, alias in DP_VARS.items()}
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

# B05006 — Place of birth for foreign-born population (verified against the
# 2023 ACS variables.json endpoint). Numbering shifts between vintages so
# don't copy-paste from older docs.
B05006_VARS = {
    "B05006_001E": "Foreign-born total",
    # Regional rolls (parent categories — useful for headline split)
    "B05006_002E": "Europe (total)",
    "B05006_047E": "Asia (total)",
    "B05006_095E": "Africa (total)",
    "B05006_130E": "Oceania (total)",
    "B05006_133E": "Americas (total)",
    "B05006_139E": "Latin America (total)",
    "B05006_140E": "  Caribbean (total)",
    "B05006_154E": "  Central America (total)",
    "B05006_164E": "  South America (total)",
    # Caribbean specific
    "B05006_141E": "Bahamas",
    "B05006_142E": "Barbados",
    "B05006_143E": "Cuba",
    "B05006_145E": "Dominican Republic",
    "B05006_147E": "Haiti",
    "B05006_148E": "Jamaica",
    # Central America specific
    "B05006_155E": "Belize",
    "B05006_156E": "Costa Rica",
    "B05006_157E": "El Salvador",
    "B05006_158E": "Guatemala",
    "B05006_159E": "Honduras",
    "B05006_160E": "Mexico",
    "B05006_161E": "Nicaragua",
    "B05006_162E": "Panama",
    # South America specific
    "B05006_165E": "Argentina",
    "B05006_167E": "Brazil",
    "B05006_168E": "Chile",
    "B05006_169E": "Colombia",
    "B05006_170E": "Ecuador",
    "B05006_172E": "Peru",
    # Asia — major Lynn communities
    "B05006_049E": "China (incl. HK + Taiwan)",
    "B05006_060E": "India",
    "B05006_070E": "Cambodia",
    "B05006_074E": "Philippines",
    "B05006_077E": "Vietnam",
    # Africa — specific (Lynn has a notable Western Africa community)
    "B05006_120E": "Cabo Verde",
    "B05006_121E": "Ghana",
    "B05006_124E": "Nigeria",
    "B05006_098E": "Ethiopia",
    "B05006_100E": "Somalia",
}


def fetch_birthplaces() -> pd.DataFrame:
    vars_list = sorted(set(B05006_VARS.keys()))
    rows = fetch(API_BASE, vars_list, "B05006 — place of birth detail")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["country", "count"])
    records = []
    for var, label in B05006_VARS.items():
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

C16001_LABELS = {
    "C16001_001E": "Total (pop 5+)",
    "C16001_002E": "Speak only English",
    "C16001_003E": "Spanish",
    "C16001_006E": "French (incl. Cajun)",
    "C16001_009E": "Haitian",
    "C16001_012E": "German",
    "C16001_015E": "Russian, Polish, or other Slavic",
    "C16001_018E": "Other Indo-European",
    "C16001_021E": "Korean",
    "C16001_024E": "Chinese (incl. Mandarin, Cantonese)",
    "C16001_027E": "Vietnamese",
    "C16001_030E": "Tagalog (incl. Filipino)",
    "C16001_033E": "Other Asian or Pacific Island",
    "C16001_036E": "Arabic",
    # C16001_039 doesn't exist in 2023 ACS; "Other and unspecified" is implicit
}


def fetch_languages() -> pd.DataFrame:
    rows = fetch(API_BASE, list(C16001_LABELS.keys()), "C16001 — language spoken at home")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["language", "count"])
    records = []
    for var, lbl in C16001_LABELS.items():
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

S2403_LABELS = {
    "S2403_C01_002E": "Agriculture, forestry, fishing, hunting, mining",
    "S2403_C01_003E": "Construction",
    "S2403_C01_004E": "Manufacturing",
    "S2403_C01_005E": "Wholesale trade",
    "S2403_C01_006E": "Retail trade",
    "S2403_C01_007E": "Transportation, warehousing, utilities",
    "S2403_C01_008E": "Information",
    "S2403_C01_009E": "Finance, insurance, real estate",
    "S2403_C01_010E": "Professional, scientific, mgmt, admin, waste mgmt",
    "S2403_C01_011E": "Educational services, healthcare, social assistance",
    "S2403_C01_012E": "Arts, entertainment, accommodation, food services",
    "S2403_C01_013E": "Other services (except public administration)",
    "S2403_C01_014E": "Public administration",
}


def fetch_industries() -> pd.DataFrame:
    rows = fetch(SUBJECT_BASE, list(S2403_LABELS.keys()),
                  "S2403 — civilian employed by industry")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["industry", "employed"])
    recs = []
    for var, lbl in S2403_LABELS.items():
        v = d.get(var)
        if v is None:
            continue
        try:
            n = int(float(v))
        except (TypeError, ValueError):
            continue
        recs.append({"industry": lbl, "employed": n})
    return pd.DataFrame(recs).sort_values("employed", ascending=False).reset_index(drop=True)


S0801_LABELS = {
    "S0801_C01_002E": "Drove alone (car/truck/van)",
    "S0801_C01_003E": "Carpooled",
    "S0801_C01_009E": "Public transportation",
    "S0801_C01_010E": "Walked",
    "S0801_C01_011E": "Bicycle / other means",
    "S0801_C01_013E": "Worked from home",
    "S0801_C01_046E": "Mean travel time to work (min)",
}


def fetch_commute() -> pd.DataFrame:
    rows = fetch(SUBJECT_BASE, list(S0801_LABELS.keys()),
                  "S0801 — commute to work")
    d = _to_dict(rows)
    if not d:
        return pd.DataFrame(columns=["mode", "pct_or_min"])
    recs = []
    for var, lbl in S0801_LABELS.items():
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
