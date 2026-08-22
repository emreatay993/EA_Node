from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ea_node_editor.execution.dpf_runtime.contracts import DpfRuntimeUnavailableError


def load_pyvista_module(import_module: Callable[[str], Any]) -> Any:
    try:
        return import_module("pyvista")
    except ModuleNotFoundError as exc:
        raise DpfRuntimeUnavailableError(
            "pyvista is not available; DPF materialization exports remain optional until used."
        ) from exc


def load_dpf_module(import_module: Callable[[str], Any]) -> Any:
    try:
        return import_module("ansys.dpf.core")
    except ModuleNotFoundError as exc:
        raise DpfRuntimeUnavailableError(
            "ansys.dpf.core is not available; DPF runtime features remain optional until used."
        ) from exc


__all__ = [
    "load_dpf_module",
    "load_pyvista_module",
]
