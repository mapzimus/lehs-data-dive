"""
Download MassGIS shapefiles for Lynn GIS visualizations.

Pulls:
  - SCHOOLS_PT_MEMA: All MA public school site points (we'll filter to Lynn + gateway HS)
  - SCHOOLDISTRICTS_POLY: MA public school district boundaries
  - TOWNSSURVEY_POLYM: MA town/municipal boundaries (M = Mass Plane proj for accuracy)
  - TIGER 2024 census tracts for MA (from US Census Bureau)

Outputs unzipped shapefiles to data/raw/gis/

Run with:
    python scripts/09_download_massgis.py
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import RAW_DIR  # noqa: E402

GIS_DIR = RAW_DIR / "gis"
GIS_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "lehs-data-dive/0.1 (github.com/mapzimus/lehs-data-dive)"
HEADERS = {"User-Agent": USER_AGENT}

# (subfolder, URL) pairs
DOWNLOADS = [
    # MassGIS layers
    ("schools_pt",
     "https://s3.us-east-1.amazonaws.com/download.massgis.digital.mass.gov/shapefiles/state/schools.zip"),
    ("school_districts",
     "https://s3.us-east-1.amazonaws.com/download.massgis.digital.mass.gov/shapefiles/state/schooldistricts.zip"),
    ("towns",
     "https://s3.us-east-1.amazonaws.com/download.massgis.digital.mass.gov/shapefiles/state/townssurvey_shp.zip"),
    # US Census TIGER/Line 2024
    ("tracts_ma",
     "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_25_tract.zip"),
]


def download_and_extract(name: str, url: str) -> bool:
    target = GIS_DIR / name
    if target.exists() and any(target.iterdir()):
        print(f"  [SKIP] {name} already exists")
        return True
    target.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=120)
        r.raise_for_status()
    except Exception as e:
        print(f"  [X] {name}: download failed: {e}")
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            z.extractall(target)
    except zipfile.BadZipFile:
        print(f"  [X] {name}: not a valid zip (got {len(r.content)} bytes)")
        return False
    print(f"  [OK] {name}: extracted to {target}")
    return True


def main() -> None:
    print("Downloading MassGIS + Census TIGER shapefiles...")
    print(f"Target dir: {GIS_DIR}\n")
    ok = fail = 0
    for name, url in DOWNLOADS:
        print(f"-> {name}")
        if download_and_extract(name, url):
            ok += 1
        else:
            fail += 1
    print(f"\nSummary: {ok} OK, {fail} failed.")


if __name__ == "__main__":
    main()
