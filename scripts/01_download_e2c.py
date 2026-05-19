"""
Discover and download datasets from the Massachusetts Education-to-Career (E2C)
Data Hub — a Socrata-powered open data portal at educationtocareer.data.mass.gov.

This script:
  1. Searches the Socrata Discovery API by dataset name
  2. Picks the best match for each target
  3. Downloads the full CSV to data/raw/e2c_hub/
  4. Saves a manifest with dataset IDs and metadata to data/raw/e2c_hub/_manifest.json

Run with:
    python scripts/01_download_e2c.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

# allow `from utils...` when run as `python scripts/01_download_e2c.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import E2C_DOMAIN, RAW_DIR  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

E2C_RAW_DIR = RAW_DIR / "e2c_hub"
E2C_RAW_DIR.mkdir(parents=True, exist_ok=True)

CATALOG_URL = "https://api.us.socrata.com/api/catalog/v1"

# (slug used in constants.py, exact-ish title to find, optional priority hint)
TARGETS = [
    # Tier 1 — core datasets
    ("mcas_achievement",                "MCAS Achievement Results"),
    ("dart_success_after_hs",           "DART: Success After High School"),
    ("enrollment_demographics",         "Enrollment: Grade, Race/Ethnicity, Gender, and Selected Populations"),
    ("student_attendance",              "Student Attendance"),
    ("ap_performance",                  "Advanced Placement (AP) Performance"),
    ("masscore_completion",             "MassCore Completion"),
    ("staffing_race_gender",            "Staffing: Race/Ethnicity and Gender"),
    ("school_expenditures",             "School Expenditures by Spending Category"),
    ("district_expenditures",           "District Expenditures by Spending Category"),
    ("graduation_rates",                "High School Graduation Rates"),
    ("pathways_enrollment",             "Pathways/Programs Enrollment"),
    ("plans_of_graduates",              "Plans of High School Graduates"),
    ("special_ed_indicators",           "Special Education Indicators"),

    # Tier 1.5 — additional datasets
    ("early_college_credits",           "Early College Credits"),
    ("early_college_participation",     "Early College Participation"),
    ("college_career_outcomes",         "College and Career Outcomes of High School Graduates"),
    ("earnings_by_industry",            "Average Earnings of High School Graduates by Industry"),
    ("postsecondary_fall_enrollment",   "Public Postsecondary Fall Enrollment: Detail"),
    ("postsecondary_retention",         "Public Postsecondary First Year Retention: Summary"),
    ("postsecondary_awards",            "Public Postsecondary Awards (Degrees) Conferred by Institution: Detail"),
    ("postsecondary_tuition",           "Public Postsecondary Tuition and Fees"),
    ("student_progression_hs_to_postsec","Student Progression from High School through Postsecondary Education"),
]

USER_AGENT = "lehs-data-center/0.1 (https://github.com/mapzimus/lehs-data-center)"
HEADERS = {"User-Agent": USER_AGENT}

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def search_catalog(query: str, limit: int = 10) -> list[dict]:
    """Search the Socrata Discovery API for datasets matching a name."""
    params = {
        "domains": E2C_DOMAIN,
        "q": query,
        "limit": limit,
        "search_context": E2C_DOMAIN,
    }
    r = requests.get(CATALOG_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def best_match(results: list[dict], target_title: str) -> dict | None:
    """Pick the best-matching dataset from a result list.

    Strategy: prefer an exact (case-insensitive) title match; otherwise prefer
    the highest-page-view dataset of type 'dataset'. Falls back to the first
    result if nothing else fits.
    """
    if not results:
        return None
    target_lower = target_title.lower()
    # 1. exact match (preferred)
    for res in results:
        title = res["resource"]["name"]
        if title.lower() == target_lower:
            return res
    # 2. exact match ignoring punctuation
    target_clean = target_lower.replace(":", "").replace(",", "").strip()
    for res in results:
        if res["resource"]["name"].lower().replace(":", "").replace(",", "").strip() == target_clean:
            return res
    # 3. starts-with match for type dataset
    for res in results:
        if res["resource"]["type"] == "dataset" and res["resource"]["name"].lower().startswith(target_lower[:30]):
            return res
    # 4. first dataset-type result
    for res in results:
        if res["resource"]["type"] == "dataset":
            return res
    return results[0]


def download_csv(dataset_id: str, out_path: Path) -> int:
    """Download the full CSV for a Socrata dataset. Returns bytes written."""
    url = f"https://{E2C_DOMAIN}/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"
    with requests.get(url, headers=HEADERS, stream=True, timeout=300) as r:
        r.raise_for_status()
        bytes_written = 0
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bytes_written += len(chunk)
    return bytes_written


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    manifest: dict[str, dict] = {}
    failures: list[tuple[str, str]] = []

    for slug, title in TARGETS:
        print(f"\n-> {slug}: searching for '{title}'")
        try:
            results = search_catalog(title)
            match = best_match(results, title)
            if not match:
                print(f"  [X] no match found")
                failures.append((slug, "no match"))
                continue

            res = match["resource"]
            dataset_id = res["id"]
            matched_name = res["name"]
            print(f"  [OK] matched: {matched_name}  ({dataset_id})")

            out_csv = E2C_RAW_DIR / f"{slug}.csv"
            size = download_csv(dataset_id, out_csv)
            print(f"  [OK] downloaded: {size / 1024:.1f} KB -> {out_csv.name}")

            manifest[slug] = {
                "dataset_id": dataset_id,
                "matched_name": matched_name,
                "target_name": title,
                "url": f"https://{E2C_DOMAIN}/d/{dataset_id}",
                "csv_path": str(out_csv.relative_to(out_csv.parent.parent.parent)),
                "size_bytes": size,
            }

            time.sleep(0.5)  # be polite to Socrata
        except Exception as e:
            print(f"  [X] error: {e}")
            failures.append((slug, str(e)))

    manifest_path = E2C_RAW_DIR / "_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote manifest: {manifest_path}")

    print(f"\nSummary: {len(manifest)} datasets downloaded, {len(failures)} failed.")
    if failures:
        print("Failures:")
        for slug, reason in failures:
            print(f"  - {slug}: {reason}")


if __name__ == "__main__":
    main()
