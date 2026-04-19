"""Compatibility exports for the extracted DPF operator catalog."""

from __future__ import annotations

from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    _discovered_generated_operator_definitions,
    load_ansys_dpf_operator_plugin_descriptors,
)

__all__ = [
    "_discovered_generated_operator_definitions",
    "load_ansys_dpf_operator_plugin_descriptors",
]
