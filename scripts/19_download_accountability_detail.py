"""
Download DESE's detailed accountability data files.

The thin top-line accountability file (classification / percentile / progress)
is fetched by scripts/02_download_dese_profiles.py. This script grabs the
RICHER bulk workbooks DESE publishes on its accountability lists-and-tools
page — the ones that carry the per-indicator, per-student-group detail behind
each school's classification:

  * accountability-data-{year}.xlsx
      Table 2 = one row per school with the full classification context
      (federal designation, low-performing groups, criterion-referenced %s).

  * criterion-referenced-percentage-{year}.xlsx
      The machine-readable twin of the "Detailed data for each indicator" tab:
      every indicator (achievement / growth / graduation / dropout / ELP
      progress / chronic absenteeism / advanced coursework) x every student
      group, with prior + current value, change, target, N, points, and reason.

All of this is school-level AGGREGATE data — no student records — so it is safe
to land in the processed parquet layer.

Only the current determination year is published at these stable URLs; DESE
archives prior years under different paths. We therefore attempt a small window
of years and skip any that 404, so next year's release is picked up with no
code change. Run scripts/16_process_dese_profiles.py afterward to build the
parquets.
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import RAW_DIR  # noqa: E402

BASE = "https://www.doe.mass.edu/accountability/lists-tools"
OUT_DIR = RAW_DIR / "accountability"
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "lehs-data-dive/0.1 (https://github.com/mapzimus/lehs-data-dive)"
HEADERS = {"User-Agent": USER_AGENT}

# File stems to pull for each year. Add stems here (e.g. the percentile research
# files) if a future page needs them.
STEMS = [
    "accountability-data",
    "criterion-referenced-percentage",
]

# Determination years to attempt, newest first. A 404 just means that year is
# archived elsewhere (or not yet published) — we skip it quietly.
YEARS = [2026, 2025, 2024, 2023]


def download(stem: str, year: int) -> bool:
    """Fetch one {stem}-{year}.xlsx. Returns True on success, False on 404/skip."""
    name = f"{stem}-{year}.xlsx"
    url = f"{BASE}/{name}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
    except requests.RequestException as exc:
        print(f"  [WARN] {name}: {exc}")
        return False
    # Archived / not-yet-published years return 404 or 403 (Forbidden) at these
    # stable URLs — both just mean "skip this year". Only a 5xx is a real error.
    if 400 <= r.status_code < 500:
        return False
    r.raise_for_status()
    out = OUT_DIR / name
    out.write_bytes(r.content)
    print(f"  [OK] {name}  ({len(r.content):,} bytes) -> {out}")
    return True


def main() -> None:
    print("Downloading DESE detailed accountability workbooks...")
    print(f"  output dir: {OUT_DIR}")
    print()
    any_ok = False
    for year in YEARS:
        for stem in STEMS:
            if download(stem, year):
                any_ok = True
    print()
    if not any_ok:
        print("No files downloaded — check connectivity or whether DESE moved "
              "the lists-tools URLs.")
        sys.exit(1)
    print("Done. Next: python scripts/16_process_dese_profiles.py")


if __name__ == "__main__":
    main()
