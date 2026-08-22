from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol


PropertySourcePathResolver = Callable[[Any, str], str]


@dataclass(frozen=True, slots=True)
class PropertyEditAdapterContext:
    node: Any
    spec: Any | None = None
    workspace_id: str = ""
    workspace_nodes: Mapping[str, Any] | None = None
    workspace_edges: Any | None = None
    project_path: str | None = None
    project_metadata: Mapping[str, Any] | None = None
    source_path_resolver: PropertySourcePathResolver | None = None

    def source_path_for_property(self, property_key: str = "path", *, node: Any | None = None) -> str:
        if self.source_path_resolver is None:
            return ""
        return str(self.source_path_resolver(node or self.node, property_key) or "").strip()


@dataclass(frozen=True, slots=True)
class PropertyEditRewrite:
    key: str
    value: Any


class AddOnPropertyEditAdapter(Protocol):
    def rewrite_property_edit(
        self,
        context: PropertyEditAdapterContext,
        *,
        key: str,
        value: Any,
    ) -> PropertyEditRewrite | None: ...

    def build_property_items(
        self,
        context: PropertyEditAdapterContext,
        items: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]: ...


def rewrite_property_edit_with_adapters(
    adapters: Iterable[AddOnPropertyEditAdapter],
    context: PropertyEditAdapterContext,
    *,
    key: str,
    value: Any,
) -> PropertyEditRewrite | None:
    for adapter in adapters:
        rewrite = adapter.rewrite_property_edit(context, key=key, value=value)
        if rewrite is not None:
            return rewrite
    return None


def build_property_items_with_adapters(
    adapters: Iterable[AddOnPropertyEditAdapter],
    context: PropertyEditAdapterContext,
    items: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    resolved_items = [dict(item) for item in items]
    for adapter in adapters:
        resolved_items = adapter.build_property_items(context, resolved_items)
    return resolved_items


__all__ = [
    "AddOnPropertyEditAdapter",
    "PropertyEditAdapterContext",
    "PropertyEditRewrite",
    "PropertySourcePathResolver",
    "build_property_items_with_adapters",
    "rewrite_property_edit_with_adapters",
]
