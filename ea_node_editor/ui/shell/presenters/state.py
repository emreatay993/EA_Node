from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ea_node_editor.app_preferences import (
    effective_graph_node_icon_pixel_size,
    normalize_edge_crossing_style,
    normalize_floating_toolbar_size,
    normalize_floating_toolbar_style,
    normalize_graph_label_pixel_size,
    normalize_graph_node_icon_pixel_size_override,
    normalize_graphics_performance_mode,
    normalize_grid_overlay_style,
)
from ea_node_editor.graph.effective_ports import find_port
from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.shell.window_library_inspector import (
    build_canvas_quick_insert_items,
    build_connection_quick_insert_items,
)

UNSET = object()


@dataclass(slots=True)
class ShellWorkspaceUiState:
    show_grid: bool
    grid_style: str
    edge_crossing_style: str
    floating_toolbar_style: str
    floating_toolbar_size: str
    graph_label_pixel_size: int
    graph_node_icon_pixel_size_override: int | None
    node_title_icon_pixel_size: int
    show_minimap: bool
    show_port_labels: bool
    node_shadow: bool
    shadow_strength: int
    shadow_softness: int
    shadow_offset: int
    graphics_performance_mode: str
    tab_strip_density: str
    graphics_show_tooltips: bool
    active_theme_id: str


def build_default_shell_workspace_ui_state(
    graphics_settings: Any = DEFAULT_GRAPHICS_SETTINGS,
) -> ShellWorkspaceUiState:
    canvas = graphics_settings.get("canvas", {}) if isinstance(graphics_settings, dict) else {}
    shell = graphics_settings.get("shell", {}) if isinstance(graphics_settings, dict) else {}
    performance = graphics_settings.get("performance", {}) if isinstance(graphics_settings, dict) else {}
    theme = graphics_settings.get("theme", {}) if isinstance(graphics_settings, dict) else {}
    typography = graphics_settings.get("typography", {}) if isinstance(graphics_settings, dict) else {}
    show_tooltips = shell.get("show_tooltips", DEFAULT_GRAPHICS_SETTINGS["shell"]["show_tooltips"])
    if not isinstance(show_tooltips, bool):
        show_tooltips = DEFAULT_GRAPHICS_SETTINGS["shell"]["show_tooltips"]
    graph_label_pixel_size = normalize_graph_label_pixel_size(
        typography.get("graph_label_pixel_size", DEFAULT_GRAPHICS_SETTINGS["typography"]["graph_label_pixel_size"])
    )
    graph_node_icon_pixel_size_override = normalize_graph_node_icon_pixel_size_override(
        typography.get("graph_node_icon_pixel_size_override")
    )
    return ShellWorkspaceUiState(
        show_grid=bool(canvas.get("show_grid", DEFAULT_GRAPHICS_SETTINGS["canvas"]["show_grid"])),
        grid_style=normalize_grid_overlay_style(
            canvas.get("grid_style", DEFAULT_GRAPHICS_SETTINGS["canvas"]["grid_style"])
        ),
        edge_crossing_style=normalize_edge_crossing_style(
            canvas.get("edge_crossing_style", DEFAULT_GRAPHICS_SETTINGS["canvas"]["edge_crossing_style"])
        ),
        floating_toolbar_style=normalize_floating_toolbar_style(
            canvas.get(
                "floating_toolbar_style",
                DEFAULT_GRAPHICS_SETTINGS["canvas"]["floating_toolbar_style"],
            )
        ),
        floating_toolbar_size=normalize_floating_toolbar_size(
            canvas.get(
                "floating_toolbar_size",
                DEFAULT_GRAPHICS_SETTINGS["canvas"]["floating_toolbar_size"],
            )
        ),
        graph_label_pixel_size=graph_label_pixel_size,
        graph_node_icon_pixel_size_override=graph_node_icon_pixel_size_override,
        node_title_icon_pixel_size=effective_graph_node_icon_pixel_size(
            graph_label_pixel_size,
            graph_node_icon_pixel_size_override,
        ),
        show_minimap=bool(canvas.get("show_minimap", DEFAULT_GRAPHICS_SETTINGS["canvas"]["show_minimap"])),
        show_port_labels=bool(
            canvas.get("show_port_labels", DEFAULT_GRAPHICS_SETTINGS["canvas"]["show_port_labels"])
        ),
        node_shadow=bool(canvas.get("node_shadow", DEFAULT_GRAPHICS_SETTINGS["canvas"]["node_shadow"])),
        shadow_strength=int(canvas.get("shadow_strength", DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_strength"])),
        shadow_softness=int(canvas.get("shadow_softness", DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_softness"])),
        shadow_offset=int(canvas.get("shadow_offset", DEFAULT_GRAPHICS_SETTINGS["canvas"]["shadow_offset"])),
        graphics_performance_mode=normalize_graphics_performance_mode(
            performance.get("mode", DEFAULT_GRAPHICS_SETTINGS["performance"]["mode"])
        ),
        tab_strip_density=str(
            shell.get("tab_strip_density", DEFAULT_GRAPHICS_SETTINGS["shell"]["tab_strip_density"])
        ),
        graphics_show_tooltips=show_tooltips,
        active_theme_id=str(theme.get("theme_id", DEFAULT_GRAPHICS_SETTINGS["theme"]["theme_id"])),
    )


def connection_quick_insert_overlay_coordinate(context: dict[str, Any] | None, key: str) -> float:
    return float((context or {}).get(key, 0.0))


def connection_quick_insert_source_summary(context: dict[str, Any] | None) -> str:
    context = context or {}
    node_title = str(context.get("node_title", "")).strip()
    port_label = str(context.get("port_label", "")).strip()
    data_type = str(context.get("data_type", "")).strip()
    if not node_title and not port_label:
        return ""
    summary = f"{node_title}.{port_label}" if node_title and port_label else (node_title or port_label)
    if data_type:
        summary += f" [{data_type}]"
    return summary


def connection_quick_insert_is_canvas_mode(context: dict[str, Any] | None) -> bool:
    return str((context or {}).get("mode", "")).strip() == "canvas_insert"


def update_connection_quick_insert_state(
    quick_insert: Any,
    *,
    open_: bool | None = None,
    query: str | None = None,
    results: list[dict[str, Any]] | None = None,
    highlight_index: int | None = None,
    context: dict[str, Any] | None | object = UNSET,
) -> bool:
    changed = False
    if open_ is not None:
        normalized_open = bool(open_)
        if normalized_open != quick_insert.open:
            quick_insert.open = normalized_open
            changed = True
    if query is not None:
        normalized_query = str(query)
        if normalized_query != quick_insert.query:
            quick_insert.query = normalized_query
            changed = True
    if results is not None:
        normalized_results = list(results)
        if normalized_results != quick_insert.results:
            quick_insert.results = normalized_results
            changed = True
    if highlight_index is not None:
        normalized_index = int(highlight_index)
        if normalized_index != quick_insert.highlight_index:
            quick_insert.highlight_index = normalized_index
            changed = True
    if context is not UNSET:
        normalized_context = dict(context) if isinstance(context, dict) else None
        if normalized_context != quick_insert.context:
            quick_insert.context = normalized_context
            changed = True
    return changed


def build_connection_quick_insert_context(host: Any, node_id: str, port_key: str) -> dict[str, Any] | None:
    workspace = host.model.project.workspaces.get(host.workspace_manager.active_workspace_id())
    if workspace is None:
        return None
    normalized_node_id = str(node_id).strip()
    normalized_port_key = str(port_key).strip()
    if not normalized_node_id or not normalized_port_key:
        return None
    node = workspace.nodes.get(normalized_node_id)
    if node is None:
        return None
    spec = host.registry.get_spec(node.type_id)
    port = find_port(
        node=node,
        spec=spec,
        workspace_nodes=workspace.nodes,
        port_key=normalized_port_key,
    )
    if port is None or not bool(port.exposed):
        return None
    connection_count = 0
    for edge in workspace.edges.values():
        if edge.source_node_id == normalized_node_id and edge.source_port_key == normalized_port_key:
            connection_count += 1
        if edge.target_node_id == normalized_node_id and edge.target_port_key == normalized_port_key:
            connection_count += 1
    return {
        "node_id": normalized_node_id,
        "node_title": str(node.title),
        "type_id": str(node.type_id),
        "port_key": normalized_port_key,
        "port_label": str(port.label or port.key),
        "direction": str(port.direction),
        "kind": str(port.kind),
        "data_type": str(port.data_type),
        "connection_count": int(connection_count),
    }


def build_connection_quick_insert_results(
    host: Any,
    combined_items: list[dict[str, Any]],
    query: str,
    quick_insert: Any,
) -> tuple[list[dict[str, Any]], int]:
    context = quick_insert.context
    if context is None:
        return [], -1
    normalized_query = str(query)
    results: list[dict[str, Any]] = []
    if connection_quick_insert_is_canvas_mode(context):
        results = build_canvas_quick_insert_items(
            combined_items=combined_items,
            query=normalized_query,
            limit=host._CONNECTION_QUICK_INSERT_LIMIT,
        )
    elif not (
        str(context.get("direction", "")).strip().lower() == "in"
        and int(context.get("connection_count", 0)) > 0
    ):
        results = build_connection_quick_insert_items(
            combined_items=combined_items,
            query=normalized_query,
            source_direction=str(context.get("direction", "")),
            source_kind=str(context.get("kind", "")),
            source_data_type=str(context.get("data_type", "")),
            limit=host._CONNECTION_QUICK_INSERT_LIMIT,
        )
    highlight_index = 0 if results else -1
    if 0 <= quick_insert.highlight_index < len(results):
        highlight_index = quick_insert.highlight_index
    return results, highlight_index
