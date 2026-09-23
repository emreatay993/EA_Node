# Purpose: CorexClient facade for workspace.* / view.* plus activate / frame sugar.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


def _compact(params: Mapping[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values so omitted keyword arguments never reach the closed param schemas."""
    return {key: value for key, value in params.items() if value is not None}


def _id_list(values: str | Iterable[str]) -> list[str]:
    return [values] if isinstance(values, str) else [str(value) for value in values]


class WorkspacesApi:
    """Facade for workspace.* / view.*.

    Every method builds catalog params and returns ``client.call(op, params)``;
    the server validates, so the facade never re-implements rules.
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    # -------------------------------------------------------------- workspaces

    def list(self) -> dict[str, Any]:
        return self._client.call("workspace.list", {})

    def create(
        self,
        name: str | None = None,
        *,
        duplicate_of: str | None = None,
        activate: bool | None = None,
    ) -> dict[str, Any]:
        params = _compact(
            {
                "name": None if name is None else str(name),
                "duplicate_of": None if duplicate_of is None else str(duplicate_of),
                "activate": None if activate is None else bool(activate),
            }
        )
        return self._client.call("workspace.create", params)

    def duplicate(self, workspace_id: str, *, name: str | None = None, activate: bool | None = None) -> dict[str, Any]:
        return self.create(name, duplicate_of=workspace_id, activate=activate)

    def update(self, workspace_id: str, *, name: str | None = None, activate: bool | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"workspace_id": str(workspace_id)}
        params.update(_compact({"name": None if name is None else str(name), "activate": None if activate is None else bool(activate)}))
        return self._client.call("workspace.update", params)

    def rename(self, workspace_id: str, name: str) -> dict[str, Any]:
        return self.update(workspace_id, name=name)

    def activate(self, workspace_id: str) -> dict[str, Any]:
        """Make ``workspace_id`` the active tab (graph ops always target the active workspace)."""
        return self.update(workspace_id, activate=True)

    def close(self, workspace_id: str, *, discard_unsaved: bool = False) -> dict[str, Any]:
        return self._client.call("workspace.close", {"workspace_id": str(workspace_id), "discard_unsaved": bool(discard_unsaved)})

    # ------------------------------------------------------------------- views

    def create_view(self, name: str | None = None, *, activate: bool | None = None) -> dict[str, Any]:
        params = _compact({"name": None if name is None else str(name), "activate": None if activate is None else bool(activate)})
        return self._client.call("view.create", params)

    def update_view(self, view_id: str, *, name: str | None = None, activate: bool | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"view_id": str(view_id)}
        params.update(_compact({"name": None if name is None else str(name), "activate": None if activate is None else bool(activate)}))
        return self._client.call("view.update", params)

    def activate_view(self, view_id: str) -> dict[str, Any]:
        return self.update_view(view_id, activate=True)

    def close_view(self, view_id: str) -> dict[str, Any]:
        return self._client.call("view.close", {"view_id": str(view_id)})

    def set_camera(
        self,
        *,
        zoom: float | None = None,
        center_x: float | None = None,
        center_y: float | None = None,
        frame: str | None = None,
        node_ids: str | Iterable[str] | None = None,
    ) -> dict[str, Any]:
        params = _compact(
            {
                "zoom": None if zoom is None else float(zoom),
                "center_x": None if center_x is None else float(center_x),
                "center_y": None if center_y is None else float(center_y),
                "frame": None if frame is None else str(frame),
                "node_ids": None if node_ids is None else _id_list(node_ids),
            }
        )
        return self._client.call("view.set_camera", params)

    def frame_all(self) -> dict[str, Any]:
        return self.set_camera(frame="all")

    def frame_selection(self) -> dict[str, Any]:
        return self.set_camera(frame="selection")

    def frame_nodes(self, node_ids: str | Iterable[str]) -> dict[str, Any]:
        return self.set_camera(frame="nodes", node_ids=node_ids)


__all__ = ["WorkspacesApi"]
