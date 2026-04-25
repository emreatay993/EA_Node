from __future__ import annotations

import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_SCRIPT = _REPO_ROOT / "scripts" / "run.sh"


class RunScriptTests(unittest.TestCase):
    def test_run_script_launches_package_bootstrap(self) -> None:
        text = _RUN_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('PYTHON_BIN="${EA_NODE_EDITOR_PYTHON:-python}"', text)
        self.assertIn('exec "${PYTHON_BIN}" -m ea_node_editor.bootstrap "$@"', text)
        self.assertNotIn("main.py", text)


if __name__ == "__main__":
    unittest.main()
