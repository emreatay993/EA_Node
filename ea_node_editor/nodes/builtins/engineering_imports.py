# Purpose: Provide neutral FE and CAD file import nodes that emit prepared scene handles.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_engineering_import_nodes.py
from __future__ import annotations

from ea_node_editor.common.scene_protocol import COREX_SCENE_DATA_TYPE
from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type_spec
from ea_node_editor.nodes.builtins.integrations_common import pick_path, require_existing_file
from ea_node_editor.nodes.decorators import plugin_descriptor
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.file_dialog_filters import CAD_SCENE_FILES_FILTER, FE_SCENE_FILES_FILTER
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec


def _import_scene(ctx, *, source_kind: str):  # noqa: ANN001, ANN202
    node_name = "FE Import" if source_kind == "fe" else "CAD Import"
    path = pick_path(ctx, input_key="path", property_key="path", node_name=node_name)
    require_existing_file(path, node_name=node_name)
    worker_services = getattr(ctx, "worker_services", None)
    if worker_services is None:
        raise RuntimeError(f"{node_name} requires worker runtime services.")
    runtime = worker_services.prepared_scene_runtime
    length_unit = str(ctx.properties.get("length_unit", "file") or "file").strip()
    if length_unit.casefold() == "file":
        length_unit = ""
    owner_scope = worker_services.run_owner_scope(ctx.run_id)
    if source_kind == "fe":
        return runtime.prepare_fe_scene(
            path,
            length_unit=length_unit,
            workspace_id=ctx.workspace_id,
            owner_scope=owner_scope,
        )
    return runtime.prepare_cad_scene(
        path,
        length_unit=length_unit,
        workspace_id=ctx.workspace_id,
        owner_scope=owner_scope,
    )


def _length_unit_property() -> PropertySpec:
    return PropertySpec(
        "length_unit",
        "enum",
        "file",
        "Length Unit",
        enum_values=("file", "m", "mm", "cm", "in", "ft"),
        group="Import",
    )


class FeImportNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="engineering.fe_import",
            display_name="FE Import",
            category_path=("Engineering", "Import"),
            description="Imports a neutral finite-element file as a prepared COREX scene.",
            keywords=("finite element", "mesh", "import"),
            ports=(
                PortSpec(
                    "path",
                    "in",
                    "data",
                    'COREX.DataTypes.Path',
                    required=True,
                    uses_property_default=True,
                    description="Path to the neutral finite-element file to import.",
                ),
                PortSpec(
                    "scene",
                    "out",
                    "data",
                    COREX_SCENE_DATA_TYPE,
                    exposed=True,
                    description="Prepared finite-element scene for viewing or downstream processing.",
                ),
            ),
            properties=(
                PropertySpec("path", "path", "", "FE File", file_filter=FE_SCENE_FILES_FILTER),
                _length_unit_property(),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult(outputs={"scene": _import_scene(ctx, source_kind="fe")})


class CadImportNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="engineering.cad_import",
            display_name="CAD Import",
            category_path=("Engineering", "Import"),
            description="Imports a neutral CAD file as a prepared COREX scene.",
            keywords=("cad", "geometry", "import"),
            ports=(
                PortSpec(
                    "path",
                    "in",
                    "data",
                    'COREX.DataTypes.Path',
                    required=True,
                    uses_property_default=True,
                    description="Path to the neutral CAD file to import.",
                ),
                PortSpec(
                    "scene",
                    "out",
                    "data",
                    COREX_SCENE_DATA_TYPE,
                    exposed=True,
                    description="Prepared CAD scene for viewing or downstream processing.",
                ),
            ),
            properties=(
                PropertySpec("path", "path", "", "CAD File", file_filter=CAD_SCENE_FILES_FILTER),
                _length_unit_property(),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult(outputs={"scene": _import_scene(ctx, source_kind="cad")})


ENGINEERING_IMPORT_NODE_DESCRIPTORS = (
    plugin_descriptor(FeImportNodePlugin),
    plugin_descriptor(CadImportNodePlugin),
)


__all__ = [
    "CadImportNodePlugin",
    "ENGINEERING_IMPORT_NODE_DESCRIPTORS",
    "FeImportNodePlugin",
]
