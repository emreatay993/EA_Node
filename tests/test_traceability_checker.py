import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_traceability.py"


def load_checker_module():
    spec = importlib.util.spec_from_file_location("check_traceability", CHECKER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TraceabilityCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checker = load_checker_module()

    def make_repo_fixture(self, root: Path) -> None:
        paths_to_copy = (
            "README.md",
            "docs/GETTING_STARTED.md",
            "docs/specs/requirements/TRACEABILITY_MATRIX.md",
            "docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md",
            "docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md",
            "docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md",
            "docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md",
            "docs/specs/perf/RC_PACKAGING_REPORT.md",
            "docs/specs/perf/PILOT_SIGNOFF.md",
            "scripts/check_traceability.py",
            "tests/test_traceability_checker.py",
        )
        for relative_path in paths_to_copy:
            source = REPO_ROOT / relative_path
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def test_audit_repository_passes_for_current_repo(self) -> None:
        self.assertEqual([], self.checker.audit_repository(REPO_ROOT))

    def test_audit_repository_reports_missing_required_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            (repo_root / "docs/specs/perf/PILOT_SIGNOFF.md").unlink()

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "Missing required artifact: docs/specs/perf/PILOT_SIGNOFF.md",
            issues,
        )

    def test_audit_repository_reports_stale_text_and_row_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            graph_surface_doc = repo_root / "docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md"
            graph_surface_doc.write_text(
                graph_surface_doc.read_text(encoding="utf-8").replace(
                    "Both module-level shell wrappers passed directly on `2026-03-18`, so no\n  per-test fresh-process fallback is currently required.\n",
                    "In environments where either module-level wrapper exits with code `5`, the approved fallback is to rerun every shell case in its own fresh process.\n",
                ),
                encoding="utf-8",
            )

            matrix_path = repo_root / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
            matrix_path.write_text(
                matrix_path.read_text(encoding="utf-8").replace(
                    "Current verification baseline-status note and proof audit",
                    "Recorded serializer baseline caveat",
                ),
                encoding="utf-8",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md: missing required text: Both module-level shell wrappers passed directly",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/TRACEABILITY_MATRIX.md: row AC-REQ-QA-017-01 missing required text: Current verification baseline-status note and proof audit",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/TRACEABILITY_MATRIX.md: row AC-REQ-QA-017-01 found stale text: Recorded serializer baseline caveat",
            issues,
        )


if __name__ == "__main__":
    unittest.main()
