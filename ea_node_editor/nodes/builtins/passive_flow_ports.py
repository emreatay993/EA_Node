from __future__ import annotations

from ea_node_editor.nodes.types import PortSpec

CARDINAL_PASSIVE_FLOW_PORTS = (
    PortSpec("top", "neutral", "flow", "flow", side="top", allow_multiple_connections=True),
    PortSpec("right", "neutral", "flow", "flow", side="right", allow_multiple_connections=True),
    PortSpec("bottom", "neutral", "flow", "flow", side="bottom", allow_multiple_connections=True),
    PortSpec("left", "neutral", "flow", "flow", side="left", allow_multiple_connections=True),
)


__all__ = ["CARDINAL_PASSIVE_FLOW_PORTS"]
