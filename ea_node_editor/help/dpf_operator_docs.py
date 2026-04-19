"""Compatibility exports for the extracted DPF operator docs lookup."""

from __future__ import annotations

from ea_node_editor.addons.ansys_dpf.operator_docs import (
    docs_root,
    is_dpf_operator_type_id,
    markdown_for_node,
    markdown_for_type_id,
    markdown_path_for_type_id,
)

__all__ = [
    "docs_root",
    "is_dpf_operator_type_id",
    "markdown_for_node",
    "markdown_for_type_id",
    "markdown_path_for_type_id",
]
