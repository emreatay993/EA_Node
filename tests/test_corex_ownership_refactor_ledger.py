from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/specs/perf/COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR_QA_MATRIX.md"
PLAN = ROOT / "docs/PLAN_COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR.md"

TASK_STATUSES = {
    "NOT STARTED",
    "IN PROGRESS",
    "ACCEPTED",
    "ACCEPTED NO-OP",
    "BLOCKED",
}
FINAL_DISPOSITIONS = {
    "retained",
    "moved_to_owner",
    "replaced_by_owner_test",
    "replaced_by_qml_quick",
    "retained_real_shell_lifecycle",
    "redundant_existing_owner_proof",
    "deleted_obsolete_behavior",
}
PENDING_DISPOSITION = "pending_migration"
MIGRATION_HEADER = (
    "Program",
    "Owning task",
    "ID kind",
    "Old ID / selector / target",
    "Behavior guarded",
    "Production owner",
    "Phase / isolation",
    "Disposition",
    "Replacement IDs / selectors",
    "Assertion equivalence",
    "Collecting commit",
    "Execution result",
    "Accepted commit",
)
PHASES_BY_KIND = {
    "python": {
        "fast.pytest",
        "fast.serial.pytest",
        "gui.pytest",
        "gui.serial.pytest",
        "slow.pytest",
    },
    "qml_quick": {"gui.qml_quick / qmltestrunner"},
    "shell_target": {"full.shell_isolation / child process"},
}
COMMIT_RE = re.compile(r"^(?:This commit|[0-9a-f]{8,40})$")


def _table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    table = [
        [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.startswith("|") and not re.match(r"^\|\s*-", line)
    ]
    return table[0], table[1:]


def _top_status(text: str) -> str:
    match = re.search(r"(?m)^Status: `([^`]+)`$", text)
    assert match is not None
    return match.group(1)


def _task_statuses(rows: list[list[str]]) -> dict[str, str]:
    return {row[0].split()[0]: row[2] for row in rows}


def _validate_tasks(rows: list[list[str]]) -> list[int]:
    assert all(len(row) == 9 for row in rows)
    task_ids = [row[0].split()[0] for row in rows]
    statuses = [row[2] for row in rows]
    assert task_ids == [f"T{index:02d}" for index in range(27)]
    assert set(statuses) <= TASK_STATUSES

    active = [
        index
        for index, status in enumerate(statuses)
        if status in {"IN PROGRESS", "BLOCKED"}
    ]
    assert len(active) <= 1
    boundary = active[0] if active else next(
        (index for index, status in enumerate(statuses) if status == "NOT STARTED"),
        len(statuses),
    )
    assert all(
        status in {"ACCEPTED", "ACCEPTED NO-OP"}
        for status in statuses[:boundary]
    )
    if active:
        assert all(status == "NOT STARTED" for status in statuses[boundary + 1 :])
    else:
        assert all(status == "NOT STARTED" for status in statuses[boundary:])

    for row in rows:
        status = row[2]
        if status not in {"ACCEPTED", "ACCEPTED NO-OP"}:
            continue
        writer, focused, performance, review, commit = (
            row[3], row[5], row[6], row[7], row[8]
        )
        assert all(
            value not in {"", "Pending", "N/A"}
            for value in (writer, focused, performance, review)
        )
        if status == "ACCEPTED":
            assert COMMIT_RE.fullmatch(commit)
        else:
            assert commit == "N/A — accepted no-op"

    if statuses[13] not in {"ACCEPTED", "ACCEPTED NO-OP"}:
        assert all(status == "NOT STARTED" for status in statuses[14:])
    return active


def _valid_old_id(kind: str, old_id: str) -> bool:
    if kind == "python":
        return old_id.startswith("tests/") and "::" in old_id
    if kind == "qml_quick":
        return re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]*::test_[A-Za-z0-9_]+", old_id
        ) is not None
    if kind == "shell_target":
        return re.fullmatch(
            r"(?:main_window|script_editor|run_controller|project_session)__[a-z0-9_]+",
            old_id,
        ) is not None
    return False


def _validate_migrations(
    rows: list[list[str]], task_status: dict[str, str]
) -> None:
    assert len({(row[2], row[3]) for row in rows}) == len(rows)
    for row in rows:
        assert len(row) == len(MIGRATION_HEADER)
        assert all(cell != "" for cell in row)
        (
            program,
            owning_task,
            kind,
            old_id,
            _behavior,
            production_owner,
            phase,
            disposition,
            replacement,
            equivalence,
            collecting,
            result,
            accepted,
        ) = row
        assert program in {"A", "B"}
        assert owning_task in task_status
        task_number = int(owning_task[1:])
        assert (program == "A" and 1 <= task_number <= 12) or (
            program == "B" and 14 <= task_number <= 25
        )
        assert kind in PHASES_BY_KIND
        assert _valid_old_id(kind, old_id)
        assert phase in PHASES_BY_KIND[kind]
        assert disposition in FINAL_DISPOSITIONS | {PENDING_DISPOSITION}

        na_columns = {index for index, value in enumerate(row) if value == "N/A"}
        legal_na: set[int] = set()
        if disposition == "deleted_obsolete_behavior":
            legal_na.update({5, 8})
        if disposition in {"retained", "retained_real_shell_lifecycle"}:
            legal_na.add(8)
        assert na_columns <= legal_na
        if production_owner == "N/A":
            assert disposition == "deleted_obsolete_behavior"

        owner_status = task_status[owning_task]
        if disposition == PENDING_DISPOSITION:
            assert owner_status in {"NOT STARTED", "IN PROGRESS"}
            continue

        assert equivalence not in {"Pending", "N/A"}
        assert collecting not in {"Pending", "N/A"}
        assert result not in {"Pending", "N/A"}
        assert accepted not in {"Pending", "N/A"}
        assert COMMIT_RE.fullmatch(collecting)
        assert COMMIT_RE.fullmatch(accepted)
        if disposition in {
            "moved_to_owner",
            "replaced_by_owner_test",
            "replaced_by_qml_quick",
            "redundant_existing_owner_proof",
        }:
            assert replacement not in {"Pending", "N/A"}

    if task_status["T13"] in {"ACCEPTED", "ACCEPTED NO-OP"}:
        assert all(row[7] != PENDING_DISPOSITION for row in rows if row[0] == "A")
    if task_status["T25"] in {"ACCEPTED", "ACCEPTED NO-OP"}:
        assert all(row[7] != PENDING_DISPOSITION for row in rows)


def _validate_status_sync(
    plan_text: str, ledger_text: str, task_rows: list[list[str]], active: list[int]
) -> None:
    status = _top_status(plan_text)
    assert status == _top_status(ledger_text)
    statuses = [row[2] for row in task_rows]
    if active:
        index = active[0]
        assert status == f"{statuses[index]} — T{index:02d}"
        return
    if statuses[-1] in {"ACCEPTED", "ACCEPTED NO-OP"}:
        assert status == "COMPLETED — T00–T26 ACCEPTED"
        return
    next_index = next(
        index for index, value in enumerate(statuses) if value == "NOT STARTED"
    )
    assert next_index > 0
    assert status == (
        f"CHECKPOINT — T{next_index - 1:02d} ACCEPTED; NEXT T{next_index:02d}"
    )


def _validate_documents(plan_text: str, ledger_text: str) -> None:
    task_header, task_rows = _table(ledger_text, "## Task Ledger")
    assert task_header[:3] == ["Task", "Program", "Status"]
    active = _validate_tasks(task_rows)
    migration_header, migration_rows = _table(ledger_text, "## Test Migration Ledger")
    assert tuple(migration_header) == MIGRATION_HEADER
    _validate_migrations(migration_rows, _task_statuses(task_rows))
    _validate_status_sync(plan_text, ledger_text, task_rows, active)


def test_plan_and_ledger_are_complete_and_synchronized() -> None:
    _validate_documents(
        PLAN.read_text(encoding="utf-8"),
        LEDGER.read_text(encoding="utf-8"),
    )


def test_clean_checkpoint_between_tasks_is_valid() -> None:
    plan_text = PLAN.read_text(encoding="utf-8")
    ledger_text = LEDGER.read_text(encoding="utf-8")
    active = "CHECKPOINT — T14 ACCEPTED; NEXT T15"
    assert _top_status(plan_text) == active
    assert _top_status(ledger_text) == active
    _validate_documents(plan_text, ledger_text)


def test_accepted_task_requires_complete_evidence() -> None:
    _, rows = _table(LEDGER.read_text(encoding="utf-8"), "## Task Ledger")
    rows[0][5] = "Pending"
    with pytest.raises(AssertionError):
        _validate_tasks(rows)


def test_plan_and_ledger_status_drift_is_rejected() -> None:
    with pytest.raises(AssertionError):
        _validate_documents(
            PLAN.read_text(encoding="utf-8").replace(
                "Status: `CHECKPOINT — T14 ACCEPTED; NEXT T15`",
                "Status: `CHECKPOINT — T13 ACCEPTED; NEXT T14`",
                1,
            ),
            LEDGER.read_text(encoding="utf-8"),
        )


def _pending_row() -> list[str]:
    return [
        "A",
        "T01",
        "python",
        "tests/test_example.py::test_case",
        "Behavior",
        "ea_node_editor.owner",
        "fast.pytest",
        PENDING_DISPOSITION,
        "Pending",
        "Pending",
        "Pending",
        "Pending",
        "Pending",
    ]


def _not_started_statuses() -> dict[str, str]:
    return {f"T{index:02d}": "NOT STARTED" for index in range(27)}


def test_migration_rejects_missing_required_fields() -> None:
    row = _pending_row()
    row[4] = ""
    with pytest.raises(AssertionError):
        _validate_migrations([row], _not_started_statuses())


@pytest.mark.parametrize(
    ("kind", "phase"),
    (("invalid", "fast.pytest"), ("python", "gui.qml_quick / qmltestrunner")),
)
def test_migration_rejects_invalid_kind_or_phase(kind: str, phase: str) -> None:
    row = _pending_row()
    row[2], row[6] = kind, phase
    with pytest.raises(AssertionError):
        _validate_migrations([row], _not_started_statuses())


def test_pending_migration_is_illegal_after_owner_acceptance() -> None:
    statuses = _not_started_statuses()
    statuses["T01"] = "ACCEPTED"
    with pytest.raises(AssertionError):
        _validate_migrations([_pending_row()], statuses)


@pytest.mark.parametrize("evidence_index", (10, 11, 12))
def test_final_migration_rejects_pending_evidence(evidence_index: int) -> None:
    row = _pending_row()
    row[7] = "moved_to_owner"
    row[8] = "tests/test_owner.py::test_case"
    row[9] = "Same assertions at direct owner"
    row[10] = row[12] = "This commit"
    row[11] = "PASS"
    row[evidence_index] = "Pending"
    with pytest.raises(AssertionError):
        _validate_migrations([row], _not_started_statuses())


def test_recovery_and_protected_baselines_remain_explicit() -> None:
    text = LEDGER.read_text(encoding="utf-8")
    anchors = (
        "1. `AGENTS.md`",
        "2. `docs/PLAN_COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR.md`",
        "3. this QA matrix",
        "4. `git status --short --branch`",
        "5. `git log -1 --oneline`",
        "6. the next `IN PROGRESS` or `NOT STARTED` task row below",
        "7. current active-agent state",
    )
    positions = [text.index(anchor) for anchor in anchors]
    assert positions == sorted(positions)
    for digest in (
        "43BFA388899097D924301BED29BBB57935512498237BCC7AF6EFDF9FF631D431",
        "F1709CD27CDD97141E354AB0644B3602F8EA43EBEFBB294B0C5FA4578C6788F2",
        "468C04C09DF327871ED6CD947EF58E8F26412D632A1E969C3C56303DFC44061B",
    ):
        assert digest in text
