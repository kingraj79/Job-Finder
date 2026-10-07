"""Small shared helpers."""
from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(raw: str | None) -> str:
    """Turn ATS-provided HTML job descriptions into plain text."""
    if not raw:
        return ""
    # Entities first: content often arrives HTML-entity-encoded (e.g. "&lt;h2&gt;"),
    # so unescaping before stripping tags is what actually removes them. Some
    # sources double-encode (e.g. "&amp;nbsp;"), so unescape twice.
    text = html.unescape(html.unescape(raw))
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()
