from __future__ import annotations

from dataclasses import dataclass

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.workspace.ownership import sync_project_workspace_ownership


@dataclass(slots=True)
class WorkspaceRef:
    workspace_id: str
    name: str
    dirty: bool


class WorkspaceManager:
    def __init__(self, model: GraphModel) -> None:
        self._model = model
        self._sync_workspace_ownership()

    def _sync_workspace_ownership(self) -> list[str]:
        sync_project_workspace_ownership(self._model.project)
        return self._model.project.metadata["workspace_order"]

    def list_workspaces(self) -> list[WorkspaceRef]:
        order = self._sync_workspace_ownership()
        refs: list[WorkspaceRef] = []
        for workspace_id in order:
            workspace = self._model.project.workspaces[workspace_id]
            refs.append(
                WorkspaceRef(
                    workspace_id=workspace.workspace_id,
                    name=workspace.name,
                    dirty=workspace.dirty,
                )
            )
        return refs

    def create_workspace(self, name: str | None = None) -> str:
        workspace = self._model._create_workspace_record(name=name)
        order = self._sync_workspace_ownership()
        if workspace.workspace_id not in order:
            order.append(workspace.workspace_id)
        self._model._set_active_workspace_id(workspace.workspace_id)
        return workspace.workspace_id

    def rename_workspace(self, workspace_id: str, new_name: str) -> None:
        self._model._rename_workspace_record(workspace_id, new_name)

    def duplicate_workspace(self, workspace_id: str) -> str:
        source_order = list(self._sync_workspace_ownership())
        duplicated = self._model._duplicate_workspace_record(workspace_id)
        order = self._sync_workspace_ownership()
        if duplicated.workspace_id in order:
            order.remove(duplicated.workspace_id)
        try:
            source_index = source_order.index(workspace_id)
        except ValueError:
            source_index = len(order) - 1
        order.insert(source_index + 1, duplicated.workspace_id)
        self._model._set_active_workspace_id(duplicated.workspace_id)
        return duplicated.workspace_id

    def close_workspace(self, workspace_id: str) -> None:
        order = self._sync_workspace_ownership()
        if workspace_id not in self._model.project.workspaces:
            return
        was_active = self._model.project.active_workspace_id == workspace_id
        close_index = order.index(workspace_id) if workspace_id in order else -1
        self._model._close_workspace_record(workspace_id)
        order = self._sync_workspace_ownership()
        if was_active and order:
            next_index = min(max(close_index, 0), len(order) - 1)
            self._model._set_active_workspace_id(order[next_index])

    def set_active_workspace(self, workspace_id: str) -> None:
        self._model._set_active_workspace_id(workspace_id)

    def create_view(
        self,
        workspace_id: str,
        name: str | None = None,
        *,
        source_view_id: str | None = None,
    ) -> str:
        view = self._model.create_view(workspace_id, name=name, source_view_id=source_view_id)
        return view.view_id

    def set_active_view(self, workspace_id: str, view_id: str) -> None:
        self._model.set_active_view(workspace_id, view_id)

    def close_view(self, workspace_id: str, view_id: str) -> None:
        self._model.close_view(workspace_id, view_id)

    def rename_view(self, workspace_id: str, view_id: str, new_name: str) -> None:
        self._model.rename_view(workspace_id, view_id, new_name)

    def move_view(self, workspace_id: str, from_index: int, to_index: int) -> None:
        self._model.move_view(workspace_id, from_index, to_index)

    def move_workspace(self, from_index: int, to_index: int) -> None:
        order = self._sync_workspace_ownership()
        if len(order) < 2:
            return
        if from_index < 0 or from_index >= len(order):
            return
        to_index = max(0, min(to_index, len(order) - 1))
        if from_index == to_index:
            return
        workspace_id = order.pop(from_index)
        order.insert(to_index, workspace_id)

    def active_workspace_id(self) -> str:
        order = self._sync_workspace_ownership()
        active_id = self._model.project.active_workspace_id
        if active_id in self._model.project.workspaces:
            return active_id
        fallback_id = order[0]
        self._model._set_active_workspace_id(fallback_id)
        return fallback_id
