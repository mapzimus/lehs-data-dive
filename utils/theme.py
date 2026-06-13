"""
In-app light/dark theme.

Default is light. The active theme comes from the URL (``?theme=dark``) so a
shared link keeps it, and ``theme_toggle()`` (in the sidebar control rail) flips
it. Two things follow the theme:

  * **Charts** — ``utils.charts.DEFAULT_LAYOUT`` resolves its colors from
    ``chart_tokens()`` at access time, so every ``**DEFAULT_LAYOUT`` call site
    re-themes with no per-page edits.
  * **App chrome** — ``theme_css()`` returns a dark stylesheet that
    ``sidebar_attribution()`` injects when dark is active.

``get_theme()`` is defensive: outside a Streamlit run context (e.g. the annual
report script that also splats ``DEFAULT_LAYOUT``) it just returns light.
"""

from __future__ import annotations

import streamlit as st

SUPPORTED = {"light", "dark"}
DEFAULT = "light"
_QP = "theme"


def get_theme() -> str:
    try:
        raw = st.query_params.get(_QP, DEFAULT)
    except Exception:
        return DEFAULT
    return raw if raw in SUPPORTED else DEFAULT


def set_theme(theme: str) -> None:
    if theme == DEFAULT:
        st.query_params.pop(_QP, None)
    elif theme in SUPPORTED:
        st.query_params[_QP] = theme


# Per-theme chart color tokens. Light values match the long-standing palette so
# the default look is unchanged.
_CHART_TOKENS = {
    "light": {
        "template": "simple_white",
        "plot_bgcolor": "#FAFBFD",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font_color": "#3F4D66",
        "hover_bgcolor": "white",
    },
    "dark": {
        "template": "plotly_dark",
        "plot_bgcolor": "#161B26",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font_color": "#C9D2E0",
        "hover_bgcolor": "#222a36",
    },
}


def chart_tokens(theme: str | None = None) -> dict:
    return _CHART_TOKENS[theme or get_theme()]


def theme_toggle(*, location=None) -> str:
    """Render the light/dark switcher in the sidebar rail; return active theme."""
    container = location if location is not None else st.sidebar
    order = ["light", "dark"]
    current = get_theme()
    choice = container.radio(
        "Theme",
        order,
        index=order.index(current),
        format_func=lambda t: {"light": "☀ Light", "dark": "🌙 Dark"}[t],
        horizontal=True,
        key="_ui_theme",
    )
    if choice != current:
        set_theme(choice)
        st.rerun()
    return choice


# Dark stylesheet for the app chrome. Scoped to stable Streamlit testids; light
# mode injects nothing, so the default look is untouched. Anything a selector
# misses simply stays light — additive, never breaking.
_DARK_CSS = """
<style>
:root { color-scheme: dark; }
.stApp, section.main, [data-testid="stAppViewContainer"] {
    background-color: #0E1117 !important;
    color: #C9D2E0 !important;
}
[data-testid="stHeader"] { background: #0E1117 !important; }
[data-testid="stSidebar"] { background-color: #161B26 !important; }
[data-testid="stSidebar"] * { color: #C9D2E0 !important; }
.stApp .stMarkdown, .stApp p, .stApp li, .stApp span,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label {
    color: #DCE3EF !important;
}
.stApp a { color: #8FB7FF !important; }
div[data-testid="stMetric"] {
    background: #161B26 !important;
    border: 1px solid #2C3340 !important;
    border-radius: 8px;
}
div[data-testid="stMetricValue"] { color: #FFFFFF !important; }
div[data-testid="stMetricLabel"] { color: #9AA7BD !important; }
[data-testid="stExpander"] details {
    background: #161B26 !important;
    border: 1px solid #2C3340 !important;
}
div[data-testid="stDataFrame"] { background: #161B26 !important; }
.stApp [data-testid="stAlert"] { background: #1A2230 !important; }
div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #161B26 !important;
    border-color: #2C3340 !important;
}
</style>
"""


def theme_css(theme: str | None = None) -> str:
    """Dark chrome stylesheet (or empty string in light mode)."""
    return _DARK_CSS if (theme or get_theme()) == "dark" else ""
