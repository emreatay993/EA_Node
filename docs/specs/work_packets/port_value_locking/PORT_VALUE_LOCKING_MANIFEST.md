# PORT_VALUE_LOCKING Work Packet Manifest

- Date: `2026-04-12`
- Integration base: `main`
- Published packet window: `P00` through `P06`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md](../../../../PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md) into an execution-ready, strictly sequential packet set that adds persisted primitive-port lock state; one-way auto-lock on meaningful inline/default values; backend rejection for locked incoming targets; scene payload and authoring seams for manual port lock toggles; Variant A locked-port chrome in the graph node surface; per-view hide-locked and hide-optional decluttering controls with empty-canvas gestures; and retained verification, QA, and traceability evidence.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md](../../../../PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md`

## Retained Packet Order

1. `PORT_VALUE_LOCKING_P00_bootstrap.md`
2. `PORT_VALUE_LOCKING_P01_state_contract_and_persistence.md`
3. `PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants.md`
4. `PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters.md`
5. `PORT_VALUE_LOCKING_P04_locked_port_qml_ux.md`
6. `PORT_VALUE_LOCKING_P05_canvas_hide_gestures.md`
7. `PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/port-value-locking/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and tracking rules for the port value locking packet set |
| P01 State Contract and Persistence | `codex/port-value-locking/p01-state-contract-and-persistence` | Add durable node and view state, lockability helpers, effective-port lock metadata, and persistence-safe round-trip coverage |
| P02 Mutation Semantics and Locked Port Invariants | `codex/port-value-locking/p02-mutation-semantics-and-locked-port-invariants` | Make lock state meaningful in validated graph mutations, creation/property auto-lock flows, fragment copy paths, and backend connection rejection |
| P03 Payload Projection and View Filters | `codex/port-value-locking/p03-payload-projection-and-view-filters` | Expose locked and optional payload fields, add scene-facing view filter mutations, and filter rows from payloads without QML gesture work yet |
| P04 Locked Port QML UX | `codex/port-value-locking/p04-locked-port-qml-ux` | Adopt Variant A locked-port chrome, manual double-click toggle routing, and locked-port interaction suppression in the graph surface |
| P05 Canvas Hide Gestures | `codex/port-value-locking/p05-canvas-hide-gestures` | Add empty-canvas hide-locked and hide-optional gestures on top of the retained view-filter state and bridge plumbing |
| P06 Verification Docs Traceability Closeout | `codex/port-value-locking/p06-verification-docs-traceability-closeout` | Publish retained QA evidence, requirement updates, and traceability closeout for the shipped port value locking behavior |

## Locked Defaults

- A port is lockable only when it is an input data port with `data_type` in `{"int", "float", "bool", "str"}` and a same-key `PropertySpec` exists on the owning node type.
- Lock-triggering values remain exactly the user-approved rules from the review baseline: non-zero `int`, non-zero `float`, `True` `bool`, and non-empty trimmed `str`.
- Auto-lock is one-way. Creation-time and property-edit-time helpers may set a lock, but they never auto-unlock a locked port after the value returns to zero or empty.
- Manual lock and unlock do not rewrite the property value. They only change whether the port is eligible as an incoming-edge target.
- Locked primitive rows keep their existing inline property editors in `GraphInlinePropertiesLayer.qml`; the padlock treatment changes the port chrome and edge eligibility only.
- Backend validation must reject new incoming connections to locked target ports even if stale QML payload still offers a drag target.
- Per-view `hide_locked_ports` and `hide_optional_ports` are persisted on `ViewState`; they are view-local decluttering toggles, not node data.
- This packet set stays strictly sequential. No non-bootstrap packet shares a wave.
- When a later packet changes an earlier packet's asserted payload or bridge surface, the later packet inherits and updates that earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

### Wave 5
- `P05`

### Wave 6
- `P06`

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md`
- Visual basis: `port_value_locking_variants.html`
- Spec contract: `PORT_VALUE_LOCKING_P00_bootstrap.md` through `PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P06`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P06_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md`
- Status ledger: [PORT_VALUE_LOCKING_STATUS.md](./PORT_VALUE_LOCKING_STATUS.md)

## Standard Thread Prompt Shell

`Implement PORT_VALUE_LOCKING_PXX_<name>.md exactly. Before editing, read PORT_VALUE_LOCKING_MANIFEST.md, PORT_VALUE_LOCKING_STATUS.md, and PORT_VALUE_LOCKING_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update PORT_VALUE_LOCKING_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
