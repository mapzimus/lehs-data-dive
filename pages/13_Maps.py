"""
Section 13 — Maps.

The interactive maps live as standalone MapLibre GL JS apps (not
Streamlit components) for performance reasons:
  - Lynn-focused:  maxwellhowegis.com/Lynn-data-dive/maps/
  - MA Education Atlas:  maxwellhowegis.com/ma-atlas/

This page is the launch pad — st.link_button opens each in a new tab
on purpose. The Streamlit dashboard is itself iframed on the public
site, so opening a map *in-page* would nest iframes; popping out gives
the maps full-screen real estate they need to be useful.

Layout mirrors the user audit:
  - symmetric 2-column treatment (Lynn Maps no longer feels like an
    afterthought next to the MA Atlas)
  - user-facing hero copy (no MapLibre/vector-tile jargon)
  - "What's in it" + "Use this map when…" for each
  - preview image slots — drop assets/images/lynn-maps-preview.png and
    /ma-atlas-preview.png and they appear automatically
  - "Reading these maps" footer that cross-links to Data 101 for
    choropleth-curious newcomers
"""

from pathlib import Path

import streamlit as st

from utils.branding import sidebar_attribution
from utils.constants import IMAGES_DIR

st.set_page_config(page_title="Maps | LEHS", page_icon="🗺️", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.title("🗺️ Maps")

st.markdown(
    "Two interactive maps to explore Lynn and Massachusetts by geography. "
    "Click any shape or school to drill into the data; pan, zoom, filter, "
    "and export. Built as standalone apps so they have room to breathe — "
    "**each map opens in a new tab.**"
)

st.divider()

# ---------------------------------------------------------------------------
# Helper — show a preview image if it exists on disk, otherwise show a
# small placeholder that explains what should be there. Lets us ship
# the layout now and drop images in later.
# ---------------------------------------------------------------------------


def _preview_or_placeholder(filename: str, alt_text: str) -> None:
    path = IMAGES_DIR / filename
    if path.exists():
        st.image(str(path), use_container_width=True)
    else:
        st.markdown(
            f"""
            <div style="
                border: 1px dashed #B0BEC5;
                border-radius: 6px;
                background: #F5F7FA;
                color: #607D8B;
                padding: 2.5rem 1rem;
                text-align: center;
                font-size: 0.85rem;
                margin-bottom: 0.5rem;
            ">
              <div style="font-size: 2rem; margin-bottom: 0.25rem;">🗺️</div>
              <div><em>{alt_text}</em></div>
              <div style="font-size: 0.7rem; margin-top: 0.25rem;">
                Drop a screenshot at <code>assets/images/{filename}</code>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Two maps, side by side
# ---------------------------------------------------------------------------

c_lynn, c_atlas = st.columns(2, gap="large")

# --- Lynn Maps ---------------------------------------------------------------
with c_lynn:
    st.subheader("🏙️ Lynn Maps")
    st.caption(
        "Hyper-focused on the city. Census-tract demographics, every Lynn "
        "school pinned, plus surrounding towns (Saugus, Swampscott, "
        "Marblehead, Nahant) for context."
    )

    _preview_or_placeholder("lynn-maps-preview.png", "Lynn Maps preview")

    st.markdown(
        """
**What's in it**
- All 22 Lynn census tracts as togglable polygons
- Every LPS school pinned (color-coded by level: elementary,
  middle, high, alternative)
- ACS 5-year demographic layers: median income, % low-income,
  % foreign-born, % under 18
- EJScreen environmental layers (air quality, lead paint risk,
  proximity to hazardous sites)
- CDC PLACES community-health layers (asthma, chronic disease)
- Surrounding-town outlines for spatial context
"""
    )

    st.markdown(
        """
**Use this map when you want to:**
- See how poverty or language varies **block-by-block** across Lynn
- Sketch out the LEHS catchment area visually
- Show neighborhood-scale inequality to a school committee or board
- Pair a Lynn statistic with the environmental layer behind it
"""
    )

    st.link_button(
        "Open Lynn Maps  ↗",
        "https://maxwellhowegis.com/Lynn-data-dive/maps/",
        type="primary",
        use_container_width=True,
    )

# --- MA Atlas ----------------------------------------------------------------
with c_atlas:
    st.subheader("🏛️ MA Education Atlas")
    st.caption(
        "Statewide view. Every school district, every public school, "
        "every Gateway city — all on one map with 40+ metrics."
    )

    _preview_or_placeholder("ma-atlas-preview.png", "MA Education Atlas preview")

    st.markdown(
        """
**What's in it**
- All **351 MA municipalities** as polygons
- **274 academic school districts** (dissolved town polygons)
- **78 charter schools**, **26 regional vocational** overlays
- **1,700 MA public schools** as togglable points
- Sticky right-side detail panel on every click
- **40+ joined metrics**: MCAS, graduation, AP, college plans,
  per-pupil spending, teacher workforce, retention, demographics
- Year slider 2017–2026 with slideshow playback
- Student-group filter (Hispanic, Black, ELL, Low Income, …)
- 12 color palettes (color-blind-safe group at top)
- Jenks natural breaks · quantile · equal-interval · continuous
- Compare mode with split-screen + synced pan/zoom
- PNG export · shareable URL state
"""
    )

    st.markdown(
        """
**Use this map when you want to:**
- Benchmark LEHS against **the 26 MA Gateway cities** by any metric
- See how the state's school spending stratifies geographically
- Track one metric across all 351 towns over the past decade
- Build a side-by-side comparison (e.g., Lynn vs. Lawrence) with
  synced pan/zoom
"""
    )

    st.link_button(
        "Open MA Atlas  ↗",
        "https://maxwellhowegis.com/ma-atlas/",
        type="primary",
        use_container_width=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Footer — reading-these-maps primer
# ---------------------------------------------------------------------------

st.subheader("📖 Reading these maps")

st.markdown(
    """
Both maps use **choropleth shading**: each shape is colored by a value
— darker means more, lighter means less. Pick a metric from the
layer panel and the whole map re-shades. Click any shape to see the
underlying numbers in the detail panel.

**A note on map design.** These maps shade polygons (towns, tracts,
districts) instead of using bubbles whose *size* represents a value.
Bubble-size maps look dramatic but can mislead — a bubble that's
twice as wide is four times the area, which most people read as a
much bigger number than it actually is. Polygon shading keeps the
geography honest.

**New to reading maps and charts?** Start at
**[Data 101](/Data_101)** — it covers the choropleth pattern plus the
other chart types this dashboard uses, with live examples.
"""
)
