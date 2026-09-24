# Purpose: Structure automation handlers: Group backdrops, subnodes (create/ungroup/pins), scope navigation, selection, layout (align/distribute/match size, straighten wires).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_structure.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ea_node_editor.automation.errors import INVALID_PARAMS, AutomationOpError, no_effect
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.graph.records import EdgeInstance, NodeInstance
from ea_node_editor.graph.subnode_contract import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    is_subnode_pin_type,
    is_subnode_shell_type,
)
from ea_node_editor.ui.shell.automation.context import AutomationContext

ALIGNMENTS: dict[str, str] = {
    "align_left": "left",
    "align_right": "right",
    "align_top": "top",
    "align_bottom": "bottom",
    "align_center_x": "center_x",
    "align_center_y": "center_y",
}
DISTRIBUTIONS: dict[str, str] = {
    "distribute_horizontal": "horizontal",
    "distribute_vertical": "vertical",
}
MATCH_DIMENSIONS: dict[str, str] = {
    "match_width": "width",
    "match_height": "height",
}
# Snapping rounds the top-left corner, which would undo a center alignment, so center modes never snap.
CENTER_ALIGNMENTS = frozenset({"align_center_x", "align_center_y"})
# Straightness check on the drawn wire endpoints; live QML port centres may differ from the solver by sub-pixels.
STRAIGHT_TOLERANCE_PX = 1.0
_HORIZONTAL_SIDES = frozenset({"left", "right"})
_VERTICAL_SIDES = frozenset({"top", "bottom"})
_SIZE_EPSILON = 0.01
PIN_TYPE_BY_DIRECTION: dict[str, str] = {"in": SUBNODE_INPUT_TYPE_ID, "out": SUBNODE_OUTPUT_TYPE_ID}


# ----------------------------------------------------------------- helpers


def _unique_ids(values: Iterable[Any]) -> list[str]:
    ordered: list[str] = []
    for value in values or ():
        node_id = str(value or "").strip()
        if node_id and node_id not in ordered:
            ordered.append(node_id)
    return ordered


def _nodes_in_scope(context: AutomationContext, node_ids: Iterable[str]) -> list[NodeInstance]:
    return [context.require_node_in_scope(node_id) for node_id in node_ids]


def _require_shell(context: AutomationContext, node: NodeInstance, op: str) -> NodeInstance:
    if not is_subnode_shell_type(node.type_id):
        raise AutomationOpError(
            INVALID_PARAMS,
            f"{op}: node '{node.node_id}' is a {node.type_id}, not a subnode shell.",
            hint="Pass the shell_node_id returned by subnode.create (type core.subnode).",
            details={"node_id": node.node_id, "type_id": node.type_id, "op": op},
        )
    return node


def _apply_title(context: AutomationContext, op: str, node_id: str, title: Any) -> None:
    """Set a node title through the verified scene path; fall back to the persisted title property."""
    normalized = str(title if title is not None else "").strip()
    if not normalized:
        return
    scene = context.scene
    scene.set_node_title(node_id, normalized)
    node = context.require_node(node_id)
    if node.title == normalized:
        return
    scene.set_node_property(node_id, "title", normalized)
    node = context.require_node(node_id)
    if node.title != normalized and str(node.properties.get("title", "")) != normalized:
        raise no_effect(op, f"title '{normalized}' was not applied to node '{node_id}'", details={"node_id": node_id, "title": normalized})


def _children_of(context: AutomationContext, parent_node_id: str) -> list[NodeInstance]:
    workspace = context.active_workspace()
    return [node for node in workspace.nodes.values() if (node.parent_node_id or "") == parent_node_id]


def _pin_ids(children: Iterable[NodeInstance], pin_type_id: str) -> list[str]:
    return [node.node_id for node in children if str(node.type_id) == pin_type_id]


# ---------------------------------------------------------------- handlers


def wrap_group(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node_ids = _unique_ids(params["node_ids"])
    _nodes_in_scope(context, node_ids)
    before = context.node_id_set()
    group_id = str(context.scene.wrap_node_ids_in_group_backdrop(list(node_ids)) or "").strip()
    new_ids = context.new_ids_since(before)
    if not group_id and len(new_ids) == 1:
        group_id = new_ids[0]
    group = context.node_or_none(group_id) if group_id else None
    if group is None:
        raise no_effect(
            "group.wrap",
            "the scene did not create a Group backdrop",
            details={"node_ids": node_ids, "new_node_ids": new_ids, "scope_path": context.scope_path()},
        )
    _apply_title(context, "group.wrap", group_id, params.get("title"))
    group = context.require_node(group_id)
    return {"group_node_id": group_id, "member_node_ids": node_ids, "group": context.node_summary(group)}


def create_subnode(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node_ids = _unique_ids(params["node_ids"])
    _nodes_in_scope(context, node_ids)
    if len(node_ids) < 2:
        raise AutomationOpError(
            INVALID_PARAMS,
            "subnode.create needs at least two distinct nodes in the open scope.",
            details={"node_ids": node_ids, "problems": ["node_ids: must contain at least 2 distinct ids"]},
        )
    scope_parent = context.scope_parent_id()
    before = context.node_id_set()
    with context.with_selection(node_ids):
        selected = context.selected_node_ids()
        missing = [node_id for node_id in node_ids if node_id not in selected]
        if missing:
            raise no_effect("subnode.create", "the scene refused to select some nodes", details={"missing_node_ids": missing})
        grouped = bool(context.scene.group_selected_nodes())
    new_ids = context.new_ids_since(before)
    workspace = context.active_workspace()
    shells = [
        node_id
        for node_id in new_ids
        if is_subnode_shell_type(workspace.nodes[node_id].type_id)
        and (workspace.nodes[node_id].parent_node_id or None) == scope_parent
    ]
    if not grouped or len(shells) != 1:
        raise no_effect(
            "subnode.create",
            "the scene did not collapse the nodes into a subnode shell",
            details={"node_ids": node_ids, "new_node_ids": new_ids, "owner_result": grouped},
        )
    shell_id = shells[0]
    children = _children_of(context, shell_id)
    _apply_title(context, "subnode.create", shell_id, params.get("title"))
    shell = context.require_node(shell_id)
    return {
        "shell_node_id": shell_id,
        "input_pin_ids": _pin_ids(children, SUBNODE_INPUT_TYPE_ID),
        "output_pin_ids": _pin_ids(children, SUBNODE_OUTPUT_TYPE_ID),
        "member_node_ids": [node.node_id for node in children if not is_subnode_pin_type(node.type_id)],
        "shell": context.node_summary(shell),
    }


def ungroup_subnode(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    shell = _require_shell(context, context.require_node_in_scope(str(params["shell_node_id"])), "subnode.ungroup")
    shell_id = shell.node_id
    scope_parent = context.scope_parent_id()
    workspace = context.active_workspace()
    parents_before = {node_id: (node.parent_node_id or None) for node_id, node in workspace.nodes.items()}
    with context.with_selection([shell_id]):
        ungrouped = bool(context.scene.ungroup_selected_subnode())
    if not ungrouped or context.node_or_none(shell_id) is not None:
        raise no_effect(
            "subnode.ungroup",
            f"the scene did not dissolve shell '{shell_id}'",
            details={"shell_node_id": shell_id, "owner_result": ungrouped},
        )
    restored = [
        node_id
        for node_id, node in context.active_workspace().nodes.items()
        if node_id in parents_before
        and parents_before[node_id] != (node.parent_node_id or None)
        and (node.parent_node_id or None) == scope_parent
    ]
    return {"restored_node_ids": restored, "removed_shell_node_id": shell_id}


def add_subnode_pin(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    shell = _require_shell(context, context.require_node(str(params["shell_node_id"])), "subnode.add_pin")
    direction = str(params["direction"]).strip().lower()
    pin_type_id = PIN_TYPE_BY_DIRECTION[direction]
    pin_id = str(context.scene.add_subnode_shell_pin(shell.node_id, pin_type_id) or "").strip()
    pin = context.node_or_none(pin_id) if pin_id else None
    if pin is None or (pin.parent_node_id or "") != shell.node_id or str(pin.type_id) != pin_type_id:
        raise no_effect(
            "subnode.add_pin",
            f"the scene did not add a {direction} pin to shell '{shell.node_id}'",
            details={"shell_node_id": shell.node_id, "direction": direction, "pin_node_id": pin_id},
        )
    return {"pin_node_id": pin_id, "direction": direction, "pin": context.node_summary(pin)}


def navigate_scope(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    target = str(params["target"]).strip().lower()
    before = context.scope_path()
    scene = context.scene
    expected_leaf: str | None = None
    if target == "root":
        navigated = bool(scene.navigate_scope_root())
    elif target == "parent":
        navigated = bool(scene.navigate_scope_parent())
    else:
        node_id = str(params.get("node_id") or "").strip()
        if not node_id:
            raise AutomationOpError(
                INVALID_PARAMS,
                "scope.navigate: node_id is required when target=node.",
                details={"problems": ["params.node_id: is required when target=node"]},
            )
        shell = _require_shell(context, context.require_node(node_id), "scope.navigate")
        if not context.in_active_scope(shell):
            # Move to the scope that contains the shell first, then step inside it.
            scene.open_scope_for_node(shell.node_id)
        navigated = bool(scene.open_subnode_scope(shell.node_id))
        expected_leaf = shell.node_id
    after = context.scope_path()
    if not navigated or after == before or (expected_leaf is not None and (not after or after[-1] != expected_leaf)):
        location = "/".join(after) or "root"
        raise no_effect(
            "scope.navigate",
            f"the scope did not change (now at {location})",
            details={"target": target, "scope_path": after, "previous_scope_path": before},
        )
    return {"scope_path": after, "previous_scope_path": before}


def set_selection(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    mode = str(params.get("mode") or "replace").strip().lower()
    node_ids = _unique_ids(params.get("node_ids") or ())
    scene = context.scene
    if mode == "clear":
        scene.clear_selection()
        return {"selected_node_ids": context.selected_node_ids(), "mode": mode}
    if not node_ids:
        raise AutomationOpError(
            INVALID_PARAMS,
            f"selection.set: node_ids is required for mode={mode}.",
            details={"problems": ["params.node_ids: must contain at least 1 items"], "mode": mode},
        )
    _nodes_in_scope(context, node_ids)
    if mode == "replace":
        scene.clear_selection()
    already_selected = set(context.selected_node_ids())
    for node_id in node_ids:
        if node_id in already_selected:
            continue  # additive select_node toggles; keep it selected
        scene.select_node(node_id, True)
    selected = context.selected_node_ids()
    missing = [node_id for node_id in node_ids if node_id not in selected]
    if missing:
        raise no_effect("selection.set", "the scene refused to select some nodes", details={"missing_node_ids": missing, "mode": mode})
    return {"selected_node_ids": selected, "mode": mode}


def _position_map(context: AutomationContext, node_ids: Iterable[str]) -> dict[str, tuple[float, float]]:
    workspace = context.active_workspace()
    return {node_id: (float(workspace.nodes[node_id].x), float(workspace.nodes[node_id].y)) for node_id in node_ids}


def _size_map(context: AutomationContext, node_ids: Iterable[str]) -> dict[str, tuple[float, float] | None]:
    sizes: dict[str, tuple[float, float] | None] = {}
    for node_id in node_ids:
        bounds = context.node_bounds(node_id)
        sizes[node_id] = None if bounds is None else (bounds[2], bounds[3])
    return sizes


def _drawn_node_ids(context: AutomationContext) -> set[str]:
    """Nodes the canvas draws in the open scope; members of a collapsed Group backdrop are hidden and absent."""
    scene = context.scene
    drawn = {str(row.get("node_id", "")) for row in scene.nodes_model}
    drawn.update(str(row.get("node_id", "")) for row in scene.backdrop_nodes_model)
    return drawn


def _node_skip_reason(context: AutomationContext, node_id: str, drawn: set[str], selectable: set[str]) -> str:
    """Why a layout action left a node alone ('' when it was usable)."""
    if node_id not in drawn:
        return "hidden_in_collapsed_group"
    if node_id in selectable:
        return ""
    node = context.node_or_none(node_id)
    return "locked_node" if node is not None and node.locked else "not_selectable"


def _usable_node_ids(context: AutomationContext, node_ids: list[str]) -> tuple[list[str], list[dict[str, str]], set[str]]:
    """Split ``node_ids`` into the ones the scene lets the user act on and the skipped rest (with reasons).

    The scene's selection rules decide: locked nodes (unless the "interact with locked objects" preference is on)
    and nodes outside an open comment peek cannot be selected; hidden members of a collapsed Group are excluded
    here because moving them would pull them out of the group.
    """
    drawn = _drawn_node_ids(context)
    visible = [node_id for node_id in node_ids if node_id in drawn]
    with context.with_selection(visible):
        selected = set(context.selected_node_ids())
    usable = [node_id for node_id in visible if node_id in selected]
    usable_set = set(usable)
    skipped = [
        {"node_id": node_id, "reason": _node_skip_reason(context, node_id, drawn, usable_set)}
        for node_id in node_ids
        if node_id not in usable_set
    ]
    return usable, skipped, drawn


def _too_few_usable(action: str, node_ids: list[str], skipped: list[dict[str, str]]) -> AutomationOpError:
    return AutomationOpError(
        INVALID_PARAMS,
        f"layout.arrange {action}: fewer than two of the given nodes can be arranged.",
        hint=(
            "details.skipped_nodes says why each node was left out: unlock it with node_update(locked=false), "
            "expand its collapsed Group, or pass other nodes."
        ),
        details={
            "node_ids": node_ids,
            "skipped_nodes": skipped,
            "problems": ["node_ids: fewer than 2 nodes can be arranged"],
        },
    )


def _overlapping_node_pairs(context: AutomationContext, node_ids: Iterable[str]) -> list[list[str]]:
    """Pairs of the given nodes whose drawn bounds intersect; Group backdrops enclose members by design and are skipped."""
    rects: list[tuple[str, tuple[float, float, float, float]]] = []
    for node_id in node_ids:
        node = context.node_or_none(node_id)
        spec = context.registry.spec_or_none(node.type_id) if node is not None else None
        if spec is None or str(spec.surface_family or "").strip() == "group_backdrop":
            continue
        bounds = context.node_bounds(node_id)
        if bounds is None or bounds[2] <= 0.0 or bounds[3] <= 0.0:
            continue
        rects.append((node_id, bounds))
    pairs: list[list[str]] = []
    for index, (first_id, (ax, ay, aw, ah)) in enumerate(rects):
        for second_id, (bx, by, bw, bh) in rects[index + 1 :]:
            if ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by:
                pairs.append([first_id, second_id])
    return pairs


def _positions_payload(positions: Mapping[str, tuple[float, float]]) -> dict[str, dict[str, float]]:
    return {node_id: {"x": x, "y": y} for node_id, (x, y) in positions.items()}


def _match_size(context: AutomationContext, node_ids: list[str], action: str) -> dict[str, Any]:
    dimension = MATCH_DIMENSIONS[action]
    usable, skipped, drawn = _usable_node_ids(context, node_ids)
    buckets: dict[str, list[str]] = {}
    for node_id in usable:
        node = context.require_node(node_id)
        spec = context.spec_for(node)
        if str(spec.runtime_behavior or "").strip().lower() == "passive":
            buckets.setdefault(str(node.type_id), []).append(node_id)
    eligible = {type_id: ids for type_id, ids in buckets.items() if len(ids) >= 2}
    eligible_ids = {node_id for ids in eligible.values() for node_id in ids}
    ignored = [node_id for node_id in usable if node_id not in eligible_ids]
    if not eligible:
        raise AutomationOpError(
            INVALID_PARAMS,
            f"layout.arrange {action}: no two of the given nodes are passive nodes of the same type.",
            hint=(
                f"{action} resizes passive nodes of the same type_id to the first listed node of that type; "
                "use node_update(width=..., height=...) for other nodes."
            ),
            details={
                "node_ids": node_ids,
                "ignored_node_ids": ignored,
                "skipped_nodes": skipped,
                "problems": ["node_ids: needs two or more passive nodes with the same type_id"],
            },
        )
    sizes_before = _size_map(context, usable)
    # The UI passes the selection here; ``usable`` is exactly what the scene would let the user select.
    context.scene.set_selected_same_type_size(list(usable), dimension)
    sizes_after = _size_map(context, usable)
    resized = []
    for node_id in usable:
        before, after = sizes_before[node_id], sizes_after[node_id]
        if before is None or after is None:
            continue
        if abs(before[0] - after[0]) > _SIZE_EPSILON or abs(before[1] - after[1]) > _SIZE_EPSILON:
            resized.append(node_id)
    visible = [node_id for node_id in node_ids if node_id in drawn]
    return {
        "moved_node_ids": [],
        "resized_node_ids": resized,
        "action": action,
        "reference_node_ids": {type_id: ids[0] for type_id, ids in eligible.items()},
        "ignored_node_ids": ignored,
        "skipped_nodes": skipped,
        "sizes": {node_id: {"width": size[0], "height": size[1]} for node_id, size in sizes_after.items() if size is not None},
        "positions": _positions_payload(_position_map(context, node_ids)),
        "overlapping_node_pairs": _overlapping_node_pairs(context, visible),
    }


def arrange_layout(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node_ids = _unique_ids(params["node_ids"])
    action = str(params["action"]).strip().lower()
    snap_to_grid = bool(params.get("snap_to_grid", False)) and action not in CENTER_ALIGNMENTS
    _nodes_in_scope(context, node_ids)
    if len(node_ids) < 2:
        raise AutomationOpError(
            INVALID_PARAMS,
            "layout.arrange needs at least two distinct nodes.",
            details={"node_ids": node_ids, "problems": ["node_ids: must contain at least 2 distinct ids"]},
        )
    if action in MATCH_DIMENSIONS:
        return _match_size(context, node_ids, action)
    positions_before = _position_map(context, node_ids)
    usable, skipped, drawn = _usable_node_ids(context, node_ids)
    if len(usable) < 2:
        raise _too_few_usable(action, node_ids, skipped)
    scene = context.scene
    with context.with_selection(usable):
        if action in ALIGNMENTS:
            scene.align_selected_nodes(ALIGNMENTS[action], snap_to_grid=snap_to_grid)
        else:
            scene.distribute_selected_nodes(DISTRIBUTIONS[action], snap_to_grid=snap_to_grid)
    positions_after = _position_map(context, node_ids)
    moved = [node_id for node_id in node_ids if positions_after[node_id] != positions_before[node_id]]
    return {
        "moved_node_ids": moved,
        "resized_node_ids": [],
        "action": action,
        "skipped_nodes": skipped,
        "positions": _positions_payload(positions_after),
        "overlapping_node_pairs": _overlapping_node_pairs(context, [node_id for node_id in node_ids if node_id in drawn]),
    }


def _straighten_targets(context: AutomationContext, params: Mapping[str, Any]) -> tuple[list[str], list[EdgeInstance]]:
    """Resolve the node set (explicit ids, wire endpoints, or the whole open scope) and its candidate wires."""
    node_ids = _unique_ids(params.get("node_ids") or ())
    edge_ids = _unique_ids(params.get("edge_ids") or ())
    workspace = context.active_workspace()
    if not node_ids and not edge_ids:
        node_ids = [node.node_id for node in workspace.nodes.values() if context.in_active_scope(node)]
    else:
        _nodes_in_scope(context, node_ids)
        for edge_id in edge_ids:
            edge = context.require_edge(edge_id)
            for endpoint in (edge.source_node_id, edge.target_node_id):
                context.require_node_in_scope(endpoint)
                if endpoint not in node_ids:
                    node_ids.append(endpoint)
    node_set = set(node_ids)
    candidates = [
        edge
        for edge in workspace.edges.values()
        if edge.source_node_id in node_set
        and edge.target_node_id in node_set
        and edge.source_node_id != edge.target_node_id
    ]
    if not candidates:
        raise AutomationOpError(
            INVALID_PARAMS,
            "layout.straighten: no edge connects two of the given nodes.",
            hint="Pass node_ids that are wired to each other, or edge_ids of the wires to straighten.",
            details={"node_ids": node_ids, "problems": ["node_ids: no edge connects two of these nodes"]},
        )
    wired = {node_id for edge in candidates for node_id in (edge.source_node_id, edge.target_node_id)}
    return [node_id for node_id in node_ids if node_id in wired], candidates


def _wire_side(context: AutomationContext, row: Mapping[str, Any], edge: EdgeInstance, end: str) -> str:
    """Side a wire end leaves from: the drawn port side, else in->left / out->right (mirrors the owner's fallback)."""
    for key in (f"{end}_port_side", f"{end}_anchor_side"):
        side = str(row.get(key) or "").strip().lower()
        if side in _HORIZONTAL_SIDES or side in _VERTICAL_SIDES:
            return side
    node = context.node_or_none(edge.source_node_id if end == "source" else edge.target_node_id)
    if node is None or context.registry.spec_or_none(node.type_id) is None:
        return ""
    port = context.port_spec_or_none(node, edge.source_port_key if end == "source" else edge.target_port_key)
    direction = str(port.direction or "").strip().lower() if port is not None else ""
    return {"in": "left", "out": "right"}.get(direction, "")


def _classify_wires(
    context: AutomationContext,
    candidates: list[EdgeInstance],
    *,
    drawn: set[str],
    usable: set[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    rows = {str(row.get("edge_id", "")): row for row in context.scene.edges_model}
    straightened: list[str] = []
    skipped: list[dict[str, Any]] = []
    for edge in candidates:
        blocked = [node_id for node_id in (edge.source_node_id, edge.target_node_id) if node_id not in usable]
        if blocked:
            skipped.append(
                {
                    "edge_id": edge.edge_id,
                    "reason": _node_skip_reason(context, blocked[0], drawn, usable),
                    "node_id": blocked[0],
                }
            )
            continue
        row = rows.get(edge.edge_id)
        if row is None:
            skipped.append({"edge_id": edge.edge_id, "reason": "not_drawn"})
            continue
        source_side = _wire_side(context, row, edge, "source")
        target_side = _wire_side(context, row, edge, "target")
        if source_side in _HORIZONTAL_SIDES and target_side in _HORIZONTAL_SIDES:
            offset = abs(float(row.get("sy", 0.0)) - float(row.get("ty", 0.0)))
        elif source_side in _VERTICAL_SIDES and target_side in _VERTICAL_SIDES:
            offset = abs(float(row.get("sx", 0.0)) - float(row.get("tx", 0.0)))
        else:
            skipped.append(
                {"edge_id": edge.edge_id, "reason": "mixed_port_sides", "source_side": source_side, "target_side": target_side}
            )
            continue
        if offset <= STRAIGHT_TOLERANCE_PX:
            straightened.append(edge.edge_id)
            continue
        # Either the wires of this connected set need contradictory offsets, or a port is drawn away from the
        # anchor the solver aligns (ports inside settings groups / inline editors on some data nodes).
        skipped.append(
            {
                "edge_id": edge.edge_id,
                "reason": "unresolved_offset",
                "source_side": source_side,
                "target_side": target_side,
                "offset": round(offset, 3),
            }
        )
    return straightened, skipped


def straighten_layout(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    node_ids, candidates = _straighten_targets(context, params)
    positions_before = _position_map(context, node_ids)
    usable, _skipped_nodes, drawn = _usable_node_ids(context, node_ids)
    if len(usable) >= 2:
        with context.with_selection(usable):
            context.scene.straighten_selected_connections()
    positions_after = _position_map(context, node_ids)
    moved = [node_id for node_id in node_ids if positions_after[node_id] != positions_before[node_id]]
    straightened, skipped = _classify_wires(context, candidates, drawn=drawn, usable=set(usable))
    return {
        "moved_node_ids": moved,
        "straightened_edge_ids": straightened,
        "skipped_edges": skipped,
        "positions": _positions_payload({node_id: positions_after[node_id] for node_id in moved}),
        "overlapping_node_pairs": _overlapping_node_pairs(context, [node_id for node_id in node_ids if node_id in drawn]),
    }


HANDLERS = {
    'group.wrap': wrap_group,
    'subnode.create': create_subnode,
    'subnode.ungroup': ungroup_subnode,
    'subnode.add_pin': add_subnode_pin,
    'scope.navigate': navigate_scope,
    'selection.set': set_selection,
    'layout.arrange': arrange_layout,
    'layout.straighten': straighten_layout,
}

__all__ = [
    "ALIGNMENTS",
    "CENTER_ALIGNMENTS",
    "DISTRIBUTIONS",
    "HANDLERS",
    "MATCH_DIMENSIONS",
    "PIN_TYPE_BY_DIRECTION",
    "STRAIGHT_TOLERANCE_PX",
]
