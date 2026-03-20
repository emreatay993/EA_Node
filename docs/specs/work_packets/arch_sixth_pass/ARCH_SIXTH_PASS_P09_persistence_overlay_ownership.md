# ARCH_SIXTH_PASS P09: Persistence Overlay Ownership

## Objective
- Replace weakref-style persistence overlay ownership and narrow autosave/session persistence boundaries so persistence-only state stops living as an implicit sidecar on live workspace objects.

## Preconditions
- `P00` through `P08` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P08`

## Target Subsystems
- persistence overlay ownership
- project codec and serializer integration
- session and autosave persistence API shape

## Conservative Write Scope
- `ea_node_editor/persistence/overlay.py`
- `ea_node_editor/graph/model.py`
- `ea_node_editor/persistence/project_codec.py`
- `ea_node_editor/persistence/session_store.py`
- `ea_node_editor/persistence/serializer.py`
- `tests/test_serializer.py`
- `tests/test_serializer_schema_migration.py`
- `tests/test_registry_validation.py`
- `tests/test_shell_project_session_controller.py`
- `docs/specs/work_packets/arch_sixth_pass/P09_persistence_overlay_ownership_WRAPUP.md`

## Required Behavior
- Introduce a clearer persistence-side state contract than the current global weakref overlay map.
- Remove packet-owned live-model compatibility accessors when the packet can replace them with an explicit persistence boundary safely.
- Narrow packet-owned autosave and session flows away from raw `project_doc` handling when a more explicit boundary is available.
- Preserve current-schema `.sfe` behavior, unresolved payload retention, and session/autosave behavior exactly.

## Non-Goals
- No plugin/package provenance changes in this packet.
- No workspace lifecycle authority work in this packet.
- No verification-runner or docs-only work in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py tests/test_shell_project_session_controller.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_serializer.py tests/test_registry_validation.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P09_persistence_overlay_ownership_WRAPUP.md`

## Acceptance Criteria
- Packet-owned persistence overlay ownership is more explicit than the current weakref sidecar pattern.
- Packet-owned session/autosave flows depend less on raw `project_doc` transport.
- Serializer, registry-validation, and session tests pass with unchanged behavior.

## Handoff Notes
- `P10` owns plugin/package provenance cleanup after persistence-side ownership is narrowed.
- Preserve current-schema behavior and unresolved-plugin retention exactly.
