from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import dpf_category_path
from ea_node_editor.nodes.builtins.plot.generic import (
    PLOT_AXIS_LIMITS_DEFAULT,
    PLOT_BACKEND_VALUES,
    PLOT_COLORMAP_VALUES,
    PLOT_DATA_EXPORT_FORMATS,
    PLOT_LOG_SCALES_DEFAULT,
    PLOT_STATIC_EXPORT_FORMATS,
    _export_format,
    _mapping_property,
    _property_defaults,
    _runtime_artifact_metadata,
    _string_property,
)
from ea_node_editor.nodes.dpf_runtime_contracts import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.output_artifacts import (
    allocate_managed_output,
    artifact_store_for_context,
    persist_artifact_store,
    register_staged_path_artifact,
)
from ea_node_editor.nodes.plugin_contracts import PluginDescriptor
from ea_node_editor.nodes.runtime_refs import RuntimeHandleRef

if TYPE_CHECKING:
    from ea_node_editor.execution.plot_backend import PlotExportResult, PlotRenderRequest

# Keep node registration independent from execution implementation imports.
AUTO_PLOT_BACKEND_ID = "auto"
MATPLOTLIB_PLOT_BACKEND_ID = "matplotlib"
DPF_PLOT_FRAME_SELECTOR_DEFAULT = "1"
PLOT_SURFACE_STATIC_EXPORT = "static_export"
PLOT_SURFACE_DATA_EXPORT = "data_export"
PLOT_TYPE_LINE = "line"
PLOT_TYPE_SCATTER = "scatter"
PLOT_TYPE_BAR = "bar"
PLOT_TYPE_HISTOGRAM = "histogram"
PLOT_TYPE_HEATMAP = "heatmap"
PLOT_TYPE_CONTOUR = "contour"
PLOT_TYPE_SURFACE = "surface"
PLOT_TYPE_POINT_CLOUD = "point_cloud"
PLOT_TYPE_STREAMLINES = "streamlines"
DPF_PLOT_SERIES_RUNTIME_SHAPES = (
    "DPF Field handles",
    "DPF FieldsContainer handles",
    "DPF mesh and scoping metadata",
)
DPF_PLOT_CATEGORY_PATH = dpf_category_path("Plot")
DPF_PLOT_ICON = "dpf/ansys.svg"
DPF_PLOT_FRAME_SELECTOR_PROPERTY = "frame_selector"
DPF_PLOT_ANIMATE_PROPERTY = "animate"
DPF_PLOT_RUNTIME_SHAPE_TEXT = ", ".join(DPF_PLOT_SERIES_RUNTIME_SHAPES)


@dataclass(frozen=True, slots=True)
class DpfPlotNodeDefinition:
    type_id: str
    display_name: str
    plot_type: str
    supports_colormap: bool = False
    description: str = ""


DPF_PLOT_NODE_DEFINITIONS = (
    DpfPlotNodeDefinition("dpf.plot.line", "DPF Line Plot", PLOT_TYPE_LINE),
    DpfPlotNodeDefinition("dpf.plot.scatter", "DPF Scatter Plot", PLOT_TYPE_SCATTER),
    DpfPlotNodeDefinition("dpf.plot.bar", "DPF Bar Plot", PLOT_TYPE_BAR),
    DpfPlotNodeDefinition("dpf.plot.histogram", "DPF Histogram Plot", PLOT_TYPE_HISTOGRAM),
    DpfPlotNodeDefinition("dpf.plot.heatmap", "DPF Heatmap Plot", PLOT_TYPE_HEATMAP, supports_colormap=True),
    DpfPlotNodeDefinition("dpf.plot.contour", "DPF Contour Plot", PLOT_TYPE_CONTOUR, supports_colormap=True),
    DpfPlotNodeDefinition("dpf.plot.surface", "DPF Surface Plot", PLOT_TYPE_SURFACE, supports_colormap=True),
    DpfPlotNodeDefinition(
        "dpf.plot.point_cloud",
        "DPF Point Cloud Plot",
        PLOT_TYPE_POINT_CLOUD,
        supports_colormap=True,
    ),
    DpfPlotNodeDefinition(
        "dpf.plot.streamlines",
        "DPF Streamlines Plot",
        PLOT_TYPE_STREAMLINES,
        supports_colormap=True,
    ),
)
DPF_PLOT_NODE_TYPE_IDS = tuple(definition.type_id for definition in DPF_PLOT_NODE_DEFINITIONS)


def _dpf_plot_ports() -> tuple[PortSpec, ...]:
    return (
        PortSpec(
            "series",
            "in",
            "data",
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            label="DPF Series",
            required=True,
            data_access="list",
            accepted_data_types=(DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE),
        ),
        PortSpec("mesh", "in", "data", DPF_MESH_DATA_TYPE, label="Mesh", required=False),
        PortSpec("scoping", "in", "data", DPF_SCOPING_DATA_TYPE, label="Scoping", required=False),
        PortSpec("static_export", "out", "data", 'COREX.DataTypes.Path', label="Image Export", exposed=True),
        PortSpec("data_export", "out", "data", 'COREX.DataTypes.Path', label="Data Export", exposed=True),
        PortSpec("exports", "out", "data", 'COREX.DataTypes.Any', label="Exports", exposed=True),
    )


def _dpf_plot_properties(*, supports_colormap: bool) -> tuple[PropertySpec, ...]:
    properties: list[PropertySpec] = [
        PropertySpec(
            "backend",
            "enum",
            AUTO_PLOT_BACKEND_ID,
            "Backend",
            enum_values=PLOT_BACKEND_VALUES,
            inspector_editor="enum",
            group="Rendering",
        ),
        PropertySpec("title", "str", "", "Title", inline_editor="text", group="Text"),
        PropertySpec("x_label", "str", "", "X Axis Label", inline_editor="text", group="Text"),
        PropertySpec("y_label", "str", "", "Y Axis Label", inline_editor="text", group="Text"),
        PropertySpec("z_label", "str", "", "Z Axis Label", inline_editor="text", group="Text"),
        PropertySpec(
            "axis_limits",
            "json",
            copy.deepcopy(PLOT_AXIS_LIMITS_DEFAULT),
            "Axis Limits",
            inspector_editor="textarea",
            group="Axes",
        ),
        PropertySpec(
            "log_scales",
            "json",
            copy.deepcopy(PLOT_LOG_SCALES_DEFAULT),
            "Log Scales",
            inspector_editor="textarea",
            group="Axes",
        ),
        PropertySpec("grid", "bool", True, "Grid", inspector_editor="toggle", group="Axes"),
        PropertySpec("legend", "bool", True, "Legend", inspector_editor="toggle", group="Text"),
    ]
    if supports_colormap:
        properties.append(
            PropertySpec(
                "colormap",
                "enum",
                "viridis",
                "Colormap",
                enum_values=PLOT_COLORMAP_VALUES,
                inspector_editor="enum",
                group="Rendering",
            )
        )
    properties.extend(
        [
            PropertySpec(
                DPF_PLOT_FRAME_SELECTOR_PROPERTY,
                "str",
                DPF_PLOT_FRAME_SELECTOR_DEFAULT,
                "Frame Selector",
                inspector_editor="text",
                group="DPF",
            ),
            PropertySpec(
                DPF_PLOT_ANIMATE_PROPERTY,
                "bool",
                False,
                "Animate",
                inspector_editor="toggle",
                group="DPF",
            ),
            PropertySpec(
                "render_in_canvas",
                "bool",
                True,
                "Render In Canvas",
                inspector_editor="toggle",
                group="Rendering",
            ),
            PropertySpec(
                "archive_export_on_run",
                "bool",
                False,
                "Archive Export On Run",
                inspector_editor="toggle",
                group="Export",
            ),
            PropertySpec(
                "static_export_format",
                "enum",
                "png",
                "Image Export Format",
                enum_values=PLOT_STATIC_EXPORT_FORMATS,
                inspector_editor="enum",
                group="Export",
            ),
            PropertySpec(
                "data_export_format",
                "enum",
                "csv",
                "Data Export Format",
                enum_values=PLOT_DATA_EXPORT_FORMATS,
                inspector_editor="enum",
                group="Export",
            ),
            PropertySpec(
                "plot_options",
                "json",
                {},
                "Plot Options",
                inspector_editor="textarea",
                group="Rendering",
            ),
        ]
    )
    return tuple(properties)


def _dpf_plot_node_description(definition: DpfPlotNodeDefinition) -> str:
    if definition.description:
        return definition.description
    return (
        f"DPF typed {definition.display_name.lower()} node. The variadic DPF series input accepts "
        f"{DPF_PLOT_RUNTIME_SHAPE_TEXT} and adapts selected frames into plot backend data."
    )


def _dpf_plot_node_spec(definition: DpfPlotNodeDefinition) -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id=definition.type_id,
        display_name=definition.display_name,
        category_path=DPF_PLOT_CATEGORY_PATH,
        icon=DPF_PLOT_ICON,
        ports=_dpf_plot_ports(),
        properties=_dpf_plot_properties(supports_colormap=definition.supports_colormap),
        description=_dpf_plot_node_description(definition),
        surface_variant=definition.plot_type,
    )


def _as_plain(value: Any) -> Any:
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return _as_plain(tolist())
    if isinstance(value, Mapping):
        return {str(key): _as_plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_as_plain(item) for item in value]
    return value


def _input_items(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, RuntimeHandleRef):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return (value,)


def _numeric_magnitude(value: Any) -> Any:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        components = []
        for item in value:
            try:
                components.append(float(item))
            except (TypeError, ValueError):
                return _as_plain(value)
        return math.sqrt(sum(component * component for component in components))
    return value


def _field_data_rows(field: Any) -> list[Any]:
    raw_data = _as_plain(getattr(field, "data", ()))
    if isinstance(raw_data, list):
        return raw_data
    return [raw_data]


def _field_scalar_values(field: Any) -> list[Any]:
    return [_numeric_magnitude(row) for row in _field_data_rows(field)]


def _field_component_rows(field: Any) -> list[list[Any]]:
    rows = _field_data_rows(field)
    component_rows: list[list[Any]] = []
    for row in rows:
        if isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
            component_rows.append(list(row))
        else:
            component_rows.append([row])
    return component_rows


def _scoping_ids(scoping: Any) -> list[Any]:
    ids = getattr(scoping, "ids", ())
    try:
        return list(ids)
    except TypeError:
        return []


def _field_x_values(
    field: Any,
    values: Sequence[Any],
    metadata: Mapping[str, Any] | None = None,
) -> list[Any]:
    time_axis_values = _time_axis_values(metadata, expected_length=len(values))
    if time_axis_values is not None:
        return time_axis_values
    ids = _scoping_ids(getattr(field, "scoping", None))
    if len(ids) == len(values):
        return ids
    return list(range(len(values)))


def _time_axis_values(
    metadata: Mapping[str, Any] | None,
    *,
    expected_length: int,
) -> list[float] | None:
    if not metadata or str(metadata.get("x_axis", "")).strip() != "time":
        return None
    raw_values = metadata.get("time_values")
    if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes, bytearray)):
        return None
    if len(raw_values) != expected_length:
        return None
    try:
        return [float(value) for value in raw_values]
    except (TypeError, ValueError):
        return None


def _grid_from_values(values: Sequence[Any]) -> list[list[Any]]:
    if not values:
        return [[]]
    width = max(1, int(math.ceil(math.sqrt(len(values)))))
    rows: list[list[Any]] = []
    for offset in range(0, len(values), width):
        row = list(values[offset : offset + width])
        if len(row) < width:
            row.extend([row[-1] if row else 0] * (width - len(row)))
        rows.append(row)
    if len(rows) == 1:
        rows.append(list(rows[0]))
    return rows


def _points_from_component_rows(rows: Sequence[Sequence[Any]]) -> list[list[Any]]:
    points: list[list[Any]] = []
    for index, row in enumerate(rows):
        values = list(row)
        if len(values) >= 3:
            points.append([values[0], values[1], values[2]])
        elif len(values) == 2:
            points.append([values[0], values[1], 0.0])
        elif len(values) == 1:
            points.append([float(index), values[0], 0.0])
    return points


def _mesh_points(mesh: Any | None) -> list[list[Any]]:
    if mesh is None:
        return []
    nodes = getattr(mesh, "nodes", None)
    coordinates_field = getattr(nodes, "coordinates_field", None)
    raw_coordinates = getattr(coordinates_field, "data", coordinates_field)
    rows = _as_plain(raw_coordinates)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return []
    points: list[list[Any]] = []
    for row in rows:
        if isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)) and len(row) >= 3:
            points.append([row[0], row[1], row[2]])
    return points


def _field_metadata(field: Any, *, source_ref: RuntimeHandleRef | None, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    metadata = copy.deepcopy(dict(source_ref.metadata if source_ref is not None else {}))
    metadata.update(copy.deepcopy(dict(extra or {})))
    scoping = getattr(field, "scoping", None)
    metadata.update(
        {
            "location": str(getattr(field, "location", metadata.get("location", "")) or ""),
            "component_count": int(getattr(field, "component_count", metadata.get("component_count", 0)) or 0),
            "entity_count": int(getattr(scoping, "size", metadata.get("entity_count", 0)) or 0),
            "unit": str(getattr(field, "unit", metadata.get("unit", "")) or ""),
        }
    )
    if source_ref is not None:
        metadata["source_handle_id"] = source_ref.handle_id
        metadata["source_handle_kind"] = source_ref.kind
    return metadata


def _series_label(metadata: Mapping[str, Any], fallback: str) -> str:
    result_name = str(metadata.get("result_name", "") or "").strip()
    operation = str(metadata.get("operation", "") or "").strip()
    label_parts = [part for part in (result_name, operation) if part]
    label_space = metadata.get("label_space")
    entity_id = label_space.get("entity") if isinstance(label_space, Mapping) else None
    if entity_id is not None:
        label_parts.append(f"entity {entity_id}")
    else:
        set_id = metadata.get("set_id")
        if set_id is not None:
            label_parts.append(f"set {set_id}")
    return " ".join(label_parts) if label_parts else fallback


def _series_from_field(
    field: Any,
    *,
    definition: DpfPlotNodeDefinition,
    source_ref: RuntimeHandleRef | None,
    metadata: Mapping[str, Any] | None = None,
    mesh: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    field_metadata = _field_metadata(field, source_ref=source_ref, extra=metadata)
    scalar_values = _field_scalar_values(field)
    x_values = _field_x_values(field, scalar_values, field_metadata)
    label = _series_label(field_metadata, definition.display_name)
    series: dict[str, Any] = {
        "label": label,
        "x": x_values,
        "y": scalar_values,
        "values": scalar_values,
        "metadata": copy.deepcopy(field_metadata),
    }
    if definition.plot_type in {PLOT_TYPE_HEATMAP, PLOT_TYPE_CONTOUR, PLOT_TYPE_SURFACE}:
        grid_values = _grid_from_values(scalar_values)
        series.update({"values": grid_values, "z": grid_values})
    elif definition.plot_type == PLOT_TYPE_POINT_CLOUD:
        points = _mesh_points(mesh) or _points_from_component_rows(_field_component_rows(field))
        if points:
            series.update({"points": points, "scalars": scalar_values})
    elif definition.plot_type == PLOT_TYPE_STREAMLINES:
        points = _points_from_component_rows(_field_component_rows(field))
        if len(points) < 2:
            points = [[x_value, y_value, 0.0] for x_value, y_value in zip(x_values, scalar_values)]
        series.update({"points": points})
    return series, field_metadata


def _label_spaces(fields_container: Any) -> tuple[dict[str, Any], ...]:
    spaces: list[dict[str, Any]] = []
    for index in range(len(fields_container)):
        try:
            label_space = fields_container.get_label_space(index)
        except Exception:
            label_space = {}
        spaces.append(dict(label_space or {}))
    return tuple(spaces)


def _resolve_runtime_ref(
    ctx: ExecutionContext,
    value: Any,
    *,
    expected_data_type: str,
    expected_kind: str,
) -> tuple[RuntimeHandleRef | None, Any]:
    runtime_ref = ctx.runtime_handle_ref(value)
    if runtime_ref is None:
        return None, value
    return runtime_ref, ctx.resolve_handle(
        runtime_ref,
        expected_data_type=expected_data_type,
        expected_kind=expected_kind,
    )


def _resolve_mesh(ctx: ExecutionContext, value: Any) -> tuple[RuntimeHandleRef | None, Any | None]:
    if value is None:
        return None, None
    runtime_ref = ctx.runtime_handle_ref(value)
    if runtime_ref is None:
        return None, value
    if (
        runtime_ref.data_type_id != DPF_MESH_DATA_TYPE
        or runtime_ref.kind != DPF_MESH_HANDLE_KIND
    ):
        raise TypeError("DPF plot mesh input requires a dpf.mesh handle.")
    return runtime_ref, ctx.resolve_handle(
        runtime_ref,
        expected_data_type=DPF_MESH_DATA_TYPE,
        expected_kind=DPF_MESH_HANDLE_KIND,
    )


def _resolve_scoping_summary(ctx: ExecutionContext, value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    runtime_ref = ctx.runtime_handle_ref(value)
    if runtime_ref is None:
        scoping = value
        return {
            "ids": _scoping_ids(scoping),
            "location": str(getattr(scoping, "location", "") or ""),
        }
    if (
        runtime_ref.data_type_id != DPF_SCOPING_DATA_TYPE
        or runtime_ref.kind
        not in {DPF_MESH_SCOPING_HANDLE_KIND, DPF_TIME_SCOPING_HANDLE_KIND}
    ):
        raise TypeError("DPF plot scoping input requires a DPF scoping handle.")
    scoping = ctx.resolve_handle(
        runtime_ref,
        expected_data_type=DPF_SCOPING_DATA_TYPE,
        expected_kind=runtime_ref.kind,
    )
    return {
        "handle_id": runtime_ref.handle_id,
        "handle_kind": runtime_ref.kind,
        "ids": _scoping_ids(scoping) or list(runtime_ref.metadata.get("ids", ())),
        "location": str(getattr(scoping, "location", runtime_ref.metadata.get("location", "")) or ""),
        "metadata": copy.deepcopy(dict(runtime_ref.metadata)),
    }


def _mesh_summary(mesh_ref: RuntimeHandleRef | None, mesh: Any | None) -> dict[str, Any]:
    if mesh is None:
        return {}
    nodes = getattr(mesh, "nodes", None)
    elements = getattr(mesh, "elements", None)
    summary = {
        "node_count": int(getattr(nodes, "n_nodes", 0) or 0),
        "element_count": int(getattr(elements, "n_elements", 0) or 0),
        "unit": str(getattr(mesh, "unit", "") or ""),
    }
    if mesh_ref is not None:
        summary["handle_id"] = mesh_ref.handle_id
        summary["metadata"] = copy.deepcopy(dict(mesh_ref.metadata))
    return summary


def _adapt_dpf_series(
    ctx: ExecutionContext,
    *,
    definition: DpfPlotNodeDefinition,
    properties: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    from ea_node_editor.execution.plot_backend import normalize_dpf_plot_frame_selector

    mesh_ref, mesh = _resolve_mesh(ctx, ctx.inputs.get("mesh"))
    scoping_summary = _resolve_scoping_summary(ctx, ctx.inputs.get("scoping"))
    animate = bool(properties.get(DPF_PLOT_ANIMATE_PROPERTY, False))
    frame_selector = properties.get(DPF_PLOT_FRAME_SELECTOR_PROPERTY)
    series: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    animation_frames: list[dict[str, Any]] = []

    for source_index, raw_value in enumerate(_input_items(ctx.inputs.get("series"))):
        runtime_ref = ctx.runtime_handle_ref(raw_value)
        if runtime_ref is not None:
            if (
                runtime_ref.data_type_id == DPF_FIELD_DATA_TYPE
                and runtime_ref.kind == DPF_FIELD_HANDLE_KIND
            ):
                field_ref, field = _resolve_runtime_ref(
                    ctx,
                    raw_value,
                    expected_data_type=DPF_FIELD_DATA_TYPE,
                    expected_kind=DPF_FIELD_HANDLE_KIND,
                )
                item_series, item_metadata = _series_from_field(
                    field,
                    definition=definition,
                    source_ref=field_ref,
                    metadata={"series_index": source_index},
                    mesh=mesh,
                )
                series.append(item_series)
                sources.append(item_metadata)
                continue
            if (
                runtime_ref.data_type_id == DPF_FIELDS_CONTAINER_DATA_TYPE
                and runtime_ref.kind == DPF_FIELDS_CONTAINER_HANDLE_KIND
            ):
                container_ref, fields_container = _resolve_runtime_ref(
                    ctx,
                    raw_value,
                    expected_data_type=DPF_FIELDS_CONTAINER_DATA_TYPE,
                    expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                )
                spaces = _label_spaces(fields_container)
                selection = normalize_dpf_plot_frame_selector(
                    frame_selector,
                    frame_count=len(fields_container),
                    label_spaces=spaces,
                )
                for frame_index in range(len(fields_container)):
                    frame_metadata = {
                        "frame_index": frame_index,
                        "set_id": selection.available_set_ids[frame_index],
                        "label_space": copy.deepcopy(spaces[frame_index]),
                    }
                    animation_frames.append(frame_metadata)
                for frame_index in selection.selected_indices:
                    label_space = copy.deepcopy(spaces[frame_index])
                    set_id = selection.available_set_ids[frame_index]
                    item_series, item_metadata = _series_from_field(
                        fields_container[frame_index],
                        definition=definition,
                        source_ref=container_ref,
                        metadata={
                            "series_index": source_index,
                            "frame_index": frame_index,
                            "set_id": set_id,
                            "set_ids": [set_id],
                            "label_space": label_space,
                        },
                        mesh=mesh,
                    )
                    series.append(item_series)
                    sources.append(item_metadata)
                continue
            raise TypeError(
                "DPF plot series input requires dpf.field or dpf.fields_container handles."
            )

        if hasattr(raw_value, "get_label_space") and hasattr(raw_value, "__len__"):
            spaces = _label_spaces(raw_value)
            selection = normalize_dpf_plot_frame_selector(
                frame_selector,
                frame_count=len(raw_value),
                label_spaces=spaces,
            )
            animation_frames.extend(
                {
                    "frame_index": frame_index,
                    "set_id": selection.available_set_ids[frame_index],
                    "label_space": copy.deepcopy(spaces[frame_index]),
                }
                for frame_index in range(len(raw_value))
            )
            for frame_index in selection.selected_indices:
                item_series, item_metadata = _series_from_field(
                    raw_value[frame_index],
                    definition=definition,
                    source_ref=None,
                    metadata={
                        "series_index": source_index,
                        "frame_index": frame_index,
                        "set_id": selection.available_set_ids[frame_index],
                        "set_ids": [selection.available_set_ids[frame_index]],
                        "label_space": copy.deepcopy(spaces[frame_index]),
                    },
                    mesh=mesh,
                )
                series.append(item_series)
                sources.append(item_metadata)
            continue

        if hasattr(raw_value, "component_count") and hasattr(raw_value, "scoping"):
            item_series, item_metadata = _series_from_field(
                raw_value,
                definition=definition,
                source_ref=None,
                metadata={"series_index": source_index},
                mesh=mesh,
            )
            series.append(item_series)
            sources.append(item_metadata)
            continue

        raise TypeError("DPF plot series input requires a DPF field or fields container.")

    dpf_metadata = {
        "family": "dpf.plot",
        "frame_selector": str(frame_selector or DPF_PLOT_FRAME_SELECTOR_DEFAULT).strip(),
        "animate": animate,
        "selected_frame_count": len(series),
        "sources": sources,
        "mesh": _mesh_summary(mesh_ref, mesh),
        "scoping": scoping_summary,
        "animation": {
            "enabled": animate,
            "frames": animation_frames,
            "frame_count": len(animation_frames),
        },
    }
    return tuple(series), dpf_metadata


def _dpf_plot_options(
    definition: DpfPlotNodeDefinition,
    properties: Mapping[str, Any],
    dpf_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    options = _mapping_property(properties, "plot_options", {})
    options.update(
        {
            "axis_limits": _mapping_property(properties, "axis_limits", PLOT_AXIS_LIMITS_DEFAULT),
            "log_scales": _mapping_property(properties, "log_scales", PLOT_LOG_SCALES_DEFAULT),
            "grid": bool(properties.get("grid", True)),
            "legend": bool(properties.get("legend", True)),
            "render_in_canvas": bool(properties.get("render_in_canvas", False)),
            "z_label": _string_property(properties, "z_label"),
            "dpf": copy.deepcopy(dict(dpf_metadata)),
            "frame_selector": str(
                properties.get(DPF_PLOT_FRAME_SELECTOR_PROPERTY, DPF_PLOT_FRAME_SELECTOR_DEFAULT)
                or DPF_PLOT_FRAME_SELECTOR_DEFAULT
            ).strip(),
            "animate": bool(properties.get(DPF_PLOT_ANIMATE_PROPERTY, False)),
        }
    )
    if definition.supports_colormap:
        options["cmap"] = _string_property(properties, "colormap") or "viridis"
    return options


def _default_backend_per_type(definition: DpfPlotNodeDefinition) -> dict[str, str]:
    return {
        "default": MATPLOTLIB_PLOT_BACKEND_ID,
        definition.plot_type: MATPLOTLIB_PLOT_BACKEND_ID,
    }


class DpfPlotNodePlugin:
    def __init__(self, definition: DpfPlotNodeDefinition) -> None:
        self._definition = definition
        self._spec = _dpf_plot_node_spec(definition)

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def _build_render_request(
        self, ctx: ExecutionContext
    ) -> tuple[PlotRenderRequest, Mapping[str, Any]]:
        from ea_node_editor.execution.plot_backend import build_plot_render_request

        properties = _property_defaults(self._spec)
        properties.update(dict(ctx.properties or {}))
        series, dpf_metadata = _adapt_dpf_series(
            ctx,
            definition=self._definition,
            properties=properties,
        )
        render_request = build_plot_render_request(
            plot_type=self._definition.plot_type,
            series=series,
            properties=properties,
            options=_dpf_plot_options(self._definition, properties, dpf_metadata),
        )
        return render_request, properties

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        render_request, properties = self._build_render_request(ctx)
        outputs: dict[str, Any] = {}
        if bool(properties.get("archive_export_on_run", False)):
            outputs.update(self._archive_exports(ctx, render_request, properties))
        return NodeResult(outputs=outputs)

    def _archive_exports(
        self,
        ctx: ExecutionContext,
        render_request: PlotRenderRequest,
        properties: Mapping[str, Any],
    ) -> dict[str, Any]:
        from ea_node_editor.execution.plot_backend import (
            PlotDataExportRequest,
            PlotStaticExportRequest,
            create_plot_backend_registry,
        )

        backend_id = _string_property(properties, "backend") or AUTO_PLOT_BACKEND_ID
        registry = create_plot_backend_registry()
        default_backend_per_type = _default_backend_per_type(self._definition)
        static_backend = registry.resolve(
            backend_id,
            plot_type=self._definition.plot_type,
            surface=PLOT_SURFACE_STATIC_EXPORT,
            plot_default_backend_per_type=default_backend_per_type,
            require_headless_safe=True,
        )
        data_backend = registry.resolve(
            backend_id,
            plot_type=self._definition.plot_type,
            surface=PLOT_SURFACE_DATA_EXPORT,
            plot_default_backend_per_type=default_backend_per_type,
            require_headless_safe=True,
        )

        static_format = _export_format(properties, "static_export_format", "png")
        data_format = _export_format(properties, "data_export_format", "csv")
        static_result: PlotExportResult | None = None
        data_result: PlotExportResult | None = None

        def write_static(output_path):
            nonlocal static_result
            static_result = static_backend.export_static(
                PlotStaticExportRequest(
                    render_request=render_request,
                    output_path=output_path,
                    format=static_format,
                )
            )

        def write_data(output_path):
            nonlocal data_result
            data_result = data_backend.export_data(
                PlotDataExportRequest(
                    render_request=render_request,
                    output_path=output_path,
                    format=data_format,
                )
            )

        store = artifact_store_for_context(ctx)
        touched_relative_paths: list[str] = []
        registered_ids: list[str] = []
        try:
            static_target = allocate_managed_output(
                ctx,
                output_key="static_export",
                default_suffix=f".{static_format}",
                managed_subdirectory="plots",
            )
            touched_relative_paths.append(static_target.relative_path)
            write_static(static_target.path)
            registered_ids.append(static_target.artifact_id)
            static_ref = register_staged_path_artifact(
                ctx,
                store=store,
                artifact_id=static_target.artifact_id,
                payload_path=static_target.path,
                relative_path=static_target.relative_path,
                slot=static_target.slot,
                format=static_target.format,
                entry_metadata=static_target.entry_metadata,
            )

            data_target = allocate_managed_output(
                ctx,
                output_key="data_export",
                default_suffix=f".{data_format}",
                managed_subdirectory="plots",
            )
            touched_relative_paths.append(data_target.relative_path)
            write_data(data_target.path)
            registered_ids.append(data_target.artifact_id)
            data_ref = register_staged_path_artifact(
                ctx,
                store=store,
                artifact_id=data_target.artifact_id,
                payload_path=data_target.path,
                relative_path=data_target.relative_path,
                slot=data_target.slot,
                format=data_target.format,
                entry_metadata=data_target.entry_metadata,
            )
            persist_artifact_store(ctx, store)
        except BaseException:
            try:
                store.discard_staged_entries(registered_ids)
            except BaseException:
                pass
            try:
                store.discard_staged_paths(touched_relative_paths)
            except BaseException:
                pass
            try:
                persist_artifact_store(ctx, store)
            except BaseException:
                pass
            raise
        return {
            "static_export": static_ref,
            "data_export": data_ref,
            "exports": {
                "static_export": static_ref,
                "data_export": data_ref,
                "static_metadata": _runtime_artifact_metadata(static_result),
                "data_metadata": _runtime_artifact_metadata(data_result),
            },
        }


def _dpf_plot_descriptor(definition: DpfPlotNodeDefinition) -> PluginDescriptor:
    return PluginDescriptor(
        spec=_dpf_plot_node_spec(definition),
        factory=lambda definition=definition: DpfPlotNodePlugin(definition),
    )


DPF_PLOT_NODE_DESCRIPTORS = tuple(
    _dpf_plot_descriptor(definition) for definition in DPF_PLOT_NODE_DEFINITIONS
)

__all__ = [
    "DPF_PLOT_ANIMATE_PROPERTY",
    "DPF_PLOT_CATEGORY_PATH",
    "DPF_PLOT_FRAME_SELECTOR_PROPERTY",
    "DPF_PLOT_NODE_DEFINITIONS",
    "DPF_PLOT_NODE_DESCRIPTORS",
    "DPF_PLOT_NODE_TYPE_IDS",
    "DPF_PLOT_RUNTIME_SHAPE_TEXT",
    "DpfPlotNodeDefinition",
    "DpfPlotNodePlugin",
]
