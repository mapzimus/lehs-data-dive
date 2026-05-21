# Map ↔ Dashboard Data Parity

Goal: the Lynn map should surface every metric the Streamlit dashboard does, at the level (school / district / muni / tract) that makes sense for it.

## Current state (audit, 2026-05-21)

`maps/data/ma_academic_districts.geojson` has **44 base columns** including all of the "stripped" metrics (chronic_absent_pct, attendance_rate, ap_pct_3plus, staff_*_pct, teacher_experienced_pct, teacher_infield_pct, etc.). The schema is fine — **every column is all-null**.

This means the joins in `scripts/11_build_lynn_geo.py` ran successfully but matched zero rows. Two likely causes:

1. **Raw CSVs are empty or missing.** The build script reads from `data/raw/e2c_hub/student_attendance.csv`, `ap_performance.csv`, `staffing_race_gender.csv`, `teacher_data.csv`, etc. If those files are empty (failed download) or were deleted after a `data/raw/` cleanup, the filter `(df.ORG_TYPE == "District") & (df.STU_GRP == "All Students")` returns zero rows, and the subsequent merge adds the column with all NaN.

2. **Filter conditions don't match the latest schema.** E2C Hub occasionally renames columns or splits aggregation categories (e.g. `STU_GRP` → `STUDENT_GROUP`). If a single column name drifted, the filter returns empty without erroring.

The dashboard works fine because it reads from `data/processed/lehs_master.parquet` — a wide pre-joined master panel built by `08_build_master_panel.py`. That panel was built at a different point in time when the raw CSVs had data.

## Recommended fix (one-time, then automate)

```powershell
# In lehs-data-dive working tree, with conda env activated:
$env:CENSUS_API_KEY = "your-key"
python scripts/01_download_e2c.py            # refresh E2C raw CSVs
python scripts/11_build_lynn_geo.py          # rebuild GeoJSONs

# If raw download is broken (E2C API changed), the workaround is to
# pivot 11_build_lynn_geo.py to read from data/processed/lehs_master.parquet
# instead of raw CSVs — same data, more reliable, already what the
# dashboard uses.
```

After the rebuild, the "(data refresh pending)" labels in the metric dropdown will disappear automatically — the JS checks the geojson for non-null values at render time.

## Broader parity work

Beyond restoring the all-null columns, the dashboard surfaces several categories of data that aren't yet in any map layer:

| Dashboard page | Data | Where it could land |
|---|---|---|
| 4 College & Career | IPEDS destination colleges per district | new district column or a school-point overlay |
| 6 Teachers & Workforce | CRDC support-staff ratios | district columns |
| 8 Discipline & Climate | CRDC indicators + disproportionality | district columns |
| 9 Community Context | EJScreen + CDC PLACES | tract columns (partially exists) |
| 17 Federal CRDC | Full CRDC deep-dive | district columns |
| 18 Cohort Tracking | Multi-year cohort follow | district year-keyed columns |

Each is an incremental join to add to `11_build_lynn_geo.py`. Tackle once the basic refresh is back to populated.
