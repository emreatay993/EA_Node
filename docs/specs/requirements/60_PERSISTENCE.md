# Persistence Requirements

## File Format
- `REQ-PERSIST-001`: Canonical project format shall be `.sfe` (versioned JSON).
- `REQ-PERSIST-002`: Document shall include schema version, project metadata, workspaces, views, nodes, and edges.
- `REQ-PERSIST-003`: Serialization shall be deterministic (stable ordering) for diffability.

## Migration
- `REQ-PERSIST-004`: Serializer shall implement migration hooks from earlier schema versions.
- `REQ-PERSIST-005`: Load shall migrate in-memory document before model construction.

## Session Persistence
- `REQ-PERSIST-006`: Last session shall persist workspace/view state across restarts.
- `REQ-PERSIST-007`: Metadata schema shall persist normalized UI state and workflow settings (`metadata.ui`, `metadata.workflow_settings`) with auto-migration from earlier schema versions.
- `REQ-PERSIST-009`: Schema migration and codecs shall persist normalized subnode hierarchy view state (`ViewState.scope_path`) and project-local custom workflow definitions (`metadata.custom_workflows`).
- `REQ-PERSIST-010`: Custom workflow snapshot interchange shall use a versioned `.eawf` JSON file format that stores exactly one normalized custom workflow definition.
- `REQ-PERSIST-011`: app-wide graphics preferences, including graphics performance mode plus shell-theme and graph-theme state, shall persist in a versioned app-preferences JSON document under `user_data_dir()` and shall remain separate from `.sfe` project metadata and `last_session.json`.
- `REQ-PERSIST-012`: graph-theme state shall be stored only under `graphics.graph_theme = {follow_shell_theme, selected_theme_id, custom_themes}` with custom graph themes serialized inline in app preferences rather than external files.
- `REQ-PERSIST-013`: `.sfe` project documents shall persist passive-node visual metadata, passive media properties, `flow` edge labels/styles, and project-local passive style preset libraries under normalized project metadata.
- `REQ-PERSIST-014`: `.sfe` project documents shall persist authored comment backdrop title/body/collapsed state and geometry through the normal node document path, but shall not persist derived membership or containment metadata; load shall recompute ownership from geometry.

## Module Decomposition
- `REQ-PERSIST-008`: Persistence internals shall be split into project codec (`ProjectData` <-> JSON document), migration/normalization pipeline, and session/autosave storage service.

## Acceptance
- `AC-REQ-PERSIST-001-01`: Save/load round trip preserves ids, wiring, properties, active workspace, and active view.
- `AC-REQ-PERSIST-004-01`: Older schema docs are upgraded without manual edits.
- `AC-REQ-PERSIST-006-01`: Restart restores previous session when available.
- `AC-REQ-PERSIST-007-01`: v1 project documents load into v2 shape with normalized metadata defaults.
- `AC-REQ-PERSIST-009-01`: Save/load round trips preserve nested scope paths and normalized custom workflow metadata, including snapshot fragments.
- `AC-REQ-PERSIST-010-01`: `.eawf` export/import round trips preserve custom workflow snapshot fidelity across projects.
- `AC-REQ-PERSIST-011-01`: app-preferences round-trip preserves graphics performance mode, shell-theme, and graph-theme settings and does not serialize them into `.sfe` project metadata or `last_session.json`.
- `AC-REQ-PERSIST-012-01`: v1 app-preferences documents migrate to v2 with a default `graphics.graph_theme` payload, and persisted custom graph themes round-trip inline under app preferences.
- `AC-REQ-PERSIST-013-01`: passive-only workspaces round-trip authored node sizes/colors, media source properties, `flow` edge labels/styles, and `metadata.ui.passive_style_presets` without losing fidelity.
- `AC-REQ-PERSIST-014-01`: serializer regressions confirm comment backdrop save/load strips runtime membership fields and rebuilds ownership from geometry without losing authored backdrop state.
