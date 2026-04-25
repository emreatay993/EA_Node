# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P01: No-Legacy Guardrails

## Objective

- Convert compatibility-supporting tests and architecture checks into no-legacy guardrails before broad compatibility deletion begins.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only source/test files needed for this packet

## Preconditions

- `P00` is marked `PASS` in `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md`.
- No later packet from this set is in progress.
- Recent graph-action route merges through `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION` P05 are present on the packet branch.

## Execution Dependencies

- `P00`

## Target Subsystems

- `tests/test_dead_code_hygiene.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_traceability_checker.py`
- `scripts/verification_manifest.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P01_no_legacy_guardrails_WRAPUP.md`

## Conservative Write Scope

- `tests/test_dead_code_hygiene.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_traceability_checker.py`
- `scripts/verification_manifest.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P01_no_legacy_guardrails_WRAPUP.md`

## Required Behavior

- Add a small no-legacy guardrail inventory for packet-owned compatibility names and files that later packets will delete, including `GraphCanvasBridge`, private `_canvas*CompatRef` / `_legacyCanvasViewBridgeRef` aliases, legacy plugin class probing, old project/preference schema compatibility paths, telemetry/import shims, and runtime `project_doc` / `project_path` rebuild paths.
- Update tests that currently assert legacy bridge parity so they either assert the current post-P05 graph-action bridge contract or explicitly mark the legacy assertion as a pre-cleanup anchor owned by later packets.
- Do not delete production code in this packet; this packet is a guardrail and stale-test-preparation packet.
- Keep guardrails semantic-first where practical: prefer AST import/name checks, concrete context-property contract checks, or explicit lists of retired paths over brittle long string snippets.
- Document in the wrap-up which later packet owns each new guardrail category.

## Non-Goals

- No production compatibility removal.
- No docs closeout or QA matrix publication.
- No broad rewrite of traceability rows beyond registering guardrail tokens needed by later packets.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_architecture_boundaries.py tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_architecture_boundaries.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P01_no_legacy_guardrails_WRAPUP.md`

## Acceptance Criteria

- New guardrails identify packet-owned legacy surfaces without failing on code that later packets have not yet removed.
- Existing graph-action route tests reflect the completed `GraphActionController` / `GraphActionBridge` baseline and no longer imply that high-level routing still needs to be implemented.
- Guardrail tests pass with no production edits.

## Handoff Notes

- `P02` inherits graph-canvas and QML bridge guardrails.
- `P09` and `P10` inherit node/plugin/add-on guardrails.
- `P11` inherits runtime payload guardrails.
- `P13` inherits launch/import shim guardrails.
