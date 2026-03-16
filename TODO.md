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
