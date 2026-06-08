"""
Build the Lynn/LEHS slices for DESE's two **course-access / opportunity**
dashboards — an equity lens on *who gets to take* computer-science and arts
coursework, not just how students score. Both are pulled at full precision from
the SODA JSON API and peer-filtered to the LEHS + Lynn + 26-gateway + State
universe (see utils/gap_sources.py), exactly like scripts/build_gap_datasets.py.

Writes to data/processed/:
    dlcs_course_taking.parquet   share taking any Digital Literacy / Computer
                                 Science course (fbdq-3q4d, subj='All Subjects').
                                 ALL_GRADES_PCT = % of enrolled students taking
                                 one or more DLCS courses.
    arts_course_taking.parquet   share taking any arts course (w3f3-phkq,
                                 art_subj='All Subjects'). ALL_GRDS_PCT = % of
                                 enrolled students taking one or more arts courses.

Both files are org x subgroup x year, so the page can show an All-Students-plus-
subgroup access chart at LEHS against the Massachusetts rate.

Re-runnable and additive: only the two files above are touched; a fetch that
fails soft leaves the existing parquet untouched. Run:
    python scripts/build_course_access_gap.py
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
    print(f"  [OK] {name:24s} {len(df):>7,} rows  Lynn={has_lynn}  LEHS={has_lehs}  {note}")
    summary.append((name, len(df), has_lynn, has_lehs, note))


# ── Per-dataset fetchers (each returns a tidy, peer-filtered frame) ────────────

def fetch_dlcs(codes) -> pd.DataFrame:
    # subj='All Subjects' = the rollup row whose ALL_GRADES_PCT is the share of
    # enrolled students taking ONE OR MORE Digital Literacy / Computer Science
    # courses (per org x subgroup x year). The individual-subject rows are
    # dropped server-side via extra_where so this stays one clean access metric.
    df = pull("fbdq-3q4d",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,subj,"
              "total_cnt,all_grades_cnt,all_grades_pct",
              codes["districts"], extra_where="subj='All Subjects'")
    return tidy(canon_peer(df, codes))


def fetch_arts(codes) -> pd.DataFrame:
    # art_subj='All Subjects' = the rollup row whose ALL_GRDS_PCT is the share of
    # enrolled students taking ONE OR MORE arts courses (per org x subgroup x
    # year). Leaf art-subject rows (Dance, Music, …) are dropped server-side.
    df = pull("w3f3-phkq",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,art_subj,"
              "tot_stu_cnt,all_grds_cnt,all_grds_pct",
              codes["districts"], extra_where="art_subj='All Subjects'")
    return tidy(canon_peer(df, codes))


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_peer_codes()
    print(f"Peer universe: {len(codes['schools'])} schools, "
          f"{len(codes['districts'])} districts (+State).\n")
    summary: list = []

    print("Pulling course-access datasets from DESE SODA (full precision)…")
    _write(fetch_dlcs(codes), "dlcs_course_taking", summary)
    _write(fetch_arts(codes), "arts_course_taking", summary)

    print("\n" + "=" * 70)
    print(f"{'dataset':24s} {'rows':>8s}  Lynn  LEHS  years")
    for name, n, lynn, lehs, note in summary:
        print(f"{name:24s} {n:>8,}  {lynn:>4s}  {lehs:>4s}  {note}")
    print(f"\nWritten to {PROCESSED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
