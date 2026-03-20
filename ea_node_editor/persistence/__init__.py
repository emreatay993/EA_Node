from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "JsonProjectSerializer",
    "JsonProjectMigration",
    "JsonProjectCodec",
    "SessionAutosaveStore",
]

if TYPE_CHECKING:
    from ea_node_editor.persistence.migration import JsonProjectMigration
    from ea_node_editor.persistence.project_codec import JsonProjectCodec
    from ea_node_editor.persistence.serializer import JsonProjectSerializer
    from ea_node_editor.persistence.session_store import SessionAutosaveStore


def __getattr__(name: str) -> Any:
    if name == "JsonProjectMigration":
        from ea_node_editor.persistence.migration import JsonProjectMigration

        globals()[name] = JsonProjectMigration
        return JsonProjectMigration
    if name == "JsonProjectCodec":
        from ea_node_editor.persistence.project_codec import JsonProjectCodec

        globals()[name] = JsonProjectCodec
        return JsonProjectCodec
    if name == "JsonProjectSerializer":
        from ea_node_editor.persistence.serializer import JsonProjectSerializer

        globals()[name] = JsonProjectSerializer
        return JsonProjectSerializer
    if name == "SessionAutosaveStore":
        from ea_node_editor.persistence.session_store import SessionAutosaveStore

        globals()[name] = SessionAutosaveStore
        return SessionAutosaveStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
