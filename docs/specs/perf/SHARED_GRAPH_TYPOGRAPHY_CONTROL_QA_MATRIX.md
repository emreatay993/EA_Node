# Shared Graph Typography Control QA Matrix

- Updated: `2026-04-09`
- Packet set: retained `SHARED_GRAPH_TYPOGRAPHY_CONTROL` (`P01` through `P07`)
- Scope: final closeout matrix for the shipped app-global shared graph typography preference, centralized `GraphSharedTypography.qml` role contract, Graphics Settings `Theme > Typography` control, passive-authoritative override precedence, deterministic metric alignment, and traceability/docs evidence.

## Locked Scope

- `graphics.typography.graph_label_pixel_size` remains an app-global graphics preference with default `10` and inclusive clamp `8..18`.
- The shipped UI surface is one Graphics Settings `Theme > Typography` control. The feature does not add a graph-theme typography schema, per-node typography persistence, or `.sfe` payload expansion.
- `GraphSharedTypography.qml` remains the single shared role source: standard node title `base + 2`, port labels `base`, elapsed footer `base`, inline property labels `base`, badge text `max(9, base - 1)`, flow edge label text `base + 1`, flow edge pill text `base + 2`, and exec arrow port label `base + 8`, with centralized role weights.
- Existing passive `visual_style.font_size` and `visual_style.font_weight` paths remain authoritative where already wired; the shared app-global token supplies the standard/default graph chrome roles without replacing authored passive title/body typography.
- Deterministic layout math stays aligned: `standard_metrics.py`, `graph_scene_payload_builder.py`, and the canvas/QML bindings consume the same clamped base value, shared typography updates reuse the existing graph-canvas payload refresh or revision seam, and the shipped feature does not add a second typography-only invalidation channel.
- The elapsed-footer typography surface remains a dependent consumer only. `PERSISTENT_NODE_ELAPSED_TIMES` stays authoritative for worker timing metadata, cache invalidation, session-only cached elapsed semantics, and the no-`.sfe` persistence precedent.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Preference normalization, default `10`, clamp `8..18`, and nested app-preference persistence | `P01` | `REQ-UI-035`, `REQ-QA-032` | `.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k graph_typography_preferences --ignore=venv -q` | Accepted `P01` packet commit `af6d24a665b0910bfec54259424c89e3a9840593` |
| Shell/workspace presenter projection plus bridge-owned graph-label pixel size property seam | `P02` | `REQ-UI-035`, `AC-REQ-UI-035-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/test_main_window_shell.py -k graph_typography_bridge --ignore=venv -q` | Accepted `P02` packet commit `d734a5321d5e080e674610612802fe3798a969dd` |
| Canvas-facing binding, shared role names, and metric/payload alignment | `P03` | `REQ-UI-035`, `REQ-PERF-011`, `AC-REQ-PERF-011-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_qml_contract --ignore=venv -q` | Accepted `P03` packet commit `894223fb5534ba152fe290f5d9bf59dc56a080f3` |
| Standard node headers, ports, and elapsed footer adopt shared roles without disturbing shell-run footer behavior | `P04` | `REQ-UI-035`, `REQ-QA-032` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k graph_typography_host_chrome --ignore=venv -q` | Accepted `P04` packet commit `1978d8eedb2c903e59bed7e959aee2ec374a0959` |
| Passive-host title/body authority stays in control while shared chrome roles update around it | `P04` | `REQ-UI-035`, `AC-REQ-UI-035-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_host_chrome --ignore=venv -q` | Accepted `P04` packet commit `1978d8eedb2c903e59bed7e959aee2ec374a0959` |
| Canvas/QML coverage for standard title, port, and elapsed-footer role adoption | `P04` | `REQ-UI-035`, `REQ-PERF-011` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k graph_typography_host_chrome --ignore=venv -q` | Accepted `P04` packet commit `1978d8eedb2c903e59bed7e959aee2ec374a0959` |
| Inline property labels and status chips follow the shared role hierarchy | `P05` | `REQ-UI-035`, `AC-REQ-UI-035-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_inline.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_inline_edge --ignore=venv -q` | Accepted `P05` packet commit `3c1e13240d4c9ccb8ec75587f70517f27ed4127f` |
| Flow-edge label/pill typography and preserved edge geometry across shared-role scaling | `P05` | `REQ-UI-035`, `REQ-PERF-011`, `AC-REQ-PERF-011-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_inline_edge --ignore=venv -q` | Accepted `P05` packet commit `3c1e13240d4c9ccb8ec75587f70517f27ed4127f` |
| Passive-host inline-role coverage without reopening passive typography authority contracts | `P05` | `REQ-UI-035`, `REQ-QA-032` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k graph_typography_inline_edge --ignore=venv -q` | Accepted `P05` packet commit `3c1e13240d4c9ccb8ec75587f70517f27ed4127f` |
| Graphics Settings `Theme > Typography` control round-trip and preference persistence | `P06` | `REQ-UI-035`, `AC-REQ-UI-035-01`, `REQ-QA-032` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py tests/test_graphics_settings_preferences.py -k graph_typography_dialog --ignore=venv -q` | Accepted `P06` packet commit `cd409e0cffd8d6e7c41a94f9dd70bee336c75965` |
| Shell/QML dialog handoff keeps the app-global typography control synchronized with the live canvas | `P06` | `REQ-UI-035`, `REQ-QA-032` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py tests/graph_track_b/qml_preference_bindings.py -k graph_typography_dialog --ignore=venv -q` | Accepted `P06` packet commit `cd409e0cffd8d6e7c41a94f9dd70bee336c75965` |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Packet-owned traceability regression for the shared graph typography closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Review-gate proof audit for the retained requirement, QA, index, and traceability docs |

## 2026-04-09 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the new QA matrix, spec-index registration, requirement anchors, and traceability rows for the shared graph typography closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the index, requirements, QA matrix, and traceability updates landed in this packet worktree |

## Remaining Manual Smoke Checks

1. Desktop Graphics Settings check: start the app in a desktop Qt session, open `Settings > Graphics Settings > Theme > Typography`, and confirm `Graph label size` defaults to `10` in a clean app-preferences state, accepts only the locked `8..18` range, and restores the last saved value after relaunch.
2. Shared chrome scaling check: on a graph with standard executable nodes, inline properties, and flow edges, switch the app-global typography size between `8` and `18` and confirm standard node titles, ports, elapsed footer text, inline labels/status chips, and flow-edge labels/pills all scale together while preserving the shipped hierarchy.
3. Passive-authoritative override check: repeat the size change on passive nodes that already author `visual_style.font_size` or `visual_style.font_weight`, and confirm those passive title/body overrides remain authoritative while surrounding shared chrome roles still follow the app-global token.
4. Metric-alignment check: at both non-default bounds, confirm node headers/ports do not clip, inline labels do not overlap their cards, and flow-edge label/pill geometry stays aligned with the rendered text after the existing scene refresh seam updates.
5. Elapsed-footer precedent check: run a node to surface elapsed footer text, change the typography size, and confirm only the footer typography changes while timing-cache invalidation, session-only retention, and save/reopen behavior continue to follow `PERSISTENT_NODE_ELAPSED_TIMES`.

## Residual Desktop-Only Validation

- Offscreen automated coverage does not validate final font rasterization, antialiasing, or perceived hierarchy on a real Windows desktop compositor across both shell themes and high-DPI scaling factors.
- Passive-authoritative font overrides are covered by focused regressions, but desktop validation is still needed to confirm authored passive surfaces remain visually coherent next to shared chrome roles at the `8` and `18` bounds.
- Deterministic metric alignment is covered by bridge/QML/edge regressions; manual desktop checks should still confirm there is no perceived clipping or crowding in dense graphs after live typography changes.

## Residual Risks

- The closeout matrix depends on retained packet-local regressions and accepted `P01` through `P06` packet commits because `P07` is intentionally docs-and-traceability-only.
- Later work that retunes shared typography role sizes, weights, or refresh seams will need to update this matrix, the requirement lines, and the traceability rows together to keep the closeout evidence authoritative.
