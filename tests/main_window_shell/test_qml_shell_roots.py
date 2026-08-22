from __future__ import annotations

from tests.main_window_shell.bridge_qml_boundaries import (
    ShellAddOnManagerQmlBoundaryTests,
    ShellInspectorBridgeQmlBoundaryTests,
    ShellLibraryBridgeQmlBoundaryTests,
    ShellStatusStripQmlBoundaryTests,
    ShellWorkspaceBridgeQmlBoundaryTests,
)
from tests.main_window_shell.shell_runtime_contracts import (
    MainWindowShellContentFullscreenStaticContractsTests,
)

__all__ = [
    "MainWindowShellContentFullscreenStaticContractsTests",
    "ShellAddOnManagerQmlBoundaryTests",
    "ShellInspectorBridgeQmlBoundaryTests",
    "ShellLibraryBridgeQmlBoundaryTests",
    "ShellStatusStripQmlBoundaryTests",
    "ShellWorkspaceBridgeQmlBoundaryTests",
]
