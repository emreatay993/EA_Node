from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from ea_node_editor.ui.shell.controllers.workspace_io_ops import WorkspaceIOOps

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class _WorkspacePackageIOControllerProtocol(Protocol):
    def _custom_workflow_definitions(self) -> list[dict[str, Any]]: ...

    def _set_custom_workflow_definitions(self, definitions: list[dict[str, Any]]) -> None: ...

    def _prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, Any]],
    ) -> dict[str, Any] | None: ...


class WorkspacePackageIOController:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspacePackageIOControllerProtocol,
    ) -> None:
        self._ops = WorkspaceIOOps(host, controller)

    @staticmethod
    def custom_workflow_export_label(definition: dict[str, Any]) -> str:
        return WorkspaceIOOps.custom_workflow_export_label(definition)

    @staticmethod
    def custom_workflow_default_filename(name: object) -> str:
        return WorkspaceIOOps.custom_workflow_default_filename(name)

    def import_custom_workflow(self) -> None:
        self._ops.import_custom_workflow()

    def export_custom_workflow(self) -> None:
        self._ops.export_custom_workflow()

    def prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return self._ops.prompt_custom_workflow_export_definition(definitions)

    def import_node_package(self) -> None:
        self._ops.import_node_package()

    def export_node_package(self) -> None:
        self._ops.export_node_package()
