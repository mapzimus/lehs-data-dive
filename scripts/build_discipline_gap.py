"""
Build the Lynn/LEHS slices for two DESE E2C datasets the Discipline & Climate
page still lacked: the **annual dropout rate** (cmm7-ttbg) and the
**instructional days lost to discipline** distribution (3etc-hecr).

Modeled exactly on scripts/build_gap_datasets.py: each dataset is pulled from
the SODA JSON API at full precision (no CSV display-rounding) and reduced to
this project's peer universe (LEHS + every Lynn school + Lynn district + each
gateway city's main HS + the Massachusetts ``State`` benchmark row). Pulls fail
soft, so a partial run never clobbers a good parquet.

Writes to data/processed/:
    dropout.parquet                 annual dropout rate by org x subgroup x year,
                                    incl. by-grade (9-12) breakdowns (cmm7-ttbg)
    discipline_days_missed.parquet  share of disciplined students who lost
                                    1 / 2-3 / 4-7 / 8-10 / >10 instructional days
                                    (All Offenses) by org x subgroup x year (3etc-hecr)

Re-runnable and additive. Run:  python scripts/build_discipline_gap.py
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
    print(f"  [OK] {name:30s} {len(df):>7,} rows  Lynn={has_lynn}  LEHS={has_lehs}  {note}")
    summary.append((name, len(df), has_lynn, has_lehs, note))


# ── Per-dataset fetchers (each returns a tidy, peer-filtered frame) ────────────

def fetch_dropout(codes) -> pd.DataFrame:
    """Annual dropout rate by org x subgroup x year, with by-grade (9-12) splits.

    drpout_pct_all is a 0-1 annual dropout rate; the per-grade columns are the
    same fraction restricted to one grade. State benchmark row included via the
    pull() ``org_type='State'`` branch.
    """
    df = pull("cmm7-ttbg",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,"
              "enroll_cnt_all,drpout_cnt_all,drpout_pct_all,"
              "drpout_pct_grd_09,drpout_pct_grd_10,drpout_pct_grd_11,drpout_pct_grd_12",
              codes["districts"], has_org_type=True)
    return tidy(canon_peer(df, codes))


def fetch_discipline_days_missed(codes) -> pd.DataFrame:
    """Distribution of instructional days lost to discipline (All Offenses).

    days_*_pct columns are the share of *disciplined* students whose discipline
    cost them that many days (1 / 2-3 / 4-7 / 8-10 / >10).
    """
    df = pull("3etc-hecr",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,offense,"
              "stu_cnt,stu_discipl_cnt,days_1_pct,days_2_3_pct,days_4_7_pct,"
              "days_8_10_pct,days_grtr_10_pct",
              codes["districts"], has_org_type=True,
              extra_where="offense='All Offenses'")
    df = tidy(canon_peer(df, codes))
    if not df.empty:
        # State rollup carries a null ORG_NAME in some E2C tables — label it.
        df.loc[df["ORG_TYPE"] == "State", "ORG_NAME"] = (
            df.loc[df["ORG_TYPE"] == "State", "ORG_NAME"].fillna("Massachusetts")
        )
    return df


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_peer_codes()
    print(f"Peer universe: {len(codes['schools'])} schools, "
          f"{len(codes['districts'])} districts (+State).\n")
    summary: list = []

    print("Pulling dropout + discipline-days-missed from DESE SODA (full precision)…")
    _write(fetch_dropout(codes),                 "dropout",                 summary)
    _write(fetch_discipline_days_missed(codes),  "discipline_days_missed",  summary)

    print("\n" + "=" * 78)
    print(f"{'dataset':32s} {'rows':>8s}  Lynn  LEHS  years")
    for name, n, lynn, lehs, note in summary:
        print(f"{name:32s} {n:>8,}  {lynn:>4s}  {lehs:>4s}  {note}")
    print(f"\nWritten to {PROCESSED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
