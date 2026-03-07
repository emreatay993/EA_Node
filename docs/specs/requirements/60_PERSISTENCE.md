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

## Module Decomposition
- `REQ-PERSIST-008`: Persistence internals shall be split into project codec (`ProjectData` <-> JSON document), migration/normalization pipeline, and session/autosave storage service.

## Acceptance
- `AC-REQ-PERSIST-001-01`: Save/load round trip preserves ids, wiring, properties, active workspace, and active view.
- `AC-REQ-PERSIST-004-01`: Older schema docs are upgraded without manual edits.
- `AC-REQ-PERSIST-006-01`: Restart restores previous session when available.
- `AC-REQ-PERSIST-007-01`: v1 project documents load into v2 shape with normalized metadata defaults.
