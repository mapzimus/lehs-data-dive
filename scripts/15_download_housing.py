"""
Download Zillow housing-market time series for Lynn (city), MA (state),
and the US (national). Two indices, both free, no API key required:

  - ZHVI  (Zillow Home Value Index) — typical home value at the 33-67th
          percentile range, smoothed/seasonally adjusted, single-family +
          condo. Monthly.
  - ZORI  (Zillow Observed Rent Index) — typical asking rent across
          SFR + condo + multifamily, smoothed. Monthly.

Source: zillow.com/research/data/
URLs are stable bulk CSVs hosted on files.zillowstatic.com.

Filters to:
  - Lynn, MA (city level — both ZHVI and ZORI)
  - Massachusetts state level (ZHVI only — ZORI is not published at state level)
  - National "United States" row (from the metro/national file — both indices)

Outputs:
  data/processed/lynn_housing_trend.parquet  — long format
    columns: date (monthly), scope ∈ {"Lynn", "Massachusetts", "United States"},
             metric ∈ {"ZHVI", "ZORI"}, value (USD)

Run with:
    python scripts/15_download_housing.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR, RAW_DIR  # noqa: E402

ZHVI_CITY_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "City_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)
ZORI_CITY_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zori/"
    "City_zori_uc_sfrcondomfr_sm_month.csv"
)
ZHVI_STATE_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "State_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)
# ZORI is NOT published at state level. Use national metro file's
# "United States" row as the cross-Lynn comparator.
ZHVI_NATIONAL_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)
ZORI_NATIONAL_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zori/"
    "Metro_zori_uc_sfrcondomfr_sm_month.csv"
)

USER_AGENT = "lehs-data-dive/0.1 (github.com/mapzimus/lehs-data-dive)"
HEADERS = {"User-Agent": USER_AGENT}

OUT_RAW = RAW_DIR / "zillow"
OUT_RAW.mkdir(parents=True, exist_ok=True)


def fetch_csv(url: str, label: str) -> pd.DataFrame:
    print(f"  Fetching {label} ...")
    r = requests.get(url, headers=HEADERS, timeout=300)
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content))


def melt_long(df: pd.DataFrame, scope_label: str, metric: str) -> pd.DataFrame:
    """Zillow wide format → long. Date columns look like '2024-01-31'."""
    id_cols = [c for c in df.columns if not c[:4].isdigit()]
    date_cols = [c for c in df.columns if c[:4].isdigit()]
    long_df = df.melt(id_vars=id_cols, value_vars=date_cols,
                      var_name="date", value_name="value")
    long_df["date"] = pd.to_datetime(long_df["date"], errors="coerce")
    long_df["scope"] = scope_label
    long_df["metric"] = metric
    return long_df[["date", "scope", "metric", "value"]].dropna(subset=["value"])


def main() -> None:
    rows: list[pd.DataFrame] = []

    # --- Lynn (city level) -------------------------------------------------
    for url, metric in [(ZHVI_CITY_URL, "ZHVI"), (ZORI_CITY_URL, "ZORI")]:
        df = fetch_csv(url, f"city {metric}")
        lynn = df[(df["RegionName"] == "Lynn") & (df["State"] == "MA")]
        if lynn.empty:
            print(f"  [WARN] no Lynn, MA row in {metric} city CSV")
            continue
        rows.append(melt_long(lynn, "Lynn", metric))

    # --- Massachusetts (state level) — ZHVI only; ZORI not published here ---
    df = fetch_csv(ZHVI_STATE_URL, "state ZHVI")
    ma = df[df["RegionName"] == "Massachusetts"]
    if not ma.empty:
        rows.append(melt_long(ma, "Massachusetts", "ZHVI"))
    else:
        print("  [WARN] no Massachusetts row in ZHVI state CSV")

    # --- United States (national row in metro file) -----------------------
    for url, metric in [(ZHVI_NATIONAL_URL, "ZHVI"), (ZORI_NATIONAL_URL, "ZORI")]:
        df = fetch_csv(url, f"national {metric}")
        # National row uses RegionName == "United States"
        us = df[df["RegionName"] == "United States"]
        if us.empty:
            print(f"  [WARN] no national row in {metric} metro CSV")
            continue
        rows.append(melt_long(us, "United States", metric))

    if not rows:
        print("No data fetched. Aborting.")
        sys.exit(1)

    combined = pd.concat(rows, ignore_index=True).sort_values(["scope", "metric", "date"])
    out_path = PROCESSED_DIR / "lynn_housing_trend.parquet"
    combined.to_parquet(out_path, index=False)

    print()
    print(f"Wrote {len(combined):,} rows -> {out_path}")
    print(f"Scopes: {sorted(combined['scope'].unique())}")
    print(f"Metrics: {sorted(combined['metric'].unique())}")
    print(f"Date range: {combined['date'].min()} to {combined['date'].max()}")
    print("\nLatest values:")
    latest = combined.sort_values("date").groupby(["scope", "metric"]).tail(1)
    print(latest.to_string(index=False))


if __name__ == "__main__":
    main()
