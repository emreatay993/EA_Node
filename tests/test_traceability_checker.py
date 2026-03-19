from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_traceability.py"
VERIFICATION_MANIFEST_PATH = REPO_ROOT / "scripts" / "verification_manifest.py"


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def replace_text(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text(encoding="utf-8-sig").replace(old, new), encoding="utf-8")


def update_markdown_table_result(path: Path, command: str, new_result: str, new_notes: str | None = None) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    command_cell = f"`{command}`"
    for index, line in enumerate(lines):
        if not line.startswith(f"| {command_cell} |"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        cells[1] = new_result
        if new_notes is not None and len(cells) > 2:
            cells[2] = new_notes
        lines[index] = "| " + " | ".join(cells) + " |"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise AssertionError(f"Command row not found: {command}")


def remove_token_from_traceability_row(path: Path, row_id: str, token: str) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"| {row_id} |"):
            continue
        lines[index] = line.replace(token, "").replace(", ,", ",")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise AssertionError(f"Traceability row not found: {row_id}")


class TraceabilityCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_module("verification_manifest_for_traceability_tests", VERIFICATION_MANIFEST_PATH)
        cls.checker = load_module("check_traceability_for_tests", CHECKER_PATH)

    def test_checker_uses_manifest_owned_audit_catalogs(self) -> None:
        self.assertEqual(self.manifest.PROOF_AUDIT_REQUIRED_ARTIFACTS, self.checker.REQUIRED_ARTIFACTS)
        manifest_rules = {
            path: (rule.required, rule.forbidden)
            for path, rule in self.manifest.GENERIC_DOCUMENT_RULES.items()
        }
        checker_rules = {
            path: (rule.required, rule.forbidden)
            for path, rule in self.checker.GENERIC_DOCUMENT_RULES.items()
        }
        self.assertEqual(manifest_rules, checker_rules)

    def make_repo_fixture(self, root: Path) -> None:
        for relative_path in self.checker.REQUIRED_ARTIFACTS:
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

            (repo_root / self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC).unlink()

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            f"Missing required artifact: {self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC}",
            issues,
        )

    def test_audit_repository_reports_structured_perf_and_row_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            graph_canvas_doc = repo_root / self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC
            update_markdown_table_result(
                graph_canvas_doc,
                self.manifest.TRACK_H_REGRESSION_COMMAND,
                "Pending",
                "Harness/report/traceability regression slice was not rerun",
            )

            track_h_doc = repo_root / self.manifest.TRACK_H_BENCHMARK_REPORT_DOC
            replace_text(
                track_h_doc,
                "offscreen regression snapshot",
                "Historical offscreen harness baseline restored from repo",
            )

            traceability_matrix = repo_root / self.manifest.TRACEABILITY_MATRIX_DOC
            remove_token_from_traceability_row(
                traceability_matrix,
                "REQ-QA-018",
                "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertIn(
            f"{self.manifest.GRAPH_CANVAS_PERF_MATRIX_DOC}: 2026-03-18 Execution Results command "
            f"{self.manifest.TRACK_H_REGRESSION_COMMAND} has unexpected result: Pending",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACK_H_BENCHMARK_REPORT_DOC}: track-h benchmark report missing fact: offscreen regression snapshot",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACK_H_BENCHMARK_REPORT_DOC}: found stale text: Historical offscreen harness baseline restored from repo",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACEABILITY_MATRIX_DOC}: row REQ-QA-018 missing required text: GRAPH_CANVAS_PERF_QA_MATRIX.md",
            issues,
        )

    def test_audit_repository_reports_shell_phase_doc_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.make_repo_fixture(repo_root)

            readme_path = repo_root / "README.md"
            replace_text(
                readme_path,
                "dedicated fresh-process shell-isolation phase",
                "shell-wrapper suites for isolated `unittest` execution",
            )

            qa_path = repo_root / self.manifest.QA_ACCEPTANCE_DOC
            replace_text(
                qa_path,
                self.manifest.SHELL_ISOLATION_SPEC.test_path,
                "tests/test_shell_wrapper_phase.py",
            )
            qa_path.write_text(
                qa_path.read_text(encoding="utf-8-sig")
                + "\n"
                + "`REQ-QA-015`: the four shell-wrapper modules `tests.test_main_window_shell`, "
                + "`tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and "
                + "`tests.test_shell_project_session_controller` shall remain on explicit "
                + "fresh-process `unittest` execution inside the documented `full` workflow rather "
                + "than the pytest phases.\n",
                encoding="utf-8",
            )

            verification_matrix = repo_root / self.manifest.VERIFICATION_SPEED_MATRIX_DOC
            replace_text(
                verification_matrix,
                "`26 passed in 57.27s`",
                "57.27 seconds",
            )
            replace_text(
                verification_matrix,
                "resolved value to `6` workers.",
                "resolved value to `6` workers.\nadds `-n auto` only when `pytest-xdist` is importable in the project venv",
            )

            traceability_matrix = repo_root / self.manifest.TRACEABILITY_MATRIX_DOC
            remove_token_from_traceability_row(
                traceability_matrix,
                "REQ-QA-015",
                self.manifest.SHELL_ISOLATION_SPEC.test_path,
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
            f"{self.manifest.QA_ACCEPTANCE_DOC}: found stale text: the four shell-wrapper modules "
            "`tests.test_main_window_shell`, `tests.test_script_editor_dock`, "
            "`tests.test_shell_run_controller`, and `tests.test_shell_project_session_controller` "
            "shall remain on explicit fresh-process `unittest` execution",
            issues,
        )
        self.assertIn(
            f"{self.manifest.QA_ACCEPTANCE_DOC}: requirement REQ-QA-015 missing fact: {self.manifest.SHELL_ISOLATION_SPEC.test_path}",
            issues,
        )
        self.assertIn(
            f"{self.manifest.VERIFICATION_SPEED_MATRIX_DOC}: dedicated shell-isolation benchmark result is not a pytest timing summary: 57.27 seconds",
            issues,
        )
        self.assertIn(
            f"{self.manifest.VERIFICATION_SPEED_MATRIX_DOC}: found stale text: adds `-n auto` only when `pytest-xdist` is importable in the project venv",
            issues,
        )
        self.assertIn(
            f"{self.manifest.TRACEABILITY_MATRIX_DOC}: row REQ-QA-015 missing required text: {self.manifest.SHELL_ISOLATION_SPEC.test_path}",
            issues,
        )


if __name__ == "__main__":
    unittest.main()
