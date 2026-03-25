# P13 DPF Viewer Live Policy Wrap-Up

## Implementation Summary
- Packet: `P13`
- Commit Owner: `worker`
- Substantive Commit SHA: `dda4f4d2eef64ccb2727afccceb2d1510ba14b42`
- Added the `dpf.viewer` built-in node (`type_id="dpf.viewer"`) as the canonical DPF viewer-family node with `surface_family="viewer"`, heavy/proxy render-quality defaults, deterministic `viewer_session_<sha1(workspace:node)>` session ids, `output_mode` defaulting to `both`, and `viewer_live_policy` constrained to `focus_only|keep_live`.
- Moved the viewer-node runtime contract onto the worker session service so the node seeds cached DPF source refs plus proxy/live dataset state through the session cache instead of pushing viewer datasets through ordinary graph outputs.
- Updated `ViewerSessionBridge` to keep playback/live policy session-owned, enforce the one-live default for `focus_only`, keep `keep_live` as explicit opt-in, preserve local reopen summaries such as camera/result state across proxy demotion, and rematerialize cached sessions through the worker service when a proxy is promoted back to live.
- Tightened `EmbeddedViewerOverlayManager` so native overlays only attach to `live_ready` sessions in `live_mode="full"`; proxy sessions no longer keep the live widget open.

## Changed Files
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `ea_node_editor/nodes/builtins/ansys_dpf.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_surface_host.py`
- `docs/specs/work_packets/pydpf_viewer_v1/P13_dpf_viewer_live_policy_WRAPUP.md`

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_viewer_node.py tests/test_dpf_node_catalog.py tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q` (`16 passed in 12.07s`)
- Final Verification Verdict: PASS

## Review Gate
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dpf_viewer_node.py --ignore=venv -q` (`2 passed in 4.53s`)
- Final Review Gate Verdict: PASS

## Manual Test Directives
- Ready for manual testing.
- Prerequisite: start the shell from this worktree with `./venv/Scripts/python.exe` so the viewer-family node catalog and shell-side `viewerSessionBridge` are loaded from the packet branch.
- Test 1: place a `dpf.viewer` node in a workspace backed by a valid DPF result/model chain and execute it once; expected result is a proxy-ready viewer session with the node showing the packet-owned viewer surface controls.
- Test 2: open two `dpf.viewer` sessions with the default `focus_only` policy and switch selection between them; expected result is exactly one live overlay at a time, with the unfocused viewer demoted to proxy.
- Test 3: enable `keep_live` on one viewer and then focus a different viewer; expected result is the pinned viewer remains live while the newly focused viewer can also promote to live.
- Test 4: demote a live viewer to proxy by changing focus, then refocus it; expected result is the viewer reopens through the worker session service with the same result summary and preserved camera/reopen state.

## Residual Risks
- The packet now keeps playback state and live/proxy promotion session-owned, but true step-by-step requery across multiple result sets is still bounded by the existing worker session-service source-ref contract outside this packet’s write scope.
- `focus_only` promotion after a proxy demotion currently rematerializes from the cached worker session; if later packets need a cheaper partial refresh path, that should be added in the worker session service rather than pushed back through the graph.

## Ready for Integration
- Yes: `dpf.viewer` is now part of the canonical DPF built-in family, the one-live default plus `keep_live` opt-in are enforced through packet-owned session orchestration, the required verification lanes passed, and the packet is ready for integration on top of `main`.
