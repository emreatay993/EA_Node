#!/usr/bin/env python3
"""Validate the packet-owned verification traceability layer."""

from __future__ import annotations

from pathlib import Path
import re
import sys

try:
    import verification_manifest as manifest
except ModuleNotFoundError:
    import scripts.verification_manifest as manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ARTIFACTS = manifest.PROOF_AUDIT_REQUIRED_ARTIFACTS
GENERIC_DOCUMENT_RULES = manifest.GENERIC_DOCUMENT_RULES
OLD_SHELL_TAIL_RESULT_PATTERN = re.compile(r"^`\d+\.\d+s` mean across `\d+` reps$")
SHELL_ISOLATION_RESULT_PATTERN = re.compile(r"^`\d+ passed in \d+\.\d+s`$")

P10_TRACEABILITY_TEST_COMMAND = (
    "./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q"
)
GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR = "artifacts/graphics_performance_modes_docs"
GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD = (
    f"{GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR}/TRACK_H_BENCHMARK_REPORT.md"
)
GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON = (
    f"{GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR}/track_h_benchmark_report.json"
)
P10_REQUIRED_GENERATED_ARTIFACTS = (
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
)
GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND = (
    "QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe "
    "-m ea_node_editor.telemetry.performance_harness "
    "--nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 "
    "--baseline-runs 1 --performance-mode max_performance --scenario heavy_media "
    f"--report-dir {GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR}"
)
GRAPHICS_PERFORMANCE_MODES_INTERACTIVE_COMMAND = (
    "QT_QPA_PLATFORM=windows ./venv/Scripts/python.exe "
    "-m ea_node_editor.telemetry.performance_harness "
    "--nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 "
    "--baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference "
    "--performance-mode max_performance --scenario heavy_media "
    f"--report-dir {GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR}"
)

P10_REQUIREMENT_DOC_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "docs/specs/requirements/20_UI_UX.md": {
        "REQ-UI-016": ("graphics performance mode", "Full Fidelity", "Max Performance"),
        "REQ-UI-024": ("status strip", "Graphics:", "same persisted preference"),
        "AC-REQ-UI-016-01": ("graphics performance mode", "shell-theme", "graph-theme"),
        "AC-REQ-UI-024-01": ("status-strip", "Graphics Settings", "saved mode"),
    },
    "docs/specs/requirements/40_NODE_SDK.md": {
        "REQ-NODE-016": (
            "render_quality",
            "weight_class",
            "max_performance_strategy",
            "supported_quality_tiers",
            "safe defaults",
        ),
        "AC-REQ-NODE-016-01": ("render_quality", "graph-surface payload", "safe defaults"),
    },
    "docs/specs/requirements/60_PERSISTENCE.md": {
        "REQ-PERSIST-011": ("graphics performance mode", "user_data_dir()", "last_session.json"),
        "AC-REQ-PERSIST-011-01": ("graphics performance mode", "last_session.json"),
    },
    "docs/specs/requirements/80_PERFORMANCE.md": {
        "REQ-PERF-006": (
            "full_fidelity",
            "max_performance",
            "whole-canvas simplification",
            "proxy-surface",
            "steady-state idle appearance returns automatically",
        ),
        "AC-REQ-PERF-002-01": (
            "performance_mode",
            "resolved_graphics_performance_mode",
            "scenario",
            "media_surface_count",
            "GraphCanvas.qml",
        ),
        "AC-REQ-PERF-002-02": (
            "--performance-mode max_performance --scenario heavy_media",
            GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
            "interactive desktop/manual",
        ),
        "AC-REQ-PERF-003-01": (
            GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
            "mode-aware heavy-media benchmark workflow",
        ),
    },
}

P10_QA_ACCEPTANCE_REQUIREMENT_TOKENS = {
    "REQ-QA-009": ("graphics-performance", "status-strip quick-toggle", "canvas preference behavior"),
    "REQ-QA-011": ("render-quality metadata", "built-in media proxy behavior"),
    "REQ-QA-018": (
        "performance_mode",
        "scenario",
        "canonical artifact path",
        "interactive desktop/manual follow-up",
    ),
    "AC-REQ-QA-018-01": (
        GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
        manifest.proof_audit_command(),
        manifest.GRAPH_CANVAS_PERF_MATRIX_DOC,
        manifest.TRACK_H_BENCHMARK_REPORT_DOC,
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    ),
}
QA_ACCEPTANCE_REQUIREMENT_TOKENS = dict(manifest.QA_ACCEPTANCE_REQUIREMENT_TOKENS)
QA_ACCEPTANCE_REQUIREMENT_TOKENS.update(P10_QA_ACCEPTANCE_REQUIREMENT_TOKENS)

GRAPHICS_PERFORMANCE_MODES_MATRIX_REQUIRED_TOKENS = (
    "GRAPHICS_PERFORMANCE_MODES",
    "GraphCanvas.qml",
    "--performance-mode max_performance --scenario heavy_media",
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
    "## Desktop/Manual Follow-Up",
    "outstanding",
)
GRAPHICS_PERFORMANCE_MODES_MATRIX_AUDIT_COMMANDS = (
    P10_TRACEABILITY_TEST_COMMAND,
    GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
    manifest.proof_audit_command(),
)
GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_REQUIRED_TOKENS = (
    "GraphCanvas.qml",
    GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
    GRAPHICS_PERFORMANCE_MODES_INTERACTIVE_COMMAND,
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
    GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    "Performance mode: `max_performance`",
    "Scenario: `heavy_media`",
    "Resolved canvas mode: `max_performance`",
    "Media surface count: `6`",
    "## 2026-03-20 Offscreen Snapshot",
    "Interactive desktop/GPU validation remains required",
    manifest.GRAPH_CANVAS_PERF_MATRIX_DOC,
)
GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_FORBIDDEN_TOKENS = (
    "artifacts/graph_canvas_perf_docs",
    "Historical offscreen harness baseline restored from repo",
    "`P04`",
    "P08 did not rerun the performance harness.",
)

P10_TRACEABILITY_ROW_REQUIRED_TOKENS = {
    "REQ-UI-016": (
        "graphics_settings_dialog.py",
        "show_graphics_settings_dialog",
        "tests/test_graphics_settings_preferences.py",
    ),
    "REQ-UI-024": ("ShellStatusStrip.qml", "shell_runtime_contracts.py", "bridge_qml_boundaries.py"),
    "AC-REQ-UI-016-01": (
        "tests/test_graphics_settings_preferences.py",
        "tests/test_shell_theme.py",
        "tests/test_main_window_shell.py",
    ),
    "AC-REQ-UI-024-01": (
        "shell_runtime_contracts.py",
        "bridge_qml_boundaries.py",
        "P03_status_strip_quick_toggle_WRAPUP.md",
    ),
    "REQ-NODE-016": (
        "graph_scene_payload_builder.py",
        "tests/test_graph_surface_input_contract.py",
        "tests/test_passive_node_contracts.py",
    ),
    "AC-REQ-NODE-016-01": (
        "tests/test_graph_surface_input_contract.py",
        "tests/test_passive_node_contracts.py",
        "tests/test_registry_validation.py",
    ),
    "REQ-PERSIST-011": (
        "tests/test_graphics_settings_preferences.py",
        "tests/main_window_shell/shell_basics_and_search.py",
    ),
    "AC-REQ-PERSIST-011-01": (
        "tests/test_shell_project_session_controller.py",
        "tests/main_window_shell/shell_basics_and_search.py",
    ),
    "REQ-PERF-001": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    ),
    "REQ-PERF-002": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        "GraphCanvas.qml",
    ),
    "REQ-PERF-003": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        "load",
    ),
    "REQ-PERF-006": (
        "GraphCanvasPerformancePolicy.js",
        "tests/graph_track_b/qml_preference_bindings.py",
        "tests/test_passive_graph_surface_host.py",
    ),
    "REQ-QA-009": (
        "shell_runtime_contracts.py",
        "bridge_qml_boundaries.py",
        "tests/test_graphics_settings_dialog.py",
    ),
    "REQ-QA-011": (
        "tests/test_graph_surface_input_contract.py",
        "tests/test_passive_node_contracts.py",
        "tests/test_passive_graph_surface_host.py",
    ),
    "REQ-QA-018": (
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        manifest.CHECK_TRACEABILITY_SCRIPT,
    ),
    "AC-REQ-PERF-002-01": (
        "TRACK_H_BENCHMARK_REPORT.md",
        "tests/test_track_h_perf_harness.py",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
    ),
    "AC-REQ-PERF-003-01": (
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
    ),
    "AC-REQ-PERF-002-02": (
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_DIR,
    ),
    "AC-REQ-QA-018-01": (
        GRAPHICS_PERFORMANCE_MODES_OFFSCREEN_COMMAND,
        "GRAPH_CANVAS_PERF_QA_MATRIX.md",
        "TRACK_H_BENCHMARK_REPORT.md",
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_MD,
        GRAPHICS_PERFORMANCE_MODES_CANONICAL_REPORT_JSON,
        manifest.CHECK_TRACEABILITY_SCRIPT,
    ),
}
TRACEABILITY_ROW_REQUIRED_TOKENS = dict(manifest.TRACEABILITY_ROW_REQUIRED_TOKENS)
TRACEABILITY_ROW_REQUIRED_TOKENS.update(P10_TRACEABILITY_ROW_REQUIRED_TOKENS)

P10_TRACEABILITY_ROW_FORBIDDEN_TOKENS = {
    "REQ-QA-018": ("artifacts/graph_canvas_perf_docs",),
    "AC-REQ-PERF-003-01": ("artifacts/graph_canvas_perf_docs",),
    "AC-REQ-QA-018-01": ("artifacts/graph_canvas_perf_docs",),
}
TRACEABILITY_ROW_FORBIDDEN_TOKENS = dict(manifest.TRACEABILITY_ROW_FORBIDDEN_TOKENS)
TRACEABILITY_ROW_FORBIDDEN_TOKENS.update(P10_TRACEABILITY_ROW_FORBIDDEN_TOKENS)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def strip_code_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped


def strip_worktree_ignore_args(command: str) -> str:
    stripped = command
    for arg in manifest.worktree_pytest_ignore_args():
        stripped = stripped.replace(f" {arg}", "")
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


def audit_requirement_tokens(
    text: str,
    relative_path: str,
    requirement_tokens: dict[str, tuple[str, ...]],
    issues: list[str],
) -> None:
    requirements = parse_requirement_lines(text)
    for requirement_id, tokens in requirement_tokens.items():
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


def audit_generic_document_rule(
    *,
    relative_path: str,
    text: str,
    rule: manifest.DocumentRule,
    issues: list[str],
) -> None:
    for snippet in rule.required:
        if snippet not in text:
            issues.append(f"{relative_path}: missing required text: {snippet}")
    for snippet in rule.forbidden:
        if snippet in text:
            issues.append(f"{relative_path}: found stale text: {snippet}")


def audit_qa_acceptance(text: str, relative_path: str, issues: list[str]) -> None:
    audit_requirement_tokens(text, relative_path, QA_ACCEPTANCE_REQUIREMENT_TOKENS, issues)


def audit_requirement_doc(text: str, relative_path: str, issues: list[str]) -> None:
    requirement_tokens = P10_REQUIREMENT_DOC_TOKENS.get(relative_path)
    if requirement_tokens is None:
        return
    audit_requirement_tokens(text, relative_path, requirement_tokens, issues)


def audit_verification_speed_matrix(text: str, relative_path: str, issues: list[str]) -> None:
    for forbidden in manifest.VERIFICATION_SPEED_FORBIDDEN_TOKENS:
        if forbidden in text:
            issues.append(f"{relative_path}: found stale text: {forbidden}")

    workflow_rows = table_after_heading(
        text,
        relative_path=relative_path,
        heading="Approved Verification Workflow",
        issues=issues,
    )
    if workflow_rows is not None:
        for mode in manifest.MODE_NAMES:
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
            expected_command = manifest.run_verification_command(mode)
            if command != expected_command:
                issues.append(
                    f"{relative_path}: Approved Verification Workflow row {mode} has unexpected command: {command}"
                )
            require_tokens(
                row.get("Notes", ""),
                manifest.VERIFICATION_SPEED_WORKFLOW_NOTE_TOKENS[mode],
                relative_path=relative_path,
                label=f"workflow row {mode}",
                issues=issues,
            )

    shell_rules = extract_section(text, "Locked Shell Isolation Rules")
    if shell_rules is None:
        issues.append(f"{relative_path}: missing section: Locked Shell Isolation Rules")
    else:
        shell_rule_command = manifest.shell_isolation_pytest_command()
        require_tokens(
            shell_rules,
            tuple(
                token
                for token in manifest.VERIFICATION_SPEED_SHELL_RULE_TOKENS
                if token != shell_rule_command
            ),
            relative_path=relative_path,
            label="Locked Shell Isolation Rules",
            issues=issues,
        )
        if (
            shell_rule_command not in shell_rules
            and strip_worktree_ignore_args(shell_rule_command) not in shell_rules
        ):
            issues.append(
                f"{relative_path}: Locked Shell Isolation Rules missing fact: "
                f"{shell_rule_command}"
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
            manifest.VERIFICATION_SPEED_ENVIRONMENT_NOTE_TOKENS,
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
            manifest.VERIFICATION_SPEED_COMPANION_PROOF_TOKENS,
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
            manifest.VERIFICATION_SPEED_BASELINE_REQUIRED_TOKENS,
            relative_path=relative_path,
            label="Current Baseline Status",
            issues=issues,
        )
        for forbidden in manifest.VERIFICATION_SPEED_BASELINE_FORBIDDEN_TOKENS:
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
            predicate=lambda command: command == manifest.VERIFICATION_SPEED_RESULT_COMMANDS[0],
            label=manifest.VERIFICATION_SPEED_RESULT_COMMANDS[0],
            issues=issues,
        )
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: (
                (
                    command.startswith(manifest.VERIFICATION_SPEED_SHELL_RESULT_COMMAND_PREFIX)
                    or command.startswith(
                        strip_worktree_ignore_args(
                            manifest.VERIFICATION_SPEED_SHELL_RESULT_COMMAND_PREFIX
                        )
                    )
                )
                and all(
                    token in command
                    for token in manifest.VERIFICATION_SPEED_SHELL_RESULT_REQUIRED_TOKENS
                )
            ),
            label=manifest.SHELL_ISOLATION_SPEC.test_path,
            issues=issues,
        )
        require_command_result(
            result_rows,
            relative_path=relative_path,
            heading="2026-03-18 Verification Results",
            predicate=lambda command: command == manifest.VERIFICATION_SPEED_RESULT_COMMANDS[1],
            label=manifest.VERIFICATION_SPEED_RESULT_COMMANDS[1],
            issues=issues,
        )


def audit_graph_canvas_perf_matrix(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        GRAPHICS_PERFORMANCE_MODES_MATRIX_REQUIRED_TOKENS,
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
        for command in GRAPHICS_PERFORMANCE_MODES_MATRIX_AUDIT_COMMANDS:
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
        heading="2026-03-20 Execution Results",
        issues=issues,
    )
    if execution_rows is not None:
        for command in GRAPHICS_PERFORMANCE_MODES_MATRIX_AUDIT_COMMANDS:
            require_command_result(
                execution_rows,
                relative_path=relative_path,
                heading="2026-03-20 Execution Results",
                predicate=lambda value, command=command: value == command,
                label=command,
                issues=issues,
            )


def audit_track_h_report(text: str, relative_path: str, issues: list[str]) -> None:
    require_tokens(
        text,
        GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_REQUIRED_TOKENS,
        relative_path=relative_path,
        label="track-h benchmark report",
        issues=issues,
    )
    for forbidden in GRAPHICS_PERFORMANCE_MODES_TRACK_H_REPORT_FORBIDDEN_TOKENS:
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
            issues.append(f"{manifest.TRACEABILITY_MATRIX_DOC}: missing row: {row_id}")
            continue
        for token in required_tokens:
            if token not in row:
                issues.append(
                    f"{manifest.TRACEABILITY_MATRIX_DOC}: row {row_id} missing required text: {token}"
                )
        for token in TRACEABILITY_ROW_FORBIDDEN_TOKENS.get(row_id, ()):
            if token in row:
                issues.append(
                    f"{manifest.TRACEABILITY_MATRIX_DOC}: row {row_id} found stale text: {token}"
                )


SPECIAL_DOCUMENT_AUDITORS = {
    "docs/specs/requirements/20_UI_UX.md": audit_requirement_doc,
    "docs/specs/requirements/40_NODE_SDK.md": audit_requirement_doc,
    "docs/specs/requirements/60_PERSISTENCE.md": audit_requirement_doc,
    "docs/specs/requirements/80_PERFORMANCE.md": audit_requirement_doc,
    manifest.QA_ACCEPTANCE_DOC: audit_qa_acceptance,
    manifest.VERIFICATION_SPEED_MATRIX_DOC: audit_verification_speed_matrix,
    manifest.GRAPH_CANVAS_PERF_MATRIX_DOC: audit_graph_canvas_perf_matrix,
    manifest.TRACK_H_BENCHMARK_REPORT_DOC: audit_track_h_report,
}


def audit_repository(repo_root: Path) -> list[str]:
    issues: list[str] = []
    matrix_text: str | None = None

    for relative_path in REQUIRED_ARTIFACTS:
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"Missing required artifact: {relative_path}")
    for relative_path in P10_REQUIRED_GENERATED_ARTIFACTS:
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"Missing required generated artifact: {relative_path}")

    audited_documents = set(GENERIC_DOCUMENT_RULES) | set(SPECIAL_DOCUMENT_AUDITORS)
    for relative_path in audited_documents:
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = read_text(path)
        if relative_path == manifest.TRACEABILITY_MATRIX_DOC:
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
        matrix_path = repo_root / manifest.TRACEABILITY_MATRIX_DOC
        if matrix_path.exists():
            matrix_text = read_text(matrix_path)

    if matrix_text is None:
        issues.append(f"Missing required artifact: {manifest.TRACEABILITY_MATRIX_DOC}")
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
