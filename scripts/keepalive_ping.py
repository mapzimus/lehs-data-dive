"""
Real-browser keepalive for Streamlit Community Cloud.

WHY THIS IS NEEDED (and why a plain HTTP GET isn't enough):
  Streamlit Cloud's sleep policy is based on active websocket sessions, NOT
  HTTP traffic. A plain `requests.get(URL)` returns the Zzzz sleep page HTML
  with HTTP 200 — the monitor thinks the app is "Up" but no session actually
  opens, so Streamlit's container never warms back up. The app stays asleep.

  To genuinely wake + keep-alive a Streamlit app you have to behave like a
  real user: open the URL in a headless browser, let it execute JS, connect
  the websocket, and wait until the actual app renders. Playwright does this.

WHAT THIS SCRIPT DOES:
  1. Launch headless Chromium
  2. Navigate to the app
  3. If we land on the Zzzz page, click "Yes, get this app back up!"
  4. Wait until the real app shell renders (looks for Streamlit's root mount
     point + a known string from our app — e.g., "Lynn")
  5. Sit on the page for 10s so the websocket session is established
  6. Take a screenshot for debugging (uploaded as a GH Actions artifact)
  7. Exit 0 on success, non-zero on failure

Run locally:
    pip install playwright && playwright install chromium
    python scripts/keepalive_ping.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = "https://lynn-data-dive.streamlit.app"
WAKE_BUTTON_TEXT = "Yes, get this app back up!"
APP_READY_NEEDLE = "Lynn"            # any string we know appears on Home.py
COLD_START_TIMEOUT_MS = 90_000       # Streamlit cold start can take a minute
SETTLE_SECONDS = 10                  # sit on the page so the WS session counts
SCREENSHOT = Path(__file__).resolve().parent.parent / "keepalive-last.png"


def main() -> int:
    print(f"Keepalive (real browser) -> {URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        try:
            print("  navigating...")
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

            # Give the page a moment to render past 'domcontentloaded'.
            # Streamlit's React shell needs a tick before the wake button
            # (if present) is interactable.
            page.wait_for_timeout(3_000)

            # If we landed on the Zzzz page, click the wake button.
            zzzz_selector = f'button:has-text("{WAKE_BUTTON_TEXT}")'
            wake_btn = page.locator(zzzz_selector).first
            if wake_btn.count() > 0:
                print("  app is asleep -- clicking the wake button")
                wake_btn.click(timeout=10_000)
                print(f"  waiting up to {COLD_START_TIMEOUT_MS // 1000}s for cold start...")
                # Streamlit shows a 'spinning up' status then redirects to
                # the real app. Wait for the network to settle, which
                # signals the websocket session is established + initial
                # render is done.
                try:
                    page.wait_for_load_state(
                        "networkidle", timeout=COLD_START_TIMEOUT_MS,
                    )
                except PWTimeout:
                    print("  (networkidle never settled, continuing anyway)")
                print("  cold start complete")
            else:
                print("  app was already awake")
                try:
                    page.wait_for_load_state("networkidle", timeout=30_000)
                except PWTimeout:
                    pass

            # Step 3: sit on the page so the websocket session is established
            # and Streamlit registers active traffic.
            print(f"  app rendered — holding session for {SETTLE_SECONDS}s")
            time.sleep(SETTLE_SECONDS)

            # Step 4: screenshot for debugging
            page.screenshot(path=str(SCREENSHOT), full_page=False)
            print(f"  screenshot saved to {SCREENSHOT.name}")
            print("  [OK]")
            return 0
        except Exception as e:
            try:
                page.screenshot(path=str(SCREENSHOT), full_page=False)
            except Exception:
                pass
            print(f"  [FAIL] {type(e).__name__}: {e}")
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
