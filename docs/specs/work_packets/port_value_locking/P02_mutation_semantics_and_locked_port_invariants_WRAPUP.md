# P02 Mutation Semantics And Locked Port Invariants Wrap-Up

## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/port-value-locking/p02-mutation-semantics-and-locked-port-invariants`
- Commit Owner: `worker`
- Commit SHA: `1fe2cd8e5e048261dadba6823a5966dd3a8bb280`
- Changed Files: `docs/specs/work_packets/port_value_locking/P02_mutation_semantics_and_locked_port_invariants_WRAPUP.md`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/graph/transform_fragment_ops.py`, `ea_node_editor/ui/graph_interactions.py`, `tests/graph_track_b/scene_model_graph_scene_suite.py`, `tests/test_port_locking.py`
- Artifacts Produced: `docs/specs/work_packets/port_value_locking/P02_mutation_semantics_and_locked_port_invariants_WRAPUP.md`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/graph/transform_fragment_ops.py`, `ea_node_editor/ui/graph_interactions.py`, `tests/graph_track_b/scene_model_graph_scene_suite.py`, `tests/test_port_locking.py`

P02 makes `locked_ports` enforceable in the validated mutation layer instead of keeping it as passive state. Node creation now seeds lock state from normalized defaults, property edits can auto-lock and prune now-illegal incoming edges, manual `set_locked_port` rejects non-lockable ports and preserves property values, backend edge validation rejects locked targets with a stable user-facing reason, and graph-fragment copy/paste preserves lock state through normalization and restore. The owned graph-scene tests were updated to use an explicit backend unlock where they intentionally wire into `core.logger.message`, and `GraphInteractions.connect_ports()` now returns the same locked-target rejection reason before attempting the scene mutation.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py tests/graph_track_b/scene_model_graph_scene_suite.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py --ignore=venv -q`

- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

- Prerequisites: launch the application from this branch and open a workspace with the standard graph canvas.
- Test 1: Add a `Constant` node and a `Logger` node, then try to connect `Constant.as_text` to `Logger.message`. Expected result: the connection is rejected and no edge is created because `Logger.message` starts locked from its non-empty default value.
- Test 2: Add a `Constant` node and a `Process Run` node, then connect `Constant.as_text` to `Process Run.command`. Expected result: the edge is created because `Process Run.command` starts empty and unlocked.
- Test 3: With the `Process Run` node still connected, edit `command` to any non-empty string such as `python --version`. Expected result: the existing incoming edge to `command` disappears immediately, and a new attempt to reconnect into `command` is rejected while the property stays unchanged.

## Residual Risks

- Manual lock and unlock now exist in the backend mutation service, but this packet intentionally does not expose a scene bridge slot or QML gesture for that control yet; UI-side manual toggle coverage remains deferred to later packets.
- Built-in nodes with meaningful default primitive inputs, such as `core.logger.message`, now start locked by construction; packet-owned tests that intentionally wire those ports need explicit backend unlock setup until later packets expose authored lock control in the scene.
- Pytest completed with exit code `0`, but the Windows environment still emitted a non-failing temp-directory cleanup `PermissionError` during process shutdown.

## Ready for Integration

- Yes: P02 enforces the locked-port mutation invariants in backend mutations and fragment restore paths, the packet verification passed, and the current scene-level interaction entry point now reports the expected locked-target failure reason.
