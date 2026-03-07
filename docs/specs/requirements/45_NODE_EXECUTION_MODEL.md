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
- `REQ-NODE-010`: Port compatibility shall reject kind mismatches (for example `exec` to `data`) and enforce directed source/target orientation.
- `REQ-NODE-011`: Pure/data-only nodes shall be executable as dependencies when downstream nodes request their outputs, without requiring exec ports.
- `REQ-NODE-012`: Side-effect and ordered-action nodes shall execute only through an exec/event trigger path and may expose failure paths.
- `REQ-NODE-013`: The SDK and docs shall provide explicit author guidance for selecting pure/action/flow/event/hybrid patterns.
- `REQ-NODE-014`: Built-in node catalog shall preserve representative coverage of pure, action/hybrid, and flow/event-oriented nodes.

## Authoring Guidance
- Use data-only ports when evaluation is deterministic and externally invisible.
- Add exec ports when operation performs file/process/network/UI/state effects or depends on ordering.
- For fallible actions, expose a failure path (`failed` or equivalent) and include error payloads.
- Keep type IDs and external plugin import surface stable when refactoring internals.

## Acceptance
- `AC-REQ-NODE-009-01`: Port kind schema and registry validation tests verify allowed port kinds and declarations.
- `AC-REQ-NODE-010-01`: Graph wiring tests verify mismatched/directionally invalid connections are rejected.
- `AC-REQ-NODE-011-01`: Worker execution tests verify dependency data propagation for connected data edges.
- `AC-REQ-NODE-012-01`: Process/action execution tests verify exec-triggered behavior, completion, and failure/cancel handling.
- `AC-REQ-NODE-013-01`: SDK docs expose plugin author contract and examples for node definition.
- `AC-REQ-NODE-014-01`: Bootstrap registry includes built-in node families that exercise pure, hybrid/action, and flow/event usage.
