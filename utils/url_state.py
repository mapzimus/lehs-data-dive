"""
URL query-param state — make widget selections shareable via the page URL.

Streamlit reruns the whole script top-to-bottom on every interaction, so by
default a selectbox/radio/slider choice lives only in memory and is lost when a
visitor copies the URL to share "this exact view." These thin wrappers fix that:

  * on first render they seed the widget's default from ``st.query_params`` so a
    shared link like ``?detail_grp=English+Learners`` restores the selection, and
  * on change they write the chosen value back into the URL.

Every wrapper requires a stable ``key=`` — it doubles as the query-param name.
Keys are already unique within a page in this app, and only one page is mounted
at a time, so the bare key is used as the param name (readable URLs). If two
pages ever need the *same* key with *different* meaning, pass ``ns=`` to
namespace the param.

These wrappers are intentionally drop-in: ``qp_selectbox(label, options,
key=...)`` takes the same args as ``st.selectbox`` and returns the same value,
so retrofitting an existing call site is a one-line change.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

import streamlit as st


def _param_name(key: str, ns: str | None) -> str:
    return f"{ns}.{key}" if ns else key


def qp_get(key: str, default: Any = None, *, ns: str | None = None) -> Any:
    """Read a raw string value from the URL query params (or ``default``)."""
    return st.query_params.get(_param_name(key, ns), default)


def qp_set(key: str, value: Any, *, ns: str | None = None) -> None:
    """Write (or, if ``value`` is None, clear) a URL query param."""
    name = _param_name(key, ns)
    if value is None:
        st.query_params.pop(name, None)
    else:
        st.query_params[name] = str(value)


def _seed_index(options: Sequence[Any], raw: str | None, fallback: int) -> int:
    """Resolve the option index matching a raw URL string, else ``fallback``."""
    if raw is None:
        return fallback
    for i, opt in enumerate(options):
        if str(opt) == raw:
            return i
    return fallback


def qp_selectbox(
    label: str,
    options: Sequence[Any],
    *,
    key: str,
    index: int = 0,
    ns: str | None = None,
    **kwargs: Any,
) -> Any:
    """``st.selectbox`` whose selection round-trips through the URL.

    On first load the index is taken from ``?<key>=...`` if present; thereafter
    the user's choice is written back so the link stays shareable.
    """
    options = list(options)
    if not options:
        return None
    # Streamlit ignores ``index`` once ``key`` exists in session_state (i.e. after
    # the first interaction), so URL-seeding only steers the initial render — which
    # is exactly what a shared link needs.
    if key not in st.session_state:
        index = _seed_index(options, qp_get(key, ns=ns), index)
    value = st.selectbox(label, options, index=index, key=key, **kwargs)
    # Write back only on change to avoid a redundant rerun (Streamlit reruns when
    # query_params actually mutate; an identical assignment is a no-op).
    if value is not None and str(value) != qp_get(key, ns=ns):
        qp_set(key, value, ns=ns)
    return value


def qp_radio(
    label: str,
    options: Sequence[Any],
    *,
    key: str,
    index: int = 0,
    ns: str | None = None,
    **kwargs: Any,
) -> Any:
    """``st.radio`` whose selection round-trips through the URL."""
    options = list(options)
    if not options:
        return None
    if key not in st.session_state:
        index = _seed_index(options, qp_get(key, ns=ns), index)
    value = st.radio(label, options, index=index, key=key, **kwargs)
    if value is not None and str(value) != qp_get(key, ns=ns):
        qp_set(key, value, ns=ns)
    return value


def qp_multiselect(
    label: str,
    options: Sequence[Any],
    *,
    key: str,
    default: Sequence[Any] | None = None,
    ns: str | None = None,
    **kwargs: Any,
) -> list[Any]:
    """``st.multiselect`` whose selection round-trips through the URL (comma-joined)."""
    options = list(options)
    if key not in st.session_state:
        raw = qp_get(key, ns=ns)
        if raw is not None:
            wanted = {p for p in raw.split(",") if p}
            default = [o for o in options if str(o) in wanted]
    value = st.multiselect(label, options, default=list(default or []), key=key, **kwargs)
    encoded = ",".join(str(v) for v in value)
    if encoded != (qp_get(key, ns=ns) or ""):
        qp_set(key, encoded or None, ns=ns)
    return value


def qp_slider(
    label: str,
    *args: Any,
    key: str,
    value: Any = None,
    ns: str | None = None,
    cast: Callable[[str], Any] = float,
    **kwargs: Any,
) -> Any:
    """``st.slider`` whose value round-trips through the URL.

    Single-value sliders encode as ``v``; range sliders as ``lo,hi``. ``cast``
    converts the raw URL strings back to numbers (``float`` by default; pass
    ``int`` for integer sliders).
    """
    if key not in st.session_state:
        raw = qp_get(key, ns=ns)
        if raw is not None:
            try:
                parts = [cast(p) for p in raw.split(",") if p != ""]
                value = tuple(parts) if len(parts) > 1 else parts[0]
            except (ValueError, TypeError):
                pass
    result = st.slider(label, *args, value=value, key=key, **kwargs)
    encoded = ",".join(str(v) for v in result) if isinstance(result, tuple) else str(result)
    if encoded != (qp_get(key, ns=ns) or ""):
        qp_set(key, encoded, ns=ns)
    return result
