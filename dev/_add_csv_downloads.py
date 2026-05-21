"""
One-shot helper: append a CSV-download expander to every dashboard page that
already loads at least one dataset. Run from repo root.

Idempotent — checks for the sentinel '# >>> auto: csv downloads <<<' before
appending.
"""

import re
from pathlib import Path

PAGES = Path(__file__).resolve().parent.parent / "pages"
SENTINEL = "# >>> auto: csv downloads <<<"

# Per-page datasets to expose. Mirrors what each page calls load_dataset() on.
PAGE_DATASETS = {
    "1_School_Profile.py":          {"Enrollment & demographics": "enrollment"},
    "2_Academic_Performance.py":    {"MCAS achievement": "mcas"},
    "3_ELL_Pipeline.py":            {"Enrollment & demographics": "enrollment",
                                      "MCAS achievement": "mcas"},
    "4_College_and_Career.py":      {"AP performance": "ap",
                                      "MassCore completion": "masscore",
                                      "Pathways enrollment": "pathways",
                                      "Early College participation": "ec_part",
                                      "IPEDS destinations": "ipeds"},
    "5_Success_After_HS.py":        {"DART (Success After HS)": "dart",
                                      "Graduation rates": "grad",
                                      "Plans of graduates": "plans"},
    "6_Teachers_and_Workforce.py":  {"Staffing (race/gender)": "staffing",
                                      "Enrollment & demographics": "enrollment",
                                      "CRDC staffing": "crdc_staff"},
    "7_Finance.py":                 {"School expenditures": "school_exp",
                                      "District expenditures": "dist_exp"},
    "8_Discipline_and_Climate.py":  {"Student attendance": "attendance",
                                      "Discipline disproportionality": "disp",
                                      "CRDC discipline": "crdc"},
    "9_Community_Context.py":       {"Enrollment & demographics": "enrollment"},
    "10_Lynn_District_and_Siblings.py": {},
    "11_Gateway_Peer_Comparison.py":    {},
    "12_Correlation_Lab.py":            {"Master gateway-HS panel": "panel"},
    "14_All_Lynn_Schools.py":       {"Enrollment & demographics": "enrollment",
                                      "MCAS achievement": "mcas",
                                      "Student attendance": "attendance",
                                      "Per-school performance panel": "perf"},
    "15_Lynn_District_Dashboard.py":{"Enrollment & demographics": "enrollment",
                                      "Graduation rates": "grad",
                                      "MCAS achievement": "mcas",
                                      "Student attendance": "attendance",
                                      "District expenditures": "dist_exp"},
    "17_Federal_CRDC.py":           {"CRDC discipline": "discipline",
                                      "CRDC offerings": "offerings",
                                      "CRDC staffing": "staffing"},
}


def block(datasets: dict[str, str]) -> str:
    if not datasets:
        return ""
    lines = [
        "",
        SENTINEL,
        "try:",
        "    from utils.charts import data_downloads_panel as _dl",
        "    _dl({",
    ]
    for label, var in datasets.items():
        lines.append(f"        {label!r}: {var},")
    lines.append("    })")
    lines.append("except NameError:")
    lines.append("    # one of the dataset variables wasn't defined on this run")
    lines.append("    pass")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    for filename, datasets in PAGE_DATASETS.items():
        p = PAGES / filename
        if not p.exists():
            print(f"[SKIP] {filename} not found")
            continue
        text = p.read_text(encoding="utf-8")
        if SENTINEL in text:
            print(f"[OK]   {filename} already has CSV block")
            continue
        if not datasets:
            print(f"[SKIP] {filename} (no datasets to expose)")
            continue
        text = text.rstrip() + "\n" + block(datasets) + "\n"
        p.write_text(text, encoding="utf-8")
        print(f"[ADD]  {filename}")


if __name__ == "__main__":
    main()
