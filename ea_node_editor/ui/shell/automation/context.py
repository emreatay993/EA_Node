# Purpose: AutomationContext facade over live shell owners plus the node/edge summary and lookup helpers every handler shares.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from ea_node_editor.automation.errors import (
    NOT_FOUND,
    NOT_PASSIVE,
    UNKNOWN_NODE_TYPE,
    WRONG_SCOPE,
    AutomationOpError,
    not_found,
)
from ea_node_editor.automation.gate import AutomationGate
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import EdgeInstance, NodeInstance
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec
from ea_node_editor.nodes.registry import NodeRegistry


@dataclass(frozen=True, slots=True)
class AutomationContext:
    """Frozen bundle of the shell owners automation handlers may call.

    Field -> owner (all are existing objects; automation never re-implements them):

    - ``host`` -- ``ShellWindow`` (``None`` in the shell-free test harness)
    - ``scene`` -- ``GraphSceneBridge`` (``host.scene``): every graph mutation
    - ``view`` -- ``ViewportBridge`` (``host.view``): camera
    - ``model`` -- ``GraphModel``; ``registry`` -- ``NodeRegistry``
    - ``workspace_manager`` -- ``WorkspaceManager``: workspace order/activation
    - ``runtime_history`` -- ``RuntimeGraphHistory``: grouped undo steps
    - ``nav`` -- ``WorkspaceNavigationController``: views, framing, tab refresh
    - ``workspace_presenter`` -- ``ShellWorkspacePresenter``: graphics prefs
    - ``workspace_edit`` -- ``WorkspaceEditController``: undo/redo entry points
    - ``project_session`` -- ``ProjectSessionController``: open/save/stage
    - ``run_controller`` / ``run_state`` -- ``RunController`` / ``ShellRunState``
    - ``console`` -- ``ConsoleModel`` (``host.console_panel``): log tail
    - ``canvas_export`` -- ``CanvasExportPresenter``: PNG capture
    - ``effects`` -- ``MutationUiEffects``: post-mutation UI refresh hooks
    - ``quick_widget`` -- ``QQuickWidget`` host for window grabs
    """

    host: Any
    scene: Any
    view: Any
    model: GraphModel
    registry: NodeRegistry
    workspace_manager: Any
    runtime_history: Any
    nav: Any
    workspace_presenter: Any
    workspace_edit: Any
    project_session: Any
    run_controller: Any
    run_state: Any
    console: Any
    canvas_export: Any
    effects: Any
    quick_widget: Any
    gate: AutomationGate | None = None

    @classmethod
    def from_host(cls, host: Any, *, gate: AutomationGate | None = None) -> "AutomationContext":
        """Build the context from a fully bootstrapped ``ShellWindow``."""
        workspace_edit = host.workspace_edit_controller
        return cls(
            host=host,
            scene=host.scene,
            view=host.view,
            model=host.model,
            registry=host.registry,
            workspace_manager=host.workspace_manager,
            runtime_history=host.runtime_history,
            nav=host.workspace_navigation_controller,
            workspace_presenter=host.shell_workspace_presenter,
            workspace_edit=workspace_edit,
            project_session=host.project_session_controller,
            run_controller=host.run_controller,
            run_state=host.run_state,
            console=host.console_panel,
            canvas_export=host.canvas_export_presenter,
            effects=workspace_edit.mutation_ui_effects,
            quick_widget=host.quick_widget,
            gate=gate,
        )

    # ----------------------------------------------------------------- lookups

    @property
    def has_shell(self) -> bool:
        return self.host is not None

    def require_shell(self, op: str) -> Any:
        if self.host is None:
            raise AutomationOpError(
                "INTERNAL",
                f"{op} requires the full COREX shell; the shell-free harness cannot serve it.",
                hint="Run this op against a live COREX instance.",
            )
        return self.host

    def workspace_id(self) -> str:
        if self.workspace_manager is not None:
            return str(self.workspace_manager.active_workspace_id() or "").strip()
        return str(self.model.active_workspace.workspace_id)

    def active_workspace(self) -> WorkspaceData:
        workspace_id = self.workspace_id()
        workspace = self.model.project.workspaces.get(workspace_id)
        if workspace is None:
            raise AutomationOpError(NOT_FOUND, "No active workspace is available.", details={"workspace_id": workspace_id})
        return workspace

    def scope_path(self) -> list[str]:
        # ``active_scope_path`` is a pyqtProperty on GraphSceneBridge (QVariantList), not a method.
        return [str(item) for item in self.scene.active_scope_path]

    def scope_parent_id(self) -> str | None:
        path = self.scope_path()
        return path[-1] if path else None

    def node_or_none(self, node_id: str) -> NodeInstance | None:
        normalized = str(node_id or "").strip()
        if not normalized:
            return None
        return self.active_workspace().nodes.get(normalized)

    def require_node(self, node_id: str) -> NodeInstance:
        node = self.node_or_none(node_id)
        if node is None:
            raise not_found("Node", str(node_id))
        return node

    def require_nodes(self, node_ids: Iterable[Any]) -> list[NodeInstance]:
        return [self.require_node(str(node_id)) for node_id in node_ids]

    def require_node_in_scope(self, node_id: str) -> NodeInstance:
        node = self.require_node(node_id)
        if not self.in_active_scope(node):
            raise AutomationOpError(
                WRONG_SCOPE,
                f"Node '{node.node_id}' lives in a different scope (parent {node.parent_node_id or 'root'}).",
                details={"node_id": node.node_id, "parent_node_id": node.parent_node_id or "", "scope_path": self.scope_path()},
            )
        return node

    def in_active_scope(self, node: NodeInstance) -> bool:
        return (node.parent_node_id or None) == self.scope_parent_id()

    def edge_or_none(self, edge_id: str) -> EdgeInstance | None:
        normalized = str(edge_id or "").strip()
        if not normalized:
            return None
        return self.active_workspace().edges.get(normalized)

    def require_edge(self, edge_id: str) -> EdgeInstance:
        edge = self.edge_or_none(edge_id)
        if edge is None:
            raise not_found("Edge", str(edge_id))
        return edge

    def spec_for(self, node_or_type: NodeInstance | str) -> NodeTypeSpec:
        type_id = node_or_type.type_id if isinstance(node_or_type, NodeInstance) else str(node_or_type or "").strip()
        spec = self.registry.spec_or_none(type_id)
        if spec is None:
            raise AutomationOpError(
                UNKNOWN_NODE_TYPE,
                f"Unknown node type '{type_id}'.",
                details={"type_id": type_id, "suggestions": self.suggest_type_ids(type_id)},
            )
        return spec

    def suggest_type_ids(self, type_id: str, *, limit: int = 5) -> list[str]:
        import difflib

        candidates = [spec.type_id for spec in self.registry.all_specs()]
        close = difflib.get_close_matches(type_id, candidates, n=limit, cutoff=0.4)
        if close:
            return close
        needle = type_id.lower().split(".")[-1]
        return [candidate for candidate in candidates if needle and needle in candidate.lower()][:limit]

    def require_passive(self, node: NodeInstance) -> NodeTypeSpec:
        spec = self.spec_for(node)
        if spec.runtime_behavior != "passive":
            raise AutomationOpError(
                NOT_PASSIVE,
                f"Node '{node.node_id}' ({node.type_id}) is not a passive node.",
                details={"node_id": node.node_id, "type_id": node.type_id, "runtime_behavior": spec.runtime_behavior},
            )
        return spec

    def port_spec_or_none(self, node: NodeInstance, port_key: str) -> PortSpec | None:
        normalized = str(port_key or "").strip()
        for port in self.spec_for(node).ports:
            if port.key == normalized:
                return port
        return None

    def require_port(self, node: NodeInstance, port_key: str) -> PortSpec:
        port = self.port_spec_or_none(node, port_key)
        if port is None:
            raise AutomationOpError(
                NOT_FOUND,
                f"Port '{port_key}' does not exist on node '{node.node_id}' ({node.type_id}).",
                hint="Call graph.get_node to list the node's effective ports.",
                details={"node_id": node.node_id, "port": str(port_key), "available": [p.key for p in self.spec_for(node).ports]},
            )
        return port

    # --------------------------------------------------------------- summaries

    def node_bounds(self, node_id: str) -> tuple[float, float, float, float] | None:
        bounds = self.scene.node_bounds(node_id)
        if bounds is None:
            return None
        return (float(bounds.x()), float(bounds.y()), float(bounds.width()), float(bounds.height()))

    def node_summary(self, node: NodeInstance) -> dict[str, Any]:
        spec = self.registry.spec_or_none(node.type_id)
        bounds = self.node_bounds(node.node_id)
        width = bounds[2] if bounds is not None else (float(node.custom_width) if node.custom_width else None)
        height = bounds[3] if bounds is not None else (float(node.custom_height) if node.custom_height else None)
        return {
            "node_id": node.node_id,
            "type_id": node.type_id,
            "title": node.title,
            "x": float(node.x),
            "y": float(node.y),
            "width": width,
            "height": height,
            "collapsed": bool(node.collapsed),
            "locked": bool(node.locked),
            "parent_node_id": node.parent_node_id or "",
            "runtime_behavior": spec.runtime_behavior if spec is not None else "",
            "surface_family": spec.surface_family if spec is not None else "",
            "comment_count": len(node.comments),
            "link_count": len(node.links),
        }

    def edge_summary(self, edge: EdgeInstance) -> dict[str, Any]:
        workspace = self.active_workspace()
        source = workspace.nodes.get(edge.source_node_id)
        kind = ""
        if source is not None:
            port = self.port_spec_or_none(source, edge.source_port_key) if self.registry.spec_or_none(source.type_id) else None
            kind = port.kind if port is not None else ""
        return {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "source_port": edge.source_port_key,
            "target_node_id": edge.target_node_id,
            "target_port": edge.target_port_key,
            "enabled": bool(edge.enabled),
            "label": edge.label,
            "kind": kind,
        }

    def incident_edges(self, node_id: str) -> list[EdgeInstance]:
        workspace = self.active_workspace()
        return [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == node_id or edge.target_node_id == node_id
        ]

    # ------------------------------------------------------------- selection

    def selected_node_ids(self) -> list[str]:
        # ``selected_node_ids`` is a pyqtProperty on GraphSceneBridge (QVariantList), not a method.
        return [str(item) for item in self.scene.selected_node_ids]

    @contextmanager
    def with_selection(self, node_ids: Sequence[str]) -> Iterator[None]:
        """Temporarily select ``node_ids`` (facade has clear + additive select only)."""
        previous = self.selected_node_ids()
        self.scene.clear_selection()
        for node_id in node_ids:
            self.scene.select_node(str(node_id), True)
        try:
            yield
        finally:
            self.scene.clear_selection()
            for node_id in previous:
                if self.node_or_none(node_id) is not None:
                    self.scene.select_node(node_id, True)

    def node_id_set(self) -> set[str]:
        return set(self.active_workspace().nodes)

    def new_ids_since(self, before: set[str]) -> list[str]:
        return sorted(self.node_id_set() - set(before))


__all__ = ["AutomationContext"]
