"""
Download bulk CSV reports from DESE Profiles statereport
(profiles.doe.mass.edu/statereport/).

Many DESE reports are not on the E2C Hub Socrata portal — they live on the
older profiles.doe.mass.edu site as static CSV/Excel downloads. This script
fetches the ones we need but can't get elsewhere:

  - Student Discipline Data Report (suspensions, expulsions)
  - VOCAL Survey results
  - Accountability Information (ESSA designations)
  - ACCESS for ELLs (school-level WIDA scores)
  - Counselor / Nurse / Psychologist / Social Worker ratios
  - Teacher Retention, Years of Experience, In-Field %
  - Class size by subject
  - Stability / Mobility, Homeless (McKinney-Vento), Foster care
  - Special Education Educational Environment
  - AP/IB Course Offerings list
  - Per-Pupil Expenditure (ESSA federal method)

Status: STUB. Will be filled in as we discover each report's URL by
visiting profiles.doe.mass.edu/statereport and inspecting download links.

Run with:
    python scripts/02_download_dese_profiles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import RAW_DIR  # noqa: E402

PROFILES_DIR = RAW_DIR / "dese_profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

PROFILES_BASE = "https://profiles.doe.mass.edu/statereport/"

# Each entry: (slug, statereport report URL, year (or 'all'))
# To be populated by visiting the statereport page and finding the
# "Download as CSV/Excel" link for each report.
TARGETS: list[tuple[str, str | None, str]] = [
    ("discipline_data",              None, "all"),
    ("vocal_survey",                 None, "all"),
    ("accountability",               None, "all"),
    ("access_for_ells",              None, "all"),
    ("staffing_ratios",              None, "all"),
    ("teacher_retention",            None, "all"),
    ("teacher_experience",           None, "all"),
    ("teacher_in_field",             None, "all"),
    ("class_size",                   None, "all"),
    ("stability_mobility",           None, "all"),
    ("homeless_students",            None, "all"),
    ("foster_care",                  None, "all"),
    ("special_ed_environment",       None, "all"),
    ("ap_ib_course_offerings",       None, "all"),
    ("per_pupil_essa_federal",       None, "all"),
]


def main() -> None:
    print("DESE Profiles statereport scraper — currently STUB.")
    print()
    print("To populate URLs:")
    print(f"  1. Visit {PROFILES_BASE}")
    print(f"  2. For each report in TARGETS, click through and find the download URL.")
    print(f"  3. Update the TARGETS list in this file with the URL.")
    print()
    print("Reports needed:")
    for slug, url, year in TARGETS:
        marker = "[OK]" if url else "—"
        print(f"  [{marker}] {slug}")


if __name__ == "__main__":
    main()
