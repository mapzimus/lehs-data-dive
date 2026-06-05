"""
Build the Lynn/LEHS slices for the eight DESE datasets the statewide atlas
acquired but this deep dive had not yet isolated (the parity gaps found
2026-06-05). Pulls each from the SODA JSON API at full precision and peer-filters
to the LEHS + Lynn + 26-gateway + State universe (see utils/gap_sources.py).

Writes to data/processed/:
    el_access.parquet            ACCESS for ELLs reporting elements (puw9-zucz)
    school_choice.parquet        resident-student outflow by reason   (vxt3-k35x)
    early_education.parquet      Pre-K / Kindergarten enrollment       (rg9w-dkpg)
    sped_placement.parquet       SpEd program characteristics          (n62c-bx65)
    grade_retention.parquet      grade-retention rate                  (c8ur-ajfv)
    ap_participation.parquet     AP test-taker / exam counts           (37cp-pad8)
    teacher_attendance.parquet   staff attendance rate                 (2hei-cc7k)
    discipline_disaggregated.parquet      REBUILT with real values from 2kca-w7rq
    discipline_disproportionality.parquet REBUILT (latest year per org) — this is
                                          what un-breaks pages/8_Discipline_and_Climate.py,
                                          which until now showed a "not yet populated" notice.

Re-runnable and additive: only the files above are touched; a fetch that fails
soft leaves the existing parquet untouched. Run:  python scripts/build_gap_datasets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    GATEWAY_CITIES,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)
from utils.gap_sources import (  # noqa: E402
    canon_peer,
    in_clause,
    load_peer_codes,
    pull,
    soda_all,
    tidy,
)

STATE_DIST = "00000000"  # DESE statewide rollup dist_code (used as the sped benchmark)

# ── Discipline legacy-schema mapping ──────────────────────────────────────────
# pages/8_Discipline_and_Climate.py expects the schema scripts/03 scaffolded:
#   discipline_disaggregated:      SY, ORG_CODE, ORG_NAME, DIM, GROUP, INDICATOR, VALUE
#   discipline_disproportionality: + GROUP_RATE, ALL_RATE, RISK_RATIO
# Map the SODA student-group labels (2kca-w7rq) to that file's (DIM, GROUP) taxonomy.
SODA_GRP_TO_LEGACY = {
    "All Students":                        ("all",    "All Students"),
    "Black or African American":           ("race",   "African American/Black"),
    "Asian":                               ("race",   "Asian"),
    "Hispanic or Latino":                  ("race",   "Hispanic/Latino"),
    "White":                               ("race",   "White"),
    "Multi-Race, Not Hispanic or Latino":  ("race",   "Multi-Race, Non-Hispanic/Latino"),
    "English Learners":                    ("ell",    "English Learner"),
    "Students with Disabilities":          ("sped",   "Students w/ Disabilities"),
    "Female":                              ("gender", "Female"),
    "Male":                                ("gender", "Male"),
}
# INDICATOR label -> SODA rate column (all already 0-1 fractions in the source).
INDICATOR_TO_COL = {
    "In-School Suspension Rate":     "IN_SUSP_PCT",
    "Out-of-School Suspension Rate": "OUT_SUSP_PCT",
    "Expulsion Rate":                "EXP_PCT",
    "Emergency Removal Rate":        "EMERG_RMVL_PCT",
}


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

def fetch_el_access(codes):
    df = pull("puw9-zucz",
              "dist_code,dist_name,org_code,org_name,org_type,sy,grade,"
              "enrolled_cnt,part_rate,re1_pct,re2_pct,re3_pct,re5_pct,re1_swd_pct",
              codes["districts"])
    return tidy(canon_peer(df, codes))


def fetch_school_choice(codes):
    # vxt3-k35x is keyed by TOWN OF RESIDENCE (town_name); its dist_code is the
    # *receiving* district. To measure each peer city's resident OUTFLOW we filter
    # by town_name (not dist_code) and sum enr_cnt per reason server-side. Reasons:
    # "Resident/Member" = stayed in own district; "School Choice Program" /
    # "Charter School" / "Tuitioned Out …" = left. Share is of all resident students.
    where = in_clause("town_name", set(GATEWAY_CITIES))  # 26 gateway cities incl. Lynn
    try:
        rows = soda_all("vxt3-k35x", {
            "$select": "town_name,sy,enr_reason,sum(enr_cnt) as enr_cnt",
            "$where": where,
            "$group": "town_name,sy,enr_reason",
            "$order": "town_name,sy",
        })
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] pull vxt3-k35x failed ({exc}); skipped")
        return pd.DataFrame()
    df = tidy(pd.DataFrame(rows))
    if df.empty:
        return df
    # Attach the residence town's district code so this file joins to the others.
    peers = json.loads((PROCESSED_DIR / "_peer_schools.json").read_text())
    town2dist = {c: i.get("district_code")
                 for c, i in peers.get("gateway_main_hs", {}).items()}
    df["DIST_CODE"] = df["TOWN_NAME"].map(town2dist).fillna("").astype(str).str.zfill(8)
    tot = df.groupby(["TOWN_NAME", "SY"])["ENR_CNT"].transform("sum")
    df["PCT_OF_RESIDENTS"] = (df["ENR_CNT"] / tot).round(4)
    return df.sort_values(["TOWN_NAME", "SY", "ENR_CNT"], ascending=[True, True, False])


def fetch_early_education(codes):
    df = pull("rg9w-dkpg",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,"
              "pkg_pkenr_tot,pk_subgroup_cnt,pkenr_pct,kgr_subgroup_cnt,"
              "kgr_subgroup_ful_cnt,kgr_subgroup_ful_pct",
              codes["districts"])
    return tidy(canon_peer(df, codes))


def fetch_sped_placement(codes):
    # District-grain only (no school/org dimension at DESE). Add the statewide
    # rollup row (00000000) as the benchmark, since this dataset has no 'State'.
    dist = set(codes["districts"]) | {STATE_DIST}
    df = pull("n62c-bx65",
              "dist_code,dist_name,sy,ind_cat,ind_desc,tot_cnt,ind_cnt,ind_pct,value_type",
              dist, has_org_type=False)
    df = tidy(df)
    if not df.empty:
        df.loc[df["DIST_CODE"] == STATE_DIST, "DIST_NAME"] = "Massachusetts (statewide)"
    return df


def fetch_grade_retention(codes):
    df = pull("c8ur-ajfv",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,"
              "enroll_all_cnt,ret_all_cnt,ret_all_pct",
              codes["districts"])
    return tidy(canon_peer(df, codes))


def fetch_ap_participation(codes):
    # subj='All Subjects' = the participation rollup (test takers + exams per
    # org x subgroup x year). Distinct from ap_performance.parquet (score mix).
    df = pull("37cp-pad8",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,"
              "test_takers_cnt,tests_taken_cnt",
              codes["districts"], extra_where="subj='All Subjects'")
    df = tidy(canon_peer(df, codes))
    if not df.empty:
        df["EXAMS_PER_TAKER"] = (df["TESTS_TAKEN_CNT"] / df["TEST_TAKERS_CNT"]).round(3)
    return df


def fetch_teacher_attendance(codes):
    df = pull("2hei-cc7k",
              "dist_code,dist_name,org_code,org_name,org_type,sy,staff_grp,"
              "staff_cnt,staff_attend_rate,staff_cnt_avg_abs",
              codes["districts"])
    return tidy(canon_peer(df, codes))


# ── Discipline: rebuild the two legacy files the page consumes ─────────────────

def fetch_discipline_raw(codes) -> pd.DataFrame:
    """All-Offenses discipline rates by org x subgroup x year (2kca-w7rq)."""
    df = pull("2kca-w7rq",
              "dist_code,dist_name,org_code,org_name,org_type,sy,stu_grp,offense,"
              "stu_cnt,in_susp_pct,out_susp_pct,exp_pct,emerg_rmvl_pct",
              codes["districts"], extra_where="offense='All Offenses'")
    df = tidy(canon_peer(df, codes))
    if not df.empty:
        df.loc[df["ORG_TYPE"] == "State", "ORG_NAME"] = df["ORG_NAME"].fillna("Massachusetts")
        df["ORG_NAME"] = df["ORG_NAME"].fillna("Massachusetts")
    return df


def build_discipline_disaggregated(raw: pd.DataFrame) -> pd.DataFrame:
    """Long form matching scripts/03's schema, with REAL values (all years)."""
    rows = []
    for r in raw.itertuples(index=False):
        legacy = SODA_GRP_TO_LEGACY.get(r.STU_GRP)
        if not legacy:
            continue
        dim, group = legacy
        for indicator, col in INDICATOR_TO_COL.items():
            rows.append({
                "SY": int(r.SY), "ORG_CODE": r.ORG_CODE, "ORG_NAME": r.ORG_NAME,
                "DIM": dim, "GROUP": group, "INDICATOR": indicator,
                "VALUE": getattr(r, col),
            })
    return pd.DataFrame(rows)


def build_discipline_disproportionality(disagg: pd.DataFrame) -> pd.DataFrame:
    """Risk ratios (group rate / all-students rate) for the LATEST year each org
    reports — so pages/8's default chart is one clean bar per subgroup."""
    have = disagg.dropna(subset=["VALUE"])
    if have.empty:
        return pd.DataFrame()
    latest = have.groupby("ORG_CODE")["SY"].max().rename("MAXSY")
    d = disagg.merge(latest, on="ORG_CODE")
    d = d[d["SY"] == d["MAXSY"]].drop(columns="MAXSY")

    base = (d[d["DIM"] == "all"][["SY", "ORG_CODE", "INDICATOR", "VALUE"]]
            .rename(columns={"VALUE": "ALL_RATE"}))
    grp = d[d["DIM"] != "all"].merge(base, on=["SY", "ORG_CODE", "INDICATOR"], how="left")
    grp = grp.rename(columns={"VALUE": "GROUP_RATE"})
    grp["RISK_RATIO"] = (pd.to_numeric(grp["GROUP_RATE"], errors="coerce")
                         / pd.to_numeric(grp["ALL_RATE"], errors="coerce")).round(3)
    return grp[["SY", "ORG_CODE", "ORG_NAME", "DIM", "GROUP",
                "INDICATOR", "GROUP_RATE", "ALL_RATE", "RISK_RATIO"]]


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    codes = load_peer_codes()
    print(f"Peer universe: {len(codes['schools'])} schools, "
          f"{len(codes['districts'])} districts (+State).\n")
    summary: list = []

    print("Pulling gap datasets from DESE SODA (full precision)…")
    _write(fetch_el_access(codes),         "el_access",          summary)
    _write(fetch_school_choice(codes),     "school_choice",      summary)
    _write(fetch_early_education(codes),    "early_education",    summary)
    _write(fetch_sped_placement(codes),    "sped_placement",     summary)
    _write(fetch_grade_retention(codes),   "grade_retention",    summary)
    _write(fetch_ap_participation(codes),  "ap_participation",   summary)
    _write(fetch_teacher_attendance(codes), "teacher_attendance", summary)

    print("\nRebuilding discipline (real values, fixes the broken placeholder)…")
    disc = fetch_discipline_raw(codes)
    if not disc.empty:
        disagg = build_discipline_disaggregated(disc)
        dispro = build_discipline_disproportionality(disagg)
        _write(disagg, "discipline_disaggregated",      summary)
        _write(dispro, "discipline_disproportionality", summary)
    else:
        print("  [skip] discipline fetch empty — legacy files left untouched")

    print("\n" + "=" * 78)
    print(f"{'dataset':32s} {'rows':>8s}  Lynn  LEHS  years")
    for name, n, lynn, lehs, note in summary:
        print(f"{name:32s} {n:>8,}  {lynn:>4s}  {lehs:>4s}  {note}")
    print(f"\nWritten to {PROCESSED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
