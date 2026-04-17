# MEDIA_VIEWER_CONTENT_FULLSCREEN Work Packet Manifest

- Date: `2026-04-17`
- Integration base: `main`
- Published packet window: `P00` through `P05`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/Media And Viewer Content Fullscreen.md](../../../../PLANS_TO_IMPLEMENT/in_progress/Media%20And%20Viewer%20Content%20Fullscreen.md) into an execution-ready packet set that adds a transient shell-owned fullscreen overlay for media and DPF viewer nodes, exposes a `contentFullscreenBridge`, wires media/viewer surface affordances and `F11`, retargets the existing native viewer host into the fullscreen viewport, and closes with focused regression evidence.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/Media And Viewer Content Fullscreen.md](../../../../PLANS_TO_IMPLEMENT/in_progress/Media%20And%20Viewer%20Content%20Fullscreen.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md`

## Retained Packet Order

1. `MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md`
2. `MEDIA_VIEWER_CONTENT_FULLSCREEN_P01_fullscreen_state_contract.md`
3. `MEDIA_VIEWER_CONTENT_FULLSCREEN_P02_shell_overlay_and_media_renderer.md`
4. `MEDIA_VIEWER_CONTENT_FULLSCREEN_P03_surface_buttons_and_shortcut.md`
5. `MEDIA_VIEWER_CONTENT_FULLSCREEN_P04_interactive_live_viewer_retargeting.md`
6. `MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/media-viewer-content-fullscreen/p00-bootstrap` | Establish packet docs, status ledger, execution waves, and spec-index registration |
| P01 Fullscreen State Contract | `codex/media-viewer-content-fullscreen/p01-fullscreen-state-contract` | Add the shell-owned `contentFullscreenBridge` contract, node eligibility checks, normalized payloads, and cleanup lifecycle |
| P02 Shell Overlay and Media Renderer | `codex/media-viewer-content-fullscreen/p02-shell-overlay-and-media-renderer` | Add the in-app fullscreen overlay, media rendering path, viewport object names, and fullscreen icon registration |
| P03 Surface Buttons and Shortcut | `codex/media-viewer-content-fullscreen/p03-surface-buttons-and-shortcut` | Add media/viewer node fullscreen affordances, preserve interactive rect routing, and wire `F11` open/close behavior |
| P04 Interactive Live Viewer Retargeting | `codex/media-viewer-content-fullscreen/p04-interactive-live-viewer-retargeting` | Retarget the existing native viewer overlay host into the fullscreen viewport and restore it on close |
| P05 Regression Closeout | `codex/media-viewer-content-fullscreen/p05-regression-closeout` | Publish integrated regression coverage, manual smoke checklist, QA evidence, and traceability closeout |

## Locked Defaults

- Fullscreen content is an in-app shell overlay, not OS or app-window fullscreen.
- Only one content fullscreen overlay may be active at a time.
- Fullscreen state is transient UI state and must not be serialized into `.sfe` project files.
- `contentFullscreenBridge` is a shell context property and owns `open`, `node_id`, `workspace_id`, `content_kind`, `title`, `media_payload`, `viewer_payload`, `last_error`, and `content_fullscreen_changed`.
- Bridge slots are `request_open_node(node_id) -> bool`, `request_toggle_for_node(node_id) -> bool`, `request_close()`, and `can_open_node(node_id) -> bool`.
- Eligible fullscreen content kinds are image media, PDF media, and DPF viewer nodes. Ineligible nodes must leave the bridge closed and report a graph hint or bridge error without mutating graph data.
- Media fullscreen reuses the node preview source, crop, page, and fit semantics for viewing only. It must not edit crop, page, source, or node properties.
- The overlay closes through `Esc`, `F11`, and the close button.
- `F11` closes when fullscreen is already open. Otherwise it opens the single selected eligible media/viewer node and shows a graph hint when there is no single eligible selected node.
- `embeddedInteractiveRects` must continue to cover any fullscreen buttons so node drag, selection, and resize gestures do not steal button clicks.
- Live viewer fullscreen reuses the existing native viewer widget and overlay host. It must not create a second viewer widget for the same `(workspace_id, node_id)`.
- The fullscreen viewer viewport object name is `contentFullscreenViewerViewport`.
- The viewer host must restore the native widget to the node viewport on close, workspace switch, or node deletion, and must not orphan overlay containers.
- The feature scope excludes double-click fullscreen, node context-menu fullscreen, a top-level native fullscreen window, PDF page editing, crop editing, camera-control redesign, and automatic workflow reruns for blocked viewer data.
- P01 must pass before every implementation packet. P02 must pass before P03 and P04 because it owns the overlay viewport and fullscreen icon. P03 and P04 may run in parallel after P02 because their source write scopes are disjoint. P05 must wait for every implementation packet.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`
- `P04`

### Wave 4
- `P05`

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/Media And Viewer Content Fullscreen.md`
- Related viewer precedent: `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md`
- Icon and QML packet precedent: `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md`
- Spec contract: `MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md` through `MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P05`
- Packet wrap-ups: `P01_fullscreen_state_contract_WRAPUP.md` through `P05_regression_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md`
- Status ledger: [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md)

## Standard Thread Prompt Shell

`Implement MEDIA_VIEWER_CONTENT_FULLSCREEN_PXX_<name>.md exactly. Before editing, read MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md, MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md, and MEDIA_VIEWER_CONTENT_FULLSCREEN_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
