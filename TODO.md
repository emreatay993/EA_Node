# TODO Ideas

## Open

### 1. Expand/Collapse Button on Image Panel Node

**Goal:** Allow users to expand an image panel node to fill the canvas area for a larger view, then collapse it back to its original size.

**UI:**
- An expand/collapse toggle button (from the existing `uiIcons` set) appears at the **top-right** corner, **next to the crop button**
- The button is **only visible on hover** (same behavior as the crop button)
- Icon toggles between an "expand" and "collapse" state

**Expand Behavior:**
- Clicking the button **expands the node itself** to fill the available canvas/viewport area
- The node's original position and size are remembered
- The expanded view **respects the node's `fit_mode`** property (contain/cover/original)

**Collapse Behavior:**
- Clicking the button again **collapses the node back** to its original size and position

**Key Files:**
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` — hover button and expand/collapse logic
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` — node size/position management for expand/collapse

### 2. Finish the Shared Input-Layer Pattern for Interactive Node Surfaces

**Status:** Partially implemented

**What Exists Today:**
- The media crop surface already exposes a reusable host/surface contract for interactive surfaces
- `GraphNodeSurfaceLoader.qml` forwards `blocksHostInteraction` and `hoverActionHitRect` from the loaded surface
- `GraphNodeHost.qml` disables host drag, resize, and port interactions while a surface owns the interaction
- The crop surface explicitly takes cursor ownership during crop mode and yields it back when the mode ends

**Remaining Goal:** Generalize and document that pattern so future interactive nodes do not regress into cursor conflicts, swallowed clicks, or drag layers fighting with embedded controls.

**Remaining Work:**
- Establish the preferred pattern for hover-only overlays versus click/drag-capable overlays across all interactive surfaces
- Document cursor ownership rules when a surface enters an interaction mode
- Audit existing interactive nodes so host drag/resize layers yield cleanly to embedded buttons, handles, editors, and future interactive node tools
- Document the preferred primitives (`MouseArea` with `acceptedButtons: Qt.NoButton`, `HoverHandler`, explicit host locks, etc.) and where each should be used

**Key Files:**
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` — host drag/resize layers and cursor ownership
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml` — current host/surface interaction contract
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` — current crop-overlay case study
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml` — canvas-wide input layering conventions

### 3. Keep Legacy Selected-Node Routing Inspector-Only

**Status:** Partially implemented

**Goal:** Do not use the legacy selected-node property path for graph-surface controls. Graph-surface commits and browse actions should always route by explicit `nodeId`, while the selected-node APIs remain available for the inspector until the final migration/removal pass.

**Why This Matters:**
- Embedded controls on graph surfaces can claim focus before the old selected-node state has updated
- Explicit `nodeId` routing prevents edits from landing on the wrong node when the user interacts with a non-selected node
- Decoupling graph-surface editing from inspector selection keeps the interaction model predictable and reduces hidden state dependencies

**Advantages of the Explicit `nodeId` Path:**
- More correct for inline graph editing because the target node is supplied directly
- Less fragile than routing through whatever node happens to be selected
- Easier to reuse for future graph-surface editors such as `path` and `textarea`
- Cleaner separation of responsibilities: graph surface owns local editing, inspector owns selected-node editing

**Guardrails:**
- Do not introduce new graph-surface controls that call `set_selected_node_property(...)`
- Do not introduce new graph-surface browse flows that call `browse_selected_node_property_path(...)`
- Keep legacy selected-node APIs stable for inspector usage until the dedicated cleanup/removal packet
- When graph-surface controls begin interaction, select/focus the node and clear transient canvas state, but still commit by explicit `nodeId`

**Current Preferred APIs for Graph Surfaces:**
- `sceneBridge.set_node_property(nodeId, key, value)`
- `mainWindow.browse_node_property_path(nodeId, key, currentPath)`

**Legacy APIs That Should Stay Inspector-Only:**
- `mainWindow.set_selected_node_property(key, value)`
- `mainWindow.browse_selected_node_property_path(key, currentPath)`

**Key Files:**
- `ea_node_editor/ui_qml/components/GraphCanvas.qml` — graph-surface interaction preparation and explicit `nodeId` routing
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` — host-level surface control bridge seam
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml` — current inline surface editors
- `ea_node_editor/ui_qml/graph_scene_bridge.py` — QML-invokable node property bridge
- `ea_node_editor/ui/shell/window.py` — inspector APIs and graph-surface-specific browse bridge
- `docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md` — packet history for the interaction-bridge migration

## Implemented

### Image Crop Button on Image Panel Node

**Status:** Implemented on `main`

**Summary:**
- Image panel nodes expose a hover-only crop button in the top-right corner
- Clicking the button enters inline crop mode with free-form edge/corner handles
- Crop parameters are stored as hidden node properties (`crop_x`, `crop_y`, `crop_w`, `crop_h`)
- Cropping is non-destructive and applied at render time without modifying the source image on disk
- Crop mode locks host drag/resize/port interactions and owns the cursor until editing ends

### Drag-and-Drop Tab Reordering

**Status:** Implemented on `main`

**Summary:**
- Workspace tabs and view tabs can be reordered via drag
- Reordering animates tab displacement while dragging
- Custom tab order persists across sessions
- Output/Errors/Warnings tabs remain excluded

### Ungroup Subnode Action

**Status:** Implemented on `main`

**Summary:**
- "Ungroup Subnode" is available in the right-click context menu with destructive styling
- "UNGROUP" is available in the inspector for selected `core.subnode` nodes
- Both entry points call the existing ungroup action without a confirmation dialog
