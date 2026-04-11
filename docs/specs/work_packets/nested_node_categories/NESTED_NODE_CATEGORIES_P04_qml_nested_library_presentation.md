# NESTED_NODE_CATEGORIES P04: QML Nested Library Presentation

## Objective
- Keep `NodeLibraryPane` on `ListView` while adding nested indentation, ancestor-aware visibility, and `category_key`-driven collapse behavior for the new flattened tree rows.

## Preconditions
- `P03` is marked `PASS` in [NESTED_NODE_CATEGORIES_STATUS.md](./NESTED_NODE_CATEGORIES_STATUS.md).
- The Python library payload already emits `depth`, `ancestor_category_keys`, `category_key`, and full-path display metadata.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md`
- `docs/specs/work_packets/nested_node_categories/P04_qml_nested_library_presentation_WRAPUP.md`

## Required Behavior
- Keep `NodeLibraryPane.qml` on `ListView` and consume the flattened nested rows emitted by `P03`.
- Indent category and node rows from the packet-owned `depth` metadata instead of deriving nesting from string parsing in QML.
- Key collapse state by `category_key`, not by rendered category label text.
- Keep all categories collapsed by default when the pane initializes, resets, or rehydrates after project install.
- Hide descendants until every ancestor category in `ancestor_category_keys` is expanded.
- Expanding a parent must not auto-expand child categories.
- Preserve click, double-click, drag, and quick-insert interactions for node rows while category rows continue to act as expand/collapse controls only.
- Inherit and update any earlier custom-workflow or grouped-row assertions from `tests/main_window_shell/drop_connect_and_workflow_io.py` that the new collapse-key contract changes.
- If the QML contract requires a grouped-row shape or metadata refinement, inherit and update the Python row-shape assertions in `tests/test_window_library_inspector.py` instead of leaving packet-local field drift behind.
- Add packet-owned regression tests whose names include `nested_category_qml` so the targeted verification commands below remain stable.

## Non-Goals
- No replacement of `ListView` with `TreeView`.
- No new library bridge property surface beyond the packet-owned row metadata already emitted by `P03`.
- No docs or requirements updates yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/drop_connect_and_workflow_io.py tests/test_main_window_shell.py -k nested_category_qml --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py -k nested_category_qml --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/nested_node_categories/P04_qml_nested_library_presentation_WRAPUP.md`

## Acceptance Criteria
- `NodeLibraryPane` renders nested categories from row metadata while remaining a `ListView`.
- Category collapse is keyed by `category_key`, starts collapsed, and keeps descendants hidden until all ancestors expand.
- Expanding one category does not implicitly expand its child categories.
- Node row interactions continue to work for placement, drag, and quick-insert flows.
- The packet-owned `nested_category_qml` regressions pass and prove the nested-library presentation contract.

## Handoff Notes
- `P05` updates documentation and traceability only; it must not reopen the QML row contract unless a closeout-only fix is unavoidable and still within this packet's written behavior.
- Any post-closeout packet that changes collapse semantics must inherit and update the `nested_category_qml` regressions.
