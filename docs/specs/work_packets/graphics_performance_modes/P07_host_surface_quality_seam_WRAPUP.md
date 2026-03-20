# P07 Host Surface Quality Seam Wrap-Up

## Implementation Summary

- Packet: `P07`
- Branch Label: `codex/graphics-performance-modes/p07-host-surface-quality-seam`
- Commit Owner: `worker`
- Commit SHA: `aca18f6`
- Changed Files: `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `tests/test_graph_surface_input_contract.py`, `tests/test_passive_graph_surface_host.py`, `docs/specs/work_packets/graphics_performance_modes/P07_host_surface_quality_seam_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/graphics_performance_modes/P07_host_surface_quality_seam_WRAPUP.md`
- Host Contract: `GraphNodeHost.qml` now normalizes `nodeData.render_quality` into stable host-facing properties `renderQuality`, `requestedQualityTier`, `resolvedQualityTier`, `proxySurfaceRequested`, and `surfaceQualityContext` so loaded surfaces can observe the node contract from `P06` plus the current performance-tier request.
- Loader Mirror: `GraphNodeSurfaceLoader.qml` mirrors the same quality contract with `renderQuality`, `requestedQualityTier`, `resolvedQualityTier`, `proxySurfaceRequested`, `proxySurfaceActive`, and `surfaceQualityContext` for surface-side discovery without changing existing `host` plumbing.
- Proxy Decision Point: the host resolves `requestedQualityTier` from the degraded-window flags already threaded into `graphNodeCard`, upgrades `resolvedQualityTier` to `proxy` only when the node declares `max_performance_strategy="proxy_surface"` and supports the `proxy` tier, and leaves `proxySurfaceActive` false until a later packet provides a real proxy implementation.
- Compatibility: ordinary surface loading stays unchanged for standard and passive nodes; the seam is additive and future packets can adopt it through the existing `host` reference instead of reopening the canvas contract again.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q` -> `11 passed in 8.15s`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "render_quality or proxy_surface or quality_tier" -q` -> `1 passed, 22 deselected in 1.27s`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -k "render_quality" -q` -> `2 passed, 9 deselected in 1.33s`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Too soon for manual testing.

- Blocker: `P07` only adds an internal host/surface seam for render-quality metadata and proxy requests; no built-in surface in this branch switches to a new user-visible proxy presentation yet.
- Next condition: manual testing becomes worthwhile once `P08` adopts the seam for image/PDF media surfaces and exposes a concrete proxy behavior that a user can see.
- Automated verification is the primary validation for now: the accepted QML contract tests lock the new host properties, the loader mirror, the generic-fallback reduced tier, and the proxy-request seam while preserving the current loaded surface path.

## Residual Risks

- `P07` deliberately stops at the seam. `proxySurfaceRequested` can now resolve to `true`, but no built-in surface sets `proxySurfaceActive` yet, so the branch does not by itself prove a real proxy rendering path.
- The resolved tier is derived from the degraded-window signals already reaching `GraphNodeHost` (`snapshotReuseActive` / `shadowSimplificationActive`). If later packets introduce a broader host-quality signal, they should route it through these seam properties instead of bypassing them.
- Existing QML fixtures still omit `render_quality` in some standalone host probes, so the host keeps its own defensive normalization defaults in addition to the Python-side normalization from `P06`.

## Ready for Integration

- Yes: `P07` exposes the normalized render-quality contract and resolved quality tiers through the existing host/surface seam, preserves ordinary surface loading for non-adopters, documents a stable proxy decision point for later packets, and passes the required verification suite plus review gate.
