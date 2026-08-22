from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, coerce_runtime_snapshot


@dataclass(frozen=True, slots=True)
class WorkflowPythonEnvironment:
    configured: bool = False
    python_executable: str = ""
    valid: bool = True
    error: str = ""
    is_current_python: bool = False


def _path_key(path: Path) -> str:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    return os.path.normcase(str(resolved))


def _strip_wrapping_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1].strip()
    return text


def workflow_python_path_from_snapshot(value: RuntimeSnapshot | Mapping[str, Any] | None) -> str:
    runtime_snapshot = coerce_runtime_snapshot(value)
    metadata = runtime_snapshot.metadata if runtime_snapshot is not None else {}
    if not isinstance(metadata, Mapping):
        return ""
    workflow_settings = metadata.get("workflow_settings")
    if not isinstance(workflow_settings, Mapping):
        return ""
    environment = workflow_settings.get("environment")
    if not isinstance(environment, Mapping):
        return ""
    return _strip_wrapping_quotes(str(environment.get("python_path", "") or ""))


def resolve_workflow_python_environment(
    value: RuntimeSnapshot | Mapping[str, Any] | None,
    *,
    current_executable: str | Path | None = None,
) -> WorkflowPythonEnvironment:
    raw_python_path = workflow_python_path_from_snapshot(value)
    if not raw_python_path:
        return WorkflowPythonEnvironment()

    candidate = Path(raw_python_path).expanduser()
    try:
        normalized_candidate = candidate.resolve()
    except OSError:
        normalized_candidate = candidate

    if not normalized_candidate.exists():
        return WorkflowPythonEnvironment(
            configured=True,
            python_executable=str(normalized_candidate),
            valid=False,
            error=f"Workflow Python executable does not exist: {normalized_candidate}",
        )
    if not normalized_candidate.is_file():
        return WorkflowPythonEnvironment(
            configured=True,
            python_executable=str(normalized_candidate),
            valid=False,
            error=f"Workflow Python executable is not a file: {normalized_candidate}",
        )
    if not os.access(normalized_candidate, os.X_OK):
        return WorkflowPythonEnvironment(
            configured=True,
            python_executable=str(normalized_candidate),
            valid=False,
            error=f"Workflow Python executable is not executable: {normalized_candidate}",
        )

    current = Path(current_executable or sys.executable)
    return WorkflowPythonEnvironment(
        configured=True,
        python_executable=str(normalized_candidate),
        valid=True,
        is_current_python=_path_key(normalized_candidate) == _path_key(current),
    )


__all__ = [
    "WorkflowPythonEnvironment",
    "resolve_workflow_python_environment",
    "workflow_python_path_from_snapshot",
]
