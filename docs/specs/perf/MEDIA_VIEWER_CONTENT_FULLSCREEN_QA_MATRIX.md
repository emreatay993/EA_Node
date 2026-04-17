# Media Viewer Content Fullscreen QA Matrix

- Updated: `2026-04-17`
- Packet set: `MEDIA_VIEWER_CONTENT_FULLSCREEN` (`P01` through `P05`)
- Scope: final closeout matrix for the shipped shell-owned content fullscreen overlay covering passive image media, passive PDF media, DPF viewer retargeting, `F11` routing, close paths, transient state, and traceability evidence.

## Locked Scope

- Content fullscreen is an in-app shell overlay, not OS or top-level application fullscreen.
- Only eligible passive image media, passive PDF media, and DPF viewer nodes may open through `contentFullscreenBridge`.
- Fullscreen state is transient UI state and is not serialized into `.sfe` project files.
- Media fullscreen reuses preview source, crop, page, fit, and caption semantics for viewing only; fullscreen display-mode controls must not mutate node properties.
- Surface buttons, `F11`, `Esc`, and the close button are the shipped entry and exit paths; double-click fullscreen and context-menu fullscreen remain out of scope.
- Live viewer fullscreen retargets the existing native viewer widget into `contentFullscreenViewerViewport` and restores it to the node viewport without creating a second widget for the same `(workspace_id, node_id)`.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| `contentFullscreenBridge` eligibility, normalized image/PDF/viewer payloads, transient state, workspace switch, and deletion cleanup | `P01`, `P05` | `REQ-UI-040`, `AC-REQ-UI-040-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py --ignore=venv -q` | P01 PASS in `docs/specs/work_packets/media_viewer_content_fullscreen/P01_fullscreen_state_contract_WRAPUP.md`; P05 aggregate command below |
| Shell overlay rendering, image and PDF media display, background interaction blocking, close button, `Esc`, and `F11` close paths | `P02`, `P05` | `REQ-UI-040`, `AC-REQ-UI-040-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py --ignore=venv -q` | P02 PASS in `docs/specs/work_packets/media_viewer_content_fullscreen/P02_shell_overlay_and_media_renderer_WRAPUP.md`; P05 aggregate command below |
| Media and viewer surface buttons, crop-mode suppression, `embeddedInteractiveRects`, and selected-node `F11` routing or hint behavior | `P03`, `P05` | `REQ-UI-040`, `AC-REQ-UI-040-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_contract.py tests/test_viewer_surface_contract.py --ignore=venv -q` | P03 PASS in `docs/specs/work_packets/media_viewer_content_fullscreen/P03_surface_buttons_and_shortcut_WRAPUP.md`; P05 aggregate command below |
| Live DPF viewer fullscreen retargeting, blocked viewer fallback, restore on close, workspace cleanup, and no orphaned native viewer overlay state | `P04`, `P05` | `REQ-INT-010`, `AC-REQ-INT-010-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_host_service.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q` | P04 PASS in `docs/specs/work_packets/media_viewer_content_fullscreen/P04_interactive_live_viewer_retargeting_WRAPUP.md`; P05 aggregate command below |
| Final integrated fullscreen regression command | `P05` | `REQ-QA-039`, `AC-REQ-QA-039-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_shell_window_lifecycle.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_contract.py tests/test_viewer_surface_contract.py tests/test_viewer_host_service.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q` | PASS recorded in `docs/specs/work_packets/media_viewer_content_fullscreen/P05_regression_closeout_WRAPUP.md` |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_shell_window_lifecycle.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_contract.py tests/test_viewer_surface_contract.py tests/test_viewer_host_service.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q` | Integrated offscreen regression gate for bridge, overlay, media/viewer controls, shortcut behavior, viewer retargeting, and cleanup |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Packet-owned traceability regression for the canonical docs closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Review-gate proof audit for retained requirements, index registration, QA matrix, and traceability rows |

## 2026-04-17 Execution Results

| Command | Result | Notes |
|---|---|---|
| `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_shell_window_lifecycle.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_contract.py tests/test_viewer_surface_contract.py tests/test_viewer_host_service.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q` | PASS (`88 passed, 4 warnings, 30 subtests passed`) | P05 integrated fullscreen regression gate; warnings are existing Ansys DPF operator deprecations |
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS (`58 passed`) | Traceability checker regression for retained closeout docs |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | PASS (`TRACEABILITY CHECK PASS`) | Verification command and duplicate Review Gate both passed |

## Manual Smoke Checklist

1. Image fullscreen desktop check: in a native Windows Qt session, add a passive image media node with a local image, confirm the fullscreen button opens the shell overlay, switch between Fit, Fill, and 100%, close with the close button, `Esc`, and `F11`, and confirm node crop/source/fit/caption properties do not change.
2. Crop-mode suppression check: activate image crop editing on the media node and confirm the fullscreen button is hidden while crop mode is active, then exit crop mode and confirm the button returns when the node is hovered or selected.
3. PDF fullscreen desktop check: add a passive PDF media node using a local PDF, open fullscreen, confirm the correct page preview and caption render, and confirm graph background clicks or wheel input do not interact with the canvas while the overlay is open.
4. `F11` selection check: select exactly one eligible media or viewer node and confirm `F11` opens fullscreen, select zero or multiple nodes and confirm the graph hint appears, then select an ineligible node and confirm the bridge reports the unsupported-node hint without graph data changes.
5. Live viewer retargeting check: run a DPF viewer node with live data available, open content fullscreen, confirm the existing native viewer widget moves into `contentFullscreenViewerViewport`, close fullscreen, and confirm the same widget restores to the node viewport without a duplicate viewer.
6. Viewer cleanup and blocked-state check: with a live viewer open, switch workspaces and delete the viewer node to confirm cleanup; reopen a saved project without rerunning viewer data and confirm the blocked/rerun-required state stays explicit and does not create a stale native widget.

## Residual Desktop-Only Validation

- Real PyVista/VTK/QtInteractor widget behavior still needs native desktop validation; the automated tests use offscreen shell coverage and test doubles for native viewer hosts.
- Final visual quality for PDF/image scaling, anti-aliasing, and perceived overlay sizing is not judged by offscreen assertions.
- Operator-supplied DPF projects and large result files remain manual smoke inputs rather than committed fast-lane fixtures.

## Residual Risks

- Existing Ansys DPF deprecation warnings may still appear during the offscreen regression suite and are not introduced by content fullscreen.
- Manual Windows smoke checks remain the release-candidate gate for native viewer rendering and real desktop input behavior.
- Future fullscreen entry points such as double-click, node context menu actions, or OS-level fullscreen require a separate packet set and are not covered by this matrix.

## Packet Evidence Links

- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P01_fullscreen_state_contract_WRAPUP.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P02_shell_overlay_and_media_renderer_WRAPUP.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P03_surface_buttons_and_shortcut_WRAPUP.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P04_interactive_live_viewer_retargeting_WRAPUP.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P05_regression_closeout_WRAPUP.md`
