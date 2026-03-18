from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_SCRIPT = _REPO_ROOT / "scripts" / "run.sh"


def _bash_path(path: Path) -> str:
    text = str(path)
    drive, tail = os.path.splitdrive(text)
    if drive:
        normalized_tail = tail.replace("\\", "/")
        return f"/mnt/{drive[0].lower()}{normalized_tail}"
    return text.replace("\\", "/")


def _write_unix_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


class RunScriptTests(unittest.TestCase):
    def test_run_script_launches_repo_main_with_local_venv_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_root = temp_path / "repo"
            scripts_dir = repo_root / "scripts"
            venv_dir = repo_root / "venv" / "Scripts"
            scripts_dir.mkdir(parents=True)
            venv_dir.mkdir(parents=True)

            record_path = repo_root / "record.txt"
            fake_python = venv_dir / "python.exe"
            bash_record_path = _bash_path(record_path)
            _write_unix_text(
                fake_python,
                "\n".join(
                    (
                        "#!/usr/bin/env bash",
                        "set -euo pipefail",
                        f"printf '%s\\n' \"$PWD\" > '{bash_record_path}'",
                        f"printf '%s\\n' \"$@\" >> '{bash_record_path}'",
                    )
                )
                + "\n",
            )
            fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)
            _write_unix_text(repo_root / "main.py", "print('placeholder launcher target')\n")

            copied_run_script = scripts_dir / "run.sh"
            _write_unix_text(copied_run_script, _RUN_SCRIPT.read_text(encoding="utf-8"))
            copied_run_script.chmod(copied_run_script.stat().st_mode | stat.S_IXUSR)

            result = subprocess.run(
                ["bash", _bash_path(copied_run_script), "--example-flag", "value"],
                cwd=temp_path,
                env=os.environ.copy(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            record_lines = record_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(record_lines[0], _bash_path(repo_root))
            self.assertEqual(record_lines[1:], ["main.py", "--example-flag", "value"])


if __name__ == "__main__":
    unittest.main()
