# P05 Workspace Custom Workflow Authority Wrap-up

## Implementation Summary

- Packet: COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P05 Workspace Custom Workflow Authority
- Branch Label: codex/corex-no-legacy-architecture-cleanup/p05-workspace-custom-workflow-authority
- Commit Owner: worker
- Commit SHA: dddb6716cfebf25831edb8d7395d857f6c773d2e
- Changed Files:
  - ea_node_editor/custom_workflows/codec.py
  - ea_node_editor/custom_workflows/global_store.py
  - ea_node_editor/ui/shell/controllers/project_session_controller.py
  - ea_node_editor/ui/shell/controllers/workflow_library_controller.py
  - ea_node_editor/ui/shell/controllers/workspace_library_controller.py
  - ea_node_editor/ui/shell/presenters/library_presenter.py
  - ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml
  - ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml
  - ea_node_editor/ui_qml/shell_library_bridge.py
  - ea_node_editor/workspace/manager.py
  - ea_node_editor/workspace/ownership.py
  - tests/main_window_shell/drop_connect_and_workflow_io.py
  - tests/serializer/workflow_cases.py
  - tests/test_workspace_library_controller_unit.py
  - tests/test_workspace_manager.py
  - tests/workspace_library_controller_unit/custom_workflow_io.py
  - docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P05_workspace_custom_workflow_authority_WRAPUP.md
- Artifacts Produced:
  - docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P05_workspace_custom_workflow_authority_WRAPUP.md

P05 moved live workspace ordering onto the workspace record order maintained by `WorkspaceManager`, with metadata retained as an emitted mirror rather than a reconciliation fallback. Project session workspace operations now require the focused workspace navigation controller surface.

Custom workflow rename/delete/scope operations now require explicit `workflow_id` and `workflow_scope`. Published subnode workflows use stable workflow IDs, current-format metadata drops `source_shell_ref_id`, name/source fallback upsert matching is removed, ShellLibraryBridge exposes only explicit two-argument rename/delete slots, and the global workflow store now accepts only the versioned envelope shape.

## Verification

PASS: `.\venv\Scripts\python.exe -m pytest tests/test_workspace_manager.py tests/workspace_library_controller_unit/custom_workflow_io.py --ignore=venv -q` (`16 passed, 24 warnings`)
PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_workspace_manager.py tests/test_workspace_library_controller_unit.py tests/workspace_library_controller_unit/custom_workflow_io.py tests/main_window_shell/drop_connect_and_workflow_io.py tests/serializer/workflow_cases.py --ignore=venv -q` (`84 passed, 32 warnings`)
PASS: `git diff --check`

Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing.

Prerequisite: launch the P05 branch with the project virtualenv and a writable user data directory.

1. Publish a subnode as a custom workflow, edit the subnode pin label, publish it again, and confirm the library item updates in place rather than creating a duplicate.
2. Right-click a project-local custom workflow in the node library, rename it, then delete it. Expected result: the context actions operate on that local workflow only and the library refreshes immediately.
3. Move a custom workflow from project-local to global and back to project-local. Expected result: the item changes scope, remains draggable from the library, and persists through a project save/reopen.
4. Create several workspaces, reorder them, save and reopen the project. Expected result: tab order and active workspace are preserved.

## Residual Risks

The required verification commands passed. The only observed warnings were existing Ansys DPF operator rename deprecation warnings from the project environment.

Manual UI smoke testing was not run in this packet execution; the directives above are the recommended human check for the QML context menu and persistence paths.

## Ready for Integration

Yes: P05 is ready for integration after the substantive commit and wrap-up artifact.
