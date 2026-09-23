# Purpose: CorexClient facade for graph.get / get_node / find_nodes.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_nodes.py
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


def _compact(params: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


class GraphApi:
    """Facade for graph.get / get_node / find_nodes (read-only)."""

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    def get(
        self,
        *,
        workspace_id: str | None = None,
        scope: str | None = None,
        include_style: bool | None = None,
        include_properties: bool | None = None,
    ) -> dict[str, Any]:
        params = _compact(
            {
                "workspace_id": None if workspace_id is None else str(workspace_id),
                "scope": None if scope is None else str(scope),
                "include_style": None if include_style is None else bool(include_style),
                "include_properties": None if include_properties is None else bool(include_properties),
            }
        )
        return self._client.call("graph.get", params)

    def get_node(self, node_id: str) -> dict[str, Any]:
        return self._client.call("graph.get_node", {"node_id": str(node_id)})

    def find_nodes(
        self,
        *,
        query: str | None = None,
        type_id: str | None = None,
        title: str | None = None,
        title_contains: str | None = None,
        scope: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = _compact(
            {
                "query": None if query is None else str(query),
                "type_id": None if type_id is None else str(type_id),
                "title": None if title is None else str(title),
                "title_contains": None if title_contains is None else str(title_contains),
                "scope": None if scope is None else str(scope),
                "limit": None if limit is None else int(limit),
            }
        )
        return self._client.call("graph.find_nodes", params)


__all__ = ["GraphApi"]
