# COREX Node Editor - Release Candidate Notes

Date: `2026-03-22`

## Shipped Capabilities

- Core editor shell/workspaces/views, graph model, node SDK, execution engine, persistence, and integration nodes (Tracks A-H).
- App-wide Graphics Settings modal for grid, minimap, snap-to-grid default, shell-theme selection, graph-theme follow-shell or explicit selection, and graph-theme manager access.
- Dedicated graph-theme pipeline for node/edge visuals: `ThemeBridge` keeps shell/canvas chrome on `stitch_dark` / `stitch_light`, while `graphThemeBridge` resolves built-in and custom graph themes for `NodeCard`, `EdgeLayer`, and graph payload presentation.
- Custom graph-theme library/editor with built-in read-only themes, custom duplication/CRUD, inline token editing, and live apply when editing the active explicit custom theme.
- Versioned `app_preferences.json` persistence for graphics, shell-theme, and graph-theme preferences, kept separate from project `.sfe` data and `last_session.json`.
- Passive visual authoring families for flowchart, planning, annotation, and local media panels, all stored in the existing workspace graph model.
- Shared header inline node-title editing across standard, passive, collapsed, and scope-capable node shells, using the same rename/history mutation path and preserving a dedicated `OPEN` badge for scope entry on subnode shells.
- Passive `flow` edge routing, labels, and style overrides with runtime exclusion from compiler/worker execution.
- Project-local passive node and flow-edge style presets persisted inside `.sfe` metadata.
- Local image preview panels and single-page local PDF preview panels on the passive media surface path.
- Reference passive workspace fixture and manual visual checklist for reopen, preset, and media-preview verification.
- Full automated QA gate coverage (`unittest` suite) and offscreen performance harness reporting.
- Windows PyInstaller packaging pipeline:
  `ea_node_editor.spec` + `scripts/build_windows_package.ps1`.
- Packaging operator documentation and RC packaging evidence report.

## Known Risks

- Performance baselines in CI/automation are offscreen and may differ from desktop GPU/compositor behavior.
- Packaging smoke test validates startup/liveness only; it is not a full interactive UI acceptance run.
- Shell-theme and graph-theme coverage are automated and offscreen in repo validation; real-display visual sign-off still matters for packaged builds.
- Passive media panels intentionally accept local filesystem sources only, and PDF scope remains single-page preview rather than a full reader/editor.
- Passive-only workspaces are presentation artifacts; `Run` intentionally ignores passive nodes and `flow` edges.
- Unsigned build artifacts are produced (no installer/signing/notarization pipeline in repo).
- Excel XLSX node paths remain runtime dependency-gated when `openpyxl` is not installed.

## Run and Build Commands

- Run tests:
  `venv\Scripts\python -m unittest discover -s tests -v`
- Run the passive-node final regression gate:
  `QT_QPA_PLATFORM=offscreen venv\Scripts\python -m unittest tests.test_registry_validation tests.test_registry_filters tests.test_serializer tests.test_serializer_schema_migration tests.test_execution_worker tests.test_graph_track_b tests.test_main_window_shell tests.test_inspector_reflection tests.test_passive_node_contracts tests.test_passive_runtime_wiring tests.test_passive_visual_metadata tests.test_passive_property_editors tests.test_passive_graph_surface_host tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_passive_flowchart_catalog tests.test_flowchart_visual_polish tests.test_planning_annotation_catalog tests.test_passive_style_dialogs tests.test_passive_style_presets tests.test_passive_image_nodes tests.test_pdf_preview_provider -v`
- Run benchmark harness:
  `venv\Scripts\python -m ea_node_editor.telemetry.performance_harness`
- Run app from source:
  `venv\Scripts\python main.py`
- Build Windows package (+default smoke):
  `.\scripts\build_windows_package.ps1 -Clean`
- Build only (skip smoke):
  `.\scripts\build_windows_package.ps1 -Clean -SkipSmoke`
