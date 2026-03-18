# DEAD_CODE_HYGIENE P02: Internal Python Helper Cleanup

## Objective
- Remove the approved internal dead helpers and only the directly adjacent dead imports in the touched modules, without widening into broader symbol or API cleanup.

## Preconditions
- `P00` is marked `PASS` in [DEAD_CODE_HYGIENE_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md).
- `P01` is marked `PASS` because this packet set is intentionally sequential.
- No later `DEAD_CODE_HYGIENE` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/ui/shell/library_flow.py`
- `ea_node_editor/ui_qml/edge_routing.py`

## Conservative Write Scope
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/ui/shell/library_flow.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `tests/test_execution_client.py` only if the packet uncovers a directly adjacent stale import/reference that must be repaired to keep the approved verification slice green
- `tests/test_execution_worker.py` only if the packet uncovers a directly adjacent stale import/reference that must be repaired to keep the approved verification slice green
- `tests/test_window_library_inspector.py` only if the packet uncovers a directly adjacent stale import/reference that must be repaired to keep the approved verification slice green
- `tests/test_graph_track_b.py` only if the packet uncovers a directly adjacent stale import/reference that must be repaired to keep the approved verification slice green
- `tests/test_icon_registry.py` only if the packet uncovers a directly adjacent stale import/reference that must be repaired to keep the approved verification slice green
- `docs/specs/work_packets/dead_code_hygiene/P02_internal_python_helper_cleanup_WRAPUP.md`

## Required Behavior
- Remove `dict_to_event_type` from `ea_node_editor/execution/protocol.py`.
- Remove `input_port_is_available` from `ea_node_editor/ui/shell/library_flow.py`.
- Remove `inline_body_height` from `ea_node_editor/ui_qml/edge_routing.py`.
- Remove only the directly adjacent imports made dead by those deletions in the same touched modules.
- Keep surrounding runtime behavior and dataclass/adapter contracts stable.
- If local tooling such as `vulture` or lint checks reports additional unused symbols in the same modules, do not remove them unless they are directly adjacent import cleanup caused by the approved helper deletions.
- Keep the packet scoped away from broader package/public-surface cleanup, especially:
  - `AsyncNodePlugin`
  - `icon_names`
  - `list_installed_packages`
  - `uninstall_package`
  - package `__init__` re-export surfaces

## Non-Goals
- No QML property cleanup. `P01` owns that.
- No new dead-code audit tests. `P03` owns regression locks.
- No removal of broader unused protocol adapters, helpers, or public-looking surfaces even if tooling flags them.
- No serializer/schema, execution-semantics, or UI behavior changes.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_icon_registry.py tests/test_window_library_inspector.py tests/test_execution_client.py tests/test_execution_worker.py tests/test_graph_track_b.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_execution_worker.py tests/test_window_library_inspector.py -q`

## Expected Artifacts
- `docs/specs/work_packets/dead_code_hygiene/P02_internal_python_helper_cleanup_WRAPUP.md`

## Acceptance Criteria
- The verification command passes.
- The review gate passes.
- Only the approved helper removals and directly adjacent import cleanup land in the touched runtime modules.
- No additional public-looking or package-surface symbols are removed.
- Execution protocol behavior, library/inspector behavior, and edge-routing behavior remain unchanged apart from the eliminated dead helper seams.

## Handoff Notes
- `P03` should add a narrow static guard so these helpers do not silently reappear.
- If any adjacent import cleanup was intentionally retained because it is still live, document that decision so `P03` does not convert it into a false-positive lock.
