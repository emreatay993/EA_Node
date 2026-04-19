"""Make upstream DPF-operator Markdown renderable by Qt's ``TextEdit.MarkdownText``.

The Jinja template in ``ansys.dpf.core.documentation`` emits Markdown that embeds
inline HTML inside table cells (``<strong>``, ``<br>``, styled ``<span>`` badges)
and wraps each language example in ``<details>/<summary>``. Qt's Markdown parser
corrupts rows containing inline HTML and does not unfold ``<details>``, which is
why the Help pane shows empty Name columns and disconnected Output cells.

This module rewrites that input into a plain Qt-friendly subset. It is pure text
manipulation — no third-party dependency.
"""

from __future__ import annotations

import re

_STRONG_PATTERN = re.compile(r"<(?P<tag>strong|b)>(.*?)</(?P=tag)>", re.IGNORECASE | re.DOTALL)
_BADGE_PATTERN = re.compile(
    r"\s*<br\s*/?>\s*<span[^>]*>\s*(Required|Optional)\s*</span>",
    re.IGNORECASE,
)
_DETAILS_PATTERN = re.compile(
    r"<details>\s*<summary>\s*([^<]+?)\s*</summary>\s*(.*?)\s*</details>",
    re.IGNORECASE | re.DOTALL,
)
_STANDALONE_BR_PATTERN = re.compile(r"(?m)^\s*<br\s*/?>\s*$")
_INLINE_BR_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)


def prepare_for_qt(markdown: str) -> str:
    """Return a variant of ``markdown`` that Qt's MarkdownText can render cleanly."""
    if not markdown:
        return markdown
    text = markdown
    text = _DETAILS_PATTERN.sub(lambda m: f"**{m.group(1).strip()}**\n\n{m.group(2).strip()}", text)
    text = _BADGE_PATTERN.sub("", text)
    text = _STRONG_PATTERN.sub(lambda m: f"**{m.group(2).strip()}**", text)
    text = _STANDALONE_BR_PATTERN.sub("", text)
    text = _INLINE_BR_PATTERN.sub(" ", text)
    return text


__all__ = ["prepare_for_qt"]
