from __future__ import annotations

import sys

import pytest

from scripts import verification_manifest as manifest
from tests.shell_isolation_runtime import format_child_output
from tests.shell_isolation_runtime import list_target_ids
from tests.shell_isolation_runtime import load_target_registry
from tests.shell_isolation_runtime import resolve_target
from tests.shell_isolation_runtime import run_shell_isolation_target


def _target_params():
    target_ids = list_target_ids()
    if target_ids:
        return [pytest.param(target_id, id=target_id) for target_id in target_ids]
    return [
        pytest.param(
            "",
            id="no-targets",
            marks=pytest.mark.skip(reason="Shell isolation target catalogs are empty in P01."),
        )
    ]


def test_shell_isolation_target_catalogs_follow_manifest_owned_prefixes() -> None:
    registry = load_target_registry()

    assert registry
    allowed_prefixes = manifest.shell_isolation_target_id_prefixes()
    for target_id in registry:
        assert target_id.startswith(allowed_prefixes)


def test_shell_isolation_pytest_targets_use_manifest_owned_pytest_args() -> None:
    registry = load_target_registry()
    pytest_targets = [
        target
        for target in registry.values()
        if target.command[0] == sys.executable and target.command[1:3] == ("-m", "pytest")
    ]

    assert pytest_targets
    for target in pytest_targets:
        nodeids = target.command[4:-1]
        expected = (sys.executable, *manifest.shell_isolation_target_pytest_args(*nodeids))
        assert target.command == expected


@pytest.mark.parametrize(
    "target_id",
    _target_params(),
)
def test_shell_isolation_target(target_id: str) -> None:
    target = resolve_target(target_id)
    completed = run_shell_isolation_target(target)
    if completed.returncode == 0:
        return
    pytest.fail(
        "Shell isolation child process failed "
        f"for {target_id} (exit={completed.returncode}).\n"
        f"Command: {' '.join(target.command)}\n"
        f"{format_child_output(completed)}",
        pytrace=False,
    )
