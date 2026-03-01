# Graph Model Requirements

## Data Model
- `REQ-GRAPH-001`: Graph model shall include `ProjectData`, `WorkspaceData`, `ViewState`, `NodeInstance`, `EdgeInstance`.
- `REQ-GRAPH-002`: Node instances shall contain `collapsed` state, properties, and exposed port overrides.
- `REQ-GRAPH-003`: Workspaces shall include isolated node/edge sets and active view.

## Graph Operations
- `REQ-GRAPH-004`: Model shall support add/remove/move node operations.
- `REQ-GRAPH-005`: Model shall support add/remove edge operations.
- `REQ-GRAPH-006`: Model shall support workspace and view lifecycle operations.

## Rendering
- `REQ-GRAPH-007`: Custom graphics items shall represent nodes and edges.
- `REQ-GRAPH-008`: Collapsed nodes shall reduce visual footprint and use side connection anchors.
- `REQ-GRAPH-009`: Graph canvas and item rendering shall support Stitch-aligned visual chrome with zoom-aware level-of-detail simplification.

## Acceptance
- `AC-REQ-GRAPH-004-01`: Node drag updates persisted model position.
- `AC-REQ-GRAPH-005-01`: Edge creation appears in scene and serialized graph.
- `AC-REQ-GRAPH-008-01`: Collapsing a node updates geometry and edge paths.
- `AC-REQ-GRAPH-009-01`: Zooming out simplifies labels/details while preserving connection semantics and interaction performance.
