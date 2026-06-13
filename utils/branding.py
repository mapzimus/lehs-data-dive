"""Shared branding/attribution helpers — call from every page."""

import streamlit as st
import streamlit.components.v1 as components

from utils.i18n import language_toggle, t


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


# Global UI fixes injected on every page via a Streamlit components
# iframe. Same-origin with the parent, so window.parent.document reaches
# the real app DOM. Two jobs:
#
#   (1) NAV COLLAPSE — Streamlit's dict-based st.navigation renders each
#       section header as a clickable <header> that defaults to expanded.
#       With 10 pages in "The School (LEHS)" that pushes other sections
#       below the fold. We click the "View N more" truncation toggle so
#       every section is mounted, then collapse all sections except the
#       one containing the active page.
#
#   (2) STRIP target="_blank" — Streamlit's markdown renderer hard-codes
#       target="_blank" on every <a>. That makes every internal link in
#       a markdown list pop a new browser tab, which is especially bad
#       inside an iframe (visitors lose the embedding context). We strip
#       target on any <a href="/..."> so internal nav stays in-tab.
#
# Idempotent — runs once on first paint and again on each Streamlit
# mutation via a MutationObserver that disconnects after the page has
# settled.
_NAV_COLLAPSE_JS = """
<script>
(function () {
  const PARENT = window.parent.document;
  let didCollapse = false;

  // ----- (1) Sidebar nav-section collapse -----------------------------

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

  const applyNavCollapse = () => {
    if (didCollapse) return;  // one-shot — don't fight user toggles

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
      // Always keep "The School (LEHS)" expanded — it's the dashboard's core
      // section, so it stays open even when the active page is elsewhere.
      if ((h.textContent || '').trim() === 'The School (LEHS)') return;
      collapseSection(h);
    });

    didCollapse = true;
    // Note: don't disconnect the shared observer here — link stripping
    // (below) still wants tick() calls on later Streamlit re-renders.
    // The single hard-cap timeout at the bottom handles cleanup.
  };

  // ----- (2) Strip target="_blank" from internal links ---------------
  //
  // Streamlit's markdown renderer hardcodes target="_blank" on every
  // <a>. For internal multipage routes (href starts with "/") we want
  // navigation to stay in the current tab/iframe.
  //
  // Marker attribute (data-stripped) prevents re-processing the same
  // anchor on every mutation tick.

  const stripBlankTargets = () => {
    const links = PARENT.querySelectorAll(
      '[data-testid="stMarkdown"] a[href^="/"][target="_blank"]:not([data-stripped])'
    );
    links.forEach((a) => {
      a.removeAttribute('target');
      a.removeAttribute('rel');
      a.setAttribute('data-stripped', '1');
    });
  };

  // ----- Run + observe -----------------------------------------------

  const tick = () => {
    applyNavCollapse();
    stripBlankTargets();
  };

  tick();
  const obs = new MutationObserver(tick);
  obs.observe(PARENT.body, { childList: true, subtree: true });
  // Stop observing after a generous window — by then nav collapse and
  // the initial link sweep are both done, and any markdown that
  // appears later (a re-run that re-renders a markdown block) will
  // re-trigger this whole script on the next full page load.
  setTimeout(() => obs.disconnect(), 10000);
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

    # Sidebar control rail — language switcher (theme toggle + search join here
    # in later phases). Rendered once per page since this runs on every page.
    language_toggle()

    st.sidebar.markdown(
        f"""
        ---
        **LEHS Data Dive**
        {t("Built by")} **{AUTHOR_NAME}**
        [{AUTHOR_SITE}](https://{AUTHOR_SITE})
        """
    )


def page_footer() -> None:
    """Standard footer for every page."""
    st.divider()
    st.caption(
        t("Built by {author} · Data: MA DESE E2C Hub, profiles.doe.mass.edu, "
          "US Census, US Dept of Education · See Methodology for full citations.",
          author=AUTHOR_NAME)
    )


def crosslink_callout(text_md: str, url_path: str, label: str) -> None:
    """A bordered "see also" box linking to another page in the dashboard.

    `url_path` is the page's nav url_path (as registered in Home.py, e.g.
    "Accountability"), NOT a file path — st.page_link doesn't resolve under this
    app's st.navigation routing, so we render a plain in-app markdown link, which
    is the established cross-link pattern here.
    """
    with st.container(border=True):
        st.markdown(f"{text_md}\n\n[{label}](/{url_path})")
