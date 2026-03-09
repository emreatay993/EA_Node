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

## Acceptance
- `AC-REQ-UI-002-01`: Tab actions operate without data loss for non-closed workspaces.
- `AC-REQ-UI-005-01`: Switching views restores stored zoom and pan center.
- `AC-REQ-UI-010-01`: Failure event visibly highlights failed node and displays error message.
- `AC-REQ-UI-011-01`: QML shell and graph canvas visually match the Stitch baseline and remain fully functional.
- `AC-REQ-UI-012-01`: Settings modal saves user edits to project metadata and subsequent run triggers include these values.
- `AC-REQ-UI-013-01`: Script editor reflects selected script node content and applying edits updates model state.
- `AC-REQ-UI-014-01`: Users can author nested subnode workflows end-to-end (group, navigate scopes, edit pins, publish custom workflow, and place published snapshots from the library).
- `AC-REQ-UI-015-01`: Exporting and importing `.eawf` files preserves custom-workflow snapshot fidelity and updates library availability without changing `.eanp` package behavior.
