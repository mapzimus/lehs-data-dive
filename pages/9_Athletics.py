"""
Section 9 — Athletics.

A tight core for Lynn English Bulldogs athletics from MaxPreps records:
this-season snapshot, the Thanksgiving rivalry, the real banners,
all-team standings, and a per-team win-% chart. The deep heritage (Hall
of Fame, legacy coaches, Manning Bowl, athlete-alumni) lives on the LEHS
History page. Both pages read assets/curated/lehs_athletics_history.yaml.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT
from utils.constants import ASSETS_DIR, IMAGES_DIR
from utils.data_loader import load_dataset

st.set_page_config(page_title="Athletics | LEHS", page_icon="🐶", layout="wide")
sidebar_attribution()

# --- Header ----------------------------------------------------------------
_h_l, _h_r = st.columns([1, 5])
with _h_l:
    st.image(str(IMAGES_DIR / "lehs-bulldog.png"), width=130)
with _h_r:
    st.title("Lynn English Athletics")
    st.markdown(
        "**Home of the Bulldogs.** Season-by-season win-loss records for "
        "every varsity team, from MaxPreps. The deep heritage — Hall of Fame, "
        "legacy coaches, the Manning Bowl story, athlete-alumni — is on the "
        "**[LEHS History](/LEHS_History?embed=true)** page."
    )

st.divider()

# --- Load data -------------------------------------------------------------
ath = load_dataset("lehs_athletics")
if ath.empty:
    st.info(
        "Athletics data not yet built. Run "
        "`python scripts/17_download_maxpreps.py` then "
        "`python scripts/18_process_maxpreps.py`."
    )
    st.stop()

# Add a sortable numeric year for charts and a friendly display year.
ath = ath.copy()
ath["_year_num"] = ath["year"].str.split("-").str[0].astype(int) + 2000
ath["year_display"] = ath["year"].apply(lambda y: f"20{y}")  # e.g. "2024-25"

# Most recent year present in the dataset.
LATEST_NUM = int(ath["_year_num"].max())
latest_label = ath[ath["_year_num"] == LATEST_NUM]["year"].iloc[0]
latest = ath[ath["_year_num"] == LATEST_NUM].copy()

# Team key — sport + gender, plus season *only when it disambiguates* (e.g.
# Soccer's COVID-era Fall II "spring" variant, which would otherwise pile up
# on the fall bars). Detect multi-season pairs from the full dataset.
_multi_season_pairs = {
    pair for pair, grp in ath.groupby(["sport", "gender"])
    if grp["season"].nunique() > 1
}

def _team_key(frame: pd.DataFrame) -> pd.Series:
    needs_season = frame.set_index(["sport", "gender"]).index.isin(_multi_season_pairs)
    base = frame["sport"].values + " (" + frame["gender"].values + ")"
    with_season = (
        frame["sport"].values + " (" + frame["gender"].values
        + ", " + frame["season"].values + ")"
    )
    return pd.Series(
        [w if needs else b for b, w, needs in zip(base, with_season, needs_season)],
        index=frame.index,
    )

ath["team"] = _team_key(ath)
latest["team"] = _team_key(latest)

# Curated history file feeds the rivalry, banners, coaches, and AD blocks.
_history_path = ASSETS_DIR / "curated" / "lehs_athletics_history.yaml"
history: dict = {}
if _history_path.exists():
    try:
        history = yaml.safe_load(_history_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        st.error(f"Couldn't parse `lehs_athletics_history.yaml`: {e}")

# --- This season at a glance ------------------------------------------------
st.header(f"This Season at a Glance — 20{latest_label}")

active = latest[(latest["wins"].fillna(0) + latest["losses"].fillna(0)) > 0].copy()
total_teams = active["team"].nunique()
total_wins = int(active["wins"].fillna(0).sum())
total_losses = int(active["losses"].fillna(0).sum())
overall_pct = total_wins / max(total_wins + total_losses, 1)

# Min-games threshold for the "best record" tile, so a 1-0 COVID sliver
# doesn't outrank a real 20-game season.
MIN_GAMES = 5
active_qualifying = active[active["games_played"].fillna(0) >= MIN_GAMES]
best_row = active_qualifying.sort_values("win_pct", ascending=False).head(1)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Varsity teams active", f"{total_teams}")
with c2:
    st.metric(
        "Combined record",
        f"{total_wins}-{total_losses}",
        f"{overall_pct:.1%} win rate",
        delta_color="off",
    )
with c3:
    if not best_row.empty:
        b = best_row.iloc[0]
        st.metric(
            "Best record",
            f"{b['team']}",
            f"{int(b['wins'])}-{int(b['losses'])} ({b['win_pct']:.1%})",
            delta_color="off",
        )

st.divider()

# --- Human interest — the rivalry, the banners, the bowl (up top) ----------
# The Thanksgiving game is the most institutional sports thing about LEHS.
riv = history.get("rivalry") or {}
if riv:
    st.header(
        f"The {riv.get('tradition', '')} Rivalry — Bulldogs vs "
        f"{riv.get('opponent', '')}".strip()
    )
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric("Series began", f"{riv.get('started', '—')}")
    with rc2:
        st.metric("All-time series", f"{riv.get('all_time_series', '—')}")
    with rc3:
        st.metric("Sport", f"{riv.get('sport', '—')}")
    if riv.get("most_recent"):
        st.markdown(f"**Most recent.** {riv['most_recent']}")
    if riv.get("notes"):
        st.caption(riv["notes"])

# Banners — only the real ones: the 2 D1 basketball state titles + the
# football GBL title. The YAML carries more (JROTC, co-champ years); skip them.
_REAL = ("state champions", "greater boston league champions")
banners = [
    c for c in (history.get("championships") or [])
    if any(k in str(c.get("level", "")).lower() for k in _REAL)
    and "co-champ" not in str(c.get("level", "")).lower()
    and "jrotc" not in str(c.get("sport", "")).lower()
]
if banners:
    st.subheader("Banners in the gym")
    for c in sorted(banners, key=lambda x: x.get("year", 0), reverse=True):
        st.markdown(
            f"**{c.get('year', '—')} · {c.get('sport', '')}** — "
            f"{c.get('level', '')}"
            + (f" · *Coach {c.get('coach', '')}*" if c.get("coach") else "")
            + (f" · {c.get('record', '')}" if c.get("record") else "")
        )

# Manning Bowl photo — image + a two-sentence caption only. The full
# venue history lives on the LEHS History page.
_bowl_img = IMAGES_DIR / "manning-bowl.jpg"
if _bowl_img.exists():
    st.image(
        str(_bowl_img),
        use_container_width=True,
        caption=(
            "Manning Bowl, Lynn (c. 1940s). The 21,000-seat stadium opened in "
            "1937 and hosted the Thanksgiving rivalry until it closed after the "
            "2004 game; Manning Field replaced it on the same site in 2005. "
            "Full history on the LEHS History page."
        ),
    )

st.divider()

# --- All teams — this season's standings (the most useful element) ---------
st.header("All Teams — This Season's Standings")
table = (
    active.sort_values("win_pct", ascending=False)[
        ["team", "season", "wins", "losses", "ties", "win_pct",
         "league_name", "conf_standing_place", "url"]
    ]
    .rename(columns={
        "team": "Team", "season": "Season",
        "wins": "W", "losses": "L", "ties": "T", "win_pct": "Win %",
        "league_name": "League", "conf_standing_place": "Standing",
        "url": "MaxPreps",
    })
)
st.dataframe(
    table.style.format({"Win %": "{:.1%}"}),
    use_container_width=True, hide_index=True,
    column_config={"MaxPreps": st.column_config.LinkColumn("MaxPreps", display_text="page")},
)

st.divider()

# --- Season-by-season — team picker → win % bar chart ----------------------
st.header("Season-by-Season Records")
st.caption("Pick a team to see its full MaxPreps win-percentage history.")

team_options = sorted(ath["team"].unique())
# Default to the longest-history team (most rows) so the chart looks meaningful.
default_team = ath.groupby("team").size().sort_values(ascending=False).index[0]
selected_team = st.selectbox("Team", team_options, index=team_options.index(default_team))

team_df = ath[ath["team"] == selected_team].sort_values("_year_num").copy()
team_df["W-L"] = team_df.apply(
    lambda r: f"{int(r['wins'])}-{int(r['losses'])}" if pd.notna(r["wins"]) else "—", axis=1,
)

fig = px.bar(
    team_df, x="year_display", y="win_pct", text="W-L", color="win_pct",
    color_continuous_scale=[(0, "#B71C1C"), (0.5, "#FBC02D"), (1, "#2E7D32")],
    range_color=(0, 1),
)
fig.add_hline(y=0.5, line_dash="dash", line_color="#455A64",
              annotation_text=".500", annotation_position="right")
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(
    **DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Win %",
    xaxis_title="Season", coloraxis_showscale=False, yaxis_range=[0, 1.05],
    # Force categorical x-axis — else "2024-25" parses as a YYYY-MM date and
    # Plotly truncates the axis (because "2012-13" is an invalid month).
    xaxis_type="category",
    title=f"{selected_team} — win percentage by season",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Who runs the program — AD one-liner + compact coaches roster ----------
st.header("Who Runs the Program")

ad = history.get("athletic_director") or {}
if ad:
    _line = f"**Athletic Director — {ad.get('name', '—')}**"
    if ad.get("since"):
        _line += f" (since {ad['since']})"
    if ad.get("historic_note"):
        _line += f". {ad['historic_note']}"
    st.markdown(_line)

coaches = history.get("current_coaches") or []
if coaches:
    roster = pd.DataFrame([
        {"Sport": c.get("sport", ""), "Head coach": c.get("name", ""),
         "Since": c.get("since", "") or "—"}
        for c in coaches
    ])
    st.dataframe(roster, use_container_width=True, hide_index=True)

st.caption(
    "Hall of Fame, legacy coaches, the full Manning Bowl history, and notable "
    "athlete-alumni live on the **[LEHS History](/LEHS_History?embed=true)** "
    "page (Athletics heritage tab)."
)

st.divider()

# --- Footnote — source attribution -----------------------------------------
st.caption(
    f"**Source.** Season records through 20{latest_label} from "
    "[MaxPreps](https://www.maxpreps.com/ma/lynn/lynn-english-bulldogs/). "
    "Coverage of lower-profile MA sports is uneven in early years, so a "
    "missing season usually means missing MaxPreps data, not a team that "
    "didn't field. **Pre-MaxPreps history & alumni** are hand-curated in "
    "`assets/curated/lehs_athletics_history.yaml`."
)
