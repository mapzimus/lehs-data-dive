"""
Ping the public Streamlit Cloud URL so the app doesn't go to sleep.

Streamlit Community Cloud naps apps after ~7 days of inactivity. The GitHub
Action at .github/workflows/keepalive.yml runs this script every 6 hours.

What "success" looks like:
  - HTTP 200 from the URL
  - The response body does NOT contain the "Zzzz" sleep page sentinel
  - Up to 3 retries with backoff if Streamlit is mid-wake (cold start ~30s)

Exits non-zero on persistent failure so GitHub emails you.
"""

from __future__ import annotations

import sys
import time

import requests

URL = "https://lynn-data-dive.streamlit.app"

# Use a realistic browser User-Agent. Streamlit's edge sometimes serves the
# sleep page to bot-like UAs even on a warm app.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SLEEP_SENTINELS = [
    "This app has gone to sleep",
    "Zzzz",
    "get this app back up",
]

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [10, 30]  # waits between attempts 1->2 and 2->3


def attempt(n: int) -> tuple[bool, str]:
    """One GET. Returns (ok, message)."""
    try:
        r = requests.get(URL, headers=HEADERS, timeout=60, allow_redirects=True)
    except Exception as e:
        return False, f"request raised: {e!r}"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    body = r.text
    hit = next((s for s in SLEEP_SENTINELS if s in body), None)
    if hit:
        return False, f"sleep-page sentinel matched: {hit!r}"
    # Final sanity: the real app page mentions Streamlit/Lynn somewhere
    if "Lynn" not in body and "streamlit" not in body.lower():
        return False, "body returned 200 but doesn't look like the app page"
    return True, f"OK ({len(body):,} bytes)"


def main() -> int:
    print(f"Pinging {URL}")
    for i in range(MAX_ATTEMPTS):
        ok, msg = attempt(i + 1)
        print(f"  attempt {i + 1}/{MAX_ATTEMPTS}: {msg}")
        if ok:
            return 0
        if i < len(BACKOFF_SECONDS):
            wait = BACKOFF_SECONDS[i]
            print(f"  waiting {wait}s before retry (app may be cold-starting)...")
            time.sleep(wait)
    print("  [FAIL] All attempts failed — app may be down or stuck on the sleep page.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
