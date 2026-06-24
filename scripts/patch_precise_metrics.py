"""
Patch the two precision-degraded metrics into the live ``ma_academic_districts.geojson``
(all three tracked copies) WITHOUT a full pipeline rebuild.

Why a standalone patch (not a ``11_build_lynn_geo.py`` rerun): the raw inputs the full
build reads (E2C CSVs, MassGIS shapefiles, Census, community health) are gitignored and
not on disk, and the existing geojson is correct on every metric *except* these two. This
script recomputes only

    staff_white_pct, staff_hispanic_pct, staff_black_pct      (DESE fz9c-2g33, headcount-weighted)
    ap_pct_3plus, ap_pct_3plus__2007..__2025, ap_pct_3plus__{group}   (DESE 787a-3wen, precise)

at full precision via the SODA JSON API (``utils.precise_sources``) and overwrites just
those properties — geometry and every other metric stay byte-identical. Where the precise
source has no value for a district/year, the cell is set to ``null`` so no stale rounded
value lingers.

Both fixes share the exact root cause + fetchers used by ``11_build_lynn_geo.py``; this
script just applies them to the already-built geojson instead of rebuilding from raw.

Writes, preserving each file's native serialization:
  - data/processed/ma_academic_districts.geojson              (GDAL/GeoJSON driver style — via geopandas)
  - maps/data/ma_academic_districts.geojson                   (mirror — via geopandas)
  - ../ma-education-atlas/data/ma_academic_districts.geojson  (compact, 5-dec coords — via json)

Run:  python scripts/patch_precise_metrics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR, PROJECT_ROOT  # noqa: E402
from utils.precise_sources import fetch_precise_ap, fetch_precise_staff_race  # noqa: E402

LEHS = PROCESSED_DIR / "ma_academic_districts.geojson"
MAPS = PROJECT_ROOT / "maps" / "data" / "ma_academic_districts.geojson"
ATLAS = PROJECT_ROOT.parent / "ma-education-atlas" / "data" / "ma_academic_districts.geojson"

STAFF_COLS = ("staff_white_pct", "staff_hispanic_pct", "staff_black_pct")
# Columns whose before/after we headline in the console report.
HEADLINE = ("staff_white_pct", "ap_pct_3plus")


def build_lookup() -> tuple[dict[str, dict], list[str]]:
    """Return ({DIST_CODE: {col: value_or_None}}, all_precise_cols)."""
    ap = fetch_precise_ap()
    staff = fetch_precise_staff_race()
    if ap.empty and staff.empty:
        raise SystemExit("[X] both precise SODA fetches returned nothing — check network; aborting")
    if ap.empty:
        print("  [!] AP precise fetch empty — patching staff only")
        precise = staff
    elif staff.empty:
        print("  [!] staff precise fetch empty — patching AP only")
        precise = ap
    else:
        precise = ap.merge(staff, on="DIST_CODE", how="outer")

    cols = [c for c in precise.columns if c != "DIST_CODE"]
    lookup: dict[str, dict] = {}
    for rec in precise.to_dict("records"):
        dc = str(rec["DIST_CODE"]).zfill(8)
        lookup[dc] = {c: (None if pd.isna(rec[c]) else round(float(rec[c]), 4)) for c in cols}
    print(f"  precise sources: {len(lookup)} districts, {len(cols)} columns "
          f"(AP {sum(c.startswith('ap_pct_3plus') for c in cols)}, staff {sum(c in STAFF_COLS for c in cols)})")
    return lookup, cols


def target_columns(path: Path) -> list[str]:
    """Metric columns actually present in this geojson (union over all features)."""
    fc = json.loads(path.read_text(encoding="utf-8"))
    keys: set[str] = set()
    for f in fc["features"]:
        keys.update(f["properties"].keys())
    return sorted(c for c in keys
                  if c in STAFF_COLS or c == "ap_pct_3plus" or c.startswith("ap_pct_3plus__"))


def _distinct(path: Path, cols: list[str]) -> dict[str, tuple[int, int]]:
    fc = json.loads(path.read_text(encoding="utf-8"))
    feats = fc["features"]
    out: dict[str, tuple[int, int]] = {}
    for c in cols:
        nn = [f["properties"].get(c) for f in feats]
        nn = [v for v in nn if v is not None]
        out[c] = (len(set(nn)), len(nn))
    return out


def _report(path: Path, cols: list[str], before: dict, after: dict) -> None:
    print(f"  {path}")
    for c in HEADLINE:
        if c in before:
            bd, bn = before[c]
            ad, an = after[c]
            print(f"     {c:<20} distinct {bd:>3} -> {ad:>3}   (non-null {bn} -> {an})")
    yk = sorted(c for c in cols if c.startswith("ap_pct_3plus__") and c.split("__")[1].isdigit())
    if yk:
        bd = [before[c][0] for c in yk]
        ad = [after[c][0] for c in yk]
        print(f"     ap_pct_3plus__YYYY   distinct/yr min-max {min(bd)}-{max(bd)} -> {min(ad)}-{max(ad)}  ({len(yk)} cols)")


def patch_via_geopandas(path: Path, lookup: dict[str, dict]) -> None:
    """Processed/maps copies: assign columns, re-emit with the GeoJSON driver
    (reproduces the build's exact formatting — only changed values differ)."""
    cols = target_columns(path)
    before = _distinct(path, cols)
    gdf = gpd.read_file(path)
    key = gdf["DIST_CODE"].astype(str).str.zfill(8)
    for col in cols:
        mapped = key.map({dc: vals.get(col) for dc, vals in lookup.items()})
        gdf[col] = pd.to_numeric(mapped, errors="coerce")
    gdf.to_file(path, driver="GeoJSON")
    _report(path, cols, before, _distinct(path, cols))


def patch_via_json(path: Path, lookup: dict[str, dict]) -> None:
    """Atlas copy: surgical property edit, re-emit compact (5-dec coords untouched)."""
    cols = target_columns(path)
    before = _distinct(path, cols)
    fc = json.loads(path.read_text(encoding="utf-8"))
    for f in fc["features"]:
        dc = str(f["properties"].get("DIST_CODE", "")).zfill(8)
        vals = lookup.get(dc, {})
        for col in cols:
            f["properties"][col] = vals.get(col)  # value or None (absent -> null)
    path.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    _report(path, cols, before, _distinct(path, cols))


def _spot(path: Path) -> None:
    fc = json.loads(path.read_text(encoding="utf-8"))
    for f in fc["features"]:
        pr = f["properties"]
        if pr.get("DIST_CODE") in ("00350000", "01630000"):
            print(f"     {pr.get('DIST_CODE')} {pr.get('DIST_NAME'):<10} "
                  f"staff_white_pct={pr.get('staff_white_pct')}  "
                  f"ap_pct_3plus={pr.get('ap_pct_3plus')}  "
                  f"staff_hispanic_pct={pr.get('staff_hispanic_pct')}  "
                  f"staff_black_pct={pr.get('staff_black_pct')}")


def main() -> int:
    print("Fetching precise metrics from DESE SODA…")
    lookup, _cols = build_lookup()

    print("\nPatching geojson copies:")
    for path in (LEHS, MAPS):
        if path.exists():
            patch_via_geopandas(path, lookup)
        else:
            print(f"  [skip] {path} (not found)")
    if ATLAS.exists():
        patch_via_json(ATLAS, lookup)
    else:
        print(f"  [skip] {ATLAS} (not found)")

    print("\nSpot check (Boston 00350000, Lynn 01630000):")
    _spot(LEHS)
    print("\n[OK] patch complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
