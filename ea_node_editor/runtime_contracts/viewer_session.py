from __future__ import annotations

import copy
import hashlib
from typing import Any


def default_viewer_session_id(workspace_id: str, node_id: str) -> str:
    digest = hashlib.sha1(f"{workspace_id}:{node_id}".encode("utf-8")).hexdigest()[:16]
    return f"viewer_session_{digest}"


def viewer_event_payload(event: object) -> dict[str, Any]:
    return {
        "workspace_id": str(getattr(event, "workspace_id", "")).strip(),
        "node_id": str(getattr(event, "node_id", "")).strip(),
        "session_id": str(getattr(event, "session_id", "")).strip(),
        "backend_id": str(getattr(event, "backend_id", "")).strip(),
        "data_refs": copy.deepcopy(getattr(event, "data_refs", {})),
        "transport": copy.deepcopy(getattr(event, "transport", {})),
        "transport_revision": int(getattr(event, "transport_revision", 0) or 0),
        "live_open_status": str(getattr(event, "live_open_status", "")).strip(),
        "live_open_blocker": copy.deepcopy(getattr(event, "live_open_blocker", {})),
        "camera_state": copy.deepcopy(getattr(event, "camera_state", {})),
        "playback_state": copy.deepcopy(getattr(event, "playback_state", {})),
        "summary": copy.deepcopy(getattr(event, "summary", {})),
        "options": copy.deepcopy(getattr(event, "options", {})),
    }


__all__ = [
    "default_viewer_session_id",
    "viewer_event_payload",
]
