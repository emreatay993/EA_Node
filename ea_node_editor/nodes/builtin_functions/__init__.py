# Purpose: Aggregate inert decorated built-in source without importing callables.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_builtin_function_infrastructure.py

from __future__ import annotations

from ea_node_editor.nodes.builtin_functions import core_value, spatial, unit_math


def source_modules() -> tuple[tuple[str, str], ...]:
    """Return fixed bundle members; family writers only replace SOURCE strings."""

    return (
        ("core_value.py", core_value.SOURCE),
        ("unit_math.py", unit_math.SOURCE),
        ("spatial.py", spatial.SOURCE),
    )


__all__ = ["source_modules"]
