"""
Section 9 — Athletics.

Lynn English Bulldogs athletics, from MaxPreps season records (back to
2004-05 where available) plus hand-curated pre-MaxPreps history and
notable-alumni content from assets/curated/lehs_athletics_history.yaml.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY
from utils.constants import ASSETS_DIR, IMAGES_DIR
from utils.data_loader import load_dataset

st.set_page_config(page_title="Athletics | LEHS", page_icon="🐶", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

_h_l, _h_r = st.columns([1, 5])
with _h_l:
    st.image(str(IMAGES_DIR / "lehs-bulldog.png"), width=130)
with _h_r:
    st.title("Lynn English Athletics")
    st.markdown(
        "**Home of the Bulldogs.** Season-by-season records for every "
        "varsity team going back to 2004-05, drawn from MaxPreps. Pre-MaxPreps "
        "history (state titles, notable seasons, legacy coaches, notable "
        "alumni) is hand-curated and grows over time — see the bottom of the "
        "page."
    )

st.divider()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

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
latest_label = (
    ath[ath["_year_num"] == LATEST_NUM]["year"].iloc[0]
)
latest = ath[ath["_year_num"] == LATEST_NUM].copy()

# Sport+gender uniqueness — Soccer Boys vs Soccer Girls are separate teams.
ath["team"] = ath["sport"] + " (" + ath["gender"] + ")"
latest["team"] = latest["sport"] + " (" + latest["gender"] + ")"

# ---------------------------------------------------------------------------
# Hero — current season at a glance
# ---------------------------------------------------------------------------

st.header(f"This Season at a Glance — 20{latest_label}")

active = latest[(latest["wins"].fillna(0) + latest["losses"].fillna(0)) > 0].copy()
total_teams = active["team"].nunique()
total_wins = int(active["wins"].fillna(0).sum())
total_losses = int(active["losses"].fillna(0).sum())
overall_pct = total_wins / max(total_wins + total_losses, 1)

best_row = active.sort_values("win_pct", ascending=False).head(1)
worst_row = active[active["games_played"].fillna(0) >= 5].sort_values("win_pct", ascending=True).head(1)

c1, c2, c3, c4 = st.columns(4)
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
with c4:
    if not worst_row.empty:
        w = worst_row.iloc[0]
        st.metric(
            "Lowest win rate",
            f"{w['team']}",
            f"{int(w['wins'])}-{int(w['losses'])} ({w['win_pct']:.1%})",
            delta_color="off",
        )

# Current-season table — all teams sorted by win pct
st.subheader("All teams — this season's standings")
table = (
    active.sort_values("win_pct", ascending=False)[
        ["team", "season", "wins", "losses", "ties", "win_pct",
         "league_name", "conf_standing_place"]
    ]
    .rename(columns={
        "team": "Team", "season": "Season",
        "wins": "W", "losses": "L", "ties": "T", "win_pct": "Win %",
        "league_name": "League", "conf_standing_place": "Standing",
    })
)
st.dataframe(
    table.style.format({"Win %": "{:.1%}"}),
    use_container_width=True, hide_index=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Per-team historical trend — sport picker → win pct over time
# ---------------------------------------------------------------------------

st.header("Season-by-Season Records")
st.caption("Pick a team to see its full MaxPreps history.")

team_options = sorted(ath["team"].unique())
# Default to the longest history team (most rows) so the chart looks meaningful
default_team = (
    ath.groupby("team").size().sort_values(ascending=False).index[0]
)
selected_team = st.selectbox(
    "Team", team_options,
    index=team_options.index(default_team),
)

team_df = ath[ath["team"] == selected_team].sort_values("_year_num").copy()
team_df["W-L"] = team_df.apply(
    lambda r: f"{int(r['wins'])}-{int(r['losses'])}" if pd.notna(r["wins"]) else "—",
    axis=1,
)

c1, c2 = st.columns([2, 3])
with c1:
    # Hero stats for the selected team
    seasons = len(team_df)
    total_w = int(team_df["wins"].fillna(0).sum())
    total_l = int(team_df["losses"].fillna(0).sum())
    all_pct = total_w / max(total_w + total_l, 1)
    best_season = team_df.sort_values("win_pct", ascending=False).head(1).iloc[0]
    st.metric(f"{selected_team} — career on MaxPreps", f"{total_w}-{total_l}",
              f"{all_pct:.1%} across {seasons} seasons", delta_color="off")
    st.metric(
        "Best season",
        f"20{best_season['year']}",
        f"{int(best_season['wins'])}-{int(best_season['losses'])} ({best_season['win_pct']:.1%})",
        delta_color="off",
    )

with c2:
    # Win % by season — bar
    fig = px.bar(
        team_df, x="year_display", y="win_pct", text="W-L",
        color="win_pct", color_continuous_scale=[(0, "#B71C1C"), (0.5, "#FBC02D"), (1, "#2E7D32")],
        range_color=(0, 1),
    )
    fig.add_hline(y=0.5, line_dash="dash", line_color="#455A64",
                  annotation_text=".500", annotation_position="right")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        **DEFAULT_LAYOUT,
        yaxis_tickformat=".0%",
        yaxis_title="Win %",
        xaxis_title="Season",
        coloraxis_showscale=False,
        yaxis_range=[0, 1.05],
        title=f"{selected_team} — win percentage by season",
    )
    st.plotly_chart(fig, use_container_width=True)

# Detailed table for the selected team
with st.expander(f"All {selected_team} seasons (full detail)", expanded=False):
    detail = team_df[[
        "year_display", "wins", "losses", "ties", "win_pct",
        "points_for", "points_against", "league_name", "conf_standing_place",
        "url",
    ]].rename(columns={
        "year_display": "Season", "wins": "W", "losses": "L", "ties": "T",
        "win_pct": "Win %", "points_for": "Pts For", "points_against": "Pts Against",
        "league_name": "League", "conf_standing_place": "Standing", "url": "MaxPreps",
    }).sort_values("Season", ascending=False)
    st.dataframe(
        detail.style.format({"Win %": "{:.1%}"}),
        use_container_width=True, hide_index=True,
        column_config={"MaxPreps": st.column_config.LinkColumn("MaxPreps")},
    )

st.divider()

# ---------------------------------------------------------------------------
# Multi-team comparison — all sports on one heatmap
# ---------------------------------------------------------------------------

st.header("Every Team, Every Year — Win % Heatmap")
st.caption(
    "One cell per (team, season) — color is win percentage. Empty cells mean "
    "the team didn't field that year, or didn't report data to MaxPreps."
)

heat = (
    ath.pivot_table(index="team", columns="year_display", values="win_pct", aggfunc="mean")
       .sort_index()
)
# Sort columns chronologically
heat = heat.reindex(sorted(heat.columns), axis=1)
fig = go.Figure(go.Heatmap(
    z=heat.values, x=list(heat.columns), y=list(heat.index),
    colorscale=[(0, "#B71C1C"), (0.5, "#FBC02D"), (1, "#2E7D32")],
    zmin=0, zmax=1,
    colorbar=dict(title="Win %", tickformat=".0%"),
    hovertemplate="<b>%{y}</b><br>Season %{x}<br>Win %: %{z:.0%}<extra></extra>",
))
fig.update_layout(
    **{k: v for k, v in DEFAULT_LAYOUT.items() if k != "height"},
    height=max(380, 28 * len(heat)),
    xaxis_title="Season", yaxis_title="",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Pre-MaxPreps history — curated YAML
# ---------------------------------------------------------------------------

st.header("Banners, Legacy & Notable Alumni")
st.caption(
    "MaxPreps coverage of LEHS begins in the mid-2000s. Everything older — "
    "and the stories around it — lives in a hand-curated file that grows over "
    "time. To add an entry, edit "
    "`assets/curated/lehs_athletics_history.yaml`."
)

_history_path = ASSETS_DIR / "curated" / "lehs_athletics_history.yaml"
if _history_path.exists():
    try:
        history = yaml.safe_load(_history_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        history = {}
        st.error(f"Couldn't parse `lehs_athletics_history.yaml`: {e}")
else:
    history = {}

# School history — short prose anchor before the structured lists
school_hist = history.get("school_history")
if school_hist:
    st.subheader("The school, briefly")
    st.markdown(school_hist)

# Current Athletic Director — features prominently because leadership
# context shapes how every other entry on the page reads.
ad = history.get("athletic_director") or {}
if ad:
    st.subheader("Athletic Director")
    cols = st.columns([3, 2])
    with cols[0]:
        st.markdown(
            f"### {ad.get('name', '—')}"
            + (f"  \n*Since {ad['since']}*" if ad.get("since") else "")
        )
        if ad.get("historic_note"):
            st.success(f"**Historic note.** {ad['historic_note']}")
        if ad.get("bio"):
            st.markdown(ad["bio"])
    with cols[1]:
        if ad.get("replaced"):
            st.markdown("**Replaced**")
            st.caption(ad["replaced"])

# Current head coaches roster
coaches = history.get("current_coaches") or []
if coaches:
    st.subheader("Current head coaches")
    for c in coaches:
        with st.expander(
            f"**{c.get('sport', '—')}** — {c.get('name', '')}"
            + (f"  ·  since {c['since']}" if c.get("since") else ""),
            expanded=False,
        ):
            if c.get("bio"):
                st.markdown(c["bio"])

# Rivalry — its own callout. The Thanksgiving game is the single most
# institutional sports thing about Lynn English.
riv = history.get("rivalry") or {}
if riv:
    st.subheader(f"The {riv.get('tradition', '')} Rivalry — Bulldogs vs {riv.get('opponent', '')}".strip())
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric("Series began", f"{riv.get('started', '—')}")
    with rc2:
        st.metric("All-time series", f"{riv.get('all_time_series', '—')}")
    with rc3:
        st.metric("Sport", f"{riv.get('sport', '—')}")
    if riv.get("most_recent"):
        st.markdown(f"**Most recent.** {riv['most_recent']}")
    if riv.get("venue"):
        st.markdown(f"**Venue.** {riv['venue']}")
    if riv.get("notes"):
        st.caption(riv["notes"])

# Championships
champs = history.get("championships") or []
if champs:
    st.subheader("Championships")
    for c in sorted(champs, key=lambda x: x.get("year", 0), reverse=True):
        st.markdown(
            f"**{c.get('year', '—')} · {c.get('sport', '')}** — "
            f"{c.get('level', '')}"
            + (f" · *Coach {c.get('coach', '')}*" if c.get("coach") else "")
            + (f" · Record {c.get('record', '')}" if c.get("record") else "")
        )
        if c.get("notes"):
            st.caption(c["notes"])

# Notable seasons
nots = history.get("notable_seasons") or []
if nots:
    st.subheader("Notable seasons")
    for n in sorted(nots, key=lambda x: x.get("year", 0), reverse=True):
        st.markdown(
            f"**{n.get('year', '—')} · {n.get('sport', '')}** — "
            + (f"Record {n.get('record', '')}" if n.get("record") else "")
            + (f" · *{n.get('league', '')}*" if n.get("league") else "")
        )
        if n.get("notes"):
            st.caption(n["notes"])

# Legacy coaches
coaches = history.get("legacy_coaches") or []
if coaches:
    st.subheader("Legacy coaches")
    for c in coaches:
        st.markdown(
            f"**{c.get('name', '—')}** · {c.get('sport', '')} · {c.get('years', '')}"
        )
        if c.get("highlights"):
            st.caption(c["highlights"])

# Hall of Fame — full class lists by induction year
hof = history.get("hall_of_fame") or []
if hof:
    st.subheader("Hall of Fame")
    st.caption(
        "The LEHS Athletics & Distinguished Alumni Hall of Fame inducts "
        "classes periodically. Full class lists below — names without "
        "additional notes mean the public record we've gathered so far "
        "doesn't include their specifics (yet)."
    )
    for cls in sorted(hof, key=lambda x: x.get("year", 0), reverse=True):
        ttl = f"**Class of {cls.get('year')}**"
        if cls.get("ceremony_date"):
            ttl += f"  ·  {cls['ceremony_date']}"
        if cls.get("location"):
            ttl += f"  ·  *{cls['location']}*"
        with st.expander(ttl, expanded=False):
            inductees = cls.get("inductees") or []
            if not inductees:
                if cls.get("notes"):
                    st.markdown(cls["notes"])
                else:
                    st.info("No inductee detail captured yet.")
            for ind in inductees:
                yr = ind.get("grad_year")
                line = f"**{ind.get('name', '—')}**"
                if yr:
                    line += f" (LEHS '{yr})"
                if ind.get("sport"):
                    line += f" · *{ind['sport']}*"
                st.markdown(line)
                if ind.get("notes"):
                    st.caption(ind["notes"])
            if cls.get("notes") and inductees:
                st.caption(cls["notes"])

# Venues & milestones — Manning Bowl history etc.
venues = history.get("venues") or []
if venues:
    st.subheader("Venues & milestones")
    for v in venues:
        st.markdown(f"### {v.get('name', '—')}")
        if v.get("history"):
            st.markdown(v["history"])

# Notable alumni
alumni = history.get("notable_alumni") or []
if alumni:
    st.subheader("Notable alumni")
    for a in alumni:
        st.markdown(
            f"**{a.get('name', '—')}** "
            + (f"(LEHS '{a.get('grad_year', '')})" if a.get("grad_year") else "")
            + (f" · {a.get('sport', '')}" if a.get("sport") else "")
        )
        if a.get("bio"):
            st.caption(a["bio"])

if not any([champs, nots, coaches, alumni]):
    st.info(
        "**No curated history yet.** Add championships, notable seasons, "
        "legacy coaches, and notable alumni to "
        "`assets/curated/lehs_athletics_history.yaml` and they'll render here."
    )

st.divider()

# ---------------------------------------------------------------------------
# Footnote — source attribution and methodology
# ---------------------------------------------------------------------------

st.caption(
    f"**Source.** Season records for {ath['_year_num'].min()}-"
    f"{ath['_year_num'].min() + 1 - 2000:02d} through 20{latest_label} pulled "
    "from [MaxPreps](https://www.maxpreps.com/ma/lynn/lynn-english-bulldogs/) "
    "via the Lynn English Bulldogs team page. MaxPreps coverage of MA HS "
    "sports is uneven for lower-profile sports in early years — gaps in the "
    "heatmap usually reflect missing MaxPreps data rather than seasons not "
    "fielded. **Pre-MaxPreps history & alumni** are hand-curated in "
    "`assets/curated/lehs_athletics_history.yaml`."
)
