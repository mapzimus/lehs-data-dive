"""
Build the Lynn/LEHS slices for two DESE "academic on-track" datasets the deep
dive had not yet isolated, surfaced on pages/2_Academic_Performance.py:

Writes to data/processed/:
    grade9_passing.parquet   Grade-9 course-passing rates by org x subgroup x
                             subject x year (4sut-78p8). pass_pct is a 0-1 share
                             of grade-9 students passing that subject; an
                             "All Subjects" rollup row exists per org/year and is
                             used for the on-track headline + trend.
    mcas_alt.parquet         MCAS Alternate Assessment performance-level mix by
                             org x subject x year (ks7h-2kdy), for the small group
                             of students with the most significant cognitive
                             disabilities. Levels: Progressing / Emerging /
                             Awareness / Incomplete (each a 0-1 share). tot_stu_cnt
                             is tiny (~10 at LEHS) so read as indicative only.

Modeled on scripts/build_gap_datasets.py: full-precision SODA JSON pulls,
server-side peer-filtered to the LEHS + Lynn + 26-gateway + State universe (see
utils/gap_sources.py), re-runnable and additive. Run:
    python scripts/build_academic_gap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)
from utils.gap_sources import (  # noqa: E402
    canon_peer,
    load_peer_codes,
    pull,
    tidy,
)


def _write(df: pd.DataFrame, name: str, summary: list) -> None:
    """Write a tidy parquet and record a verification row (skips empty fetches)."""
    out = PROCESSED_DIR / f"{name}.parquet"
    if df is None or df.empty:
        print(f"  [skip] {name}: empty fetch — existing file left untouched")
        summary.append((name, 0, "—", "—", "fetch empty"))
        return
    df.to_parquet(out, index=False)
    has_lynn = has_lehs = "n/a"
    if "DIST_CODE" in df.columns:
        has_lynn = "yes" if (df["DIST_CODE"] == LYNN_DISTRICT_CODE).any() else "NO"
    if "ORG_CODE" in df.columns:
        has_lehs = "yes" if (df["ORG_CODE"] == LEHS_SCHOOL_CODE).any() else "NO"
    note = f"{df['SY'].min()}–{df['SY'].max()}" if "SY" in df.columns else ""
    print(f"  [OK] {name:20s} {len(df):>7,} rows  Lynn={has_lynn}  LEHS={has_lehs}  {note}")
    summary.append((name, len(df), has_lynn, has_lehs, note))


# ── Per-dataset fetchers (each returns a tidy, peer-filtered frame) ────────────

def fetch_grade9_passing(codes):
    # Grade-9 course passing by org x subgroup x subject x year. pass_pct is a
    # 0-1 share; the 'All Subjects' subject is the per-org/year on-track rollup.
    # pass_pct can be null where the cell is suppressed (tiny n).
    df = pull("4sut-78p8",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,subject,"
              "g09_cnt,pass_cnt,pass_pct",
              codes["districts"])
    df = canon_peer(df, codes)
    # tidy() numeric-coerces any column not in its STRING_COLS allow-list, and
    # the source's "subject" label column is NOT on it (only the "subj" spelling
    # is). Rename to the recognized "subj" before tidy() so the subject labels
    # survive as strings instead of being blanked to NaN.
    if "subject" in df.columns:
        df = df.rename(columns={"subject": "subj"})
    return tidy(df)


def fetch_mcas_alt(codes):
    # MCAS Alternate Assessment performance-level distribution by org x subject x
    # year. Each *_pct is a 0-1 share of the (very small) tested group.
    df = pull("ks7h-2kdy",
              "dist_code,dist_name,org_code,org_name,org_type,sy,subj,"
              "tot_stu_cnt,prog_cnt,prog_pct,emrg_cnt,emrg_pct,awr_cnt,awr_pct,"
              "incomplt_cnt,incomplt_pct",
              codes["districts"])
    return tidy(canon_peer(df, codes))


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_peer_codes()
    print(f"Peer universe: {len(codes['schools'])} schools, "
          f"{len(codes['districts'])} districts (+State).\n")
    summary: list = []

    print("Pulling academic on-track datasets from DESE SODA (full precision)…")
    _write(fetch_grade9_passing(codes), "grade9_passing", summary)
    _write(fetch_mcas_alt(codes),       "mcas_alt",       summary)

    print("\n" + "=" * 70)
    print(f"{'dataset':20s} {'rows':>8s}  Lynn  LEHS  years")
    for name, n, lynn, lehs, note in summary:
        print(f"{name:20s} {n:>8,}  {lynn:>4s}  {lehs:>4s}  {note}")
    print(f"\nWritten to {PROCESSED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
