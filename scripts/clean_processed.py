"""
Final cleaning pass over data/processed/*.parquet. Idempotent; run after every
refresh (it is the last data step in refresh_all.py).

DESE/E2C ship a few recurring defects that the download steps pass through
verbatim. Each fix below names the defect it removes:

  1. Exact duplicate rows (every column identical). DART Success After HS
     repeats whole indicator blocks in SY2024/2025; Special Education
     Indicators repeats some MassCore rows.

  2. "Ghost" rows: the same school x group x indicator x year appears twice,
     once with the real value and once with a tiny STU_INCL and a blank value.
     Pages that take the first match could show a blank.

  3. Two real values for one key. DART postsecondary indicators for SY2022
     and SY2024 come in pairs with no column telling them apart. The SY2024
     pairs share a cohort and differ by a student or two (a re-match); in
     SY2022 the larger cohort is the one consistent with the school's
     single All Students row. Keep the larger cohort, ties -> the later row.

  4. SpEd placement lists "Other Disability" twice for some districts in
     SY2021-2025 (counts within a few students). Keep the later row.

  5. Infinite discipline risk ratios where the all-students rate rounds to 0.
     The builders now leave those blank; this clears any already on disk.

Run:  python scripts/clean_processed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR  # noqa: E402

# dataset -> (key columns, value column, cohort-size column or None)
KEYED = {
    "dart_success_after_hs": (
        ["SY", "ORG_CODE", "GRADES", "STU_GRP", "CATEGORY", "INDICATOR", "VALUETYPE"],
        "VALUE", "STU_INCL"),
    "special_ed_indicators": (
        ["SY", "DIST_CODE", "GRADES", "STU_GRP", "IND_CAT", "IND_DESC", "VALUE_TYPE"],
        "IND_PCT", "TOT_CNT"),
    "sped_placement": (
        ["SY", "DIST_CODE", "IND_CAT", "IND_DESC", "VALUE_TYPE"],
        "IND_PCT", None),
}


def collapse_keys(df: pd.DataFrame, keys: list[str], value: str,
                  size: str | None) -> pd.DataFrame:
    """One row per key: drop blank-value ghosts, then keep the largest cohort
    (or simply the last row when there is no cohort column)."""
    df = df.reset_index(drop=True)
    dup = df.duplicated(subset=keys, keep=False)
    if not dup.any():
        return df
    has_value = df.groupby(keys, dropna=False)[value].transform("count") > 0
    ghost = dup & df[value].isna() & has_value
    df = df[~ghost]
    order = [size] if size else []
    # Stable sort keeps file order among ties, so keep="last" = later row.
    df = (df.assign(_row=np.arange(len(df)))
            .sort_values(order + ["_row"], kind="stable")
            .drop_duplicates(subset=keys, keep="last")
            .sort_values("_row")
            .drop(columns="_row"))
    return df.reset_index(drop=True)


def main() -> None:
    total = 0
    for path in sorted(PROCESSED_DIR.glob("*.parquet")):
        name = path.stem
        df = pd.read_parquet(path)
        before = len(df)
        notes = []

        df = df.drop_duplicates()
        if len(df) < before:
            notes.append(f"{before - len(df)} exact duplicates")

        if name in KEYED:
            keys, value, size = KEYED[name]
            n = len(df)
            df = collapse_keys(df, keys, value, size)
            if len(df) < n:
                notes.append(f"{n - len(df)} duplicate-key rows")

        changed = len(df) < before
        if name == "discipline_disproportionality" and "RISK_RATIO" in df.columns:
            inf = np.isinf(df["RISK_RATIO"])
            if inf.any():
                df.loc[inf, "RISK_RATIO"] = np.nan
                notes.append(f"{int(inf.sum())} infinite risk ratios blanked")
                changed = True

        if changed:
            df.to_parquet(path, index=False)
            total += before - len(df)
            print(f"  {name}: " + ", ".join(notes))
    print(f"Done. {total:,} rows removed.")


if __name__ == "__main__":
    main()
