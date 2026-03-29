# Node Execution Model Requirements

## Scope
- Defines when nodes are data-only versus execution-controlled.
- Defines edge-kind compatibility for graph wiring.
- Defines runtime behavior for data dependency evaluation versus exec-triggered steps.

## Node Categories
- `pure`: deterministic transform, no side effects, data ports only.
- `action`: side effect and/or ordered step, requires exec trigger.
- `flow_control`: controls branch/sequence/loop behavior.
- `event_source`: emits exec without exec input (timer/button/file event).
- `event_sink`: terminal effect; may intentionally omit exec output.
- `hybrid`: combines data input/output with exec lifecycle.

## Contracts
- `REQ-NODE-009`: The model shall distinguish execution edges from data edges via explicit port kinds (`exec`, `completed`, `failed`, `data`).
- `REQ-NODE-010`: Port compatibility shall reject kind mismatches (for example `exec` to `data`) and enforce directed source/target orientation for fixed-direction ports. Passive flowchart ports with `direction="neutral"`, `kind="flow"`, `data_type="flow"`, and a cardinal `side` field are the only exception: when both endpoints are neutral flowchart ports, gesture order defines source and target while non-flowchart nodes keep fixed `in` / `out` validation.
- `REQ-NODE-011`: Pure/data-only nodes shall be executable as dependencies when downstream nodes request their outputs, without requiring exec ports.
- `REQ-NODE-012`: Side-effect and ordered-action nodes shall execute only through an exec/event trigger path and may expose failure paths.
- `REQ-NODE-013`: The SDK and docs shall provide explicit author guidance for selecting pure/action/flow/event/hybrid patterns.
- `REQ-NODE-014`: Built-in node catalog shall preserve representative coverage of pure, action/hybrid, and flow/event-oriented nodes.
- `REQ-NODE-015`: Execution preparation shall compile nested subnode shells/pins into a flat runtime graph while preserving node IDs used for diagnostics and UI focus.
- `REQ-NODE-018`: execution preparation shall exclude passive nodes (`runtime_behavior="passive"`) and passive `flow` edges from compiled/runtime graphs while leaving them intact in the authored workspace document.
- `REQ-NODE-019`: graph validation and connection authoring shall use registry-aware multiplicity rules so passive `flow` inputs, including neutral cardinal flowchart ports, can opt into multiple incoming edges without weakening executable-port validation.
- `REQ-NODE-023`: execution data flow shall allow stored-output adopters to replace oversized inline payloads with `RuntimeArtifactRef` values while downstream nodes resolve the referenced local file within the same run from runtime-snapshot and project artifact metadata.
- `REQ-NODE-024`: the first shipped heavy-output adopter shall remain explicit and user-controlled: `io.process_run` switches only between `memory` and `stored`, and `stored` mode stages stdout/stderr transcripts instead of adding automatic size-based switching.
- `REQ-NODE-026`: cross-process viewer execution shall keep playback and live/proxy state session-owned: `dpf.viewer` may publish projection-safe summaries into graph state, but live promotion, demotion, one-live arbitration, `backend_id` / `transport_revision`, and session-scoped temp transport bundle lifecycle shall occur through the worker `ViewerSessionService` even when the node stays `output_mode=memory`; project reload and worker reset shall reopen only as blocked rerun-required projection until rerun recreates live transport.

## Authoring Guidance
- Use data-only ports when evaluation is deterministic and externally invisible.
- Add exec ports when operation performs file/process/network/UI/state effects or depends on ordering.
- For fallible actions, expose a failure path (`failed` or equivalent) and include error payloads.
- Keep type IDs and external plugin import surface stable when refactoring internals.

## Acceptance
- `AC-REQ-NODE-009-01`: Port kind schema and registry validation tests verify allowed port kinds and declarations.
- `AC-REQ-NODE-010-01`: Graph wiring tests verify mismatched or directionally invalid non-flowchart connections are rejected, while neutral flowchart authoring keeps gesture-ordered source/target assignment without regressing fixed-direction validation.
- `AC-REQ-NODE-011-01`: Worker execution tests verify dependency data propagation for connected data edges.
- `AC-REQ-NODE-012-01`: Process/action execution tests verify exec-triggered behavior, completion, and failure/cancel handling.
- `AC-REQ-NODE-013-01`: SDK docs expose plugin author contract and examples for node definition.
- `AC-REQ-NODE-014-01`: Bootstrap registry includes built-in node families that exercise pure, hybrid/action, and flow/event usage.
- `AC-REQ-NODE-015-01`: Nested subnode workflows execute through the existing worker engine, and runtime failures map back to authored node IDs for scope-aware focus.
- `AC-REQ-NODE-018-01`: passive runtime-wiring and worker regressions verify passive nodes and `flow` edges never reach compiled/runtime execution graphs.
- `AC-REQ-NODE-019-01`: graph-scene and runtime-wiring regressions verify registry-declared multi-connection `flow` inputs, including neutral cardinal flowchart ports, are accepted without regressing exec/data edge validation.
- `AC-REQ-NODE-023-01`: execution worker, client, and integration regressions confirm runtime artifact refs cross the queue boundary and downstream file-backed nodes resolve them successfully within the same run.
- `AC-REQ-NODE-024-01`: `Process Run` regressions confirm `memory` keeps inline strings, `stored` emits staged transcript refs, and stored-mode failures clean up staged transcript artifacts instead of leaving broken refs behind.
- `AC-REQ-NODE-026-01`: viewer-node, worker-service, bridge, restore, and viewer-surface regressions confirm session-owned live/proxy transitions, `output_mode=memory` live transport bundling, rerun-required reopen blocking, and post-rerun restoration without reintroducing multi-set viewer payloads into ordinary graph execution.
