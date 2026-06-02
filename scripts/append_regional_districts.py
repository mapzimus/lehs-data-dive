"""
Splice the six regional-district features built by add_regional_districts.py into
the live ``ma_academic_districts.geojson`` in BOTH repos:

  - lehs-data-dive/data/processed/   (build artifact; line-per-feature OGR style)
  - ma-education-atlas/data/         (deployed; 5-decimal rounded, compact, per
                                      the atlas's scripts/round_coords.py)

Idempotent: if a DIST_CODE is already present it is skipped, so re-running never
double-adds. Run AFTER add_regional_districts.py.

Run:  python scripts/add_regional_districts.py && python scripts/append_regional_districts.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ADDITIONS = REPO / "data" / "processed" / "_regional_additions.json"

LEHS = REPO / "data" / "processed" / "ma_academic_districts.geojson"
ATLAS = REPO.parent / "ma-education-atlas" / "data" / "ma_academic_districts.geojson"

NDIGITS = 5  # matches ma-education-atlas/scripts/round_coords.py


def round_coords(node):
    if isinstance(node, list):
        if node and all(isinstance(x, (int, float)) for x in node):
            return [round(x, NDIGITS) for x in node]
        return [round_coords(x) for x in node]
    return node


def existing_codes(fc: dict) -> set[str]:
    return {f["properties"].get("DIST_CODE") for f in fc["features"]}


def splice_atlas(features: list[dict]) -> int:
    """Append (5-decimal rounded) + re-emit compact, exactly as round_coords.py."""
    fc = json.loads(ATLAS.read_text(encoding="utf-8"))
    have = existing_codes(fc)
    added = 0
    for f in features:
        if f["properties"]["DIST_CODE"] in have:
            continue
        f = json.loads(json.dumps(f))  # deep copy
        f["geometry"]["coordinates"] = round_coords(f["geometry"]["coordinates"])
        fc["features"].append(f)
        added += 1
    ATLAS.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    return added


def splice_lehs(features: list[dict]) -> int:
    """Append in the line-per-feature style the GeoJSON driver emits, preserving
    the existing 274 feature lines byte-for-byte (minimal diff)."""
    text = LEHS.read_text(encoding="utf-8")
    fc = json.loads(text)
    have = existing_codes(fc)
    new = [f for f in features if f["properties"]["DIST_CODE"] not in have]
    if not new:
        return 0
    # The file ends with: "<last feature>\n]\n}\n" (with optional trailing ws).
    # Find the final feature's terminating "\n]" and insert ",\n<feat>,…" before it.
    marker = "\n]"
    idx = text.rfind(marker)
    if idx == -1:
        raise SystemExit("[X] could not locate feature-array close in LEHS file")
    serialized = ",\n".join(
        json.dumps(f, separators=(", ", ": "), ensure_ascii=False) for f in new
    )
    patched = text[:idx] + ",\n" + serialized + text[idx:]
    # sanity: must still parse and have the right count
    check = json.loads(patched)
    assert len(check["features"]) == len(fc["features"]) + len(new)
    LEHS.write_text(patched, encoding="utf-8")
    return len(new)


def main() -> int:
    if not ADDITIONS.exists():
        raise SystemExit(f"[X] {ADDITIONS} not found — run add_regional_districts.py first")
    feats = json.loads(ADDITIONS.read_text(encoding="utf-8"))["features"]
    print(f"Loaded {len(feats)} regional features to splice.")

    n_atlas = splice_atlas(feats)
    fc = json.loads(ATLAS.read_text(encoding="utf-8"))
    print(f"  atlas:  +{n_atlas}  -> {len(fc['features'])} features  ({ATLAS})")

    n_lehs = splice_lehs(feats)
    fc = json.loads(LEHS.read_text(encoding="utf-8"))
    print(f"  lehs:   +{n_lehs}  -> {len(fc['features'])} features  ({LEHS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
