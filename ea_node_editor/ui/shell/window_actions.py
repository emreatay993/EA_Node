from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

from ea_node_editor.ui.icon_registry import qicon

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


def create_window_actions(window: ShellWindow) -> None:
    window.action_new_project = QAction("New Project", window)
    window.action_new_project.setShortcut(QKeySequence.StandardKey.New)
    window.action_new_project.triggered.connect(window._new_project)

    window.action_new_workspace = QAction("New Workspace", window)
    window.action_new_workspace.setShortcut(QKeySequence("Ctrl+Shift+N"))
    window.action_new_workspace.triggered.connect(window._create_workspace)

    window.action_save_project = QAction("Save Project", window)
    window.action_save_project.setShortcut(QKeySequence.StandardKey.Save)
    window.action_save_project.triggered.connect(window._save_project)

    window.action_open_project = QAction("Open Project", window)
    window.action_open_project.setShortcut(QKeySequence.StandardKey.Open)
    window.action_open_project.triggered.connect(window._open_project)

    window.action_clear_recent_projects = QAction("Clear Recent Files", window)
    window.action_clear_recent_projects.triggered.connect(window._clear_recent_projects)

    window.action_workflow_settings = QAction("Workflow Settings", window)
    window.action_workflow_settings.setShortcut(QKeySequence("Ctrl+,"))
    window.action_workflow_settings.triggered.connect(window.show_workflow_settings_dialog)

    window.action_graphics_settings = QAction("Graphics Settings", window)
    window.action_graphics_settings.triggered.connect(window.show_graphics_settings_dialog)

    window.action_toggle_script_editor = QAction("Script Editor", window)
    window.action_toggle_script_editor.setCheckable(True)
    window.action_toggle_script_editor.setShortcut(QKeySequence("Ctrl+Shift+E"))
    window.action_toggle_script_editor.triggered.connect(window.set_script_editor_panel_visible)

    window.action_run = QAction("Run", window)
    window.action_run.setIcon(qicon("run"))
    window.action_run.setShortcut(QKeySequence("F5"))
    window.action_run.triggered.connect(window._run_workflow)

    window.action_stop = QAction("Stop", window)
    window.action_stop.setIcon(qicon("stop"))
    window.action_stop.setShortcut(QKeySequence("Shift+F5"))
    window.action_stop.triggered.connect(window._stop_workflow)

    window.action_pause = QAction("Pause", window)
    window.action_pause.setIcon(qicon("pause"))
    window.action_pause.setShortcut(QKeySequence("F6"))
    window.action_pause.triggered.connect(window._toggle_pause_resume)

    window.action_connect_selected = QAction("Connect Selected", window)
    window.action_connect_selected.setShortcut(QKeySequence("Ctrl+L"))
    window.action_connect_selected.triggered.connect(window._connect_selected_nodes)

    window.action_duplicate_selection = QAction("Duplicate Selection", window)
    window.action_duplicate_selection.setShortcut(QKeySequence("Ctrl+D"))
    window.action_duplicate_selection.triggered.connect(window._duplicate_selected_nodes)

    window.action_wrap_selection_in_comment_backdrop = QAction("Wrap Selection in Comment Backdrop", window)
    window.action_wrap_selection_in_comment_backdrop.setShortcut(QKeySequence("C"))
    window.action_wrap_selection_in_comment_backdrop.triggered.connect(
        window._wrap_selected_nodes_in_comment_backdrop
    )

    window.action_group_selection = QAction("Group Selection", window)
    window.action_group_selection.setShortcut(QKeySequence("Ctrl+G"))
    window.action_group_selection.triggered.connect(window._group_selected_nodes)

    window.action_ungroup_selection = QAction("Ungroup Selection", window)
    window.action_ungroup_selection.setShortcut(QKeySequence("Ctrl+Shift+G"))
    window.action_ungroup_selection.triggered.connect(window._ungroup_selected_nodes)

    window.action_align_left = QAction("Align Left", window)
    window.action_align_left.triggered.connect(window._align_selection_left)

    window.action_align_right = QAction("Align Right", window)
    window.action_align_right.triggered.connect(window._align_selection_right)

    window.action_align_top = QAction("Align Top", window)
    window.action_align_top.triggered.connect(window._align_selection_top)

    window.action_align_bottom = QAction("Align Bottom", window)
    window.action_align_bottom.triggered.connect(window._align_selection_bottom)

    window.action_distribute_horizontally = QAction("Distribute Horizontally", window)
    window.action_distribute_horizontally.triggered.connect(window._distribute_selection_horizontally)

    window.action_distribute_vertically = QAction("Distribute Vertically", window)
    window.action_distribute_vertically.triggered.connect(window._distribute_selection_vertically)

    window.action_snap_to_grid = QAction("Snap to Grid", window)
    window.action_snap_to_grid.setCheckable(True)
    window.action_snap_to_grid.setChecked(False)
    window.action_snap_to_grid.toggled.connect(window.set_snap_to_grid_enabled)

    window.action_show_port_labels = QAction("Port Labels", window)
    window.action_show_port_labels.setCheckable(True)
    window.action_show_port_labels.setChecked(True)
    window.action_show_port_labels.toggled.connect(window.set_graphics_show_port_labels)

    window.action_undo = QAction("Undo", window)
    window.action_undo.setShortcut(QKeySequence("Ctrl+Z"))
    window.action_undo.triggered.connect(window._undo)

    window.action_redo = QAction("Redo", window)
    window.action_redo.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
    window.action_redo.triggered.connect(window._redo)

    window.action_copy_selection = QAction("Copy Selection", window)
    window.action_copy_selection.setShortcut(QKeySequence.StandardKey.Copy)
    window.action_copy_selection.triggered.connect(window._copy_selected_nodes_to_clipboard)

    window.action_cut_selection = QAction("Cut Selection", window)
    window.action_cut_selection.setShortcut(QKeySequence.StandardKey.Cut)
    window.action_cut_selection.triggered.connect(window._cut_selected_nodes_to_clipboard)

    window.action_paste_selection = QAction("Paste Selection", window)
    window.action_paste_selection.setShortcut(QKeySequence.StandardKey.Paste)
    window.action_paste_selection.triggered.connect(window._paste_nodes_from_clipboard)

    window.action_frame_all = QAction("Frame All", window)
    window.action_frame_all.setShortcut(QKeySequence("A"))
    window.action_frame_all.triggered.connect(window._frame_all)

    window.action_frame_selection = QAction("Frame Selection", window)
    window.action_frame_selection.setShortcut(QKeySequence("F"))
    window.action_frame_selection.triggered.connect(window._frame_selection)

    window.action_center_selection = QAction("Center Selection", window)
    window.action_center_selection.setShortcut(QKeySequence("Shift+F"))
    window.action_center_selection.triggered.connect(window._center_on_selection)

    window.action_scope_parent = QAction("Scope Parent", window)
    window.action_scope_parent.setShortcut(QKeySequence("Alt+Left"))
    window.action_scope_parent.triggered.connect(window.request_navigate_scope_parent)

    window.action_scope_root = QAction("Scope Root", window)
    window.action_scope_root.setShortcut(QKeySequence("Alt+Home"))
    window.action_scope_root.triggered.connect(window.request_navigate_scope_root)

    window.action_graph_search = QAction("Graph Search", window)
    window.action_graph_search.setShortcut(QKeySequence("Ctrl+K"))
    window.action_graph_search.triggered.connect(window.request_open_graph_search)

    window.action_new_view = QAction("New View", window)
    window.action_new_view.setShortcut(QKeySequence("Ctrl+Shift+V"))
    window.action_new_view.triggered.connect(window._create_view)

    window.action_duplicate_workspace = QAction("Duplicate Workspace", window)
    window.action_duplicate_workspace.setShortcut(QKeySequence("Ctrl+Shift+D"))
    window.action_duplicate_workspace.triggered.connect(window._duplicate_active_workspace)

    window.action_rename_workspace = QAction("Rename Workspace", window)
    window.action_rename_workspace.setShortcut(QKeySequence("F2"))
    window.action_rename_workspace.triggered.connect(window._rename_active_workspace)

    window.action_close_workspace = QAction("Close Workspace", window)
    window.action_close_workspace.setShortcut(QKeySequence.StandardKey.Close)
    window.action_close_workspace.triggered.connect(window._close_active_workspace)

    window.action_next_workspace = QAction("Next Workspace", window)
    window.action_next_workspace.setShortcuts([QKeySequence("Ctrl+Tab"), QKeySequence("Ctrl+PgDown")])
    window.action_next_workspace.triggered.connect(lambda: window._switch_workspace_by_offset(1))

    window.action_prev_workspace = QAction("Previous Workspace", window)
    window.action_prev_workspace.setShortcuts([QKeySequence("Ctrl+Shift+Tab"), QKeySequence("Ctrl+PgUp")])
    window.action_prev_workspace.triggered.connect(lambda: window._switch_workspace_by_offset(-1))

    window.action_import_node_package = QAction("Import Node Package...", window)
    window.action_import_node_package.triggered.connect(window._import_node_package)

    window.action_export_node_package = QAction("Export Node Package...", window)
    window.action_export_node_package.triggered.connect(window._export_node_package)

    window.action_import_custom_workflow = QAction("Import Custom Workflow...", window)
    window.action_import_custom_workflow.triggered.connect(window._import_custom_workflow)

    window.action_export_custom_workflow = QAction("Export Custom Workflow...", window)
    window.action_export_custom_workflow.triggered.connect(window._export_custom_workflow)

    for action in (
        window.action_new_project,
        window.action_new_workspace,
        window.action_save_project,
        window.action_open_project,
        window.action_clear_recent_projects,
        window.action_workflow_settings,
        window.action_graphics_settings,
        window.action_toggle_script_editor,
        window.action_run,
        window.action_stop,
        window.action_pause,
        window.action_undo,
        window.action_redo,
        window.action_copy_selection,
        window.action_cut_selection,
        window.action_paste_selection,
        window.action_connect_selected,
        window.action_duplicate_selection,
        window.action_wrap_selection_in_comment_backdrop,
        window.action_group_selection,
        window.action_ungroup_selection,
        window.action_align_left,
        window.action_align_right,
        window.action_align_top,
        window.action_align_bottom,
        window.action_distribute_horizontally,
        window.action_distribute_vertically,
        window.action_snap_to_grid,
        window.action_show_port_labels,
        window.action_frame_all,
        window.action_frame_selection,
        window.action_center_selection,
        window.action_scope_parent,
        window.action_scope_root,
        window.action_graph_search,
        window.action_new_view,
        window.action_duplicate_workspace,
        window.action_rename_workspace,
        window.action_close_workspace,
        window.action_next_workspace,
        window.action_prev_workspace,
        window.action_import_custom_workflow,
        window.action_export_custom_workflow,
        window.action_import_node_package,
        window.action_export_node_package,
    ):
        action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        window.addAction(action)


def build_window_menu_bar(window: ShellWindow) -> None:
    menu_bar = window.menuBar()
    menu_bar.clear()

    file_menu = menu_bar.addMenu("&File")
    file_menu.addAction(window.action_new_project)
    file_menu.addAction(window.action_open_project)
    window.menu_recent_projects = file_menu.addMenu("Open Recent")
    window.menu_recent_projects.aboutToShow.connect(window._refresh_recent_projects_menu)
    window._refresh_recent_projects_menu()
    file_menu.addAction(window.action_save_project)
    file_menu.addSeparator()
    file_menu.addAction(window.action_import_custom_workflow)
    file_menu.addAction(window.action_export_custom_workflow)
    file_menu.addSeparator()
    file_menu.addAction(window.action_import_node_package)
    file_menu.addAction(window.action_export_node_package)

    edit_menu = menu_bar.addMenu("&Edit")
    edit_menu.addAction(window.action_undo)
    edit_menu.addAction(window.action_redo)
    edit_menu.addSeparator()
    edit_menu.addAction(window.action_copy_selection)
    edit_menu.addAction(window.action_cut_selection)
    edit_menu.addAction(window.action_paste_selection)
    edit_menu.addSeparator()
    edit_menu.addAction(window.action_connect_selected)
    edit_menu.addAction(window.action_duplicate_selection)
    edit_menu.addAction(window.action_wrap_selection_in_comment_backdrop)
    edit_menu.addAction(window.action_group_selection)
    edit_menu.addAction(window.action_ungroup_selection)
    layout_menu = edit_menu.addMenu("Layout")
    layout_menu.addAction(window.action_align_left)
    layout_menu.addAction(window.action_align_right)
    layout_menu.addAction(window.action_align_top)
    layout_menu.addAction(window.action_align_bottom)
    layout_menu.addSeparator()
    layout_menu.addAction(window.action_distribute_horizontally)
    layout_menu.addAction(window.action_distribute_vertically)
    edit_menu.addAction(window.action_snap_to_grid)
    edit_menu.addSeparator()
    edit_menu.addAction(window.action_graph_search)

    view_menu = menu_bar.addMenu("&View")
    view_menu.addAction(window.action_toggle_script_editor)
    view_menu.addAction(window.action_show_port_labels)
    view_menu.addSeparator()
    view_menu.addAction(window.action_frame_all)
    view_menu.addAction(window.action_frame_selection)
    view_menu.addAction(window.action_center_selection)
    view_menu.addSeparator()
    view_menu.addAction(window.action_scope_parent)
    view_menu.addAction(window.action_scope_root)

    run_menu = menu_bar.addMenu("&Run")
    run_menu.addAction(window.action_run)
    run_menu.addAction(window.action_pause)
    run_menu.addAction(window.action_stop)

    workspace_menu = menu_bar.addMenu("&Workspace")
    workspace_menu.addAction(window.action_new_workspace)
    workspace_menu.addAction(window.action_new_view)
    workspace_menu.addAction(window.action_duplicate_workspace)
    workspace_menu.addAction(window.action_rename_workspace)
    workspace_menu.addAction(window.action_close_workspace)
    workspace_menu.addSeparator()
    workspace_menu.addAction(window.action_next_workspace)
    workspace_menu.addAction(window.action_prev_workspace)

    settings_menu = menu_bar.addMenu("&Settings")
    settings_menu.addAction(window.action_workflow_settings)
    settings_menu.addAction(window.action_graphics_settings)
