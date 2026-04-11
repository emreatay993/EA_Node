# NESTED_NODE_CATEGORIES P03: Library Tree Payload Projection

## Objective
- Rebuild Python-side library payloads, grouped rows, category options, quick insert results, and adjacent metadata around path-backed tree data so the shell can hand QML one flattened nested-library model without reparsing category display strings.

## Preconditions
- `P02` is marked `PASS` in [NESTED_NODE_CATEGORIES_STATUS.md](./NESTED_NODE_CATEGORIES_STATUS.md).
- The registry already exposes path-backed category semantics and the nested Ansys DPF taxonomy.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/custom_workflows/codec.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window_library_inspector.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/custom_workflows/codec.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md`
- `docs/specs/work_packets/nested_node_categories/P03_library_tree_payload_projection_WRAPUP.md`

## Required Behavior
- Extend library item payloads to carry the packet-owned category metadata:
  - `category_path`
  - `category_key`
  - `category_display`
  - `root_category`
  - derived read-only `category` display text for packet-external consumers that still read a flat string
- Rebuild grouped library rows from a trie so Python emits synthesized intermediate category rows, preorder flattening, segment-by-segment sorting, and category-before-node ordering inside each subtree.
- Keep mixed-depth category sorting stable and ensure duplicate leaf labels under different parents do not collide in grouped rows or category keys.
- Emit the row metadata QML needs later in `P04`, including `depth`, `ancestor_category_keys`, `category_key`, and `label` for category rows.
- Keep text search and category filtering path-aware and descendant-inclusive. Full-path display text must be searchable without reparsing arbitrary delimiters at call sites.
- Update category options to use path-backed values suitable for later nested filtering rather than flat label equality.
- Keep custom workflows on `("Custom Workflows",)` and project their derived display/category metadata through the same payload contract.
- Ensure quick insert and inspector/library-adjacent metadata surfaces expose the full displayed path text rather than a stale flat category label.
- Add packet-owned regression tests whose names include `nested_category_library_payload` so the targeted verification commands below remain stable.

## Non-Goals
- No QML `ListView` indentation/collapse behavior yet.
- No broader shell-window API or bridge contract refactor outside packet-owned library payload flow.
- No README or requirements updates yet.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_window_library_inspector.py tests/main_window_shell/bridge_support.py -k nested_category_library_payload --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py -k nested_category_library_payload --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py -k nested_category_library_payload --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/nested_node_categories/P03_library_tree_payload_projection_WRAPUP.md`

## Acceptance Criteria
- Python-side library payloads expose normalized path, key, display, root, and row-depth metadata without making flat display strings authoritative again.
- Grouped rows synthesize missing intermediate folders, sort predictably, and place category rows before direct node rows in each subtree.
- Mixed-depth category sorting stays stable, and duplicate leaf labels under different parents remain distinct through path-backed keys and payload rows.
- Custom workflows continue to appear under one single-segment category family with the new payload contract.
- Quick insert and library-adjacent metadata surfaces show full displayed category paths.
- The packet-owned `nested_category_library_payload` regressions pass and prove the payload/trie behavior.

## Handoff Notes
- `P04` consumes the row metadata emitted here. Do not rename `depth`, `ancestor_category_keys`, `category_key`, or `label` after this packet.
- Any later packet that changes grouped-row shape or custom-workflow library assertions must inherit and update the `nested_category_library_payload` regressions.
