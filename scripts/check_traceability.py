#!/usr/bin/env python3
"""Validate the packet-owned verification traceability layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ARTIFACTS = (
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


@dataclass(frozen=True)
class DocumentRule:
    required: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


DOCUMENT_RULES: dict[str, DocumentRule] = {
    "README.md": DocumentRule(
        required=(
            "scripts/check_traceability.py",
            "Graph Surface Input QA Matrix",
            "Verification Speed QA Matrix",
            "dedicated fresh-process shell-isolation phase",
            "tests/test_shell_isolation_phase.py",
            "proof-audit command",
        ),
        forbidden=(
            "serializer caveat.",
            "shell-wrapper suites for isolated `unittest` execution",
        ),
    ),
    "docs/GETTING_STARTED.md": DocumentRule(
        required=(
            "scripts/check_traceability.py",
            "tests/test_shell_isolation_phase.py",
            "psutil.cpu_count(logical=True)",
            "dedicated fresh-process",
            "serializer spot-check",
            "no longer carries that",
            "benchmark evidence",
        ),
        forbidden=(
            "remains a separate persistence follow-up",
            "isolated module-level",
        ),
    ),
    "docs/specs/requirements/90_QA_ACCEPTANCE.md": DocumentRule(
        required=(
            "REQ-QA-015",
            "tests/test_shell_isolation_phase.py",
            "psutil.cpu_count(logical=True)",
            "AC-REQ-QA-015-01",
            "AC-REQ-QA-016-01",
            "REQ-QA-018",
            "AC-REQ-QA-018-01",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "graph_canvas_perf_docs",
        ),
        forbidden=(
            "the four shell-wrapper modules `tests.test_main_window_shell`, `tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and `tests.test_shell_project_session_controller` shall remain on explicit fresh-process `unittest` execution",
            "on separate `unittest` commands after the pytest phases",
        ),
    ),
    "docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md": DocumentRule(
        required=(
            "dedicated shell-isolation phase",
            "tests/test_shell_isolation_phase.py",
            "psutil.cpu_count(logical=True)",
            "77.776s",
            "26 passed in 57.27s",
            "## Companion Proof Audit",
            "scripts/check_traceability.py",
            "## Current Baseline Status",
            "earlier passive image-panel serializer caveat",
            "is retired.",
            "No known out-of-scope verification baseline failures remain",
        ),
        forbidden=(
            "isolated shell-wrapper `unittest` phase",
            "adds `-n auto` only when `pytest-xdist` is importable in the project venv",
            "still fails because passive image-panel round-trips add default crop fields",
            "serializer baseline remains open",
        ),
    ),
    "docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md": DocumentRule(
        required=(
            "## Shell Verification Policy",
            "Both module-level shell wrappers passed directly",
        ),
        forbidden=(
            "wrapper instability (`code 5`)",
            "approved fresh-process fallback completed",
        ),
    ),
    "docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md": DocumentRule(
        required=(
            "## Locked Benchmark Contract",
            "GraphCanvas.qml",
            "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q",
            "artifacts/graph_canvas_perf_docs",
            "## Desktop/Manual Follow-Up",
            "The desktop/manual follow-up is still outstanding",
        ),
        forbidden=(
            "| Pending |",
        ),
    ),
    "docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md": DocumentRule(
        required=(
            "Evidence Status: real `GraphCanvas.qml` offscreen regression snapshot refreshed after `P04`.",
            "artifacts/graph_canvas_perf_docs/TRACK_H_BENCHMARK_REPORT.md",
            "## 2026-03-18 Offscreen Snapshot",
            "Interactive desktop/GPU validation remains required",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        ),
        forbidden=(
            "Historical offscreen harness baseline restored from repo",
            "P08 did not rerun the performance harness.",
        ),
    ),
    "docs/specs/requirements/80_PERFORMANCE.md": DocumentRule(
        required=(
            "GraphCanvas.qml",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "steady-state idle appearance returns automatically",
        ),
    ),
    "docs/specs/perf/RC_PACKAGING_REPORT.md": DocumentRule(
        required=(
            "Evidence Status: Archived RC packaging smoke snapshot restored from repo",
            "Current Constraint: P08 did not rerun packaging.",
            "## Archived 2026-03-01 Snapshot",
        ),
    ),
    "docs/specs/perf/PILOT_SIGNOFF.md": DocumentRule(
        required=(
            "Evidence Status: Archived packaged desktop pilot sign-off restored from repo",
            "Current Constraint: P08 did not rerun the packaged pilot.",
            "## Archived 2026-03-01 Snapshot",
        ),
    ),
}

TRACEABILITY_ROW_RULES: dict[str, DocumentRule] = {
    "REQ-PERF-001": DocumentRule(
        required=(
            "TRACK_H_BENCHMARK_REPORT.md",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "GraphCanvas.qml",
        ),
    ),
    "REQ-PERF-002": DocumentRule(
        required=(
            "TRACK_H_BENCHMARK_REPORT.md",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "GraphCanvas.qml",
        ),
    ),
    "REQ-PERF-003": DocumentRule(
        required=(
            "TRACK_H_BENCHMARK_REPORT.md",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "load",
        ),
    ),
    "AC-REQ-QA-001-02": DocumentRule(
        required=(
            "RC_PACKAGING_REPORT.md",
            "archived `2026-03-01` build/smoke summary",
        ),
    ),
    "AC-REQ-QA-001-03": DocumentRule(
        required=(
            "PILOT_SIGNOFF.md",
            "archived `2026-03-01` run",
        ),
    ),
    "REQ-QA-013": DocumentRule(
        required=(
            "scripts/check_traceability.py",
            "tests/test_traceability_checker.py",
            "GRAPH_SURFACE_INPUT_QA_MATRIX.md",
        ),
    ),
    "REQ-QA-014": DocumentRule(
        required=(
            "scripts/check_traceability.py",
            "tests/test_traceability_checker.py",
            "VERIFICATION_SPEED_QA_MATRIX.md",
        ),
    ),
    "REQ-QA-017": DocumentRule(
        required=(
            "Current verification baseline-status notes and proof audit",
            "scripts/check_traceability.py",
        ),
    ),
    "REQ-QA-015": DocumentRule(
        required=(
            "tests/test_shell_isolation_phase.py",
            "README.md",
            "docs/GETTING_STARTED.md",
            "VERIFICATION_SPEED_QA_MATRIX.md",
        ),
    ),
    "REQ-QA-016": DocumentRule(
        required=(
            "psutil.cpu_count(logical=True)",
            "README.md",
            "docs/GETTING_STARTED.md",
            "VERIFICATION_SPEED_QA_MATRIX.md",
        ),
    ),
    "REQ-QA-018": DocumentRule(
        required=(
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "TRACK_H_BENCHMARK_REPORT.md",
            "scripts/check_traceability.py",
        ),
    ),
    "AC-REQ-UI-023-01": DocumentRule(
        required=(
            "Locked graph-surface host/inline/media/shell regression matrix and proof audit",
            "tests/test_traceability_checker.py",
        ),
    ),
    "AC-REQ-QA-013-01": DocumentRule(
        required=(
            "Current graph-surface regression commands and refreshed matrix",
            "scripts/check_traceability.py",
        ),
        forbidden=(
            "approved fresh-process shell fallback",
        ),
    ),
    "AC-REQ-QA-014-01": DocumentRule(
        required=(
            "scripts/check_traceability.py",
            "tests/test_traceability_checker.py",
        ),
    ),
    "AC-REQ-QA-015-01": DocumentRule(
        required=(
            "./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run",
            "tests/test_shell_isolation_phase.py",
            "README.md",
            "docs/GETTING_STARTED.md",
        ),
    ),
    "AC-REQ-QA-016-01": DocumentRule(
        required=(
            "README.md",
            "docs/GETTING_STARTED.md",
            "VERIFICATION_SPEED_QA_MATRIX.md",
        ),
    ),
    "AC-REQ-QA-017-01": DocumentRule(
        required=(
            "Current verification baseline-status note and proof audit",
            "scripts/check_traceability.py",
        ),
        forbidden=(
            "Recorded serializer baseline caveat",
        ),
    ),
    "AC-REQ-PERF-002-01": DocumentRule(
        required=(
            "TRACK_H_BENCHMARK_REPORT.md",
            "tests/test_track_h_perf_harness.py",
            "2026-03-18",
        ),
    ),
    "AC-REQ-PERF-003-01": DocumentRule(
        required=(
            "TRACK_H_BENCHMARK_REPORT.md",
            "graph_canvas_perf_docs",
        ),
    ),
    "AC-REQ-PERF-002-02": DocumentRule(
        required=(
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "TRACK_H_BENCHMARK_REPORT.md",
        ),
    ),
    "AC-REQ-QA-018-01": DocumentRule(
        required=(
            "graph_canvas_perf_docs",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "TRACK_H_BENCHMARK_REPORT.md",
            "scripts/check_traceability.py",
        ),
    ),
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def find_traceability_row(matrix_text: str, row_id: str) -> str | None:
    for line in matrix_text.splitlines():
        if line.startswith(f"| {row_id} |"):
            return line
    return None


def audit_repository(repo_root: Path) -> list[str]:
    issues: list[str] = []
    matrix_text: str | None = None

    for relative_path in REQUIRED_ARTIFACTS:
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"Missing required artifact: {relative_path}")

    for relative_path, rule in DOCUMENT_RULES.items():
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = read_text(path)
        for snippet in rule.required:
            if snippet not in text:
                issues.append(f"{relative_path}: missing required text: {snippet}")
        for snippet in rule.forbidden:
            if snippet in text:
                issues.append(f"{relative_path}: found stale text: {snippet}")
        if relative_path == "docs/specs/requirements/TRACEABILITY_MATRIX.md":
            matrix_text = text

    if matrix_text is None:
        matrix_path = repo_root / "docs/specs/requirements/TRACEABILITY_MATRIX.md"
        if matrix_path.exists():
            matrix_text = read_text(matrix_path)

    if matrix_text is None:
        issues.append("Missing required artifact: docs/specs/requirements/TRACEABILITY_MATRIX.md")
        return issues

    for row_id, rule in TRACEABILITY_ROW_RULES.items():
        row = find_traceability_row(matrix_text, row_id)
        if row is None:
            issues.append(
                "docs/specs/requirements/TRACEABILITY_MATRIX.md: "
                f"missing row: {row_id}"
            )
            continue
        for snippet in rule.required:
            if snippet not in row:
                issues.append(
                    "docs/specs/requirements/TRACEABILITY_MATRIX.md: "
                    f"row {row_id} missing required text: {snippet}"
                )
        for snippet in rule.forbidden:
            if snippet in row:
                issues.append(
                    "docs/specs/requirements/TRACEABILITY_MATRIX.md: "
                    f"row {row_id} found stale text: {snippet}"
                )

    return issues


def main() -> int:
    issues = audit_repository(REPO_ROOT)
    if issues:
        print("TRACEABILITY CHECK FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("TRACEABILITY CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
