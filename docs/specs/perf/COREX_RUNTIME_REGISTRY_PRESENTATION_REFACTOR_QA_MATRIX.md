# COREX Runtime, Registry, and Presentation Ownership Refactor QA Matrix

Status: `CHECKPOINT — T05 ACCEPTED; NEXT T06`

This is the single compaction-safe task, test-migration, performance, and review
ledger for
`docs/PLAN_COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR.md`. It is the source of
truth for task progress. Do not infer progress from a working-tree diff alone.

## Locked Baseline

| Fact | Value |
| --- | --- |
| Starting branch | `main` |
| Starting commit | `db3cbc512d0f8993173ee2d0e69b124c3d3be738` |
| Upstream at start | `origin/main` at `db3cbc512d0f8993173ee2d0e69b124c3d3be738` |
| Publication | Local commits only; no push |
| Starting status | `docs/specs/INDEX.md` modified; Physical Simulation plan and strain CSV untracked; nothing staged |
| Performance policy | Advisory matched evidence; no timing-only rollback |
| Frozen harness | `ea_node_editor/ui/perf/performance_harness.py` and its current report schema |
| Ignored ledger staging | After privacy review, the orchestrator must use `git add -f -- docs/specs/perf/COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR_QA_MATRIX.md`; ordinary staging is insufficient and no other ignored path is authorized |

### Protected dirty paths

These hashes were taken before the T00 plan/index edit. The orchestrator must
compare them before every commit. Only an exact new plan/status hunk in
`docs/specs/INDEX.md` belongs to this refactor.

| Path | Starting state | SHA-256 before T00 | Git blob hash before T00 | Protected content |
| --- | --- | --- | --- | --- |
| `docs/specs/INDEX.md` | modified, unstaged | `43BFA388899097D924301BED29BBB57935512498237BCC7AF6EFDF9FF631D431` | `268cefb5e02d82c65fe4c50e54607cb871e9ecec` | Existing one-line Physical Simulation plan registration must remain byte-identical and unstaged except when exact hunk staging separates this plan's new row. |
| `docs/PLAN_COREX_Physical_Simulation_Backend.md` | untracked | `F1709CD27CDD97141E354AB0644B3602F8EA43EBEFBB294B0C5FA4578C6788F2` | `27f9da6d30a4f2c74ad769c1b27551c204dce6a2` | Entire file is user-owned; never edit or stage. |
| `scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv` | untracked | `468C04C09DF327871ED6CD947EF58E8F26412D632A1E969C3C56303DFC44061B` | `7aeb2d3a41c1e6b48900b5bc901fdd5e5d26b1d1` | Entire file is user-owned; never edit or stage. |

The pre-T00 `docs/specs/INDEX.md` diff was exactly one added line:

```text
+- [COREX Physical Simulation Backend](../PLAN_COREX_Physical_Simulation_Backend.md) — `PLANNED — NO IMPLEMENTATION PROOF`
```

## Compaction Recovery Checklist

Before continuing after compaction, stop editing and read these in order:

1. `AGENTS.md`
2. `docs/PLAN_COREX_RUNTIME_REGISTRY_PRESENTATION_REFACTOR.md`
3. this QA matrix
4. `git status --short --branch`
5. `git log -1 --oneline`
6. the next `IN PROGRESS` or `NOT STARTED` task row below
7. current active-agent state

Then reconcile the protected hashes, last accepted commit, working diff, staged
diff, and any running writer. Only one writer may edit at a time.

## Task Status Rules

- Allowed statuses are `NOT STARTED`, `IN PROGRESS`, `ACCEPTED`,
  `ACCEPTED NO-OP`, and `BLOCKED`.
- Zero or one task may be `IN PROGRESS` or `BLOCKED`, allowing a clean accepted
  checkpoint before the next writer starts.
- A task becomes `ACCEPTED` only after its focused checks and independent review
  pass and its writer, focused evidence, performance verdict, review, and
  accepted commit are non-pending. `This commit` is the permitted commit marker
  while the current task's commit is self-referential.
- `ACCEPTED NO-OP` records evidence and a reason but has no empty commit; its
  accepted-commit cell is exactly `N/A — accepted no-op`.
- T01–T12 must be accepted before T13. T14–T25 must not start before T13 is
  accepted. T26 closes the full plan.
- Plan and ledger top-level status lines must match. Use `IN PROGRESS — Txx` or
  `BLOCKED — Txx` for an active task, `CHECKPOINT — Txx ACCEPTED; NEXT Tyy` for
  a clean gap, and `COMPLETED — T00–T26 ACCEPTED` only after T26.

## Task Ledger

| Task | Program | Status | Writer | Conservative write scope | Focused evidence | Performance evidence | Independent review | Accepted commit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T00 Plan, ledger, baseline | Bootstrap | `ACCEPTED` | `t00_writer` | Plan, this ledger, ledger validator, exact spec-index plan row, generated source/test inventory | 12 ledger/schema tests and 7 shell guards passed; 916 A and 696 B IDs collected with matching hashes; dry-run/maps/traceability/links/generators/diff checks passed | measurement contracts accepted; no T00 timing acceptance claim | Architecture/integration `CLEAR`; ledger/test `CLEAR`; performance `CLEAR` | This commit |
| T01 Add-on apply authority | A | `ACCEPTED` | `t01_writer` | Add-on state changes, registry replacement, direct tests/maps | Remediated state/catalog/registry/plugin 75 passed; DPF/runtime/viewer 48 passed/19 subtests; architecture/dead-code/runner 89 passed/116 subtests; ledger 12 passed; earlier traceability/ledger 102 and add-on shell route 10 passed/246 deselected; maps, traceability, links, generators, Ruff, compile, full dry-run, and diff hygiene passed | STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTA NOT ATTRIBUTED | Architecture `CLEAR`; correctness/security/no-lost-tests `CLEAR`; performance `CLEAR` | This commit |
| T02 Registry contributions | A | `ACCEPTED` | `t02_writer` | Plugin/built-in/add-on contributions, direct tests/maps | Remediated public/add-on/built-in 60 passed; package/worker/agreement/replacement 137 passed; registry/catalog/authoring 136 passed/104 subtests; DPF/add-on/shell 64 passed/1 skipped/20 subtests; packaging/architecture/dead-code/traceability/ledger/runner 219 passed/126 subtests; maps/indexes/traceability/links 120 passed/15 subtests plus direct generator/check PASS; exact five-node collection and 17 migration rows confirmed; Ruff and compile PASS; routing unchanged, so the previously passing T02 full dry-run was not repeated | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTAS NOT ATTRIBUTED`; post-remediation structural-only probe matched all hashes/order/read counts; discovery `+0.73%`, worker `-0.07%`, export `+2.69%` retained as unattributed advisory context | Architecture `CLEAR`; correctness/security/no-lost-tests `CLEAR`; performance `CLEAR` | This commit |
| T03 Registry validation | A | `ACCEPTED` | `t03_writer` | Registry, instance-resolution/coercion/validation owners, direct tests/maps | Remediated validation/direct owners 86 passed/104 subtests; plugin/package/function/add-on 254 passed; dynamic/default/catalog 88 passed; runtime agreement/replacement 72 passed; affected graph/execution/UI callers 145 passed/56 subtests; architecture/dead-code/DPF 71 passed/157 subtests; ledger/maps/indexes/traceability/Markdown 132 passed/15 subtests plus direct generator/check PASS; full dry-run, Ruff, format, compile, and diff hygiene passed | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTAS NOT ATTRIBUTED`; post-remediation structural-only recheck matched all calls/copies/passes/orders/fingerprints without new timing | Architecture `CLEAR`; correctness/security/no-lost-tests `CLEAR`; performance `CLEAR` | This commit |
| T04 Registry normalization | A | `ACCEPTED` | `t04_writer` | Registry, normalization owner, direct tests/maps | Normalization/validation 90 passed/104 subtests; Web/DPF 42 passed/18 subtests; graph mutation/filter/default paths 66 passed; plugin/runtime agreement 174 passed; catalog/declaration 134 passed; architecture/dead-code 51 passed/162 subtests; ledger/maps/indexes/traceability/Markdown 132 passed/15 subtests plus direct generator/check PASS; full dry-run, Ruff, format, compile, and diff hygiene passed | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTAS NOT ATTRIBUTED`; exact candidate evidence below, with base-spec lookups improved from 28 to 16 | Architecture `CLEAR`; correctness/security/no-lost-tests `CLEAR`; performance `CLEAR` | This commit |
| T05 Library queries | A | `ACCEPTED` | `t05_writer` | Registry and existing Library projection/presenter | Library/Quick Insert/cache 41 passed/2 subtests; registry/catalog/Inspector 99 passed/74 subtests; DPF/add-on/workflow 92 passed/18 subtests; focused real-shell Library/Node Browser 9 passed/242 deselected/19 subtests; architecture/dead-code 51 passed/165 subtests; ledger/maps/indexes/traceability/Markdown 132 passed/15 subtests plus direct generator/check PASS; full dry-run, Ruff, format, compile, and diff hygiene passed | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, NO TIMING-ONLY ROLLBACK`; exact candidate and advisory-repeat evidence below | Architecture `CLEAR`; correctness/security/no-lost-tests `CLEAR`; performance `CLEAR` | This commit |
| T06 DPF runtime package | A | `NOT STARTED` | Pending | DPF package/facades/constants, direct tests/maps | Pending | Pending | Pending | Pending |
| T07 Protocol split | A | `NOT STARTED` | Pending | Protocol message/codec owners and imports/tests/maps | Pending | Pending | Pending | Pending |
| T08 Client split | A | `NOT STARTED` | Pending | Concrete transports/backend routing/generation owners | Pending | Pending | Pending | Pending |
| T09 Solution contracts | A | `NOT STARTED` | Pending | Solution store/boundary contracts/repository imports | Pending | Pending | Pending | Pending |
| T10 Runtime and CLI split | A | `NOT STARTED` | Pending | Runtime requests/loader/runtime/CLI and imports | Pending | Pending | Pending | Pending |
| T11 Run projection | A | `NOT STARTED` | Pending | Run state/projection/controller/composition | Pending | Pending | Pending | Pending |
| T12 Event intake | A | `NOT STARTED` | Pending | Event controller/composition/ShellWindow forwarding | Pending | Pending | Pending | Pending |
| T13 Program A closeout | A gate | `NOT STARTED` | Pending | Plan/ledger/evidence and review corrections only | Pending | Pending | Pending | Pending |
| T14 Workspace graph actions | B | `NOT STARTED` | Pending | Workspace/direct graph-action owners/tests/maps | Pending | Pending | Pending | Pending |
| T15 Media actions | B | `NOT STARTED` | Pending | Media action service/callback wiring/tests/maps | Pending | Pending | Pending | Pending |
| T16 Canvas export | B | `NOT STARTED` | Pending | Canvas export owner and split bridge composition | Pending | Pending | Pending | Pending |
| T17 Viewer/plot injection | B | `NOT STARTED` | Pending | Four native viewer/plot classes and composition | Pending | Pending | Pending | Pending |
| T18 Native handoff | B | `NOT STARTED` | Pending | Shared handoff plus distinct viewer/plot hosts | Pending | Pending | Pending | Pending |
| T19 Edge paint policy | B | `NOT STARTED` | Pending | Edge paint JS/math and two renderers | Pending | Pending | Pending | Pending |
| T20 Surface overlays | B | `NOT STARTED` | Pending | Root layers/new overlay component/tests/maps | Pending | Pending | Pending | Pending |
| T21 Port row | B | `NOT STARTED` | Pending | Ports layer/new row component/tests/maps | Pending | Pending | Pending | Pending |
| T22 Port context menu | B | `NOT STARTED` | Pending | Ports layer/new menu component/tests/maps | Pending | Pending | Pending | Pending |
| T23 Action presentation | B | `NOT STARTED` | Pending | Pure action shaping and direct consumers | Pending | Pending | Pending | Pending |
| T24 Toolbar popovers | B | `NOT STARTED` | Pending | Toolbar/new popover host/tests/maps | Pending | Pending | Pending | Pending |
| T25 Residual test ownership | B | `NOT STARTED` | Pending | Proven test/QML/shell routing changes only | Pending | Pending | Pending | Pending |
| T26 Final closeout | Final gate | `NOT STARTED` | Pending | Plan/ledger/evidence and review corrections only | Pending | Pending | Pending | Pending |

## Navigation Audit

| Field | T00 record |
| --- | --- |
| Route index entries checked | Exact `nav.py source` entries for registry, execution client, graph-canvas presenter; `nav.py qml` entries for `GraphNodePortsLayer` and `GraphCanvasRootLayers` |
| Maps consulted | Agent atlas/coverage; execution; nodes/registry/built-ins; add-ons; UI shell; QML shell/bridges; graph canvas; viewer surfaces; verification; QML/graph-surface testing; shell isolation; run controller; add-on manager; viewer/fullscreen; graph actions; edge routing; port availability; floating toolbar; DPF transport |
| Source candidates | The exact starting-owner table below |
| QML candidates | Edge Canvas/retained layers, `GraphCanvasRootLayers`, `GraphNodePortsLayer`, `GraphCanvasActionRouter`, `GraphNodeFloatingToolbar` |
| Test candidates | The two Python collection cohorts, 62 affected QuickTest selectors, and 51 shell targets below |
| Searches run | Bounded exact-path and exact-symbol `rg` after map selection; no generated/build/vendor/worktree search |
| Fallback reason | Generated source/test index is a path inventory, not owner mapping; direct maps/tests were needed to lock collection and shell/QML identities |

No agent-map edit is needed in T00 because no production or test ownership moves.

## Starting Owner Snapshot

All 17 listed Python modules imported successfully at the starting commit. File
hashes allow later reviewers to distinguish a true move from an unrelated
rewrite.

| Starting owner | Lines | SHA-256 at `db3cbc51` |
| --- | ---: | --- |
| `ea_node_editor/addons/hot_apply.py` | 246 | `357FF1737525F741135DB159986DE8EC824777B36DE89D93DCB62B2793C710D8` |
| `ea_node_editor/nodes/plugin_loader.py` | 1,006 | `FB707E6B5D04A147EB59840594DEA187FB8E07FFB51537DFC18F0DDD28FE8A5B` |
| `ea_node_editor/nodes/registry.py` | 2,654 | `FE6F35AEA20FB2E94F627608122D293D20713E973AE91C11EE8A468C2307326B` |
| `ea_node_editor/execution/dpf_runtime_service.py` | 81 | `AABF796C5D3C1E3754189191B5B0369FA7E0E7BCED2210DD9E7E2BF64966BB85` |
| `ea_node_editor/nodes/dpf_runtime_contracts.py` | 125 | `E6416FE860E30B2BF4C87268EF766A20C3F5BE97826349E9D7762347FEAD825D` |
| `ea_node_editor/execution/protocol.py` | 3,498 | `C6B17CB324C7B00F57BC4C07A3DB0FBA7B9B925C519D3B535F7DEC9615022FEE` |
| `ea_node_editor/execution/client.py` | 5,797 | `712CF75072AA693C8B84366D183A22491E81015E4245E177A7EC84B610084127` |
| `ea_node_editor/execution/solution_store.py` | 2,823 | `2035E1BB3E0F9832DF51F41234D68677F041A89E4DB60CC6D78FBD4660091FC6` |
| `ea_node_editor/execution/headless_runtime.py` | 2,390 | `86AF67B0FE45E68C9DA4F54F4AD26F6E4B729D4C011813DE6F3D00AF1DD2B89F` |
| `ea_node_editor/ui/shell/controllers/run_controller.py` | 1,656 | `DB970387CC5E3F6FDD1845665D9F11AF167319B0B29DFB31AC4613E671A89FE4` |
| `ea_node_editor/ui/shell/controllers/workspace_library_controller.py` | 564 | `44117BB39A211939BA880F2F58DD6AD65B3A7BD3E2AD44B9E2F7F09A3D42B640` |
| `ea_node_editor/ui/shell/controllers/workspace_graph_edit_controller.py` | 401 | `F7D3D2A65528BA5DE57899772ADCA728B20AC23B1B88BF26AF0ADA7C4867C608` |
| `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py` | 2,013 | `898BBEDCCAA57F82DFCDDD95D4E2BA525646825259C15C581A37E8B0EF3CAE20` |
| `ea_node_editor/ui_qml/viewer_session_bridge.py` | 1,906 | `367A19958ABC8F5C454318ADA8847BC7CE0BE681E30B14BF97D2A3027F30BD1C` |
| `ea_node_editor/ui_qml/viewer_control_bridge.py` | 744 | `C7DF7B9E18FAEEB59E8F3791321DA8CD8F9BDE009DFF85CC74A13355EFDB7303` |
| `ea_node_editor/ui_qml/viewer_host_service.py` | 2,769 | `C72048ECF4D053208036F46012FF20397ACC4C1465FE73D07E1B9C1B509403B8` |
| `ea_node_editor/ui_qml/plot_host_service.py` | 1,742 | `5BFDBEE60BF269CA224DEE7691E90A555C70A7541326361C7BDE96B2B65BF760` |
| `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml` | 1,212 | `CD26C558A41CF375F407487E6845A88AC582DA8A1AC663CE7053FB2C62E6E443` |
| `ea_node_editor/ui_qml/components/graph/EdgeRetainedLayer.qml` | 585 | `3694BFA0F536C8D222BB7097CD960BD79D79C2431239B5045798A8E8F597F37B` |
| `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml` | 1,823 | `0E52E26E7E8E8A432B82FC392FDC3CC2294689F1B3221D9BC2DCE43E495E937C` |
| `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml` | 2,520 | `F578B882F6B750A94453D205C8C3AAFA2310D87FFEAADEC8AC5FB7EF99E8CC16` |
| `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasActionRouter.qml` | 663 | `B829907B1473DECFCADBA91C835D6F1D9CF8A2D67448DB66667C7F257E23A3C3` |
| `ea_node_editor/ui_qml/components/graph/overlay/GraphNodeFloatingToolbar.qml` | 2,054 | `BA0A0B75D830FF12C2A1EAC414CD0F18D01454EA8DC2AD2552097CB827DA5511` |

## Stable Surface Snapshot

| Surface | Starting evidence |
| --- | --- |
| Top-level `corex` API | 17 unique names: `node,input,output,text,text_area,number,switch,dropdown,slider,color,path,interval,list,Any,Image,Color,Interval` |
| Default registry | 933 specs; contract fingerprint `15b4c3fdd641aa71ba5dde56018c0d0414b96fd6df44c3623ebe0f9b3960daad` |
| Public-plugin fingerprint | `9b8d91309eaf5db655e230e1411074fa41848f60183112b191ecddb0711e297a` |
| Data-type catalog fingerprint | `1d20c15d960bb2cb84d63611903a445af12d47c8df65ce6864d2628164fc31d2` |
| Graph/QML meta-object fixture | `tests/fixtures/graph_canvas_surface_snapshot.json`, 30,674 bytes, SHA-256 `8FACC5C409C1589D92ED16F5528328655265160A18DD7659497F1280C73A4B48` |
| Current structural shell counts | 156 QObjects, 3 timers, 1 graph host, 1 shell host, 5 image providers, retained at the exact starting `HEAD` by the accepted predecessor QA matrix; this is not a fresh timing result and must be remeasured at T13 |

## Seed Test Inventories

The seed inventories are reproducible starting-commit snapshots. Exact IDs
actually removed, renamed, or consolidated must be added individually to the
Test Migration Ledger before their old test is deleted. A cohort hash is not a
replacement for a migration row.

### Python collection cohorts

Node-ID hashes are SHA-256 over the collected node IDs in pytest output order,
joined with the platform newline. Both commands use the project venv,
`--collect-only -q -n 0 --ignore=venv`.

| Program | Current owner modules | Node IDs | Node-ID SHA-256 | T00 result |
| --- | --- | ---: | --- | --- |
| A | 32 modules listed below | 916 | `E11011966B1D425685AFA9F3D43525D7728E04EC967CAA7536AA65A99B13BB0E` | `PASS`, 5.78 s |
| B | 35 modules listed below | 696 | `89FABCC19D0E6A548E6F377FE1A9781208ACC5E12CB4B8D07BEA515492B6E060` | `PASS`, 3.65 s |

Program A modules:

```text
tests/test_registry_replacement.py
tests/test_addon_catalog.py
tests/test_addon_manager_install.py
tests/test_plugin_loader.py
tests/test_plugin_runtime_agreement.py
tests/test_plugin_worker_loading.py
tests/test_package_manager.py
tests/test_builtin_function_infrastructure.py
tests/test_registry_validation.py
tests/test_library_projection.py
tests/test_default_port_values.py
tests/test_dpf_contracts.py
tests/test_dpf_runtime_service.py
tests/test_dpf_runtime_analysis.py
tests/test_dpf_materialization.py
tests/test_dpf_compute_nodes.py
tests/test_dpf_viewer_node.py
tests/test_execution_protocol.py
tests/test_execution_viewer_protocol.py
tests/test_execution_client.py
tests/test_execution_worker.py
tests/test_execution_viewer_service.py
tests/test_solution_store_session.py
tests/test_solution_records.py
tests/test_solution_repository.py
tests/test_headless_runtime.py
tests/test_run_controller_unit.py
tests/test_port_flow_state.py
tests/test_port_availability.py
tests/test_project_session_controller_unit.py
tests/test_workspace_library_controller_unit.py
tests/test_architecture_boundaries.py
```

Program B modules:

```text
tests/test_graph_action_contracts.py
tests/test_transform_layout_ops.py
tests/test_workspace_library_controller_unit.py
tests/test_graph_canvas_split_bridges.py
tests/test_graph_canvas_surface_snapshot.py
tests/test_canvas_view_export.py
tests/test_project_review_deck.py
tests/test_content_fullscreen_bridge.py
tests/test_content_fullscreen_bridge_lifecycle.py
tests/test_media_panel.py
tests/test_media_panel_creation_preferences.py
tests/test_media_panel_qml_surface.py
tests/test_media_video_state.py
tests/test_video_trim.py
tests/test_viewer_session_bridge.py
tests/test_viewer_control_bridge.py
tests/test_viewer_host_service.py
tests/test_plot_host_service.py
tests/test_embedded_viewer_overlay_manager.py
tests/test_plot_detached_window.py
tests/test_engineering_viewer_widget_binder.py
tests/test_edge_snapshot_spatial_index.py
tests/test_flow_edge_labels.py
tests/test_graph_surface_input_controls.py
tests/test_graph_surface_input_contract.py
tests/test_graph_surface_input_inline.py
tests/test_data_tree_ui.py
tests/test_floating_toolbar_positioning.py
tests/test_panel_surface.py
tests/test_passive_graph_surface_host.py
tests/test_graph_node_link_hover_layer.py
tests/test_graph_output_mode_ui.py
tests/test_data_type_ui_projection.py
tests/test_graph_type_enforcement.py
tests/test_architecture_boundaries.py
```

### Affected QML QuickTest selectors

These 62 selectors are currently owned by the `gui.qml_quick` phase under
`qmltestrunner`; SHA-256 over this ordered list is
`ADE8746FC400E06B6950A4EBC078F97BD25FDA2C2D2585A06B6207C77616608B`.
The two `SecretEditor` selectors are outside this refactor and are not listed.

```text
GraphNodeHost::test_graph_node_host_loads_standard_surface_for_standard_nodes
GraphNodeHost::test_graph_node_host_uses_surface_spec_for_standard_surface_selection
GraphNodeHost::test_graph_node_host_uses_curve_rendering_for_node_text
GraphNodeHost::test_graph_node_host_exposes_split_helper_layers_with_stable_stacking
GraphNodeHost::test_graph_node_host_render_quality_contract_exposes_reduced_quality_tier
GraphNodeHost::test_standard_data_ports_remain_visible_without_hover
GraphNodeHost::test_active_invalid_input_grip_uses_coral_without_changing_passive_palette
GraphNodeHost::test_standard_data_grip_grows_on_real_pointer_hover_and_keeps_halo
GraphNodeHost::test_flow_edge_ports_reveal_on_hover_and_pending_connection_only
GraphNodeHost::test_graph_node_host_shadow_cache_key_ignores_viewport_activity_but_tracks_geometry_and_shadow_preferences
GraphNodeHost::test_graph_node_host_shows_resize_handles_only_for_passive_expanded_nodes
GraphNodeHost::test_graph_node_host_keeps_resize_handles_hidden_for_collapsed_nodes
GraphNodeHost::test_graph_node_host_loads_flowchart_surface_family
GraphNodeHost::test_collapsed_flowchart_keeps_compact_header_title_and_hides_body_surface
GraphNodeHost::test_flowchart_host_hides_raw_port_labels_and_keeps_port_handles
GraphNodeHost::test_new_flowchart_silhouette_variants_load_on_host_surface
GraphNodeHost::test_icon_like_flowchart_variants_do_not_fallback_to_library_label
GraphNodeHost::test_timestamp_flowchart_surface_actions_commit_live_snapshot_and_manual_values
GraphNodeHost::test_timestamp_live_property_drives_rendered_body_text
GraphNodeHost::test_flowchart_body_text_uses_fallback_chain_and_passive_style_hooks
GraphNodeHost::test_graph_node_host_loads_shared_planning_card_surface
GraphNodeHost::test_graph_node_host_loads_shared_annotation_note_surface
GraphNodeHost::test_graph_node_host_loads_bare_text_annotation_surface
GraphNodeHost::test_library_flowchart_visual_fits_multi_document_to_metadata_aspect_ratio
GraphNodeHost::test_graph_node_host_loads_group_backdrop_without_body_or_shadow
GraphNodeHost::test_selected_untitled_group_shows_prompt_and_edits_an_empty_title
GraphNodeHost::test_collapsed_group_backdrop_ignores_node_icon_source_for_title_contract
GraphNodeHost::test_collapsed_group_backdrop_width_fits_long_title_with_stale_metrics
GraphSurfaceControls::test_interactive_region_maps_host_space_rect_and_emits_control_start
GraphSurfaceControls::test_button_and_text_field_publish_rects_and_host_styling
GraphSurfaceControls::test_slider_commits_on_release_only_and_publishes_contracts
GraphSurfaceControls::test_interval_slider_preserves_semantic_direction_and_separates_equal_handles
GraphSurfaceControls::test_combo_box_and_check_box_emit_control_start_and_keep_surface_contracts
GraphSurfaceControls::test_searchable_combo_filters_options_and_publishes_surface_rect
GraphSurfaceControls::test_dropdown_controls_publish_hover_and_press_visual_state
GraphSurfaceControls::test_inline_properties_layer_publishes_control_scoped_rects_for_core_editors
GraphSurfaceControls::test_inline_layer_uses_dynamic_upstream_display_and_condition_state
GraphSurfaceControls::test_inline_stacked_controls_follow_enlarged_typography_without_clipping
GraphSurfaceControls::test_single_line_surface_controls_publish_uncapped_display_text_fit_widths
GraphSurfaceControls::test_inline_properties_layer_fits_widest_eligible_row_and_excludes_multiline_controls
GraphSurfaceControls::test_floating_toolbar_publishes_rect_and_dispatches_each_action_exactly_once
GraphSurfaceControls::test_floating_toolbar_video_bookmarks_popover_refreshes_after_repeated_adds
GraphSurfaceControls::test_floating_toolbar_font_size_popover_uses_field_slider_and_stepper
GraphSurfaceControls::test_floating_toolbar_pdf_page_popover_uses_page_field_and_navigation_buttons
GraphSurfaceControls::test_floating_toolbar_source_storage_popover_uses_external_default_combo
GraphSurfaceControls::test_floating_toolbar_font_family_popover_filters_and_dispatches_selection
GraphSurfaceControls::test_floating_toolbar_grouped_surface_popover_dispatches_surface_actions
GraphSurfaceControls::test_floating_toolbar_routes_surface_kind_actions_to_surface_dispatch
GraphSurfaceControls::test_floating_toolbar_fullscreen_click_survives_viewer_action_refresh
GraphSurfaceControls::test_floating_toolbar_does_not_fall_back_to_node_dispatch_when_surface_action_unhandled
GraphSurfaceControls::test_floating_toolbar_tooltips_stay_clear_of_scaled_toolbar_hit_area
GraphSurfaceControls::test_floating_toolbar_renders_checked_action_state_without_disabling_button
GraphSurfaceControls::test_floating_toolbar_run_action_exposes_selected_run_menu
GraphSurfaceControls::test_floating_toolbar_buttons_support_keyboard_tab_and_enter
GraphSurfaceControls::test_floating_toolbar_visibility_tracks_host_toolbar_active_flag
GraphSurfaceControls::test_floating_toolbar_uses_readable_shell_accent_for_web_style_actions
GraphSurfaceControls::test_floating_toolbar_anchor_flip_does_not_trigger_binding_loop
GraphSurfaceControls::test_selection_envelope_defaults_to_minimal_affordance_and_tracks_bounds
GraphSurfaceControls::test_selection_envelope_minimal_tooltip_stays_clear_of_affordance
GraphSurfaceControls::test_selection_envelope_click_affordance_and_right_click_trigger_menu
GraphSurfaceControls::test_selection_envelope_side_rail_dispatches_enabled_actions_only
GraphSurfaceControls::test_selection_envelope_hides_edge_only_and_disables_straighten_without_internal_edge
```

### Shell-isolation target inventory

These 51 target IDs are current `full.shell_isolation` child-process targets.
Each target has one hard child timeout, serial tests inside the child, and a
bounded outer worker pool. SHA-256 over this ordered list is
`2DACD2F801DDF72ABA2CDCA0099EE698F5BB40E99B9E4980269AF30A676D8EC0`.
The canonical order is declaration order from
`tuple(tests.shell_isolation_runtime.load_target_registry())`, not the sorted
order returned by `list_target_ids()`; the displayed list and hash input use
that same tuple.

```text
main_window__drop_connect_and_workflow_io__project_and_selection
main_window__drop_connect_and_workflow_io__connection_drag_and_cycle
main_window__drop_connect_and_workflow_io__connection_constraints_and_library_drop
main_window__drop_connect_and_workflow_io__quick_insert_and_workflow_mutations
main_window__drop_connect_and_workflow_io__workflow_round_trip_and_install
main_window__drop_connect_and_workflow_io__nested_category_startup
main_window__drop_connect_and_workflow_io__workflow_updates_and_nested_drop
main_window__edit_clipboard_history__graph_edits_and_clipboard_basics
main_window__edit_clipboard_history__clipboard_artifacts_and_backdrops
main_window__edit_clipboard_history__clipboard_history_and_undo
main_window__passive_property_editors
main_window__passive_style_context_menus
main_window__shell_basics_and_search__menus_and_settings
main_window__shell_basics_and_search__preferences_and_dialogs
main_window__shell_basics_and_search__typography_labels_and_bridges
main_window__shell_basics_and_search__node_browser_and_tabs
main_window__shell_basics_and_search__qml_canvas_and_preferences
main_window__shell_basics_and_search__workspace_actions
main_window__shell_basics_and_search__graph_search
main_window__view_library_inspector__panes_and_console
main_window__view_library_inspector__graph_and_library
main_window__view_library_inspector__subnodes_and_inspector
main_window__view_library_inspector__ports_payloads_and_viewport
main_window__view_library_inspector__views_and_workspaces
main_window__passive_image_nodes__editors_and_storage
main_window__passive_image_nodes__crop_interactions
main_window__passive_pdf_nodes__editors_and_storage
main_window__passive_pdf_nodes__toolbar_and_page_resolution
main_window__bridge_local_pack__contracts_and_library_qml
main_window__bridge_local_pack__remaining_qml_and_runtime
main_window__graph_canvas_host_subprocess
script_editor__test_script_editor_binds_to_selected_python_script_node
script_editor__test_script_editor_state_persists_in_metadata
script_editor__test_script_editor_exposes_cursor_diagnostics_and_dirty_state
script_editor__test_set_script_editor_panel_visible_focuses_editor_for_script_node
script_editor__test_script_apply_failure_keeps_draft_dirty
script_editor__test_numeric_overflow_draft_stays_dirty_and_leaves_graph_unchanged
script_editor__test_script_apply_failure_draft_survives_panel_reopen
script_editor__test_script_draft_survives_same_node_property_refresh
run_controller__test_stream_log_events_are_scoped_to_active_run
run_controller__test_stale_run_events_do_not_mutate_active_run_ui
run_controller__test_failure_focus_reveals_parent_chain_when_present
run_controller__test_node_settled_failure_centers_failed_node_and_retains_root_error_details
project_session__test_session_restore_recovers_workspace_order_active_workspace_and_view_camera
project_session__test_open_project_rejects_saved_node_when_startup_preferences_disable_addon
project_session__test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc
project_session__test_recovery_prompt_accept_loads_newer_autosave
project_session__test_recovery_prompt_reject_keeps_empty_startup_project_and_discards_autosave
project_session__test_restore_session_handles_corrupted_session_and_autosave_files
project_session__test_recovery_prompt_is_deferred_until_main_window_is_visible
project_session__test_recent_project_paths_are_owned_by_explicit_session_state
```

### Phase and current-owner inventory

| Inventory | Phase / isolation | Current owner |
| --- | --- | --- |
| Program A Python cohort | Existing pytest fast/gui/serial routing; collected serially for T00 | Registry, add-on, execution, persistence, and run-controller suites listed above |
| Program B Python cohort | Existing pytest fast/gui/serial routing; collected serially for T00 | Direct graph, canvas, media, viewer, plot, edge, port, and presentation suites listed above |
| 62 affected QML selectors | `gui.qml_quick`; native `qmltestrunner` process | `tests/qml_quick/tst_graph_node_host.qml` and `tst_graph_surface_controls.qml` |
| 31 main-window target groups | `full.shell_isolation`; one child per target group | `tests/shell_isolation_main_window_targets.py` |
| 20 controller/session targets | `full.shell_isolation`; one child per target | `tests/shell_isolation_controller_targets.py` |

## Test Migration Ledger

Every removed Python node ID, qualified QML selector, or shell target gets one
row before deletion. Many-to-one replacements still require one row per old ID.
The ledger begins empty because T00 moves no tests.

Allowed final dispositions:

- `retained`
- `moved_to_owner`
- `replaced_by_owner_test`
- `replaced_by_qml_quick`
- `retained_real_shell_lifecycle`
- `redundant_existing_owner_proof`
- `deleted_obsolete_behavior`

`pending_migration` is the only provisional disposition. Either program may use
it only while the row's owning task is `NOT STARTED` or `IN PROGRESS`. Final
rows require non-pending collection, execution, and accepted-commit evidence;
`This commit` is permitted for a self-referential current commit. Program A rows
must be final before T13 is accepted; all Program B rows must be final before
T25 is accepted.

ID kinds and phase/isolation values are exact:

- `python`: a pytest node ID beginning `tests/` and containing `::`; phase is
  `fast.pytest`, `fast.serial.pytest`, `gui.pytest`, `gui.serial.pytest`, or
  `slow.pytest`.
- `qml_quick`: `TestCase::test_name`; phase is
  `gui.qml_quick / qmltestrunner`.
- `shell_target`: a manifest target ID; phase is
  `full.shell_isolation / child process`.

Every field is required. `N/A` is legal only for the production owner and
replacement of `deleted_obsolete_behavior`, or for the replacement of a
retained same-ID case. Use an explicit assertion-equivalence explanation even
when a test is retained.

| Program | Owning task | ID kind | Old ID / selector / target | Behavior guarded | Production owner | Phase / isolation | Disposition | Replacement IDs / selectors | Assertion equivalence | Collecting commit | Execution result | Accepted commit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | T01 | python | tests/test_plugin_loader.py::test_generic_addon_state_normalization_preserves_enabled_and_pending_restart | Generic add-on state normalization | ea_node_editor.addons.state_changes | fast.pytest | moved_to_owner | tests/test_addon_state_changes.py::test_generic_addon_state_normalization_preserves_enabled_and_pending_restart | Same normalized enabled and pending-restart mapping | This commit | PASS — state/catalog/registry/plugin cohort, 73 tests | This commit |
| A | T01 | python | tests/test_plugin_loader.py::test_set_addon_state_updates_the_generic_addon_state_store | Generic add-on state update | ea_node_editor.addons.state_changes | fast.pytest | moved_to_owner | tests/test_addon_state_changes.py::test_set_addon_state_updates_the_generic_addon_state_store | Same generic state write and readback | This commit | PASS — state/catalog/registry/plugin cohort, 73 tests | This commit |
| A | T01 | python | tests/test_plugin_loader.py::test_hot_apply_uses_runtime_coordinator_boundary_for_runtime_rebuild | Standalone coordinator injection seam | N/A | fast.pytest | deleted_obsolete_behavior | N/A | Injection-only parallel coordinator deleted; direct-owner absence guard proves no replacement seam | This commit | PASS — architecture absence guard | This commit |
| A | T01 | python | tests/test_plugin_loader.py::test_hot_apply_failure_keeps_consumers_and_persisted_preference_unchanged | Add-on publication failure preserves consumers and preferences | ea_node_editor.ui.shell.registry_replacement | fast.pytest | redundant_existing_owner_proof | tests/test_registry_replacement.py::test_addon_preference_failure_restores_every_published_consumer | Existing guarded owner proves complete reverse rollback and unchanged preferences after persistence failure | 2d8d5dbe | PASS — state/catalog/registry/plugin cohort, 73 tests | This commit |
| A | T01 | python | tests/test_plugin_loader.py::test_hot_apply_publishes_consumers_then_persists_success | Add-on publication precedes persistence | ea_node_editor.ui.shell.registry_replacement | fast.pytest | redundant_existing_owner_proof | tests/test_registry_replacement.py::test_addon_apply_uses_transaction_and_persists_preferences_last | Existing guarded owner proves full consumer order, persistence last, and notification after persistence | 2d8d5dbe | PASS — state/catalog/registry/plugin cohort, 73 tests | This commit |
| A | T01 | python | tests/test_dpf_runtime_service.py::DpfRuntimeServiceTests::test_hot_apply_disable_rebuilds_worker_runtime_and_reenable_restores_dpf_services | Worker runtime reset invalidates DPF handles and restores DPF services | ea_node_editor.execution.worker_services | fast.pytest | moved_to_owner | tests/test_dpf_runtime_service.py::DpfRuntimeServiceTests::test_worker_runtime_rebuild_invalidates_handles_and_restores_dpf_services | Same handle invalidation and backend/service restoration through the direct worker owner | This commit | PASS — DPF/runtime/viewer cohort, 48 tests and 19 subtests | This commit |
| A | T01 | python | tests/test_dpf_runtime_service.py::DpfRuntimeServiceTests::test_restart_required_apply_only_persists_pending_restart_state | Restart-required add-on state is pending without runtime rebuild | ea_node_editor.addons.state_changes | fast.pytest | replaced_by_owner_test | tests/test_addon_state_changes.py::test_prepare_restart_required_state_marks_pending_without_runtime_work; tests/test_registry_replacement.py::test_restart_required_addon_persists_pending_without_registry_build | Pure owner proves pending state; sole transaction owner proves one persistence and zero builds/admission/publication | This commit | PASS — state/catalog/registry/plugin cohort, 73 tests | This commit |
| A | T01 | python | tests/test_dpf_viewer_node.py::DpfViewerNodeTests::test_hot_apply_toggle_rebuilds_scene_between_live_node_and_disabled_registry | DPF viewer scene follows disabled and re-enabled registries without deleting graph data | ea_node_editor.ui.shell.registry_replacement | fast.pytest | replaced_by_owner_test | tests/test_registry_replacement.py::test_real_coordinator_disables_and_reenables_dpf_registry_and_viewer_services; tests/test_registry_replacement.py::test_real_coordinator_refuses_disabling_dpf_used_by_open_graph | Real coordinator proves permitted DPF/viewer rebuild and fail-closed refusal for an incompatible open DPF graph without graph mutation | This commit | PASS — state/catalog/registry/plugin cohort, 73 tests | This commit |
| A | T01 | python | tests/test_execution_viewer_service.py::ViewerSessionServiceTests::test_hot_apply_rebuild_clears_cached_dpf_transport_and_restores_live_materialization | Worker runtime rebuild clears cached DPF transport and restores materialization | ea_node_editor.execution.worker_services | fast.pytest | moved_to_owner | tests/test_execution_viewer_service.py::ViewerSessionServiceTests::test_worker_runtime_rebuild_clears_cached_dpf_transport_and_restores_live_materialization | Same transport cleanup and rematerialization through the direct worker owner | This commit | PASS — DPF/runtime/viewer cohort, 48 tests and 19 subtests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_function_contract_rejects_inconsistent_fields | Trusted backend function contract validation | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_function_contract_rejects_inconsistent_fields | Same invalid callable, tuple, uniqueness, trimming, and paired-field rejections | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_functions_are_static_deterministic_and_worker_compatible | Trusted backend static deterministic function contribution | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_functions_are_static_deterministic_and_worker_compatible | Same non-execution, provenance, immutable generation, deterministic fingerprint, and worker-readable declaration assertions | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_internal_builtin_function_entries_keep_no_plugin_provenance | Reserved built-in function provenance | ea_node_editor.nodes.builtin_catalog | fast.pytest | moved_to_owner | tests/test_builtin_function_infrastructure.py::test_internal_builtin_function_entries_keep_no_plugin_provenance | Same reserved entry and absent provenance assertions | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[sources0] | Trusted backend source container must be immutable | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[list-container] | Same list-container rejection and zero-contribution assertions | This commit | PASS — exact collected replacement node | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[sources1] | Trusted backend source path may not escape its package | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[parent-traversal] | Same parent-traversal rejection and zero-contribution assertions | This commit | PASS — exact collected replacement node | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[sources2] | Trusted backend source paths are case-fold unique | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[casefold-duplicate] | Same case-insensitive duplicate rejection and zero-contribution assertions | This commit | PASS — exact collected replacement node | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[sources3] | Trusted backend source members must be text | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[bytes-source] | Same bytes-source rejection and zero-contribution assertions | This commit | PASS — exact collected replacement node | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[sources4] | Trusted backend source member size is bounded | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_function_sources_reject_path_duplicate_and_size_bounds[oversized-source] | Same oversized-source rejection and zero-contribution assertions | This commit | PASS — exact collected replacement node | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_function_mismatch_and_unavailability_contribute_nothing | Unavailable or mismatched trusted contribution is atomic and empty | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_function_mismatch_and_unavailability_contribute_nothing | Same unavailable-source non-call and empty registry/bundle assertions | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_owner_replacement_removes_old_functions_and_descriptors | Trusted owner replacement removes the prior complete contribution | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_owner_replacement_removes_old_functions_and_descriptors | Same old-owner removal, new-owner inventory, bundle order, and fingerprint change assertions | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_bundle_and_fingerprint_failures_roll_back_the_whole_owner | Trusted bundle or fingerprint failure rolls back the whole owner | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_bundle_and_fingerprint_failures_roll_back_the_whole_owner | Same mismatched bundle and fingerprint exception with byte-identical registry state | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_register_plugin_backends_redacts_availability_and_failure_details | Trusted backend diagnostics redact hostile details | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_register_plugin_backends_redacts_availability_and_failure_details | Same unavailable/failure labels and absence of private path, token, and traceback data | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_failure_logs_omit_hostile_dynamic_exception_class_names | Trusted backend logs omit hostile exception class names | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_failure_logs_omit_hostile_dynamic_exception_class_names | Same hostile class/path/message redaction assertions | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_failure_does_not_leave_partial_type_contribution | Failed trusted contribution leaves no partial data type | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_failure_does_not_leave_partial_type_contribution | Same zero spec/bundle/type/manifest residue assertions | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_type_conflict_does_not_leave_partial_descriptor | Trusted type conflict leaves no partial descriptor | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_type_conflict_does_not_leave_partial_descriptor | Same existing owner preservation and no conflict-family residue assertions | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_plugin_backend_descriptor_publishes_toolchain_runtime_artifact_and_surface_contracts | Trusted descriptor publishes complete manifest contracts | ea_node_editor.addons.registry_contributions | fast.pytest | moved_to_owner | tests/test_addon_registry_contributions.py::test_plugin_backend_descriptor_publishes_toolchain_runtime_artifact_and_surface_contracts | Same loaded descriptor and exact merged runtime/toolchain/artifact/surface manifest | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T02 | python | tests/test_plugin_loader.py::test_frozen_import_availability_uses_the_actual_bundle_importer | Frozen bundled-import availability uses the real importer | ea_node_editor.nodes.function_bundle | fast.pytest | moved_to_owner | tests/test_function_bundle.py::test_frozen_import_availability_uses_the_actual_bundle_importer | Same frozen `find_spec` path and unavailable result | This commit | PASS — remediated T02 public/add-on/built-in cohort, 60 tests | This commit |
| A | T03 | python | tests/test_registry_validation.py::RegistryValidationTests::test_dynamic_port_group_declarations_are_validated | Dynamic port-group declaration structure | ea_node_editor.nodes.spec_validation | fast.pytest | moved_to_owner | tests/test_spec_validation.py::SpecValidationTests::test_dynamic_port_group_declarations_are_validated | Same valid declaration and all invalid tuple/type/id/property/direction/bounds/callable/rename cases | This commit | PASS — direct validator/coercion and atomicity smoke, 8 tests/30 subtests | This commit |
| A | T03 | python | tests/test_registry_validation.py::RegistryValidationTests::test_dynamic_port_resolver_failures_are_atomic_validation_errors | Dynamic resolver result validation and registration atomicity | ea_node_editor.nodes.spec_validation; ea_node_editor.nodes.registry | fast.pytest | moved_to_owner | tests/test_spec_validation.py::SpecValidationTests::test_dynamic_port_resolver_failures_are_atomic_validation_errors; tests/test_registry_validation.py::RegistryValidationTests::test_dynamic_resolver_failure_keeps_complete_registry_identity_unchanged | Direct owner preserves the resolver exception/tuple/port/key/data-access/kind/direction/default/collision/bounds rejection matrix; registry integration separately proves entries, catalog snapshot/fingerprint, plugin fingerprint, and contract fingerprint remain unchanged | This commit | PASS — remediation resolution/validator/atomicity smoke | This commit |
| A | T03 | python | tests/test_registry_validation.py::RegistryValidationTests::test_register_rejects_invalid_enum_default | Enum default coercion rejection | ea_node_editor.nodes.property_coercion | fast.pytest | moved_to_owner | tests/test_property_coercion.py::test_invalid_enum_default_raises_exact_value_error | Same property and exact ValueError text through the extracted validator/coercion path | This commit | PASS — direct validator/coercion and atomicity smoke, 8 tests/30 subtests | This commit |
| A | T03 | python | tests/test_registry_validation.py::RegistryValidationTests::test_register_rejects_non_serializable_json_default | JSON default serialization rejection | ea_node_editor.nodes.property_coercion | fast.pytest | moved_to_owner | tests/test_property_coercion.py::test_non_serializable_json_default_raises_exact_value_error | Same property and ValueError prefix through the extracted validator/coercion path | This commit | PASS — direct validator/coercion and atomicity smoke, 8 tests/30 subtests | This commit |
| A | T04 | python | tests/test_registry_validation.py::RegistryValidationTests::test_default_properties_are_deep_copied_per_instance | Default property deep-copy isolation | ea_node_editor.nodes.property_normalization | fast.pytest | moved_to_owner | tests/test_property_normalization.py::PropertyNormalizationTests::test_default_properties_are_deep_copied_per_instance | Same two-instance nested default mutation and unchanged second value through the retained registry API | This commit | PASS — direct normalization/registry-filter smoke, 7 tests | This commit |
| A | T04 | python | tests/test_registry_validation.py::RegistryValidationTests::test_dynamic_ports_resolve_in_declared_order_and_normalize_backing_properties | Dynamic backing-property normalization and derived-port/filter behavior | ea_node_editor.nodes.property_normalization; ea_node_editor.nodes.registry | fast.pytest | moved_to_owner | tests/test_property_normalization.py::PropertyNormalizationTests::test_dynamic_ports_resolve_in_declared_order_and_normalize_backing_properties; tests/test_registry_validation.py::RegistryValidationTests::test_dynamic_ports_participate_in_registry_filters_without_factory_construction | Direct owner preserves ordered dynamic resolution, backing-key normalization, bounds failure, and no construction; renamed registry test preserves text/type/direction filter behavior without starting T05 | This commit | PASS — direct normalization/registry-filter smoke, 7 tests | This commit |
| A | T04 | python | tests/test_registry_validation.py::RegistryValidationTests::test_normalize_property_value_and_properties_fall_back_to_defaults | Scalar coercion/default fallback and include-defaults behavior | ea_node_editor.nodes.property_normalization | fast.pytest | moved_to_owner | tests/test_property_normalization.py::PropertyNormalizationTests::test_normalize_property_value_and_properties_fall_back_to_defaults | Same successful coercion, invalid-value fallback, bool fallback, and include-defaults outputs through the retained registry APIs | This commit | PASS — direct normalization/registry-filter smoke, 7 tests | This commit |
| A | T04 | python | tests/test_dpf_node_catalog.py::DpfNodeCatalogTests::test_legacy_curated_time_values_infer_explicit_time_scope_mode | Legacy single-selector DPF workflow time-scope inference | ea_node_editor.nodes.property_normalization | fast.pytest | moved_to_owner | tests/test_property_normalization.py::PropertyNormalizationTests::test_legacy_curated_time_values_infer_explicit_time_scope_mode | Same set-id and time-value mode inference for the curated workflow spec | This commit | PASS — direct normalization/registry-filter smoke, 7 tests | This commit |
| A | T04 | python | tests/test_dpf_node_catalog.py::DpfNodeCatalogTests::test_ambiguous_legacy_curated_time_values_require_explicit_mode | Ambiguous dual-selector DPF workflow time-scope handling | ea_node_editor.nodes.property_normalization | fast.pytest | moved_to_owner | tests/test_property_normalization.py::PropertyNormalizationTests::test_ambiguous_legacy_curated_time_values_require_explicit_mode | Same explicit removal of inferred `time_scope_mode` when both legacy selectors are populated | This commit | PASS — direct normalization/registry-filter smoke, 7 tests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_flowchart_category_exposes_locked_passive_catalog | Flowchart Library category inventory | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_flowchart_category_exposes_locked_passive_catalog | Same exact passive Flowchart IDs and category payload | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_planning_category_exposes_locked_passive_catalog | Planning Library category inventory | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_planning_category_exposes_locked_passive_catalog | Same exact passive Planning IDs and category payload | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_annotation_category_exposes_locked_passive_catalog | Annotation Library category inventory | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_annotation_category_exposes_locked_passive_catalog | Same exact passive Annotation IDs and category payload | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_group_is_listed_under_utilities_canvas_parent_and_leaf_filters | Group ancestor/leaf Library filtering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_group_is_listed_under_utilities_canvas_parent_and_leaf_filters | Same Group type, display, leaf path, and Utilities/Canvas ancestor options | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_filter_by_text_and_category | Text plus category Library intersection | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_filter_by_text_and_category | Same Excel read/write discoverability under Input/Output | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_filter_by_data_type_and_direction | Primary-type and direction Library filtering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_filter_by_data_type_and_direction | Same Path-input File Read discoverability | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_tabular_data_input_is_filterable_when_addon_available | Add-on Library primary/output type filtering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_tabular_data_input_is_filterable_when_addon_available | Same Path/Tabular/Array filter results under enabled Tabular add-on | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_filter_by_direction_only_returns_matching_nodes | Direction-only Library filtering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_filter_by_direction_only_returns_matching_nodes | Same nonempty set with every projected item exposing an input port | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_combined_filters_apply_as_intersection | Query/category/type/direction Library intersection | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_combined_filters_apply_as_intersection | Same stable ordered Excel Write/Image Export/File Write result | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_filter_results_use_stable_predictable_sorting | Stable Library result ordering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_filter_results_use_stable_predictable_sorting | Same repeatable category/display/type ordering | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_nested_category_registry_filter_accepts_parent_category_path | DPF descendant-inclusive parent filtering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_nested_category_library_filter_accepts_parent_category_path | Same DPF core inventory and root-category constraint through path-backed Library filtering | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_nested_category_registry_legacy_flat_category_alias_is_not_descendant_inclusive | Flat display-category behavior at the production Library owner | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_nested_category_library_flat_display_matches_ancestor | Rewritten to preserve the maintained Library behavior: flat Ansys DPF display filtering matches descendants through ancestor display names; the production-dead registry-only empty result is removed | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_nested_category_registry_leaf_category_path_filter_is_precise | Precise DPF leaf filtering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_nested_category_library_leaf_category_path_filter_is_precise | Same scoping/result/viewer leaf inventories and exact category paths | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_filters.py::RegistryFilterTests::test_nested_category_registry_category_paths_include_dpf_ancestors | DPF category ancestors and retired flat bucket | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_nested_category_library_options_include_dpf_ancestors | Same DPF ancestors/leaves, Flowchart option, and absence of retired Operators bucket, derived from combined Library items | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_validation.py::RegistryValidationTests::test_dynamic_ports_participate_in_registry_filters_without_factory_construction | Temporary registry-query proof retained during T04 | N/A | fast.pytest | deleted_obsolete_behavior | N/A | Deleted with the production-dead registry query API; dynamic resolution/normalization remains proven by T04 direct-owner tests and maintained Library filtering operates on projected row payloads | This commit | PASS — architecture absence guard | This commit |
| A | T05 | python | tests/test_registry_validation.py::RegistryValidationTests::test_default_registry_accepts_foundational_dpf_port_types_in_filters | Foundational DPF Library type filtering | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_default_library_accepts_foundational_dpf_port_types | Same DPF category, ResultFile, Model, and Scoping output discoverability | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_registry_validation.py::RegistryValidationTests::test_filter_nodes_matches_ports_through_accepted_dpf_data_types | Primary plus accepted DPF type union | ea_node_editor.ui.shell.library_projection | fast.pytest | moved_to_owner | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_library_filters_primary_and_accepted_dpf_data_types_as_union | Same Model/DataSources accepted-input and ObjectHandle primary input/output matches | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_dpf_node_catalog.py::DpfNodeCatalogTests::test_default_registry_exposes_dpf_category_and_scoping_ports | Complete DPF Library taxonomy and scoping discoverability | ea_node_editor.ui.shell.library_projection | fast.pytest | replaced_by_owner_test | tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_nested_category_library_filter_accepts_parent_category_path; tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_nested_category_library_leaf_category_path_filter_is_precise; tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_nested_category_library_options_include_dpf_ancestors; tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_default_library_accepts_foundational_dpf_port_types | Direct Library owner collectively proves DPF root/leaf/category options plus scoping/Model/ResultFile types; DPF catalog tests retain descriptor/runtime behavior | This commit | PASS — Library/Quick Insert/cache cohort, 41 tests/2 subtests | This commit |
| A | T05 | python | tests/test_number_slider_node.py::TestNumberSliderSpec::test_categories_include_data_control | Number Slider category discoverability | ea_node_editor.ui.shell.library_projection | fast.pytest | redundant_existing_owner_proof | tests/test_number_slider_node.py::TestNumberSliderSpec::test_spec_shape; tests/test_library_projection.py::LibraryProjectionRegistryCoverageTests::test_filter_by_text_and_category | Existing spec test pins `Data > Control`; direct Library category/filter coverage proves projected discoverability without a registry category API | This commit | PASS — focused Number Slider and Library suites | This commit |

## Program A Performance Baseline Contract

T00 locks measurement contracts but records no fresh timing verdict. The listed
`timeit` commands are syntax smokes only because `timeit` reports the best
repeat, not all observations. Acceptance uses a task-local stdlib probe copied
from this block; do not add or modify a tracked benchmark framework:

```python
import gc, json, math, statistics, time

# The task row below defines measure(), verify(), warmups, samples, and loops.
for _ in range(warmups):
    verify(measure())
raw_ns = []
for _ in range(samples):
    gc.collect()
    started = time.perf_counter_ns()
    for _ in range(loops):
        result = measure()
    raw_ns.append((time.perf_counter_ns() - started) / loops)
    verify(result)
ordered = sorted(raw_ns)
median = statistics.median(raw_ns)
mean = statistics.fmean(raw_ns)
print(json.dumps({
    "raw_ns": raw_ns,
    "median_ns": median,
    "p95_ns": ordered[math.ceil(0.95 * len(ordered)) - 1],
    "cv": 0.0 if mean == 0 else statistics.pstdev(raw_ns) / mean,
    "mad_ns": statistics.median(abs(value - median) for value in raw_ns),
}, sort_keys=True))
```

Every baseline/candidate side uses at least three isolated, counterbalanced
process runs; each process uses `warmups=3`, `samples=7`, and the task row's
fixed `loops`. The ledger retains every JSON `raw_ns` list, commit, fixture hash,
cache state, Qt/backend/display/power state, and structural counter snapshot.
Structural equality is checked before timing. Until that task's pre-edit run is
recorded, its verdict is exactly: `measurement contracts locked; task-specific
baseline required before editing`.

| Task | Exact starting fixture and proving nodes | `measure()` operation / loops | Structural counters and equality contract | T00 verdict |
| --- | --- | --- | --- | --- |
| T01 | Existing registry-replacement harness; `test_addon_apply_uses_transaction_and_persists_preferences_last`, `test_addon_preference_failure_restores_every_published_consumer`, all `test_publication_failure_rolls_back_in_exact_reverse_order[...]`, and both refusal tests | One complete enabled-state candidate/check/publish/persist transaction with injected no-I/O consumers; `loops=1` | Candidate/final registry builds and fingerprints, requested-state agreement checks, admission checks, publication callbacks/order, persistence calls, notifications, rollback callbacks/order | Measurement contracts locked; task-specific baseline required before editing |
| T02 | Default 933-spec registry plus deterministic public/built-in/add-on bundles; `test_candidate_registry_statically_overrides_package_and_matches_final`, `test_plugin_fingerprint_is_independent_of_install_and_generation_roots`, `test_plugin_backend_functions_are_static_deterministic_and_worker_compatible`, `test_plugin_backend_function_mismatch_and_unavailability_contribute_nothing`, `test_plugin_bundle_and_fingerprint_failures_roll_back_the_whole_owner`, `test_worker_rehashes_generation_before_first_import`, and `test_placeholder_sources_form_one_noop_internal_bundle` | Materialize the same prepared bundles and contract fingerprint; `loops=1` | Exact bundle bytes/digests, type-ID and function-ref order, plugin/full-registry fingerprints, filesystem traversals, archive/member reads, backend availability calls, worker-generation reads | Measurement contracts locked; task-specific baseline required before editing |
| T03 | Accepted/rejected corpus from `test_default_builtin_catalog_registers_all_current_specs`, `test_descriptor_and_plugin_bundle_registration_are_atomic`, both `test_owner_replacement_rolls_back_when_surviving_*`, `test_dynamic_port_group_declarations_are_validated`, `test_dynamic_port_resolver_failures_are_atomic_validation_errors`, `test_register_rejects_invalid_enum_default`, and `test_register_rejects_non_serializable_json_default` | Validate/build the fixed registry corpus with exact staged catalog; `loops=1` | Validator/coercion call order/count, exception class/text sequence, mutation/copy count, staged catalog installs, full catalog passes/traversals | Measurement contracts locked; task-specific baseline required before editing |
| T04 | Fixed scalar/interval/tree/dynamic/Select/slider/Web/DPF corpus from `test_default_properties_are_deep_copied_per_instance`, `test_dynamic_ports_resolve_in_declared_order_and_normalize_backing_properties`, `test_normalize_property_value_and_properties_fall_back_to_defaults`, `test_legacy_curated_time_values_infer_explicit_time_scope_mode`, `test_ambiguous_legacy_curated_time_values_require_explicit_mode`, and Web browser-state normalization tests | Normalize the ordered corpus and hash canonical outputs; `loops=100` | One base-spec lookup, one instance resolution, one property traversal per call; coercion, validation, and deep-copy counts; exact output hash and copy isolation | Measurement contracts locked; task-specific baseline required before editing |
| T05 | Whole `tests/test_library_projection.py`, `tests/test_quick_insert_projection.py`, and `tests/test_shell_library_projection_cache.py`; fixed default registry plus one custom-workflow item | Build/read Library display/grouped/filter/category projections and blank/nonblank connection Quick Insert in fixed order; `loops=20` | Category-tree constructions, grouped/display projections, cache hits/misses/invalidations, registry/custom-workflow traversals, result order/hash | Measurement contracts locked; task-specific baseline required before editing |
| T06 | DPF fake-provider fixtures in `test_cached_result_and_model_lease_once_per_requesting_run`, `test_load_result_file_and_model_reuse_stable_cached_handles`, `test_reset_invalidates_cached_model_handles_and_rebuilds_service_cache`, `test_worker_services_lazy_service_defers_optional_dpf_import`, `test_large_fields_metadata_is_deterministic_and_below_handle_limit`, DPF analysis cases, and all `tests/test_dpf_materialization.py` | Measure lazy factory, first load, cached load, one analysis operation, and one materialization as separate labels; `loops=1` | Optional imports, service/cache identity, model/result handles, leases, cleanup/reset calls/warnings, metadata items/bytes, staged files/bytes | Measurement contracts locked; task-specific baseline required before editing |
| T07 | `StopRunCommand(run_id='r', workspace_id='w')` plus the existing full protocol corpus in `tests/test_execution_protocol.py` and `tests/test_execution_viewer_protocol.py` | `dict_to_command(command_to_dict(command))`; `loops=100000` | Byte/dict/field-order hash, validation failures, serialization constructions, allocations/copies | Measurement contracts locked; task-specific baseline required before editing |
| T08 | Process/trusted/external client fixtures from `test_process_respawn_advances_generation_and_replaces_queues`, `test_trusted_listener_drops_retired_generation_events`, `test_external_python_same_live_worker_skips_preflight_and_generation_change`, `test_backend_viewer_forwarding_has_exact_query_and_empty_invalidation_contract`, `test_post_terminal_catalog_change_recycles_each_backend_generation`, and worker death/timeout recovery tests | Separate labels for cold start, warm reuse, dispatch, viewer command, and retirement; `loops=1` | Processes, threads, request/event queues, listeners/subscriptions, generations, locks/order, viewer routes, retirement/cleanup calls | Measurement contracts locked; task-specific baseline required before editing |
| T09 | `test_late_settlement_is_node_revision_safe_and_unrelated_branch_stays_current`, `test_preparation_eviction_and_trigger_reservation_cleanup_commit_and_discard`, lease-release tests, `test_stage_build_bind_lookup_and_lazy_payload_restart`, `test_bind_lookup_and_payload_reads_are_lazy_and_ordered`, GC/prune tests, and strict record/result tests | Separate prepare/settle/select/evict and durable stage/open/lookup labels; `loops=20` in-memory and `loops=1` filesystem | Hash calls, JSON encodes/decodes, file scans/reads/writes, store locks/order, leases, settlements, selections, eviction/GC candidates and deletes | Measurement contracts locked; task-specific baseline required before editing |
| T10 | Deterministic project/runtime fixtures from `test_prepare_is_private_and_dispatch_registers_context_before_sync_events`, `test_start_and_run_use_prepared_dispatch_and_legacy_entrypoints_are_absent`, `test_headless_boundaries_compile_once_and_preserve_authored_snapshot`, `test_cold_route_uses_execute_only_key_and_failed_start_cleans_context`, `test_invalidation_holds_lifecycle_through_plan_and_store`, `test_legacy_start_and_prepared_dispatch_share_one_lock_order`, and real-process reuse smoke | Separate fresh import, project load, prepare, dispatch, and synchronous run labels; `loops=1` | Imported modules, project decode/JSON passes, plan/key/output hashes, compile/prepare/dispatch/run counts, lifecycle/publication/store locks and order, contexts/reservations/cleanup | Measurement contracts locked; task-specific baseline required before editing |
| T11 | Current `tests.test_run_controller_unit._RunHostStub`, one `ShellRunState`, and exact projection sequence `run_started → node_started → accepted node_settled → solution_state_changed`; anchors: `test_node_execution_bridge_run_events_project_running_and_completed_nodes`, `test_node_settled_caches_typed_outputs_by_workspace_node_and_run`, `test_solution_state_events_filter_project_and_monotonic_revision`, elapsed/warning/cache tests | Replay 10,000 state-projection sequences without Qt event delivery; `loops=1` | Each signal count, accepted cache writes, dict constructions/copies, solution queries, availability observations, QObjects and timers (expected zero added) | Measurement contracts locked; task-specific baseline required before editing |
| T12 | Same `_RunHostStub`/`ShellRunState`; success sequence `run_started → node_started → accepted node_settled → solution_state_changed → viewer_invalidation_committed → run_completed`, plus stale-event rejection and fatal `run_failed`; anchors include T11 nodes, `test_run_completed_preserves_settled_state_while_stop_and_failure_clear_it`, `test_stale_run_event_is_ignored`, `test_fatal_failure_discards_pending_auto_run`, `test_viewer_session_bridge_context_property_exists_and_rerun_invalidates_current_workspace`, and `test_fatal_run_failed_event_invalidates_viewer_sessions_as_worker_reset` | Replay 10,000 direct intake sequences, then one real queued Qt signal sample; `loops=1` | Decodes, runtime subscriptions, Qt signal connections/event-loop hops, solution syncs, viewer adoptions/resets, accepted cache publications, terminal transitions, Auto drains/clears, end-to-end latency | Measurement contracts locked; task-specific baseline required before editing |

Syntax smokes only:

```powershell
.\venv\Scripts\python.exe -m timeit -r 1 -n 1 -s "from ea_node_editor.nodes.bootstrap import build_default_registry" "r=build_default_registry(); r.contract_fingerprint()"
.\venv\Scripts\python.exe -m timeit -r 1 -n 1000 -s "from ea_node_editor.execution.protocol import StopRunCommand, command_to_dict, dict_to_command; c=StopRunCommand(run_id='r',workspace_id='w')" "dict_to_command(command_to_dict(c))"
.\venv\Scripts\python.exe -m timeit -r 1 -n 1 -s "from ea_node_editor.execution.headless_runtime import CorexRuntime" "r=CorexRuntime(); r.shutdown()"
```

The existing graph harness is reserved for Program B. Its canonical real fixture
is `examples/stress_1200_nodes.cxproj`, 1,203,145 bytes, SHA-256
`DBE1B48CCD611B762615DAB9D8CE5FCA1935441449EAFFC362979126F445C4FB`.
Offscreen/software results remain diagnostic; display-attached results are needed
for release-style rendering conclusions.

## Performance Evidence

| Task | Metric and fixture | Baseline runs | Candidate runs | Attribution / repeat | Verdict |
| --- | --- | --- | --- | --- | --- |
| T01 | In-memory registry-replacement transaction from `tests/test_registry_replacement.py`, baseline SHA-256 `400E73E9...98D2E`, pre-remediation candidate `1A01EF8D...21DA`; Python 3.11.6; `warmups=3`, `samples=7`, `loops=1`; fresh registries/controller per measure; real add-on invalidation; Qt/backend/display N/A; Windows `Office` power scheme; three isolated processes per side | Run 1 raw ns `[6362200,4802700,5244100,4869600,4884600,5392500,6344700]`, median `5244100`, p95 `6362200`, CV `0.115657`, MAD `374500`; Run 2 `[5092200,4938100,4896500,5526100,4857400,4890800,5137200]`, median `4938100`, p95 `5526100`, CV `0.043305`, MAD `80700`; Run 3 `[5244800,4793200,5603800,4850300,4957900,5502700,5035900]`, median `5035900`, p95 `5603800`, CV `0.057221`, MAD `208900` | Run 1 raw ns `[5276600,4754800,4825400,4832900,5149200,5427900,5158400]`, median `5149200`, p95 `5427900`, CV `0.047215`, MAD `278700`; Run 2 `[4834800,4858600,5737300,4747600,4988400,5491200,5295100]`, median `4988400`, p95 `5737300`, CV `0.067980`, MAD `240800`; Run 3 `[5113100,6016000,4937500,4927000,5392300,5075400,6192500]`, median `5113100`, p95 `6192500`, CV `0.089704`, MAD `186100` | Recorded structural facts only: 2 candidate/final builds; equal fingerprint `450dee5a...f8f2`; 2 runtime + 2 viewer admission checks; identical publication order; 1 persistence; 1 notification; 0 rollback callbacks; final registry published. Post-remediation direct proof records exactly 2 requested-state checks on a valid apply; mismatches publish/persist/notify nothing. Baseline process-median `5035900 ns`; pre-remediation candidate `5113100 ns` (`+1.53%`). Baseline p95-median `5603800 ns`; candidate `5737300 ns` (`+2.38%`). Runs were sequential, not counterbalanced, and the candidate preceded the P1 state-agreement fix. | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTA NOT ATTRIBUTED` |
| T02 | Deterministic public loose/package + current built-in/add-on bundles, worker re-attestation, and schema-2 export; fixture SHA-256 `958EF1CC...7048`; Python 3.11.6; Office power scheme; warm paths after 3 warmups; 7 samples, loops 1, three isolated processes | Discovery raw ns: R1 `[644267900,655798000,660290300,664797100,659737300,657022900,649108600]`, median `657022900`, p95 `664797100`, CV `0.009912`, MAD `3267400`; R2 `[653505000,653379200,664665600,657547700,659131100,654496800,657845900]`, median `657547700`, p95 `664665600`, CV `0.005622`, MAD `3050900`; R3 `[655027500,661037300,660684000,665823400,656719500,660805700,654715600]`, median `660684000`, p95 `665823400`, CV `0.005608`, MAD `3964500`. Worker raw ns: R1 `[403282600,406554300,410228400,404924300,409854000,408373300,409704200]`, median `408373300`, p95 `410228400`, CV `0.006144`, MAD `1819000`; R2 `[408164000,405746100,407051900,409706200,405837800,413666500,409190500]`, median `408164000`, p95 `413666500`, CV `0.006242`, MAD `1542200`; R3 `[406077800,406082200,414520200,406696100,407270300,412811100,410611100]`, median `407270300`, p95 `414520200`, CV `0.007881`, MAD `1192500`. Export raw ns: R1 `[5163800,5389100,3758000,3663700,4815300,3983100,3718900]`, median `3983100`, p95 `5389100`, CV `0.157925`, MAD `319400`; R2 `[5176900,4133700,3917400,5250800,4072000,3841900,4527900]`, median `4133700`, p95 `5250800`, CV `0.122947`, MAD `291800`; R3 `[6486000,5138500,4108000,4306500,3852000,4666000,4070000]`, median `4306500`, p95 `6486000`, CV `0.181214`, MAD `359500` | Pending | Every run: 935 specs; 77 ordered function refs; bundle order `corex:builtin:functions, ea_node_editor.builtins.tabular_data, plugin:file:loose, plugin:package:t02_package`; bundle digests `2905AB2F...,3A0145CF...,EA2B28E9...,43FC8F4B...`; generation tree hashes `E9DFFA9D...,06132BB1...,FE549A1B...,D2AF81F8...`; total 129516 bytes; discovery type-order SHA `FB7A2552...B9E9`; function-ref order `C73902FE...E953`; plugin fingerprint `2450057B...D0B4`; full registry `8EC56A7D...321`; catalog `1D20C15D...31D2`; 2 root traversals, 1 loose read, 1 package member read, 2 add-on availability calls; worker independently reads 4 generations and produces type-order SHA `7565BBE8...3976`; export is 856 bytes SHA `2DDC81C5...170E`; source never executes | `BASELINE PASS — CANDIDATE RECORDED NEXT ROW` |
| T02 candidate | Same fixture/configuration as T02 baseline; availability instrumentation moved only to the new direct add-on owner | See T02 baseline row; process-median discovery `657547700 ns`, worker `408164000 ns`, export `4133700 ns`; median p95 discovery `664797100 ns`, worker `413666500 ns`, export `5389100 ns` | Discovery raw ns: R1 `[665161500,671626500,664818700,664457800,660988200,667220500,665861100]`, median `665161500`, p95 `671626500`, CV `0.004480`, MAD `703700`; R2 `[662045000,662338200,670476900,666476800,663262900,660028200,657256600]`, median `662338200`, p95 `670476900`, CV `0.006008`, MAD `2310000`; R3 `[658299000,657296300,658481800,657734000,657134100,657925900,737283600]`, median `657925900`, p95 `737283600`, CV `0.041564`, MAD `555900`. Worker raw ns: R1 `[408058500,407807700,413788400,404761700,407864600,413500500,407050300]`, median `407864600`, p95 `413788400`, CV `0.007651`, MAD `814300`; R2 `[420926400,411248100,414369800,408785000,409153400,400235100,402156700]`, median `409153400`, p95 `420926400`, CV `0.015923`, MAD `5216400`; R3 `[405826000,400064500,408430600,412214400,402717100,401727300,399170900]`, median `402717100`, p95 `412214400`, CV `0.010878`, MAD `3108900`. Export raw ns: R1 `[4775100,4062900,3959400,4849600,4244700,3705900,5181200]`, median `4244700`, p95 `5181200`, CV `0.114256`, MAD `530400`; R2 `[4267100,5791700,4023500,3774700,4880700,5634300,4137300]`, median `4267100`, p95 `5791700`, CV `0.160586`, MAD `492400`; R3 `[4349400,4375200,5504700,3991800,4113300,4050700,3770600]`, median `4113300`, p95 `5504700`, CV `0.121926`, MAD `236100` | Structural fields/counters exactly match the T02 baseline, including all bundle bytes/digests/order hashes/fingerprints, 2/1/1 discovery read counters, 2 availability calls, 4 worker generation reads, deterministic 856-byte export, and non-execution. A post-remediation structural-only rerun reproduced the same fixture hash and every listed value; it measured no timing or allocation parity. Process-median changes from the earlier sequential samples: discovery `+0.73%`, worker `-0.07%`, export `+2.69%`; median-p95 changes `+1.03%`, `+0.03%`, `+2.14%`. All are below the 5% repeat threshold; the single discovery p95 outlier remains visible in raw samples. Baseline and candidate were sequential rather than counterbalanced, so timing is not causally attributed. | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTAS NOT ATTRIBUTED` |
| T03 baseline | Eight named accepted/rejected validator and atomicity tests plus fixed `build_default_registry(include_public_plugins=False)` with DPF and Tabular enabled, MARS disabled; current `99f4c7e8`; Python 3.11.6; warm generation path after 3 warmups; 7 samples, loops 1, three isolated processes | Run 1 raw ns `[193256400,192847000,197183700,192761100,193786500,195572000,189277900]`, median `193256400`, p95 `197183700`, CV `0.011847`, MAD `530100`; Run 2 `[192206200,197953000,198478300,190879100,199403700,193353900,198113400]`, median `197953000`, p95 `199403700`, CV `0.016524`, MAD `1450700`; Run 3 `[197516800,196671800,203052300,193259000,197527700,197838900,194483500]`, median `197516800`, p95 `203052300`, CV `0.014604`, MAD `845000` | Pending | Named corpus: 2,847 validator calls, validation-order SHA `9376A3D5...C9B1`; 6,856 coercions, coercion-order SHA `06A41F2D...D964`; 7,398 deep copies; 29 catalog forks/snapshots, 66 `register_many`, 24,578 `require`, 0 `all_specs`; 37 normalized exception events, class/text-order SHA `ADD442F5...73B`. Full registry every run: 933 specs, 805 DPF specs, 171 data types, type-order SHA `B94BE97C...B381`, contract `15B4C3FD...DAAD`, plugin `9B8D9130...297A`, data catalog `1D20C15D...31D2`, exact add-on runtime config. Process-median `197516800 ns`; median p95 `199403700 ns`. | `BASELINE PASS — CANDIDATE PENDING` |
| T03 candidate | Same named corpus, fixed add-on configuration, interpreter, generation-cache state, warmups/samples/loops, and isolated-process shape as the T03 baseline | See baseline row; process-median `197516800 ns`; median p95 `199403700 ns` | Run 1 raw ns `[198887200,200381900,195176900,197644800,196556000,199482700,197875500]`, median `197875500`, p95 `200381900`, CV `0.008289`, MAD `1319500`; Run 2 `[198539500,198653700,197809000,199302600,197782100,198469400,203718100]`, median `198539500`, p95 `203718100`, CV `0.009608`, MAD `730500`; Run 3 `[208308000,209193200,209532800,233729600,232399100,239759000,204422900]`, median `209532800`, p95 `239759000`, CV `0.062936`, MAD `5109900` | Structural equality is exact: the named corpus repeats 2,847 validator calls/order SHA `9376A3D5...C9B1`, 6,856 coercions/order SHA `06A41F2D...D964`, 7,398 deep copies, 29 forks/snapshots, 66 registrations, 24,578 requirements, 0 full catalog traversals, and all 37 exception class/text events SHA `ADD442F5...73B`; the full registry repeats every baseline count, order hash, fingerprint, and add-on config. Process-median `198539500 ns` (`+0.52%`); median p95 `203718100 ns` (`+2.16%`). The noisy third candidate run remains visible. Baseline then candidate were sequential, not counterbalanced, so the narrow deltas are not causally attributed and did not trigger rollback. | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTAS NOT ATTRIBUTED` |
| T03 remediation structural | Same named corpus and fixed full-registry structure after the cycle removal and registry-atomicity proof | See T03 baseline and candidate timing rows | No new timing samples; earlier sequential candidate timing remains the only timing evidence | Exact repeat: 2,847 validator calls/order SHA `9376A3D5...C9B1`, 6,856 coercions/order SHA `06A41F2D...D964`, 7,398 deep copies, 29 forks/snapshots, 66 registrations, 24,578 requirements, 0 full traversals, 37 exception events SHA `ADD442F5...73B`; 933 specs, 805 DPF specs, 171 data types, type-order SHA `B94BE97C...B381`, contract `15B4C3FD...DAAD`, plugin `9B8D9130...297A`, data catalog `1D20C15D...31D2`, and exact add-on config | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTAS NOT ATTRIBUTED` |
| T04 baseline | Fixed scalar/interval/serialized-DataTree/dynamic/Select/slider/Web/DPF corpus; current `ed41281f`; Python 3.11.6; one built registry; 3 warmups, 7 samples, 100 loops, three isolated processes | Run 1 raw ns `[1011158,978261,1008194,994856,1005167,995410,987541]`, median `995410`, p95 `1011158`, CV `0.010984`, MAD `9757`; Run 2 `[1004730,1001148,1003575,980600,1010465,999271,973042]`, median `1001148`, p95 `1010465`, CV `0.012835`, MAD `3582`; Run 3 `[1010521,1001979,993725,976371,1011866,990899,985713]`, median `993725`, p95 `1011866`, CV `0.012124`, MAD `8254` | Pending | Twelve ordered outputs SHA `AC83D000...FD27`, key/order SHA `745A0B28...9A53`; exact two-error sequence SHA `8B229768...20C7`; deep-copy isolation true; ambiguous DPF dual selector omits `time_scope_mode`; one corpus performs 13 `normalize_properties`, 3 `normalize_property_value`, 3 `default_properties`, 28 base-spec lookups, 12 instance resolutions, 12 dynamic-group resolutions, 77 coercions, 186 deep copies, and 0 validation calls. Process-median `995410 ns`; median p95 `1011158 ns`. | `BASELINE PASS — CANDIDATE PENDING` |
| T04 candidate | Same fixed corpus/interpreter/registry/cache state/warmups/samples/loops/process shape as the T04 baseline | See baseline row; process-median `995410 ns`; median p95 `1011158 ns` | Run 1 raw ns `[983932,990886,994371,984285,974351,985538,968495]`, median `984285`, p95 `994371`, CV `0.008471`, MAD `6601`; Run 2 `[920250,923156,927939,908969,929822,980493,939496]`, median `927939`, p95 `980493`, CV `0.022813`, MAD `7689`; Run 3 `[1046093,985246,1130930,1055302,1044073,975085,991489]`, median `1044073`, p95 `1130930`, CV `0.048750`, MAD `52584` | Exact output/order/error hashes, deep-copy isolation, ambiguous DPF behavior, 13/3/3 API calls, 12 instance resolutions, 12 dynamic-group resolutions, 77 coercions, 186 deep copies, and 0 validation calls match baseline. Base-spec lookups improve from 28 to 16, exactly one per top-level API/error call. Process-median `984285 ns` (`-1.12%`); median p95 `994371 ns` (`-1.66%`). Baseline and candidate were sequential rather than counterbalanced, and the noisier third candidate run remains visible, so timing is not causally attributed. | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, SMALL DELTAS NOT ATTRIBUTED` |
| T05 baseline | Fixed 933-spec default registry plus one custom-workflow item; whole Library/Quick Insert/cache anchors; blank/nonblank/DPF/custom filters; Python 3.11.6; 3 warmups, 7 samples, 20 loops, three isolated processes | Blank: R1 `[266235,205480,250465,225580,272660,208540,218935]`, median `225580`, p95 `272660`; R2 `[278775,204050,217260,255585,211785,236350,225320]`, median `225320`, p95 `278775`; R3 `[208175,209075,230305,204725,207610,223200,203240]`, median `208175`, p95 `230305`. Nonblank: R1 `[1890405,1748580,1799160,1811015,1746310,1716795,1751395]`, median `1751395`, p95 `1890405`; R2 `[1804745,1783965,1753635,1711920,1837490,1691400,1790095]`, median `1783965`, p95 `1837490`; R3 `[1786590,1769340,1881625,1849245,1755505,1743790,1741310]`, median `1769340`, p95 `1881625`. DPF: R1 `[2455200,2500125,2526855,2487800,2449160,2854955,2448060]`, median `2487800`, p95 `2854955`; R2 `[2559965,2497530,2706095,2508545,2450605,2452590,2418800]`, median `2497530`, p95 `2706095`; R3 `[2527510,2448375,2479980,2488025,2484580,2548780,2511550]`, median `2488025`, p95 `2548780`. Custom: R1 `[6036830,6203965,6101190,6030580,6008545,6069645,5967445]`, median `6036830`, p95 `6203965`; R2 `[5828870,6025675,5781460,6220315,5890845,5860305,5767880]`, median `5860305`, p95 `6220315`; R3 `[5903270,5842225,5866405,6226355,5939350,5967740,5825835]`, median `5903270`, p95 `6226355` | Pending | Exact inventory counts: 933 registry/934 combined, 805 DPF, one custom, one nonblank, 84 options, 1,017 grouped, 991 display, zero blank canvas Quick Insert, one queried canvas result, 12 blank connection results. Structural hashes: combined/blank `6B841E97...7D92`, nonblank `D0F09556...FE4C`, DPF `04ADF86A...60FD`, custom `F1047EFF...C326`, tree `29506EEB...1DB3`, grouped/order `D58FB214...4BFE`/`C8798116...7CBA`, display/order `4626B357...419`/`131FFA3A...982C`, options `62A375CA...E1A5`, presenter `F9A6EF56...39B8`; one registry projection, combined projection, category-tree build, category-options build, and custom-workflow read across three cached reads. Process medians: blank `225320`, nonblank `1769340`, DPF `2488025`, custom `5903270` ns; median p95s `272660`, `1881625`, `2706095`, `6220315` ns. | `BASELINE PASS — CANDIDATE PENDING` |
| T05 candidate | Same fixed corpus/configuration/process shape as baseline; timed blank/nonblank/DPF/custom functions are unchanged | See baseline row | Blank: R1 `[211975,356160,269440,378845,230035,259215,228520]`, median `259215`, p95 `378845`; R2 `[217920,300845,235450,205210,210420,207785,225575]`, median `217920`, p95 `300845`; R3 `[230235,214415,241055,224795,209730,231045,208820]`, median `224795`, p95 `241055`. Nonblank: R1 `[1777925,1775495,1742995,1984445,1947225,2093630,2029145]`, median `1947225`, p95 `2093630`; R2 `[1861480,1569470,1584205,1553095,1579205,1548310,1553500]`, median `1569470`, p95 `1861480`; R3 `[3081570,1629425,1617310,1741740,1825390,2124600,1693825]`, median `1741740`, p95 `3081570`. DPF: R1 `[2634240,2769805,2439685,2478690,2435060,2511875,2480030]`, median `2480030`, p95 `2769805`; R2 `[2550140,2777050,2374375,2396645,2937810,2342070,2515520]`, median `2515520`, p95 `2937810`; R3 `[2448495,2365690,2323880,2361650,2312630,2331855,2321505]`, median `2331855`, p95 `2448495`. Custom: R1 `[6188685,6668590,6538400,5953850,6154435,7852155,6181570]`, median `6188685`, p95 `7852155`; R2 `[5654050,5825995,5789995,6025355,6223540,6165705,5661810]`, median `5825995`, p95 `6223540`; R3 `[6250095,5862405,7028350,6270255,7492565,6125810,6721285]`, median `6270255`, p95 `7492565` | Every count/hash/order/cache fact matches baseline exactly, including one category tree/options/registry/combined/custom read across three presenter reads and unchanged Quick Insert payloads. Process-median changes: blank `-0.23%`, nonblank `-1.56%`, DPF `-0.32%`, custom `+4.84%`; median-p95 changes `+10.34%`, `+11.27%`, `+2.35%`, `+20.46%`. The p95 variance triggered the advisory repeat; the timed filter implementation was not edited. | `STRUCTURAL COUNTERS PASS; TIMING REPEAT REQUIRED — NON-COUNTERBALANCED` |
| T05 advisory repeat | Same candidate and measurement shape; repeat taken because the first candidate p95 batch crossed advisory thresholds despite an unchanged timed path | See T05 baseline row | Blank: R1 `[223460,230910,210850,216635,245410,234275,252680]`, median `230910`, p95 `252680`; R2 `[226105,230575,218715,224995,262705,220885,211695]`, median `224995`, p95 `262705`; R3 `[305615,212010,209835,230285,226145,211480,246785]`, median `226145`, p95 `305615`. Nonblank: R1 `[1778245,1917755,1828340,1746675,1717480,1836505,1916330]`, median `1828340`, p95 `1917755`; R2 `[1849135,1900955,1805270,2006230,2310080,2123520,1889590]`, median `1900955`, p95 `2310080`; R3 `[1843630,1769230,1740435,1842165,1724565,1748910,1720740]`, median `1748910`, p95 `1843630`. DPF: R1 `[2986245,2910925,2627325,2565740,3158035,2619230,3275685]`, median `2910925`, p95 `3275685`; R2 `[2627865,2634045,2589220,2600735,2580800,2661790,2524405]`, median `2600735`, p95 `2661790`; R3 `[2493805,2440900,2892665,2879885,2760280,2533850,2515095]`, median `2533850`, p95 `2892665`. Custom: R1 `[7036425,7021895,8234900,7744065,6331980,7795125,7156650]`, median `7156650`, p95 `8234900`; R2 `[6135645,6465550,6095810,6418525,6146600,6640495,6282035]`, median `6282035`, p95 `6640495`; R3 `[6389305,7278500,6351240,6153715,5886700,6237980,5985350]`, median `6237980`, p95 `7278500` | Structural facts again match exactly. Repeat process-median changes versus baseline: blank `+0.37%`, nonblank `+3.33%`, DPF `+4.53%`, custom `+6.42%`; repeat median-p95 changes `-3.65%`, `+1.92%`, `+6.89%`, custom `+17.00%`. High within-run CV/outliers remain visible, and the timed filter function is byte-unchanged; sequential non-counterbalanced timing is therefore not attributed to the ownership refactor. | `STRUCTURAL COUNTERS PASS; TIMING INCONCLUSIVE — NON-COUNTERBALANCED, NO TIMING-ONLY ROLLBACK` |
| T06–T12 | Pending per task | Pending | Pending | Pending | Pending |
| T14–T25 | Baseline locked at T13/T18/QML gates | Pending | Pending | Pending | Pending |

## Review Ledger

| Review | Scope | Reviewer | Findings | Resolution | Verdict |
| --- | --- | --- | --- | --- | --- |
| T00 architecture/integration re-review | Plan fidelity, checkpoint status, ignored ledger, protected/index state | `history_intent_audit` | Ignored QA ledger needed exact force-stage rule; validator rejected clean checkpoints and allowed incomplete accepted rows; T00 overclaimed performance readiness | Added exact privacy-reviewed force-stage command without changing `.gitignore`; validator now allows zero/one active task and requires complete accepted evidence; T00 wording now says task baseline is required before editing | `CLEAR` |
| T00 performance re-review | Program A fixture/statistics coverage and stale/fresh claims | `core_ownership_audit` | `timeit` hid raw repeats; T02–T12 contracts/counters were incomplete; T08–T10 were incorrectly aggregated | Demoted `timeit` to syntax smokes; added stdlib raw-sample statistics contract and exact T01–T12 fixtures/tests/counters; split T08, T09, and T10; retained no-fresh-timing wording | `CLEAR` |
| T00 ledger/test re-review | Migration schema, status synchronization, inventories and shell ordering | `test_verification_audit` | Migration rows lacked owning task/kind/pending state and required-field validation; plan/ledger statuses could drift; shell hash order was implicit | Added 13-field schema, both-program `pending_migration`, kind/phase/evidence rules and negative tests; synchronized top statuses; defined `tuple(load_target_registry())` declaration order | `CLEAR` |
| T01 architecture review | Sole add-on requested-state and publication authority | Architecture reviewer | P1: candidate and final registries could agree with each other while both disagreed with the requested add-on state | Resolved: pass the requested boolean into the guarded transaction; verify candidate before compatibility and final before fingerprint/compatibility/publication; matching-wrong and final-only mismatch tests prove zero side effects; re-review found no remaining issue | `CLEAR` |
| T01 correctness/security/no-lost-tests review | T01 production, trust ordering, direct tests, and nine migration rows | Correctness reviewer | No remaining finding after requested-state remediation | Confirmed candidate/final fail-closed checks, unchanged publication/persistence/rollback ordering, direct runtime-owner coverage, and final evidence for all nine migrated IDs | `CLEAR` |
| T01 performance review | T01 transaction probe and attribution | Performance reviewer | Sequential baseline/candidate samples were not counterbalanced and were mislabeled as formal neutral timing acceptance | Resolved: preserve raw `+1.53%`/`+2.38%` context, narrow structural claims to measured counters, record two requested-state checks through direct proof, and mark timing inconclusive without new harness machinery; re-review found no remaining issue | `CLEAR` |
| T02 architecture review | Contribution owners, startup imports, and direct publication paths | Architecture reviewer | Public/built-in imports became eager; `function_bundle.py` retained reserved/private registration decisions; live add-on dispatch copied ignored result lists | Resolved: bootstrap imports public and built-in owners only inside construction calls; built-in, public, and trusted add-on publishers make their own permission/provenance/publication decisions; live add-on dispatch is a direct `None`-returning loop; architecture and lazy-import guards added; re-review found no remaining issue | `CLEAR` |
| T02 correctness/security/no-lost-tests review | Trust validation, direct-owner tests, and exact migrations | Correctness reviewer | One parametrized migration row hid five separately collected source-validation cases | Resolved: five stable descriptive replacement IDs and five exact old `sources0`–`sources4` rows bring T02 to 17 closed migration rows; trust-boundary validation and all-or-none publication remain in their direct owners; re-review found no remaining issue | `CLEAR` |
| T02 performance review | Startup import work, add-on dispatch allocations, and timing attribution | Performance reviewer | Eager startup imported the heavier discovery route; live add-on dispatch built an unused aggregate list; allocation parity was not measured | Resolved: restored lazy construction imports and deleted the unused aggregate/copy path; retained the recorded `+0.73%`/`-0.07%`/`+2.69%` timing context as non-counterbalanced and unattributed, with no allocation-parity claim; re-review found no remaining issue | `CLEAR` |
| T03 architecture review | Validation/resolution ownership and dependency direction | Architecture reviewer | `spec_validation.py` lazily imported registry-owned resolution, creating a real registry/validation cycle; four port-policy constants remained duplicated after the owner move | Resolved: added cycle-free `instance_resolution.py` as the sole port-policy/instance/dynamic resolution owner, removed duplicated constants from specification validation, updated every registry/graph/execution/UI/test caller directly without aliases, and added import/absence guards; re-review found no remaining issue | `CLEAR` |
| T03 correctness/security/no-lost-tests review | Staged-catalog validation, error parity, and migrated resolver coverage | Correctness reviewer | The migrated direct rejection matrix no longer proved registry-state atomicity | Resolved: retained the complete direct resolver rejection matrix and added registry integration proof that entries, catalog snapshot/fingerprint, plugin fingerprint, and contract fingerprint remain unchanged; four migration rows resolve to five final IDs; re-review found no remaining issue | `CLEAR` |
| T03 performance review | Validator/coercion/copy/catalog-pass counters and full-registry construction | Performance reviewer | No remaining finding after cycle and policy cleanup | Confirmed exact structural parity for validation/coercion order and counts, deep copies, catalog forks/registrations/requirements/traversals, exception sequence, registry inventory/order/fingerprints, and add-on config; retained sequential `+0.52%` median and `+2.16%` median-p95 timing as inconclusive/unattributed; re-review found no remaining issue | `CLEAR` |
| T04 architecture review | Normalization policy ownership and registry API boundary | Architecture reviewer | No remaining finding | Confirmed generic traversal plus Select/Number Slider/Web/DPF policy live only in `property_normalization.py`; registry contains no built-in imports or DPF/type-specific branches and retains only its three intentional catalog-aware APIs; no callback/plugin framework or T05 work was introduced | `CLEAR` |
| T04 correctness/security/no-lost-tests review | Defaults/carriers/dynamic ports/Web/DPF behavior, graph mutation path, and five migration rows | Correctness reviewer | No remaining finding | Confirmed exact output/order/error hashes, deep-copy isolation, typed/interval/tree and dynamic behavior, Web sanitization/persistence toggle, DPF single/dual-selector semantics, graph mutation route, and five rows resolving to six final replacement IDs | `CLEAR` |
| T04 performance review | Registry lookup, resolution/traversal/coercion/copy/validation counters and timing attribution | Performance reviewer | No remaining finding | Confirmed identical resolution/dynamic/coercion/deep-copy/validation counts with base-spec lookups reduced from 28 to 16; retained sequential `-1.12%` median and `-1.66%` median-p95 timing as inconclusive/unattributed | `CLEAR` |
| T05 architecture review | Registry query deletion and direct Library projection/category ownership | Architecture reviewer | No remaining finding | Confirmed no production caller remained beyond the presenter dependency replaced in this task; registry filter/category APIs and private helpers are absent, the presenter has no registry-category cache, and the existing Library projection derives filters/options/tree from one combined registry/custom-workflow source without a replacement API | `CLEAR` |
| T05 correctness/security/no-lost-tests review | Library/Quick Insert/QML payloads, DPF taxonomy, custom workflows, accepted unions, hidden ports, and test migrations | Correctness reviewer | No remaining finding | Confirmed exact item/order/category/tree/options/Quick Insert/presenter hashes, one cached tree/options build, DPF and custom-workflow discoverability, maintained flat-category behavior, accepted-type union/hidden-port coverage, 19 final migration rows, 22 replacement IDs, and one explicit obsolete disposition | `CLEAR` |
| T05 performance review | Library query timings and presenter projection/cache construction counts | Performance reviewer | No correctness or structural finding; candidate timing remained noisy on an unchanged timed filter path | Confirmed exact structural/cache parity; recorded initial threshold-crossing raw samples and the advisory repeat; retained non-counterbalanced repeat deltas without timing-only rollback or causal attribution | `CLEAR` |
| Program A architecture/ownership | T01–T12 | Pending | Pending | Pending | Pending |
| Program A correctness/security/no-lost-tests | T01–T12 | Pending | Pending | Pending | Pending |
| Program A performance causality | T01–T12 | Pending | Pending | Pending | Pending |
| Program B architecture/ownership | T14–T25 | Pending | Pending | Pending | Pending |
| Program B correctness/security/no-lost-tests | T14–T25 | Pending | Pending | Pending | Pending |
| Program B performance causality | T14–T25 | Pending | Pending | Pending | Pending |

## T00 Evidence

| Command / evidence | Result |
| --- | --- |
| Starting Git/ref/status/protected hashes | `PASS`; recorded above |
| 17 starting Python-owner imports | `PASS` |
| Program A focused `--collect-only -q -n 0` | `PASS`; 916 IDs across 32 modules; SHA-256 `E1101196...BB0E` reproduced after remediation |
| Program B focused `--collect-only -q -n 0` | `PASS`; 696 IDs across 35 modules; SHA-256 `89FABCC1...E060` reproduced after remediation |
| QML selector and shell target inventory | `PASS`; 62 affected selectors SHA-256 `ADE8746F...608B`; 51 declaration-ordered shell targets SHA-256 `2DACD2F8...8EC0` reproduced |
| Ledger validator | `PASS`; 12 tests including missing-field, invalid-kind/phase, illegal-pending, final-evidence, accepted-task, checkpoint, and status-drift negatives |
| Shell catalog guards | `PASS`; 7 exact non-lifecycle guards |
| `full --dry-run` | `PASS`; all seven phases rendered; `qmltestrunner.exe` unavailable notice retained |
| Agent maps | `PASS` |
| Traceability | `PASS` |
| Markdown links | `PASS` |
| Route/source-test/QML generator checks | `PASS`; source/test index regenerated only because the T00 validator is a new indexed test; route and QML outputs unchanged |
| Diff hygiene and protected-path comparison | `PASS`; working and cached diff checks passed; nothing staged; removing only the T00 index row reproduces starting index SHA-256 `43BFA388...D431`; the other two protected hashes are unchanged |
| Ignored QA ledger | File remains unstaged/ignored as required during T00 writing; acceptance must privacy-review and force-stage only its exact path with the locked command |

## Final Acceptance

| Gate | Command / evidence | Result |
| --- | --- | --- |
| Ledger completeness | `tests/test_corex_ownership_refactor_ledger.py` | Pending |
| Focused task suites | Recorded per task above | Pending |
| Agent maps | `.\venv\Scripts\python.exe .\scripts\check_agent_maps.py` | Pending |
| Traceability | `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | Pending |
| Markdown links | `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | Pending |
| Generated navigation | Three generator `--check` commands from the plan | Pending |
| Full verification | `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --summarize-output` | Pending |
| Diff/privacy hygiene | Working/cached diff checks plus protected-path audit | Pending |
| Publication | Local commit series only; no push | Pending |
