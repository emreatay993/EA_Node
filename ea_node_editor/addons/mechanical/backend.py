# Purpose: Execute the small allowlisted Mechanical owner lifecycle protocol.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_owner_protocol.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


LIFECYCLE_OPERATIONS = frozenset({"health", "close"})


def execute_lifecycle_operation(
    operation: str, args: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute lifecycle-only operations before T05 adds native model operations."""

    if operation not in LIFECYCLE_OPERATIONS:
        raise ValueError(f"Unsupported Mechanical owner operation: {operation!r}")
    if args:
        raise ValueError(
            f"Mechanical owner operation {operation!r} does not accept arguments"
        )
    return {"status": "ready" if operation == "health" else "closed"}


__all__ = ["LIFECYCLE_OPERATIONS", "execute_lifecycle_operation"]
