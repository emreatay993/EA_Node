from __future__ import annotations

import importlib
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


main = importlib.import_module("main")
bootstrap_module = importlib.import_module("ea_node_editor.bootstrap")
app_module = importlib.import_module("ea_node_editor.app")


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


class MainBootstrapTests(unittest.TestCase):
    def test_source_launcher_delegates_to_package_bootstrap(self) -> None:
        self.assertIs(main.main, bootstrap_module.main)

    def test_console_script_targets_package_bootstrap(self) -> None:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        pyproject_text = pyproject_path.read_text(encoding="utf-8")

        self.assertIn('ea-node-editor = "ea_node_editor.bootstrap:main"', pyproject_text)

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
            script_path = repo_root / "main.py"
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text("print('placeholder')\n", encoding="utf-8")

            exec_calls: list[tuple[str, list[str], dict[str, str]]] = []

            def _fake_execvpe(file: str, args: list[str], env: dict[str, str]) -> None:
                exec_calls.append((file, args, env))
                raise AssertionError("bootstrap should re-exec exactly once")

            with patch.object(bootstrap_module, "__file__", str(repo_root / "ea_node_editor" / "bootstrap.py")), patch.object(
                bootstrap_module.sys, "executable", str(current_python)
            ), patch.object(
                bootstrap_module.sys, "argv", [str(script_path), "--example-flag", "value"]
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
                [str(preferred_python), "main.py", "--example-flag", "value"],
            )
            self.assertEqual(exec_calls[0][2][bootstrap_module._BOOTSTRAP_SENTINEL], "1")
            chdir_mock.assert_called_once_with(repo_root)

            with patch.object(bootstrap_module, "__file__", str(repo_root / "ea_node_editor" / "bootstrap.py")), patch.object(
                bootstrap_module.sys, "executable", str(current_python)
            ), patch.object(
                bootstrap_module.sys, "argv", [str(script_path), "--example-flag", "value"]
            ), patch.object(bootstrap_module.os, "execvpe") as execvpe_mock, patch.dict(
                bootstrap_module.os.environ, {bootstrap_module._BOOTSTRAP_SENTINEL: "1"}, clear=False
            ), patch.object(bootstrap_module, "_preferred_python", return_value=preferred_python):
                bootstrap_module._bootstrap_python()

            execvpe_mock.assert_not_called()


class AppBootstrapTests(unittest.TestCase):
    def test_run_applies_startup_theme_and_bootstraps_shell_window(self) -> None:
        fake_app = Mock()
        fake_app.exec.return_value = 17

        with patch.object(app_module.mp, "freeze_support") as freeze_support_mock, patch.object(
            app_module,
            "QApplication",
            return_value=fake_app,
        ) as app_ctor, patch.object(
            app_module,
            "_startup_theme_id",
            return_value="packet-theme",
        ), patch.object(
            app_module,
            "build_theme_stylesheet",
            side_effect=lambda theme_id: f"stylesheet:{theme_id}",
        ), patch.object(
            app_module,
            "build_and_show_shell_window",
        ) as build_window_mock:
            self.assertEqual(app_module.run(), 17)

        freeze_support_mock.assert_called_once_with()
        app_ctor.assert_called_once()
        fake_app.setApplicationName.assert_called_once_with("EA Node Editor")
        fake_app.setStyleSheet.assert_called_once_with("stylesheet:packet-theme")
        build_window_mock.assert_called_once_with()
        fake_app.exec.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
