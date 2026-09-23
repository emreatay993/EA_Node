# Purpose: CorexClient facade for app.status / app.history / app.quit plus undo()/redo() sugar.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


class AppApi:
    """Facade for app.status / app.history / app.quit.

    Every method builds catalog params and returns ``client.call(op, params)``;
    the server validates, so the facade never re-implements rules.
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    def status(self) -> dict[str, Any]:
        """Instance identity, project, active workspace/view/scope, selection, run and busy flags."""
        return self._client.call("app.status", {})

    def history(self, action: str = "status") -> dict[str, Any]:
        """``undo`` | ``redo`` | ``status`` (depths only)."""
        return self._client.call("app.history", {"action": str(action)})

    def undo(self) -> dict[str, Any]:
        """Undo the last step in the active workspace; ``applied`` is False when there is nothing to undo."""
        return self.history("undo")

    def redo(self) -> dict[str, Any]:
        return self.history("redo")

    def quit(self, *, discard_unsaved: bool = False) -> dict[str, Any]:
        """Close the instance (PROJECT_DIRTY unless ``discard_unsaved``); the app exits ~250 ms after replying."""
        return self._client.call("app.quit", {"discard_unsaved": bool(discard_unsaved)})


__all__ = ["AppApi"]
