# Purpose: Share QML-free execution and source fixtures across generic Plot tests.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_generic_plot_preparation.py, tests/test_generic_plot_exports.py
from __future__ import annotations

from pathlib import Path

from ea_node_editor.execution.plot_backend import PlotRenderRequest
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, RuntimeSnapshotContext
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.plot.generic import build_generic_plot_render_request
from ea_node_editor.nodes.execution_context import ExecutionContext


def _execution_context(
    *,
    inputs: dict[str, object] | None = None,
    properties: dict[str, object] | None = None,
    project_path: Path | None = None,
    runtime_snapshot: RuntimeSnapshot | None = None,
    runtime_snapshot_context: RuntimeSnapshotContext | None = None,
    path_resolver=None,  # noqa: ANN001
    node_type_id: str = "plot.bar",
) -> ExecutionContext:
    return ExecutionContext(
        run_id="run_plot_contract",
        node_id="node_plot_line",
        workspace_id="ws_plot_contract",
        inputs=dict(inputs or {}),
        properties=dict(properties or {}),
        emit_log=lambda _level, _message: None,
        project_path=str(project_path) if project_path is not None else "",
        runtime_snapshot=runtime_snapshot,
        runtime_snapshot_context=runtime_snapshot_context,
        path_resolver=path_resolver or (lambda _value: None),
        node_type_id=node_type_id,
    )



def _tabular_input_context(source: Path, **properties: object) -> ExecutionContext:
    payload = {"path": str(source), **properties}
    return ExecutionContext(
        run_id="run_tabular_for_plot",
        node_id="node_tabular_for_plot",
        workspace_id="ws_plot_contract",
        inputs={},
        properties=payload,
        emit_log=lambda _level, _message: None,
    )



def _generic_render_request(
    *,
    type_id: str = "plot.bar",
    series_input: object,
    properties: dict[str, object] | None = None,
) -> PlotRenderRequest:
    registry = build_default_registry()
    normalized_properties = registry.normalize_properties(type_id, properties or {})
    render_request, warnings = build_generic_plot_render_request(
        node_type_id=type_id,
        properties=normalized_properties,
        series_input=series_input,
    )
    assert warnings == ()
    assert isinstance(render_request, PlotRenderRequest)
    return render_request
