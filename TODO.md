# TODO Ideas

## Open

### 1. Image Crop Button on Image Panel Node

**Goal:** Add an inline crop tool to image panel nodes, allowing users to non-destructively crop images directly on the canvas.

**UI:**
- A crop button icon (from the existing `uiIcons` set) appears at the **top-right** corner of the image panel node
- The button is **only visible on hover** (hidden by default)

**Crop Behavior:**
- Clicking the button activates an **inline crop UI** with drag handles directly on the image
- The crop region is **free-form** (no aspect ratio constraint)
- Users drag corners/edges to define the crop rectangle

**Storage (Non-Destructive):**
- Crop parameters (`crop_x`, `crop_y`, `crop_w`, `crop_h`) stored as **node properties**
- The original image file on disk is **never modified**
- The crop is applied at render time by adjusting the visible region of the image

**Key Files:**
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` — hover button overlay and inline crop UI
- `ea_node_editor/nodes/builtins/passive_media.py` — new crop rect node properties
- `ea_node_editor/ui_qml/graph_surface_metrics.py` — layout adjustments if needed

### 2. Expand/Collapse Button on Image Panel Node

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

### 3. Global Input-Layer Pattern for Interactive Node Surfaces

**Goal:** Define a clean, reusable input-layer pattern so future interactive nodes do not regress into cursor conflicts, swallowed clicks, or drag layers fighting with embedded controls.

**Problem Statement:**
- Full-overlay `MouseArea` items are swallowing left-clicks in several interactive-node scenarios
- Nested controls and crop/resize handles can expose the right local cursor shape, while the user still sees a host-level drag cursor
- Each new interactive surface is re-solving pointer ownership ad hoc instead of following one codebase-wide rule

**Desired Outcome:**
- Establish a shared pattern for hover-only overlays versus click/drag-capable overlays
- Make cursor ownership explicit when a surface enters an interaction mode
- Ensure host drag/resize layers yield cleanly to embedded buttons, handles, editors, and future interactive node tools
- Document the preferred primitives (`MouseArea` with `acceptedButtons: Qt.NoButton`, `HoverHandler`, explicit host locks, etc.) and where each should be used

**Key Files:**
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` — host drag/resize layers and cursor ownership
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` — current crop-overlay case study
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml` — canvas-wide input layering conventions

## Implemented

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
