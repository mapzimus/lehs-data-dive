"""
Lightweight UI internationalization (i18n).

Streamlit has no built-in translation layer, so this is a tiny gettext-style
helper backed by flat JSON catalogs in ``lang/``. **English is the source of
truth**: a call site reads ``t("Built by Maxwell Howe")`` and gets the English
string back unless the active language has a translation, in which case it
returns that. Missing translations fall back to English — never blank.

Why keep the English text inline as the lookup key (rather than abstract slugs)?
It keeps call sites readable, makes the extractor trivial (just find ``t("…")``),
and guarantees a sane fallback even before a catalog exists.

Active language comes from the URL (``?lang=es``) so a shared link preserves it;
``language_toggle()`` renders the switcher (in the sidebar control rail). Catalog
shape (``lang/es.json``)::

    {"_meta": {"status": "draft — pending native-speaker review"},
     "Built by Maxwell Howe": "Creado por Maxwell Howe", ...}

The ``_meta`` key is ignored for lookups.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

LANG_DIR = Path(__file__).resolve().parent.parent / "lang"

# Languages the UI offers. English is always the implicit source/fallback.
SUPPORTED = {"en": "English", "es": "Español"}
DEFAULT_LANG = "en"
_QP = "lang"  # URL query-param name


def get_language() -> str:
    """Active UI language code from the URL (``?lang=``), validated to SUPPORTED."""
    raw = st.query_params.get(_QP, DEFAULT_LANG)
    return raw if raw in SUPPORTED else DEFAULT_LANG


def set_language(lang: str) -> None:
    """Persist the chosen language to the URL (English clears the param)."""
    if lang == DEFAULT_LANG:
        st.query_params.pop(_QP, None)
    elif lang in SUPPORTED:
        st.query_params[_QP] = lang


def _catalog_sig(path: Path) -> int:
    try:
        s = path.stat()
        return hash((s.st_mtime_ns, s.st_size))
    except OSError:
        return 0


@st.cache_data(show_spinner=False)
def _load_catalog_cached(path_str: str, sig: int) -> dict[str, str]:
    # `sig` is part of the cache key so editing a catalog busts the cache
    # (same trick as utils.data_loader). Underscore-prefixed keys are metadata.
    try:
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, str)}


def _catalog(lang: str) -> dict[str, str]:
    if lang == DEFAULT_LANG:
        return {}
    path = LANG_DIR / f"{lang}.json"
    return _load_catalog_cached(str(path), _catalog_sig(path))


def t(text: str, /, **fmt: Any) -> str:
    """Translate ``text`` into the active language (English fallback).

    Optional ``**fmt`` keyword args run ``str.format`` on the result, so a
    string with placeholders translates *and* interpolates::

        t("October enrollment {n:,}", n=1727)

    Keep placeholders identical between the English source and the translation.
    """
    lang = get_language()
    out = _catalog(lang).get(text, text) if lang != DEFAULT_LANG else text
    if fmt:
        try:
            out = out.format(**fmt)
        except (KeyError, IndexError, ValueError):
            # A malformed translation must never crash a page — fall back to the
            # English source formatted with the same args.
            out = text.format(**fmt)
    return out


def language_toggle(*, location: Any = None) -> str:
    """Render the EN/ES switcher and return the active language code.

    Defaults to the sidebar (the shared control rail). Uses a horizontal radio
    so it reads as a compact toggle; selecting a language updates the URL and
    Streamlit reruns with the new catalog applied.
    """
    container = location if location is not None else st.sidebar
    codes = list(SUPPORTED)
    current = get_language()
    choice = container.radio(
        "Language / Idioma",
        codes,
        index=codes.index(current),
        format_func=lambda c: SUPPORTED[c],
        horizontal=True,
        key="_ui_lang",
    )
    if choice != current:
        set_language(choice)
        st.rerun()
    return choice


def translation_status(lang: str | None = None) -> str:
    """Return the catalog's ``_meta.status`` note (for a 'draft translation' banner)."""
    lang = lang or get_language()
    if lang == DEFAULT_LANG:
        return ""
    path = LANG_DIR / f"{lang}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("_meta", {}).get("status", ""))
    except (OSError, json.JSONDecodeError):
        return ""
