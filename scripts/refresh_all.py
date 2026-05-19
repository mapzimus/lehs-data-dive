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
    ("01_download_e2c.py",           "Download E2C Hub Socrata datasets"),
    # ("02_download_dese_profiles.py", "Scrape DESE Profiles statereport bulk CSVs"),
    # ("03_download_crdc.py",          "Download federal CRDC data"),
    # ("04_download_census.py",        "Download Census ACS / SAIPE"),
    # ("05_download_ipeds.py",         "Download IPEDS postsecondary data"),
    # ("06_extract_local_files.py",    "Parse reporting-element4.xlsx + state.docx"),
    # ("07_identify_peer_schools.py",  "Resolve sibling + gateway school codes"),
    # ("08_build_master_panel.py",     "Join everything --> master Parquet"),
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
