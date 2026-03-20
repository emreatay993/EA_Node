from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PersistencePackageImportTests(unittest.TestCase):
    def _run_python(self, script: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def test_graph_model_import_does_not_hit_persistence_cycle(self) -> None:
        result = self._run_python(
            "from ea_node_editor.graph.model import GraphModel; print(GraphModel.__name__)"
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr or result.stdout,
        )
        self.assertEqual(result.stdout.strip(), "GraphModel")

    def test_persistence_package_exports_resolve_lazily(self) -> None:
        result = self._run_python(
            "from ea_node_editor.persistence import "
            "JsonProjectCodec, JsonProjectMigration, JsonProjectSerializer, SessionAutosaveStore; "
            "print(','.join(["
            "JsonProjectCodec.__name__, "
            "JsonProjectMigration.__name__, "
            "JsonProjectSerializer.__name__, "
            "SessionAutosaveStore.__name__]))"
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr or result.stdout,
        )
        self.assertEqual(
            result.stdout.strip(),
            "JsonProjectCodec,JsonProjectMigration,JsonProjectSerializer,SessionAutosaveStore",
        )
