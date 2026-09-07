# Purpose: Own lazy Workbench lifecycle imports behind the Mechanical owner process.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_owner_protocol.py

from __future__ import annotations

from typing import Any


def launch_workbench_owner(*, release_code: int, **options: Any) -> Any:
    """Import and launch Workbench only after the dedicated owner process starts."""

    from ansys.workbench.core import launch_workbench

    return launch_workbench(version=int(release_code), **options)


__all__ = ["launch_workbench_owner"]
