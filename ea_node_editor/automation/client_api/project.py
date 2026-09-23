# Purpose: CorexClient facade for project.open / new / save / save_as / stage_file (path or bytes).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

import base64
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


def _compact(params: Mapping[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values so omitted keyword arguments never reach the closed param schemas."""
    return {key: value for key, value in params.items() if value is not None}


class ProjectApi:
    """Facade for project.open / save / stage_file.

    Every method builds catalog params and returns ``client.call(op, params)``;
    the server validates, so the facade never re-implements rules.
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    def open(self, path: str | Path, *, discard_unsaved: bool = False) -> dict[str, Any]:
        """Open a ``.cxproj``; PROJECT_DIRTY unless ``discard_unsaved`` or the project is clean."""
        return self._client.call("project.open", {"path": str(path), "discard_unsaved": bool(discard_unsaved)})

    def new(self, *, discard_unsaved: bool = False) -> dict[str, Any]:
        """Start a blank project (``project.open`` with ``new=true``)."""
        return self._client.call("project.open", {"new": True, "discard_unsaved": bool(discard_unsaved)})

    def save(self, path: str | Path | None = None) -> dict[str, Any]:
        """Save in place, or Save As when ``path`` is given (INVALID_PARAMS for a never-saved project without path)."""
        return self._client.call("project.save", _compact({"path": None if path is None else str(path)}))

    def save_as(self, path: str | Path) -> dict[str, Any]:
        return self.save(path)

    def stage_file(
        self,
        path: str | Path | None = None,
        *,
        content: bytes | None = None,
        content_base64: str | None = None,
        filename: str | None = None,
        subdirectory: str | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        """Copy ``path`` (or write ``content`` / ``content_base64`` as ``filename``) into the project staging area."""
        if content is not None and content_base64 is None:
            content_base64 = base64.b64encode(bytes(content)).decode("ascii")
        params = _compact(
            {
                "path": None if path is None else str(path),
                "content_base64": content_base64,
                "filename": None if filename is None else str(filename),
                "subdirectory": None if subdirectory is None else str(subdirectory),
                "node_id": None if node_id is None else str(node_id),
            }
        )
        return self._client.call("project.stage_file", params)

    def stage_bytes(self, filename: str, content: bytes, **kwargs: Any) -> dict[str, Any]:
        return self.stage_file(content=content, filename=filename, **kwargs)


__all__ = ["ProjectApi"]
