from __future__ import annotations

import re
import unicodedata

_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def clean_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    without_html = _HTML_TAG.sub(" ", normalized)
    collapsed = _WS.sub(" ", without_html).strip()
    return collapsed
