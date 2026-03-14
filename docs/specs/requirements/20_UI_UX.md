# UI/UX Requirements

## Layout
- `REQ-UI-001`: Main shell shall be rendered in QML and include menu bar, top toolbar, left node library, center graph canvas, right inspector, bottom workspace tabs, and bottom console/log.
- `REQ-UI-002`: Workspace tabs shall support create, rename, duplicate, close, reorder, and switch.
- `REQ-UI-003`: Workspace tabs shall be displayed below the canvas area.
- `REQ-UI-004`: Each workspace shall support multiple named views (`V1`, `V2`, ...).
- `REQ-UI-005`: Each view shall preserve independent pan/zoom state.

## Node Library
- `REQ-UI-006`: Node library shall support text search and filtering by category, port direction, and data type.
- `REQ-UI-007`: Double-click or button action shall add selected node to canvas.

## Node Inspector
- `REQ-UI-008`: Selecting a node shall show editable properties and exposed-port toggles.
- `REQ-UI-009`: Collapse/expand control shall be available per collapsible node.

## Error UX
- `REQ-UI-010`: On execution failure, app shall switch to containing workspace, center failed node, and show error details.

## RC2 UX Surfaces
- `REQ-UI-011`: Application shell styling shall match Stitch references using QML theme tokens and surface hierarchy.
- `REQ-UI-012`: `ShellWindow` shall expose `show_workflow_settings_dialog()` and persist workflow settings metadata from a modal UI.
- `REQ-UI-013`: `ShellWindow` shall expose `set_script_editor_panel_visible()` and provide a Python script editor surface bound to selected `core.python_script` nodes.

## Subnode UX Surfaces
- `REQ-UI-014`: Shell and canvas UX shall support subnode scope navigation (breadcrumbs + keyboard navigation), group/ungroup transforms, and subnode pin editing directly from the inspector/library workflows.
- `REQ-UI-015`: File menu UX shall provide project-local custom workflow interchange through versioned `.eawf` import/export actions that remain separate from `.eanp` node package actions.

## Graphics Settings UX Surfaces
- `REQ-UI-016`: `ShellWindow` shall expose `show_graphics_settings_dialog()` and the Settings menu shall provide an app-wide Graphics Settings modal covering grid, minimap, snap-to-grid default, shell-theme selection, graph-theme follow-shell or explicit selection, and graph-theme manager access.
- `REQ-UI-017`: shell and graph canvas chrome surfaces shall support live application of shared shell-theme tokens for `stitch_dark` and `stitch_light`.
- `REQ-UI-018`: node and edge visuals shall resolve through dedicated graph-theme tokens while canvas chrome (background, grid, minimap, marquee, and drop-preview) stays on the shell-theme path.
- `REQ-UI-019`: `ShellWindow` shall expose `show_graph_theme_editor_dialog()` and provide a graph-theme manager/editor that groups built-in read-only themes and editable custom themes with create, duplicate, rename, delete, use-selected, and token-editing workflows.

## Acceptance
- `AC-REQ-UI-002-01`: Tab actions operate without data loss for non-closed workspaces.
- `AC-REQ-UI-005-01`: Switching views restores stored zoom and pan center.
- `AC-REQ-UI-010-01`: Failure event visibly highlights failed node and displays error message.
- `AC-REQ-UI-011-01`: QML shell and graph canvas visually match the Stitch baseline and remain fully functional.
- `AC-REQ-UI-012-01`: Settings modal saves user edits to project metadata and subsequent run triggers include these values.
- `AC-REQ-UI-013-01`: Script editor reflects selected script node content and applying edits updates model state.
- `AC-REQ-UI-014-01`: Users can author nested subnode workflows end-to-end (group, navigate scopes, edit pins, publish custom workflow, and place published snapshots from the library).
- `AC-REQ-UI-015-01`: Exporting and importing `.eawf` files preserves custom-workflow snapshot fidelity and updates library availability without changing `.eanp` package behavior.
- `AC-REQ-UI-016-01`: accepting Graphics Settings updates runtime graphics behavior and reopening the application restores the persisted shell-theme and graph-theme preferences.
- `AC-REQ-UI-017-01`: `stitch_dark` and `stitch_light` both render shell and graph-canvas chrome surfaces without breaking existing shell/canvas contracts.
- `AC-REQ-UI-018-01`: `NodeCard` and `EdgeLayer` follow the active graph theme while background/grid/minimap/drop-preview chrome stay on the shell-theme path.
- `AC-REQ-UI-019-01`: the graph-theme manager keeps built-in themes read-only, persists custom-theme library edits, and only live-applies token edits when the edited theme is the active explicit custom theme.
