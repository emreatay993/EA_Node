# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P05: Workspace Custom Workflow Authority

## Objective

- Make workspace ownership and custom workflow operations explicit, scoped, and ID-based instead of relying on metadata reconciliation, local/global fallback lookup, or legacy identity matching.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only workspace/custom workflow files needed for this packet

## Preconditions

- `P04` is marked `PASS`.

## Execution Dependencies

- `P04`

## Target Subsystems

- `ea_node_editor/workspace/ownership.py`
- `ea_node_editor/workspace/manager.py`
- `ea_node_editor/custom_workflows/codec.py`
- `ea_node_editor/custom_workflows/file_codec.py`
- `ea_node_editor/custom_workflows/global_store.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workflow_library_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `tests/test_workspace_manager.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/workspace_library_controller_unit/custom_workflow_io.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/serializer/workflow_cases.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P05_workspace_custom_workflow_authority_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/workspace/ownership.py`
- `ea_node_editor/workspace/manager.py`
- `ea_node_editor/custom_workflows/codec.py`
- `ea_node_editor/custom_workflows/file_codec.py`
- `ea_node_editor/custom_workflows/global_store.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workflow_library_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `tests/test_workspace_manager.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/workspace_library_controller_unit/custom_workflow_io.py`
- `tests/main_window_shell/drop_connect_and_workflow_io.py`
- `tests/serializer/workflow_cases.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P05_workspace_custom_workflow_authority_WRAPUP.md`

## Required Behavior

- Move workspace order and active workspace authority to one canonical model/service contract; stop normalizing from `project.metadata["workspace_order"]` as a live fallback path.
- Require the workspace navigation controller surface in project/session flows; delete fallback to the umbrella workspace-library controller once callers are migrated.
- Make custom workflow rename/delete/move operations require explicit `workflow_scope` and `workflow_id`; remove local-first/global-fallback lookup for packet-owned actions.
- Remove legacy one-argument Qt/QML overloads for custom workflow rename/delete once QML passes explicit scope.
- Remove `source_shell_ref_id` and name-based upsert matching from packet-owned current-format custom workflow metadata; stable `workflow_id` is the identity contract.
- Require the versioned global workflow store envelope; do not accept a raw list file as a current store shape.

## Non-Goals

- No general project serializer schema cleanup; that belongs to `P06`.
- No shell graph-action cleanup; that belongs to `P03`.
- No feature changes to custom workflow import/export beyond current-format identity tightening.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_workspace_manager.py tests/test_workspace_library_controller_unit.py tests/workspace_library_controller_unit/custom_workflow_io.py tests/main_window_shell/drop_connect_and_workflow_io.py tests/serializer/workflow_cases.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_workspace_manager.py tests/workspace_library_controller_unit/custom_workflow_io.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P05_workspace_custom_workflow_authority_WRAPUP.md`

## Acceptance Criteria

- Workspace ownership does not depend on metadata reconciliation as a live compatibility layer.
- Custom workflow operations are explicit about scope and ID.
- Tests no longer assert omitted-scope or legacy identity fallback behavior.

## Handoff Notes

- `P06` may still remove old project/session input-shape tolerance that touched the same logical metadata, but it must not reintroduce local/global workflow fallback lookup.
