# Execution Edge Progress Visualization

## Summary
- Extend the existing execution-visualization system from nodes to authored control edges: `exec`, `completed`, and `failed`.
- During an active run, control edges start dimmed. When an edge progresses, it returns to its normal look and plays a brief one-shot flash.
- The state is in-memory only, filtered to the active run workspace, and cleared when the run starts fresh, ends, stops, fatally fails, or the project session is closed/reopened.

## Key Changes
- State and interfaces:
  - Add `progressed_execution_edge_ids: set[str]` to `ShellRunState`.
  - Add `mark_execution_edges_progressed(workspace_id, edge_ids)` to the shell/window execution-state helpers.
  - Expose `progressed_execution_edge_lookup` from `GraphCanvasStateBridge` and forward it through the existing GraphCanvas bindings.
  - Keep using the existing execution-visualization signal/revision path instead of introducing a second signal.
- Run-event projection:
  - On `run_started`, build a per-run authored-edge index from the selected workspace snapshot, grouped by `source_node_id` and source port kind.
  - On `node_completed`, mark that source node’s authored `exec` and `completed` edges as progressed.
  - Add a new worker event `node_failed_handled` with `run_id`, `workspace_id`, `node_id`, and `error`.
  - Emit `node_failed_handled` when a node throws but execution continues through failure handlers, then use it in the run controller to mark that source node’s authored `failed` edges as progressed.
  - Use authored workspace edges, not flattened runtime edges, as the UI source of truth because the canvas renders authored edge ids and the runtime compiler currently strips edge ids during flattening.
- Edge rendering:
  - Treat an edge as an execution edge when its source port kind is `exec`, `completed`, or `failed`.
  - Add snapshot metadata for edge tests and rendering: `executionProgressed`, `executionDimmed`, and `executionFlashProgress`.
  - Visual defaults:
    - Unprogressed control edge: `0.35` alpha and `1.7px` base width.
    - Progressed control edge: current normal stroke/color/width.
    - First progress transition: `240ms` QML-local flash using a secondary stroke in the edge’s current base color, `+1.4px` wider, alpha easing from `0.55` to `0.0`.
  - Selection and preview keep their current interaction colors and widths; they do not get dimmed, but the flash can still layer on top.
  - Data edges and passive flow edges remain unchanged.
- Docs and traceability:
  - Treat this as an extension of the existing node-execution visualization packet, not a new packet.
  - Update the existing requirement text and QA matrix to mention dim-before-progress execution edges, post-progress flash, `node_failed_handled`, active-workspace filtering, and no persistence.

## Test Plan
- Run-controller coverage:
  - `run_started` clears progressed edge state.
  - `node_completed` marks authored `exec` and `completed` edge ids.
  - `node_failed_handled` marks authored `failed` edge ids.
  - Terminal events clear edge state together with node state.
  - Nonfatal handled failures preserve current-run visualization until the run actually ends.
- Shell/QML coverage:
  - Before progress, visible control edges are dimmed.
  - After progress, they return to normal and briefly flash.
  - Failed-branch edges progress through `node_failed_handled`.
  - Non-control edges stay unchanged.
  - Selected/previewed edges are not dimmed.
  - Run completion/stop/fatal failure clears the edge state.
- Traceability:
  - Update the existing node-execution QA matrix and requirement packet, then rerun the current node-execution regression and traceability checks.

## Assumptions And Defaults
- “Execution edges” means authored control edges only: `exec`, `completed`, and `failed`.
- The feature is active-run only and is never persisted to project files.
- The per-run authored-edge index is intentionally frozen from the run-start workspace snapshot so it matches the run’s execution snapshot even if the graph is edited mid-run.
