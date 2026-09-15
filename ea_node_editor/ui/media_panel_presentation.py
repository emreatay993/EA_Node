# Purpose: Project a previous immutable Plot preview for canvas display only.
# Map: feature_routes/media_image_video_pdf_refocus.md
# Tests: tests/test_media_panel_presentation.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json

from ea_node_editor.runtime_contracts import DataTree, PlotValue
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.ui.image_value_preview_provider import image_value_preview_source
from ea_node_editor.ui.media_panel_source import MediaPanelSourceResolution
from ea_node_editor.ui.support.solution_output_cache import retained_output_record


def _plot(record: Mapping | None, port: str) -> PlotValue | None:
    if record is None or not record.get("outputs_available", False):
        return None
    output = record.get("outputs", {}).get(port)
    if not isinstance(output, SettledPortResult) or output.status != "value":
        return None
    tree = output.value
    if not isinstance(tree, DataTree) or tree.item_count != 1:
        return None
    value = next(item for _path, items in tree.branches for item in items)
    return value if type(value) is PlotValue else None


def _source_route(workspace: object, node_id: str, producer_id: str) -> tuple | None:
    """Bind the media path, stopping at the plot (whose inputs may be edited)."""
    nodes = workspace.nodes
    pending = [node_id]
    visited = set()
    edges = []
    while pending:
        target = pending.pop()
        if target in visited:
            continue
        visited.add(target)
        if target not in nodes:
            return None
        if target == producer_id:
            continue
        incoming = [
            edge
            for edge in workspace.edges.values()
            if edge.enabled
            and edge.target_node_id == target
            and (target != node_id or edge.target_port_key == "source")
        ]
        for edge in incoming:
            edges.append(
                (
                    edge.edge_id,
                    edge.source_node_id,
                    edge.source_port_key,
                    edge.target_node_id,
                    edge.target_port_key,
                )
            )
            pending.append(edge.source_node_id)
    if producer_id not in visited:
        return None
    return tuple(sorted(edges)), tuple(sorted(visited))


def _updating(
    run_state: object, workspace: object, route_nodes: tuple[str, ...]
) -> bool:
    workspace_id = workspace.workspace_id
    if getattr(run_state, "node_execution_workspace_id", "") == workspace_id and set(
        route_nodes
    ).intersection(getattr(run_state, "running_node_ids", ())):
        return True
    if any(
        getattr(run_state, f"active_{kind}_id", "")
        and getattr(run_state, f"active_{kind}_workspace_id", "") == workspace_id
        for kind in ("submission", "run")
    ) and set(route_nodes).intersection(
        getattr(run_state, "active_execution_node_ids", ())
    ):
        return True
    if getattr(run_state, "pending_auto_run_workspace_id", "") != workspace_id:
        return False
    pending = list(getattr(run_state, "pending_auto_run_target_node_ids", ()))
    visited = set()
    while pending:
        source = pending.pop()
        if source in visited:
            continue
        if source in route_nodes:
            return True
        visited.add(source)
        pending.extend(
            edge.target_node_id
            for edge in workspace.edges.values()
            if edge.enabled and edge.source_node_id == source
        )
    return False


@dataclass(frozen=True)
class _Binding:
    route: tuple
    value_signature: str
    record_ids: tuple[tuple[str, str], ...]


def _observed_record(
    run_state: object,
    workspace_id: str,
    node_id: str,
    binding: _Binding | None,
    *,
    pending: bool,
) -> dict | None:
    record = retained_output_record(run_state, workspace_id, node_id)
    if record is not None or binding is None or not pending:
        return record
    # Whole-workspace facts may arrive before the corresponding node's queued
    # cache event. Use only the exact earlier record this presentation observed,
    # and only until relevant work finishes. Eviction/failed/empty records do not
    # enter this path and never become eligible current results.
    facts = getattr(run_state, "node_solution_facts_by_workspace_id", {}).get(
        workspace_id, {}
    )
    fact = facts.get(node_id)
    selected_id = getattr(fact, "retained_record_id", "")
    previous_id = dict(binding.record_ids).get(node_id)
    if (
        getattr(getattr(fact, "freshness", None), "value", "") != "current"
        or not selected_id
        or not previous_id
        or selected_id == previous_id
    ):
        return None
    records = (
        getattr(run_state, "cached_node_output_records_by_workspace_id", {})
        .get(workspace_id, {})
        .get(node_id, {})
    )
    if selected_id in records:
        return None
    previous = records.get(previous_id)
    return (
        previous
        if isinstance(previous, dict) and previous.get("record_id") == previous_id
        else None
    )


class MediaPanelPresentation:
    """Remember only source identity; previous pixels always come from runtime facts.

    This is deliberately separate from the strict resolver used by exports,
    fullscreen sessions and current-result consumers. No Plot/value cache lives here.
    """

    def __init__(self) -> None:
        self._context: tuple | None = None
        self._bindings: dict[str, _Binding] = {}
        self._context_revision = 0

    def begin(self, project: object, workspace: object, run_state: object) -> None:
        context = (project, workspace, run_state)
        if self._context is None or any(
            a is not b for a, b in zip(context, self._context)
        ):
            self._bindings.clear()
            self._context = context
            self._context_revision += 1
        self._bindings = {
            key: value
            for key, value in self._bindings.items()
            if key in workspace.nodes
        }

    def project(
        self,
        *,
        node: object,
        workspace: object,
        run_state: object,
        resolution: MediaPanelSourceResolution,
    ) -> dict:
        payload = resolution.to_qml_payload()
        payload["previous_plot_preview"] = {}
        node_id = node.node_id
        workspace_id = workspace.workspace_id
        previous_binding = self._bindings.get(node_id)
        pending = bool(
            previous_binding
            and _updating(run_state, workspace, previous_binding.route[1])
        )
        media_record = _observed_record(
            run_state, workspace_id, node_id, previous_binding, pending=pending
        )
        publication_gap = (
            media_record is not None
            and retained_output_record(run_state, workspace_id, node_id) is None
        )
        plot = (
            resolution.raw_value
            if resolution.state == "ready"
            else _plot(
                media_record,
                "_surface_source",
            )
        )
        valid = (
            resolution.input_exposed
            and resolution.input_connected
            and (
                resolution.state in {"ready", "stale", "running"}
                or (publication_gap and resolution.state in {"waiting", "empty"})
            )
            and type(plot) is PlotValue
            and plot.provenance.workspace_id == workspace_id
            and getattr(workspace.nodes.get(plot.provenance.node_id), "type_id", "")
            == "plot.signal"
        )
        route = (
            _source_route(workspace, node_id, plot.provenance.node_id)
            if valid
            else None
        )
        if route is None:
            self._bindings.pop(node_id, None)
            return payload
        records = {
            source_id: _observed_record(
                run_state, workspace_id, source_id, previous_binding, pending=pending
            )
            for source_id in route[1]
        }
        binding = _Binding(
            route,
            plot.value_signature,
            tuple(
                (source_id, record["record_id"])
                for source_id, record in records.items()
                if record is not None
            ),
        )
        payload["plot_display_key"] = str(self._context_revision) + json.dumps(route)
        if resolution.state == "ready":
            self._bindings[node_id] = binding
            return payload
        if (
            previous_binding is None
            or previous_binding.route != route
            or previous_binding.value_signature != binding.value_signature
        ):
            # Acceptance can publish both new CURRENT records before the queued
            # visual "running" flag is cleared. Stage that accepted replacement
            # on the same source route without relaxing the strict source state.
            current_media = _plot(
                retained_output_record(
                    run_state, workspace_id, node_id, current_only=True
                ),
                "_surface_source",
            )
            current_producer = _plot(
                retained_output_record(
                    run_state, workspace_id, plot.provenance.node_id, current_only=True
                ),
                "image",
            )
            if not (
                previous_binding
                and previous_binding.route == route
                and current_media is not None
                and current_producer is not None
                and current_media.value_signature
                == current_producer.value_signature
                == plot.value_signature
            ):
                self._bindings.pop(node_id, None)
                return payload
            self._bindings[node_id] = binding
        for source_id, record in records.items():
            if record is None or not record.get("outputs_available", False):
                self._bindings.pop(node_id, None)
                return payload
            if getattr(run_state, "node_execution_workspace_id", "") == workspace_id:
                if any(
                    source_id in getattr(run_state, attr, ())
                    for attr in (
                        "failed_node_ids",
                        "blocked_node_ids",
                        "empty_node_ids",
                    )
                ):
                    self._bindings.pop(node_id, None)
                    return payload
            if source_id == plot.provenance.node_id and _plot(record, "image") is None:
                self._bindings.pop(node_id, None)
                return payload
        self._bindings[node_id] = binding
        preview_url = image_value_preview_source(plot.preview)
        if preview_url:
            payload["previous_plot_preview"] = {
                "preview_source_url": preview_url,
                "status": "updating"
                if _updating(run_state, workspace, route[1])
                else "out_of_date",
            }
        return payload
