# V1_CLASSIC_EXPLORER_FOLDER_NODE P05: Shell Inspector Library

## Objective
- Expose `io.folder_explorer` in the node library and inspector, support folder path editing through existing path editor flows, and prove transient Classic Explorer UI state stays out of project persistence.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only shell/inspector/library/test files needed for this packet

## Preconditions
- `P01` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- `P03` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- `P04` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- No later `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet is in progress.

## Execution Dependencies
- `P01`
- `P03`
- `P04`

## Target Subsystems
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui/shell/controllers/workspace_graph_edit_controller.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/passive_property_editors.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_serializer.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui/shell/controllers/workspace_graph_edit_controller.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/passive_property_editors.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_serializer.py`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P05_shell_inspector_library_WRAPUP.md`

## Source Public Entry Points
- Node library grouping/search payload for `io.folder_explorer`.
- Inspector property payload for `current_path` with folder browsing behavior.
- Existing path editor and property commit commands.

## Regression Public Entry Points
- Window library/inspector tests.
- Main-window shell passive property editor tests.
- Serializer tests that prove transient UI state is not persisted.

## State Owner
- Library and inspector own presentation payloads only.
- `current_path` remains the only project-semantic field added by this feature.

## Allowed Dependencies
- Existing shell library and inspector bridge APIs.
- Existing folder path editor/browse flows.
- P01 node contract and P04 surface metadata.

## Required Behavior
- Make `io.folder_explorer` discoverable from the existing node library.
- Project the `current_path` property into inspector payloads as a folder-path editor.
- Reuse the existing property mutation path for inspector and surface path changes.
- Add persistence coverage proving only semantic node state is serialized.

## Required Invariants
- Users can find and create `io.folder_explorer` from the existing node library.
- Inspector exposes `current_path` as a folder path field using the directory-picker behavior.
- Editing `current_path` from inspector and surface uses the same graph property mutation path.
- Project serialization contains `current_path` but excludes navigation history, search text, sort state, selected row, context-menu state, and maximized state.

## Non-Goals
- No new filesystem service methods.
- No Classic Explorer visual redesign.
- No app preference migration for browse history.

## Forbidden Shortcuts
- Do not add a separate root-level launcher or startup path.
- Do not store app-wide browse defaults in `.sfe`.
- Do not fork a second inspector path editor when the existing path editor can be extended.
- Do not change unrelated node library grouping behavior.

## Required Tests
- Add library tests proving `io.folder_explorer` is present in the expected file-I/O/integration grouping.
- Add inspector tests proving folder browse mode is used for `current_path`.
- Add persistence tests proving transient Classic Explorer state is not serialized.

## Verification Anchor Handoff
- Later packets that change library grouping, inspector property payload shape, or `current_path` editor mode must inherit and update `tests/test_window_library_inspector.py` and `tests/main_window_shell/passive_property_editors.py`.
- Later packets may add tests without duplicating serializer assertions when persistence behavior remains stable.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_window_library_inspector.py tests/main_window_shell/passive_property_editors.py tests/test_graph_surface_input_inline.py tests/test_serializer.py --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/passive_property_editors.py -k folder --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P05_shell_inspector_library_WRAPUP.md`

## Acceptance Criteria
- `io.folder_explorer` is discoverable in the node library.
- Inspector folder-path editing works for `current_path`.
- Surface and inspector path updates share the same graph mutation route.
- Serialization tests prove transient V1 UI state is excluded from `.sfe`.

## Handoff Notes
- `P06` owns broader cross-surface integration tests after this packet lands.
- Any later change to node library category names or inspector property payload shape must inherit this packet's tests.
