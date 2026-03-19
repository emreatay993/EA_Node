#!/usr/bin/env python3
"""Validate the packet-owned verification traceability layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

try:
    from verification_manifest import CHECK_TRACEABILITY_SCRIPT
    from verification_manifest import GRAPH_CANVAS_PERF_MATRIX_DOC
    from verification_manifest import GRAPH_CANVAS_REPORT_DIR
    from verification_manifest import GRAPH_CANVAS_SNAPSHOT_COMMAND
    from verification_manifest import GRAPH_SURFACE_INPUT_MATRIX_DOC
    from verification_manifest import MAX_GUI_PARALLEL_WORKERS
    from verification_manifest import MODE_NAMES
    from verification_manifest import NON_SHELL_PYTEST_IGNORES
    from verification_manifest import PROOF_AUDIT_REQUIRED_ARTIFACTS
    from verification_manifest import QA_ACCEPTANCE_DOC
    from verification_manifest import RUN_VERIFICATION_SCRIPT
    from verification_manifest import SERIALIZER_BASELINE_COMMAND
    from verification_manifest import SHELL_ISOLATION_SPEC
    from verification_manifest import TRACK_H_BENCHMARK_ARTIFACT
    from verification_manifest import TRACK_H_BENCHMARK_REPORT_DOC
    from verification_manifest import TRACK_H_REGRESSION_COMMAND
    from verification_manifest import TRACEABILITY_MATRIX_DOC
    from verification_manifest import TRACEABILITY_ROW_FORBIDDEN_TOKENS
    from verification_manifest import TRACEABILITY_ROW_REQUIRED_TOKENS
    from verification_manifest import VERIFICATION_SPEED_MATRIX_DOC
    from verification_manifest import XDIST_RESOLUTION_TOKENS
    from verification_manifest import proof_audit_command
    from verification_manifest import run_verification_command
    from verification_manifest import shell_direct_unittest_commands
    from verification_manifest import shell_isolation_pytest_command
except ModuleNotFoundError:
    from scripts.verification_manifest import CHECK_TRACEABILITY_SCRIPT
    from scripts.verification_manifest import GRAPH_CANVAS_PERF_MATRIX_DOC
    from scripts.verification_manifest import GRAPH_CANVAS_REPORT_DIR
    from scripts.verification_manifest import GRAPH_CANVAS_SNAPSHOT_COMMAND
    from scripts.verification_manifest import GRAPH_SURFACE_INPUT_MATRIX_DOC
    from scripts.verification_manifest import MAX_GUI_PARALLEL_WORKERS
    from scripts.verification_manifest import MODE_NAMES
    from scripts.verification_manifest import NON_SHELL_PYTEST_IGNORES
    from scripts.verification_manifest import PROOF_AUDIT_REQUIRED_ARTIFACTS
    from scripts.verification_manifest import QA_ACCEPTANCE_DOC
    from scripts.verification_manifest import RUN_VERIFICATION_SCRIPT
    from scripts.verification_manifest import SERIALIZER_BASELINE_COMMAND
    from scripts.verification_manifest import SHELL_ISOLATION_SPEC
    from scripts.verification_manifest import TRACK_H_BENCHMARK_ARTIFACT
    from scripts.verification_manifest import TRACK_H_BENCHMARK_REPORT_DOC
    from scripts.verification_manifest import TRACK_H_REGRESSION_COMMAND
    from scripts.verification_manifest import TRACEABILITY_MATRIX_DOC
    from scripts.verification_manifest import TRACEABILITY_ROW_FORBIDDEN_TOKENS
    from scripts.verification_manifest import TRACEABILITY_ROW_REQUIRED_TOKENS
    from scripts.verification_manifest import VERIFICATION_SPEED_MATRIX_DOC
    from scripts.verification_manifest import XDIST_RESOLUTION_TOKENS
    from scripts.verification_manifest import proof_audit_command
    from scripts.verification_manifest import run_verification_command
    from scripts.verification_manifest import shell_direct_unittest_commands
    from scripts.verification_manifest import shell_isolation_pytest_command

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ARTIFACTS = PROOF_AUDIT_REQUIRED_ARTIFACTS
OLD_SHELL_TAIL_RESULT_PATTERN = re.compile(r"^`\d+\.\d+s` mean across `\d+` reps$")
SHELL_ISOLATION_RESULT_PATTERN = re.compile(r"^`\d+ passed in \d+\.\d+s`$")


@dataclass(frozen=True)
class DocumentRule:
    required: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


GENERIC_DOCUMENT_RULES: dict[str, DocumentRule] = {
    "README.md": DocumentRule(
        required=(
            CHECK_TRACEABILITY_SCRIPT,
            "Graph Surface Input QA Matrix",
            "Verification Speed QA Matrix",
            "dedicated fresh-process shell-isolation phase",
            SHELL_ISOLATION_SPEC.test_path,
            "proof-audit command",
        ),
        forbidden=(
            "serializer caveat.",
            "shell-wrapper suites for isolated `unittest` execution",
        ),
    ),
    "docs/GETTING_STARTED.md": DocumentRule(
        required=(
            CHECK_TRACEABILITY_SCRIPT,
            SHELL_ISOLATION_SPEC.test_path,
            XDIST_RESOLUTION_TOKENS[0],
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
    QA_ACCEPTANCE_DOC: DocumentRule(
        forbidden=(
            "the four shell-wrapper modules `tests.test_main_window_shell`, "
            "`tests.test_script_editor_dock`, `tests.test_shell_run_controller`, and "
            "`tests.test_shell_project_session_controller` shall remain on explicit "
            "fresh-process `unittest` execution",
            "on separate `unittest` commands after the pytest phases",
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def strip_code_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped


def extract_section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return None
    return match.group("body").strip("\n")


def parse_markdown_table(section_text: str) -> list[dict[str, str]] | None:
    table_lines: list[str] = []
    in_table = False
    for line in section_text.splitlines():
        if line.startswith("|"):
            table_lines.append(line)
            in_table = True
            continue
        if in_table:
            break
    if len(table_lines) < 2:
        return None

    headers = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def table_after_heading(
    text: str,
    *,
    relative_path: str,
    heading: str,
    issues: list[str],
) -> list[dict[str, str]] | None:
    section = extract_section(text, heading)
    if section is None:
        issues.append(f"{relative_path}: missing section: {heading}")
        return None
    rows = parse_markdown_table(section)
    if rows is None:
        issues.append(f"{relative_path}: missing markdown table in section: {heading}")
        return None
    return rows


def find_row(
    rows: list[dict[str, str]],
    *,
    column: str,
    predicate,
) -> dict[str, str] | None:
    for row in rows:
        value = row.get(column, "")
        if predicate(value):
            return row
    return None


def require_tokens(
    text: str,
    tokens: tuple[str, ...],
    *,
    relative_path: str,
    label: str,
    issues: list[str],
) -> None:
    for token in tokens:
        if token not in text:
            issues.append(f"{relative_path}: {label} missing fact: {token}")


def require_command_result(
    rows: list[dict[str, str]],
    *,
    relative_path: str,
    heading: str,
    predicate,
    label: str,
    issues: list[str],
) -> dict[str, str] | None:
    row = find_row(rows, column="Command", predicate=lambda value: predicate(strip_code_fence(value)))
    if row is None:
        issues.append(f"{relative_path}: {heading} missing command row: {label}")
        return None
    result = strip_code_fence(row.get("Result", ""))
    if result != "PASS":
        issues.append(
            f"{relative_path}: {heading} command {label} has unexpected result: {result}"
        )
    return row


def parse_requirement_lines(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^- `([^`]+)`: (.+)$", line.strip())
        if match is not None:
            parsed[match.group(1)] = match.group(2)
    return parsed


def audit_generic_document_rule(
    *,
    relative_path: str,
    text: str,
    rule: DocumentRule,
    issues: list[str],
) -> None:
    for snippet in rule.required:
        if snippet not in text:
            issues.append(f"{relative_path}: missing required text: {snippet}")
    for snippet in rule.forbidden:
        if snippet in text:
            issues.append(f"{relative_path}: found stale text: {snippet}")


def audit_qa_acceptance(text: str, relative_path: str, issues: list[str]) -> None:
    requirements = parse_requirement_lines(text)
    required_tokens = {
        "REQ-QA-014": (RUN_VERIFICATION_SCRIPT, *MODE_NAMES),
        "REQ-QA-015": (SHELL_ISOLATION_SPEC.test_path, *SHELL_ISOLATION_SPEC.shell_module_names),
        "REQ-QA-016": ("pytest-xdist", *XDIST_RESOLUTION_TOKENS),
        "REQ-QA-017": ("baseline failures", "fully green aggregate"),
        "REQ-QA-018": ("GraphCanvas.qml", "interactive desktop/manual follow-up"),
        "AC-REQ-QA-014-01": (run_verification_command("full", dry_run=True), "VERIFICATION_SPEED_QA_MATRIX.md"),
        "AC-REQ-QA-015-01": (
            SHELL_ISOLATION_SPEC.test_path,
            *SHELL_ISOLATION_SPEC.shell_module_names,
        ),
        "AC-REQ-QA-016-01": ("VERIFICATION_SPEED_QA_MATRIX.md",),
        "AC-REQ-QA-018-01": (
            GRAPH_CANVAS_SNAPSHOT_COMMAND,
            proof_audit_command(),
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
            "TRACK_H_BENCHMARK_REPORT.md",
        ),
    }
    for requirement_id, tokens in required_tokens.items():
        body = requirements.get(requirement_id)
        if body is None:
            issues.append(f"{relative_path}: missing requirement line: {requirement_id}")
            continue
        require_tokens(
            body,
            tokens,
            relative_path=relative_path,
            label=f"requirement {requirement_id}",
            issues=issues,
        )


def audit_verification_speed_matrix(text: str, relative_path: str, issues: list[str]) -> None:
    for forbidden in (
        "isolated shell-wrapper `unittest` phase",
        "adds `-n auto` only when `pytest-xdist` is importable in the project venv",
    ):
        if forbidden in text:
            issues.append(f"{relative_path}: found stale text: {forbidden}")

    workflow_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Approved Verification Workflow",
        issues=issues,
    )
    if workflow_rows is not None:
        for mode in MODE_NAMES:
            row = find_row(
                workflow_rows,
                column="Mode",
                predicate=lambda value, mode=mode: strip_code_fence(value) == mode,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Approved Verification Workflow missing mode row: {mode}"
                )
                continue
            command = strip_code_fence(row.get("Command", ""))
            expected_command = run_verification_command(mode)
            if command != expected_command:
                issues.append(
                    f"{relative_path}: Approved Verification Workflow row {mode} has unexpected command: {command}"
                )
            notes = row.get("Notes", "")
            if mode in {"fast", "gui"}:
                require_tokens(
                    notes,
                    ("pytest-xdist", XDIST_RESOLUTION_TOKENS[0]),
                    relative_path=relative_path,
                    label=f"workflow row {mode}",
                    issues=issues,
                )
            if mode == "fast":
                require_tokens(
                    notes,
                    ("not gui and not slow", SHELL_ISOLATION_SPEC.test_path),
                    relative_path=relative_path,
                    label="workflow row fast",
                    issues=issues,
                )
            elif mode == "gui":
                require_tokens(
                    notes,
                    (str(MAX_GUI_PARALLEL_WORKERS), SHELL_ISOLATION_SPEC.test_path),
                    relative_path=relative_path,
                    label="workflow row gui",
                    issues=issues,
                )
            elif mode == "slow":
                require_tokens(
                    notes,
                    ("Serial", SHELL_ISOLATION_SPEC.test_path),
                    relative_path=relative_path,
                    label="workflow row slow",
                    issues=issues,
                )
            else:
                require_tokens(
                    notes,
                    ("--dry-run",),
                    relative_path=relative_path,
                    label="workflow row full",
                    issues=issues,
                )

    shell_rules = extract_section(text, "Locked Shell Isolation Rules")
    if shell_rules is None:
        issues.append(f"{relative_path}: missing section: Locked Shell Isolation Rules")
    else:
        require_tokens(
            shell_rules,
            tuple(f"--ignore={path}" for path in NON_SHELL_PYTEST_IGNORES),
            relative_path=relative_path,
            label="Locked Shell Isolation Rules",
            issues=issues,
        )
        require_tokens(
            shell_rules,
            (
                shell_isolation_pytest_command(),
                *XDIST_RESOLUTION_TOKENS,
                *shell_direct_unittest_commands(),
            ),
            relative_path=relative_path,
            label="Locked Shell Isolation Rules",
            issues=issues,
        )

    benchmark_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Published Shell-Tail Benchmark Evidence",
        issues=issues,
    )
    if benchmark_rows is not None:
        old_row = find_row(
            benchmark_rows,
            column="Workflow Shape",
            predicate=lambda value: value == "Old sequential shell-tail baseline",
        )
        if old_row is None:
            issues.append(
                f"{relative_path}: Published Shell-Tail Benchmark Evidence missing row: Old sequential shell-tail baseline"
            )
        elif not OLD_SHELL_TAIL_RESULT_PATTERN.match(old_row.get("Recorded Result", "")):
            issues.append(
                f"{relative_path}: old shell-tail benchmark result is not a timed mean summary: {old_row.get('Recorded Result', '')}"
            )

        dedicated_row = find_row(
            benchmark_rows,
            column="Workflow Shape",
            predicate=lambda value: value == "Dedicated shell-isolation phase",
        )
        if dedicated_row is None:
            issues.append(
                f"{relative_path}: Published Shell-Tail Benchmark Evidence missing row: Dedicated shell-isolation phase"
            )
        else:
            result = dedicated_row.get("Recorded Result", "")
            if not SHELL_ISOLATION_RESULT_PATTERN.match(result):
                issues.append(
                    f"{relative_path}: dedicated shell-isolation benchmark result is not a pytest timing summary: {result}"
                )

    environment_notes = extract_section(text, "Current Environment Notes")
    if environment_notes is None:
        issues.append(f"{relative_path}: missing section: Current Environment Notes")
    else:
        require_tokens(
            environment_notes,
            (
                run_verification_command("fast").split()[0],
                "pytest-xdist",
                XDIST_RESOLUTION_TOKENS[0],
                str(MAX_GUI_PARALLEL_WORKERS),
            ),
            relative_path=relative_path,
            label="Current Environment Notes",
            issues=issues,
        )

    proof_audit = extract_section(text, "Companion Proof Audit")
    if proof_audit is None:
        issues.append(f"{relative_path}: missing section: Companion Proof Audit")
    else:
        require_tokens(
            proof_audit,
            (proof_audit_command(), CHECK_TRACEABILITY_SCRIPT),
            relative_path=relative_path,
            label="Companion Proof Audit",
            issues=issues,
        )

    baseline_status = extract_section(text, "Current Baseline Status")
    if baseline_status is None:
        issues.append(f"{relative_path}: missing section: Current Baseline Status")
    else:
        require_tokens(
            baseline_status,
            (
                SERIALIZER_BASELINE_COMMAND,
                "retired",
                "No known out-of-scope verification baseline failures remain",
            ),
            relative_path=relative_path,
            label="Current Baseline Status",
            issues=issues,
        )
        for forbidden in (
            "serializer baseline remains open",
            "still fails because passive image-panel round-trips add default crop fields",
        ):
            if forbidden in baseline_status:
                issues.append(f"{relative_path}: found stale text: {forbidden}")

    result_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-03-18 Verification Results",
        issues=issues,
    )
    if result_rows is not None:
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: command == run_verification_command("full", dry_run=True),
            label=run_verification_command("full", dry_run=True),
            issues=issues,
        )
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: (
                command.startswith(
                    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest "
                    f"{SHELL_ISOLATION_SPEC.test_path} -q"
                )
                and "--dist load" in command
            ),
            label=SHELL_ISOLATION_SPEC.test_path,
            issues=issues,
        )
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: command == SERIALIZER_BASELINE_COMMAND,
            label=SERIALIZER_BASELINE_COMMAND,
            issues=issues,
        )


def audit_graph_canvas_perf_matrix(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        (
            "## Locked Benchmark Contract",
            "GraphCanvas.qml",
            "## Desktop/Manual Follow-Up",
            "desktop/manual",
            "outstanding",
        ),
        relative_path=relative_path,
        label="graph-canvas perf matrix",
        issues=issues,
    )

    approved_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Approved Regression Commands",
        issues=issues,
    )
    if approved_rows is not None:
        expected_commands = (
            TRACK_H_REGRESSION_COMMAND,
            GRAPH_CANVAS_SNAPSHOT_COMMAND,
            proof_audit_command(),
        )
        for command in expected_commands:
            row = find_row(
                approved_rows,
                column="Command",
                predicate=lambda value, command=command: strip_code_fence(value) == command,
            )
            if row is None:
                issues.append(
                    f"{relative_path}: Approved Regression Commands missing command row: {command}"
                )

    execution_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="2026-03-18 Execution Results",
        issues=issues,
    )
    if execution_rows is not None:
        for command in (
            TRACK_H_REGRESSION_COMMAND,
            GRAPH_CANVAS_SNAPSHOT_COMMAND,
            proof_audit_command(),
        ):
            require_command_result(
                execution_rows,
                relative_path=relative_path,
                heading="2026-03-18 Execution Results",
                predicate=lambda value, command=command: value == command,
                label=command,
                issues=issues,
            )


def audit_track_h_report(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        (
            "GraphCanvas.qml",
            "offscreen regression snapshot",
            "`P04`",
            GRAPH_CANVAS_SNAPSHOT_COMMAND,
            TRACK_H_BENCHMARK_ARTIFACT,
            "## 2026-03-18 Offscreen Snapshot",
            "Interactive desktop/GPU validation remains required",
            "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        ),
        relative_path=relative_path,
        label="track-h benchmark report",
        issues=issues,
    )
    for forbidden in (
        "Historical offscreen harness baseline restored from repo",
        "P08 did not rerun the performance harness.",
    ):
        if forbidden in text:
            issues.append(f"{relative_path}: found stale text: {forbidden}")


def find_traceability_row(matrix_text: str, row_id: str) -> str | None:
    for line in matrix_text.splitlines():
        if line.startswith(f"| {row_id} |"):
            return line
    return None


def audit_traceability_rows(matrix_text: str, issues: list[str]) -> None:
    for row_id, required_tokens in TRACEABILITY_ROW_REQUIRED_TOKENS.items():
        row = find_traceability_row(matrix_text, row_id)
        if row is None:
            issues.append(f"{TRACEABILITY_MATRIX_DOC}: missing row: {row_id}")
            continue
        for token in required_tokens:
            if token not in row:
                issues.append(
                    f"{TRACEABILITY_MATRIX_DOC}: row {row_id} missing required text: {token}"
                )
        for token in TRACEABILITY_ROW_FORBIDDEN_TOKENS.get(row_id, ()):
            if token in row:
                issues.append(
                    f"{TRACEABILITY_MATRIX_DOC}: row {row_id} found stale text: {token}"
                )


SPECIAL_DOCUMENT_AUDITORS = {
    QA_ACCEPTANCE_DOC: audit_qa_acceptance,
    VERIFICATION_SPEED_MATRIX_DOC: audit_verification_speed_matrix,
    GRAPH_CANVAS_PERF_MATRIX_DOC: audit_graph_canvas_perf_matrix,
    TRACK_H_BENCHMARK_REPORT_DOC: audit_track_h_report,
}


def audit_repository(repo_root: Path) -> list[str]:
    issues: list[str] = []
    matrix_text: str | None = None

    for relative_path in REQUIRED_ARTIFACTS:
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"Missing required artifact: {relative_path}")

    audited_documents = set(GENERIC_DOCUMENT_RULES) | set(SPECIAL_DOCUMENT_AUDITORS)
    for relative_path in audited_documents:
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = read_text(path)
        if relative_path == TRACEABILITY_MATRIX_DOC:
            matrix_text = text
        rule = GENERIC_DOCUMENT_RULES.get(relative_path)
        if rule is not None:
            audit_generic_document_rule(
                relative_path=relative_path,
                text=text,
                rule=rule,
                issues=issues,
            )
        auditor = SPECIAL_DOCUMENT_AUDITORS.get(relative_path)
        if auditor is not None:
            auditor(text, relative_path, issues)

    if matrix_text is None:
        matrix_path = repo_root / TRACEABILITY_MATRIX_DOC
        if matrix_path.exists():
            matrix_text = read_text(matrix_path)

    if matrix_text is None:
        issues.append(f"Missing required artifact: {TRACEABILITY_MATRIX_DOC}")
        return issues

    audit_traceability_rows(matrix_text, issues)
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
