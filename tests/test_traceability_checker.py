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
            "docs/specs/requirements/80_PERFORMANCE.md",
            "docs/specs/requirements/90_QA_ACCEPTANCE.md",
            "docs/specs/requirements/TRACEABILITY_MATRIX.md",
            "docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md",
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

            (repo_root / "docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md").unlink()

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "Missing required artifact: docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md",
            issues,
        )

    def test_audit_repository_reports_stale_text_and_row_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            graph_canvas_doc = repo_root / "docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md"
            graph_canvas_doc.write_text(
                graph_canvas_doc.read_text(encoding="utf-8").replace(
                    "| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q` | PASS | Harness/report/traceability regression slice passed in the project venv |",
                    "| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q` | Pending | Harness/report/traceability regression slice was not rerun |",
                ),
                encoding="utf-8",
            )

            track_h_doc = repo_root / "docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md"
            track_h_doc.write_text(
                track_h_doc.read_text(encoding="utf-8").replace(
                    "Evidence Status: real `GraphCanvas.qml` offscreen regression snapshot refreshed after `P04`.",
                    "Evidence Status: Historical offscreen harness baseline restored from repo",
                ),
                encoding="utf-8",
            )

            matrix_path = repo_root / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
            matrix_path.write_text(
                matrix_path.read_text(encoding="utf-8").replace(
                    "Graph-canvas performance QA matrix and proof audit: `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`, `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`, `scripts/check_traceability.py`, `tests/test_traceability_checker.py`, `tests/test_track_h_perf_harness.py`",
                    "Graph-canvas performance QA matrix and proof audit: `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`, `scripts/check_traceability.py`, `tests/test_traceability_checker.py`, `tests/test_track_h_perf_harness.py`",
                ),
                encoding="utf-8",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md: found stale text: | Pending |",
            issues,
        )
        self.assertIn(
            "docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md: missing required text: Evidence Status: real `GraphCanvas.qml` offscreen regression snapshot refreshed after `P04`.",
            issues,
        )
        self.assertIn(
            "docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md: found stale text: Historical offscreen harness baseline restored from repo",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/TRACEABILITY_MATRIX.md: row REQ-QA-018 missing required text: GRAPH_CANVAS_PERF_QA_MATRIX.md",
            issues,
        )

    def test_audit_repository_reports_shell_phase_doc_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            readme_path = repo_root / "README.md"
            readme_path.write_text(
                readme_path.read_text(encoding="utf-8").replace(
                    "dedicated fresh-process shell-isolation phase",
                    "shell-wrapper suites for isolated `unittest` execution",
                ),
                encoding="utf-8",
            )

            qa_path = repo_root / "docs/specs/requirements/90_QA_ACCEPTANCE.md"
            qa_path.write_text(
                qa_path.read_text(encoding="utf-8")
                + "\n"
                + "`REQ-QA-015`: the four shell-wrapper modules `tests.test_main_window_shell`, `tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and `tests.test_shell_project_session_controller` shall remain on explicit fresh-process `unittest` execution inside the documented `full` workflow rather than the pytest phases.\n",
                encoding="utf-8",
            )

            matrix_doc = repo_root / "docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md"
            matrix_doc.write_text(
                matrix_doc.read_text(encoding="utf-8").replace(
                    "26 passed in 57.27s",
                    "57.27 seconds",
                ).replace(
                    "resolved value to `6` workers.",
                    "resolved value to `6` workers.\nadds `-n auto` only when `pytest-xdist` is importable in the project venv",
                ),
                encoding="utf-8",
            )

            traceability_matrix = repo_root / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
            traceability_matrix.write_text(
                traceability_matrix.read_text(encoding="utf-8").replace(
                    "| REQ-QA-015 | 90_QA_ACCEPTANCE | Dedicated shell-isolation phase in the documented `full` workflow: `scripts/run_verification.py`, `tests/test_shell_isolation_phase.py`, `tests/shell_isolation_runtime.py`, `tests/shell_isolation_main_window_targets.py`, `tests/shell_isolation_controller_targets.py`, `scripts/check_traceability.py`, `tests/test_traceability_checker.py`, `README.md`, `docs/GETTING_STARTED.md`, `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` |",
                    "| REQ-QA-015 | 90_QA_ACCEPTANCE | Shell-wrapper isolation in the documented `full` workflow: `scripts/run_verification.py`, `scripts/check_traceability.py`, `tests/test_traceability_checker.py`, `tests/test_main_window_shell.py`, `tests/test_script_editor_dock.py`, `tests/test_shell_run_controller.py`, `tests/test_shell_project_session_controller.py`, `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` |",
                ),
                encoding="utf-8",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            "README.md: missing required text: dedicated fresh-process shell-isolation phase",
            issues,
        )
        self.assertIn(
            "README.md: found stale text: shell-wrapper suites for isolated `unittest` execution",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/90_QA_ACCEPTANCE.md: found stale text: the four shell-wrapper modules `tests.test_main_window_shell`, `tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and `tests.test_shell_project_session_controller` shall remain on explicit fresh-process `unittest` execution",
            issues,
        )
        self.assertIn(
            "docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md: missing required text: 26 passed in 57.27s",
            issues,
        )
        self.assertIn(
            "docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md: found stale text: adds `-n auto` only when `pytest-xdist` is importable in the project venv",
            issues,
        )
        self.assertIn(
            "docs/specs/requirements/TRACEABILITY_MATRIX.md: row REQ-QA-015 missing required text: tests/test_shell_isolation_phase.py",
            issues,
        )


if __name__ == "__main__":
    unittest.main()
