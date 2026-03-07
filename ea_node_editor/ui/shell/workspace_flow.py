from __future__ import annotations

from typing import Any, Iterable


def next_workspace_tab_index(count: int, current_index: int, offset: int) -> int | None:
    if count <= 0:
        return None
    if current_index < 0:
        current_index = 0
    return (current_index + offset) % count


def build_workspace_tab_items(workspace_refs: Iterable[Any]) -> list[dict[str, str]]:
    tabs: list[dict[str, str]] = []
    for workspace_ref in workspace_refs:
        workspace_id = str(getattr(workspace_ref, "workspace_id", "")).strip()
        if not workspace_id:
            continue
        name = str(getattr(workspace_ref, "name", "")).strip() or "Workspace"
        dirty = bool(getattr(workspace_ref, "dirty", False))
        tabs.append(
            {
                "workspace_id": workspace_id,
                "label": f"{name}{' *' if dirty else ''}",
            }
        )
    return tabs
