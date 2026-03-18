from __future__ import annotations

import pytest

from tests.shell_isolation_runtime import format_child_output
from tests.shell_isolation_runtime import list_target_ids
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
