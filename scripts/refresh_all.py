"""
Orchestrator: refresh every data source in sequence.

Run annually (or whenever DESE releases updates) to rebuild the entire data
pipeline from scratch:

    python scripts/refresh_all.py

Individual steps can also be run on their own (see scripts/01_..., 02_..., etc.).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

STEPS = [
    ("01_download_e2c.py",                 "Download E2C Hub Socrata datasets"),
    ("03_download_dese_statereport.py",    "Scrape DESE statereport (disaggregated discipline)"),
    ("04_download_crdc.py",                "Download federal CRDC bulk data"),
    ("05_download_ipeds.py",               "Download IPEDS / College Scorecard destinations"),
    ("06_extract_local_files.py",          "Parse reporting-element4.xlsx + state.docx"),
    ("07_identify_peer_schools.py",        "Resolve sibling + gateway school codes"),
    ("08_build_master_panel.py",           "Join everything --> master Parquet"),
    ("09_download_massgis.py",             "Download MassGIS shapefiles"),
    ("10_download_census_acs.py",          "Download Census ACS tract data"),
    # 12 (community health) must run BEFORE 11 (build geo), because 11 joins
    # EJScreen + CDC PLACES onto lynn_tracts.geojson. With the old order, each
    # refresh's community-health updates lagged by one cycle.
    ("12_download_community_health.py",    "Download EJScreen + CDC PLACES"),
    ("11_build_lynn_geo.py",               "Build processed GeoJSON layers"),
    ("14_download_lynn_city_stats.py",     "Download Lynn city-level ACS data"),
    # Best-effort statewide MA youth mental-health (YRBS). Degrades to no-op
    # if the CDC source is unreachable — the Wellbeing page falls back to proxies.
    ("21_download_myrbs.py",               "Download MA youth mental-health (YRBS, statewide)"),
    ("19_download_accountability_detail.py", "Download DESE detailed accountability workbooks"),
    ("16_process_dese_profiles.py",        "Build accountability summary + indicator parquets"),
    ("13_build_annual_report.py",          "Build the State of LEHS PDF report"),
]


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    python = sys.executable
    for filename, desc in STEPS:
        print(f"\n{'=' * 70}")
        print(f"STEP: {desc}")
        print(f"  --> {filename}")
        print("=" * 70)
        result = subprocess.run([python, str(script_dir / filename)], check=False)
        if result.returncode != 0:
            print(f"\n[X] Step failed: {filename} (exit code {result.returncode})")
            print("  Refresh halted. Fix the error above and re-run.")
            sys.exit(result.returncode)
    print("\n[OK] All refresh steps completed successfully.")


if __name__ == "__main__":
    main()
