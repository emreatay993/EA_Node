# Cross-Process Viewer Backend Framework for Embedded DPF Sessions

## Summary
- Preserve the current architecture split: the worker remains the DPF authority, and the UI remains the widget host.
- Build the full reusable viewer-backend framework now, not a DPF-only patch.
- Use internal session-scoped temp viewer files as the live transport, even when the node is `output_mode=memory`; do not change user-facing `output_mode` behavior.
- After loading a saved project, a live viewer requires a rerun before it can open; project load may show proxy/session summary state, but not a live embedded render.

## Implementation Changes
1. Execution-side viewer backend framework
- Introduce a generic execution-side viewer backend contract that owns live transport preparation, refresh, cleanup, and camera/playback state round-trip.
- Keep `ViewerSessionService` as the single authority for viewer lifecycle, session identity, liveness, invalidation, and reopen state.
- Extend authoritative session state to include generic backend metadata such as `backend_id`, typed `transport` descriptor, transport revision/version, and a live-open blocker state for “run required”.
- Implement the first concrete backend for DPF: materialize the live dataset in the worker, export a session-scoped temp VTK/PyVista-readable bundle plus manifest/metadata, cache it per session, and release it on close, invalidation, rerun, worker reset, project replacement, and shutdown.

2. Shell-side viewer host framework
- Add a shell-owned viewer host/binding service between the session bridge and the overlay manager.
- Reduce the overlay manager to widget/container lifecycle, visibility, and geometry only; it should never interpret DPF handles or decide how to populate a renderer.
- Introduce a generic widget-binder interface keyed by `backend_id`; the DPF binder becomes the first implementation.
- The DPF binder creates or reuses `QtInteractor`, loads the worker-prepared temp bundle, applies initial camera/session state, and clears/rebinds deterministically on demotion, promotion, close, or transport revision changes.

3. Bridge and QML behavior
- Keep `ViewerSessionBridge` as a projection and intent-forwarding layer, not a second source of viewer truth.
- Update viewer protocol/event payloads so the bridge receives transport descriptors and explicit open blockers rather than only worker-local handle refs.
- Change the viewer surface states so “live unavailable before rerun” is explicit and user-readable instead of falling through to a blank native widget.
- Do not persist live transport data into `.sfe`; project reopen must recreate runtime viewer data via rerun.

## Public Interface Changes
- Add a generic execution viewer-backend interface and a generic shell widget-binder interface, both registry-driven.
- Extend viewer session protocol payloads/events with typed transport metadata and explicit live-open status/blocker fields.
- Add camera-state hydrate/update flow through the authoritative session path; no raw PyVista/VTK objects cross the worker/UI boundary.

## Test Plan
- Execution tests for generic backend contract, DPF temp-transport creation/reuse/release, protocol serialization of transport descriptors, and cleanup on invalidation or worker reset.
- Shell tests for host-service/binder lifecycle, overlay-manager separation, transport revision rebinding, and “run required” projection after project load.
- DPF binder tests with a fake interactor proving the binder loads a temp bundle into the widget instead of only creating the widget.
- Manual/integration checks using `dene3.sfe`: run and open viewer shows populated geometry; save/reopen shows “run required” before rerun; rerun restores live open; `focus_only`/`keep_live`, close, worker reset, and project switch clean up transport and widgets correctly.

## Assumptions
- The spawned worker-process model stays in place.
- Internal temp live-transport files are acceptable and remain separate from user-managed stored outputs.
- User-facing `output_mode` semantics stay unchanged.
- Live viewer reopen after project load does not lazy-recompute and does not persist live runtime seeds into project files.
