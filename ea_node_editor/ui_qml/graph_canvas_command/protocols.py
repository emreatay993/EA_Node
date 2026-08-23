from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol



if TYPE_CHECKING:
    pass

class _GraphCanvasCommandSource(Protocol):
    def trigger_node(self, node_id: str) -> bool: ...

    def set_snap_to_grid_enabled(self, enabled: bool) -> None: ...

    def set_graphics_minimap_expanded(self, expanded: bool) -> None: ...

    def set_graphics_show_grid(self, show_grid: bool) -> None: ...

    def set_graphics_canvas_background_variant(self, variant: str) -> None: ...

    def set_graphics_grid_style(self, style: str) -> None: ...

    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None: ...

    def set_graphics_node_elapsed_time_unit(self, unit: str) -> None: ...
    def set_graphics_node_elapsed_time_visibility(self, visibility: str) -> None: ...
    def set_graphics_node_comment_editor_default(self, value: str) -> None: ...

    def set_selected_run_preview_before_run(self, enabled: bool) -> None: ...

    def set_graphics_node_shadow(self, enabled: bool) -> None: ...

    def set_graphics_floating_toolbar_style(self, style: str) -> None: ...

    def set_graphics_floating_toolbar_size(self, size: str) -> None: ...

    def set_graphics_selection_toolbar_mode(self, mode: str) -> None: ...

    def set_graphics_selection_toolbar_minimal_menu_trigger(self, trigger: str) -> None: ...

    def set_folder_explorer_column_widths(self, widths: dict[str, object]) -> None: ...

    def record_recent_text_color(self, color: str) -> None: ...

    def set_graphics_shell_theme(self, theme_id: str) -> None: ...

    def set_graphics_graph_follow_shell_theme(self, follow_shell_theme: bool) -> None: ...

    def set_graphics_graph_theme(self, theme_id: str) -> None: ...

    def upsert_node_comment(
        self,
        node_id: str,
        comment_id: str,
        body: str,
        author: str = "",
        parent_id: str = "",
        resolved: bool = False,
        unread: bool = True,
        pinned: bool = False,
    ) -> str: ...

    def remove_node_comment(self, node_id: str, comment_id: str) -> bool: ...
    def set_node_comment_resolved(self, node_id: str, comment_id: str, resolved: bool) -> bool: ...
    def set_node_comment_pinned(self, node_id: str, comment_id: str, pinned: bool) -> bool: ...
    def resolve_all_node_comments(self, node_id: str) -> bool: ...
    def mark_node_comments_read(self, node_id: str) -> bool: ...

    def request_open_graphics_settings(self) -> None: ...

    def request_open_subnode_scope(self, node_id: str) -> bool: ...

    def browse_node_property_path(self, node_id: str, key: str, current_path: str, source_mode: str = "") -> str: ...

    def internalize_node_property_path(self, node_id: str, key: str, current_path: str) -> str: ...

    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str: ...

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> bool: ...

    def request_drop_node_from_library_with_properties(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        properties: dict[str, Any],
    ) -> bool: ...

    def video_frame_capture_path(self, video_node_id: str, position_ms: int) -> str: ...

    def request_save_image_crop_replace(
        self,
        image_node_id: str,
        crop_rect: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def request_create_video_frame_image_node(
        self,
        video_node_id: str,
        frame_path: str,
        position_ms: int,
        scene_x: float,
        scene_y: float,
        capture_width: float,
        capture_height: float,
    ) -> dict[str, Any]: ...

    def request_create_video_timestamp_annotation(
        self,
        video_node_id: str,
        position_ms: int,
        scene_x: float,
        scene_y: float,
    ) -> dict[str, Any]: ...

    def request_trim_video_clip_replace(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def request_trim_video_clip_copy(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        scene_x: float,
        scene_y: float,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        append_requested: bool = False,
    ) -> bool: ...

    def request_rewire_edges(
        self,
        edge_ids: list[object],
        endpoint: str,
        node_id: str,
        port_key: str,
        copy_requested: bool = False,
        append_requested: bool = False,
    ) -> bool: ...

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        cursor_scene_x: float,
        cursor_scene_y: float,
        overlay_x: float,
        overlay_y: float,
        append_requested: bool = False,
    ) -> bool: ...

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None: ...

class _GraphCanvasHostSource(Protocol):
    def request_delete_selected_graph_items(self, edge_ids: list[object]) -> bool: ...

    def request_navigate_scope_parent(self) -> bool: ...

    def request_navigate_scope_root(self) -> bool: ...

    def set_graph_cursor_shape(self, cursor_shape: int) -> None: ...

    def clear_graph_cursor_shape(self) -> None: ...

    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]: ...

    def describe_image_preview(self, source: str) -> dict[str, Any]: ...

    def describe_mail_preview(self, source: str) -> dict[str, Any]: ...

    def open_local_file_source(self, source: str, chooser: bool = False) -> dict[str, Any]: ...

    def describe_tabular_preview(
        self,
        properties_or_source: dict[str, Any] | str,
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def resolve_local_file_source_url(self, source: str) -> str: ...

class _GraphCanvasSceneCommandSource(Protocol):
    def select_node(self, node_id: str, additive: bool = False) -> None: ...

    def clear_selection(self) -> None: ...

    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None: ...

    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None: ...

    def set_node_property(self, node_id: str, key: str, value: object) -> None: ...

    def set_pending_surface_action(self, node_id: str) -> None: ...

    def consume_pending_surface_action(self, node_id: str) -> bool: ...

    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool: ...

    def set_node_settings_group_expanded(
        self,
        node_id: str,
        group_id: str,
        expanded: bool,
    ) -> bool: ...

    def parameter_setup_link_options(
        self, pool_node_id: str
    ) -> list[dict[str, Any]]: ...

    def parameter_setup_link_status(self, pool_node_id: str) -> dict[str, Any]: ...

    def link_parameter_setup(self, pool_node_id: str, setup_node_id: str) -> bool: ...

    def unlink_parameter_setup(self, pool_node_id: str) -> bool: ...

    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str: ...

    def add_path_pointer_node(self, path: str, mode: str, x: float = 0.0, y: float = 0.0) -> str: ...

    def add_folder_explorer_node(self, current_path: str, x: float = 0.0, y: float = 0.0) -> str: ...

    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool: ...

    def move_node(self, node_id: str, x: float, y: float) -> None: ...

    def resize_node(self, node_id: str, width: float, height: float) -> None: ...

    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None: ...

    def set_edge_enabled(self, edge_id: str, enabled: bool) -> bool: ...

    def set_edges_enabled(self, edge_ids: list[Any], enabled: bool) -> bool: ...

    def set_edges_display_mode(self, edge_ids: list[Any], mode: str) -> bool: ...

    def set_port_modifiers(
        self,
        node_id: str,
        port_key: str,
        modifiers: list[Any],
    ) -> bool: ...

    def set_principal_input_port(self, node_id: str, port_key: str) -> bool: ...

    def insert_dynamic_port(
        self,
        node_id: str,
        group_id: str,
        ordinal: int,
    ) -> str: ...

    def remove_dynamic_port(
        self,
        node_id: str,
        group_id: str,
        port_key: str,
    ) -> dict[str, Any]: ...

    def rename_dynamic_port(
        self,
        node_id: str,
        group_id: str,
        port_key: str,
        value: str,
    ) -> dict[str, Any]: ...

    def normalize_edge_label(self, label: Any) -> str: ...

    def set_edge_label(self, edge_id: str, label: Any) -> None: ...

    def clear_edge_label(self, edge_id: str) -> None: ...

    def normalize_edge_visual_style(self, visual_style: Any) -> dict[str, Any]: ...

    def set_edge_visual_style(self, edge_id: str, visual_style: Any) -> None: ...

    def clear_edge_visual_style(self, edge_id: str) -> None: ...

class _GraphCanvasScenePolicySource(Protocol):
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool: ...

    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool: ...
