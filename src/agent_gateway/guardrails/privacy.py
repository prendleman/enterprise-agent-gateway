"""Privacy helpers."""

from __future__ import annotations

import re


def mask_api_key(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def sanitize_log_text(text: str, max_length: int = 200) -> str:
    trimmed = text[:max_length]
    return re.sub(r"\s+", " ", trimmed).strip()
