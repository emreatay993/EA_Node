from __future__ import annotations

from ea_node_editor.ui.shell.window_actions import (
    format_recent_project_menu_label as format_recent_project_menu_label_value,
)
from ea_node_editor.ui.shell.window_state import context_properties as _context_properties
from ea_node_editor.ui.shell.window_state import library_and_overlay_state as _library_and_overlay_state
from ea_node_editor.ui.shell.window_state import project_session_actions as _project_session_actions
from ea_node_editor.ui.shell.window_state import run_and_style_state as _run_and_style_state
from ea_node_editor.ui.shell.window_state import workspace_graph_actions as _workspace_graph_actions

_WINDOW_STATE_MODULES = (
    _context_properties,
    _library_and_overlay_state,
    _workspace_graph_actions,
    _project_session_actions,
    _run_and_style_state,
)
for _window_state_module in _WINDOW_STATE_MODULES:
    globals().update(
        {
            name: getattr(_window_state_module, name)
            for name in getattr(_window_state_module, "__all__", ())
        }
    )

SHELL_WINDOW_FACADE_BINDINGS = {}
for _window_state_module in _WINDOW_STATE_MODULES:
    SHELL_WINDOW_FACADE_BINDINGS.update(_window_state_module.WINDOW_STATE_FACADE_BINDINGS)
SHELL_WINDOW_FACADE_BINDINGS["_format_recent_project_menu_label"] = staticmethod(
    format_recent_project_menu_label_value
)

__all__ = [
    "SHELL_WINDOW_FACADE_BINDINGS",
    "project_path",
    "recent_project_paths",
    "_library_query",
    "_library_category",
    "_library_data_type",
    "_library_direction",
    "_active_run_id",
    "_active_run_workspace_id",
    "_engine_state_value",
    "_last_manual_save_ts",
    "_last_autosave_fingerprint",
    "_autosave_recovery_deferred",
    "_qt_project_display_name",
    "_qt_filtered_node_library_items",
    "_qt_grouped_node_library_items",
    "_qt_library_category_options",
    "_qt_library_direction_options",
    "_qt_library_data_type_options",
    "_qt_pin_data_type_options",
    "_qt_graph_search_open",
    "_qt_graph_search_query",
    "_qt_graph_search_enabled_scopes",
    "_qt_graph_search_results",
    "_qt_graph_search_highlight_index",
    "_qt_connection_quick_insert_open",
    "_qt_connection_quick_insert_query",
    "_qt_connection_quick_insert_results",
    "_qt_connection_quick_insert_highlight_index",
    "_qt_connection_quick_insert_overlay_x",
    "_qt_connection_quick_insert_overlay_y",
    "_qt_connection_quick_insert_source_summary",
    "_qt_connection_quick_insert_is_canvas_mode",
    "_qt_graph_hint_message",
    "_qt_graph_hint_visible",
    "_qt_graphics_show_grid",
    "_qt_graphics_grid_style",
    "_qt_graphics_edge_crossing_style",
    "_qt_graphics_show_minimap",
    "_qt_graphics_show_port_labels",
    "_qt_graphics_show_tooltips",
    "_qt_graphics_minimap_expanded",
    "_qt_graphics_node_shadow",
    "_qt_graphics_shadow_strength",
    "_qt_graphics_shadow_softness",
    "_qt_graphics_shadow_offset",
    "_qt_graphics_performance_mode",
    "_qt_graphics_floating_toolbar_style",
    "_qt_graphics_tab_strip_density",
    "_qt_active_theme_id",
    "_qt_snap_to_grid_enabled",
    "_qt_snap_grid_size",
    "_qt_active_workspace_id",
    "_qt_active_workspace_name",
    "_qt_active_view_name",
    "_qt_active_view_items",
    "_qt_active_scope_breadcrumb_items",
    "_qt_selected_node_title",
    "_qt_selected_node_subtitle",
    "_qt_selected_node_header_items",
    "_qt_selected_node_summary",
    "_qt_has_selected_node",
    "_qt_selected_node_collapsible",
    "_qt_selected_node_collapsed",
    "_qt_selected_node_is_subnode_pin",
    "_qt_selected_node_is_subnode_shell",
    "_qt_can_publish_custom_workflow_from_scope",
    "_qt_selected_node_property_items",
    "_qt_selected_node_port_items",
]
