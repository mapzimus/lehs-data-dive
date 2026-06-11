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
                             sy: int, keep_codes: set[str]) -> pd.DataFrame:
    """Wide DESE criterion sheet -> tidy long frame (one row per school×group×indicator)."""
    data = data.copy()
    data.columns = headers
    data["ORG_CODE"] = data["School code plus group"].astype(str).str[:8].str.zfill(8)
    data["DIST_CODE"] = data["District code"].astype(str).str.zfill(8)
    # Keep our peer schools plus the statewide row (code 00000000) for context.
    data = data[data["ORG_CODE"].isin(keep_codes | {"00000000"})].copy()
    if data.empty:
        return pd.DataFrame()

    records: list[dict] = []
    for _, row in data.iterrows():
        is_state = row["ORG_CODE"] == "00000000"
        base = {
            "SY": sy,
            "ORG_CODE": row["ORG_CODE"],
            "ORG_NAME": ("Massachusetts" if is_state else row["School name"]),
            "ORG_TYPE": ("State" if is_state else "School"),
            "DIST_CODE": row["DIST_CODE"],
            "DIST_NAME": row["District name"],
            "GROUP": row["Group"],
        }
        for prefix, name, category, unit in _INDICATOR_CATALOG:
            cols = [h for h in headers if h.startswith(prefix)]
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

    rename = {
        "District Code": "DIST_CODE",
        "School Code": "ORG_CODE",
        "District Name": "DIST_NAME",
        "School Name": "ORG_NAME",
        "Grades Served": "GRADES",
        "School Type": "SCHOOL_TYPE",
        "October 2024 Enrollment": "ENROLLMENT",
        "District Overall Classification": "DIST_CLASSIFICATION",
        "School Overall Classification": "CLASSIFICATION",
        "Reason for School Classification": "REASON",
        "2025 Accountability Percentile": "PERCENTILE",
        "2024 Annual Criterion-Referenced Target Percentage (%)": "CRIT_PRIOR",
        "2025 Annual Criterion-Referenced Target Percentage (%)": "CRIT_CURRENT",
        "2025 Cumulative Criterion-Referenced Target Percentage (%)": "CRIT_CUMULATIVE",
        "2025 Reason for Classification - Overall Performance": "REASON_OVERALL",
        "2025 Reason for Classification - Student Group Performance": "REASON_GROUP",
        "2025 Reason for Classification - Graduation Rate": "REASON_GRAD",
        "2025 Reason for Classification - Participation": "REASON_PARTICIPATION",
        "2025 Low Performing Student Group(s)": "LOW_PERFORMING_GROUPS",
        "2025 Low Participation Student Group(s)": "LOW_PARTICIPATION_GROUPS",
        "2025 Federal Designation": "FEDERAL_DESIGNATION",
        "Title I Status": "TITLE_I_STATUS",
    }
    keep = _peer_school_codes()
    frames = []
    for path in files:
        m = re.search(r"(\d{4})", path.stem)
        sy = int(m.group(1)) if m else None
        raw = pd.read_excel(path, sheet_name="Table 2 - Schools", header=None, dtype=str)
        headers = [str(c).strip() for c in raw.iloc[1].tolist()]
        data = raw.iloc[2:].reset_index(drop=True)
        data.columns = headers
        data = data.rename(columns=rename)
        data["ORG_CODE"] = data["ORG_CODE"].astype(str).str.zfill(8)
        data["DIST_CODE"] = data["DIST_CODE"].astype(str).str.zfill(8)
        data = data[data["ORG_CODE"].isin(keep)].copy()
        data["SY"] = sy
        cols = [c for c in rename.values() if c in data.columns] + ["SY"]
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
    print("Done.")


if __name__ == "__main__":
    main()
