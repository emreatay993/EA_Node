# COREX Architecture Entry Point Reduction Plan

## Summary

- This plan has been converted into a subagent-ready work-packet set.
- Packet directory: `docs/specs/work_packets/corex_architecture_entry_point_reduction/`
- Execution target: reduce graph UI action breadcrumbing by merging PyQt menu actions, shortcuts, QML context-menu actions, and node delegate high-level actions behind one canonical graph action contract, `GraphActionController`, and `GraphActionBridge`.
- Strategy: aggressive internal merge after each replacement route is verified. Preserve all user-visible behavior, saved data, menu labels, shortcuts, context-menu items, launch commands, and existing capabilities.

## Key Changes

- Add `GraphActionId` / `GraphActionSpec` contract metadata for high-level graph UI verbs.
- Add `GraphActionController` as the internal owner for high-level graph UI actions.
- Add `GraphActionBridge` as the QML-facing dispatch surface.
- Route PyQt menu and shortcut paths through the controller.
- Route QML graph context menus and node delegate high-level actions through the bridge.
- Keep low-level canvas operations in existing owners: selection, movement, resize, viewport, port drag, geometry updates, and direct scene policy checks.
- Publish architecture docs and QA evidence after the route merge.

## Public Interface Changes

- No user-facing behavior changes.
- Menu labels, shortcuts, context-menu items, project schema, node plugins, app launch commands, and saved files remain compatible.
- Internal QML gains `graphActionBridge`; obsolete high-level `GraphCanvasCommandBridge.request_*` action slots may be removed only after app QML and tests no longer use them.

## Execution Tasks

### T01 Action Inventory Guardrails

- Goal: create the canonical action contract and static tests for PyQt/QML action coverage.
- Preconditions: `P00` packet docs are available.
- Conservative write scope: `ea_node_editor/ui/shell/graph_action_contracts.py`, `tests/test_graph_action_contracts.py`.
- Deliverables: action contract, action inventory tests, `P01_action_inventory_guardrails_WRAPUP.md`.
- Verification: packet `P01` verification commands.
- Non-goals: no runtime route changes.
- Packetization notes: maps to `P01`.

### T02 Canonical Controller and Bridge

- Goal: add `GraphActionController`, `GraphActionBridge`, and QML context wiring while old routes still work.
- Preconditions: `P01` is `PASS`.
- Conservative write scope: shell controller, QML bridge, shell composition/bootstrap tests.
- Deliverables: controller, bridge, bootstrap assertions, `P02_canonical_controller_and_bridge_WRAPUP.md`.
- Verification: packet `P02` verification commands.
- Non-goals: do not rewire PyQt or QML callers yet.
- Packetization notes: maps to `P02`.

### T03 PyQt Action Route Merge

- Goal: route shell menu actions and shortcuts through the controller and remove redundant PyQt wrappers when safe.
- Preconditions: `P02` is `PASS`.
- Conservative write scope: `window_actions.py`, `workspace_graph_actions.py`, inherited shell/action tests.
- Deliverables: PyQt route merge, compatibility delegate cleanup, `P03_pyqt_action_route_merge_WRAPUP.md`.
- Verification: packet `P03` verification commands.
- Non-goals: no QML context-menu rewrite.
- Packetization notes: maps to `P03`.

### T04 QML Action Route Merge

- Goal: route graph context menus and node delegate high-level actions through the bridge and remove obsolete high-level command bridge slots when safe.
- Preconditions: `P03` is `PASS`.
- Conservative write scope: graph canvas QML, graph action bridge/controller, high-level command bridge slots, inherited QML/shell tests.
- Deliverables: QML route merge, command bridge cleanup, `P04_qml_action_route_merge_WRAPUP.md`.
- Verification: packet `P04` verification commands.
- Non-goals: keep low-level canvas movement/selection/port/viewport operations in existing owners.
- Packetization notes: maps to `P04`.

### T05 Closeout Docs and Metrics

- Goal: update architecture docs, QA matrix, spec index, and maintainability metrics.
- Preconditions: `P04` is `PASS`.
- Conservative write scope: `ARCHITECTURE.md`, docs/spec index, QA matrix, documentation checks.
- Deliverables: architecture ownership map, QA evidence, `P05_closeout_docs_and_metrics_WRAPUP.md`.
- Verification: packet `P05` verification commands.
- Non-goals: no graph mutation, runtime, plugin registration, or verification/devtools cleanup.
- Packetization notes: maps to `P05`.

## Work Packet Conversion Map

- `P00 Bootstrap`: create packet docs, status ledger, execution waves, standalone prompts, and spec-index registration. Status: `PASS`.
- `P01 Action Inventory Guardrails`: create the canonical action contract and static tests for PyQt/QML action coverage.
- `P02 Canonical Controller and Bridge`: add `GraphActionController`, `GraphActionBridge`, and QML context wiring while old routes still work.
- `P03 PyQt Action Route Merge`: route shell menu actions and shortcuts through the controller and remove redundant PyQt wrappers when safe.
- `P04 QML Action Route Merge`: route graph context menus and node delegate high-level actions through the bridge and remove obsolete high-level command bridge slots when safe.
- `P05 Closeout Docs and Metrics`: update architecture docs, QA matrix, spec index, and maintainability metrics.

## Execution Waves

- Wave 1: `P01`
- Wave 2: `P02`
- Wave 3: `P03`
- Wave 4: `P04`
- Wave 5: `P05`

Execution is sequential because later packets inherit action-contract and shell/QML regression anchors from earlier packets.

## Test Plan

- Use the project venv: `.\venv\Scripts\python.exe`.
- Packet-owned verification is defined in each packet spec.
- The overall packet family uses these main anchors:
  - `tests/test_graph_action_contracts.py`
  - `tests/test_main_window_shell.py`
  - `tests/main_window_shell/bridge_contracts_graph_canvas.py`
  - `tests/main_window_shell/comment_backdrop_workflows.py`
  - `tests/main_window_shell/passive_style_context_menus.py`
  - `tests/test_graph_scene_bridge_bind_regression.py`
  - `tests/test_markdown_hygiene.py`
  - `tests/test_traceability_checker.py`

## Assumptions

- Target merge branch is `main`.
- Workers should treat the saved packet docs as the only source of truth.
- `P00` is documentation/bootstrap only and is already marked `PASS`.
- Implementation workers use `gpt-5.5` with `xhigh` reasoning.
- Existing dirty worktree changes outside this packet set are unrelated unless the executor detects a direct conflict.

## Exact Fresh-Thread Prompt

```text
Use C:\Users\emre_\.codex\skills\subagent-work-packet-executor\SKILL.md.

Target merge branch: main.

Execute the already-bootstrapped packet set for COREX Architecture Entry Point Reduction at:

docs/specs/work_packets/corex_architecture_entry_point_reduction/

Treat the saved packet docs as the only source of truth. Confirm P00 is present and PASS, confirm the manifest has Execution Waves, then execute the first pending wave using worker subagents as defined by the executor skill. The goal is to reduce graph UI action breadcrumbing by merging PyQt menu actions, shortcuts, QML context-menu actions, and node delegate high-level actions behind the canonical GraphActionController and GraphActionBridge route while preserving all user-visible behavior and existing capabilities.

Use the project venv for packet verification commands. Stay inside each packet's Conservative Write Scope, require wrap-up artifacts, run validators and Review Gates, update the shared status ledger only from the executor, and stop when the packet set is either ready for merge into main or blocked by a terminal packet failure.
```
