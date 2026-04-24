from __future__ import annotations

import importlib
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication


bootstrap_module = importlib.import_module("ea_node_editor.bootstrap")
app_module = importlib.import_module("ea_node_editor.app")
shell_composition_module = importlib.import_module("ea_node_editor.ui.shell.composition")
shell_presenters_module = importlib.import_module("ea_node_editor.ui.shell.presenters")
registry_loader_module = importlib.import_module("ea_node_editor.ui.splash.registry_loader")
shell_window_module = importlib.import_module("ea_node_editor.ui.shell.window")


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


class MainBootstrapTests(unittest.TestCase):
    def test_root_source_launcher_is_retired(self) -> None:
        self.assertFalse((Path(__file__).resolve().parents[1] / "main.py").exists())

    def test_console_script_targets_package_bootstrap(self) -> None:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        pyproject_text = pyproject_path.read_text(encoding="utf-8")

        self.assertIn('corex-node-editor = "ea_node_editor.bootstrap:main"', pyproject_text)

    def test_shell_launcher_targets_package_bootstrap_module(self) -> None:
        run_script_path = Path(__file__).resolve().parents[1] / "scripts" / "run.sh"
        run_script_text = run_script_path.read_text(encoding="utf-8")

        self.assertIn("-m ea_node_editor.bootstrap", run_script_text)
        self.assertNotIn("find_worktree_python", run_script_text)
        self.assertNotIn(" main.py", run_script_text)

    def test_preferred_python_prefers_local_venv_over_shared_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            local_python = _touch(repo_root / "venv" / "Scripts" / "python.exe")
            shared_python = _touch(Path(temp_dir) / "shared" / "venv" / "Scripts" / "python.exe")

            with patch.object(bootstrap_module, "_find_worktree_python", return_value=shared_python):
                self.assertEqual(bootstrap_module._preferred_python(repo_root), local_python)

    def test_preferred_python_discovers_shared_worktree_venv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            shared_root = Path(temp_dir) / "shared-worktree"
            shared_python = _touch(shared_root / "venv" / "Scripts" / "python.exe")

            fake_git_output = "\n".join(
                (
                    f"worktree {repo_root}",
                    "HEAD abcdef1234567890",
                    "branch refs/heads/main",
                    f"worktree {shared_root}",
                    "HEAD 1234567890abcdef",
                    "branch refs/heads/codex/shared",
                )
            )

            fake_result = types.SimpleNamespace(stdout=fake_git_output)
            with patch.object(bootstrap_module.subprocess, "run", return_value=fake_result):
                self.assertEqual(bootstrap_module._preferred_python(repo_root), shared_python)

    def test_bootstrap_reexecs_once_and_honors_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            preferred_python = _touch(repo_root / "venv" / "Scripts" / "python.exe")
            current_python = _touch(Path(temp_dir) / "system" / "python.exe")
            exec_calls: list[tuple[str, list[str], dict[str, str]]] = []

            def _fake_execvpe(file: str, args: list[str], env: dict[str, str]) -> None:
                exec_calls.append((file, args, env))
                raise AssertionError("bootstrap should re-exec exactly once")

            with patch.object(bootstrap_module, "__file__", str(repo_root / "ea_node_editor" / "bootstrap.py")), patch.object(
                bootstrap_module.sys, "executable", str(current_python)
            ), patch.object(
                bootstrap_module.sys, "argv", ["-m", "--example-flag", "value"]
            ), patch.object(bootstrap_module.os, "execvpe", side_effect=_fake_execvpe), patch.object(
                bootstrap_module.os, "chdir"
            ) as chdir_mock, patch.dict(bootstrap_module.os.environ, {}, clear=False), patch.object(
                bootstrap_module, "_preferred_python", return_value=preferred_python
            ):
                with self.assertRaises(AssertionError):
                    bootstrap_module._bootstrap_python()

            self.assertEqual(len(exec_calls), 1)
            self.assertEqual(exec_calls[0][0], str(preferred_python))
            self.assertEqual(
                exec_calls[0][1],
                [str(preferred_python), "-m", "ea_node_editor.bootstrap", "--example-flag", "value"],
            )
            self.assertEqual(exec_calls[0][2][bootstrap_module._BOOTSTRAP_SENTINEL], "1")
            chdir_mock.assert_called_once_with(repo_root)

            with patch.object(bootstrap_module, "__file__", str(repo_root / "ea_node_editor" / "bootstrap.py")), patch.object(
                bootstrap_module.sys, "executable", str(current_python)
            ), patch.object(
                bootstrap_module.sys, "argv", ["-m", "--example-flag", "value"]
            ), patch.object(bootstrap_module.os, "execvpe") as execvpe_mock, patch.dict(
                bootstrap_module.os.environ, {bootstrap_module._BOOTSTRAP_SENTINEL: "1"}, clear=False
            ), patch.object(bootstrap_module, "_preferred_python", return_value=preferred_python):
                bootstrap_module._bootstrap_python()

            execvpe_mock.assert_not_called()

    def test_bootstrap_skips_reexec_for_frozen_package_runs(self) -> None:
        with patch.object(bootstrap_module.sys, "frozen", True, create=True), patch.object(
            bootstrap_module, "_preferred_python"
        ) as preferred_python_mock, patch.object(bootstrap_module.os, "execvpe") as execvpe_mock:
            bootstrap_module._bootstrap_python()

        preferred_python_mock.assert_not_called()
        execvpe_mock.assert_not_called()

    def test_bootstrap_owns_windows_qquick_controls_style_default(self) -> None:
        with patch.object(bootstrap_module.sys, "platform", "win32"), patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            bootstrap_module.configure_qquick_controls_runtime()
            self.assertEqual(os.environ["QT_QUICK_CONTROLS_STYLE"], "Basic")

        with patch.object(bootstrap_module.sys, "platform", "win32"), patch.dict(
            os.environ,
            {"QT_QUICK_CONTROLS_STYLE": "Material"},
            clear=True,
        ):
            bootstrap_module.configure_qquick_controls_runtime()
            self.assertEqual(os.environ["QT_QUICK_CONTROLS_STYLE"], "Material")


class AppBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        self.app.sendPostedEvents()
        self.app.processEvents()

    def test_build_and_show_shell_window_uses_composition_root(self) -> None:
        fake_window = Mock()
        preferences_document = {"graphics": {"theme": {"theme_id": "packet-theme"}}}

        with patch.object(
            app_module,
            "_load_startup_preferences_document",
            return_value=preferences_document,
        ) as load_preferences_mock, patch.object(
            app_module,
            "create_shell_window",
            return_value=fake_window,
        ) as create_shell_window_mock:
            self.assertIs(app_module.build_and_show_shell_window(), fake_window)

        load_preferences_mock.assert_called_once_with()
        create_shell_window_mock.assert_called_once_with(preferences_document=preferences_document)
        fake_window.show.assert_called_once_with()

    def test_create_shell_window_builds_composition_before_bootstrap(self) -> None:
        composition = object()
        preferences_document = {"graphics": {"theme": {"theme_id": "packet-theme"}}}
        with patch.object(
            shell_composition_module,
            "build_shell_window_composition",
            return_value=composition,
        ) as build_composition_mock, patch.object(
            shell_composition_module,
            "bootstrap_shell_window",
        ) as bootstrap_mock:
            window = shell_composition_module.create_shell_window(preferences_document=preferences_document)

        self.assertIsInstance(window, shell_window_module.ShellWindow)
        build_composition_mock.assert_called_once_with(
            window,
            registry=None,
            preferences_document=preferences_document,
        )
        bootstrap_mock.assert_called_once_with(window, composition)
        window.close()
        window.deleteLater()
        self.app.sendPostedEvents()
        self.app.processEvents()

    def test_registry_loader_builds_default_registry_with_preloaded_preferences_document(self) -> None:
        preferences_document = {"addons": {"states": {"tests.addon": {"enabled": False, "pending_restart": False}}}}
        sentinel_registry = object()
        captured: list[object] = []

        loader = registry_loader_module.RegistryLoader(preferences_document=preferences_document)
        loader.ready.connect(captured.append)

        with patch.object(
            registry_loader_module,
            "build_default_registry",
            return_value=sentinel_registry,
        ) as build_registry_mock:
            loader._worker.run()

        build_registry_mock.assert_called_once_with(preferences_document=preferences_document)
        self.assertEqual(captured, [sentinel_registry])

    def test_build_shell_window_composition_returns_typed_contract(self) -> None:
        window = shell_window_module.ShellWindow(_defer_bootstrap=True)

        composition = shell_composition_module.build_shell_window_composition(window)

        self.assertIsInstance(composition, shell_composition_module.ShellWindowComposition)
        self.assertIsInstance(composition.state, shell_composition_module.ShellStateDependencies)
        self.assertIsInstance(composition.primitives, shell_composition_module.ShellPrimitiveDependencies)
        self.assertIsInstance(composition.controllers, shell_composition_module.ShellControllerDependencies)
        self.assertIsInstance(composition.presenters, shell_composition_module.ShellPresenterDependencies)
        self.assertIsInstance(composition.runtime, shell_composition_module.ShellRuntimeDependencies)
        self.assertIsInstance(composition.context_bridges, shell_composition_module.ShellContextBridgeDependencies)
        self.assertIsInstance(
            composition.presenters.graph_canvas_host_presenter,
            shell_presenters_module.GraphCanvasHostPresenter,
        )
        self.assertIsNot(composition.controllers.workspace_library_controller._host, window)
        self.assertIs(composition.controllers.workspace_library_controller._host.window, window)
        self.assertIsNot(composition.controllers.project_session_controller._host, window)
        self.assertIs(composition.controllers.project_session_controller._host.window, window)
        self.assertIsNot(composition.controllers.run_controller._host, window)
        self.assertIs(composition.controllers.run_controller._host.window, window)
        self.assertIsNot(composition.presenters.shell_library_presenter._host, window)
        self.assertIs(composition.presenters.shell_library_presenter._host.window, window)
        self.assertIsNot(composition.presenters.shell_workspace_presenter._host, window)
        self.assertIs(composition.presenters.shell_workspace_presenter._host.window, window)
        self.assertIsNot(composition.presenters.shell_inspector_presenter._host, window)
        self.assertIs(composition.presenters.shell_inspector_presenter._host.window, window)
        self.assertIsNot(composition.presenters.graph_canvas_presenter._host, window)
        self.assertIs(composition.presenters.graph_canvas_presenter._host.window, window)
        self.assertIsNot(composition.presenters.graph_canvas_host_presenter._host, window)
        self.assertIs(composition.presenters.graph_canvas_host_presenter._host.window, window)
        context_bindings = dict(composition.context_bridges.qml_context_property_bindings)
        self.assertIs(context_bindings["viewerSessionBridge"], composition.runtime.viewer_session_bridge)
        self.assertIs(context_bindings["viewerHostService"], composition.runtime.viewer_host_service)
        self.assertNotIn("_shell_context_bridges", window.__dict__)
        self.assertNotIn("viewer_session_bridge", window.__dict__)
        self.assertNotIn("viewer_host_service", window.__dict__)
        window.close()
        window.deleteLater()
        self.app.sendPostedEvents()
        self.app.processEvents()

    def test_bootstrap_shell_window_uses_single_explicit_attach_point(self) -> None:
        host = Mock()
        composition = Mock(spec=shell_composition_module.ShellWindowComposition)
        timer_dependencies = Mock()

        with patch.object(shell_composition_module, "_configure_shell_window_host") as configure_mock, patch.object(
            shell_composition_module,
            "_run_shell_startup_sequence",
        ) as startup_mock, patch.object(
            shell_composition_module.ShellWindowBootstrapCoordinator,
            "create_timer_dependencies",
            return_value=timer_dependencies,
        ) as create_timer_mock, patch.object(
            shell_composition_module,
            "_finalize_shell_window_bootstrap",
        ) as finalize_mock:
            shell_composition_module.bootstrap_shell_window(host, composition)

        configure_mock.assert_called_once_with(host)
        composition.attach.assert_called_once_with(host)
        startup_mock.assert_called_once_with(host)
        create_timer_mock.assert_called_once()
        timer_dependencies.attach.assert_called_once_with(host)
        finalize_mock.assert_called_once_with(host)

    def test_shell_window_accepts_injected_composition_bundle(self) -> None:
        composition = object()
        with patch.object(shell_window_module, "build_shell_window_composition") as build_composition_mock, patch.object(
            shell_window_module,
            "bootstrap_shell_window",
        ) as bootstrap_mock:
            window = shell_window_module.ShellWindow(composition=composition)

        build_composition_mock.assert_not_called()
        bootstrap_mock.assert_called_once_with(window, composition)
        window.close()
        window.deleteLater()
        self.app.sendPostedEvents()
        self.app.processEvents()

    def test_shell_window_module_stays_within_packet_budget_and_uses_helper_surface(self) -> None:
        shell_dir = Path(__file__).resolve().parents[1] / "ea_node_editor" / "ui" / "shell"
        window_path = shell_dir / "window.py"
        helper_path = shell_dir / "window_state_helpers.py"

        window_text = window_path.read_text(encoding="utf-8")
        helper_text = helper_path.read_text(encoding="utf-8")

        self.assertLessEqual(len(window_text.splitlines()), 900)
        self.assertIn("window_state_helpers", window_text)
        self.assertIn("SHELL_WINDOW_FACADE_BINDINGS", helper_text)

    def test_run_applies_startup_theme_and_bootstraps_shell_window(self) -> None:
        fake_app = Mock()
        fake_app.exec.return_value = 17
        fake_splash = Mock()
        fake_loader = Mock()
        preferences_document = {"graphics": {"theme": {"theme_id": "packet-theme"}}}

        with patch.object(app_module.mp, "freeze_support") as freeze_support_mock, patch.object(
            app_module,
            "QApplication",
            return_value=fake_app,
        ) as app_ctor, patch.object(
            app_module,
            "_startup_theme_id",
            return_value="packet-theme",
        ) as startup_theme_mock, patch.object(
            app_module,
            "_load_startup_preferences_document",
            return_value=preferences_document,
        ), patch.object(
            app_module,
            "build_theme_stylesheet",
            side_effect=lambda theme_id: f"stylesheet:{theme_id}",
        ), patch.object(
            app_module,
            "apply_application_icon",
        ), patch.object(
            app_module,
            "OpeningSplash",
            return_value=fake_splash,
        ) as splash_ctor, patch.object(
            app_module,
            "RegistryLoader",
            return_value=fake_loader,
        ) as loader_ctor, patch.object(
            app_module,
            "create_shell_window",
        ) as create_shell_window_mock:
            self.assertEqual(app_module.run(), 17)

        freeze_support_mock.assert_called_once_with()
        app_ctor.assert_called_once()
        fake_app.setApplicationName.assert_called_once_with("COREX Node Editor")
        fake_app.setStyleSheet.assert_called_once_with("stylesheet:packet-theme")
        startup_theme_mock.assert_called_once_with(preferences_document=preferences_document)
        splash_ctor.assert_called_once_with()
        fake_splash.show_centered.assert_called_once_with()
        loader_ctor.assert_called_once_with(preferences_document=preferences_document)
        fake_splash.boot_completed.connect.assert_called_once()
        fake_loader.ready.connect.assert_called_once()
        fake_loader.failed.connect.assert_called_once()
        fake_loader.start.assert_called_once_with()
        create_shell_window_mock.assert_not_called()
        fake_app.exec.assert_called_once_with()

    def test_run_registry_failure_falls_back_to_shell_build_with_preloaded_preferences_document(self) -> None:
        class _Signal:
            def __init__(self) -> None:
                self._callbacks: list[object] = []

            def connect(self, callback) -> None:  # noqa: ANN001
                self._callbacks.append(callback)

            def emit(self, *args, **kwargs) -> None:  # noqa: ANN003, ANN002
                for callback in list(self._callbacks):
                    callback(*args, **kwargs)

        class _SplashStub:
            def __init__(self) -> None:
                self.boot_completed = _Signal()
                self.finish = Mock()

            def show_centered(self) -> None:
                return None

        class _LoaderStub:
            def __init__(self) -> None:
                self.ready = _Signal()
                self.failed = _Signal()

            def start(self) -> None:
                return None

        fake_app = Mock()
        fake_splash = _SplashStub()
        fake_loader = _LoaderStub()
        preferences_document = {"graphics": {"theme": {"theme_id": "packet-theme"}}}

        def _exec() -> int:
            fake_splash.boot_completed.emit()
            fake_loader.failed.emit("traceback")
            return 17

        fake_app.exec.side_effect = _exec

        with patch.object(app_module.mp, "freeze_support"), patch.object(
            app_module,
            "QApplication",
            return_value=fake_app,
        ), patch.object(
            app_module,
            "_startup_theme_id",
            return_value="packet-theme",
        ), patch.object(
            app_module,
            "_load_startup_preferences_document",
            return_value=preferences_document,
        ), patch.object(
            app_module,
            "build_theme_stylesheet",
            side_effect=lambda theme_id: f"stylesheet:{theme_id}",
        ), patch.object(
            app_module,
            "apply_application_icon",
        ), patch.object(
            app_module,
            "OpeningSplash",
            return_value=fake_splash,
        ), patch.object(
            app_module,
            "RegistryLoader",
            return_value=fake_loader,
        ), patch.object(
            app_module,
            "create_shell_window",
            return_value=Mock(),
        ) as create_shell_window_mock:
            self.assertEqual(app_module.run(), 17)

        create_shell_window_mock.assert_called_once_with(
            registry=None,
            preferences_document=preferences_document,
        )

    def test_shell_window_configuration_applies_title_size_and_icon(self) -> None:
        host = Mock()
        with patch.object(shell_composition_module, "apply_window_icon") as apply_window_icon_mock:
            shell_composition_module._configure_shell_window_host(host)

        host.setWindowTitle.assert_called_once_with("COREX Node Editor")
        host.resize.assert_called_once_with(1600, 900)
        apply_window_icon_mock.assert_called_once_with(host)


if __name__ == "__main__":
    unittest.main()
