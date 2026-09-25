# Purpose: Scene Group commands: wrap nodes in a Group, grow Groups around stray held members before an expand, fill in the member lists of older collapsed Groups, and hold nodes added while peeking.
# Map: feature_routes/group_backdrops_peek_membership
# Tests: tests/test_group_backdrop_identity_membership.py, tests/test_group_backdrop_interactions.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ea_node_editor.graph.group_backdrop_geometry import lists_to_clear, lists_to_freeze
from ea_node_editor.graph.group_backdrop_mutation_ops import wrap_selection_in_group_backdrop
from ea_node_editor.graph.transform_layout_ops import LayoutNodeBounds
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.ui.shell.runtime_history import ACTION_WRAP_GROUP
from ea_node_editor.ui_qml.graph_scene_mutation.group_scope import (
    GroupScope,
    collect_group_scope_for_node,
    group_membership_for_scope,
    grow_group_around,
    is_group_backdrop_spec,
    scene_layout_bounds,
)


@dataclass(frozen=True, slots=True)
class GroupStrayGrowth:
    grown_rect: LayoutNodeBounds | None
    geometries: dict[str, tuple[float, float, float, float]] = field(default_factory=dict)


def wrap_nodes_in_group_backdrop(self, node_ids: list[Any]) -> str:
    model = self._scene_context.model
    if model is None:
        return ""
    registry = self._scene_context.registry
    if registry is None:
        return ""
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return ""
    # Fit the Group to the nodes as drawn, or it may not contain the ones whose drawn size the adapters miss.
    drawn = scene_layout_bounds(
        self,
        workspace,
        [
            workspace.nodes[node_id]
            for node_id in dict.fromkeys(str(value).strip() for value in node_ids)
            if node_id in workspace.nodes
        ],
    )

    wrapped = None
    held_in_peek = False
    history_group = self._scene_context.grouped_history_action(
        ACTION_WRAP_GROUP,
        workspace,
        commit_if=lambda: wrapped is not None,
    )
    with history_group:
        wrapped = self._run_graph_operation(
            "wrap_selection_in_group_backdrop",
            lambda: wrap_selection_in_group_backdrop(
                model=model,
                registry=registry,
                workspace_id=workspace.workspace_id,
                selected_node_ids=node_ids,
                scope_path=self._scene_context.scope_path,
                boundary_adapters=self._boundary_adapters,
                node_sizes={node_id: (rect.width, rect.height) for node_id, rect in drawn.items()},
            ),
        )
        if wrapped is not None:
            held_in_peek = hold_new_nodes_in_peeked_group(self, workspace, [wrapped.backdrop_node_id])
    if wrapped is None:
        return ""

    self._scope_selection.set_selected_node_ids([wrapped.backdrop_node_id], workspace=workspace)
    if held_in_peek:
        # It joined the peeked Group: Peek draws (and so selects) it only once a full rebuild lists it.
        self._scene_context.rebuild_models()
        self._scope_selection.set_selected_node_ids([wrapped.backdrop_node_id], workspace=workspace)
    elif not self._scene_context.publish_node_addition_delta(
        wrapped.backdrop_node_id,
        publication_path="group_backdrop_addition_delta",
    ):
        self._scene_context.rebuild_models()
    return wrapped.backdrop_node_id


def wrap_selected_nodes_in_group_backdrop(self) -> bool:
    model = self._scene_context.model
    if model is None:
        return False
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return False
    selected_node_ids = self._selected_node_ids_in_workspace(workspace)
    if not selected_node_ids:
        return False
    return bool(self.wrap_nodes_in_group_backdrop(selected_node_ids))


def group_stray_growth(
    self,
    workspace: WorkspaceData,
    group_id: str,
    *,
    scope: GroupScope | None = None,
) -> GroupStrayGrowth:
    """Before ``group_id`` expands: grow every Group whose list the expand clears around its held members outside it.

    Innermost first, so an outer Group sees the grown inner ones. ``grown_rect`` is the expanding Group's final
    expanded rectangle (the make-room cascade starts from it); ``geometries`` holds each grown Group (x/y move when a
    stray lies left or above).
    """
    scope = scope or collect_group_scope_for_node(self, workspace, group_id, dict(workspace.nodes))
    expanded = scope.expanded_rects.get(group_id, scope.rects.get(group_id))
    if expanded is None:
        return GroupStrayGrowth(grown_rect=None)
    work_rects = dict(scope.rects)
    work_rects[group_id] = expanded
    geometries: dict[str, tuple[float, float, float, float]] = {}
    cleared = lists_to_clear(workspace.nodes, group_id)
    for cleared_id in sorted(cleared, key=lambda item: (-_depth(scope, item), item)):
        base = work_rects.get(cleared_id)
        if base is None:
            continue
        grown = grow_group_around(scope, work_rects, cleared_id, scope.direct_members(cleared_id), base_rect=base)
        if grown is None:
            continue
        work_rects[cleared_id] = grown
        geometries[cleared_id] = (grown.x, grown.y, grown.width, grown.height)
    return GroupStrayGrowth(grown_rect=work_rects[group_id], geometries=geometries)


def fill_missing_held_member_ids(
    self,
    workspace: WorkspaceData,
    node_ids: Iterable[str] | None = None,
) -> set[str]:
    """Give collapsed Groups from older files or fragments the list today's area rule implies (not an edit).

    With ``node_ids`` (a paste) only those Groups are filled and every list keeps only ``node_ids`` (no bystanders).
    Written with no history entry and no dirty flag; returns the Groups that got a list.
    """
    registry = self._scene_context.registry
    if registry is None:
        return set()
    allowed = None if node_ids is None else {str(node_id) for node_id in node_ids}
    targets_by_parent: dict[str | None, list[str]] = {}
    for node_id, node in workspace.nodes.items():
        if not node.collapsed or node.held_member_ids is not None:
            continue
        if allowed is not None and node_id not in allowed:
            continue
        spec = registry.spec_or_none(node.type_id)
        if spec is None or not is_group_backdrop_spec(spec):
            continue
        targets_by_parent.setdefault(node.parent_node_id, []).append(node_id)
    if not targets_by_parent:
        return set()
    workspace_nodes = dict(workspace.nodes)
    lists: dict[str, tuple[str, ...]] = {}
    for target_ids in targets_by_parent.values():
        # Targets have no list yet, so they are measured expanded and claim by area: today's rule, once.
        membership, _group_ids = group_membership_for_scope(
            self,
            workspace,
            target_ids[0],
            workspace_nodes=workspace_nodes,
        )
        for target_id in sorted(target_ids):
            for group_id, member_ids in lists_to_freeze(target_id, membership, workspace.nodes).items():
                if allowed is not None:
                    if group_id not in allowed:
                        continue  # a Group that was not pasted keeps its state
                    member_ids = tuple(member_id for member_id in member_ids if member_id in allowed)
                lists.setdefault(group_id, member_ids)
    if lists:
        self._record_mutations().adopt_held_member_ids(lists)
    return set(lists)


def hold_new_nodes_in_peeked_group(self, workspace: WorkspaceData, new_node_ids: Iterable[str]) -> bool:
    """Nodes added while peeking into a collapsed Group join it (and every Group whose list holds it).

    Otherwise they would vanish when Peek closes. A new Group among them gets its own list (its contents).
    """
    peek_id = str(self._scope_selection.comment_peek_node_id or "").strip()
    peeked = workspace.nodes.get(peek_id) if peek_id else None
    if peeked is None or not peeked.collapsed or peeked.held_member_ids is None:
        return False
    added = [
        node_id
        for node_id in dict.fromkeys(str(value) for value in new_node_ids)
        if node_id != peek_id
        and node_id in workspace.nodes
        and workspace.nodes[node_id].parent_node_id == peeked.parent_node_id
    ]
    if not added:
        return False
    mutations = self._record_mutations()
    holder_ids = [peek_id] + sorted(
        node_id
        for node_id, node in workspace.nodes.items()
        if node.held_member_ids is not None and peek_id in node.held_member_ids
    )
    for holder_id in holder_ids:
        mutations.set_node_held_member_ids(holder_id, (*workspace.nodes[holder_id].held_member_ids, *added))
    registry = self._scene_context.registry
    new_group_ids = [
        node_id
        for node_id in added
        if workspace.nodes[node_id].held_member_ids is None
        and registry is not None
        and (spec := registry.spec_or_none(workspace.nodes[node_id].type_id)) is not None
        and is_group_backdrop_spec(spec)
    ]
    if new_group_ids:
        membership, _group_ids = group_membership_for_scope(
            self,
            workspace,
            peek_id,
            workspace_nodes=dict(workspace.nodes),
        )
        for group_id in new_group_ids:
            group_membership = membership.get(group_id)
            mutations.set_node_held_member_ids(
                group_id,
                ()
                if group_membership is None
                else (*group_membership.contained_node_ids, *group_membership.contained_backdrop_ids),
            )
    return True


def _depth(scope: GroupScope, node_id: str) -> int:
    membership = scope.membership.get(node_id)
    return 0 if membership is None else int(membership.backdrop_depth)


__all__ = [
    "GroupStrayGrowth",
    "fill_missing_held_member_ids",
    "group_stray_growth",
    "hold_new_nodes_in_peeked_group",
    "wrap_nodes_in_group_backdrop",
    "wrap_selected_nodes_in_group_backdrop",
]
