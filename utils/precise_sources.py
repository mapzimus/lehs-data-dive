"""
Precise district metrics pulled straight from MA DESE's Socrata **SODA JSON API**
(``/resource/{id}.json`` on ``educationtocareer.data.mass.gov``), bypassing the
rounded CSV bulk export.

Why this module exists
----------------------
``scripts/01_download_e2c.py`` downloads Socrata **CSV bulk exports**
(``/api/views/{id}/rows.csv``), which apply each column's *display formatting*.
For DESE's AP and staffing datasets the percent columns are formatted to the
nearest 10%, so the values baked into ``ma_academic_districts.geojson`` collapse
to a handful of bins (``staff_white_pct`` → 7 distinct values statewide;
``ap_pct_3plus`` → ≤10 per year). The **SODA JSON resource API** returns the very
same datasets at full precision. Proven head-to-head on the retention dataset
``52c5-e56a``: CSV export ``RETND_PCT=0.9`` vs SODA ``retnd_pct=0.911``. This is
the identical root cause + fix the atlas already shipped for
``teacher_retention_pct`` (``ma-education-atlas/scripts/fetch_educator_detail2.py``).

Both fetchers key on the zero-padded 8-char ``DIST_CODE`` used throughout the
pipeline and **fail soft** (return an empty DataFrame) on any network/parse
error, so a full rebuild degrades gracefully exactly like the build script's
existing ``.exists()`` guards.

Datasets (verified 2026-06-05 against live SODA):
  - ``787a-3wen``  Advanced Placement (AP) Performance        → ap_pct_3plus*
  - ``fz9c-2g33``  Total Educators … by Race/Ethnicity         → staff_*_pct
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import E2C_DOMAIN  # noqa: E402

AP_DATASET = "787a-3wen"
STAFF_RACE_DATASET = "fz9c-2g33"

_UA = {"User-Agent": "lehs-data-dive/1.0 (precise_sources; github.com/mapzimus/lehs-data-dive)"}

# DESE STU_GRP label -> short group code baked into `{metric}__{code}` columns.
# Mirrors GROUP_CODE_MAP in scripts/11_build_lynn_geo.py (keep the two in sync).
GROUP_CODE_MAP = {
    "Hispanic or Latino":          "hl",
    "Black or African American":   "baa",
    "Asian":                       "as",
    "White":                       "wh",
    "English Learners":            "ell",
    "English Learner":             "ell",
    "Former English Learners":     "fmrell",
    "Low Income":                  "li",
    "Students with Disabilities":  "swd",
    "High Needs":                  "hn",
}

# Staff race_eth value (as published in fz9c-2g33) -> output column name.
STAFF_RACE_COLS = {
    "White":            "staff_white_pct",
    "Hispanic/Latino":  "staff_hispanic_pct",
    "Afr. Amer./Black": "staff_black_pct",
}


def soda(dataset: str, params: dict) -> list[dict]:
    """GET one page of a Socrata SODA JSON resource. Returns a list of row dicts.

    Uses the JSON resource endpoint (``/resource/{id}.json``), which returns raw
    full-precision values — unlike the CSV bulk export that rounds percent
    columns to their display format.
    """
    url = f"https://{E2C_DOMAIN}/resource/{dataset}.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def soda_all(dataset: str, params: dict, page: int = 50000) -> list[dict]:
    """Fetch every row, paging on ``$offset``. Requires a stable ``$order`` in
    ``params`` so offset paging neither repeats nor skips rows."""
    rows: list[dict] = []
    offset = 0
    while True:
        p = dict(params, **{"$limit": str(page), "$offset": str(offset)})
        chunk = soda(dataset, p)
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        offset += page


def _zfill8(code) -> str:
    """DESE codes are sometimes un-padded / float-ish; the geojson key is 8-char."""
    return str(code).split(".")[0].zfill(8)


def _to_frac(value):
    """Coerce to a 0-1 fraction, or None. Guards percent-style values (88.1→0.881)."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f < 0:
        return None
    return f / 100.0 if f > 1.0 else f


def fetch_precise_ap() -> pd.DataFrame:
    """District AP %-scoring-3+ at full precision, keyed by ``DIST_CODE``.

    Returns one wide frame with columns:
      - ``ap_pct_3plus``              base = latest year, All Students
      - ``ap_pct_3plus__{YYYY}``      All Students, one column per year (2007-2025)
      - ``ap_pct_3plus__{group}``     latest year per student group (GROUP_CODE_MAP)

    The district grand-total row is ``org_type='District' AND
    subj_cat='All Subjects' AND subj='All Subjects'`` — per-exam rows roll up to
    ``subj='All Subjects'``, and schools share their district's ``dist_code`` so
    ``org_type='District'`` isolates the single district aggregate. ``pct_3_5`` is
    already a 0-1 fraction. Empty frame on any failure (build fails soft).
    """
    try:
        rows = soda_all(AP_DATASET, {
            "$select": "dist_code,sy,stu_grp,pct_3_5",
            "$where": "org_type='District' AND subj_cat='All Subjects' AND subj='All Subjects'",
            "$order": "dist_code,sy,stu_grp",
        })
    except Exception as exc:  # noqa: BLE001 — fail soft like the build's .exists() guards
        print(f"  [!] fetch_precise_ap: SODA fetch failed ({exc}); precise AP skipped")
        return pd.DataFrame()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["DIST_CODE"] = df["dist_code"].map(_zfill8)
    df["sy"] = pd.to_numeric(df["sy"], errors="coerce").astype("Int64")
    df["val"] = pd.to_numeric(df["pct_3_5"].map(_to_frac), errors="coerce").round(4)
    df = df.dropna(subset=["sy"])

    allstu = df[df["stu_grp"] == "All Students"].dropna(subset=["val"])
    if allstu.empty:
        return pd.DataFrame()

    # base = each district's LATEST available All-Students year (matches the
    # pipeline's `sort_values("SY").groupby("DIST_CODE").tail(1)` semantics and the
    # audit's "base == latest __YYYY" — a district whose AP data ends before the
    # global latest year keeps its own most-recent value rather than going null).
    base = (allstu.sort_values("sy").groupby("DIST_CODE").tail(1)[["DIST_CODE", "val"]]
            .rename(columns={"val": "ap_pct_3plus"}))

    yk = allstu.pivot_table(index="DIST_CODE", columns="sy", values="val", aggfunc="first")
    yk.columns = [f"ap_pct_3plus__{int(c)}" for c in yk.columns]
    yk = yk.reset_index()

    out = base.merge(yk, on="DIST_CODE", how="outer")

    grp = df[df["stu_grp"].isin(GROUP_CODE_MAP)].dropna(subset=["val"]).copy()
    if not grp.empty:
        grp = grp.sort_values("sy").groupby(["DIST_CODE", "stu_grp"]).tail(1)
        grp["code"] = grp["stu_grp"].map(GROUP_CODE_MAP)
        gk = grp.pivot_table(index="DIST_CODE", columns="code", values="val", aggfunc="first")
        gk.columns = [f"ap_pct_3plus__{c}" for c in gk.columns]
        out = out.merge(gk.reset_index(), on="DIST_CODE", how="outer")

    return out


def fetch_precise_staff_race() -> pd.DataFrame:
    """All-staff race shares at full precision, **headcount-weighted across the
    five ``job_class_grp`` values**, keyed by ``DIST_CODE``. Latest published
    year (currently SY2023 — the educator race breakdown lags).

    Columns: ``staff_white_pct``, ``staff_hispanic_pct``, ``staff_black_pct``.

    Per district: numerator = Σ ``educators_cnt`` for the race across the 5 job
    classes; denominator = Σ ``educators_cnt`` for ``race_eth='All Educators'``
    across the same classes (the all-staff headcount). Empty frame on failure.
    """
    try:
        latest_resp = soda(STAFF_RACE_DATASET, {"$select": "max(sy) as mx"})
        latest = latest_resp[0].get("mx") if latest_resp else None
        if not latest:
            return pd.DataFrame()
        wanted = list(STAFF_RACE_COLS) + ["All Educators"]
        race_in = ",".join("'" + r.replace("'", "''") + "'" for r in wanted)
        rows = soda_all(STAFF_RACE_DATASET, {
            "$select": "dist_code,job_class_grp,race_eth,educators_cnt",
            "$where": f"sy='{latest}' AND race_eth in({race_in})",
            "$order": "dist_code,job_class_grp,race_eth",
        })
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] fetch_precise_staff_race: SODA fetch failed ({exc}); precise staff race skipped")
        return pd.DataFrame()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["DIST_CODE"] = df["dist_code"].map(_zfill8)
    df["cnt"] = pd.to_numeric(df["educators_cnt"], errors="coerce")
    df = df.dropna(subset=["cnt"])

    # Sum headcounts across the 5 job classes → district × race matrix.
    agg = df.groupby(["DIST_CODE", "race_eth"])["cnt"].sum().unstack(fill_value=0.0)
    if "All Educators" not in agg.columns:
        return pd.DataFrame()
    total = agg["All Educators"]

    out = pd.DataFrame({"DIST_CODE": agg.index})
    for race, col in STAFF_RACE_COLS.items():
        if race in agg.columns:
            share = (agg[race] / total).where(total > 0).round(4)
            out[col] = share.values
    return out.reset_index(drop=True)
