# Purpose: Annotation automation handlers: node comments and links (T07) through the GraphSceneBridge owners with check-before/verify-after.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_annotations.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import invalid_params, no_effect, not_found
from ea_node_editor.graph.records import NodeCommentRecord, NodeInstance, NodeLinkRecord
from ea_node_editor.ui.shell.automation.context import AutomationContext

DEFAULT_COMMENT_AUTHOR = "automation"

# Owner facts (ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py):
# - upsert_node_comment(node_id, comment_id, body, author, parent_id, resolved, unread, pinned) -> str
#   generates the id when comment_id is blank, returns "" when the node is missing or the body
#   normalizes to empty, and on an *existing* comment keeps the stored author (when the passed
#   author is blank), parent_id, resolved, unread and pinned; flags change only through
#   set_node_comment_resolved / set_node_comment_pinned.
# - remove_node_comment cascades to replies; remove/move return False when nothing changed.
# - upsert_node_link(node_id, link_id, kind, title, target, subtitle, target_workspace_id,
#   target_node_id) -> str appends new ids at the end; move_node_link(node_id, link_id, offset)
#   clamps to the list bounds and returns False for a zero move.
# Each owner call records its own history entry, which dispatch folds into one grouped step.


def _text(value: Any) -> str:
    return str(value or "").strip()


def _comment_or_none(node: NodeInstance, comment_id: str) -> NodeCommentRecord | None:
    for record in node.comments:
        if record.comment_id == comment_id:
            return record
    return None


def _link_index(node: NodeInstance, link_id: str) -> int:
    for index, record in enumerate(node.links):
        if record.link_id == link_id:
            return index
    return -1


def _serialize_comment(record: NodeCommentRecord) -> dict[str, Any]:
    return {
        "comment_id": record.comment_id,
        "body": record.body,
        "author": record.author,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "resolved": bool(record.resolved),
        "unread": bool(record.unread),
        "pinned": bool(record.pinned),
        "parent_id": record.parent_id or "",
    }


def _serialize_link(record: NodeLinkRecord, position: int) -> dict[str, Any]:
    return {
        "link_id": record.link_id,
        "kind": record.kind,
        "title": record.title,
        "target": record.target,
        "subtitle": record.subtitle or "",
        "target_workspace_id": record.target_workspace_id or "",
        "target_node_id": record.target_node_id or "",
        "position": int(position),
    }


# -------------------------------------------------------------------- comments


def upsert_comment(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
    op = "comment.upsert"
    node = context.require_node(_text(params.get("node_id")))
    body = _text(params.get("body"))
    if not body:
        raise invalid_params(["params.body: must not be blank"], op=op)
    comment_id = _text(params.get("comment_id"))
    existing = _comment_or_none(node, comment_id) if comment_id else None
    if comment_id and existing is None:
        raise not_found("Comment", comment_id, hint="Call graph.get_node to list the node's comments, or omit comment_id to create one.")

    parent_id = _text(params.get("parent_id"))
    if parent_id:
        if parent_id == comment_id:
            raise invalid_params(["params.parent_id: a comment cannot be its own parent"], op=op)
        if _comment_or_none(node, parent_id) is None:
            raise invalid_params([f"params.parent_id: comment '{parent_id}' does not exist on node '{node.node_id}'"], op=op)
        if existing is not None and existing.parent_id != parent_id:
            raise invalid_params(["params.parent_id: cannot change the parent of an existing comment"], op=op)

    resolved_param = params.get("resolved")
    pinned_param = params.get("pinned")
    if existing is None:
        author = _text(params.get("author")) or DEFAULT_COMMENT_AUTHOR
        resolved = bool(resolved_param) if resolved_param is not None else False
        pinned = bool(pinned_param) if pinned_param is not None else False
    else:
        author = _text(params.get("author"))  # blank keeps the stored author (owner rule)
        resolved = bool(resolved_param) if resolved_param is not None else bool(existing.resolved)
        pinned = bool(pinned_param) if pinned_param is not None else bool(existing.pinned)
    expected_author = author or (existing.author if existing is not None else DEFAULT_COMMENT_AUTHOR)

    # Automation-authored comments are never "unread" for the author; edits keep the stored flag.
    stored_id = context.scene.upsert_node_comment(node.node_id, comment_id, body, author, parent_id, resolved, False, pinned)
    if not stored_id:
        raise no_effect(op, "the scene rejected the comment", details={"node_id": node.node_id, "comment_id": comment_id})
    if existing is not None:
        if bool(existing.resolved) != resolved:
            context.scene.set_node_comment_resolved(node.node_id, stored_id, resolved)
        if bool(existing.pinned) != pinned:
            context.scene.set_node_comment_pinned(node.node_id, stored_id, pinned)

    record = _comment_or_none(context.require_node(node.node_id), stored_id)
    if record is None or record.body != body or bool(record.resolved) != resolved or bool(record.pinned) != pinned or record.author != expected_author:
        raise no_effect(
            op,
            "the stored comment does not match the request",
            details={"node_id": node.node_id, "comment_id": stored_id, "stored": _serialize_comment(record) if record is not None else None},
        )
    return {"comment_id": stored_id, "comment": _serialize_comment(record)}


def remove_comment(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
    op = "comment.remove"
    node = context.require_node(_text(params.get("node_id")))
    comment_id = _text(params.get("comment_id"))
    if _comment_or_none(node, comment_id) is None:
        raise not_found("Comment", comment_id, hint="Call graph.get_node to list the node's comments.")
    before_ids = [record.comment_id for record in node.comments]
    removed = context.scene.remove_node_comment(node.node_id, comment_id)
    if not removed:
        raise no_effect(op, "the scene did not remove the comment", details={"node_id": node.node_id, "comment_id": comment_id})
    remaining = {record.comment_id for record in context.require_node(node.node_id).comments}
    if comment_id in remaining:
        raise no_effect(op, "the comment is still present after removal", details={"node_id": node.node_id, "comment_id": comment_id})
    removed_ids = [candidate for candidate in before_ids if candidate not in remaining]
    return {"removed": True, "removed_comment_ids": removed_ids}


# ----------------------------------------------------------------------- links


def _resolve_link_target(context: AutomationContext, op: str, params: Mapping[str, Any]) -> tuple[str, str, str]:
    """Return ``(target, target_workspace_id, target_node_id)`` after the per-kind existence checks."""
    kind = _text(params.get("kind"))
    target = _text(params.get("target"))
    target_workspace_id = _text(params.get("target_workspace_id"))
    target_node_id = _text(params.get("target_node_id"))
    workspaces = context.model.project.workspaces
    if kind == "url":
        if not target:
            raise invalid_params(["params.target: a non-empty URL is required for kind=url"], op=op)
        return target, "", ""
    if kind in ("file", "folder"):
        if not target:
            raise invalid_params([f"params.target: a non-empty path is required for kind={kind}"], op=op)
        return target, "", ""
    if kind == "workspace":
        workspace_id = target or target_workspace_id
        if not workspace_id:
            raise invalid_params(["params.target: a workspace id is required for kind=workspace"], op=op)
        if workspace_id not in workspaces:
            raise not_found("Workspace", workspace_id, hint="Call workspace.list to get valid workspace ids.")
        return workspace_id, "", ""
    if kind == "node":
        node_ref = target_node_id or target
        if not node_ref:
            raise invalid_params(["params.target_node_id: a node id is required for kind=node"], op=op)
        workspace_id = target_workspace_id or context.workspace_id()
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            raise not_found("Workspace", workspace_id, hint="Call workspace.list to get valid workspace ids.")
        if node_ref not in workspace.nodes:
            raise not_found(
                "Node",
                node_ref,
                hint=f"Node '{node_ref}' is not in workspace '{workspace_id}'; check target_workspace_id or refresh ids with graph.get.",
            )
        return node_ref, workspace_id, node_ref
    raise invalid_params([f"params.kind: unsupported link kind '{kind}'"], op=op)


def upsert_link(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
    op = "link.upsert"
    node = context.require_node(_text(params.get("node_id")))
    kind = _text(params.get("kind"))
    title = _text(params.get("title"))
    if not title:
        raise invalid_params(["params.title: must not be blank"], op=op)
    link_id = _text(params.get("link_id"))
    if link_id and _link_index(node, link_id) < 0:
        raise not_found("Link", link_id, hint="Call graph.get_node to list the node's links, or omit link_id to create one.")
    target, target_workspace_id, target_node_id = _resolve_link_target(context, op, params)
    subtitle = _text(params.get("subtitle"))
    position = params.get("position")
    wanted: int | None = None
    if position is not None:
        # Validated before the upsert so a bad position never leaves a half-applied link behind.
        if isinstance(position, bool) or not isinstance(position, int) or position < 0:
            raise invalid_params([f"params.position: must be a non-negative integer, got {position!r}"], op=op)
        final_count = len(node.links) + (0 if link_id else 1)
        wanted = min(position, final_count - 1)

    stored_id = context.scene.upsert_node_link(node.node_id, link_id, kind, title, target, subtitle, target_workspace_id, target_node_id)
    if not stored_id:
        raise no_effect(op, "the scene rejected the link", details={"node_id": node.node_id, "link_id": link_id, "kind": kind})
    node = context.require_node(node.node_id)
    index = _link_index(node, stored_id)
    if index < 0:
        raise no_effect(op, "the link is missing after upsert", details={"node_id": node.node_id, "link_id": stored_id})

    if wanted is not None:
        offset = wanted - index
        if offset != 0:
            moved = context.scene.move_node_link(node.node_id, stored_id, offset)
            if not moved:
                raise no_effect(op, "the scene did not reorder the link", details={"node_id": node.node_id, "link_id": stored_id, "position": wanted})
            node = context.require_node(node.node_id)
            index = _link_index(node, stored_id)
            if index != wanted:
                raise no_effect(op, "the link did not land at the requested position", details={"node_id": node.node_id, "link_id": stored_id, "position": wanted, "actual": index})

    record = node.links[index]
    if record.kind != kind or record.title != title or record.target != target:
        raise no_effect(op, "the stored link does not match the request", details={"node_id": node.node_id, "link_id": stored_id, "stored": _serialize_link(record, index)})
    return {"link_id": stored_id, "link": _serialize_link(record, index)}


def remove_link(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
    op = "link.remove"
    node = context.require_node(_text(params.get("node_id")))
    link_id = _text(params.get("link_id"))
    if _link_index(node, link_id) < 0:
        raise not_found("Link", link_id, hint="Call graph.get_node to list the node's links.")
    removed = context.scene.remove_node_link(node.node_id, link_id)
    if not removed:
        raise no_effect(op, "the scene did not remove the link", details={"node_id": node.node_id, "link_id": link_id})
    if _link_index(context.require_node(node.node_id), link_id) >= 0:
        raise no_effect(op, "the link is still present after removal", details={"node_id": node.node_id, "link_id": link_id})
    return {"removed": True}


HANDLERS = {
    "comment.upsert": upsert_comment,
    "comment.remove": remove_comment,
    "link.upsert": upsert_link,
    "link.remove": remove_link,
}

__all__ = ["HANDLERS"]
