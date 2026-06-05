"""
Backfill the six regional *secondary* school districts that
``build_ma_academic_districts()`` (in 11_build_lynn_geo.py) silently drops.

Why they're dropped
-------------------
The academic-district polygons are synthesised by a *town-dissolve*: each town is
assigned to the single district that operates the most public schools in it (its
"dominant" district), and towns are dissolved by that code. A regional 7-12 / 9-12
district shares every one of its member towns with that town's own K-8 elementary
district, which always has more schools — so the regional wins **no** town, gets
**no** polygon, and vanishes from ``ma_academic_districts.geojson`` and therefore
from every DESE side-join (each fetcher filters to the geojson's DIST_CODE set).

What this script does
---------------------
A one-time materialisation that avoids re-pulling the full ~400 MB E2C CSV set:
  1. Fetches *only these six districts'* rows (plus a control district that is
     already baked) from the DESE Education-to-Career Socrata hub.
  2. Runs the SAME ``_build_district_metrics_table()`` the main builder uses, so
     the baked-column schema is identical to the other 274 districts.
  3. Dissolves each district's member-town polygons (MassGIS TOWNSSURVEY) for
     geometry — the union of member towns, exactly as a regional district's
     footprint is defined.
  4. Verifies the metric pipeline against the control district's already-baked
     values, then writes the six features to ``data/processed/_regional_additions.json``
     for review.  (append_regional_districts.py does the actual splice.)

The permanent fix lives in ``build_ma_academic_districts()``; this script exists
only so the live map picks up the six districts now, without a full refresh.

Run:  python scripts/add_regional_districts.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
PROCESSED = REPO / "data" / "processed"
TMP = REPO / "data" / "_regional_tmp"

DOMAIN = "educationtocareer.data.mass.gov"
UA = {"User-Agent": "lehs-data-dive/0.1 (regional-district backfill)"}

# DESE org_code (8-char) -> (official DESE name, member towns as they appear in
# the TOWNSSURVEY_POLYM `TOWN` column). Member towns verified against the live
# t8td-gens enrollment feed and DESE district directories; see scripts/analysis/
# regional_hs_gap.md.
MEMBERS: dict[str, tuple[str, list[str]]] = {
    "06400000": ("Concord-Carlisle",   ["CONCORD", "CARLISLE"]),
    "06950000": ("Lincoln-Sudbury",    ["LINCOLN", "SUDBURY"]),
    "06600000": ("Nauset",             ["BREWSTER", "EASTHAM", "ORLEANS", "WELLFLEET"]),
    "06900000": ("King Philip",        ["NORFOLK", "WRENTHAM", "PLAINVILLE"]),
    "07050000": ("Masconomet",         ["BOXFORD", "TOPSFIELD", "MIDDLETON"]),
    "07300000": ("Northboro-Southboro", ["NORTHBOROUGH", "SOUTHBOROUGH"]),
    # Added 2026-06-05: spliced into the geojson by PR #50 with only a partial
    # property set (~41 props: demographics + grad_4yr + mcas_g10), missing
    # per_pupil/dropout/grad_5yr/ap/masscore/staff/stu_tchr_ratio/postsec + all
    # subgroup breakdowns. Re-running through the full pipeline backfills it to
    # parity with the other regionals. Member towns: Somerset + Berkley (9-12).
    "07630000": ("Somerset Berkley",   ["SOMERSET", "BERKLEY"]),
}

# Friendlier display/search alias for regionals whose DESE name isn't their
# common name (mirrors DISPLAY_OVERRIDES in build_ma_academic_districts()).
DISPLAY_OVERRIDES = {"07300000": "Northboro-Southboro (Algonquin)"}

# A district already present in the baked geojson — used to prove this script's
# metric pipeline reproduces the production builder's values.
CONTROL_CODE = "06550000"  # Dover-Sherborn

# E2C Socrata dataset ids consumed by _build_district_metrics_table().
# (Resolved via the Socrata catalog; graduation/mcas/enrollment confirmed against
# the atlas fetchers + builder manifest.)
DATASETS: dict[str, str] = {
    "enrollment_demographics": "t8td-gens",
    "graduation_rates":        "n2xa-p822",
    "mcas_achievement":        "i9w6-niyt",
    "student_attendance":      "ak6h-9k7x",
    "ap_performance":          "787a-3wen",
    "masscore_completion":     "a9ye-ac8e",
    "district_expenditures":   "er3w-dyti",
    "staffing_race_gender":    "j5ue-xkfn",
    "teacher_data":            "4684-cw3t",
    "plans_of_graduates":      "37px-xsir",
    "staff_retention":         "52c5-e56a",
}


def soda(dataset: str, params: dict) -> list[dict]:
    url = f"https://{DOMAIN}/resource/{dataset}.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_district_rows(dataset: str, codes: list[str]) -> pd.DataFrame:
    """All rows for the given DIST_CODEs (any org_type / year / group), with
    column names upper-cased so they match what the builder's CSV reader expects.
    Paginates defensively."""
    inlist = "(" + ",".join("'" + c + "'" for c in codes) + ")"
    rows: list[dict] = []
    offset, page = 0, 50000
    while True:
        batch = soda(dataset, {
            "$where": f"dist_code in {inlist}",
            "$limit": page,
            "$offset": offset,
            "$order": ":id",
        })
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    df = pd.DataFrame(rows)
    df.columns = [c.upper() for c in df.columns]
    return df


def load_builder_module():
    """Import 11_build_lynn_geo.py (name starts with a digit -> importlib)."""
    path = SCRIPTS / "11_build_lynn_geo.py"
    spec = importlib.util.spec_from_file_location("build_lynn_geo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dissolve_member_towns(mod, codes: list[str]) -> dict[str, object]:
    """Union each district's member-town polygons -> one geometry per code,
    simplified for the web exactly as the builder does for every other layer."""
    towns = gpd.read_file(mod.TOWNS_SHP).to_crs(mod.WEB_CRS)
    towns["TOWN_U"] = towns["TOWN"].str.upper()
    geom = {}
    rows = []
    for code in codes:
        members = [m.upper() for m in MEMBERS[code][1]]
        sub = towns[towns["TOWN_U"].isin(members)]
        missing = set(members) - set(sub["TOWN_U"])
        if missing:
            raise SystemExit(f"[X] {code}: member towns not found in TOWNSSURVEY: {missing}")
        rows.append({"DIST_CODE": code, "geometry": sub.geometry.union_all()})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=mod.WEB_CRS)
    gdf = mod.simplify_for_web(gdf)
    return {r.DIST_CODE: r.geometry for r in gdf.itertuples()}


def main() -> int:
    codes = list(MEMBERS) + [CONTROL_CODE]

    # 1. Fetch 6-district (+control) subsets and stage them as the CSVs the
    #    builder reads, under a temp RAW_DIR.
    e2c_tmp = TMP / "e2c_hub"
    if TMP.exists():
        shutil.rmtree(TMP)
    e2c_tmp.mkdir(parents=True)
    print("Fetching DESE subsets for", len(codes), "districts ...")
    for slug, ds in DATASETS.items():
        df = fetch_district_rows(ds, codes)
        df.to_csv(e2c_tmp / f"{slug}.csv", index=False)
        print(f"  {slug:26s} {ds:10s} {len(df):>6} rows  cols={len(df.columns)}")

    # 2. Run the real metric builder against the staged subset.
    mod = load_builder_module()
    mod.RAW_DIR = TMP                      # _build_district_metrics_table reads RAW_DIR/e2c_hub
    metrics = mod._build_district_metrics_table()
    metrics["DIST_CODE"] = metrics["DIST_CODE"].astype(str).str.zfill(8)
    metrics = metrics[metrics["DIST_CODE"].isin(codes)].copy()
    print(f"\nBuilt metric table: {len(metrics)} rows, {len(metrics.columns)} columns")

    # 3. Verify the pipeline against the control district already in the geojson.
    baked = json.loads((PROCESSED / "ma_academic_districts.geojson").read_text(encoding="utf-8"))
    baked_props = {f["properties"]["DIST_CODE"]: f["properties"]
                   for f in baked["features"]}
    ctrl_baked = baked_props.get(CONTROL_CODE, {})
    ctrl_new = metrics[metrics["DIST_CODE"] == CONTROL_CODE]
    print(f"\n=== CONTROL {CONTROL_CODE} ({MEMBERS.get(CONTROL_CODE, ('Dover-Sherborn',))[0]}) "
          f"this-pipeline vs already-baked ===")
    check_cols = ["TOTAL_CNT", "EL_PCT", "grad_4yr", "grad_5yr", "mcas_g10_ela_me",
                  "mcas_g10_math_me", "per_pupil", "ap_pct_3plus", "stu_tchr_ratio"]
    ok = True
    if not ctrl_new.empty:
        row = ctrl_new.iloc[0]
        for c in check_cols:
            new = row.get(c)
            old = ctrl_baked.get(c)
            new = None if pd.isna(new) else round(float(new), 4)
            old = None if old is None else round(float(old), 4)
            tol = (new is None and old is None) or (
                new is not None and old is not None and abs(new - old) <= max(0.02, abs(old) * 0.05))
            ok = ok and tol
            print(f"    {c:20s} new={str(new):>12}  baked={str(old):>12}  {'OK' if tol else '*** DIFF'}")
    print("  control check:", "PASS" if ok else "MISMATCH (review before appending)")

    # 4. Geometry: member-town dissolve for the six (not the control).
    geom = dissolve_member_towns(mod, list(MEMBERS))

    # 5. Assemble features matching the builder's academic keep-set.
    keep_a = {"DIST_CODE", "DIST_NAME", "dist_display", "is_lynn",
              "TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT", "HL_PCT", "BAA_PCT",
              "AS_PCT", "WH_PCT", "SWD_PCT", "FLNE_PCT", "FE_PCT",
              "mcas_g10_ela_me", "mcas_g10_math_me", "mcas_g10_sci_me",
              "mcas_g38_ela_me", "mcas_g38_math_me", "mcas_g38_sci_me",
              "grad_4yr", "grad_5yr", "dropout_pct", "chronic_absent_pct",
              "attendance_rate", "masscore_pct", "ap_pct_3plus",
              "pct_any_college", "pct_4yr_college", "pct_2yr_college",
              "pct_work_after_hs", "pct_military",
              "per_pupil", "per_pupil_teachers", "per_pupil_admin",
              "per_pupil_pupil_services",
              "staff_white_pct", "staff_hispanic_pct", "staff_black_pct",
              "stu_tchr_ratio", "teacher_experienced_pct",
              "teacher_infield_pct", "teacher_retention_pct"}

    def clean(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, float):
            return round(v, 6)
        return v

    features = []
    for code, (name, _) in MEMBERS.items():
        mrow = metrics[metrics["DIST_CODE"] == code]
        if mrow.empty:
            raise SystemExit(f"[X] no metric row for {code}")
        m = mrow.iloc[0].to_dict()
        m["DIST_NAME"] = name
        m["dist_display"] = DISPLAY_OVERRIDES.get(code, name)
        m["is_lynn"] = False
        cols = [c for c in m if c in keep_a or ("__" in str(c))]
        props = {c: clean(m[c]) for c in cols}
        props["DIST_CODE"] = code  # ensure zero-padded, not coerced
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": gpd.GeoSeries([geom[code]]).__geo_interface__["features"][0]["geometry"],
        })
        print(f"  built {code} {name:22s} props={len(props)} "
              f"enroll={props.get('TOTAL_CNT')} grad4={props.get('grad_4yr')} pp={props.get('per_pupil')}")

    out = PROCESSED / "_regional_additions.json"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=1))
    print(f"\nWrote {len(features)} features -> {out.relative_to(REPO)}")
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
