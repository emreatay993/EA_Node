# Purpose: Encode and decode the query ids of local file image:// preview providers exactly once.
# Map: feature_routes/media_image_video_pdf_refocus.md
# Tests: tests/test_preview_image_ids.py
"""Shared codec for ``image://<provider>/preview?key=value`` preview URLs.

Qt passes a provider the text after ``image://<provider>/`` with the query still
percent-encoded, so every value must be decoded exactly once. Values are often
already-encoded file URLs: decoding twice turns ``%23`` back into ``#`` and the
path is silently cut at a URL fragment. Values are percent-encoded rather than
form-encoded, so ``+`` stays literal (matching JavaScript ``encodeURIComponent``).
"""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote, unquote


def preview_image_url(provider_id: str, params: Mapping[str, object]) -> str:
    """Build a preview URL, omitting parameters whose value is ``None`` or blank."""
    query = "&".join(
        f"{quote(str(key), safe='')}={quote(str(value), safe='')}"
        for key, value in params.items()
        if value is not None and str(value) != ""
    )
    return f"image://{provider_id}/preview?{query}"


def preview_image_params(image_id: str) -> dict[str, str]:
    """Decode the query of a provider image id; the last occurrence of a key wins."""
    _path, _separator, query = str(image_id or "").partition("?")
    params: dict[str, str] = {}
    for field in query.split("&"):
        key, separator, value = field.partition("=")
        if separator and key:
            params[unquote(key)] = unquote(value)
    return params


__all__ = ["preview_image_params", "preview_image_url"]
