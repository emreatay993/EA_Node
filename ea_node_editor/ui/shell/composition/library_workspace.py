from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ea_node_editor.ui.shell.controllers import WorkspaceLibraryController

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


@dataclass(frozen=True, slots=True)
class ShellLibraryWorkspaceDependencies:
    workspace_library_controller: WorkspaceLibraryController

    def attach(self, host: "ShellWindow") -> None:
        host.workspace_library_controller = self.workspace_library_controller
        host.workflow_library_controller = self.workspace_library_controller.workflow_library_controller
        host.workspace_navigation_controller = self.workspace_library_controller.workspace_navigation_controller
        host.workspace_graph_edit_controller = self.workspace_library_controller.workspace_graph_edit_controller
        host.workspace_package_io_controller = self.workspace_library_controller.workspace_package_io_controller


def create_library_workspace_dependencies(host: "ShellWindow") -> ShellLibraryWorkspaceDependencies:
    return ShellLibraryWorkspaceDependencies(
        workspace_library_controller=WorkspaceLibraryController(host),
    )


__all__ = [
    "ShellLibraryWorkspaceDependencies",
    "create_library_workspace_dependencies",
]
