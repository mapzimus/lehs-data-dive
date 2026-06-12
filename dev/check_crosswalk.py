"""Assert the tract→neighborhood crosswalk fully covers lynn_tracts.geojson."""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

gj = json.loads((ROOT / "data" / "processed" / "lynn_tracts.geojson").read_text(encoding="utf-8"))
geo_ids = {str(f["properties"]["GEOID"]) for f in gj["features"]}

xwalk = pd.read_csv(ROOT / "assets" / "curated" / "lynn_tract_neighborhoods.csv", dtype=str)
csv_ids = set(xwalk["GEOID"])

missing = geo_ids - csv_ids
extra = csv_ids - geo_ids
empty = xwalk[xwalk["neighborhood"].isna() | (xwalk["neighborhood"].str.strip() == "")]

print(f"geojson tracts: {len(geo_ids)} | crosswalk rows: {len(csv_ids)}")
print(xwalk.groupby("neighborhood")["GEOID"].count().sort_values(ascending=False).to_string())

ok = True
if missing:
    ok = False
    print("MISSING from crosswalk:", sorted(missing))
if extra:
    ok = False
    print("EXTRA in crosswalk (not in geojson):", sorted(extra))
if not empty.empty:
    ok = False
    print("EMPTY neighborhood rows:", empty["GEOID"].tolist())

sys.exit(0 if ok else 1)
