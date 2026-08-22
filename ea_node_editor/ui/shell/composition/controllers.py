from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt

from ea_node_editor.execution.headless_runtime import CorexRuntime
from ea_node_editor.ui.shell.controllers import (
    AddonManagerController,
    ProjectSessionController,
    RunController,
)
from ea_node_editor.ui.shell.window_search_scope_state import (
    WindowSearchScopeController,
)

if TYPE_CHECKING:
    from ea_node_editor.nodes.registry import NodeRegistry
    from ea_node_editor.ui.shell.composition.state import ShellStateDependencies
    from ea_node_editor.ui.shell.window import ShellWindow


@dataclass(frozen=True, slots=True)
class ShellControllerDependencies:
    search_scope_controller: WindowSearchScopeController
    addon_manager_controller: AddonManagerController
    project_session_controller: ProjectSessionController
    run_controller: RunController
    execution_client: object

    def attach(self, host: "ShellWindow") -> None:
        host.search_scope_controller = self.search_scope_controller
        host.addon_manager_controller = self.addon_manager_controller
        host.project_session_controller = self.project_session_controller
        host.run_controller = self.run_controller
        host.execution_client = self.execution_client


def _create_shell_execution_client(registry: "NodeRegistry") -> CorexRuntime:
    return CorexRuntime(registry=registry)


def create_controller_dependencies(
    host: "ShellWindow",
    state: "ShellStateDependencies",
    *,
    registry: "NodeRegistry",
) -> ShellControllerDependencies:
    search_scope_controller = WindowSearchScopeController(
        host, state.search_scope_state
    )
    addon_manager_controller = AddonManagerController(host)
    project_session_controller = ProjectSessionController(host)
    run_controller = RunController(host)
    execution_client = _create_shell_execution_client(registry)
    execution_client.subscribe(host.execution_event.emit)
    host.execution_event.connect(
        host._handle_execution_event, Qt.ConnectionType.QueuedConnection
    )
    return ShellControllerDependencies(
        search_scope_controller=search_scope_controller,
        addon_manager_controller=addon_manager_controller,
        project_session_controller=project_session_controller,
        run_controller=run_controller,
        execution_client=execution_client,
    )


__all__ = [
    "ShellControllerDependencies",
    "create_controller_dependencies",
]
