# GRAPHICS_PERFORMANCE_MODES Work Packet Manifest

- Date: `2026-03-20`
- Scope baseline: introduce app-wide `Full Fidelity` / `Max Performance` graphics modes, a persistent status-strip quick toggle, and a future-proof heavy-node render-quality contract so canvas pan/zoom and mutation bursts can scale to heavier visual nodes without breaking the existing shell/canvas/plugin architecture.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [Performance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/80_PERFORMANCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/settings.py`, `ea_node_editor/app_preferences.py`, and the graphics-settings pipeline already persist app-wide shell/theme/canvas preferences in app-preferences version `2`, but there is no graphics performance mode yet.
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, and `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml` already contain interaction-only cache/culling optimizations from `GRAPH_CANVAS_PERF`, but they are not user-selectable policies and they do not yet cover mutation bursts or a whole-canvas max-performance mode.
  - `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml` is already a global shell surface, but it does not yet expose any quick graphics-performance toggle.
  - `ea_node_editor/nodes/types.py` and `ea_node_editor/ui_qml/graph_scene_payload_builder.py` expose `runtime_behavior` plus `surface_family` / `surface_variant`, but there is no `render_quality` contract for future CAD/mesh/image/PDF-style nodes.
  - `ea_node_editor/ui/perf/performance_harness.py` measures real `GraphCanvas.qml` pan/zoom work, but it does not yet record `performance_mode` or a heavy-media scenario, and the current checked-in offscreen proof still fails the pan/zoom target.

## Packet Order (Strict)

1. `GRAPHICS_PERFORMANCE_MODES_P00_bootstrap.md`
2. `GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract.md`
3. `GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui.md`
4. `GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle.md`
5. `GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation.md`
6. `GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior.md`
7. `GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract.md`
8. `GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam.md`
9. `GRAPHICS_PERFORMANCE_MODES_P08_media_surface_proxy_adoption.md`
10. `GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media.md`
11. `GRAPHICS_PERFORMANCE_MODES_P10_docs_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/graphics-performance-modes/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Preferences + Runtime Contract | `codex/graphics-performance-modes/p01-preferences-runtime-contract` | Add the additive performance-mode schema plus runtime bridge/setter surfaces without changing visuals |
| P02 Graphics Settings Mode UI | `codex/graphics-performance-modes/p02-graphics-settings-mode-ui` | Add the persistent mode selector to Graphics Settings in the existing Theme/Renderer area |
| P03 Status Strip Quick Toggle | `codex/graphics-performance-modes/p03-status-strip-quick-toggle` | Add a persistent status-strip mode toggle that routes through the same app-preferences flow |
| P04 Canvas Performance Policy Foundation | `codex/graphics-performance-modes/p04-canvas-performance-policy-foundation` | Centralize resolved canvas performance policy, mutation-burst timing, and invisible full-fidelity optimizations |
| P05 Max Performance Canvas Behavior | `codex/graphics-performance-modes/p05-max-performance-canvas-behavior` | Apply whole-canvas max-performance behavior for pan/zoom and mutation bursts while restoring full idle fidelity |
| P06 Node Render Quality Contract | `codex/graphics-performance-modes/p06-node-render-quality-contract` | Extend the Node SDK and scene payload contract with render-quality metadata for heavy nodes |
| P07 Host Surface Quality Seam | `codex/graphics-performance-modes/p07-host-surface-quality-seam` | Expose resolved quality tiers and proxy-surface hooks through the host/surface seam |
| P08 Media Surface Proxy Adoption | `codex/graphics-performance-modes/p08-media-surface-proxy-adoption` | Move built-in image/PDF media surfaces onto the new heavy-node quality/proxy path |
| P09 Perf Harness Modes + Heavy Media | `codex/graphics-performance-modes/p09-perf-harness-modes-heavy-media` | Extend benchmark/report plumbing with mode-aware and heavy-media evidence seams |
| P10 Docs + Traceability | `codex/graphics-performance-modes/p10-docs-traceability` | Update requirement docs, QA matrix, benchmark report guidance, and traceability for the new mode architecture |

## Locked Defaults

- Mode enum for v1 is exactly `full_fidelity` and `max_performance`.
- Fresh installs default to `full_fidelity`.
- The mode is app-global, not per-workspace or per-view.
- Graphics Settings remains the canonical persistent editor for the mode, and the status-strip toggle is a second view over the same persisted preference.
- The status-strip toggle updates the saved preference immediately; it is not a session-only override.
- `Full Fidelity` may take invisible structural optimizations only. It must not intentionally degrade visible quality during normal interaction.
- `Max Performance` may temporarily use whole-canvas simplification and cached/snapshot-style reuse during active pan/zoom and structural mutation bursts, but idle visuals must recover automatically after the settle timer.
- The initial degraded-window settle default is `150 ms` and should reuse the existing viewport-idle timing unless a packet explicitly proves a private equivalent is required.
- Heavy-node architecture for v1 is hybrid: every node benefits from the generic canvas fallback, and future plugins can opt into a richer `render_quality` contract and proxy-surface path.
- This packet set is intentionally sequential. No implementation wave contains more than one packet.

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

### Wave 7
- `P07`

### Wave 8
- `P08`

### Wave 9
- `P09`

### Wave 10
- `P10`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `GRAPHICS_PERFORMANCE_MODES_Pxx_<name>.md`
- Implementation prompt: `GRAPHICS_PERFORMANCE_MODES_Pxx_<name>_PROMPT.md`
- Status ledger update in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement GRAPHICS_PERFORMANCE_MODES_PXX_<name>.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P10` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep public `graphCanvas` discoverability and methods stable: `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, and `performLibraryDrop()`.
- Keep public `ShellWindow`, `GraphCanvasStateBridge`, `GraphCanvasBridge`, `GraphNodeHost`, and `NodeTypeSpec` contracts stable unless the packet explicitly introduces the new performance/render-quality surface it owns.
- Reuse the existing graphics-settings, shell-surface, graph-surface, and graph-canvas perf seams instead of reopening monolithic files without a packet-owned reason.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
