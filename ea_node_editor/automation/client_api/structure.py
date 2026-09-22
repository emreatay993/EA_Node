# Purpose: CorexClient facade for group.wrap, subnode.*, scope.navigate, selection.set, layout.arrange.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


class StructureApi:
    """Facade for group.wrap, subnode.*, scope.navigate, selection.set, layout.arrange (T06 fills in the typed methods)."""

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)


__all__ = ["StructureApi"]
