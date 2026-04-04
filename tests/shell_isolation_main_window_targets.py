"""Main-window shell isolation targets."""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _build_targets():
    from tests.shell_isolation_runtime import ShellIsolationTarget

    return (
        ShellIsolationTarget.unittest_module(
            "tests.main_window_shell.drop_connect_and_workflow_io",
            target_id="main_window__drop_connect_and_workflow_io",
        ),
        ShellIsolationTarget.unittest_module(
            "tests.main_window_shell.edit_clipboard_history",
            target_id="main_window__edit_clipboard_history",
        ),
        ShellIsolationTarget.unittest_module(
            "tests.main_window_shell.passive_property_editors",
            target_id="main_window__passive_property_editors",
        ),
        ShellIsolationTarget.unittest_module(
            "tests.main_window_shell.passive_style_context_menus",
            target_id="main_window__passive_style_context_menus",
        ),
        ShellIsolationTarget.unittest_module(
            "tests.main_window_shell.shell_basics_and_search",
            target_id="main_window__shell_basics_and_search",
        ),
        ShellIsolationTarget.unittest_module(
            "tests.main_window_shell.view_library_inspector",
            target_id="main_window__view_library_inspector",
        ),
        ShellIsolationTarget.pytest_nodeid(
            "tests/main_window_shell/passive_image_nodes.py::MainWindowShellPassiveImageNodesTests",
            target_id="main_window__passive_image_nodes",
            extra_env={"EA_NODE_EDITOR_PASSIVE_IMAGE_NODES_DIRECT": "1"},
        ),
        ShellIsolationTarget.pytest_nodeid(
            "tests/main_window_shell/passive_pdf_nodes.py::MainWindowShellPassivePdfNodesTests",
            target_id="main_window__passive_pdf_nodes",
            extra_env={"EA_NODE_EDITOR_PASSIVE_PDF_NODES_DIRECT": "1"},
        ),
        ShellIsolationTarget.pytest_nodeid_list(
            "main_window__bridge_local_pack",
            (
                "tests/main_window_shell/shell_runtime_contracts.py::FrameRateSamplerTests",
                "tests/main_window_shell/bridge_contracts.py::ShellLibraryBridgeTests",
                "tests/main_window_shell/bridge_contracts.py::ShellInspectorBridgeTests",
                "tests/main_window_shell/bridge_contracts.py::GraphCanvasBridgeTests",
                "tests/main_window_shell/bridge_contracts.py::ShellWorkspaceBridgeTests",
                "tests/main_window_shell/bridge_qml_boundaries.py::ShellLibraryBridgeQmlBoundaryTests",
                "tests/main_window_shell/bridge_qml_boundaries.py::ShellInspectorBridgeQmlBoundaryTests",
                "tests/main_window_shell/bridge_qml_boundaries.py::ShellWorkspaceBridgeQmlBoundaryTests",
                "tests/main_window_shell/shell_runtime_contracts.py::MainWindowShellTelemetryTests",
                "tests/main_window_shell/shell_runtime_contracts.py::MainWindowShellBootstrapCompositionTests",
                "tests/main_window_shell/shell_runtime_contracts.py::MainWindowShellContextBootstrapTests",
                "tests/main_window_shell/shell_runtime_contracts.py::MainWindowShellHostProtocolStateTests",
            ),
        ),
        ShellIsolationTarget.pytest_nodeid(
            "tests/main_window_shell/shell_runtime_contracts.py::_MainWindowShellGraphCanvasHostDirectTests",
            target_id="main_window__graph_canvas_host_subprocess",
            extra_env={"EA_NODE_EDITOR_GRAPH_CANVAS_HOST_DIRECT": "1"},
        ),
    )


def __getattr__(name: str):
    if name == "TARGETS":
        return _build_targets()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
