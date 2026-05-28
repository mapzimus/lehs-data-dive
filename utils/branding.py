"""Shared branding/attribution helpers — call from every page."""

import streamlit as st
import streamlit.components.v1 as components


AUTHOR_NAME = "Maxwell Howe"
AUTHOR_SITE = "maxwellhowegis.com"


# Mobile-responsive CSS injected once per page via sidebar_attribution().
# Targets Streamlit's built-in UI plus our custom layouts so the dashboard
# actually works on a phone screen.
_MOBILE_CSS = """
<style>
/* Desktop default: shrink Streamlit's generous block-container top padding
   so the hero starts higher and pages feel less spacious. Fires on every
   viewport; mobile media query below overrides if needed. */
.main .block-container,
section.main > div.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
}

@media (max-width: 768px) {
    /* === Streamlit sidebar collapse button — MUST be findable on mobile === */
    button[data-testid="collapsedControl"],
    button[kind="header"] {
        background: #0A1F44 !important;
        color: #FFB81C !important;
        border: 2px solid #FFB81C !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        box-shadow: 0 2px 8px rgba(10, 31, 68, 0.25) !important;
        margin: 8px !important;
    }
    button[data-testid="collapsedControl"] svg,
    button[kind="header"] svg {
        color: #FFB81C !important;
        fill: #FFB81C !important;
        width: 24px !important;
        height: 24px !important;
    }

    /* === Headings — tighter sizing on mobile === */
    .stMarkdown h1 { font-size: 1.7rem !important; line-height: 1.2; }
    .stMarkdown h2 { font-size: 1.35rem !important; }
    .stMarkdown h3 { font-size: 1.15rem !important; }

    /* === Reduce app padding so charts get more real estate === */
    .main .block-container,
    section.main > div.block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 0.75rem !important;
    }

    /* === Column-based metric tiles — stack vertically when narrow ===
       Streamlit columns become flex children. When 3-5 columns are
       displayed on mobile, each is too narrow to read. Force them to
       wrap to their own row. */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
        margin-bottom: 0.5rem;
    }

    /* === Metric tiles compact === */
    div[data-testid="stMetric"] {
        padding: 0.4rem 0.5rem !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }

    /* === Plotly charts — let them shrink to container; we don't want
       horizontal scroll on small screens === */
    .js-plotly-plot {
        max-width: 100% !important;
    }

    /* === Images — never overflow the column === */
    .stImage img {
        max-width: 100% !important;
        height: auto !important;
    }

    /* === DataFrames — allow horizontal scroll instead of overflowing === */
    div[data-testid="stDataFrame"] {
        overflow-x: auto !important;
    }
}

/* On very narrow screens, dial back even further */
@media (max-width: 480px) {
    .stMarkdown h1 { font-size: 1.45rem !important; }
    .stMarkdown h2 { font-size: 1.2rem !important; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
}
</style>
"""


# Streamlit's dict-based st.navigation renders each section header as a
# clickable <header data-testid="stNavSectionHeader"> that defaults to
# expanded. With 10 pages in "The School (LEHS)", that pushes
# Lynn/Comparison/About below the fold. There's also a global "View 8
# more" truncation that hides sections beyond the first ~8 items.
#
# This snippet runs in a Streamlit components iframe (same-origin with
# the parent, so window.parent.document reaches the real sidebar DOM):
#
#   1. If "View 8 more" is showing, click it so every section is mounted.
#   2. Collapse every section EXCEPT the one containing the active page.
#   3. Mark sections that the user has toggled themselves so reruns
#      don't fight them.
#
# Idempotent — runs once on first render via a MutationObserver that
# disconnects after the nav has settled.
_NAV_COLLAPSE_JS = """
<script>
(function () {
  const PARENT = window.parent.document;
  let didCollapse = false;
  let obs = null;

  // Section "collapsed" state can't be read from the icon (it always
  // says "expand_more"); the only reliable check is whether the section
  // wrapper contains <li> children — expanded sections have them,
  // collapsed sections don't.
  const sectionLiCount = (header) => {
    const sec = header.closest('[data-testid="stSidebarNavItems"] > div');
    return sec ? sec.querySelectorAll('li').length : 0;
  };

  const collapseSection = (header) => {
    if (sectionLiCount(header) === 0) return;  // already collapsed
    // Clicking the <header> would navigate to its first link; the
    // expand/collapse hit-target is the <span> wrapping the icon.
    const target = header.querySelector('[data-testid="stIconMaterial"]')?.parentElement;
    if (target) target.click();
  };

  const apply = () => {
    if (didCollapse) {
      if (obs) obs.disconnect();
      return;
    }

    const nav = PARENT.querySelector('[data-testid="stSidebarNav"]');
    if (!nav) return;

    // Expand the "View N more" truncation so every section header is
    // mounted in the DOM before we try to collapse them.
    const viewBtn = nav.querySelector('[data-testid="stSidebarNavViewButton"]');
    if (viewBtn && /view\\s+\\d+\\s+more/i.test(viewBtn.textContent)) {
      viewBtn.click();
      return;  // Wait for the next mutation tick.
    }

    const headers = nav.querySelectorAll('[data-testid="stNavSectionHeader"]');
    if (!headers.length) return;

    const activeLink = nav.querySelector('a[aria-current="page"]');
    const activeSection = activeLink
      ? activeLink.closest('[data-testid="stSidebarNavItems"] > div')
      : null;

    headers.forEach((h) => {
      const section = h.closest('[data-testid="stSidebarNavItems"] > div');
      if (section === activeSection) return;  // keep current page's section open
      collapseSection(h);
    });

    didCollapse = true;
    if (obs) obs.disconnect();
  };

  apply();
  obs = new MutationObserver(apply);
  obs.observe(PARENT.body, { childList: true, subtree: true });
  // Hard cap — bail out after a few seconds even if something stalls.
  setTimeout(() => { if (obs) obs.disconnect(); }, 5000);
})();
</script>
"""


def sidebar_attribution() -> None:
    """Render the author attribution + inject global mobile-responsive CSS.

    Called from every page, so the CSS lands on every page.
    """
    # Inject the mobile CSS once per page (Streamlit re-renders on each
    # interaction, but the style tag idempotently overrides).
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)

    # Collapse non-active sidebar nav sections on first load. height=0
    # keeps the helper iframe invisible.
    components.html(_NAV_COLLAPSE_JS, height=0)

    st.sidebar.markdown(
        f"""
        ---
        **LEHS Data Dive**
        Built by **{AUTHOR_NAME}**
        [{AUTHOR_SITE}](https://{AUTHOR_SITE})
        """
    )


def page_footer() -> None:
    """Standard footer for every page."""
    st.divider()
    st.caption(
        f"Built by {AUTHOR_NAME} · "
        f"Data: MA DESE E2C Hub, profiles.doe.mass.edu, US Census, "
        f"US Dept of Education · See Methodology for full citations."
    )
