# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK Work Packet Manifest

- Date: `2026-03-29`
- Integration base: `main`
- Published packet window: `P00` through `P06`
- Scope baseline: convert the cross-process viewer backend framework plan into an execution-ready packet set that keeps the worker as the DPF authority and the UI as the widget host, introduces a generic registry-driven execution backend plus shell binder framework, uses session-scoped temp viewer bundles as the live transport even when node `output_mode=memory`, carries typed transport descriptors and explicit live-open blockers through the authoritative viewer session path, preserves current user-facing `output_mode` semantics, and closes with verification, QA-matrix, and traceability evidence for embedded DPF sessions as the first concrete backend.
- Review baseline: [docs/Cross-Process Viewer Backend Framework for Embedded DPF Sessions.md](../../../Cross-Process%20Viewer%20Backend%20Framework%20for%20Embedded%20DPF%20Sessions.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md`
2. `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract.md`
3. `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization.md`
4. `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_shell_viewer_host_framework.md`
5. `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption.md`
6. `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states.md`
7. `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/cross-process-viewer-backend-framework/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and git tracking for the new packet set |
| P01 Execution Viewer Backend Contract | `codex/cross-process-viewer-backend-framework/p01-execution-viewer-backend-contract` | Introduce the generic execution-side backend/session contract with typed transport and blocker payloads |
| P02 DPF Transport Bundle Materialization | `codex/cross-process-viewer-backend-framework/p02-dpf-transport-bundle-materialization` | Implement the first concrete DPF backend that exports, reuses, and cleans session-scoped temp transport bundles |
| P03 Shell Viewer Host Framework | `codex/cross-process-viewer-backend-framework/p03-shell-viewer-host-framework` | Add the shell-owned host/binder framework and reduce the overlay manager to geometry and container ownership only |
| P04 DPF Widget Binder Transport Adoption | `codex/cross-process-viewer-backend-framework/p04-dpf-widget-binder-transport-adoption` | Make the DPF binder load worker-prepared transport into `QtInteractor` and rebind deterministically on revision changes |
| P05 Bridge Projection Run-Required States | `codex/cross-process-viewer-backend-framework/p05-bridge-projection-run-required-states` | Reduce the bridge to projection plus intent forwarding and surface explicit run-required blocker states after project reload |
| P06 Verification Docs Traceability Closeout | `codex/cross-process-viewer-backend-framework/p06-verification-docs-traceability-closeout` | Publish QA evidence, requirement updates, and traceability closeout for the shipped framework |

## Locked Defaults

- The worker remains the DPF authority and the UI remains the widget host; no packet may move raw DPF/PyVista/VTK ownership into the shell.
- The framework is generic and registry-driven. `backend_id` and shell binder registration must support future backends even though DPF is the first concrete implementation.
- `ViewerSessionService` is the single authority for viewer lifecycle, session identity, liveness, invalidation, reopen state, transport revision, and camera/playback snapshots.
- Viewer protocol payloads and events must carry typed transport descriptors, `backend_id`, `transport_revision`, and explicit live-open status or blocker fields; raw worker-local renderer objects and raw DPF dataset objects must not cross the worker/UI boundary.
- Internal session-scoped temp viewer files are the live transport even when the node is `output_mode=memory`; user-facing `output_mode` behavior and stored-output semantics remain unchanged.
- The shell overlay manager owns widget/container lifecycle, visibility, and geometry only after `P03`; renderer population belongs to host-service binder implementations.
- Saved projects and autosave recovery must not persist live transport bundle data into `.sfe`; after project load, viewer UI may project summary or proxy state, but live open remains blocked until rerun recreates transport.
- Cleanup for live transport and bound widgets must occur on close, invalidation, rerun, worker reset, project replacement, and shutdown.
- When a later packet changes an earlier packet's asserted seam, the later packet inherits and updates the earlier regression anchor inside its own write scope.

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

- Spec contract: `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md` through `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P06`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P06_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md`
- Status ledger: [CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md](./CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md)

## Standard Thread Prompt Shell

`Implement CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_PXX_<name>.md exactly. Before editing, read CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md, CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md, and CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
