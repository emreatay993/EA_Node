# V1_CLASSIC_EXPLORER_FOLDER_NODE P04: QML Surface

## Objective
- Add the V1 Classic Explorer graph-node surface and route `io.folder_explorer` through the graph surface loader with Explorer-style chrome, side navigation, breadcrumb navigation, details columns, context menu, drag payloads, maximize, and close behavior.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only QML/graph-surface/test files needed for this packet

## Preconditions
- `P01` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- `P02` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- `P03` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- No later `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphClassicExplorerSurface.qml`
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfacePathEditor.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/graph_surface/passive_host_interaction_suite.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphClassicExplorerSurface.qml`
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/GraphSurfacePathEditor.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P04_qml_surface_WRAPUP.md`

## Source Public Entry Points
- New QML component `GraphClassicExplorerSurface.qml`.
- Existing `GraphNodeSurfaceLoader.qml` surface-family/type routing for passive node bodies.
- Existing surface command bridge calls introduced by P03.

## Regression Public Entry Points
- Passive graph-surface host tests.
- Graph surface inline/input tests for path editing, context actions, and drag payloads.

## State Owner
- QML owns transient presentation state: navigation history, selected row, search text, sort column, context-menu position, and maximized state.
- Persistent folder path remains owned by the node property and bridge property mutation path.

## Allowed Dependencies
- Existing QML Controls, graph-surface components, inline path editor, and P03 bridge actions.
- No new runtime package dependency.

## Required Behavior
- Create `GraphClassicExplorerSurface.qml` and route `io.folder_explorer` to it from the surface loader.
- Render the V1 Classic Explorer title bar, command bar, navigation chrome, breadcrumbs, search box, side navigation, details columns, row selection, row context menu, drag payloads, maximize, and close controls.
- Dispatch all filesystem and graph mutations through P03 bridge actions.
- Keep transient UI state local to the surface.

## Required Invariants
- The surface visually matches the V1 design intent: dark Explorer chrome, title bar with folder icon/current folder/maximize/close, command bar, back/forward/up buttons, breadcrumbs, search box, left navigation, and details list columns `Name`, `Date modified`, `Type`, and `Size`.
- Double-clicking a folder row navigates into that folder.
- Row context menu exposes Open, Open in new window, Cut, Copy, Paste, Copy as path, Rename, Delete, Send to COREX as Path Pointer, and Properties.
- Dragging a file/folder row emits a path payload suitable for Path Pointer creation.
- Close deletes the node through existing graph action routing; maximize changes only presentation state.
- The surface remains usable under offscreen QML tests and does not require real user desktop interaction.

## Non-Goals
- No Python filesystem service changes.
- No node registry changes.
- No library or inspector exposure changes.

## Forbidden Shortcuts
- Do not perform filesystem operations directly in QML.
- Do not hard-code the design prototype's mock folder tree.
- Do not persist transient surface state in node properties.
- Do not change existing passive media/flowchart/annotation surface behavior.

## Required Tests
- Add QML/graph-surface tests that load `io.folder_explorer` through the surface loader.
- Add tests for breadcrumb/navigation command emission, details row context actions, and drag payload shape.
- Add tests that transient search/sort/selection state is not written as node properties.

## Verification Anchor Handoff
- Later packets that rename QML object names, command ids, drag payload fields, or loader routing must inherit and update `tests/test_passive_graph_surface_host.py`, `tests/test_graph_surface_input_inline.py`, and `tests/graph_surface/passive_host_interaction_suite.py`.
- Later visual polish may leave this packet's tests untouched only when the public object names and command payloads remain stable.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_inline.py tests/graph_surface/passive_host_interaction_suite.py -k "folder_explorer or graph_surface" --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k folder_explorer --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P04_qml_surface_WRAPUP.md`

## Acceptance Criteria
- `io.folder_explorer` renders a Classic Explorer surface in the graph canvas.
- The surface emits P03 command payloads for navigation, context actions, drag path-pointer creation, maximize, and close.
- Transient UI state remains QML-local and is not persisted.
- Existing passive graph surfaces continue to load and test successfully.

## Handoff Notes
- `P05` may adjust library/inspector payloads but must not rework this surface's object names or bridge command ids without inheriting and updating this packet's tests.
- Later visual polish must preserve the V1 required controls and details columns.
