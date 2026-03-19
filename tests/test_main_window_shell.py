from __future__ import annotations

import importlib
import unittest

from tests.main_window_shell.base import MainWindowShellTestBase, SharedMainWindowShellTestBase

_SHELL_TEST_MODULES = (
    "tests.main_window_shell.shell_basics_and_search",
    "tests.main_window_shell.drop_connect_and_workflow_io",
    "tests.main_window_shell.edit_clipboard_history",
    "tests.main_window_shell.passive_style_context_menus",
    "tests.main_window_shell.passive_property_editors",
    "tests.main_window_shell.passive_image_nodes",
    "tests.main_window_shell.passive_pdf_nodes",
    "tests.main_window_shell.view_library_inspector",
    "tests.main_window_shell.bridge_contracts",
    "tests.main_window_shell.bridge_qml_boundaries",
    "tests.main_window_shell.shell_runtime_contracts",
)


def _load_shell_test_modules() -> None:
    for module_name in _SHELL_TEST_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name != module_name:
                raise
            continue
        exported_names = getattr(module, "__all__", None)
        if exported_names is None:
            exported_names = [name for name in module.__dict__ if not name.startswith("_")]
        globals().update({name: getattr(module, name) for name in exported_names})


def _pop_isolated_imported_shell_cases() -> dict[str, type[MainWindowShellTestBase]]:
    isolated_cases: dict[str, type[MainWindowShellTestBase]] = {}
    for isolated_name in (
        "MainWindowShellPassiveImageNodesTests",
        "MainWindowShellPassivePdfNodesTests",
        "MainWindowShellPassiveImageNodesSubprocessTests",
        "MainWindowShellPassivePdfNodesSubprocessTests",
    ):
        candidate = globals().pop(isolated_name, None)
        if (
            isinstance(candidate, type)
            and candidate.__module__ == "tests.main_window_shell.shell_runtime_contracts"
        ):
            globals()[isolated_name] = candidate
            continue
        if isinstance(candidate, type) and issubclass(candidate, MainWindowShellTestBase):
            isolated_cases[isolated_name] = candidate
    return isolated_cases


_load_shell_test_modules()
_ISOLATED_IMPORTED_SHELL_CASES = _pop_isolated_imported_shell_cases()


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(FrameRateSamplerTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellLibraryBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellInspectorBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellWorkspaceBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellLibraryBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellInspectorBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellWorkspaceBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(GraphCanvasQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(MainWindowShellPassiveImageNodesTests))
    suite.addTests(loader.loadTestsFromTestCase(MainWindowShellPassivePdfNodesTests))
    suite.addTests(loader.loadTestsFromTestCase(MainWindowShellGraphCanvasHostTests))

    shell_classes: list[type[SharedMainWindowShellTestBase]] = []
    for candidate in globals().values():
        if not isinstance(candidate, type):
            continue
        if not issubclass(candidate, SharedMainWindowShellTestBase):
            continue
        if candidate is SharedMainWindowShellTestBase:
            continue
        shell_classes.append(candidate)

    for case_type in sorted(shell_classes, key=lambda item: (item.__module__, item.__name__)):
        suite.addTests(loader.loadTestsFromTestCase(case_type))
    return suite


if __name__ == "__main__":
    unittest.main()
