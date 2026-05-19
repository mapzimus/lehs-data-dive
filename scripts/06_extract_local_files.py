"""
Extract clean CSV data from locally downloaded DESE files:
  - reporting-element4.xlsx — Former EL MCAS by year of exit, all MA districts
  - state.docx — WIDA ACCESS 2025 statewide ELL proficiency

Outputs:
  - data/raw/local/former_el_mcas.csv     (filtered to Lynn + gateway cities)
  - data/raw/local/wida_state_summary.json (key statewide WIDA metrics)

Run with:
    python scripts/06_extract_local_files.py
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from utils.constants import (  # noqa: E402
    GATEWAY_CITIES,
    LYNN_DISTRICT_CODE,
    RAW_DIR,
)

LOCAL_DIR = RAW_DIR / "local"
LOCAL_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = Path("C:/Users/Calen/Downloads")
REPORTING_ELEMENT4 = DOWNLOADS / "reporting-element4.xlsx"
WIDA_STATE_DOCX = DOWNLOADS / "state.docx"

# ---------------------------------------------------------------------------
# reporting-element4.xlsx — Former EL MCAS achievement
# ---------------------------------------------------------------------------


def extract_former_el_mcas() -> None:
    if not REPORTING_ELEMENT4.exists():
        print(f"  [X] {REPORTING_ELEMENT4} not found, skipping")
        return

    print(f"Reading {REPORTING_ELEMENT4.name}...")
    # File structure: row 0 = report title, row 1 = subtitle, row 2 = blank,
    # row 3 = actual column headers
    df = pd.read_excel(REPORTING_ELEMENT4, dtype=str, header=3)
    # Strip newlines from column names (Excel formatted some as "ELA \nE+M #")
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    print(f"  loaded: {len(df):,} rows, {len(df.columns)} columns")
    print(f"  columns: {list(df.columns)}")

    org_code_col = "Org Code" if "Org Code" in df.columns else None
    if not org_code_col:
        print(f"  warning: 'Org Code' column not found. Saving full file.")
        out = LOCAL_DIR / "former_el_mcas_all.csv"
        df.to_csv(out, index=False)
        return

    # zero-pad codes
    df[org_code_col] = df[org_code_col].astype(str).str.zfill(8)

    # full file (useful for gateway-city filtering downstream)
    out_all = LOCAL_DIR / "former_el_mcas_all.csv"
    df.to_csv(out_all, index=False)
    print(f"  wrote full file: {out_all}")

    # Lynn-only subset
    lynn = df[df[org_code_col] == LYNN_DISTRICT_CODE].copy()
    out_lynn = LOCAL_DIR / "former_el_mcas_lynn.csv"
    lynn.to_csv(out_lynn, index=False)
    print(f"  wrote Lynn-only: {out_lynn} ({len(lynn)} rows)")


# ---------------------------------------------------------------------------
# state.docx — WIDA ACCESS 2025 statewide
# ---------------------------------------------------------------------------


def extract_docx_text(docx_path: Path) -> str:
    """Extract all text from a .docx by reading word/document.xml."""
    with zipfile.ZipFile(docx_path) as z:
        with z.open("word/document.xml") as f:
            xml_raw = f.read().decode("utf-8", errors="replace")
    matches = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml_raw)
    return "\n".join(matches)


def extract_wida_state() -> None:
    if not WIDA_STATE_DOCX.exists():
        print(f"  [X] {WIDA_STATE_DOCX} not found, skipping")
        return

    print(f"Reading {WIDA_STATE_DOCX.name}...")
    text = extract_docx_text(WIDA_STATE_DOCX)
    print(f"  extracted {len(text):,} characters of text")

    # Save the full text for reference / further parsing
    txt_out = LOCAL_DIR / "wida_state_2025_text.txt"
    txt_out.write_text(text, encoding="utf-8")
    print(f"  wrote raw text: {txt_out}")

    # Parse out key headline metrics (from manual extraction in prior session)
    # These are statewide totals from WIDA ACCESS 2025
    summary = {
        "report": "WIDA ACCESS 2025 Statewide Results",
        "publisher": "MA DESE",
        "published": "April 2026",
        "total_ell_k12_enrolled": 126769,
        "total_ell_tested": 124564,
        "participation_rate": 0.98,
        "avg_proficiency": {
            "speaking": 2.9,
            "writing": 2.9,
            "reading": 3.1,
            "listening": 4.1,
        },
        "reclassification": {
            "criteria": "overall >= 4.2, literacy >= 3.9",
            "pct_meeting_criteria": 0.133,
        },
        "note": (
            "These are statewide aggregates. School-level WIDA data must be "
            "pulled from the DESE Profiles statereport bulk download (ACCESS for ELLs)."
        ),
    }
    json_out = LOCAL_DIR / "wida_state_summary.json"
    json_out.write_text(json.dumps(summary, indent=2))
    print(f"  wrote summary: {json_out}")


def main() -> None:
    print("=" * 60)
    print("Extract reporting-element4.xlsx (former EL MCAS)")
    print("=" * 60)
    extract_former_el_mcas()

    print()
    print("=" * 60)
    print("Extract state.docx (WIDA ACCESS 2025 statewide)")
    print("=" * 60)
    extract_wida_state()


if __name__ == "__main__":
    main()
