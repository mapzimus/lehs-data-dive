"""
Download + parse federal CRDC (Civil Rights Data Collection) data for Lynn.

CRDC is a biennial collection from the U.S. Department of Education's Office for
Civil Rights (civilrightsdata.ed.gov). The most recent **public-use** release is
the **2021-22** school year. It provides school-level data that state datasets
don't carry, including:
  - In-school + out-of-school suspensions, expulsions, school-based arrests,
    referrals to law enforcement, restraint and seclusion (each disaggregated
    by race / disability / English-learner status).
  - AP / IB course offerings and enrollment, advanced-math/-science offerings.
  - Counselor / nurse / social-worker / psychologist / law-enforcement FTE.

Bulk source (verified 2026-06-08; returns a ~832 MB application/x-zip ZIP that
contains 34 topical flat-file CSVs — 3 LEA-level + 31 school-level):
    https://civilrightsdata.ed.gov/assets/ocr/docs/2021-22-crdc-data.zip

That host drops long single-stream downloads, but it DOES honor HTTP Range
requests, so we fetch the ZIP in resumable 8 MB segments (see download_zip). If
the download still can't complete headlessly, drop the ZIP (or its extracted
CSVs) into data/raw/crdc/ manually and re-run — see data/raw/crdc/README.md.

Lynn district NCES LEAID = 2507110 (LEA_NAME "Lynn", LEA_STATE MA in the 2021-22
public file; this district has 25 schools incl. "Lynn English High"). NOTE: the
2515480 value carried by earlier scaffolding does NOT exist in this release and
returned zero rows — 2507110 is the verified id. The CRDC carries no
Massachusetts DESE code, so rows are filtered by NCES LEAID and the Lynn DESE
district code/name are attached afterward so the parquets join to data/processed.

CRDC reserve codes (negative values) are NOT real counts — per the 2021-22
User's Manual, Table 1: -3 skip-logic/processing-failure, -5 action-plan,
-6 force-certified, -9 not-applicable/skipped, -12 suppressed-for-privacy,
-13 missing-DIND. Every count value is coerced through `_num`, which maps any
negative to NaN so suppressed/not-collected cells never masquerade as zero.

Outputs (data/processed/):
  - crdc_discipline.parquet   (school x student-group long form)
  - crdc_offerings.parquet    (one row per school)
  - crdc_staffing.parquet     (one row per school)

Run with:
    python scripts/04_download_crdc.py
"""

from __future__ import annotations

import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    LYNN_DISTRICT_CODE,
    LYNN_DISTRICT_NAME,
    PROCESSED_DIR,
    RAW_DIR,
)

CRDC_RAW = RAW_DIR / "crdc"
CRDC_RAW.mkdir(parents=True, exist_ok=True)

# Most recent public-use release. Topical CSVs inside the ZIP live under LEA/
# and SCH/ (e.g. "SCH/Suspensions.csv").
RELEASE = "2021-22"
RELEASE_LABEL = "2021-22"
BULK_URL = "https://civilrightsdata.ed.gov/assets/ocr/docs/2021-22-crdc-data.zip"

LYNN_LEAID = "2507110"   # NCES LEAID for Lynn (MA) in the 2021-22 CRDC; verified
                         # against the file (25 schools incl. Lynn English High).
                         # Earlier scaffolding used 2515480, which is absent here.

HEADERS = {"User-Agent": "lehs-data-dive/0.3 (https://github.com/mapzimus/lehs-data-dive)"}

# Race-suffix -> readable label (CRDC uses these two-letter race codes).
RACE_SUFFIXES = {
    "HI": "Hispanic/Latino",
    "AM": "American Indian/Alaska Native",
    "AS": "Asian",
    "HP": "Native Hawaiian/Pacific Islander",
    "BL": "Black/African American",
    "WH": "White",
    "TR": "Two or More Races",
}


# ---------------------------------------------------------------------------
# Download (resumable, Range-based — the ED host resets long single streams)
# ---------------------------------------------------------------------------

def download_zip() -> Path | None:
    """Fetch the release ZIP in resumable 8 MB Range segments.

    Returns the local path once the file is complete, else None. Re-runnable: a
    partially-downloaded file is resumed and a complete file is reused. Fails
    soft on a network error so a re-run (or a manual drop) can finish the job.
    """
    out = CRDC_RAW / f"{RELEASE}.zip"
    try:
        head = requests.head(BULK_URL, headers=HEADERS, timeout=60, allow_redirects=True)
        total = int(head.headers.get("Content-Length", 0))
        ctype = head.headers.get("Content-Type", "")
    except Exception as exc:  # noqa: BLE001
        print(f"  [WARN] HEAD {BULK_URL} failed: {exc}")
        total, ctype = 0, ""

    # The site's SPA fallback is ~62 KB of text/html; a real ZIP is ~800 MB.
    if total and total < 10_000_000:
        print(f"  [WARN] {BULK_URL} returned only {total:,} bytes ({ctype}); not a "
              "data file (likely the SPA fallback page).")
        return out if (out.exists() and out.stat().st_size > 10_000_000) else None
    if out.exists() and total and out.stat().st_size == total:
        print(f"  Already downloaded: {out} ({total:,} bytes)")
        return out

    seg = 8 * 1024 * 1024
    have = out.stat().st_size if out.exists() else 0
    if total and have > total:        # stale/corrupt — restart
        have = 0
    print(f"  Downloading {BULK_URL}\n    resuming at {have:,}"
          + (f"/{total:,}" if total else ""))
    t0 = time.time()
    mode = "r+b" if have else "wb"
    stalls = 0
    with open(out, mode) as f:
        f.seek(have)
        pos = have
        while not total or pos < total:
            end = (min(pos + seg, total) - 1) if total else (pos + seg - 1)
            try:
                r = requests.get(BULK_URL, headers=dict(HEADERS, Range=f"bytes={pos}-{end}"),
                                 timeout=60, stream=True)
                if r.status_code not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status_code}")
                wrote = 0
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)
                    pos += len(chunk)
                    wrote += len(chunk)
                stalls = 0
                if not total and wrote == 0:      # server signalled EOF
                    break
            except Exception as exc:  # noqa: BLE001
                stalls += 1
                f.flush()
                pos = out.stat().st_size
                f.seek(pos)
                if stalls > 50:
                    print(f"  [WARN] aborting after repeated resets at {pos:,}: {exc}")
                    break
                time.sleep(min(stalls, 5))
    final = out.stat().st_size
    ok = (final == total) if total else (final > 10_000_000)
    print(f"  Download {'complete' if ok else 'INCOMPLETE'}: "
          f"{final:,}{('/' + format(total, ',')) if total else ''} bytes "
          f"in {time.time() - t0:.0f}s")
    return out if ok else None


def find_local_archive() -> Path | None:
    """Return the largest manually-dropped ZIP in data/raw/crdc/, if any."""
    zips = sorted(CRDC_RAW.glob("*.zip"), key=lambda p: p.stat().st_size, reverse=True)
    for z in zips:
        if z.stat().st_size > 10_000_000:
            return z
    return None


def extract_zip(zip_path: Path) -> Path:
    """Extract just the topical CSVs (skips PDFs/manuals) to save disk + time."""
    out_dir = zip_path.with_suffix("")
    out_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".csv"):
                zf.extract(name, out_dir)
    return out_dir


# ---------------------------------------------------------------------------
# CSV loading + Lynn filter + value coercion
# ---------------------------------------------------------------------------

def _read_csv(release_dir: Path, member: str) -> pd.DataFrame:
    """Read one topical CSV (e.g. 'SCH/Suspensions.csv'); empty DF if missing."""
    stem = Path(member).name
    matches = list(release_dir.rglob(stem))
    if not matches:
        print(f"    [WARN] {member} not found under {release_dir}")
        return pd.DataFrame()
    try:
        return pd.read_csv(matches[0], low_memory=False, encoding_errors="replace",
                           dtype=str)
    except Exception as exc:  # noqa: BLE001
        print(f"    [WARN] failed to read {matches[0].name}: {exc}")
        return pd.DataFrame()


def filter_lynn(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows for Lynn Public Schools (NCES LEAID 2515480)."""
    if df.empty:
        return df
    id_cols = [c for c in df.columns if c.upper() in ("LEAID", "LEA_ID", "LEAID_NCES")]
    if not id_cols:
        return df.head(0)
    col = id_cols[0]
    leaid = df[col].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)
    return df[leaid == LYNN_LEAID].copy()


def _num(series: pd.Series) -> pd.Series:
    """Coerce a CRDC count column to numeric, mapping reserve codes (any
    negative value) to NaN so suppressed/not-collected cells aren't read as 0."""
    s = pd.to_numeric(series, errors="coerce")
    return s.where(s >= 0)


def _sum_cols(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    """Row-wise sum of the given columns (reserve codes -> NaN -> skipped).

    Returns NaN only when *every* contributing column is NaN for that row,
    otherwise the sum of the present (non-negative) values.
    """
    present = [c for c in cols if c in df.columns]
    if not present:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")
    block = pd.concat([_num(df[c]) for c in present], axis=1)
    return block.sum(axis=1, min_count=1)


def _ind_yesno(series: pd.Series) -> pd.Series:
    """Normalize a CRDC '_IND' offering flag to 'Yes'/'No'/NA.

    Values are textual 'Yes'/'No' in the public file; reserve codes -> NA.
    """
    s = series.astype(str).str.strip().str.lower()
    out = pd.Series(pd.NA, index=series.index, dtype="object")
    out[s.isin(["yes", "y", "1"])] = "Yes"
    out[s.isin(["no", "n", "0"])] = "No"
    return out


def _count_offered(series: pd.Series) -> pd.Series:
    """Turn a 'number of classes/courses' column into a Yes/No offered flag."""
    n = _num(series)
    out = pd.Series(pd.NA, index=series.index, dtype="object")
    out[n > 0] = "Yes"
    out[n == 0] = "No"
    return out


# ---------------------------------------------------------------------------
# Discipline
# ---------------------------------------------------------------------------

def _disc_group_cols(prefix_wo: str, prefix_widea: str | None,
                     suffix_m: str = "_M", suffix_f: str = "_F") -> dict[str, list[str]]:
    """Build {group_key: [contributing columns]} for total / race / ell / SwD.

    prefix_wo    -> the "without disability" stem, e.g. SCH_DISCWODIS_ISS
    prefix_widea -> the "with disability (IDEA)" stem, e.g. SCH_DISCWDIS_ISS_IDEA
                    (None when this metric has no separate IDEA race block)
    Race rows combine the wo-disability race cells with the IDEA race cells.
    The All-Students total and SwD total use the TOT_* roll-up columns.
    """
    groups: dict[str, list[str]] = {}
    tot_wo = [f"TOT{prefix_wo[3:]}{suffix_m}", f"TOT{prefix_wo[3:]}{suffix_f}"]
    tot_idea: list[str] = []
    if prefix_widea:
        tot_idea = [f"TOT{prefix_widea[3:]}{suffix_m}", f"TOT{prefix_widea[3:]}{suffix_f}"]
    groups["__total__"] = tot_wo + tot_idea
    for code, label in RACE_SUFFIXES.items():
        cols = [f"{prefix_wo}_{code}{suffix_m}", f"{prefix_wo}_{code}{suffix_f}"]
        if prefix_widea:
            cols += [f"{prefix_widea}_{code}{suffix_m}", f"{prefix_widea}_{code}{suffix_f}"]
        groups[label] = cols
    groups["English Learner"] = [f"{prefix_wo}_EL{suffix_m}", f"{prefix_wo}_EL{suffix_f}"]
    if prefix_widea:
        groups["Students w/ Disabilities"] = tot_idea
    return groups


def build_discipline(release_dir: Path) -> pd.DataFrame:
    """Per-school x student-group discipline counts (long form)."""
    susp = filter_lynn(_read_csv(release_dir, "SCH/Suspensions.csv"))
    exp = filter_lynn(_read_csv(release_dir, "SCH/Expulsions.csv"))
    ref = filter_lynn(_read_csv(release_dir, "SCH/Referrals and Arrests.csv"))
    rs = filter_lynn(_read_csv(release_dir, "SCH/Restraint and Seclusion.csv"))

    if susp.empty:
        return empty_schema("discipline")

    # Join on COMBOKEY (LEAID+SCHID): SCHID itself is formatted inconsistently
    # across topical files (e.g. '01080' in discipline vs '1080' in enrollment),
    # but COMBOKEY is the canonical, consistently-padded unique key everywhere.
    base = susp[["COMBOKEY", "SCHID", "SCH_NAME"]].copy()
    base.columns = ["COMBOKEY", "SCHID", "SCHOOL_NAME"]

    def combine(*specs: dict[str, list[str]]) -> dict[str, list[str]]:
        """Merge several group-spec dicts, concatenating columns per group."""
        out: dict[str, list[str]] = {}
        for spec in specs:
            for key, cols in spec.items():
                out.setdefault(key, []).extend(cols)
        return out

    iss_spec = _disc_group_cols("SCH_DISCWODIS_ISS", "SCH_DISCWDIS_ISS_IDEA")
    soos_spec = _disc_group_cols("SCH_DISCWODIS_SINGOOS", "SCH_DISCWDIS_SINGOOS_IDEA")
    moos_spec = _disc_group_cols("SCH_DISCWODIS_MULTOOS", "SCH_DISCWDIS_MULTOOS_IDEA")
    arr_spec = _disc_group_cols("SCH_DISCWODIS_ARR", "SCH_DISCWDIS_ARR_IDEA")
    ref_spec = _disc_group_cols("SCH_DISCWODIS_REF", "SCH_DISCWDIS_REF_IDEA")
    # Expulsion = with-ed-services + without-ed-services + zero-tolerance.
    exp_spec = combine(
        _disc_group_cols("SCH_DISCWODIS_EXPWE", "SCH_DISCWDIS_EXPWE_IDEA"),
        _disc_group_cols("SCH_DISCWODIS_EXPWOE", "SCH_DISCWDIS_EXPWOE_IDEA"),
        _disc_group_cols("SCH_DISCWODIS_EXPZT", "SCH_DISCWDIS_EXPZT_IDEA"),
    )
    # Restraint (physical) and seclusion: non-IDEA + IDEA blocks; SwD = IDEA total.
    phys_spec = combine(
        _disc_group_cols("SCH_RS_NONIDEA_PHYS", None),
        _disc_group_cols("SCH_RS_IDEA_PHYS", None),
        {"Students w/ Disabilities": ["TOT_RS_IDEA_PHYS_M", "TOT_RS_IDEA_PHYS_F"]},
    )
    secl_spec = combine(
        _disc_group_cols("SCH_RS_NONIDEA_SECL", None),
        _disc_group_cols("SCH_RS_IDEA_SECL", None),
        {"Students w/ Disabilities": ["TOT_RS_IDEA_SECL_M", "TOT_RS_IDEA_SECL_F"]},
    )

    # (output column, source frame, group-spec)
    metrics = [
        ("ISS_COUNT",          susp, iss_spec),
        ("OSS_SINGLE_COUNT",   susp, soos_spec),
        ("OSS_MULTIPLE_COUNT", susp, moos_spec),
        ("EXPULSION_COUNT",    exp,  exp_spec),
        ("ARREST_COUNT",       ref,  arr_spec),
        ("LE_REFERRAL_COUNT",  ref,  ref_spec),
        ("RESTRAINT_PHYSICAL", rs,   phys_spec),
        ("SECLUSION_COUNT",    rs,   secl_spec),
    ]
    metric_cols = [m[0] for m in metrics]

    all_groups = (["__total__"] + list(RACE_SUFFIXES.values())
                  + ["English Learner", "Students w/ Disabilities"])
    GROUP_DIM = {"__total__": "total", "English Learner": "ell",
                 "Students w/ Disabilities": "disability"}
    GROUP_LABEL = {"__total__": "All Students"}

    rows: dict[tuple, dict] = {}
    for sch in base.itertuples(index=False):
        for key in all_groups:
            rows[(sch.COMBOKEY, key)] = {
                "RELEASE": RELEASE_LABEL,
                "LEAID": LYNN_LEAID,
                "SCHID": sch.SCHID,
                "SCHOOL_NAME": sch.SCHOOL_NAME,
                "GROUP": GROUP_LABEL.get(key, key),
                "GROUP_DIM": GROUP_DIM.get(key, "race"),
                **{m: pd.NA for m in metric_cols},
            }

    for out_col, frame, spec in metrics:
        if frame is None or frame.empty:
            continue
        frame = frame.reset_index(drop=True)
        keys = frame["COMBOKEY"].values
        for grp_key, cols in spec.items():
            vals = _sum_cols(frame, cols)
            by_key = dict(zip(keys, vals))
            for ck, val in by_key.items():
                k = (ck, grp_key)
                if k in rows:
                    rows[k][out_col] = (None if pd.isna(val) else float(val))

    out = pd.DataFrame(list(rows.values()))
    # Keep every All-Students row; drop subgroup rows that are entirely null.
    keep = (out["GROUP_DIM"] == "total") | out[metric_cols].notna().any(axis=1)
    out = out[keep].copy()
    cols = ["RELEASE", "LEAID", "SCHID", "SCHOOL_NAME", "GROUP", "GROUP_DIM"] + metric_cols
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Course offerings
# ---------------------------------------------------------------------------

def build_offerings(release_dir: Path) -> pd.DataFrame:
    ap = filter_lynn(_read_csv(release_dir, "SCH/Advanced Placement.csv"))
    ib = filter_lynn(_read_csv(release_dir, "SCH/International Baccalaureate.csv"))
    calc = filter_lynn(_read_csv(release_dir, "SCH/Calculus.csv"))
    phys = filter_lynn(_read_csv(release_dir, "SCH/Physics.csv"))
    geom = filter_lynn(_read_csv(release_dir, "SCH/Geometry.csv"))
    alg2 = filter_lynn(_read_csv(release_dir, "SCH/Algebra II.csv"))

    if ap.empty:
        return empty_schema("offerings")

    out = ap[["COMBOKEY", "SCHID", "SCH_NAME"]].copy()
    out.columns = ["COMBOKEY", "SCHID", "SCHOOL_NAME"]
    out.insert(0, "RELEASE", RELEASE_LABEL)
    out.insert(1, "LEAID", LYNN_LEAID)

    def joined(src: pd.DataFrame, valseries: pd.Series) -> pd.Series:
        """Map a per-school computed series onto `out` by COMBOKEY (SCHID is
        formatted inconsistently across topical files; COMBOKEY is stable)."""
        return out["COMBOKEY"].map(dict(zip(src["COMBOKEY"].values, valseries.values)))

    out["AP_OFFERED"] = joined(ap, _ind_yesno(ap["SCH_APENR_IND"]))
    out["AP_COURSE_COUNT"] = joined(ap, _num(ap["SCH_APCOURSES"]))
    out["AP_ENROLLED_TOTAL"] = joined(ap, _sum_cols(ap, ["TOT_APENR_M", "TOT_APENR_F"]))
    out["IB_OFFERED"] = (joined(ib, _ind_yesno(ib["SCH_IBENR_IND"]))
                         if not ib.empty else pd.NA)
    out["CALC_OFFERED"] = (joined(calc, _count_offered(calc["SCH_MATHCLASSES_CALC"]))
                           if not calc.empty else pd.NA)
    out["PHYSICS_OFFERED"] = (joined(phys, _count_offered(phys["SCH_SCICLASSES_PHYS"]))
                              if not phys.empty else pd.NA)
    out["GEO_OFFERED"] = (joined(geom, _count_offered(geom["SCH_MATHCLASSES_GEOM"]))
                          if not geom.empty else pd.NA)
    out["ALGEBRA_II_OFFERED"] = (joined(alg2, _count_offered(alg2["SCH_MATHCLASSES_ALG2"]))
                                 if not alg2.empty else pd.NA)

    cols = ["RELEASE", "LEAID", "SCHID", "SCHOOL_NAME", "AP_OFFERED",
            "AP_COURSE_COUNT", "AP_ENROLLED_TOTAL", "IB_OFFERED", "CALC_OFFERED",
            "PHYSICS_OFFERED", "GEO_OFFERED", "ALGEBRA_II_OFFERED"]
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Support staffing
# ---------------------------------------------------------------------------

def build_staffing(release_dir: Path) -> pd.DataFrame:
    sup = filter_lynn(_read_csv(release_dir, "SCH/School Support.csv"))
    enr = filter_lynn(_read_csv(release_dir, "SCH/Enrollment.csv"))

    if sup.empty:
        return empty_schema("staffing")

    out = sup[["COMBOKEY", "SCHID", "SCH_NAME"]].copy()
    out.columns = ["COMBOKEY", "SCHID", "SCHOOL_NAME"]
    out.insert(0, "RELEASE", RELEASE_LABEL)
    out.insert(1, "LEAID", LYNN_LEAID)

    def col(name: str) -> pd.Series:
        # Join on COMBOKEY — SCHID padding differs across topical files.
        return out["COMBOKEY"].map(dict(zip(sup["COMBOKEY"].values, _num(sup[name]).values)))

    out["COUNSELOR_FTE"] = col("SCH_FTECOUNSELORS")
    out["NURSE_FTE"] = col("SCH_FTESERVICES_NUR")
    out["SOCIAL_WORKER_FTE"] = col("SCH_FTESERVICES_SOC")
    out["PSYCHOLOGIST_FTE"] = col("SCH_FTESERVICES_PSY")
    out["LAW_ENFORCEMENT_FTE"] = col("SCH_FTESECURITY_LEO")
    out["TEACHER_FTE"] = col("SCH_FTETEACH_TOT")
    if not enr.empty:
        tot = _sum_cols(enr, ["TOT_ENR_M", "TOT_ENR_F", "TOT_ENR_X"])
        out["STUDENT_ENROLLMENT"] = out["COMBOKEY"].map(
            dict(zip(enr["COMBOKEY"].values, tot.values)))
    else:
        out["STUDENT_ENROLLMENT"] = pd.NA

    cols = ["RELEASE", "LEAID", "SCHID", "SCHOOL_NAME", "COUNSELOR_FTE",
            "NURSE_FTE", "SOCIAL_WORKER_FTE", "PSYCHOLOGIST_FTE",
            "LAW_ENFORCEMENT_FTE", "TEACHER_FTE", "STUDENT_ENROLLMENT"]
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Schema (unchanged shapes — the dashboard reads these column sets)
# ---------------------------------------------------------------------------

def empty_schema(kind: str) -> pd.DataFrame:
    """Schema-correct empty DF for each output, so the dashboard can read it."""
    if kind == "discipline":
        return pd.DataFrame(columns=[
            "RELEASE", "LEAID", "SCHID", "SCHOOL_NAME", "GROUP", "GROUP_DIM",
            "ISS_COUNT", "OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT",
            "EXPULSION_COUNT", "ARREST_COUNT", "LE_REFERRAL_COUNT",
            "RESTRAINT_PHYSICAL", "SECLUSION_COUNT",
        ])
    if kind == "offerings":
        return pd.DataFrame(columns=[
            "RELEASE", "LEAID", "SCHID", "SCHOOL_NAME",
            "AP_OFFERED", "AP_COURSE_COUNT", "AP_ENROLLED_TOTAL",
            "IB_OFFERED", "CALC_OFFERED", "PHYSICS_OFFERED",
            "GEO_OFFERED", "ALGEBRA_II_OFFERED",
        ])
    if kind == "staffing":
        return pd.DataFrame(columns=[
            "RELEASE", "LEAID", "SCHID", "SCHOOL_NAME",
            "COUNSELOR_FTE", "NURSE_FTE", "SOCIAL_WORKER_FTE",
            "PSYCHOLOGIST_FTE", "LAW_ENFORCEMENT_FTE",
            "TEACHER_FTE", "STUDENT_ENROLLMENT",
        ])
    raise ValueError(kind)


def _attach_lynn_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Prepend the Lynn DESE district code/name so these join to data/processed."""
    df = df.copy()
    df.insert(0, "DIST_CODE", LYNN_DISTRICT_CODE)
    df.insert(1, "DIST_NAME", LYNN_DISTRICT_NAME)
    return df


def main() -> int:
    print("CRDC ingest (federal Civil Rights Data Collection)")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    zp = download_zip()
    if zp is None:
        zp = find_local_archive()
        if zp is not None:
            print(f"  Using manually-dropped archive: {zp}")

    discipline = empty_schema("discipline")
    offerings = empty_schema("offerings")
    staffing = empty_schema("staffing")

    if zp is not None and zp.exists() and zp.stat().st_size > 10_000_000:
        try:
            rd = extract_zip(zp)
            print(f"  Extracted -> {rd}")
            discipline = build_discipline(rd)
            offerings = build_offerings(rd)
            staffing = build_staffing(rd)
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] parse failed ({exc}); writing schema-valid empties.")
    else:
        print("  No CRDC archive available.\n"
              f"  -> Download the {RELEASE} ZIP from\n       {BULK_URL}\n"
              f"     and place it in {CRDC_RAW} (any *.zip), then re-run.\n"
              "     See data/raw/crdc/README.md. Writing schema-valid empties.")

    discipline = _attach_lynn_codes(discipline)
    offerings = _attach_lynn_codes(offerings)
    staffing = _attach_lynn_codes(staffing)

    discipline.to_parquet(PROCESSED_DIR / "crdc_discipline.parquet", index=False)
    offerings.to_parquet(PROCESSED_DIR / "crdc_offerings.parquet", index=False)
    staffing.to_parquet(PROCESSED_DIR / "crdc_staffing.parquet", index=False)

    def _has_lehs(df: pd.DataFrame) -> str:
        if df.empty or "SCHOOL_NAME" not in df.columns:
            return "n/a"
        names = df["SCHOOL_NAME"].astype(str).str.lower()
        return "yes" if names.str.contains("english").any() else "NO"

    for name, df in (("crdc_discipline", discipline), ("crdc_offerings", offerings),
                     ("crdc_staffing", staffing)):
        print(f"  Wrote {name}.parquet ({len(df):,} rows; "
              f"Lynn={'yes' if not df.empty else 'NO'}, LEHS={_has_lehs(df)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
