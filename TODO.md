# TODO Ideas

## 1. Drag-and-Drop Tab Reordering

**Goal:** Improve UX by allowing users to drag-and-drop tabs to reorder them within their tab pill areas.

**Scope:**
- Workspace tabs (Workspace 1, Workspace 2, etc.) — reorderable via drag
- View tabs (top-right area) — reorderable via drag
- NOT the Output/Errors/Warnings tabs at the bottom

**Animation:**
- Smooth slide: other tabs smoothly slide left/right to make room as the user drags a tab

**Persistence:**
- Custom tab order is saved and persists across sessions

## ~~2. Ungroup Subnode Action~~ ✅

**Goal:** Add an "Ungroup" action for subnodes, accessible from both the right-click context menu and the inspector properties panel.

**Scope:**
- Right-click context menu: "Ungroup Subnode" item with destructive (red) styling, placed right above "Remove Node"
- Inspector panel: "UNGROUP" button in the Node Definition section, next to the collapse button, with destructive styling
- Only visible when the selected node is a subnode (`core.subnode`)
- Calls the existing ungroup logic (same as Ctrl+Shift+G)
- No confirmation dialog — performs immediately

**Status:** Implemented

## 3. Image Crop Button on Image Panel Node

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
