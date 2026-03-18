from __future__ import annotations

import importlib
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


main = importlib.import_module("main")


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


class MainBootstrapTests(unittest.TestCase):
    def test_preferred_python_prefers_local_venv_over_shared_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            local_python = _touch(repo_root / "venv" / "Scripts" / "python.exe")
            shared_python = _touch(Path(temp_dir) / "shared" / "venv" / "Scripts" / "python.exe")

            with patch.object(main, "_find_worktree_python", return_value=shared_python):
                self.assertEqual(main._preferred_python(repo_root), local_python)

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
            with patch.object(main.subprocess, "run", return_value=fake_result):
                self.assertEqual(main._preferred_python(repo_root), shared_python)

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

            with patch.object(main, "__file__", str(script_path)), patch.object(
                main.sys, "executable", str(current_python)
            ), patch.object(
                main.sys, "argv", [str(script_path), "--example-flag", "value"]
            ), patch.object(main.os, "execvpe", side_effect=_fake_execvpe), patch.object(
                main.os, "chdir"
            ) as chdir_mock, patch.dict(main.os.environ, {}, clear=False), patch.object(
                main, "_preferred_python", return_value=preferred_python
            ):
                with self.assertRaises(AssertionError):
                    main._bootstrap_python()

            self.assertEqual(len(exec_calls), 1)
            self.assertEqual(exec_calls[0][0], str(preferred_python))
            self.assertEqual(
                exec_calls[0][1],
                [str(preferred_python), "main.py", "--example-flag", "value"],
            )
            self.assertEqual(exec_calls[0][2][main._BOOTSTRAP_SENTINEL], "1")
            chdir_mock.assert_called_once_with(repo_root)

            with patch.object(main, "__file__", str(script_path)), patch.object(
                main.sys, "executable", str(current_python)
            ), patch.object(
                main.sys, "argv", [str(script_path), "--example-flag", "value"]
            ), patch.object(main.os, "execvpe") as execvpe_mock, patch.dict(
                main.os.environ, {main._BOOTSTRAP_SENTINEL: "1"}, clear=False
            ), patch.object(main, "_preferred_python", return_value=preferred_python):
                main._bootstrap_python()

            execvpe_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
