"""
Process the xlsx files scraped from DESE Profiles statereport into the
processed-data parquet layer.

Each statereport xlsx has the same shape:
  row 0 = report title (e.g. "2025 Accountability Report")
  row 1 = column headers
  row 2+ = data, one row per district or school

This script normalizes that into tidy parquet files filtered to our peer
set (Lynn district + 26 Gateway-city districts, plus their schools).

Run after scripts/02_download_dese_profiles.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import LYNN_DISTRICT_CODE, PROCESSED_DIR, RAW_DIR  # noqa: E402

DESE_PROFILES_RAW = RAW_DIR / "dese_profiles"
ACCOUNTABILITY_RAW = RAW_DIR / "accountability"

# Detailed-accountability indicator catalog. Each entry maps the column-header
# prefix DESE uses in the criterion-referenced-percentage workbook to a clean
# indicator name, its accountability category, and the unit its value carries.
# Order here is the order the indicators appear on the report.
_INDICATOR_CATALOG: list[tuple[str, str, str, str]] = [
    ("English language arts achievement", "ELA Achievement",     "Achievement",            "scaled_score"),
    ("Mathematics achievement",           "Math Achievement",    "Achievement",            "scaled_score"),
    ("Science achievement",               "Science Achievement", "Achievement",            "scaled_score"),
    ("English language arts growth",      "ELA Growth",          "Growth",                 "sgp"),
    ("Mathematics growth",                "Math Growth",         "Growth",                 "sgp"),
    ("Four-year cohort graduation rate",  "4-Year Graduation",   "High school completion", "pct"),
    ("Extended engagement rate",          "Extended Engagement", "High school completion", "pct"),
    ("Annual dropout rate",               "Annual Dropout",      "High school completion", "pct"),
    ("Progress toward attaining English language proficiency",
                                          "ELP Progress",        "EL progress",            "pct"),
    ("Chronic absenteeism",               "Chronic Absenteeism", "Additional indicators",  "pct"),
    ("Advanced coursework completion",    "Advanced Coursework", "Additional indicators",  "pct"),
]

# Case-SENSITIVE: matches the "... - High school:" / "...-High school:" /
# "... - High School:" column family but NOT "... - Non-high school:" (lowercase
# 'non'). Used to pull only the high-school columns from the MSHS sheet, which
# interleaves a non-high-school family for K-12 schools.
_HS_FAMILY_RE = re.compile(r"-\s*High [Ss]chool\s*:")

# accountability-targets-{year}.xlsx, sheet "Targets and Increments". One entry
# per scored indicator (no Growth/SGP targets exist). Column names are EXACT —
# note the double space in the dropout reduction header and the trailing space
# in the ELP "% Making Progress Target " headers. `direction` is +1 when higher
# is better, -1 for dropout/chronic-absenteeism (their increment columns are
# labeled "Reduction"). `mode`: "peryear" indicators (achievement) carry a
# separate increment column per year; "single" indicators apply one annual
# increment 2025→2027.
_TARGETS_CATALOG: list[dict] = [
    dict(indicator="ELA Achievement", unit="scaled_score", direction=1, mode="peryear",
         latest_target="2025 ELA Achievement Target", latest_year=2025,
         incr_plus1="2026 ELA Increment", incr_plus2="2027 ELA Increment",
         path="2025 ELA Path", n="2024 ELA # Included",
         baseline="2024 ELA Achievement Baseline", baseline_year=2024),
    dict(indicator="Math Achievement", unit="scaled_score", direction=1, mode="peryear",
         latest_target="2025 Math Achievement Target", latest_year=2025,
         incr_plus1="2026 Math Increment", incr_plus2="2027 Math Increment",
         path="2025 Math Path", n="2024 Math # Included",
         baseline="2024 Math Achievement Baseline", baseline_year=2024),
    dict(indicator="Science Achievement", unit="scaled_score", direction=1, mode="peryear",
         latest_target="2025 Science Achievement Target", latest_year=2025,
         incr_plus1="2026 Science Increment", incr_plus2="2027 Science Increment",
         path="2025 Science Path", n="2024 Science # Included",
         baseline="2024 Science Achievement Baseline", baseline_year=2024),
    dict(indicator="4-Year Graduation", unit="pct", direction=1, mode="single",
         latest_target="2024 4-Yr Grad Rate Target (%)", latest_year=2024,
         incr_single="Annual 4-Yr Grad Rate Increment (%) (2024-2026)",
         path=None, n="2023 4-Yr Grad Rate # Included",
         baseline="2023 4-Yr Grad Rate Baseline (%)", baseline_year=2023),
    dict(indicator="Extended Engagement", unit="pct", direction=1, mode="single",
         latest_target="2023 Extended Engagement Rate Target (%)", latest_year=2023,
         incr_single="Annual Extended Engagement Rate Increment (%) (2023-2025)",
         path=None, n="2022 Extended Engagement Rate # Included",
         baseline="2022 Extended Engagement Rate Baseline (%)", baseline_year=2022),
    dict(indicator="Annual Dropout", unit="pct", direction=-1, mode="single",
         latest_target="2024 Annual Dropout Rate Target (%)", latest_year=2024,
         incr_single="Annual  Dropout Rate Reduction (%)",   # NOTE: double space
         path=None, n="2023 Annual Dropout Rate # Included",
         baseline="2023 Annual Dropout Rate Baseline (%)", baseline_year=2023),
    dict(indicator="Advanced Coursework", unit="pct", direction=1, mode="single",
         latest_target="2025 Advanced Coursework Completion Rate Target (%)", latest_year=2025,
         incr_single="Annual Advanced Coursework Completion Rate Increment (%) (2025-2027)",
         path=None, n="2024 Advanced Coursework Completion Rate # Included",
         baseline="2024 Advanced Coursework Completion Rate Baseline (%)", baseline_year=2024),
    dict(indicator="ELP Progress", unit="pct", direction=1, mode="single",
         latest_target="2025 % Making Progress Target ", latest_year=2025,  # trailing space
         incr_single="Annual % Making Progress Increment (2025-2027)",
         path=None, n="2024 ACCESS # Included",
         baseline="2024 % Making Progress Baseline", baseline_year=2024),
    dict(indicator="Chronic Absenteeism", unit="pct", direction=-1, mode="single",
         latest_target="2025 Chronic Absenteeism Rate Target (%)", latest_year=2025,
         incr_single="Annual Chronic Absenteeism Rate Reduction (%) (2025-2027)",
         path=None, n="2024 Chronic Absenteeism Rate # Included",
         baseline="2024 Chronic Absenteeism Rate Baseline (%)", baseline_year=2024),
]

# {school,student-group}-percentile-{year}.xlsx, sheet "HS " (trailing space).
# 143 positional columns: 0-7 ID block, three 44-col year blocks (base offsets
# below), col 140 weighted mean, 141 school percentile, 142 notes. Within a year
# block, each indicator's value/percentile sit at fixed offsets (verified
# identical across the three blocks).
_PCTL_BLOCKS = {2023: 8, 2024: 52, 2025: 96}
_PCTL_LAYOUT: list[tuple[int, int, str]] = [
    # (value_offset, percentile_offset, INDICATOR)
    (0, 1, "ELA Achievement"),
    (2, 3, "Math Achievement"),
    (4, 5, "Science Achievement"),
    (8, 9, "ELA Growth"),
    (10, 11, "Math Growth"),
    (14, 15, "4-Year Graduation"),
    (16, 17, "Extended Engagement"),
    (18, 19, "Annual Dropout"),
    (22, 23, "ELP Progress"),
    (26, 27, "Chronic Absenteeism"),
    (28, 29, "Advanced Coursework"),
]


def _peer_district_codes() -> set[str]:
    peers_path = PROCESSED_DIR / "_peer_schools.json"
    if not peers_path.exists():
        return {LYNN_DISTRICT_CODE}
    peers = json.loads(peers_path.read_text())
    out = {LYNN_DISTRICT_CODE}
    for info in (peers.get("gateway_main_hs") or {}).values():
        if info.get("district_code"):
            out.add(info["district_code"])
    return out


def _peer_school_codes() -> set[str]:
    peers_path = PROCESSED_DIR / "_peer_schools.json"
    if not peers_path.exists():
        return set()
    peers = json.loads(peers_path.read_text())
    out: set[str] = set()
    # Lynn district schools
    for code in (peers.get("lynn_all_schools") or {}).values():
        out.add(str(code).zfill(8))
    # Gateway main HS
    for info in (peers.get("gateway_main_hs") or {}).values():
        if info.get("school_code"):
            out.add(str(info["school_code"]).zfill(8))
    return out


def _load_statereport_xlsx(path: Path) -> tuple[str, pd.DataFrame]:
    """Read a statereport xlsx. Returns (report_title, dataframe-with-headers)."""
    raw = pd.read_excel(path, header=None, dtype=str)
    title = str(raw.iloc[0, 0]).strip()
    headers = [str(c).strip() for c in raw.iloc[1].tolist()]
    data = raw.iloc[2:].copy()
    data.columns = headers
    data = data.dropna(how="all").reset_index(drop=True)
    return title, data


def process_accountability() -> None:
    """ESSA accountability — district + school level → one parquet, filtered."""
    dist_xlsx = DESE_PROFILES_RAW / "accountability_district.xlsx"
    sch_xlsx = DESE_PROFILES_RAW / "accountability_school.xlsx"
    if not dist_xlsx.exists() or not sch_xlsx.exists():
        print("  [SKIP] accountability — run scripts/02_download_dese_profiles.py first")
        return

    title_d, df_d = _load_statereport_xlsx(dist_xlsx)
    title_s, df_s = _load_statereport_xlsx(sch_xlsx)
    print(f"  district report: {title_d!r}  ({len(df_d):,} rows)")
    print(f"  school   report: {title_s!r}  ({len(df_s):,} rows)")

    # Year inferred from the title — both titles share the year.
    year = "".join(c for c in title_d if c.isdigit())[:4]
    sy_int = int(year) if year else None

    # Normalize district frame
    df_d = df_d.rename(columns={
        "District Name": "ORG_NAME",
        "District Code": "ORG_CODE",
        "Overall Classification": "CLASSIFICATION",
        "Reason for Classification": "REASON",
        "Cumulative Progress Toward Improvement Targets (%)": "PROGRESS_PCT",
    })
    df_d["ORG_TYPE"] = "District"
    df_d["DIST_CODE"] = df_d["ORG_CODE"].astype(str).str.zfill(8)
    df_d["PERCENTILE"] = pd.NA  # not published at district level

    # Normalize school frame
    df_s = df_s.rename(columns={
        "School Name": "ORG_NAME",
        "School Code": "ORG_CODE",
        "Overall Classification": "CLASSIFICATION",
        "Reason for Classification": "REASON",
        "Accountability Percentile (1-99)": "PERCENTILE",
        "Cumulative Progress Toward Improvement Targets (%)": "PROGRESS_PCT",
    })
    df_s["ORG_TYPE"] = "School"
    df_s["ORG_CODE"] = df_s["ORG_CODE"].astype(str).str.zfill(8)
    # School code's first 4 digits are the LEA/district id (DESE convention),
    # then zero-padded to 8.
    df_s["DIST_CODE"] = df_s["ORG_CODE"].str[:4].str.ljust(8, "0")

    # Filter to peer set
    district_codes = _peer_district_codes()
    school_codes = _peer_school_codes()

    df_d_filt = df_d[df_d["DIST_CODE"].isin(district_codes)].copy()
    df_s_filt = df_s[df_s["ORG_CODE"].isin(school_codes)].copy()

    cols = ["ORG_CODE", "ORG_NAME", "ORG_TYPE", "DIST_CODE",
            "CLASSIFICATION", "REASON", "PERCENTILE", "PROGRESS_PCT"]
    combined = pd.concat([df_d_filt[cols], df_s_filt[cols]], ignore_index=True)
    combined["SY"] = sy_int
    combined["PERCENTILE"] = pd.to_numeric(combined["PERCENTILE"], errors="coerce")
    combined["PROGRESS_PCT"] = pd.to_numeric(combined["PROGRESS_PCT"], errors="coerce")

    out_path = PROCESSED_DIR / "accountability.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"  [OK] -> {out_path.name}  ({len(combined):,} rows; "
          f"{len(df_d_filt)} districts + {len(df_s_filt)} schools)")


def _field_after_colon(header: str, prefix: str) -> str:
    """Return the metric field for an indicator column.

    Headers look like '<prefix> - High school: <field>' (capitalization of
    'High school' varies between indicators), so split on the last ': '.
    """
    after = header[len(prefix):]
    return after.split(":", 1)[1].strip() if ":" in after else ""


def _reshape_criterion_sheet(data: pd.DataFrame, headers: list[str],
                             sy: int, keep_codes: set[str],
                             col_filter=None,
                             org_meta_from_sheet: bool = False) -> pd.DataFrame:
    """Wide DESE criterion sheet -> tidy long frame (one row per school×group×indicator).

    `col_filter` (callable header -> bool): when set, an indicator's candidate
    columns are further restricted to those passing the filter. The MSHS sheet
    carries BOTH a "Non-high school:" and a "High school:" column family, so the
    benchmark build passes ``_HS_FAMILY_RE.search`` here to read only the HS
    family (otherwise a prefix like "Mathematics achievement" would also grab the
    NonHS columns and corrupt the value).

    `org_meta_from_sheet`: when True, ORG_TYPE/ORG_NAME come from the sheet's
    own 'School, district, or single-school district' column ("State"/"District"
    /"School") rather than the HS-sheet's state-only hardcode — needed because
    the MSHS sheet holds the statewide row AND district rows.
    """
    data = data.copy()
    data.columns = headers
    data["ORG_CODE"] = data["School code plus group"].astype(str).str[:8].str.zfill(8)
    data["DIST_CODE"] = data["District code"].astype(str).str.zfill(8)
    # Keep our peer schools plus the statewide row (code 00000000) for context.
    # `keep_codes=None` means the caller has already filtered rows (the benchmark
    # build pre-selects state + peer-district rows), so don't re-filter here.
    if keep_codes is not None:
        data = data[data["ORG_CODE"].isin(keep_codes | {"00000000"})].copy()
    if data.empty:
        return pd.DataFrame()

    type_col = "School, district, or single-school district"
    records: list[dict] = []
    for _, row in data.iterrows():
        is_state = row["ORG_CODE"] == "00000000"
        if org_meta_from_sheet:
            org_type = str(row.get(type_col, "")).strip() or "School"
            org_name = ("Massachusetts" if org_type == "State"
                        else (row["District name"] if org_type == "District"
                              else row["School name"]))
        else:
            org_type = "State" if is_state else "School"
            org_name = "Massachusetts" if is_state else row["School name"]
        base = {
            "SY": sy,
            "ORG_CODE": row["ORG_CODE"],
            "ORG_NAME": org_name,
            "ORG_TYPE": org_type,
            "DIST_CODE": row["DIST_CODE"],
            "DIST_NAME": row["District name"],
            "GROUP": row["Group"],
        }
        for prefix, name, category, unit in _INDICATOR_CATALOG:
            cols = [h for h in headers if h.startswith(prefix)]
            if col_filter is not None:
                cols = [h for h in cols if col_filter(h)]
            if not cols:
                continue
            slot: dict = {"prior_year": None, "curr_year": None}
            years: dict[int, object] = {}
            for col in cols:
                field = _field_after_colon(col, prefix)
                fl = field.lower()
                val = row[col]
                if "mean sgp" in fl:
                    slot["CURR_VAL"] = val
                    slot["curr_year"] = sy
                elif re.match(r"^\d{4}\b", field) and ("achievement" in fl or "rate" in fl):
                    years[int(field[:4])] = val
                elif fl.startswith("change"):
                    slot["CHANGE"] = val
                elif fl.startswith("target"):
                    slot["TARGET"] = val
                elif field == "N":
                    slot["N"] = val
                elif fl == "points":
                    slot["POINTS"] = val
                elif fl == "rating":
                    slot["RATING"] = val
                elif fl == "reason":
                    slot["REASON"] = val
            if years:
                ordered = sorted(years)
                slot["PRIOR_VAL"] = years[ordered[0]]
                slot["prior_year"] = ordered[0]
                slot["CURR_VAL"] = years[ordered[-1]]
                slot["curr_year"] = ordered[-1]
            records.append({
                **base,
                "CATEGORY": category,
                "INDICATOR": name,
                "UNIT": unit,
                "PRIOR_YEAR": slot.get("prior_year"),
                "PRIOR_VAL": slot.get("PRIOR_VAL"),
                "CURR_YEAR": slot.get("curr_year"),
                "CURR_VAL": slot.get("CURR_VAL"),
                "CHANGE": slot.get("CHANGE"),
                "TARGET": slot.get("TARGET"),
                "N": slot.get("N"),
                "POINTS": slot.get("POINTS"),
                "RATING": slot.get("RATING"),
                "REASON": slot.get("REASON"),
            })

    out = pd.DataFrame.from_records(records)
    for col in ["PRIOR_VAL", "CURR_VAL", "CHANGE", "TARGET", "N", "POINTS"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    # DESE blanks scaled-score cells for suppressed/ineligible small groups with
    # placeholder integers (e.g. "5"); a real MCAS composite is ~440-560, so null
    # anything implausible rather than charting a fake "5".
    ss = out["UNIT"] == "scaled_score"
    for col in ["PRIOR_VAL", "CURR_VAL"]:
        bad = ss & out[col].notna() & ((out[col] < 400) | (out[col] > 600))
        out.loc[bad, col] = pd.NA
    return out


def process_accountability_indicators() -> None:
    """Detailed per-indicator, per-group accountability data -> one long parquet.

    Source: criterion-referenced-percentage-{year}.xlsx (HS sheet) — the
    machine-readable twin of the report's 'Detailed data for each indicator'
    tab. All school-level aggregate; no student records.
    """
    files = sorted(ACCOUNTABILITY_RAW.glob("criterion-referenced-percentage-*.xlsx"))
    if not files:
        print("  [SKIP] accountability indicators — run "
              "scripts/19_download_accountability_detail.py first")
        return

    keep = _peer_school_codes()
    frames = []
    for path in files:
        m = re.search(r"(\d{4})", path.stem)
        sy = int(m.group(1)) if m else None
        try:
            raw = pd.read_excel(path, sheet_name="HS", header=None, dtype=str)
        except ValueError:
            print(f"  [WARN] {path.name}: no 'HS' sheet, skipping")
            continue
        headers = [str(c).replace("\n", " ").strip() for c in raw.iloc[1].tolist()]
        data = raw.iloc[2:].reset_index(drop=True)
        long = _reshape_criterion_sheet(data, headers, sy, keep)
        if not long.empty:
            frames.append(long)
            print(f"  {path.name}: SY{sy} -> {len(long):,} indicator rows")

    if not frames:
        print("  [SKIP] accountability indicators — nothing matched the peer set")
        return
    combined = pd.concat(frames, ignore_index=True)
    out_path = PROCESSED_DIR / "accountability_indicators.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"  [OK] -> {out_path.name}  ({len(combined):,} rows)")


def _resolve_sheet(xl: pd.ExcelFile, wanted: str) -> str | None:
    """Find a sheet whose name equals `wanted` after stripping whitespace.

    DESE ships several sheets with trailing spaces ('HS ', 'MSHS '), so an exact
    `sheet_name=` lookup raises ValueError — match on the stripped name instead.
    """
    for s in xl.sheet_names:
        if s.strip() == wanted:
            return s
    return None


def process_accountability_benchmarks() -> None:
    """State + peer-district HS-level indicator values -> one parquet.

    Source: criterion-referenced-percentage-{year}.xlsx, **MSHS sheet** — the
    only place the statewide aggregate and full-district rows live (the HS sheet
    we use for schools has neither). Same long schema as
    accountability_indicators, so the page can join/compare directly.
    """
    files = sorted(ACCOUNTABILITY_RAW.glob("criterion-referenced-percentage-*.xlsx"))
    if not files:
        print("  [SKIP] accountability benchmarks — run scripts/19 first")
        return
    peer_dists = _peer_district_codes()
    frames = []
    for path in files:
        m = re.search(r"(\d{4})", path.stem)
        sy = int(m.group(1)) if m else None
        xl = pd.ExcelFile(path)
        sheet = _resolve_sheet(xl, "MSHS")
        if sheet is None:
            print(f"  [WARN] {path.name}: no MSHS sheet, skipping")
            continue
        raw = xl.parse(sheet, header=None, dtype=str)
        headers = [str(c).replace("\n", " ").strip() for c in raw.iloc[1].tolist()]
        n_hs = sum(1 for h in headers if _HS_FAMILY_RE.search(h))
        if n_hs == 0:
            print(f"  [WARN] {path.name}: 0 HS-family columns on MSHS, skipping")
            continue
        data = raw.iloc[2:].reset_index(drop=True)
        data.columns = headers
        code = data["School code plus group"].astype(str).str[:8].str.zfill(8)
        dist = data["District code"].astype(str).str.zfill(8)
        type_col = "School, district, or single-school district"
        is_state = code == "00000000"
        is_peer_dist = dist.isin(peer_dists) & (data[type_col].astype(str).str.strip() == "District")
        kept = data[is_state | is_peer_dist].reset_index(drop=True)
        long = _reshape_criterion_sheet(
            kept, headers, sy, keep_codes=None,
            col_filter=_HS_FAMILY_RE.search, org_meta_from_sheet=True,
        )
        if not long.empty:
            frames.append(long)
            print(f"  {path.name}: SY{sy} MSHS -> {len(long):,} benchmark rows "
                  f"({n_hs} HS-family cols)")
    if not frames:
        print("  [SKIP] accountability benchmarks — nothing matched")
        return
    combined = pd.concat(frames, ignore_index=True)
    # Sanity anchors (2025 release): state All-Students HS ELA ≈ 498.9, Lynn ≈ 482.2.
    out_path = PROCESSED_DIR / "accountability_benchmarks.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"  [OK] -> {out_path.name}  ({len(combined):,} rows; "
          f"{combined['ORG_TYPE'].value_counts().to_dict()})")


def process_accountability_summary() -> None:
    """Rich per-school classification context (Table 2) -> one parquet.

    Source: accountability-data-{year}.xlsx, 'Table 2 - Schools'. Adds the
    fields the thin accountability.parquet lacks: federal designation, the
    low-performing/low-participation student groups that drove the
    classification, and the annual + cumulative criterion-referenced
    percentages. Filtered to the peer school set.
    """
    files = sorted(ACCOUNTABILITY_RAW.glob("accountability-data-*.xlsx"))
    if not files:
        print("  [SKIP] accountability summary — run "
              "scripts/19_download_accountability_detail.py first")
        return

    # Year-independent header names.
    rename_static = {
        "District Code": "DIST_CODE",
        "School Code": "ORG_CODE",
        "District Name": "DIST_NAME",
        "School Name": "ORG_NAME",
        "Grades Served": "GRADES",
        "School Type": "SCHOOL_TYPE",
        "District Overall Classification": "DIST_CLASSIFICATION",
        "School Overall Classification": "CLASSIFICATION",
        "Reason for School Classification": "REASON",
        "Title I Status": "TITLE_I_STATUS",
    }

    def _year_renames(sy: int) -> dict:
        """Header names that embed the determination year — rebuilt per file so
        the 2026 release processes without code changes."""
        return {
            f"October {sy - 1} Enrollment": "ENROLLMENT",
            f"{sy} Accountability Percentile": "PERCENTILE",
            f"{sy - 1} Annual Criterion-Referenced Target Percentage (%)": "CRIT_PRIOR",
            f"{sy} Annual Criterion-Referenced Target Percentage (%)": "CRIT_CURRENT",
            f"{sy} Cumulative Criterion-Referenced Target Percentage (%)": "CRIT_CUMULATIVE",
            f"{sy} Reason for Classification - Overall Performance": "REASON_OVERALL",
            f"{sy} Reason for Classification - Student Group Performance": "REASON_GROUP",
            f"{sy} Reason for Classification - Graduation Rate": "REASON_GRAD",
            f"{sy} Reason for Classification - Participation": "REASON_PARTICIPATION",
            f"{sy} Low Performing Student Group(s)": "LOW_PERFORMING_GROUPS",
            f"{sy} Low Participation Student Group(s)": "LOW_PARTICIPATION_GROUPS",
            f"{sy} Federal Designation": "FEDERAL_DESIGNATION",
        }

    keep = _peer_school_codes()
    frames = []
    out_order = list(rename_static.values()) + [
        "ENROLLMENT", "PERCENTILE", "CRIT_PRIOR", "CRIT_CURRENT", "CRIT_CUMULATIVE",
        "REASON_OVERALL", "REASON_GROUP", "REASON_GRAD", "REASON_PARTICIPATION",
        "LOW_PERFORMING_GROUPS", "LOW_PARTICIPATION_GROUPS", "FEDERAL_DESIGNATION",
    ]
    for path in files:
        m = re.search(r"(\d{4})", path.stem)
        sy = int(m.group(1)) if m else None
        rename = {**rename_static, **_year_renames(sy)}
        raw = pd.read_excel(path, sheet_name="Table 2 - Schools", header=None, dtype=str)
        headers = [str(c).strip() for c in raw.iloc[1].tolist()]
        data = raw.iloc[2:].reset_index(drop=True)
        data.columns = headers
        data = data.rename(columns=rename)
        data["ORG_CODE"] = data["ORG_CODE"].astype(str).str.zfill(8)
        data["DIST_CODE"] = data["DIST_CODE"].astype(str).str.zfill(8)
        data = data[data["ORG_CODE"].isin(keep)].copy()
        data["SY"] = sy
        cols = [c for c in out_order if c in data.columns] + ["SY"]
        frames.append(data[cols])
        print(f"  {path.name}: SY{sy} -> {len(data):,} schools")

    if not frames:
        print("  [SKIP] accountability summary — nothing matched the peer set")
        return
    combined = pd.concat(frames, ignore_index=True)
    for col in ["ENROLLMENT", "PERCENTILE", "CRIT_PRIOR", "CRIT_CURRENT", "CRIT_CUMULATIVE"]:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")
    out_path = PROCESSED_DIR / "accountability_summary.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"  [OK] -> {out_path.name}  ({len(combined):,} rows)")


def _num(v):
    """Coerce a cell to float, or NaN."""
    return pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]


def process_accountability_targets() -> None:
    """Per-school×group baselines + next-year improvement targets -> one parquet.

    Source: accountability-targets-{year}.xlsx, sheet "Targets and Increments"
    (the 70-column research file; the thinner 49-column next-cycle file is
    skipped because its required columns are absent). Powers the page's
    "what 2026 has to look like" section: TARGET_LATEST is the most recent
    published target; TARGET_PLUS1/PLUS2 apply DESE's annual increment in the
    indicator's improvement DIRECTION (dropout/chronic-absenteeism reduce).
    """
    files = sorted(ACCOUNTABILITY_RAW.glob("accountability-targets-*.xlsx"))
    if not files:
        print("  [SKIP] accountability targets — run scripts/19 first")
        return
    keep = _peer_school_codes()
    frames = []
    for path in files:
        m = re.search(r"(\d{4})", path.stem)
        sy = int(m.group(1)) if m else None
        df = pd.read_excel(path, sheet_name="Targets and Increments", header=1, dtype=str)
        cols = set(df.columns)
        needed = {e["latest_target"] for e in _TARGETS_CATALOG}
        if not needed <= cols:
            print(f"  [WARN] {path.name}: missing target columns "
                  f"(thin/next-cycle file?), skipping")
            continue
        df = df.rename(columns={
            "District Code": "DIST_CODE", "School Code": "ORG_CODE",
            "District Name": "DIST_NAME", "School Name": "ORG_NAME",
            "Group": "GROUP", "Gradespan": "GRADESPAN", "Region": "REGION",
        })
        df["ORG_CODE"] = df["ORG_CODE"].astype(str).str.zfill(8)
        df["DIST_CODE"] = df["DIST_CODE"].astype(str).str.zfill(8)
        df = df[df["ORG_CODE"].isin(keep)].copy()

        records = []
        for _, row in df.iterrows():
            meta = {k: row[k] for k in
                    ["SY", "ORG_CODE", "ORG_NAME", "DIST_CODE", "DIST_NAME",
                     "GROUP", "GRADESPAN", "REGION"] if k in row}
            meta["SY"] = sy
            for e in _TARGETS_CATALOG:
                latest = _num(row.get(e["latest_target"]))
                d = e["direction"]
                if e["mode"] == "single":
                    annual = _num(row.get(e["incr_single"]))
                    plus1 = latest + d * annual
                    plus2 = latest + d * 2 * annual
                else:  # peryear (achievement)
                    annual = _num(row.get(e["incr_plus1"]))
                    plus1 = latest + d * annual
                    plus2 = plus1 + d * _num(row.get(e["incr_plus2"]))
                if e["unit"] == "pct":  # rates stay inside [0, 100]
                    plus1 = min(max(plus1, 0.0), 100.0) if pd.notna(plus1) else plus1
                    plus2 = min(max(plus2, 0.0), 100.0) if pd.notna(plus2) else plus2
                records.append({
                    **meta,
                    "INDICATOR": e["indicator"], "UNIT": e["unit"], "DIRECTION": d,
                    "BASELINE_YEAR": e["baseline_year"], "BASELINE": _num(row.get(e["baseline"])),
                    "PATH": (row.get(e["path"]) if e["path"] else None),
                    "N_INCLUDED": _num(row.get(e["n"])),  # student COUNT, never a rate
                    "TARGET_LATEST_YEAR": e["latest_year"], "TARGET_LATEST": latest,
                    "ANNUAL_INCREMENT": annual,
                    "TARGET_PLUS1_YEAR": e["latest_year"] + 1, "TARGET_PLUS1": plus1,
                    "TARGET_PLUS2_YEAR": e["latest_year"] + 2, "TARGET_PLUS2": plus2,
                })
        if records:
            frames.append(pd.DataFrame.from_records(records))
            print(f"  {path.name}: SY{sy} -> {len(records):,} target rows")
    if not frames:
        print("  [SKIP] accountability targets — no parseable file")
        return
    combined = pd.concat(frames, ignore_index=True)
    out_path = PROCESSED_DIR / "accountability_targets.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"  [OK] -> {out_path.name}  ({len(combined):,} rows)")


def process_accountability_percentiles() -> None:
    """Statewide percentile build-up by indicator -> one parquet.

    Sources: school-percentile-{year}.xlsx (All Students) and
    student-group-percentile-{year}.xlsx (per group), sheet "HS " (trailing
    space). 143 positional columns; parsed via _PCTL_BLOCKS + _PCTL_LAYOUT.
    Tells the "low achievement but middling growth" story behind the 1st-
    percentile headline.
    """
    specs = [
        ("school-percentile-*.xlsx", "school", True),
        ("student-group-percentile-*.xlsx", "student_group", False),
    ]
    frames = []
    keep = _peer_school_codes()
    for glob_pat, source, force_all in specs:
        for path in sorted(ACCOUNTABILITY_RAW.glob(glob_pat)):
            m = re.search(r"(\d{4})", path.stem)
            sy = int(m.group(1)) if m else None
            xl = pd.ExcelFile(path)
            sheet = _resolve_sheet(xl, "HS")
            if sheet is None:
                print(f"  [WARN] {path.name}: no HS sheet, skipping")
                continue
            raw = xl.parse(sheet, header=None, dtype=str)
            headers = [str(c).replace("\n", " ").strip() for c in raw.iloc[1].tolist()]
            if len(headers) != 143 or not headers[141].startswith(f"{sy} School percentile"):
                print(f"  [WARN] {path.name}: unexpected layout "
                      f"(ncols={len(headers)}), skipping")
                continue
            data = raw.iloc[2:].reset_index(drop=True)
            org = data[0].astype(str).str[:8].str.zfill(8)
            data = data[org.isin(keep)].reset_index(drop=True)
            for _, row in data.iterrows():
                base_meta = {
                    "SY": sy,
                    "ORG_CODE": str(row[0])[:8].zfill(8),
                    "ORG_NAME": row[2],
                    "DIST_NAME": row[1],
                    "GROUP": ("All Students" if force_all else row[7]),
                    "SOURCE": source,
                    "WEIGHT_SCHEME": row[6],
                }
                for block_year, b in _PCTL_BLOCKS.items():
                    for v_off, p_off, indicator in _PCTL_LAYOUT:
                        vh = headers[b + v_off]
                        data_yr = (re.findall(r"\d{4}", vh) or [str(block_year)])[-1]
                        records_append = {
                            **base_meta,
                            "COMPONENT_YEAR": block_year,
                            "INDICATOR": indicator,
                            "DATA_YEAR": int(data_yr),
                            "VALUE": _num(row[b + v_off]),
                            "PERCENTILE": _num(row[b + p_off]),
                            "NOTES": row[142],
                        }
                        frames.append(records_append)
                # One overall (weighted) summary row per org×group.
                frames.append({
                    **base_meta, "COMPONENT_YEAR": sy, "INDICATOR": "Overall (weighted)",
                    "DATA_YEAR": sy, "VALUE": _num(row[140]),
                    "PERCENTILE": _num(row[141]), "NOTES": row[142],
                })
            print(f"  {path.name}: SY{sy} {source} -> processed")
    if not frames:
        print("  [SKIP] accountability percentiles — no parseable file")
        return
    combined = pd.DataFrame.from_records(frames)
    out_path = PROCESSED_DIR / "accountability_percentiles.parquet"
    combined.to_parquet(out_path, index=False)
    print(f"  [OK] -> {out_path.name}  ({len(combined):,} rows)")


def main() -> None:
    print("Processing DESE Profiles statereport xlsx files...")
    print(f"  raw input dir:    {DESE_PROFILES_RAW}")
    print(f"  processed output: {PROCESSED_DIR}")
    print()

    process_accountability()
    print()
    process_accountability_summary()
    print()
    process_accountability_indicators()
    print()
    process_accountability_benchmarks()
    print()
    process_accountability_targets()
    print()
    process_accountability_percentiles()

    print()
    print("Done.")


if __name__ == "__main__":
    main()
