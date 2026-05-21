"""
Build processed Parquet files for the dashboard.

For each downloaded E2C Hub CSV, filter to our schools of interest:
  - LEHS specifically  (org code 01630510)
  - All Lynn district schools  (district code 01630000)
  - All gateway-city main comprehensive HS  (26 schools)

Output to data/processed/<dataset_name>.parquet (small, joinable, committable).

Run AFTER 01_download_e2c.py and 07_identify_peer_schools.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
    RAW_DIR,
)

E2C_RAW = RAW_DIR / "e2c_hub"
PEER_FILE = PROCESSED_DIR / "_peer_schools.json"


def load_peer_schools() -> dict:
    if not PEER_FILE.exists():
        raise FileNotFoundError(
            f"{PEER_FILE} not found. Run scripts/07_identify_peer_schools.py first."
        )
    return json.loads(PEER_FILE.read_text())


def build_school_filter_codes(peers: dict) -> dict[str, set[str]]:
    """All school codes we care about, partitioned into useful groups."""
    lynn_schools = set((peers.get("lynn_all_schools") or {}).values())
    gateway_main = {
        info["school_code"]
        for info in peers.get("gateway_main_hs", {}).values()
        if info.get("school_code")
    }
    return {
        "lehs":         {LEHS_SCHOOL_CODE},
        "lynn_all":     lynn_schools,
        "gateway_main": gateway_main,
        "everything":   {LEHS_SCHOOL_CODE} | lynn_schools | gateway_main,
    }


def build_district_filter_codes(peers: dict) -> set[str]:
    """District codes for Lynn + every gateway city."""
    codes = {LYNN_DISTRICT_CODE}
    for info in peers.get("gateway_main_hs", {}).values():
        if info.get("district_code"):
            codes.add(info["district_code"])
    return codes


def filter_school_csv(
    csv_path: Path,
    out_path: Path,
    school_codes: set[str],
    district_codes: set[str] | None = None,
) -> int:
    """Read a CSV, filter to ORG_CODE in school_codes or DIST_CODE in district_codes."""
    df = pd.read_csv(csv_path, low_memory=False, dtype={"DIST_CODE": str, "ORG_CODE": str})
    if "ORG_CODE" in df.columns:
        df["ORG_CODE"] = df["ORG_CODE"].fillna("").str.zfill(8)
    if "DIST_CODE" in df.columns:
        df["DIST_CODE"] = df["DIST_CODE"].fillna("").str.zfill(8)

    # DESE/E2C are inconsistent across datasets in how they label rows. The
    # MCAS Achievement file labels schools "Public School" and districts
    # "Public School District", while enrollment, graduation, attendance, etc.
    # use the shorter "School" and "District". We accept both spellings during
    # filtering and normalize to a canonical set after, so every downstream
    # page can rely on the schema:
    #
    #     ORG_TYPE ∈ {"School", "District", "State"}
    #
    # Charter schools/districts aren't currently in our peer set, but if they
    # ever are, the same normalization map collapses them into the canonical
    # values (and we'd add a separate IS_CHARTER column if we needed to keep
    # the distinction).
    DISTRICT_ORG_TYPES = {"District", "Public School District", "Charter District"}
    ORG_TYPE_CANONICAL_MAP = {
        "Public School": "School",
        "Charter School": "School",
        "Public School District": "District",
        "Charter District": "District",
    }

    if "ORG_CODE" in df.columns:
        # Include schools we care about
        mask = df["ORG_CODE"].isin(school_codes)
        # ALSO include district-level rows for the districts we care about.
        # DESE uses the district code as ORG_CODE on these rows.
        if district_codes and "DIST_CODE" in df.columns:
            district_mask = df["DIST_CODE"].isin(district_codes)
            if "ORG_TYPE" in df.columns:
                district_mask = district_mask & df["ORG_TYPE"].isin(DISTRICT_ORG_TYPES)
            else:
                # Fall back: row where ORG_CODE == DIST_CODE
                district_mask = district_mask & (df["ORG_CODE"] == df["DIST_CODE"])
            mask = mask | district_mask
        # ALSO include state-level aggregate rows so charts can benchmark
        # against the Massachusetts statewide average.
        if "ORG_TYPE" in df.columns:
            mask = mask | (df["ORG_TYPE"] == "State")
        filtered = df[mask]
    elif "DIST_CODE" in df.columns:
        filtered = df[df["DIST_CODE"].isin(district_codes or set())]
    else:
        print(f"  WARN: no DIST_CODE or ORG_CODE column — skipping {csv_path.name}")
        return 0

    # Normalize ORG_TYPE so every page can match on the canonical
    # {"School", "District", "State"} regardless of upstream variation.
    if "ORG_TYPE" in filtered.columns:
        filtered = filtered.assign(
            ORG_TYPE=filtered["ORG_TYPE"].replace(ORG_TYPE_CANONICAL_MAP)
        )

    filtered.to_parquet(out_path, index=False)
    return len(filtered)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    peers = load_peer_schools()
    school_filters = build_school_filter_codes(peers)
    district_codes = build_district_filter_codes(peers)

    print("Filtering targets:")
    print(f"  LEHS                = {len(school_filters['lehs'])}")
    print(f"  Lynn district HS    = {len(school_filters['lynn_all'])}")
    print(f"  Gateway main HS     = {len(school_filters['gateway_main'])}")
    print(f"  Total unique schools= {len(school_filters['everything'])}")
    print(f"  Districts           = {len(district_codes)}")
    print()

    csv_files = sorted(E2C_RAW.glob("*.csv"))
    print(f"Processing {len(csv_files)} E2C CSV files...\n")

    summary = []
    for csv in csv_files:
        out = PROCESSED_DIR / f"{csv.stem}.parquet"
        try:
            n = filter_school_csv(
                csv, out, school_filters["everything"], district_codes
            )
            print(f"  [OK] {csv.name:42s} -> {n:>8,} rows -> {out.name}")
            summary.append((csv.name, n))
        except Exception as e:
            print(f"  [X]  {csv.name}: {e}")
            summary.append((csv.name, -1))

    print()
    print("=" * 70)
    print("Done. Summary:")
    for name, n in summary:
        print(f"  {name:42s} {n:>8,} rows")
    print(f"\nProcessed files written to: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
