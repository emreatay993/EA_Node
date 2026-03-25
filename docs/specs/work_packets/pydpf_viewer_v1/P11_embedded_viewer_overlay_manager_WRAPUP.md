# P11 Embedded Viewer Overlay Manager Wrap-Up

## Implementation Summary
- Packet: `P11`
- Branch Label: `codex/pydpf-viewer-v1/p11-embedded-viewer-overlay-manager`
- Commit Owner: `worker`
- Commit SHA: `a395cc6e402983eeafd0c1147d6294d2eeaa1ff5`
- Changed Files: `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py, ea_node_editor/ui/shell/window.py, tests/test_embedded_viewer_overlay_manager.py, docs/specs/work_packets/pydpf_viewer_v1/P11_embedded_viewer_overlay_manager_WRAPUP.md`
- Artifacts Produced: `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py, ea_node_editor/ui/shell/window.py, tests/test_embedded_viewer_overlay_manager.py, docs/specs/work_packets/pydpf_viewer_v1/P11_embedded_viewer_overlay_manager_WRAPUP.md`

`EmbeddedViewerOverlayManager` now owns the native live-viewer overlay lifecycle from the shell side and is parented directly to the existing `QQuickWidget`. The manager resolves the active `graphCanvas`, consumes viewer node payload plus viewport state, and maps `viewer_surface.live_rect` onto widget geometry so the native overlay stays constrained to the node body instead of covering headers, ports, or resize handles.

Overlay visibility is driven from `viewerSessionBridge` state rather than from QML ownership. Open full-live sessions get reusable widget containers, `focus_only` sessions keep one visible live overlay unless `keep_live` is enabled, offscreen nodes are hidden without teardown so the interactor can be reused when they return, and closed or invalidated sessions tear their widgets down. To preserve the packet’s required pan/zoom and move/resize sync, the manager keeps a live overlay active through the bridge’s current coarse `graph_mutation` proxy demotion when the node still exists and only the layout moved.

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q` (`4 passed in 8.79s`)
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q` (`4 passed in 8.92s`, review gate)
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing

- Prerequisite: start the shell from this worktree with `./venv/Scripts/python.exe` so the `QQuickWidget`-hosted QML shell is running under the packet branch.
- Test 1: launch the shell and inspect `window.embedded_viewer_overlay_manager` from a debugger or developer console; expected result is a non-null manager parented to `window.quick_widget`.
- Test 2: register a temporary viewer-surface test node or reuse the packet test fixture pattern, emit a `viewer_data_materialized` event with `live_mode="full"` for that node, then pan, zoom, move, and resize it; expected result is a native overlay that stays clipped to the node body rectangle and tracks geometry changes without covering node chrome.
- Test 3: with one live overlay visible, pan the node offscreen and back, then switch selection between two live `focus_only` sessions and promote one session to `keep_live`; expected result is offscreen hiding without recreation, one visible live overlay for `focus_only`, and concurrent overlays only after `keep_live` is enabled.

## Residual Risks
- The manager currently treats `summary.demoted_reason == "graph_mutation"` as layout-safe so move and resize operations keep the live overlay visible; `P13` should replace that bridge-level workaround with an explicit live-policy distinction between semantic graph changes and pure geometry updates.
- The default factory instantiates `pyvistaqt.QtInteractor`, but this packet does not yet populate a real DPF dataset into the live widget; later viewer-binding packets must own that content and camera synchronization.
- Geometry mapping assumes the current `graphCanvas` transform and root-item overlay host contract; if later shell/QML packets change the overlay host item or add extra transforms, the manager’s root-space mapping must be updated in lockstep.

## Ready for Integration
- Yes: the shell now owns a `QQuickWidget`-parented overlay manager, packet-owned tests cover live geometry sync, culling, focus-only versus keep-live visibility, and the seam is ready for P12 viewer-surface bindings.
