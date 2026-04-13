# Title Icons for Non-Passive Nodes QA Matrix

- Updated: `2026-04-13`
- Packet set: retained `TITLE_ICONS_FOR_NON_PASSIVE_NODES` (`P01` through `P05`)
- Scope: final closeout matrix for the shipped path-backed title-leading icons on active and `compile_only` nodes, passive title-icon exclusion, local-file-only resolver behavior, built-in node-title icon asset packaging, collapsed comment-backdrop icon preservation, app-global nullable icon-size override, and traceability/docs evidence.

## Locked Scope

- `NodeTypeSpec.icon` remains the authoring field, but the node-header title-icon contract treats it as a local image-path reference only.
- Supported title-icon suffixes remain `.svg`, `.png`, `.jpg`, and `.jpeg`, case-insensitive; empty values, symbolic icon names, remote URLs, data URIs, missing files, unreadable files, unsupported suffixes, and unsafe cwd-relative entry-point fallbacks resolve to no title icon.
- Built-in relative icon paths resolve from the repo-managed node-title icon asset root, while file/package plugin relative paths resolve only from safe provenance roots and safe absolute plugin paths remain allowed when the file exists.
- `icon_source` remains a derived live graph payload field, is populated only for `active` and `compile_only` nodes when local resolution succeeds, and is not persisted into `.sfe` project files.
- Passive nodes remain title-iconless even when their specs carry authored `icon` metadata, and the collapsed comment-backdrop title glyph stays on the existing `uiIcons` / `comment.svg` path instead of converting to this image-path contract.
- `graphics.typography.graph_node_icon_pixel_size_override` remains a nullable app-global integer preference: `null` follows `graph_label_pixel_size`, explicit values clamp to `8..18`, and QML uses authored image colors without theme tinting.
- The shipped feature excludes node-library tiles, inspector rendering, remote image loading, and symbolic icon-name rendering in node headers.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Local-file resolver safety, supported suffix handling, safe provenance roots, active/`compile_only` payload population, and passive exclusion | `P01` | `REQ-NODE-028`, `REQ-PERSIST-022` | `.\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_sources.py tests/test_registry_validation.py tests/test_passive_visual_metadata.py -k title_icon --ignore=venv -q` | Accepted `P01` packet commit `bfb953365082f1d96371fe919e92e995875b43f0` |
| Nullable icon-size preference normalization, automatic/custom Graphics Settings control, and app-preferences persistence | `P02` | `REQ-UI-038`, `REQ-PERSIST-022` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py -k graph_node_icon_size --ignore=venv -q` | Accepted `P02` packet commit `fc3f3c3023231a35296c48e49902dfcf15e9d980` |
| Shell, bridge, and QML projection of the effective node-title icon size across automatic and explicit override modes | `P02` | `REQ-UI-038`, `REQ-PERSIST-022` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_main_window_shell.py tests/test_shell_run_controller.py tests/graph_track_b/qml_preference_bindings.py -k graph_node_icon_size --ignore=venv -q` | Accepted `P02` packet commit `fc3f3c3023231a35296c48e49902dfcf15e9d980` |
| Non-passive header image rendering, shared-header edit hit area, and preserved centered/elided title reserve math on the live header path | `P03` | `REQ-UI-038`, `REQ-PERF-013`, `AC-REQ-UI-038-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/inline_editor_suite.py tests/graph_surface/passive_host_interaction_suite.py tests/graph_track_b/qml_preference_rendering_suite.py -k title_icon --ignore=venv -q` | Accepted `P03` packet commit `a0cbb845271b2b8d8be0150d5fcb81609e305b2f` |
| Collapsed comment-backdrop icon exception and unchanged `uiIcons` / `comment.svg` behavior alongside the new header contract | `P03` | `REQ-UI-038`, `REQ-PERF-013`, `AC-REQ-PERF-013-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py tests/main_window_shell/shell_runtime_contracts.py tests/test_icon_registry.py tests/test_comment_backdrop_contracts.py -k title_icon --ignore=venv -q` | Accepted `P03` packet commit `a0cbb845271b2b8d8be0150d5fcb81609e305b2f` |
| Built-in non-passive asset inventory, symbolic-name migration to repo-managed paths, and packaged node-title icon shipping metadata | `P04` | `REQ-NODE-028`, `AC-REQ-NODE-028-01` | `.\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_assets.py tests/test_registry_validation.py -k title_icon --ignore=venv -q` | Accepted `P04` packet commit `33090d22b59e01b45fb37521cd283cc53dce8548` |
| DPF catalog migration, passive-node title-icon ineligibility, and retained built-in contract coverage after asset rollout | `P04` | `REQ-NODE-028`, `AC-REQ-NODE-028-01` | `.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_passive_node_contracts.py tests/test_passive_flowchart_catalog.py -k title_icon --ignore=venv -q` | Accepted `P04` packet commit `33090d22b59e01b45fb37521cd283cc53dce8548` |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Packet-owned traceability regression for the canonical title-icons closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Review-gate proof audit for the retained requirement, QA, index, and traceability docs |

## 2026-04-13 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the new QA matrix, spec-index registration, requirement anchors, and traceability rows for the title-icons closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the index, requirements, QA matrix, and traceability updates landed in this packet worktree |

## Remaining Manual Smoke Checks

1. Windows built-in SVG check: start a desktop Qt session on this branch, add built-in active and `compile_only` nodes such as `Start`, `Process Run`, `Excel Write`, `Subnode Input`, and `DPF Viewer`, and confirm each shipped non-passive node renders its packaged SVG before the title while passive note/flowchart/comment-backdrop nodes remain iconless in the title row.
2. Local PNG/JPG/JPEG fixture check: on the same desktop session, use a file/package plugin or local test node spec that points `icon` at a reachable local PNG file such as `ea_node_editor/assets/app_icon/corex_app_minimal_32.png`, then repeat with JPG/JPEG fixtures where available locally; confirm each supported suffix renders in the title row, while unsupported or missing local files still show no icon.
3. Passive exclusion and comment-backdrop exception check: inspect a passive node that still carries authored `icon` metadata and confirm the header remains iconless, then collapse a comment backdrop and confirm the existing `uiIcons` comment glyph remains unchanged.
4. Centering, elision, and shared-header editing check: with long and short node titles, confirm title text stays visually centered around the displayed icon/title band, elides cleanly when narrow, and still opens the shared inline title editor when double-clicking from the icon/title area.
5. Automatic versus explicit icon-size check: open `Settings > Graphics Settings > Theme > Typography`, leave the title icon size in automatic mode while changing `Graph label size`, confirm the effective icon size follows it, then enable Custom, pick explicit values at the `8` and `18` bounds, and confirm the header icon size persists and updates without tinting or layout breakage.

## Residual Desktop-Only Validation

- Automated coverage validates the contract offscreen, but a real Windows desktop compositor is still needed to judge final rasterization quality, anti-aliasing, and perceived balance between the leading icon and centered title text.
- The shipped built-in inventory is SVG-only; PNG/JPG/JPEG title-icon coverage depends on local file or plugin fixtures and should still be exercised on a real desktop where those fixtures are available.
- Graphics Settings and bridge regressions validate the nullable override contract, but manual desktop checks should still confirm the automatic/custom control feels coherent alongside other `Theme > Typography` settings and does not introduce visual crowding at the `8` and `18` bounds.

## Residual Risks

- The closeout matrix depends on retained `P01` through `P04` packet-local regressions and accepted packet commits because `P05` is intentionally docs-and-traceability-only.
- Future work that expands title icons into node-library tiles, inspector surfaces, remote image loading, or symbolic icon-name rendering will need a separate packet set and must not rely on this closeout matrix as proof for those out-of-scope surfaces.
