# Graph Model Requirements

## Data Model
- `REQ-GRAPH-001`: Graph model shall include `ProjectData`, `WorkspaceData`, `ViewState`, `NodeInstance`, `EdgeInstance`.
- `REQ-GRAPH-002`: Node instances shall contain `collapsed` state, properties, and exposed port overrides.
- `REQ-GRAPH-003`: Workspaces shall include isolated node/edge sets and active view.

## Graph Operations
- `REQ-GRAPH-004`: Model shall support add/remove/move node operations.
- `REQ-GRAPH-005`: Model shall support add/remove edge operations.
- `REQ-GRAPH-006`: Model shall support workspace and view lifecycle operations.
- `REQ-GRAPH-010`: Graph model and scene operations shall support hierarchical node parenting with scope-aware navigation and transforms for nested subnodes.
- `REQ-GRAPH-011`: Graph operations (duplicate, clipboard, search/focus, and layout-sensitive rewiring) shall preserve valid parent chains and boundary-edge semantics across nested scopes.
- `REQ-GRAPH-012`: passive visual nodes, including comment backdrops, shall remain in `WorkspaceData.nodes` and passive `flow` connections shall remain in `WorkspaceData.edges` so selection, copy/paste, duplicate, view state, and save/load stay on the existing graph-document path.

## Rendering
- `REQ-GRAPH-007`: Custom graphics items shall represent nodes and edges.
- `REQ-GRAPH-008`: Collapsed nodes shall reduce visual footprint and use side connection anchors.
- `REQ-GRAPH-009`: Graph canvas and item rendering shall support Stitch-aligned visual chrome with zoom-aware level-of-detail simplification.
- `REQ-GRAPH-013`: `flow` edges shall support labels and flow-only visual style overrides while allowing multi-incoming targets where the declared target port permits them.
- `REQ-GRAPH-014`: passive logical-flow edges shall persist the stored cardinal port keys `top`, `right`, `bottom`, and `left`; edge labels and edge styling, not decision-specific port keys, shall carry branch meaning.
- `REQ-GRAPH-015`: passive logical-flow routing and handle placement shall resolve anchors from the authored cardinal side, using exact flowchart silhouette anchors for flowchart nodes and exact rectangular side anchors for the other passive families.
- `REQ-GRAPH-016`: comment backdrop membership shall be derived from authored geometry, selecting the smallest fully containing backdrop in the same scope and parent chain, excluding partial overlap, and supporting nested backdrop ownership.
- `REQ-GRAPH-017`: graph interactions shall reuse derived comment-backdrop membership for wrap-selection bounds plus descendant drag/resize propagation so moving or resizing a backdrop keeps contained nodes and nested backdrops coherent in scene payloads and undo history.
- `REQ-GRAPH-018`: collapsed comment backdrops shall suppress descendant node/backdrop payloads from the active scene and minimap, reroute boundary edges to backdrop-perimeter proxies, and enforce explicit-only versus recursive descendant clipboard/delete semantics depending on expanded versus collapsed state while recomputing derived ownership after duplicate, paste, and load.

## Acceptance
- `AC-REQ-GRAPH-004-01`: Node drag updates persisted model position.
- `AC-REQ-GRAPH-005-01`: Edge creation appears in scene and serialized graph.
- `AC-REQ-GRAPH-008-01`: Collapsing a node updates geometry and edge paths.
- `AC-REQ-GRAPH-009-01`: Zooming out simplifies labels/details while preserving connection semantics and interaction performance.
- `AC-REQ-GRAPH-010-01`: Group/ungroup and scope navigation retain valid hierarchy relationships and scoped editing behavior after save/load.
- `AC-REQ-GRAPH-011-01`: Hierarchy-aware duplicate/copy/paste/search/focus flows preserve rewired boundary edges and avoid cross-scope corruption.
- `AC-REQ-GRAPH-012-01`: passive-only workspaces, including comment backdrops, save, load, duplicate, and reopen through the normal graph serializer without introducing a separate artifact document model.
- `AC-REQ-GRAPH-013-01`: labeled `flow` edges render authored labels/styles, and targets such as passive connectors/end nodes can accept multiple incoming `flow` edges when the registry spec allows it.
- `AC-REQ-GRAPH-014-01`: serializer/scene round-trip preserves `top/right/bottom/left` flowchart port keys and labeled branch edges in the passive reference workspace without reviving legacy flowchart key aliases.
- `AC-REQ-GRAPH-015-01`: flowchart surface and routing regressions confirm exact top/right/bottom/left silhouette anchors and side normals across the supported passive flowchart variants.
- `AC-REQ-GRAPH-016-01`: membership regressions confirm smallest-container ownership, same-scope containment, wrap-selection bounds, and nested backdrop derivation.
- `AC-REQ-GRAPH-017-01`: interaction regressions confirm backdrop drag/resize moves descendants coherently and records grouped history without cross-scope leakage.
- `AC-REQ-GRAPH-018-01`: collapse, clipboard, serializer, and shell workflow regressions confirm descendant suppression, boundary-edge proxy rerouting, expanded-versus-collapsed copy/delete semantics, and load-time ownership recompute.
