from __future__ import annotations

_WINDOWS_INVALID = '<>:"/\\|?*'
_UNCATEGORIZED = "_uncategorized"
_DOC_INDEX_FILENAME = "doc_index.json"


def sanitize_operator_doc_filename(name: str) -> str:
    normalized = str(name).replace("::", "_")
    for bad in _WINDOWS_INVALID:
        normalized = normalized.replace(bad, "_")
    return normalized


def operator_doc_relative_path(operator_name: str, scripting_name: str, category: str) -> str:
    file_name = sanitize_operator_doc_filename(scripting_name or operator_name)
    return f"{category or _UNCATEGORIZED}/{file_name}.md"


__all__ = [
    "_DOC_INDEX_FILENAME",
    "_UNCATEGORIZED",
    "operator_doc_relative_path",
    "sanitize_operator_doc_filename",
]
