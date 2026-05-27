"""
Process the cached MaxPreps HTML pages from scripts/17_download_maxpreps.py
into a tidy parquet for the Athletics page.

Reads:
  data/raw/maxpreps/_index.json
  data/raw/maxpreps/cache/<slug>.html  (one per sport-season-year)

Writes:
  data/processed/lehs_athletics.parquet
    columns:
      sport, gender, season, year, level
      wins, losses, ties, win_pct, games_played
      points_for, points_against, point_diff
      streak_length, streak_result
      conf_wins, conf_losses, conf_ties, conf_win_pct,
      conf_standing_place, league_name
      url
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import PROCESSED_DIR, RAW_DIR  # noqa: E402

MAXPREPS_RAW = RAW_DIR / "maxpreps"
CACHE_DIR = MAXPREPS_RAW / "cache"
INDEX_PATH = MAXPREPS_RAW / "_index.json"


def _extract_next_data(html: str) -> dict | None:
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                  html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _wlt_split(s: str | None) -> tuple[int | None, int | None, int | None]:
    """Parse a "W-L" or "W-L-T" string. Returns (None,None,None) on failure."""
    if not isinstance(s, str):
        return None, None, None
    parts = s.split("-")
    try:
        if len(parts) == 2:
            return int(parts[0]), int(parts[1]), 0
        if len(parts) == 3:
            return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        pass
    return None, None, None


def _row_from_standings(ref: dict, std: dict) -> dict | None:
    """Build one record from a single year's standingsData."""
    overall = std.get("overallStanding") or {}
    league = std.get("leagueStanding") or {}
    w, l, t = _wlt_split(overall.get("overallWinLossTies"))
    cw, cl, ct = _wlt_split(league.get("conferenceWinLossTies"))
    if w is None and overall.get("winningPercentage") is None:
        return None  # nothing usable
    return {
        "sport": ref.get("sport"),
        "gender": ref.get("gender"),
        "season": ref.get("season"),
        "year": ref.get("year"),
        "level": ref.get("level"),
        "wins": w,
        "losses": l,
        "ties": t,
        "games_played": (w or 0) + (l or 0) + (t or 0) if w is not None else None,
        "win_pct": overall.get("winningPercentage"),
        "points_for": overall.get("points"),
        "points_against": overall.get("pointsAgainst"),
        "point_diff": (
            (overall.get("points") or 0) - (overall.get("pointsAgainst") or 0)
            if overall.get("points") is not None else None
        ),
        "streak_length": overall.get("streak"),
        "streak_result": overall.get("streakResult"),
        "conf_wins": cw,
        "conf_losses": cl,
        "conf_ties": ct,
        "conf_win_pct": league.get("conferenceWinningPercentage"),
        "conf_standing_place": league.get("conferenceStandingPlacement"),
        "league_name": league.get("leagueName"),
        "url": ref.get("url"),
    }


def main() -> None:
    if not INDEX_PATH.exists():
        print(f"[X] index not found at {INDEX_PATH} — run scripts/17_download_maxpreps.py first")
        sys.exit(1)
    index = json.loads(INDEX_PATH.read_text())
    refs = index.get("refs", [])
    print(f"Processing {len(refs)} sport-season pages...")

    rows: list[dict] = []
    parse_fails: list[str] = []
    no_data: list[str] = []

    for ref in refs:
        cache_file = ref.get("cache_file")
        if not cache_file:
            continue
        path = CACHE_DIR / cache_file
        if not path.exists():
            no_data.append(cache_file)
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        nd = _extract_next_data(html)
        if not nd:
            parse_fails.append(cache_file)
            continue
        tc = (nd.get("props", {})
                .get("pageProps", {})
                .get("teamContext", {}))
        std = tc.get("standingsData")
        if not std:
            # Some old-year pages only expose lastYearStandingsData against
            # the (year+1) page. Skip silently — covered by other rows.
            no_data.append(cache_file)
            continue
        row = _row_from_standings(ref, std)
        if row:
            rows.append(row)

    if not rows:
        print("[X] zero rows extracted — investigate cache contents")
        sys.exit(1)

    df = pd.DataFrame(rows)
    # Sort: latest year first, then sport, then gender
    df["_year_sort"] = df["year"].str.split("-").str[0].astype(int)
    df = df.sort_values(["_year_sort", "sport", "gender"], ascending=[False, True, True])
    df = df.drop(columns=["_year_sort"])

    out_path = PROCESSED_DIR / "lehs_athletics.parquet"
    df.to_parquet(out_path, index=False)

    print()
    print(f"[OK] wrote {len(df):,} rows -> {out_path}")
    print(f"  sports:  {df['sport'].nunique()}")
    print(f"  years:   {sorted(df['year'].unique())[:5]} ... {sorted(df['year'].unique())[-3:]}")
    print(f"  parse fails:  {len(parse_fails)}")
    print(f"  missing data: {len(no_data)}")
    if parse_fails[:3]:
        print(f"    sample parse fails: {parse_fails[:3]}")


if __name__ == "__main__":
    main()
