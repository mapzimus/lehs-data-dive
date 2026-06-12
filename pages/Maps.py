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

import base64
from pathlib import Path

import streamlit as st

from utils.branding import page_footer, sidebar_attribution
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


_MIME_BY_SUFFIX = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@st.cache_data(show_spinner=False)
def _image_data_uri(path_str: str) -> str:
    """Read an image off disk once per session and return a data: URI.

    Cached so the ~600 KB base64 string isn't re-encoded on every
    Streamlit rerun — only paid once per visitor.
    """
    path = Path(path_str)
    mime = _MIME_BY_SUFFIX.get(path.suffix.lower(), "image/png")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _preview_or_placeholder(
    filename: str, alt_text: str, link_url: str | None = None
) -> None:
    """Render the map preview image (with optional click-through link)
    or a dashed-line placeholder if the file isn't there yet.

    When `link_url` is provided, the image is wrapped in an <a> with
    target="_blank" so a click pops out to the standalone map app.
    The image is inlined as a base64 data URI so Streamlit's image
    server URL doesn't have to be reverse-engineered.
    """
    path = IMAGES_DIR / filename
    if path.exists():
        if link_url:
            data_uri = _image_data_uri(str(path))
            # Subtle hover hint: drop opacity slightly + outline so the
            # image reads as clickable. Border-radius matches the
            # rest of the dashboard's image styling.
            st.markdown(
                f"""
                <a href="{link_url}" target="_blank" rel="noopener noreferrer"
                   style="display:block; line-height:0; text-decoration:none;">
                  <img src="{data_uri}" alt="{alt_text}"
                       title="{alt_text} — opens in a new tab"
                       style="
                         width: 100%;
                         border-radius: 6px;
                         border: 1px solid #E0E5EB;
                         cursor: pointer;
                         transition: opacity 0.15s, box-shadow 0.15s;
                       "
                       onmouseover="this.style.opacity='0.85'; this.style.boxShadow='0 4px 14px rgba(10,31,68,0.15)';"
                       onmouseout="this.style.opacity='1'; this.style.boxShadow='none';" />
                </a>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.image(str(path), width="stretch")
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
        "Lynn-focused launch of the same engine that powers the MA Atlas, "
        "centered on the city and its census tracts."
    )

    _preview_or_placeholder(
        "lynn-maps-preview.png",
        "Lynn Maps preview",
        link_url="https://maxwellhowegis.com/Lynn-data-dive/maps/",
    )

    # Launch button sits directly under the preview so the image + CTA
    # read as a single unit. Detail copy follows below.
    st.link_button(
        "Open Lynn Maps  ↗",
        "https://maxwellhowegis.com/Lynn-data-dive/maps/",
        type="primary",
        width="stretch",
    )

    st.caption(
        "**How to read it:** click any census tract for its community-health "
        "profile, or click a school dot for enrollment and outcomes — darker "
        "shading means a higher value for the selected layer."
    )

    st.markdown(
        """
**What's in it**
- All **22 Lynn census tracts** as togglable polygons
- Every Lynn public school pinned — LEHS highlighted in gold,
  dot size scaled by enrollment
- **5 tract-level ACS layers**: median household income,
  % non-English at home, % foreign-born, % bachelor's-or-higher,
  % severely rent-burdened
- The same **35+ district / municipality choropleths** the MA Atlas
  carries (MCAS, graduation, demographics, finance, workforce), so
  you can compare Lynn to its neighbors and to other Gateway cities
- Surrounding MA municipalities for spatial context
- Year slider 2017–2026 · student-group filter · multiple color
  palettes · Jenks / quantile / equal-interval / continuous breaks
"""
    )

    st.markdown(
        """
**Use this map when you want to:**
- See how income, language, or rent burden varies
  **tract-by-tract** across Lynn
- Compare Lynn's stats against its immediate neighbors (Saugus,
  Swampscott, Marblehead, Nahant) or against the rest of MA
- Show neighborhood-scale inequality to a school committee or board
- Pin LEHS in context with every other Lynn school
"""
    )

# --- MA Atlas ----------------------------------------------------------------
with c_atlas:
    st.subheader("🏛️ MA Education Atlas")
    st.caption(
        "Statewide view. Every school district, every public school, "
        "every Gateway city — all on one map with 40+ metrics."
    )

    _preview_or_placeholder(
        "ma-atlas-preview.png",
        "MA Education Atlas preview",
        link_url="https://maxwellhowegis.com/ma-atlas/",
    )

    # Launch button sits directly under the preview so the image + CTA
    # read as a single unit. Detail copy follows below.
    st.link_button(
        "Open MA Atlas  ↗",
        "https://maxwellhowegis.com/ma-atlas/",
        type="primary",
        width="stretch",
    )

    st.caption(
        "**How to read it:** pick a metric to shade the whole state, then "
        "click any town, district, or school point to open its detail panel "
        "with the underlying numbers."
    )

    st.markdown(
        """
**What's in it**
- All **351 MA municipalities** as polygons
- **274 academic school districts** (dissolved town polygons)
- **82 charter schools**, **26 regional vocational** overlays
- **1,817 MA public schools** as togglable points
- Sticky right-side detail panel on every click
- **40+ joined metrics**: MCAS, graduation, AP, college plans,
  per-pupil spending, teacher workforce, retention, demographics
- Year slider 2017–2026 with animation playback
- Student-group filter (9 groups: Hispanic, Black, Asian, White,
  ELL, Former ELL, Low Income, SWD, High Needs)
- Multiple color palettes including a **bivariate** mode (two
  metrics shaded on one map)
- Jenks natural breaks · quantile · equal-interval · continuous
- **PNG export** with scope options (current view, whole state,
  selected feature, or by name)
"""
    )

    st.markdown(
        """
**Use this map when you want to:**
- Benchmark LEHS against **the 26 MA Gateway cities** by any metric
- See how the state's school spending stratifies geographically
- Track one metric across all 351 towns over the past decade
- Pair two metrics on the same map (bivariate mode) to see how
  they cluster — e.g., per-pupil spending against MCAS
"""
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
**[Data 101](/Data_101?embed=true)** — it covers the choropleth pattern plus the
other chart types this dashboard uses, with live examples.
"""
)

page_footer()
