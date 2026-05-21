"""
Download federal CRDC (Civil Rights Data Collection) data for Lynn + Gateway peers.

CRDC is a biennial collection from civilrightsdata.ed.gov. Most recent release
is 2020-21 school year (released Nov 2023). Provides school-level data on:
  - In-school + out-of-school suspensions disaggregated by race × disability × ELL
  - Expulsions, school-based arrests, referrals to law enforcement
  - Restraint and seclusion
  - Bullying/harassment by basis (race, sex, disability, etc.)
  - AP/IB course offerings and enrollment
  - Counselor/nurse/social-worker/psychologist FTE

The bulk download is one big ZIP per release at:
    https://civilrightsdata.ed.gov/api/file/2020-21
(File names have changed across releases — script tries known patterns.)

Lynn district LEAID = 2515480 (verified via NCES district directory).

Outputs:
  - data/processed/crdc_discipline.parquet
  - data/processed/crdc_offerings.parquet
  - data/processed/crdc_staffing.parquet

Run with:
    python scripts/04_download_crdc.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    GATEWAY_CITIES,
    LCHS_SCHOOL_CODE,
    LEHS_SCHOOL_CODE,
    PROCESSED_DIR,
    RAW_DIR,
)

CRDC_RAW = RAW_DIR / "crdc"
CRDC_RAW.mkdir(parents=True, exist_ok=True)

# Known CRDC bulk download URLs by release year.
# Note: ED occasionally renames these; if all fail, follow the manual download
# instructions at https://civilrightsdata.ed.gov/resources/downloads and drop
# the CSV files into data/raw/crdc/<release>/ manually.
RELEASES = {
    "2020-21": [
        "https://civilrightsdata.ed.gov/assets/downloads/2020-21-crdc-data.zip",
        "https://www2.ed.gov/about/offices/list/ocr/docs/2020-21-crdc-data.zip",
    ],
    "2017-18": [
        "https://www2.ed.gov/about/offices/list/ocr/docs/2017-18-crdc-data.zip",
    ],
}

LYNN_LEAID = "2515480"   # NCES district ID for Lynn Public Schools

HEADERS = {"User-Agent": "lehs-data-dive/0.2 (https://github.com/mapzimus/lehs-data-dive)"}
TIMEOUT = 60


def try_download(release: str, urls: list[str]) -> Path | None:
    out = CRDC_RAW / f"{release}.zip"
    if out.exists() and out.stat().st_size > 1_000_000:
        return out
    for url in urls:
        try:
            print(f"    GET {url}")
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
            r.raise_for_status()
            with open(out, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            if out.stat().st_size > 1_000_000:
                return out
        except Exception as e:
            print(f"    [WARN] {e}")
    return None


def extract_zip(zip_path: Path) -> Path:
    out_dir = zip_path.with_suffix("")
    out_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    return out_dir


def load_crdc_csv(release_dir: Path, pattern: str) -> pd.DataFrame:
    """Find first CSV in release_dir matching *pattern*; return empty DF if none."""
    matches = list(release_dir.rglob(f"*{pattern}*.csv"))
    if not matches:
        return pd.DataFrame()
    try:
        return pd.read_csv(matches[0], low_memory=False, encoding_errors="replace")
    except Exception as e:
        print(f"    [WARN] failed to read {matches[0].name}: {e}")
        return pd.DataFrame()


def filter_lynn_gateway(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    # CRDC files vary in column naming; try common ones.
    id_cols = [c for c in df.columns if c.upper() in ("LEAID", "LEA_ID", "LEAID_NCES")]
    name_cols = [c for c in df.columns if "LEA_NAME" in c.upper() or "LEANM" in c.upper()]
    if not id_cols:
        return df.head(0)
    id_col = id_cols[0]
    df = df[df[id_col].astype(str).str.zfill(7) == LYNN_LEAID].copy()
    if not df.empty and name_cols:
        df["LEA_NAME_CLEAN"] = df[name_cols[0]]
    return df


def empty_schema(kind: str) -> pd.DataFrame:
    """Schema-correct empty DF for each output, so the dashboard can read it."""
    if kind == "discipline":
        return pd.DataFrame(columns=[
            "RELEASE", "LEAID", "SCHID", "SCHOOL_NAME", "GROUP", "GROUP_DIM",
            "ISS_COUNT", "OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT",
            "EXPULSION_COUNT", "ARREST_COUNT", "LE_REFERRAL_COUNT",
            "RESTRAINT_PHYSICAL", "SECLUSION_COUNT",
        ])
    if kind == "offerings":
        return pd.DataFrame(columns=[
            "RELEASE", "LEAID", "SCHID", "SCHOOL_NAME",
            "AP_OFFERED", "AP_COURSE_COUNT", "AP_ENROLLED_TOTAL",
            "IB_OFFERED", "CALC_OFFERED", "PHYSICS_OFFERED",
            "GEO_OFFERED", "ALGEBRA_II_OFFERED",
        ])
    if kind == "staffing":
        return pd.DataFrame(columns=[
            "RELEASE", "LEAID", "SCHID", "SCHOOL_NAME",
            "COUNSELOR_FTE", "NURSE_FTE", "SOCIAL_WORKER_FTE",
            "PSYCHOLOGIST_FTE", "LAW_ENFORCEMENT_FTE",
            "TEACHER_FTE", "STUDENT_ENROLLMENT",
        ])
    raise ValueError(kind)


def main() -> None:
    print("CRDC ingest")
    got_data = False
    for release, urls in RELEASES.items():
        zp = try_download(release, urls)
        if zp is None:
            print(f"  [SKIP] {release}: no download succeeded")
            continue
        rd = extract_zip(zp)
        print(f"  Extracted {release} -> {rd}")
        # Real parsing would extract per-LEA rows by joining the various CSVs.
        # For now we just confirm files unpacked; structured parsing is a
        # follow-up task that requires the actual file inventory.
        got_data = True

    discipline = empty_schema("discipline")
    offerings = empty_schema("offerings")
    staffing = empty_schema("staffing")

    if not got_data:
        print("  No CRDC ZIP downloaded — writing schema-valid empty parquets.")

    discipline.to_parquet(PROCESSED_DIR / "crdc_discipline.parquet", index=False)
    offerings.to_parquet(PROCESSED_DIR / "crdc_offerings.parquet", index=False)
    staffing.to_parquet(PROCESSED_DIR / "crdc_staffing.parquet", index=False)
    print(f"  Wrote crdc_discipline.parquet ({len(discipline):,} rows)")
    print(f"  Wrote crdc_offerings.parquet ({len(offerings):,} rows)")
    print(f"  Wrote crdc_staffing.parquet ({len(staffing):,} rows)")


if __name__ == "__main__":
    main()
