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

### 2. Keep Legacy Selected-Node Routing Inspector-Only

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

### 3. Show Folder Node

**Goal:** Add a `Show Folder` node that can display folder contents in a Windows Explorer-style view and launch files/folders through the OS.

**Scope for Initial Implementation:** Windows-specific behavior is acceptable for now. Cross-platform support can be tracked separately as a later enhancement.

**Properties/Features:**
- It accepts file paths as optional
- The node is expandable to full view via the existing overlay button that is generally used for this purpose
- Users can browse to their own file paths if they wish
- It lists the contents of that folder as it is shown from OS explorer (like Windows's own file explorer)
- Users can use the right-click action on a file to `Open in Explorer` to open the folder or subfolder containing the selected file
- If a file is double-clicked it is opened in the default application specified by the OS

### 4. Extend Show Folder Node Beyond Windows

**Goal:** Add non-Windows OS support for the `Show Folder` node as a later enhancement.

**Potential Follow-Up Scope:**
- Detect the current platform and adapt shell/open behavior accordingly
- Support native folder browsing and file launching semantics on macOS and Linux
- Align context-menu actions with each OS's file manager expectations while preserving the existing Windows behavior
- Keep the initial Windows-first implementation stable while expanding platform coverage

## Implemented

### Image Crop Button on Image Panel Node

**Status:** Implemented on `main`

**Summary:**
- Image panel nodes expose a hover-only crop button in the top-right corner
- Clicking the button enters inline crop mode with free-form edge/corner handles
- Crop parameters are stored as hidden node properties (`crop_x`, `crop_y`, `crop_w`, `crop_h`)
- Cropping is non-destructive and applied at render time without modifying the source image on disk
- Crop mode locks host drag/resize/port interactions and owns the cursor until editing ends

### Graph-Surface Input Routing Pattern

**Status:** Implemented via the `GRAPH_SURFACE_INPUT` packet set

**Summary:**
- `GraphNodeHost.qml` keeps node-body drag/select/open/context routing underneath the loaded surface instead of above it
- `GraphNodeSurfaceLoader.qml` publishes `embeddedInteractiveRects` for local control ownership and `blocksHostInteraction` for whole-surface modal locks
- Shared graph-surface buttons and editors live under `ea_node_editor/ui_qml/components/graph/surface_controls/` so future surfaces can reuse the locked interaction pattern
- Hover-only affordances now use hover-safe primitives instead of invisible click-swallowing overlays or host hover-proxy shims
- Final regression coverage and the approved shell fallback are recorded in `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md`

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
