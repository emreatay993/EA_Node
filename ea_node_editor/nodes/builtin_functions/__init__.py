# Purpose: Aggregate inert decorated built-in source without importing callables.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_builtin_function_infrastructure.py

from __future__ import annotations

from ea_node_editor.nodes.builtin_functions import (
    core_value,
    integrations_email,
    integrations_file_io,
    integrations_process,
    integrations_spreadsheet,
    integrations_ssh_sftp,
    plot_signal,
    spatial,
    unit_math,
)


def source_modules() -> tuple[tuple[str, str], ...]:
    """Return fixed bundle members; family writers only replace SOURCE strings."""

    return (
        ("core_value.py", core_value.SOURCE),
        ("unit_math.py", unit_math.SOURCE),
        ("spatial.py", spatial.SOURCE),
        ("plot_signal.py", plot_signal.SOURCE),
        ("integrations_file_io.py", integrations_file_io.SOURCE),
        ("integrations_process.py", integrations_process.SOURCE),
        ("integrations_email.py", integrations_email.SOURCE),
        ("integrations_spreadsheet.py", integrations_spreadsheet.SOURCE),
        ("integrations_ssh_sftp.py", integrations_ssh_sftp.SOURCE),
    )


__all__ = ["source_modules"]
