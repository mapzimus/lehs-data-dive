#!/usr/bin/env python3
"""
Ingest Massachusetts youth mental-health data (YRBS mental-health indicators).

WHAT THIS IS — AND ISN'T
------------------------
Massachusetts does NOT publish a student wellbeing survey at the Lynn
district/school level in a machine-readable feed (for privacy, youth-survey
results are suppressed below the state/region level). So a Lynn-specific
student-wellbeing dataset is genuinely unavailable — that gap is documented on
the Data Gaps page.

What IS available programmatically is **Massachusetts statewide** youth
mental-health data from the CDC's YRBSS Mental Health Indicators dataset
(data.cdc.gov resource nu3s-3dwd): the share of MA high-schoolers who felt
persistently sad/hopeless, seriously considered suicide, etc., for 2019/2021/
2023, broken out Total / by sex / by race-ethnicity.

This is STATEWIDE, not Lynn. The Wellbeing page labels it accordingly — it
describes Massachusetts teens generally, not LEHS students specifically.

OUTPUT — data/processed/youth_health.parquet (tidy):
    SY         int    survey year
    GEO        str    "Massachusetts"
    GEO_LEVEL  str    "state"
    TOPIC      str    short indicator label (mapped from the survey question)
    GROUP_TYPE str    "Total" | "Sex" | "RaceEthnicity"
    GROUP      str    "Total" | "Female" | "Male" | a race/ethnicity
    VALUE      float  percent (0-100)
    LOW_CI     float  95% CI low
    HIGH_CI    float  95% CI high
    SOURCE     str    citation

DEGRADES SAFELY: on any network/parse failure or schema drift, writes NOTHING
and prints a clear message. The Wellbeing page handles an absent youth_health
dataset by falling back to proxy signals, so the pipeline never breaks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
OUT = PROCESSED / "youth_health.parquet"

ENDPOINT = "https://data.cdc.gov/resource/nu3s-3dwd.json"
STATE = "MA"
SOURCE = ("CDC Youth Risk Behavior Surveillance System (YRBSS) — Mental Health "
          "Indicators, Massachusetts statewide (not Lynn-specific)")
TIMEOUT = 35

# Map the long survey questions to short, chart-friendly topic labels. Only
# questions in this map are kept (keeps the page focused on wellbeing).
TOPIC_MAP = {
    "feel so sad or hopeless": "Felt sad or hopeless (2+ weeks)",
    "seriously consider attempting suicide": "Seriously considered suicide",
    "make a plan about how you would attempt suicide": "Made a suicide plan",
    "actually attempt suicide": "Attempted suicide",
    "mental health not good": "Poor mental health (past 30 days)",
}


def _short_topic(question: str) -> str | None:
    q = (question or "").lower()
    for needle, label in TOPIC_MAP.items():
        if needle in q:
            return label
    return None


def _fetch() -> pd.DataFrame:
    r = requests.get(ENDPOINT, params={"$where": f"area_abbr='{STATE}'",
                                        "$limit": "5000"}, timeout=TIMEOUT)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def _tidy(raw: pd.DataFrame) -> pd.DataFrame:
    needed = {"year", "question", "demographics_type", "demographics_value", "percent"}
    if raw.empty or not needed.issubset(raw.columns):
        return pd.DataFrame()

    df = raw.copy()
    df["TOPIC"] = df["question"].map(_short_topic)
    df = df[df["TOPIC"].notna()]
    if df.empty:
        return pd.DataFrame()

    out = pd.DataFrame({
        "SY": pd.to_numeric(df["year"], errors="coerce").astype("Int64"),
        "GEO": "Massachusetts",
        "GEO_LEVEL": "state",
        "TOPIC": df["TOPIC"],
        "GROUP_TYPE": df["demographics_type"].astype(str),
        "GROUP": df["demographics_value"].astype(str),
        "VALUE": pd.to_numeric(df["percent"], errors="coerce"),
        "LOW_CI": pd.to_numeric(df.get("low_confidence_interval"), errors="coerce"),
        "HIGH_CI": pd.to_numeric(df.get("high_confidence_interval"), errors="coerce"),
        "SOURCE": SOURCE,
    })
    out = out.dropna(subset=["SY", "VALUE"]).reset_index(drop=True)
    return out


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    try:
        raw = _fetch()
    except Exception as e:
        print(f"[youth_health] fetch failed ({e}); leaving dataset absent. "
              f"Wellbeing page will use proxy signals.")
        return 0

    tidy = _tidy(raw)
    if tidy.empty:
        print("[youth_health] no usable MA mental-health rows (schema drift?); "
              "leaving dataset absent so the Wellbeing page stays in proxy mode.")
        return 0

    tidy.to_parquet(OUT, index=False)
    print(f"[youth_health] wrote {OUT} — {len(tidy):,} rows, "
          f"years {sorted(tidy['SY'].dropna().unique().tolist())}, "
          f"{tidy['TOPIC'].nunique()} topics (Massachusetts STATEWIDE).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
