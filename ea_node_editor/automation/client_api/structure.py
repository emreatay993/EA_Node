# Purpose: CorexClient facade for group.wrap, subnode.*, scope.navigate, selection.set, layout.arrange/straighten/tidy plus navigation/selection/layout sugar.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


def _id_list(values: Iterable[str] | str) -> list[str]:
    if isinstance(values, str):
        return [values]
    return [str(value) for value in values]


class StructureApi:
    """Facade for group.wrap, subnode.*, scope.navigate, selection.set, layout.arrange, layout.straighten, layout.tidy."""

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    # -------------------------------------------------------------- group.wrap

    def wrap_group(self, node_ids: Iterable[str] | str, *, title: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"node_ids": _id_list(node_ids)}
        if title is not None:
            params["title"] = str(title)
        return self._client.call("group.wrap", params)

    # --------------------------------------------------------------- subnode.*

    def create_subnode(self, node_ids: Iterable[str] | str, *, title: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"node_ids": _id_list(node_ids)}
        if title is not None:
            params["title"] = str(title)
        return self._client.call("subnode.create", params)

    def ungroup_subnode(self, shell_node_id: str) -> dict[str, Any]:
        return self._client.call("subnode.ungroup", {"shell_node_id": str(shell_node_id)})

    def add_subnode_pin(self, shell_node_id: str, direction: str) -> dict[str, Any]:
        return self._client.call("subnode.add_pin", {"shell_node_id": str(shell_node_id), "direction": str(direction)})

    def add_input_pin(self, shell_node_id: str) -> dict[str, Any]:
        return self.add_subnode_pin(shell_node_id, "in")

    def add_output_pin(self, shell_node_id: str) -> dict[str, Any]:
        return self.add_subnode_pin(shell_node_id, "out")

    # ---------------------------------------------------------- scope.navigate

    def navigate_scope(self, target: str, *, node_id: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"target": str(target)}
        if node_id is not None:
            params["node_id"] = str(node_id)
        return self._client.call("scope.navigate", params)

    def open_subnode(self, shell_node_id: str) -> dict[str, Any]:
        return self.navigate_scope("node", node_id=shell_node_id)

    def navigate_parent(self) -> dict[str, Any]:
        return self.navigate_scope("parent")

    def navigate_root(self) -> dict[str, Any]:
        return self.navigate_scope("root")

    # ----------------------------------------------------------- selection.set

    def set_selection(self, node_ids: Iterable[str] | str | None = None, *, mode: str = "replace") -> dict[str, Any]:
        params: dict[str, Any] = {"mode": str(mode)}
        if node_ids is not None:
            params["node_ids"] = _id_list(node_ids)
        return self._client.call("selection.set", params)

    def select(self, node_ids: Iterable[str] | str) -> dict[str, Any]:
        return self.set_selection(node_ids, mode="replace")

    def add_to_selection(self, node_ids: Iterable[str] | str) -> dict[str, Any]:
        return self.set_selection(node_ids, mode="add")

    def clear_selection(self) -> dict[str, Any]:
        return self.set_selection(None, mode="clear")

    # ---------------------------------------------------------- layout.arrange

    def arrange(self, node_ids: Iterable[str] | str, action: str, *, snap_to_grid: bool = False) -> dict[str, Any]:
        return self._client.call(
            "layout.arrange",
            {"node_ids": _id_list(node_ids), "action": str(action), "snap_to_grid": bool(snap_to_grid)},
        )

    def align(self, node_ids: Iterable[str] | str, side: str, *, snap_to_grid: bool = False) -> dict[str, Any]:
        """``side`` is left|right|top|bottom|center_x|center_y (center_y = a row whose side ports line up)."""
        return self.arrange(node_ids, f"align_{str(side).strip().lower()}", snap_to_grid=snap_to_grid)

    def distribute(self, node_ids: Iterable[str] | str, orientation: str, *, snap_to_grid: bool = False) -> dict[str, Any]:
        """``orientation`` is horizontal|vertical."""
        return self.arrange(node_ids, f"distribute_{str(orientation).strip().lower()}", snap_to_grid=snap_to_grid)

    def match_size(self, node_ids: Iterable[str] | str, dimension: str) -> dict[str, Any]:
        """``dimension`` is width|height; passive nodes of one type take the first listed node's size."""
        return self._client.call(
            "layout.arrange",
            {"node_ids": _id_list(node_ids), "action": f"match_{str(dimension).strip().lower()}"},
        )

    # -------------------------------------------------------- layout.straighten

    def straighten(
        self,
        node_ids: Iterable[str] | str | None = None,
        *,
        edge_ids: Iterable[str] | str | None = None,
    ) -> dict[str, Any]:
        """Move nodes so their wires run straight; no ids = every wire in the open scope."""
        params: dict[str, Any] = {}
        if node_ids is not None:
            params["node_ids"] = _id_list(node_ids)
        if edge_ids is not None:
            params["edge_ids"] = _id_list(edge_ids)
        return self._client.call("layout.straighten", params)

    # -------------------------------------------------------------- layout.tidy

    def tidy(
        self,
        node_ids: Iterable[str] | str | None = None,
        *,
        mode: str = "auto_layout",
        direction: str = "auto",
        column_gap: float | None = None,
        row_gap: float | None = None,
    ) -> dict[str, Any]:
        """Lay nodes out from their wires (``mode="in_place"`` keeps the arrangement); no ids = the whole open scope.

        ``direction`` is auto|left_to_right|top_to_bottom; omitted gaps use the op defaults.
        """
        params: dict[str, Any] = {"mode": str(mode), "direction": str(direction)}
        if node_ids is not None:
            params["node_ids"] = _id_list(node_ids)
        if column_gap is not None:
            params["column_gap"] = float(column_gap)
        if row_gap is not None:
            params["row_gap"] = float(row_gap)
        return self._client.call("layout.tidy", params)


__all__ = ["StructureApi"]
