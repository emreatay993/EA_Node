from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.app_preferences import (
    effective_graph_node_icon_pixel_size,
    normalize_edge_crossing_style,
    normalize_expand_collision_avoidance_settings,
    normalize_floating_toolbar_size,
    normalize_floating_toolbar_style,
    normalize_graph_label_pixel_size,
    normalize_graph_node_icon_pixel_size_override,
    normalize_graphics_performance_mode,
    normalize_grid_overlay_style,
    normalize_property_pane_variant,
)
from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.shell.run_flow import (
    SelectedWorkspaceRunControlState,
    selected_workspace_run_control_state,
)
from ea_node_editor.ui.graph_theme import resolve_graph_theme_id, serialize_custom_graph_themes

from .contracts import _ShellWorkspacePresenterHostProtocol, _presenter_parent
from .state import ShellWorkspaceUiState


class ShellWorkspacePresenter(QObject):
    project_meta_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    graphics_preferences_changed = pyqtSignal()
    run_controls_changed = pyqtSignal()

    def __init__(
        self,
        host: _ShellWorkspacePresenterHostProtocol,
        *,
        parent: QObject | None = None,
        ui_state: ShellWorkspaceUiState | None = None,
    ) -> None:
        super().__init__(_presenter_parent(host, parent))
        self._host = host
        self._ui_state = ui_state if ui_state is not None else host.workspace_ui_state
        self._expand_collision_avoidance = normalize_expand_collision_avoidance_settings(
            DEFAULT_GRAPHICS_SETTINGS["interaction"]["expand_collision_avoidance"]
        )
        host.project_meta_changed.connect(self.project_meta_changed.emit)
        host.workspace_state_changed.connect(self.workspace_state_changed.emit)
        host.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)
        host.run_controls_changed.connect(self.run_controls_changed.emit)

    @property
    def project_display_name(self) -> str:
        filename = Path(self._host.project_path).name if self._host.project_path else "untitled.sfe"
        return f"COREX Node Editor - {filename}"

    @property
    def graphics_tab_strip_density(self) -> str: return str(self._ui_state.tab_strip_density)

    @property
    def graphics_show_tooltips(self) -> bool: return bool(self._ui_state.graphics_show_tooltips)

    @property
    def graphics_performance_mode(self) -> str: return str(self._ui_state.graphics_performance_mode)

    @property
    def graphics_floating_toolbar_style(self) -> str: return str(self._ui_state.floating_toolbar_style)

    @property
    def graphics_floating_toolbar_size(self) -> str: return str(self._ui_state.floating_toolbar_size)

    @property
    def graphics_edge_crossing_style(self) -> str: return str(self._ui_state.edge_crossing_style)

    @property
    def graphics_expand_collision_avoidance(self) -> dict[str, Any]:
        return copy.deepcopy(self._expand_collision_avoidance)

    @property
    def graphics_graph_label_pixel_size(self) -> int: return int(self._ui_state.graph_label_pixel_size)

    @property
    def graphics_graph_node_icon_pixel_size_override(self) -> int | None:
        return self._ui_state.graph_node_icon_pixel_size_override

    @property
    def graphics_node_title_icon_pixel_size(self) -> int:
        return int(self._ui_state.node_title_icon_pixel_size)

    @property
    def active_theme_id(self) -> str: return str(self._ui_state.active_theme_id)

    @property
    def active_workspace_id(self) -> str:
        try:
            return self._host.workspace_manager.active_workspace_id()
        except Exception:  # noqa: BLE001
            return ""

    @property
    def active_workspace_name(self) -> str:
        workspace = self._host.model.project.workspaces.get(self.active_workspace_id)
        return workspace.name if workspace is not None else ""

    @property
    def active_view_name(self) -> str:
        workspace = self._host.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return ""
        workspace.ensure_default_view()
        active_view = workspace.views.get(workspace.active_view_id)
        return active_view.name if active_view is not None else ""

    @property
    def active_view_items(self) -> list[dict[str, Any]]:
        workspace = self._host.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return []
        workspace.ensure_default_view()
        return [
            {
                "view_id": view.view_id,
                "label": view.name,
                "active": view.view_id == workspace.active_view_id,
            }
            for view in workspace.views.values()
        ]

    @property
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        return list(self._host.scene.scope_breadcrumb_model)

    @property
    def can_publish_custom_workflow_from_scope(self) -> bool: return bool(self._host.scene.active_scope_path)

    @property
    def _active_workspace_run_controls(self) -> SelectedWorkspaceRunControlState:
        run_state = self._host.run_state
        return selected_workspace_run_control_state(
            selected_workspace_id=self.active_workspace_id,
            active_run_id=getattr(run_state, "active_run_id", ""),
            active_run_workspace_id=getattr(run_state, "active_run_workspace_id", ""),
            engine_state=getattr(run_state, "engine_state_value", ""),
        )

    @property
    def active_workspace_can_run(self) -> bool:
        return bool(self._active_workspace_run_controls.can_run_active_workspace)

    @property
    def active_workspace_can_pause(self) -> bool:
        return bool(self._active_workspace_run_controls.can_pause_active_workspace)

    @property
    def active_workspace_can_stop(self) -> bool:
        return bool(self._active_workspace_run_controls.can_stop_active_workspace)

    def request_run_workflow(self) -> None: self._host.run_controller.run_workflow()
    def request_save_project_as(self) -> None: self._host.project_session_controller.save_project_as()
    def request_toggle_run_pause(self) -> None: self._host.run_controller.toggle_pause_resume()
    def request_stop_workflow(self) -> None: self._host.run_controller.stop_workflow()
    def show_workflow_settings_dialog(self, _checked: bool = False) -> None: self._host.project_session_controller.show_workflow_settings_dialog()
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None: self._host.project_session_controller.set_script_editor_panel_visible(checked)
    def set_graphics_performance_mode(self, mode: str) -> None: self._host.set_graphics_performance_mode(mode)
    def set_graphics_floating_toolbar_style(self, style: str) -> None: self._host.set_graphics_floating_toolbar_style(style)
    def set_graphics_floating_toolbar_size(self, size: str) -> None: self._host.set_graphics_floating_toolbar_size(size)

    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        return bool(
            self._host.search_scope_controller.navigate_scope(
                lambda: self._host.scene.navigate_scope_to(normalized_node_id)
            )
        )

    def request_switch_view(self, view_id: str) -> None:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return
        workspace.ensure_default_view()
        target_id = str(view_id).strip()
        if not target_id or target_id not in workspace.views or workspace.active_view_id == target_id:
            return
        self._host.search_scope_controller.remember_scope_camera()
        self._host.workspace_library_controller.switch_view(target_id)
        self._host.scene.sync_scope_with_active_view()
        self._host.search_scope_controller.restore_scope_camera()

    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._host.workspace_library_controller.move_view(from_index, to_index))

    def request_rename_view(self, view_id: str) -> bool:
        return bool(self._host.workspace_library_controller.rename_view(view_id))

    def request_close_view(self, view_id: str) -> bool:
        return bool(self._host.workspace_library_controller.close_view(view_id))

    def request_create_view(self) -> None: self._host.workspace_library_controller.create_view()

    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._host.workspace_library_controller.move_workspace(from_index, to_index))

    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._host.workspace_library_controller.rename_workspace_by_id(workspace_id))

    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._host.workspace_library_controller.close_workspace_by_id(workspace_id))

    def request_create_workspace(self) -> None: self._host.workspace_library_controller.create_workspace()

    def apply_graphics_preferences(self, graphics: Any) -> dict[str, Any]:
        canvas = graphics.get("canvas", {}) if isinstance(graphics, dict) else {}
        interaction = graphics.get("interaction", {}) if isinstance(graphics, dict) else {}
        performance = graphics.get("performance", {}) if isinstance(graphics, dict) else {}
        shell = graphics.get("shell", {}) if isinstance(graphics, dict) else {}
        theme = graphics.get("theme", {}) if isinstance(graphics, dict) else {}
        typography = graphics.get("typography", {}) if isinstance(graphics, dict) else {}
        graph_theme = graphics.get("graph_theme", {}) if isinstance(graphics, dict) else {}

        changed = False
        show_grid = bool(canvas.get("show_grid", self._ui_state.show_grid))
        grid_style = normalize_grid_overlay_style(
            canvas.get("grid_style", self._ui_state.grid_style),
            self._ui_state.grid_style,
        )
        edge_crossing_style = normalize_edge_crossing_style(
            canvas.get("edge_crossing_style", self._ui_state.edge_crossing_style),
            self._ui_state.edge_crossing_style,
        )
        floating_toolbar_style = normalize_floating_toolbar_style(
            canvas.get("floating_toolbar_style", self._ui_state.floating_toolbar_style),
            self._ui_state.floating_toolbar_style,
        )
        floating_toolbar_size = normalize_floating_toolbar_size(
            canvas.get("floating_toolbar_size", self._ui_state.floating_toolbar_size),
            self._ui_state.floating_toolbar_size,
        )
        graph_label_pixel_size = normalize_graph_label_pixel_size(
            typography.get("graph_label_pixel_size", self._ui_state.graph_label_pixel_size),
            self._ui_state.graph_label_pixel_size,
        )
        graph_node_icon_pixel_size_override = normalize_graph_node_icon_pixel_size_override(
            typography.get("graph_node_icon_pixel_size_override", self._ui_state.graph_node_icon_pixel_size_override)
        )
        node_title_icon_pixel_size = effective_graph_node_icon_pixel_size(
            graph_label_pixel_size,
            graph_node_icon_pixel_size_override,
        )
        show_minimap = bool(canvas.get("show_minimap", self._ui_state.show_minimap))
        show_port_labels = bool(canvas.get("show_port_labels", self._ui_state.show_port_labels))
        minimap_expanded = bool(
            canvas.get("minimap_expanded", self._host.search_scope_state.graphics_minimap_expanded)
        )
        node_shadow = bool(canvas.get("node_shadow", self._ui_state.node_shadow))
        shadow_strength = int(canvas.get("shadow_strength", self._ui_state.shadow_strength))
        shadow_softness = int(canvas.get("shadow_softness", self._ui_state.shadow_softness))
        shadow_offset = int(canvas.get("shadow_offset", self._ui_state.shadow_offset))
        graphics_performance_mode = normalize_graphics_performance_mode(
            performance.get("mode", self._ui_state.graphics_performance_mode),
            self._ui_state.graphics_performance_mode,
        )
        if "expand_collision_avoidance" in interaction:
            expand_collision_avoidance = normalize_expand_collision_avoidance_settings(
                interaction.get("expand_collision_avoidance")
            )
        else:
            expand_collision_avoidance = copy.deepcopy(self._expand_collision_avoidance)
        tab_strip_density = str(shell.get("tab_strip_density", self._ui_state.tab_strip_density))
        property_pane_variant = normalize_property_pane_variant(
            shell.get("property_pane_variant", self._ui_state.property_pane_variant),
            self._ui_state.property_pane_variant,
        )
        show_tooltips_value = shell.get("show_tooltips", self._ui_state.graphics_show_tooltips)
        show_tooltips = (
            show_tooltips_value
            if isinstance(show_tooltips_value, bool)
            else self._ui_state.graphics_show_tooltips
        )
        active_theme_id = self._host.shell_host_presenter.apply_theme(
            theme.get("theme_id", self._ui_state.active_theme_id)
        )
        follow_shell_theme = graph_theme.get("follow_shell_theme")
        if not isinstance(follow_shell_theme, bool):
            follow_shell_theme = bool(DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["follow_shell_theme"])
        custom_graph_themes = serialize_custom_graph_themes(graph_theme.get("custom_themes"))
        selected_graph_theme_id = resolve_graph_theme_id(
            graph_theme.get(
                "selected_theme_id",
                DEFAULT_GRAPHICS_SETTINGS["graph_theme"]["selected_theme_id"],
            ),
            custom_themes=custom_graph_themes,
        )
        normalized_graph_theme = {
            "follow_shell_theme": bool(follow_shell_theme),
            "selected_theme_id": selected_graph_theme_id,
            "custom_themes": custom_graph_themes,
        }
        previous_graph_theme_id = self._host.graph_theme_bridge.theme_id
        self._host.graph_theme_bridge.apply_settings(
            shell_theme_id=active_theme_id,
            graph_theme_settings=normalized_graph_theme,
        )

        if self._ui_state.show_grid != show_grid:
            self._ui_state.show_grid = show_grid
            changed = True
        if self._ui_state.grid_style != grid_style:
            self._ui_state.grid_style = grid_style
            changed = True
        if self._ui_state.edge_crossing_style != edge_crossing_style:
            self._ui_state.edge_crossing_style = edge_crossing_style
            changed = True
        if self._ui_state.floating_toolbar_style != floating_toolbar_style:
            self._ui_state.floating_toolbar_style = floating_toolbar_style
            changed = True
        if self._ui_state.floating_toolbar_size != floating_toolbar_size:
            self._ui_state.floating_toolbar_size = floating_toolbar_size
            changed = True
        if self._ui_state.graph_label_pixel_size != graph_label_pixel_size:
            self._ui_state.graph_label_pixel_size = graph_label_pixel_size
            changed = True
        if self._ui_state.graph_node_icon_pixel_size_override != graph_node_icon_pixel_size_override:
            self._ui_state.graph_node_icon_pixel_size_override = graph_node_icon_pixel_size_override
            changed = True
        if self._ui_state.node_title_icon_pixel_size != node_title_icon_pixel_size:
            self._ui_state.node_title_icon_pixel_size = node_title_icon_pixel_size
            changed = True
        if self._ui_state.show_minimap != show_minimap:
            self._ui_state.show_minimap = show_minimap
            changed = True
        if self._ui_state.show_port_labels != show_port_labels:
            self._ui_state.show_port_labels = show_port_labels
            changed = True
        if self._host.search_scope_state.graphics_minimap_expanded != minimap_expanded:
            self._host.search_scope_state.graphics_minimap_expanded = minimap_expanded
            changed = True
        if self._ui_state.node_shadow != node_shadow:
            self._ui_state.node_shadow = node_shadow
            changed = True
        if self._ui_state.shadow_strength != shadow_strength:
            self._ui_state.shadow_strength = shadow_strength
            changed = True
        if self._ui_state.shadow_softness != shadow_softness:
            self._ui_state.shadow_softness = shadow_softness
            changed = True
        if self._ui_state.shadow_offset != shadow_offset:
            self._ui_state.shadow_offset = shadow_offset
            changed = True
        if self._ui_state.graphics_performance_mode != graphics_performance_mode:
            self._ui_state.graphics_performance_mode = graphics_performance_mode
            changed = True
        if self._expand_collision_avoidance != expand_collision_avoidance:
            self._expand_collision_avoidance = copy.deepcopy(expand_collision_avoidance)
            changed = True
        if self._ui_state.tab_strip_density != tab_strip_density:
            self._ui_state.tab_strip_density = tab_strip_density
            changed = True
        if self._ui_state.property_pane_variant != property_pane_variant:
            self._ui_state.property_pane_variant = property_pane_variant
            changed = True
        self._host.shell_inspector_presenter.set_property_pane_variant(property_pane_variant)
        if self._ui_state.graphics_show_tooltips != show_tooltips:
            self._ui_state.graphics_show_tooltips = show_tooltips
            changed = True
        if self._ui_state.active_theme_id != active_theme_id:
            self._ui_state.active_theme_id = active_theme_id
            changed = True
        if previous_graph_theme_id != self._host.graph_theme_bridge.theme_id:
            changed = True

        self._host.search_scope_controller.set_snap_to_grid_enabled(
            bool(interaction.get("snap_to_grid", self._host.search_scope_state.snap_to_grid_enabled)),
            persist=False,
        )
        if changed:
            self._host.graphics_preferences_changed.emit()

        return {
            "canvas": {
                "show_grid": bool(self._ui_state.show_grid),
                "grid_style": str(self._ui_state.grid_style),
                "edge_crossing_style": str(self._ui_state.edge_crossing_style),
                "show_minimap": bool(self._ui_state.show_minimap),
                "show_port_labels": bool(self._ui_state.show_port_labels),
                "minimap_expanded": bool(self._host.search_scope_state.graphics_minimap_expanded),
                "node_shadow": bool(self._ui_state.node_shadow),
                "shadow_strength": int(self._ui_state.shadow_strength),
                "shadow_softness": int(self._ui_state.shadow_softness),
                "shadow_offset": int(self._ui_state.shadow_offset),
                "floating_toolbar_style": str(self._ui_state.floating_toolbar_style),
                "floating_toolbar_size": str(self._ui_state.floating_toolbar_size),
            },
            "interaction": {
                "snap_to_grid": bool(self._host.search_scope_state.snap_to_grid_enabled),
                "expand_collision_avoidance": copy.deepcopy(self._expand_collision_avoidance),
            },
            "performance": {
                "mode": str(self._ui_state.graphics_performance_mode),
            },
            "shell": {
                "tab_strip_density": str(self._ui_state.tab_strip_density),
                "property_pane_variant": str(self._ui_state.property_pane_variant),
                "show_tooltips": bool(self._ui_state.graphics_show_tooltips),
            },
            "theme": {
                "theme_id": str(self._ui_state.active_theme_id),
            },
            "typography": {
                "graph_label_pixel_size": int(self._ui_state.graph_label_pixel_size),
                "graph_node_icon_pixel_size_override": self._ui_state.graph_node_icon_pixel_size_override,
            },
            "graph_theme": {
                "follow_shell_theme": bool(follow_shell_theme),
                "selected_theme_id": selected_graph_theme_id,
                "custom_themes": custom_graph_themes,
            },
        }


__all__ = ["ShellWorkspacePresenter"]
