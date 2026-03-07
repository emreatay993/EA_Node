from __future__ import annotations

from typing import Any


def input_port_is_available(workspace, node_id: str, port_key: str) -> bool:
    for edge in workspace.edges.values():
        if edge.target_node_id == node_id and edge.target_port_key == port_key:
            return False
    return True


def pick_connection_candidate(
    *,
    parent,
    title: str,
    label: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    from PyQt6.QtWidgets import QInputDialog

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    options = [str(candidate.get("label", "")).strip() or f"Option {index + 1}" for index, candidate in enumerate(candidates)]
    selected, ok = QInputDialog.getItem(parent, title, label, options, 0, False)
    if not ok:
        return None
    selected_text = str(selected).strip()
    for index, option in enumerate(options):
        if option == selected_text:
            return candidates[index]
    return None
