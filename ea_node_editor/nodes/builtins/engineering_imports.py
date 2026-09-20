# Purpose: Import reusable CAD/mesh models and prepared FE scenes.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_engineering_import_nodes.py
from __future__ import annotations

from ea_node_editor.nodes.builtins.integrations_common import pick_path, require_existing_file
from ea_node_editor.nodes.execution_context import NodeResult


def _import_source(ctx, *, source_kind: str):  # noqa: ANN001, ANN202
    node_name = {"fe": "FE Import", "cad": "CAD Import", "mesh": "Mesh Import"}[source_kind]
    path = pick_path(ctx, input_key="path", property_key="path", node_name=node_name)
    require_existing_file(path, node_name=node_name)
    worker_services = getattr(ctx, "worker_services", None)
    if worker_services is None:
        raise RuntimeError(f"{node_name} requires worker runtime services.")
    runtime = worker_services.prepared_scene_runtime
    length_unit = str(ctx.properties.get("length_unit", "file") or "file").strip()
    if length_unit.casefold() in {"file", "choose"}:
        length_unit = ""
    owner_scope = worker_services.run_owner_scope(ctx.run_id)
    if source_kind == "fe":
        return runtime.prepare_fe_scene(
            path,
            length_unit=length_unit,
            workspace_id=ctx.workspace_id,
            owner_scope=owner_scope,
        )
    if source_kind == "cad":
        return runtime.import_cad_model(
            path, length_unit=length_unit, owner_scope=owner_scope,
        )
    return runtime.import_surface_model(
        path, length_unit=length_unit, owner_scope=owner_scope,
    )


def execute_engineering_import(ctx, *, source_kind: str) -> NodeResult:  # noqa: ANN001
    output_key = "scene" if source_kind == "fe" else "model"
    return NodeResult(outputs={output_key: _import_source(ctx, source_kind=source_kind)})


__all__ = [
    "execute_engineering_import",
]
