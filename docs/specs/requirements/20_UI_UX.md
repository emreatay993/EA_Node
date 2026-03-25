# UI/UX Requirements

## Layout
- `REQ-UI-001`: Main shell shall be rendered in QML and include menu bar, top toolbar, left node library, center graph canvas, right inspector, bottom workspace tabs, and bottom console/log.
- `REQ-UI-002`: Workspace tabs shall support create, rename, duplicate, close, reorder, and switch.
- `REQ-UI-003`: Workspace tabs shall be displayed below the canvas area.
- `REQ-UI-004`: Each workspace shall support multiple named views (`V1`, `V2`, ...).
- `REQ-UI-005`: Each view shall preserve independent pan/zoom state.

## Node Library
- `REQ-UI-006`: Node library shall support text search and filtering by category, port direction, and data type.
- `REQ-UI-007`: Double-click or button action shall add selected node to canvas.

## Node Inspector
- `REQ-UI-008`: Selecting a node shall show editable properties and exposed-port toggles.
- `REQ-UI-009`: Collapse/expand control shall be available per collapsible node.

## Error UX
- `REQ-UI-010`: On execution failure, app shall switch to containing workspace, center failed node, and show error details.

## RC2 UX Surfaces
- `REQ-UI-011`: Application shell styling shall match Stitch references using QML theme tokens and surface hierarchy.
- `REQ-UI-012`: `ShellWindow` shall expose `show_workflow_settings_dialog()` and persist workflow settings metadata from a modal UI.
- `REQ-UI-013`: `ShellWindow` shall expose `set_script_editor_panel_visible()` and provide a Python script editor surface bound to selected `core.python_script` nodes.

## Subnode UX Surfaces
- `REQ-UI-014`: Shell and canvas UX shall support subnode scope navigation (breadcrumbs + keyboard navigation), group/ungroup transforms, and subnode pin editing directly from the inspector/library workflows.
- `REQ-UI-015`: File menu UX shall provide project-local custom workflow interchange through versioned `.eawf` import/export actions that remain separate from `.eanp` node package actions.

## Graphics Settings UX Surfaces
- `REQ-UI-016`: `ShellWindow` shall expose `show_graphics_settings_dialog()` and the Settings menu shall provide an app-wide Graphics Settings modal covering graphics performance mode (`Full Fidelity` / `Max Performance`), grid, minimap, snap-to-grid default, shell-theme selection, graph-theme follow-shell or explicit selection, and graph-theme manager access.
- `REQ-UI-017`: shell and graph canvas chrome surfaces shall support live application of shared shell-theme tokens for `stitch_dark` and `stitch_light`.
- `REQ-UI-018`: node and edge visuals shall resolve through dedicated graph-theme tokens while canvas chrome (background, grid, minimap, marquee, and drop-preview) stays on the shell-theme path.
- `REQ-UI-019`: `ShellWindow` shall expose `show_graph_theme_editor_dialog()` and provide a graph-theme manager/editor that groups built-in read-only themes and editable custom themes with create, duplicate, rename, delete, use-selected, and token-editing workflows.
- `REQ-UI-024`: shell status strip shall expose a compact app-global graphics-performance quick toggle with a `Graphics:` summary plus `Full Fidelity` / `Max Performance` actions that read and write the same persisted preference as Graphics Settings rather than a session-only override.

## Passive Visual Authoring UX Surfaces
- `REQ-UI-020`: graph canvas node rendering shall route through a host/factory surface split that keeps the standard node contract stable while loading `flowchart`, `planning`, `annotation`, `comment_backdrop`, and `media` passive families by `surface_family` / `surface_variant`, and shall reuse the shared header inline title editor across standard, passive, collapsed, and scope-capable node shells instead of adding per-surface title workflows.
- `REQ-UI-021`: passive nodes and `flow` edges shall expose style edit/reset/copy/paste workflows plus project-local preset CRUD from the shell/canvas context-menu path.
- `REQ-UI-022`: passive image and PDF media panels shall preview local filesystem sources and keep those previews after save/reopen.
- `REQ-UI-023`: interactive graph surfaces shall follow the locked host/surface input pattern: node-body interactions stay under the loaded surface, ordinary controls publish `embeddedInteractiveRects`, whole-surface modal tools use `blocksHostInteraction`, reusable controls come from `ea_node_editor/ui_qml/components/graph/surface_controls/` without reopening the public `graphNodeCard` / `graphCanvas` contract, and scope-capable shells preserve an `OPEN` badge as the dedicated scope-entry affordance while title double-click stays reserved for the shared header title editor.
- `REQ-UI-025`: passive flowchart surfaces shall render four exposed handles keyed `top`, `right`, `bottom`, and `left`, keep raw port labels hidden on flowchart host/drop-preview surfaces, anchor those handles on the exact silhouette perimeter, and publish `origin_side` plus gesture-ordered source/target authoring when a connect gesture starts from a neutral flowchart port.
- `REQ-UI-026`: comment backdrops shall render as dedicated zero-port passive grouping surfaces on a canvas layer below edges and regular nodes, remain distinct from connectable annotation cards, and support library/drop placement plus wrap-selection creation through shortcut `C` without changing `Ctrl+G` / `Ctrl+Shift+G` structural grouping shortcuts.
- `REQ-UI-027`: comment backdrops shall reuse the shared header inline title editor and support inline plus inspector body editing while collapsed descendants remain hidden on the canvas and expanded-versus-collapsed clipboard/delete affordances stay predictable to the user.
- `REQ-UI-028`: save/open/recover managed-file UX shall stay lightweight: warnings and prompts summarize staged and broken entries, and a compact `Project Files...` dialog shall list managed files, staged items, and broken file entries without introducing a full artifact-manager pane.
- `REQ-UI-029`: Save As shall always prompt for managed-data copy behavior, default to a self-contained copy that carries over currently referenced managed files, and shall not copy staged scratch data into the destination project.
- `REQ-UI-030`: source-import workflows shall honor an app preference for `managed_copy` versus `external_link`, defaulting to managed copy, and tracked missing-file surfaces shall stay limited to the packet-owned node-level repair affordances for passive media, File Read, and Excel Read.
- `REQ-UI-031`: `Process Run` shall expose an inline `Output Mode` quick control limited to `memory` and `stored`, with a status chip that explains whether stdout/stderr stay inline or emit staged transcript refs.
- `REQ-UI-032`: the PyDPF viewer UX shall ship `dpf.viewer` as a viewer-family surface that routes proxy/live state through `viewerSessionBridge`, preserves reopen summaries, and enforces one-live `focus_only` behavior by default with explicit `keep_live` opt-in.

## Acceptance
- `AC-REQ-UI-002-01`: Tab actions operate without data loss for non-closed workspaces.
- `AC-REQ-UI-005-01`: Switching views restores stored zoom and pan center.
- `AC-REQ-UI-010-01`: Failure event visibly highlights failed node and displays error message.
- `AC-REQ-UI-011-01`: QML shell and graph canvas visually match the Stitch baseline and remain fully functional.
- `AC-REQ-UI-012-01`: Settings modal saves user edits to project metadata and subsequent run triggers include these values.
- `AC-REQ-UI-013-01`: Script editor reflects selected script node content and applying edits updates model state.
- `AC-REQ-UI-014-01`: Users can author nested subnode workflows end-to-end (group, navigate scopes, edit pins, publish custom workflow, and place published snapshots from the library).
- `AC-REQ-UI-015-01`: Exporting and importing `.eawf` files preserves custom-workflow snapshot fidelity and updates library availability without changing `.eanp` package behavior.
- `AC-REQ-UI-016-01`: accepting Graphics Settings updates runtime graphics performance mode, shell-theme, and graph-theme behavior, and reopening the application restores the persisted graphics-performance and theme preferences.
- `AC-REQ-UI-017-01`: `stitch_dark` and `stitch_light` both render shell and graph-canvas chrome surfaces without breaking existing shell/canvas contracts.
- `AC-REQ-UI-018-01`: `NodeCard` and `EdgeLayer` follow the active graph theme while background/grid/minimap/drop-preview chrome stay on the shell-theme path.
- `AC-REQ-UI-019-01`: the graph-theme manager keeps built-in themes read-only, persists custom-theme library edits, and only live-applies token edits when the edited theme is the active explicit custom theme.
- `AC-REQ-UI-020-01`: standard executable nodes and passive flowchart/planning/annotation/comment-backdrop/media nodes all render through the shared host, and inline title editing on standard, passive, collapsed, and scope-capable shells reuses the shared header editor without breaking existing `graphNodeCard` / `graphCanvas` discoverability contracts.
- `AC-REQ-UI-021-01`: passive node and `flow` edge context menus can apply, copy/paste, reset, and persist project-local presets without changing executable-node theming behavior.
- `AC-REQ-UI-022-01`: reopening a project restores passive image and PDF previews for valid local sources and keeps the authored captions and fit/page settings.
- `AC-REQ-UI-023-01`: host, inline-control, shared-header title-edit, scoped `OPEN` badge, media-surface, and shell graph-surface regressions pass without reintroducing hover-proxy shims or click-swallowing overlays, and the final matrix is recorded in `docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md`.
- `AC-REQ-UI-024-01`: the status-strip summary and buttons switch the active graphics-performance mode immediately, stay synchronized with Graphics Settings, and restore the same saved mode after relaunch.
- `AC-REQ-UI-025-01`: flowchart surface, visual-polish, flow-edge preview, and graph-surface input regressions confirm four-handle rendering, hidden raw labels, exact cardinal anchors, `origin_side` interaction payloads, and gesture-ordered neutral flowchart authoring without regressing non-flowchart node behavior.
- `AC-REQ-UI-026-01`: comment backdrop layer and shell workflow regressions confirm under-edge rendering, library/drop placement, shortcut `C`, and preserved group/ungroup shortcuts.
- `AC-REQ-UI-027-01`: comment backdrop inline-editor, collapse, and clipboard regressions confirm shared-header title edits, inline/inspector body sync, collapsed descendant hiding, and expanded-versus-collapsed copy/delete behavior without regressing existing graph-surface input routing.
- `AC-REQ-UI-028-01`: project-files dialog and prompt regressions confirm managed/staged/broken summaries across save, open, and recovery flows, plus repair-button availability, without widening the UI into a broader artifact manager.
- `AC-REQ-UI-029-01`: Save As regressions confirm the self-contained-copy default carries referenced managed files, excludes staged scratch data, and switches the live project path to the new `.sfe`.
- `AC-REQ-UI-030-01`: source-import default and file-issue regressions confirm managed-copy is the default browse mode, tracked missing managed/staged/external paths surface node-level guidance, and supported node types keep the approved repair affordances.
- `AC-REQ-UI-031-01`: `Process Run` regressions confirm the inline `memory` / `stored` toggle, chip wording, and stored transcript-ref behavior without widening quick-toggle UI to other heavy-output nodes.
- `AC-REQ-UI-032-01`: `dpf.viewer`, bridge, and viewer-surface regressions confirm `focus_only` versus `keep_live` live-policy behavior, preserved proxy reopen summaries, and shell-managed live overlays without regressing the shared viewer surface contract.
