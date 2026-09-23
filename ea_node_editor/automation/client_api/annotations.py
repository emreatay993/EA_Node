# Purpose: CorexClient facade for comment.* / link.* plus sugar: comment, reply, resolve, link_url/file/folder/workspace/node.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_annotations.py
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ea_node_editor.automation.errors import NOT_FOUND, AutomationOpError

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


def _params(required: Mapping[str, Any], **optional: Any) -> dict[str, Any]:
    """Merge required params with the optional ones that carry a value (``None``/"" are omitted)."""
    params = dict(required)
    for key, value in optional.items():
        if value is None or value == "":
            continue
        params[key] = value
    return params


class AnnotationsApi:
    """Facade for comment.* / link.*; every method builds catalog params and calls the client."""

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    # -------------------------------------------------------------- comments

    def comment_upsert(
        self,
        node_id: str,
        body: str,
        *,
        comment_id: str = "",
        author: str = "",
        parent_id: str = "",
        resolved: bool | None = None,
        pinned: bool | None = None,
    ) -> dict[str, Any]:
        """Create (no ``comment_id``) or edit a comment. Omitted flags keep the stored values on edit."""
        params = _params(
            {"node_id": node_id, "body": body},
            comment_id=comment_id,
            author=author,
            parent_id=parent_id,
            resolved=resolved,
            pinned=pinned,
        )
        return self._client.call("comment.upsert", params)

    def comment_remove(self, node_id: str, comment_id: str) -> dict[str, Any]:
        return self._client.call("comment.remove", {"node_id": node_id, "comment_id": comment_id})

    def comment(self, node_id: str, body: str, **kwargs: Any) -> dict[str, Any]:
        """Add a new top-level comment (sugar for ``comment_upsert``)."""
        return self.comment_upsert(node_id, body, **kwargs)

    def reply(self, node_id: str, parent_id: str, body: str, **kwargs: Any) -> dict[str, Any]:
        """Reply to an existing comment on the same node."""
        return self.comment_upsert(node_id, body, parent_id=parent_id, **kwargs)

    def resolve(self, node_id: str, comment_id: str) -> dict[str, Any]:
        """Mark an existing comment resolved, keeping its body, author and pinned state."""
        detail = self._client.call("graph.get_node", {"node_id": node_id})
        existing = _find_comment(detail, comment_id)
        if existing is None:
            raise AutomationOpError(
                NOT_FOUND,
                f"Comment '{comment_id}' was not found on node '{node_id}'.",
                hint="Call graph.get_node to list the node's comments.",
                details={"kind": "Comment", "id": comment_id, "node_id": node_id},
            )
        pinned = existing.get("pinned")
        return self.comment_upsert(
            node_id,
            str(existing.get("body") or ""),
            comment_id=comment_id,
            author=str(existing.get("author") or ""),
            resolved=True,
            pinned=bool(pinned) if isinstance(pinned, bool) else None,
        )

    # ----------------------------------------------------------------- links

    def link_upsert(
        self,
        node_id: str,
        kind: str,
        title: str,
        *,
        target: str = "",
        link_id: str = "",
        subtitle: str = "",
        target_workspace_id: str = "",
        target_node_id: str = "",
        position: int | None = None,
    ) -> dict[str, Any]:
        """Create (no ``link_id``) or edit a link of ``kind`` url|file|folder|workspace|node."""
        params = _params(
            {"node_id": node_id, "kind": kind, "title": title},
            target=target,
            link_id=link_id,
            subtitle=subtitle,
            target_workspace_id=target_workspace_id,
            target_node_id=target_node_id,
            position=position,
        )
        return self._client.call("link.upsert", params)

    def link_remove(self, node_id: str, link_id: str) -> dict[str, Any]:
        return self._client.call("link.remove", {"node_id": node_id, "link_id": link_id})

    def link_url(self, node_id: str, title: str, url: str, **kwargs: Any) -> dict[str, Any]:
        return self.link_upsert(node_id, "url", title, target=url, **kwargs)

    def link_file(self, node_id: str, title: str, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.link_upsert(node_id, "file", title, target=path, **kwargs)

    def link_folder(self, node_id: str, title: str, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.link_upsert(node_id, "folder", title, target=path, **kwargs)

    def link_workspace(self, node_id: str, title: str, workspace_id: str, **kwargs: Any) -> dict[str, Any]:
        return self.link_upsert(node_id, "workspace", title, target=workspace_id, **kwargs)

    def link_node(self, node_id: str, title: str, target_node_id: str, target_workspace_id: str = "", **kwargs: Any) -> dict[str, Any]:
        """Link to another node; ``target_workspace_id`` defaults to the active workspace server-side."""
        return self.link_upsert(
            node_id,
            "node",
            title,
            target_node_id=target_node_id,
            target_workspace_id=target_workspace_id,
            **kwargs,
        )


def _find_comment(detail: Mapping[str, Any], comment_id: str) -> Mapping[str, Any] | None:
    comments = detail.get("comments")
    if not isinstance(comments, list):
        return None
    wanted = str(comment_id or "").strip()
    for item in comments:
        if not isinstance(item, Mapping):
            continue
        candidate = str(item.get("comment_id") or item.get("id") or "").strip()
        if candidate == wanted:
            return item
    return None


__all__ = ["AnnotationsApi"]
