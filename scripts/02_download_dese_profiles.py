"""
Scrape bulk reports from DESE Profiles statereport (profiles.doe.mass.edu/statereport/).

Many DESE reports live on the older WebForms-based profiles.doe.mass.edu site
rather than the E2C Hub Socrata portal. Each report page is a stateful ASP.NET
form that exports XLSX via an in-page POSTback rather than a static URL — so
"download" means: GET the page, capture VIEWSTATE / EVENTVALIDATION, then
POST back with the hidden `hfExport` field set to "Excel".

What's wired up now (Phase E):
  * accountability — ESSA designations (district + school level)

What's still stubbed (Phase E follow-ups, same scraper pattern applies):
  - dropout, attendance, attrition, staffattendance
  - access (WIDA ACCESS for ELLs)
  - educatorcontracts, educatorevaluationperformance
  - VOCAL student climate survey
  - ap, ap_part (AP participation breakdowns not on Socrata)

To add a new report: append an entry to REPORTS. If the page has a report-type
dropdown (district vs school), set `selects` so the scraper hits it in both
modes. Most pages don't.

Run with:
    python scripts/02_download_dese_profiles.py
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import RAW_DIR  # noqa: E402

PROFILES_BASE = "https://profiles.doe.mass.edu/statereport/"
OUT_DIR = RAW_DIR / "dese_profiles"
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "lehs-data-dive/0.1 (github.com/mapzimus/lehs-data-dive)"


# ---------------------------------------------------------------------------
# Report definitions
# ---------------------------------------------------------------------------


@dataclass
class Report:
    """A DESE statereport target."""

    slug: str                            # local filename stem
    page: str                            # statereport page (e.g. "accountability.aspx")
    # If set, switch the report-type dropdown to each value and download once
    # per variant. The downloaded file is `{slug}_{variant.lower()}.xlsx`.
    report_type_select: str | None = None  # name of the dropdown control
    report_type_values: list[str] = field(default_factory=list)


REPORTS: list[Report] = [
    Report(
        slug="accountability",
        page="accountability.aspx",
        report_type_select="ctl00$ContentPlaceHolder1$ddReportType",
        report_type_values=["District", "School"],
    ),
    # Future Phase E additions go here. The shape:
    #   Report(slug="dropout", page="dropout.aspx"),
    #   Report(slug="staffattendance", page="staffattendance.aspx"),
    # Confirm whether each page has a ddReportType-style dropdown by inspecting
    # its HTML before adding it.
]


# ---------------------------------------------------------------------------
# ASP.NET helpers
# ---------------------------------------------------------------------------


def _hidden(name: str, html: str) -> str:
    """Pull a hidden input's value out of the rendered HTML."""
    m = re.search(rf'name="{re.escape(name)}"[^>]*value="([^"]*)"', html)
    return m.group(1) if m else ""


def _all_hidden_inputs(html: str) -> dict[str, str]:
    """Every non-system hidden input on the page — needed to round-trip ASP.NET state."""
    out: dict[str, str] = {}
    for m in re.finditer(
        r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]*value="([^"]*)"', html
    ):
        n, v = m.group(1), m.group(2)
        if not n.startswith("__"):
            out[n] = v
    return out


def _viewstate_block(html: str) -> dict[str, str]:
    return {
        "__VIEWSTATE": _hidden("__VIEWSTATE", html),
        "__VIEWSTATEGENERATOR": _hidden("__VIEWSTATEGENERATOR", html),
        "__EVENTVALIDATION": _hidden("__EVENTVALIDATION", html),
    }


def _select_options(html: str, select_name: str) -> list[tuple[str, str]]:
    """Extract (value, label) pairs from a named <select>."""
    m = re.search(
        rf'<select[^>]+name="{re.escape(select_name)}"[^>]*>(.*?)</select>',
        html, re.S,
    )
    if not m:
        return []
    return [
        (o.group(1), o.group(2).strip())
        for o in re.finditer(
            r'<option[^>]*value="([^"]*)"[^>]*>([^<]+)</option>', m.group(1)
        )
    ]


def _is_xlsx_response(resp: requests.Response) -> bool:
    ct = resp.headers.get("content-type", "").lower()
    return "spreadsheet" in ct or "excel" in ct or "officedocument" in ct


# ---------------------------------------------------------------------------
# Scrape one report
# ---------------------------------------------------------------------------


def _post_with_state(
    session: requests.Session, url: str, html: str, **overrides: str
) -> requests.Response:
    """POST back to the page, round-tripping ASP.NET state. Adds `overrides` on top."""
    data: dict[str, str] = {}
    data.update(_viewstate_block(html))
    data.update(_all_hidden_inputs(html))
    data.update(overrides)
    return session.post(url, data=data, timeout=60)


def fetch_report(session: requests.Session, report: Report) -> list[Path]:
    """Fetch a report — once for each report-type variant if applicable."""
    url = PROFILES_BASE + report.page
    print(f"\n-> {report.slug}: GET {url}")
    r = session.get(url, timeout=30)
    r.raise_for_status()

    variants = report.report_type_values or [None]
    out_paths: list[Path] = []

    for variant in variants:
        html_state = r.text
        # If there's a report-type dropdown, switch it via __EVENTTARGET POSTback
        if variant is not None and report.report_type_select:
            print(f"  switching {report.report_type_select} -> {variant}")
            switch = _post_with_state(
                session, url, html_state,
                __EVENTTARGET=report.report_type_select,
                __EVENTARGUMENT="",
                **{report.report_type_select: variant},
            )
            switch.raise_for_status()
            html_state = switch.text

        # Trigger the Excel export
        print(f"  POST export {('('+variant+')') if variant else ''}")
        overrides = {"ctl00$ContentPlaceHolder1$hfExport": "Excel"}
        if variant is not None and report.report_type_select:
            overrides[report.report_type_select] = variant
        exp = _post_with_state(session, url, html_state, **overrides)
        if not _is_xlsx_response(exp):
            print(f"  [X] not an xlsx response ({exp.status_code}, "
                  f"ct={exp.headers.get('content-type')})")
            continue

        suffix = f"_{variant.lower()}" if variant else ""
        out_path = OUT_DIR / f"{report.slug}{suffix}.xlsx"
        out_path.write_bytes(exp.content)
        print(f"  [OK] saved {out_path.name} ({len(exp.content):,} bytes)")
        out_paths.append(out_path)
        time.sleep(0.5)  # be polite

    return out_paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    print(f"Scraping {len(REPORTS)} DESE statereport target(s) ...")
    successes: list[Path] = []
    failures: list[tuple[str, str]] = []
    for rep in REPORTS:
        try:
            paths = fetch_report(session, rep)
            if not paths:
                failures.append((rep.slug, "no files written"))
            successes.extend(paths)
        except Exception as e:
            print(f"  [X] {rep.slug}: {e}")
            failures.append((rep.slug, str(e)))

    print()
    print("=" * 70)
    print(f"Done. {len(successes)} file(s) saved, {len(failures)} failure(s).")
    for p in successes:
        print(f"  [OK] {p}")
    for slug, msg in failures:
        print(f"  [X] {slug}: {msg}")


if __name__ == "__main__":
    main()
