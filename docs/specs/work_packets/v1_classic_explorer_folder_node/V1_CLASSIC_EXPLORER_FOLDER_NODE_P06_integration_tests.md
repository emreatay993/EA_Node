# V1_CLASSIC_EXPLORER_FOLDER_NODE P06: Integration Tests

## Objective
- Add focused end-to-end regression coverage for the integrated V1 Classic Explorer node across node contract, filesystem service, graph actions, QML surface, inspector/library exposure, persistence, drag-to-Path-Pointer flow, and confirmed mutation behavior.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only test files needed for the integration proof

## Preconditions
- `P01` through `P05` are marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- No later `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`
- `P05`

## Target Subsystems
- `tests/test_integrations_track_f.py`
- `tests/test_folder_explorer_filesystem_service.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/passive_property_editors.py`
- `tests/test_serializer.py`

## Conservative Write Scope
- `tests/test_integrations_track_f.py`
- `tests/test_folder_explorer_filesystem_service.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/passive_property_editors.py`
- `tests/test_serializer.py`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P06_integration_tests_WRAPUP.md`

## Source Public Entry Points
- This packet is test-focused; it exercises the public contracts introduced by `P01` through `P05`.

## Regression Public Entry Points
- Folder explorer node creation, property persistence, listing, command routing, QML command emission, Path Pointer spawn payloads, inspector editing, and confirmed mutation tests.

## State Owner
- Test fixtures own temporary filesystem state.
- No product source state is introduced in this packet.

## Allowed Dependencies
- Existing pytest, Qt offscreen fixtures, and temporary-directory helpers.
- Public source entry points from earlier packets.

## Required Behavior
- Add integration-level tests that exercise the completed `P01` through `P05` feature path.
- Keep destructive filesystem tests isolated to temporary directories.
- Keep tests focused on public contracts rather than private implementation details.
- Document any earlier-packet defect found during integration instead of broadening this packet into feature implementation.

## Required Invariants
- Test fixtures must isolate destructive filesystem operations to temp directories.
- Tests must prove unconfirmed destructive actions do not mutate temp filesystem state.
- Tests must prove confirmed actions mutate only the intended temp path.
- Tests must prove transient Classic Explorer state is not serialized.
- Tests must avoid brittle dependence on local user filesystem paths.

## Non-Goals
- No planned product source changes.
- No visual redesign or new feature behavior.
- No shell-isolation rerun unless a cross-cutting shell risk is discovered and documented.

## Forbidden Shortcuts
- Do not add product code in this packet unless executor remediation explicitly determines a tiny in-scope testability fix is safer than returning the packet for earlier-wave remediation.
- Do not skip destructive-operation tests; keep them temp-directory scoped.
- Do not require a visible desktop session.

## Required Tests
- Add or consolidate integration regressions for navigation, breadcrumb command payloads, row context actions, drag/drop path-pointer payloads, new-window creation, and mutation confirmation.
- Add persistence coverage that includes surface/inspector interactions but serializes only `current_path`.
- Add at least one test proving `io.path_pointer` remains the target for drag-out and send-to-COREX actions.

## Verification Anchor Handoff
- This packet inherits the earlier regression anchors listed in `P01` through `P05`; any assertion updated here must stay non-duplicative and must not leave earlier tests knowingly stale.
- `P07` consumes this packet's evidence for QA closeout and should not change these tests unless a docs/proof check identifies a missing durable requirement link.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py tests/test_folder_explorer_filesystem_service.py tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py tests/test_window_library_inspector.py tests/main_window_shell/passive_property_editors.py tests/test_serializer.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe scripts\run_verification.py --mode fast --dry-run`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_folder_explorer_filesystem_service.py -k folder_explorer --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P06_integration_tests_WRAPUP.md`

## Acceptance Criteria
- Integrated tests cover node creation, browsing/listing, command routing, QML command emission, drag-to-Path-Pointer, and confirmed mutations.
- Tests use temp directories for every destructive filesystem case.
- Fast verification dry-run still assembles.
- No new product behavior is introduced outside the existing packet contracts.

## Handoff Notes
- If this packet exposes a product defect in an earlier packet, prefer executor remediation against the owning earlier packet branch or a focused follow-up before marking this packet `PASS`.
- `P07` consumes the final test evidence for the QA matrix.
