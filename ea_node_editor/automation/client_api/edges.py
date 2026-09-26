# Purpose: CorexClient facade for edge.connect / update / delete plus label, style, enabled, display-mode, and reverse sugar.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


class EdgesApi:
    """Facade for edge.connect / update / delete.

    Style dicts accept the catalog keys (``color``, ``width``, ``pattern``,
    ``end_arrow`` / ``start_arrow``, ``path_mode``, ``display_mode``, ``label_color``,
    ``label_fraction``, ``label_rotation``) as well as the persisted ``stroke_*``,
    ``arrow_head`` / ``arrow_tail``, ``label_text_color``, ``label_position`` and
    ``label_orientation`` keys.
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    # ------------------------------------------------------------ edge.connect

    def connect(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
        *,
        replace_existing: bool = False,
        label: str | None = None,
        style: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "source_node_id": str(source_node_id),
            "source_port": str(source_port),
            "target_node_id": str(target_node_id),
            "target_port": str(target_port),
            "replace_existing": bool(replace_existing),
        }
        if label is not None:
            params["label"] = str(label)
        if style is not None:
            params["style"] = dict(style)
        return self._client.call("edge.connect", params)

    # ------------------------------------------------------------- edge.update

    def update(
        self,
        edge_id: str,
        *,
        label: str | None = None,
        style: Mapping[str, Any] | None = None,
        path_mode: str | None = None,
        enabled: bool | None = None,
        display_mode: str | None = None,
        reverse: bool = False,
        clear_style: bool = False,
        clear_label: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"edge_id": str(edge_id)}
        if label is not None:
            params["label"] = str(label)
        if style is not None:
            params["style"] = dict(style)
        if path_mode is not None:
            params["path_mode"] = str(path_mode)
        if enabled is not None:
            params["enabled"] = bool(enabled)
        if display_mode is not None:
            params["display_mode"] = str(display_mode)
        if reverse:
            params["reverse"] = True
        if clear_style:
            params["clear_style"] = True
        if clear_label:
            params["clear_label"] = True
        return self._client.call("edge.update", params)

    def set_label(self, edge_id: str, label: str) -> dict[str, Any]:
        return self.update(edge_id, label=label)

    def clear_label(self, edge_id: str) -> dict[str, Any]:
        return self.update(edge_id, clear_label=True)

    def set_style(self, edge_id: str, style: Mapping[str, Any], *, replace: bool = False) -> dict[str, Any]:
        return self.update(edge_id, style=style, clear_style=bool(replace))

    def clear_style(self, edge_id: str) -> dict[str, Any]:
        return self.update(edge_id, clear_style=True)

    def set_path_mode(self, edge_id: str, path_mode: str) -> dict[str, Any]:
        return self.update(edge_id, path_mode=path_mode)

    def set_display_mode(self, edge_id: str, display_mode: str) -> dict[str, Any]:
        return self.update(edge_id, display_mode=display_mode)

    def set_enabled(self, edge_id: str, enabled: bool = True) -> dict[str, Any]:
        return self.update(edge_id, enabled=bool(enabled))

    def reverse(self, edge_id: str) -> dict[str, Any]:
        return self.update(edge_id, reverse=True)

    # ------------------------------------------------------------- edge.delete

    def delete(self, edge_ids: Iterable[str] | str) -> dict[str, Any]:
        ids = [edge_ids] if isinstance(edge_ids, str) else [str(edge_id) for edge_id in edge_ids]
        return self._client.call("edge.delete", {"edge_ids": ids})


__all__ = ["EdgesApi"]
