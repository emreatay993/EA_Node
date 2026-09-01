# COREX Maintainability And Ownership Refactor QA Matrix

Status: `IN PROGRESS`

This is the single task, test-migration, performance, and review ledger for
`docs/PLAN_COREX_MAINTAINABILITY_OWNERSHIP_REFACTOR.md`.

## Locked Baseline

| Fact | Value |
| --- | --- |
| Starting branch | `main` |
| Starting commit | `5a4ae4b8` |
| Upstream at start | `origin/main` at `5a4ae4b8` |
| Publication | Local commits only; no push |
| Protected modified path | `docs/specs/INDEX.md` |
| Protected untracked path | `docs/PLAN_COREX_Physical_Simulation_Backend.md` |
| Protected untracked path | `scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv` |
| Performance policy | Advisory matched evidence; no timing-only rollback |

## Compaction Recovery Checklist

Before continuing after compaction, read these in order:

1. `AGENTS.md`
2. `docs/PLAN_COREX_MAINTAINABILITY_OWNERSHIP_REFACTOR.md`
3. this QA matrix
4. `git status --short --branch`
5. `git log -1 --oneline`
6. the next `IN PROGRESS` or `NOT STARTED` task row below

Do not edit until the protected dirty paths and last accepted commit are
reconciled with this ledger.

## Task Ledger

| Task | Status | Writer | Conservative write scope | Focused evidence | Performance evidence | Independent review | Accepted commit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T00 Plan and baseline | `ACCEPTED` | Orchestrator | Plan, this ledger, exact spec-index additions | Full dry-run, traceability, links, diff hygiene, and 582-test affected inventory passed; `qmltestrunner.exe` unavailable | Fast baseline: 4,543 passed, 2 skipped, 18 existing warnings; logs under `artifacts/verification_logs/20260901_042328/` | Two delegated read-only baseline verifiers returned no findings | `bc4233f6` |
| T01 Package policy | `ACCEPTED` | `t01_package_writer` | Nodes package schema, add-on contracts, direct tests/maps | Final focused acceptance: 235 tests and 90 subtests passed; Ruff, compile, maps, traceability, links, and diff hygiene passed | Discovery/import/export medians changed `3.030/8.717/7.220 ms` to `2.483/8.333/6.621 ms`; no added traversal and deterministic bytes retained | `t01_package_reviewer`: initial two P1/two P2/one P3 findings fixed; re-review `CLEAR` | `fa3b8ff9` |
| T02 Runtime contracts | `ACCEPTED` | `t02_runtime_writer` | Common artifact grammar, defining runtime modules, direct imports/tests/maps | Final combined acceptance: 646 tests and 209 subtests passed with one existing PyArrow warning; Ruff, compile, maps, traceability, links, and diff hygiene passed | Exact payload hashes, round trips, copy guards, and allocation peaks unchanged; confirmed micro-regressions of `+2.66 us` ImageValue and `+0.73 us` durable decode are advisory | `t02_runtime_reviewer`: residual barrels and missing exact owner/export guards fixed; source/test re-review `CLEAR` | `e402f973` |
| T03 UI projections | `READY TO COMMIT` | `t03_projection_writer` | Library, Inspector, Quick Insert, direct tests/maps | Final combined run: 309 tests and 77 subtests passed; one unrelated workspace-tab shell timeout under xdist passed immediately in exact serial rerun; Ruff, compile, maps, traceability, links, diagrams, and diff hygiene passed | Exact output counts/order/hashes retained; display and Quick Insert neutral; shared grouped/display projection materially faster | `t03_projection_reviewer`: dependency inversion fixed; source/test re-review `CLEAR` | Pending |
| T04 Graph host owner | `NOT STARTED` | Pending | Graph host presenter, shell forwarders, direct tests/maps | Pending | Pending | Pending | Pending |
| T05 Tabular query | `NOT STARTED` | Pending | Tabular service/backends/query, direct tests/maps | Pending | Pending | Pending | Pending |
| T06 Video playback | `NOT STARTED` | Pending | Video QML/state, direct tests/maps | Pending | Pending | Pending | Pending |
| T07 Residual tests | `NOT STARTED` | Pending | Ledger-proven residual tests/catalogs/maps | Pending | None for product runtime | Pending | Pending or accepted no-op |
| T08 Closeout | `NOT STARTED` | Orchestrator | QA status, shared maps/indexes/guards | Pending | Consolidated review pending | Pending | Pending |

## Test Migration Ledger

Allowed dispositions are `retained`, `moved_to_owner`,
`replaced_by_owner_test`, `replaced_by_qml_quicktest`, `merged_equivalent`, and
`deleted_redundant`.

| Task | Old node ID | Behavior | Current owner | Disposition | Replacement node ID | Proving command | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | `tests/test_plugin_loader.py::test_addon_registration_lookup_requires_canonical_addon_id` | Canonical add-on ID lookup | Add-on catalog | `moved_to_owner` | `tests/test_addon_catalog.py::test_addon_registration_lookup_requires_canonical_addon_id` | `.\venv\Scripts\python.exe -m pytest tests/test_addon_catalog.py -q` | `PASS` |
| T01 | `tests/test_plugin_loader.py::test_discover_addon_records_reports_generic_manifest_and_state` | Add-on manifest/state projection | Add-on catalog | `moved_to_owner` | `tests/test_addon_catalog.py::test_discover_addon_records_reports_generic_manifest_and_state` | `.\venv\Scripts\python.exe -m pytest tests/test_addon_catalog.py -q` | `PASS` |
| T01 | `tests/test_plugin_loader.py::test_plugin_loader_addon_record_discovery_delegates_to_addon_catalog` | Forwarding-only loader alias | Removed forwarding path | `deleted_redundant` | Add-on owner tests above plus architecture absence guard | T01 focused package/add-on/architecture suite | `PASS` |
| T02 | All affected runtime/artifact/worker test node IDs | Runtime carrier, codec, durable, and artifact grammar behavior | Defining runtime/common owners | `retained` | Same node IDs with direct defining-module imports; exact owner/export/union absence guards added | T02 focused runtime, persistence, worker, UI caller, and architecture suites | `PASS` |
| T03 | 29 node IDs from `tests/test_window_library_inspector.py` | Library/Inspector/Quick Insert projection | Three defining projection owners | `moved_to_owner` | 30 replacement node IDs across `test_library_projection.py`, `test_inspector_projection.py`, and `test_quick_insert_projection.py`; one combined test split in two | `.\venv\Scripts\python.exe -m pytest tests/test_library_projection.py tests/test_inspector_projection.py tests/test_quick_insert_projection.py -q` | `PASS` |
| T04 | Pending inventory | Graph cursor/style action routing | Shell forwarding chain | Pending | Pending | Pending | `NOT STARTED` |
| T05 | Pending inventory | Tabular source/query/cache behavior | Mixed loader service | Pending | Pending | Pending | `NOT STARTED` |
| T06 | Pending inventory | Inline/fullscreen video playback | Two QML renderers | Pending | Pending | Pending | `NOT STARTED` |
| T07 | Pending residual audit | Shell versus direct owner behavior | Shell tests | Pending | Pending | Pending | `NOT STARTED` |

### T03 Exact Node-ID Migration

All rows use disposition `moved_to_owner`; the final combined case has two
replacement node IDs.

| Old node ID under `tests/test_window_library_inspector.py` | Replacement node ID |
| --- | --- |
| `WindowLibraryInspectorUsageRankingTests::test_recent_usage_ranks_by_frequency_then_recency_and_ignores_unavailable_items` | `tests/test_library_projection.py::LibraryProjectionUsageRankingTests::test_recent_usage_ranks_by_frequency_then_recency_and_ignores_unavailable_items` |
| `WindowLibraryInspectorQuickInsertTests::test_canvas_quick_insert_blank_query_returns_no_results` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_canvas_quick_insert_blank_query_returns_no_results` |
| `WindowLibraryInspectorQuickInsertTests::test_canvas_quick_insert_non_empty_query_returns_matches` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_canvas_quick_insert_non_empty_query_returns_matches` |
| `WindowLibraryInspectorQuickInsertTests::test_connection_quick_insert_blank_query_keeps_compatible_matches` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_connection_quick_insert_blank_query_keeps_compatible_matches` |
| `WindowLibraryInspectorQuickInsertTests::test_connection_quick_insert_filters_data_ports_by_type` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_connection_quick_insert_filters_data_ports_by_type` |
| `WindowLibraryInspectorQuickInsertTests::test_connection_quick_insert_treats_primary_and_accepted_types_as_union` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_connection_quick_insert_treats_primary_and_accepted_types_as_union` |
| `WindowLibraryInspectorQuickInsertTests::test_connection_quick_insert_excludes_hidden_ports_in_both_directions` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_connection_quick_insert_excludes_hidden_ports_in_both_directions` |
| `WindowLibraryInspectorQuickInsertTests::test_connection_quick_insert_retains_runtime_check_matches_in_both_directions` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_connection_quick_insert_retains_runtime_check_matches_in_both_directions` |
| `WindowLibraryInspectorQuickInsertTests::test_connection_quick_insert_neutral_flow_source_returns_flowchart_nodes` | `tests/test_quick_insert_projection.py::QuickInsertProjectionTests::test_connection_quick_insert_neutral_flow_source_returns_flowchart_nodes` |
| `WindowLibraryInspectorQuickInsertTests::test_registry_library_items_keep_declared_data_port_order` | `tests/test_library_projection.py::LibraryProjectionRegistryTests::test_registry_library_items_keep_declared_data_port_order` |
| `WindowLibraryInspectorQuickInsertTests::test_registry_browser_payload_projects_help_metadata_and_real_port_labels` | `tests/test_library_projection.py::LibraryProjectionRegistryTests::test_registry_browser_payload_projects_help_metadata_and_real_port_labels` |
| `WindowLibraryInspectorFolderExplorerTests::test_folder_explorer_is_discoverable_in_input_output_library_group` | `tests/test_library_projection.py::LibraryProjectionFolderExplorerTests::test_folder_explorer_is_discoverable_in_input_output_library_group` |
| `WindowLibraryInspectorFolderExplorerTests::test_folder_explorer_current_path_property_is_folder_path_editor_payload` | `tests/test_inspector_projection.py::InspectorProjectionFolderExplorerTests::test_folder_explorer_current_path_property_is_folder_path_editor_payload` |
| `WindowLibraryInspectorNodeLinkTests::test_selected_node_link_items_preserve_order_and_resolve_target_metadata` | `tests/test_inspector_projection.py::InspectorProjectionNodeLinkTests::test_selected_node_link_items_preserve_order_and_resolve_target_metadata` |
| `WindowLibraryInspectorTabularDataInputTests::test_tabular_data_input_library_item_is_availability_gated` | `tests/test_library_projection.py::LibraryProjectionTabularDataInputTests::test_tabular_data_input_library_item_is_availability_gated` |
| `WindowLibraryInspectorTabularDataInputTests::test_tabular_data_input_property_items_use_file_path_and_semantic_groups` | `tests/test_inspector_projection.py::InspectorProjectionTabularDataInputTests::test_tabular_data_input_property_items_use_file_path_and_semantic_groups` |
| `WindowLibraryInspectorTabularDataInputTests::test_tabular_selection_items_come_from_property_edit_adapter` | `tests/test_inspector_projection.py::InspectorProjectionTabularDataInputTests::test_tabular_selection_items_come_from_property_edit_adapter` |
| `WindowLibraryInspectorNestedCategoryLibraryPayloadTests::test_registry_items_nested_category_library_payload_projects_path_metadata` | `tests/test_library_projection.py::LibraryProjectionNestedCategoryPayloadTests::test_registry_items_nested_category_library_payload_projects_path_metadata` |
| `WindowLibraryInspectorNestedCategoryLibraryPayloadTests::test_grouped_rows_nested_category_library_payload_flattens_trie_with_metadata` | `tests/test_library_projection.py::LibraryProjectionNestedCategoryPayloadTests::test_grouped_rows_nested_category_library_payload_flattens_trie_with_metadata` |
| `WindowLibraryInspectorNestedCategoryLibraryPayloadTests::test_display_rows_icon_mode_groups_passive_flowchart_visuals_into_tile_rows` | `tests/test_library_projection.py::LibraryProjectionNestedCategoryPayloadTests::test_display_rows_icon_mode_groups_passive_flowchart_visuals_into_tile_rows` |
| `WindowLibraryInspectorNestedCategoryLibraryPayloadTests::test_flowchart_multi_document_library_visual_uses_metric_contract_aspect_ratio` | `tests/test_library_projection.py::LibraryProjectionNestedCategoryPayloadTests::test_flowchart_multi_document_library_visual_uses_metric_contract_aspect_ratio` |
| `WindowLibraryInspectorNestedCategoryLibraryPayloadTests::test_filters_and_options_nested_category_library_payload_are_path_backed` | `tests/test_library_projection.py::LibraryProjectionNestedCategoryPayloadTests::test_filters_and_options_nested_category_library_payload_are_path_backed` |
| `WindowLibraryInspectorNestedCategoryLibraryPayloadTests::test_custom_workflows_nested_category_library_payload_use_single_segment_path` | `tests/test_library_projection.py::LibraryProjectionNestedCategoryPayloadTests::test_custom_workflows_nested_category_library_payload_use_single_segment_path` |
| `WindowLibraryInspectorNestedCategoryLibraryPayloadTests::test_quick_insert_and_header_nested_category_library_payload_show_full_paths` | `tests/test_quick_insert_projection.py::QuickInsertProjectionCategoryTests::test_quick_insert_nested_category_library_payload_shows_full_path`; `tests/test_inspector_projection.py::InspectorProjectionHeaderTests::test_header_nested_category_library_payload_shows_full_path` |
| `WindowLibraryInspectorPropertyGroupTests::test_interval_editor_input_keeps_declared_endpoint_order` | `tests/test_inspector_projection.py::InspectorProjectionPropertyGroupTests::test_interval_editor_input_keeps_declared_endpoint_order` |
| `WindowLibraryInspectorPropertyGroupTests::test_property_items_reuse_interval_and_condition_presentation` | `tests/test_inspector_projection.py::InspectorProjectionPropertyGroupTests::test_property_items_reuse_interval_and_condition_presentation` |
| `WindowLibraryInspectorPropertyGroupTests::test_property_items_emit_group_with_fallback_when_unset` | `tests/test_inspector_projection.py::InspectorProjectionPropertyGroupTests::test_property_items_emit_group_with_fallback_when_unset` |
| `WindowLibraryInspectorPropertyGroupTests::test_property_items_flag_dirty_when_value_differs_from_default` | `tests/test_inspector_projection.py::InspectorProjectionPropertyGroupTests::test_property_items_flag_dirty_when_value_differs_from_default` |
| `WindowLibraryInspectorPropertyGroupTests::test_web_page_viewer_start_location_uses_source_storage_picker` | `tests/test_inspector_projection.py::InspectorProjectionPropertyGroupTests::test_web_page_viewer_start_location_uses_source_storage_picker` |

## Performance Evidence

| Task | Metric and fixture | Baseline | Candidate | Repeat / attribution | Verdict |
| --- | --- | --- | --- | --- | --- |
| T01 | Four-member schema-2 fixture; discovery/import/export | `3.030 / 8.717 / 7.220 ms` medians | `2.483 / 8.333 / 6.621 ms` medians | Same 3 warmups + 7 measured runs; filesystem and ZIP call counts did not increase; all archive hashes identical | `NEUTRAL-TO-BETTER` (supportive, not a speedup claim) |
| T02 | Fresh import; scalar/DataTree/Image/artifact codecs; durable validate/to/from | `47.011 ms`; `28.291/135.737/51.217/130.216 us`; `19.209/3.988/10.420 us` | `47.184 ms`; `28.392/134.710/53.877/132.308 us`; `19.184/3.939/11.152 us` | Second matched batch confirmed only Image `+5.2%` (`+2.66 us`) and durable decode `+7.0%` (`+0.73 us`); hashes, copies, allocations identical | `ADVISORY MICRO-REGRESSION`; below material threshold |
| T03 | Default 933-spec registry; display/grouped projection and Quick Insert | Exact counts/order hashes pinned; display ~25-29 ms, paired projection ~49-54 ms, Quick Insert ~1.8/27 ms | Second interleaved batch: display text `-1.43%`; icon supportive/variable; paired text/icon `-52.31%/-47.04%`; Quick Insert within `+0.97%/+0.22%` | Live display-only path builds one tree and zero grouped rows; later grouped read reuses the tree; no payload/hash drift | `NEUTRAL-TO-BETTER` |
| T04 | Shell create and graph action | Pending | Pending | Pending | Pending |
| T05 | 400 MB Tabular cold/warm queries | Pending | Pending | Pending | Pending |
| T06 | Animated media and decoder ownership | Pending | Pending | Pending | Pending |

## T00 Baseline Evidence

| Command / evidence | Result |
| --- | --- |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run` | `PASS`; command graph rendered, with `qmltestrunner.exe` reported unavailable in this environment |
| Affected Python suites, serial `--collect-only` | `PASS`; 582 tests collected across 27 modules, no collection errors |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast --summarize-output` | `PASS`; parallel 4,318 passed/2 skipped, serial 225 passed, 18 existing warnings |
| `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | `PASS` |
| `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | `PASS` |
| `git diff --check` | `PASS` |
| Protected-path hash audit | `PASS`; all three pre-existing dirty paths retained their starting hashes |

## Review Ledger

| Review | Scope | Reviewer | Findings | Resolution | Verdict |
| --- | --- | --- | --- | --- | --- |
| Per-task reviews | T01 | `t01_package_reviewer` | Numeric loose-plugin generation rejection; delayed cumulative-byte checks; stale add-on test ownership; missing maps; dead imports | Production/test findings fixed by original writer; maps integrated by orchestrator | `CLEAR` |
| Per-task reviews | T02 | `t02_runtime_reviewer` | Stale docs; `value_refs` forwarding tabular/array carriers; obsolete execution codec; missing exact export/union guards | Source/test findings fixed by original writer; docs/maps integrated by orchestrator | `CLEAR` |
| Per-task reviews | T03 | `t03_projection_reviewer` | Live docs named deleted owner; Library depended on Quick Insert for projected-port parsing | Helper moved to Library; dependency/absence guards added; docs/maps integrated by orchestrator | `CLEAR` |
| Architecture/ownership closeout | Whole series | Pending | Pending | Pending | Pending |
| Correctness/security/no-lost-tests closeout | Whole series | Pending | Pending | Pending | Pending |
| Performance-evidence closeout | Whole series | Pending | Pending | Pending | Pending |

## Final Acceptance

| Gate | Command / evidence | Result |
| --- | --- | --- |
| Focused task suites | Recorded per task | Pending |
| Agent maps | `.\venv\Scripts\python.exe .\scripts\check_agent_maps.py` | Pending |
| Traceability | `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | Pending |
| Markdown links | `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | Pending |
| Full verification | `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --summarize-output` | Pending |
| Diff hygiene | `git diff --check` and cached-diff audit | Pending |
| Publication | Local commit series only | Pending |
