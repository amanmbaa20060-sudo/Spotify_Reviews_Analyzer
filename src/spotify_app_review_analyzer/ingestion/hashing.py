from __future__ import annotations

import hashlib
import re


def normalize_text(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed


def content_hash(source_key: str, text: str, title: str | None = None) -> str:
    parts = [source_key, normalize_text(text)]
    if title:
        parts.append(normalize_text(title))
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
