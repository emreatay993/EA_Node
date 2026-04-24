# Persistence Requirements

## File Format
- `REQ-PERSIST-001`: Canonical project format shall be `.sfe` (versioned JSON).
- `REQ-PERSIST-002`: Document shall include schema version, project metadata, workspaces, views, nodes, and edges.
- `REQ-PERSIST-003`: Serialization shall be deterministic (stable ordering) for diffability.

## Current Schema Normalization
- `REQ-PERSIST-004`: Serializer shall validate ordinary project loads against the current `.sfe` schema version and reject pre-current documents that need offline conversion.
- `REQ-PERSIST-005`: Load shall normalize the current-schema in-memory document before model construction.

## Session Persistence
- `REQ-PERSIST-006`: Last session shall persist workspace/view state across restarts.
- `REQ-PERSIST-007`: Metadata schema shall persist normalized UI state and workflow settings (`metadata.ui`, `metadata.workflow_settings`) for current-schema documents.
- `REQ-PERSIST-009`: Current-schema codecs shall persist normalized subnode hierarchy view state (`ViewState.scope_path`) and project-local custom workflow definitions (`metadata.custom_workflows`).
- `REQ-PERSIST-010`: Custom workflow snapshot interchange shall use a versioned `.eawf` JSON file format that stores exactly one normalized custom workflow definition.
- `REQ-PERSIST-011`: app-wide graphics preferences, including graphics performance mode plus shell-theme and graph-theme state, shall persist in a versioned app-preferences JSON document under `user_data_dir()` and shall remain separate from `.sfe` project metadata and `last_session.json`.
- `REQ-PERSIST-012`: graph-theme state shall be stored only under `graphics.graph_theme = {follow_shell_theme, selected_theme_id, custom_themes}` with custom graph themes serialized inline in app preferences rather than external files.
- `REQ-PERSIST-013`: `.sfe` project documents shall persist passive-node visual metadata, passive media properties, `flow` edge labels/styles, and project-local passive style preset libraries under normalized project metadata.
- `REQ-PERSIST-014`: `.sfe` project documents shall persist authored comment backdrop title/body/collapsed state and geometry through the normal node document path, but shall not persist derived membership or containment metadata; load shall recompute ownership from geometry.
- `REQ-PERSIST-015`: `.sfe` shall remain the canonical saved project file while project-managed data lives in a sibling `<project-stem>.data/` tree containing managed `assets/`, generated `artifacts/`, and hidden `.staging/` scratch data.
- `REQ-PERSIST-016`: managed-file state shall remain additive under `metadata.artifact_store`, with managed/staged entry maps and optional staging-root hints; managed refs persist as `artifact://<artifact_id>` strings and staged refs as `artifact-stage://<artifact_id>` strings inside ordinary project/node fields.
- `REQ-PERSIST-017`: managed imports and stored outputs shall stage first; explicit Save shall promote only still-referenced staged items, rewrite promoted refs to managed refs, replace current managed copies in place, and prune orphaned permanent managed files.
- `REQ-PERSIST-018`: Save As shall always write a new `.sfe` plus sibling `.data/` tree according to the user-selected copy mode, defaulting to a self-contained copy of currently referenced managed files while excluding staged scratch data.
- `REQ-PERSIST-019`: autosave/session recovery may preserve staged metadata and offer crash-only scratch recovery, while clean close without save discards staged scratch data and its autosave snapshot.
- `REQ-PERSIST-020`: cross-process viewer authored state shall persist only stable node properties, cached summary or proxy metadata, and result/model path selections in `.sfe`; session-scoped temp transport bundles, bundle roots, transport revisions, live-ready state, runtime handle IDs, worker viewer-session caches, and repo-local smoke fixtures under `tests/ansys_dpf_core/example_outputs/` (`.rst` / `.rth`) remain runtime or test inputs rather than serialized project artifacts.
- `REQ-PERSIST-021`: `.sfe` project documents and restore paths shall persist `NodeInstance.locked_ports` plus `ViewState.hide_locked_ports` / `hide_optional_ports`, preserve one-way auto-lock outcomes and authored manual overrides across save/load and workspace duplication, and keep the decluttering flags view-local rather than rewriting node data.
- `REQ-PERSIST-022`: title-icon persistence boundaries shall stay explicit: derived live `icon_source` values shall not serialize into `.sfe` project files, while `graphics.typography.graph_node_icon_pixel_size_override` persists only in the app-preferences document as a nullable app-global integer whose `null` mode follows `graph_label_pixel_size` and whose non-null values clamp to `8..50`.
- `REQ-PERSIST-023`: app preferences and restore paths shall persist add-on enabled-state plus pending-restart intent by add-on id, and `.sfe` documents shall retain enough unavailable-session node metadata to reopen missing add-on nodes as locked unavailable-add-on projections and rebind them when the add-on returns without widening projection payloads into editable live schema.

## Module Decomposition
- `REQ-PERSIST-008`: Persistence internals shall be split into project codec (`ProjectData` <-> JSON document), current-schema validation/normalization, and session/autosave storage service.

## Acceptance
- `AC-REQ-PERSIST-001-01`: Save/load round trip preserves ids, wiring, properties, active workspace, and active view.
- `AC-REQ-PERSIST-004-01`: Current-schema documents load deterministically, while pre-current schema documents are rejected with a clear unsupported-version error.
- `AC-REQ-PERSIST-006-01`: Restart restores previous session when available.
- `AC-REQ-PERSIST-007-01`: Current-schema project documents load with normalized metadata defaults.
- `AC-REQ-PERSIST-009-01`: Save/load round trips preserve nested scope paths and normalized custom workflow metadata, including snapshot fragments.
- `AC-REQ-PERSIST-010-01`: `.eawf` export/import round trips preserve custom workflow snapshot fidelity across projects.
- `AC-REQ-PERSIST-011-01`: app-preferences round-trip preserves graphics performance mode, shell-theme, and graph-theme settings and does not serialize them into `.sfe` project metadata or `last_session.json`.
- `AC-REQ-PERSIST-012-01`: v1 app-preferences documents migrate to v2 with a default `graphics.graph_theme` payload, and persisted custom graph themes round-trip inline under app preferences.
- `AC-REQ-PERSIST-013-01`: passive-only workspaces round-trip authored node sizes/colors, media source properties, `flow` edge labels/styles, and `metadata.ui.passive_style_presets` without losing fidelity.
- `AC-REQ-PERSIST-014-01`: serializer regressions confirm comment backdrop save/load strips runtime membership fields and rebuilds ownership from geometry without losing authored backdrop state.
- `AC-REQ-PERSIST-015-01`: artifact-store and serializer round-trip regressions keep `.sfe` as the canonical file while saved projects resolve the sibling `.data` layout predictably.
- `AC-REQ-PERSIST-016-01`: artifact-store and resolver regressions preserve additive `metadata.artifact_store` metadata plus `artifact://...` / `artifact-stage://...` string refs without migrating them into a separate persistence format.
- `AC-REQ-PERSIST-017-01`: save/promotion regressions confirm referenced staged items become managed entries, stale staged scratch is dropped, and orphan managed files are pruned.
- `AC-REQ-PERSIST-018-01`: Save As regressions confirm the default self-contained copy preserves referenced managed files, strips staged scratch from the destination metadata/tree, and leaves unresolved staged refs unresolved rather than copying scratch payloads.
- `AC-REQ-PERSIST-019-01`: autosave/session regressions confirm staged scratch can be recovered after crash-style flows but is discarded on clean close without save.
- `AC-REQ-PERSIST-020-01`: project-restore, controller, and DPF docs regressions confirm `.sfe` reopen preserves only projection-safe viewer summary state, drops live transport back to rerun-required projection, never serializes session-scoped temp bundles, and `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md` names the repo-local `.rst` / `.rth` smoke inputs plus manual `dene3.sfe` reopen checks.
- `AC-REQ-PERSIST-021-01`: serializer and port-locking regressions confirm locked-port state plus per-view hide filters round-trip through save/load, workspace snapshot restore, and duplicate-workspace flows, with retained proof summarized in `docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md`.
- `AC-REQ-PERSIST-022-01`: payload-contract, graphics-preferences, and shell-bridge regressions confirm `icon_source` remains derived/live-only, the nullable icon-size override round-trips through app preferences, and the title-icon feature does not widen `.sfe` persistence, with retained proof summarized in `docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md`.
- `AC-REQ-PERSIST-023-01`: plugin-loader, serializer, current-schema, and registry-validation regressions confirm add-on enabled-state plus pending-restart persistence and unavailable-add-on locked projection round-trip or rebind behavior, with retained proof summarized in `docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md`.
