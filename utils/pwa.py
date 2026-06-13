"""
Progressive Web App (PWA) support — make the dashboard installable to a phone
home screen / desktop.

Streamlit Community Cloud serves a fixed ``index.html`` we don't control, so we
can't add a ``<link rel="manifest">`` to its ``<head>`` the normal way. Instead
``inject_pwa()`` (called once per page from ``sidebar_attribution``) uses the
same proven ``window.parent.document`` trick the nav-collapse helper already
relies on: it injects a manifest (as a self-contained ``data:`` URI, so there's
no static-file-serving path to get wrong), the theme-color meta, and the Apple
touch icon into the real page head.

Icons are read from ``static/icons/`` and embedded as data URIs, so the manifest
is fully self-contained and works regardless of how/where static files are
served. This is best-effort: if the browser ignores it, nothing breaks — the
app simply isn't installable. Full installability (and a stable start_url) is
ultimately the job of the public wrapper page that embeds the app.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_ROOT = Path(__file__).resolve().parent.parent
_ICON_DIR = _ROOT / "static" / "icons"
_THEME_COLOR = "#0A1F44"   # LEHS navy
_BG_COLOR = "#FFFFFF"


@st.cache_data(show_spinner=False)
def _icon_data_uri(name: str) -> str:
    path = _ICON_DIR / name
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


@st.cache_data(show_spinner=False)
def _manifest_data_uri() -> str:
    icons = []
    for name, size in (("icon-192.png", "192x192"), ("icon-512.png", "512x512")):
        uri = _icon_data_uri(name)
        if uri:
            icons.append({"src": uri, "sizes": size, "type": "image/png",
                          "purpose": "any maskable"})
    manifest = {
        "name": "LEHS Data Dive",
        "short_name": "LEHS Data",
        "description": "Lynn English High School — data dashboard.",
        "start_url": ".",
        "scope": ".",
        "display": "standalone",
        "background_color": _BG_COLOR,
        "theme_color": _THEME_COLOR,
        "icons": icons,
    }
    blob = json.dumps(manifest)
    return "data:application/manifest+json;base64," + \
        base64.b64encode(blob.encode("utf-8")).decode("ascii")


def inject_pwa() -> None:
    """Inject the manifest + theme-color + apple-touch-icon into the page head.

    The manifest embeds its icons as data URIs (≈180 KB), so we inject it only
    once per session — the head tags persist across in-app page navigations, and
    re-sending the payload on every page would waste mobile data.
    """
    if st.session_state.get("_pwa_injected"):
        return
    manifest_uri = _manifest_data_uri()
    apple_icon = _icon_data_uri("icon-192.png")
    if not manifest_uri:
        return
    st.session_state["_pwa_injected"] = True
    js = f"""
    <script>
    (function () {{
      try {{
        const head = window.parent.document.head;
        if (!head || head.querySelector('link[rel="manifest"][data-lehs]')) return;
        const add = (tag, attrs) => {{
          const el = window.parent.document.createElement(tag);
          for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
          el.setAttribute('data-lehs', '1');
          head.appendChild(el);
        }};
        add('link', {{rel: 'manifest', href: {json.dumps(manifest_uri)}}});
        add('meta', {{name: 'theme-color', content: {json.dumps(_THEME_COLOR)}}});
        add('link', {{rel: 'apple-touch-icon', href: {json.dumps(apple_icon)}}});
        add('meta', {{name: 'apple-mobile-web-app-capable', content: 'yes'}});
        add('meta', {{name: 'apple-mobile-web-app-title', content: 'LEHS Data'}});
      }} catch (e) {{ /* best-effort; never break the page */ }}
    }})();
    </script>
    """
    components.html(js, height=0)
