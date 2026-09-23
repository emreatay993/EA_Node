# Purpose: CorexClient facade for catalog.list_node_types / describe_node_type / style_schema.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_nodes.py
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


def _compact(params: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


class CatalogApi:
    """Facade for catalog.list_node_types / describe_node_type / style_schema."""

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    def list_node_types(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        runtime_behavior: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params = _compact(
            {
                "query": None if query is None else str(query),
                "category": None if category is None else str(category),
                "runtime_behavior": None if runtime_behavior is None else str(runtime_behavior),
                "limit": None if limit is None else int(limit),
            }
        )
        return self._client.call("catalog.list_node_types", params)

    def describe_node_type(self, type_id: str) -> dict[str, Any]:
        return self._client.call("catalog.describe_node_type", {"type_id": str(type_id)})

    def style_schema(self) -> dict[str, Any]:
        return self._client.call("catalog.style_schema", {})


__all__ = ["CatalogApi"]
