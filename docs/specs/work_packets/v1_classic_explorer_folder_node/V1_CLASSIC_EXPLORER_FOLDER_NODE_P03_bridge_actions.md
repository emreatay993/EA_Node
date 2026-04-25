# V1_CLASSIC_EXPLORER_FOLDER_NODE P03: Bridge Actions

## Objective
- Add the Python/QML bridge action contract for folder-explorer navigation, listing refresh, search/sort requests, context-menu commands, mutation confirmations, clipboard/open-in-OS behavior, Path Pointer spawning, and opening a second Classic Explorer node.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only bridge/action/test files needed for this packet

## Preconditions
- `P01` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- `P02` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- No later `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`

## Target Subsystems
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_inline.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui_qml/graph_action_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_inline.py`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P03_bridge_actions_WRAPUP.md`

## Source Public Entry Points
- Folder explorer bridge commands exposed to QML for `list`, `navigate`, `refresh`, `setSort`, `setSearch`, `open`, `openInNewWindow`, `newFolder`, `rename`, `delete`, `cut`, `copy`, `paste`, `copyPath`, `properties`, and `sendToCorexPathPointer`.
- Existing graph mutation service entry points for creating nodes and updating node properties.
- Existing confirmation/message-box and clipboard/open-in-OS seams.

## Regression Public Entry Points
- Graph action contract tests for new action ids and payload shapes.
- Graph surface input tests for path browse/property commit behavior and node creation command routing.

## State Owner
- Bridge owns command payload normalization and dispatch.
- Filesystem listing/mutation behavior remains owned by the P02 service.
- Graph state changes remain owned by existing graph mutation services.

## Allowed Dependencies
- P01 `io.folder_explorer` node contract.
- P02 filesystem service.
- Existing shell/graph command bridge, clipboard, confirmation dialog, and graph mutation APIs.

## Required Behavior
- Add stable bridge commands for V1 navigation, listing refresh, sort/search requests, context-menu actions, and row drag/drop payloads.
- Normalize QML request payloads into service calls or graph mutation commands.
- Prompt for confirmation before destructive filesystem operations and no-op on declined confirmation.
- Return structured result payloads with success/error state and refreshed listing data where applicable.

## Required Invariants
- All destructive mutations require explicit confirmation before calling the P02 service.
- Bridge commands return structured success/error payloads consumable by QML without throwing through the QML boundary for expected user/file errors.
- `sendToCorexPathPointer` and drag/drop payloads create `io.path_pointer`, not a second folder-explorer node.
- `openInNewWindow` creates a new `io.folder_explorer` node scoped to the selected folder path.
- Navigation changes update the selected node's `current_path` through existing property mutation paths.
- Clipboard state for cut/copy remains transient and must not be persisted.

## Non-Goals
- No final Classic Explorer visual surface.
- No filesystem service implementation changes except tiny adapter fixes required by bridge tests.
- No shell library or inspector exposure.

## Forbidden Shortcuts
- Do not bypass graph mutation services or write graph records directly.
- Do not perform filesystem mutations from QML.
- Do not add the final V1 visual surface in this packet.
- Do not persist transient clipboard/history/search/sort state in `.sfe`.

## Required Tests
- Add bridge/action-contract tests for action ids, required payload fields, and routing to existing graph mutation seams.
- Add temp-service backed tests for confirmed mutation dispatch and unconfirmed cancellation.
- Add tests proving Path Pointer creation targets `io.path_pointer` and new-window creation targets `io.folder_explorer`.

## Verification Anchor Handoff
- `P04` owns QML consumption of these command ids and must inherit this packet's action-contract tests if it renames or reshapes any command.
- `P05` owns library/inspector entry points and may leave these bridge tests untouched if command ids and payloads remain stable.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py -k folder_explorer --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P03_bridge_actions_WRAPUP.md`

## Acceptance Criteria
- QML can request listing, navigation, sorting, search filtering, and all V1 context commands through stable bridge actions.
- Confirmed mutations call the P02 service; declined confirmations have no side effects.
- Path Pointer and new Classic Explorer node creation use existing graph mutation boundaries.
- Existing graph action tests pass with the new command contract.

## Handoff Notes
- `P04` consumes these commands from the V1 QML surface and must not rename command ids without inheriting and updating this packet's tests.
- `P05` may add inspector/library entry points but must continue to route folder path changes through the same property mutation paths.
