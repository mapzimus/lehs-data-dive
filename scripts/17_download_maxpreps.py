"""
Scrape Lynn English Bulldogs season records from MaxPreps for the
"Athletics" page on the LEHS Data Dive.

MaxPreps is a Next.js app. Every team-season page embeds the full
server-side data blob as `__NEXT_DATA__`, so we parse JSON rather than
HTML — much cleaner and much less fragile than DOM scraping.

Coverage:
  - All 18 sport / gender / season combos LEHS fields (per MaxPreps)
  - Each combo's Varsity-level page back to 2007-08 where available

Polite scraping:
  - Browser-style User-Agent
  - 2.0s sleep between requests
  - Per-URL HTML cache on disk (data/raw/maxpreps/cache/) so re-runs are
    nearly free unless we explicitly --refresh

Outputs:
  data/raw/maxpreps/                                          (raw cache)
    cache/{sport-slug}_{year}_{gender}_{level}.html          (per-season page)
  data/raw/maxpreps/_index.json                              (manifest of what was fetched)

Then run scripts/18_process_maxpreps.py to flatten into a parquet.

Usage:
    python scripts/17_download_maxpreps.py            # use cache
    python scripts/17_download_maxpreps.py --refresh  # bypass cache
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import RAW_DIR  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LEHS_TEAM_URL = "https://www.maxpreps.com/ma/lynn/lynn-english-bulldogs/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36 "
    "(github.com/mapzimus/lehs-data-dive)"
)

THROTTLE_SECONDS = 2.0          # be a polite citizen
TIMEOUT_SECONDS = 30

OUT_DIR = RAW_DIR / "maxpreps"
CACHE_DIR = OUT_DIR / "cache"
INDEX_PATH = OUT_DIR / "_index.json"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _slugify(url: str) -> str:
    """A stable, filesystem-safe key for a MaxPreps team-season URL."""
    p = urlparse(url).path.strip("/")
    # collapse path segments; trim "schedule" since it's a leaf alias
    if p.endswith("/schedule"):
        p = p[: -len("/schedule")]
    return p.replace("/", "_") or "root"


def fetch_html(
    session: requests.Session,
    url: str,
    *,
    use_cache: bool = True,
) -> str | None:
    cache_path = CACHE_DIR / f"{_slugify(url)}.html"
    if use_cache and cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="ignore")

    try:
        r = session.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        print(f"  [X] request failed for {url}: {e}")
        return None

    if r.status_code != 200:
        print(f"  [X] HTTP {r.status_code} for {url}")
        return None

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(r.text, encoding="utf-8")
    time.sleep(THROTTLE_SECONDS)
    return r.text


def extract_next_data(html: str) -> dict | None:
    m = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html, re.S,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------


@dataclass
class SportSeasonRef:
    sport: str            # "Baseball"
    gender: str           # "Boys" / "Girls"
    season: str           # "Fall" / "Winter" / "Spring"
    year: str             # "24-25"
    level: str            # "Varsity" / "JV" / etc.
    url: str
    cache_file: str       # filename inside CACHE_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh", action="store_true",
        help="Bypass the on-disk HTML cache and re-fetch every page.",
    )
    parser.add_argument(
        "--varsity-only", action="store_true", default=True,
        help="Only fetch Varsity-level pages (default).",
    )
    args = parser.parse_args()
    use_cache = not args.refresh

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Step 1 — fetch the main school page to inventory sports offered.
    print(f"-> Inventorying sports from {LEHS_TEAM_URL}")
    html = fetch_html(session, LEHS_TEAM_URL, use_cache=use_cache)
    if not html:
        print("  [X] could not load the main team page; aborting")
        sys.exit(1)
    data = extract_next_data(html)
    sport_seasons = (
        data.get("props", {})
            .get("pageProps", {})
            .get("schoolContext", {})
            .get("sportSeasons", [])
    )
    # Distinct sport/gender/season combos — varsity-level entry per combo
    combos: list[dict] = []
    seen: set[tuple] = set()
    for s in sport_seasons:
        key = (s.get("sport"), s.get("gender"), s.get("season"))
        if key in seen:
            continue
        # Skip JV/Freshman; varsity URLs don't carry a level suffix
        url = s.get("canonicalUrl") or ""
        if "/jv/" in url or "/freshman/" in url:
            continue
        seen.add(key)
        combos.append(s)

    print(f"  found {len(combos)} varsity sport-gender-season combos")

    # Step 2 — for each combo, fetch the sport hub page → pull the year picker
    refs: list[SportSeasonRef] = []
    for combo in combos:
        sport = combo.get("sport")
        gender = combo.get("gender")
        season = combo.get("season")
        hub_url = combo.get("canonicalUrl")
        if not hub_url:
            continue
        print(f"\n-> {sport} ({gender} {season})  hub: {hub_url}")
        hub_html = fetch_html(session, hub_url, use_cache=use_cache)
        if not hub_html:
            continue
        hub_data = extract_next_data(hub_html)
        picker = (
            hub_data.get("props", {})
                    .get("pageProps", {})
                    .get("teamContext", {})
                    .get("teamSeasonPickerData", [])
        )
        # Varsity entries across all years for this sport+gender combo
        varsity_entries = [
            p for p in picker
            if p.get("level") == "Varsity"
            and p.get("gender") == gender
            and p.get("season") == season
        ]
        # Hub page itself is the current year — capture from hub_data.standingsData
        for entry in varsity_entries:
            ref = SportSeasonRef(
                sport=sport, gender=gender, season=season,
                year=entry["year"], level=entry["level"],
                url=entry["canonicalUrl"],
                cache_file=f"{_slugify(entry['canonicalUrl'])}.html",
            )
            refs.append(ref)
            # Fetch (cache hit usually). The hub_url is one of these.
            fetch_html(session, entry["canonicalUrl"], use_cache=use_cache)

    # Step 3 — write the index
    index = {
        "team_url": LEHS_TEAM_URL,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "throttle_seconds": THROTTLE_SECONDS,
        "refs": [vars(r) for r in refs],
    }
    INDEX_PATH.write_text(json.dumps(index, indent=2))

    print()
    print("=" * 70)
    print(f"Done. {len(refs)} sport-season URLs in index.")
    print(f"Cache: {CACHE_DIR}")
    print(f"Index: {INDEX_PATH}")
    print("\nNext: run python scripts/18_process_maxpreps.py")


if __name__ == "__main__":
    main()
