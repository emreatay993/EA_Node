# Passive Surface Loading And Contracts

## Purpose
Use this for passive node host loading, surface contracts, metrics, surface sizing, and passive host entry points.

## Start Here
- `ea_node_editor/ui_qml/surface_contracts.py`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/graph_geometry/surface_contract.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostSceneAccess.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostLayout.qml`
- `ea_node_editor/ui_qml/components/graph/GraphSurfaceBase.qml` - base Item for passive/viewer surfaces: host plumbing, null-safe `nodeProperties`, the shared propRaw/propValue/propString/propBool/propNumber accessors, and the single chrome-fact derivation (`surfaceShowTitle`/`surfaceShowFrame`/`surfaceContentOnly`). New surfaces root on this; do not re-declare private accessor copies.
- `ea_node_editor/ui_qml/components/graph/passive/`
- `ea_node_editor/ui_qml/components/graph/passive/FlowchartShapeCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/passive/FlowchartShapeGeometry.js` - shared silhouette parameters, shape-aware body text regions, and the grow-to-fit searches
- `ea_node_editor/ui_qml/components/graph/passive/GraphAnnotationNoteSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphBareTextSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphFlowchartNodeSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphTimestampDateTimePopover.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`
- `tests/qml_quick/tst_graph_node_host.qml`
- `tests/graph_surface/passive_host_boundary_suite.py`

## Viewport Visibility
- Every loaded node surface receives its `GraphNodeHost` through the existing `host` property. Read the canonical `host.inVisibleViewport` fact behind the surface's normal host-null guard to suspend expensive work; surfaces must not independently calculate canvas geometry.
- Exact visibility uses the node's live scene bounds against the authoritative visible scene rectangle. Buffered `renderActive` loading and visible-model virtualization are separate: nearby off-screen surfaces may remain loaded, while far-away hosts and surfaces are still removed. `GraphNodeSurfaceLoader` incubates only those off-screen buffered surfaces asynchronously; exact-viewport and fail-open hosts keep synchronous loading. Once an off-screen load starts, it remains asynchronous until completion even if a fast pan carries the host into the exact viewport, avoiding a forced synchronous finish inside the input path.

## Surface Routing

- A collapsed host keeps its surface loaded while its floating toolbar is active because the surface owns live action descriptors and dispatch. The body stays hidden, contributes no input rectangles or interaction lock, and viewer/plot native activity is disabled while hidden. Closing the toolbar unloads the collapsed body; off-screen render-activation policy is unchanged.

- `surface_contracts.py` and the projected `surface_spec` solely own component routing; `GraphNodeHost.qml` falls back to the standard surface only when that object is absent. Projected `surface_variant` remains presentation metadata, and the host's variant override is reserved for the group-backdrop input overlay.

## Annotation Text Notes
- `passive.annotation.text` is a passive annotation node with cardinal passive ports and a chrome-free `annotation`/`text` surface.
- The surface loads through `SurfaceSpec` component key `annotation_text` and renders `GraphBareTextSurface.qml`.
- `GraphBareTextSurface.qml` delegates markdown/plain rendering, source editing, and text-style toolbar actions to `GraphRichTextBlock.qml`, the shared prose rich-text component used by annotation notes and non-timestamp flowchart body/cube text. Groups do not use rich text or body content.
- Bare Text height follows the measured rendered/editor content plus padding, while the user controls width only; height changes reuse the normal resize preview/finish path so geometry remains persisted.
- Its metric contract sets `use_host_chrome=false` and `use_host_shadow=false`; keep the fill transparent and ports active.
- `GraphNodeHost.qml` excludes only this bare-text annotation surface from host subtree bitmap caching, preserving live Qt-rendered text while leaving normal passive and active node cache behavior intact.

## Data Panel Notes
- `data.panel` is active dataflow but uses the custom surface route in `surface_contracts.py` to load `GraphPanelSurface.qml` without a standard title header.
- Its metric contract keeps host frame/shadow, uses the reference 16 px corner radius, fixes the unlabeled optional Tree ports at the upper left/right corners, and allows two-dimensional resize. The root-layer `GraphPanelEditorPopover.qml` owns modal editing; display mode leaves host click/drag handling intact except for the populated Data `ListView` double-tap forwarder. Auto-resize leaves an empty Panel at its `280x180` default and fits authored or connected content from the rendered Text/Data dimensions.
- Data mode renders branch headers flush to the body with right-aligned paths, a shaded centered index column, and left-aligned monospace values. Disconnected copy always uses authored text; connected copy may use the current runtime tree. `GraphNodeHost.qml` and `GraphNodeSurfaceLoader.qml` allow only the non-mutating Panel copy actions through read-only guards.

## Flowchart Notes
- `GraphFlowchartNodeSurface.qml` owns body-text fallback behavior; icon-like flowchart variants suppress title/display-name fallback so catalog labels do not appear inside draw.io-style shapes.
- `GraphFlowchartNodeSurface.qml` also owns the shape-aware selected glow (`graphNodeFlowchartSelectedHalo`), but the selected colour still comes from `GraphNodeHostTheme.qml` through `host.selectedGlowColor`.
- The timestamp flowchart variant owns its `live` body-rendering mode and timestamp-only toolbar actions; the manual date/time editor is hosted by `GraphCanvasRootLayers.qml` through `GraphTimestampDateTimePopover.qml`.
- Non-timestamp flowchart `body`, `body_top`, and `body_right` fields use reusable rich-text slots; timestamp `body` stays plain and keeps the live/manual timestamp contract.
- `FlowchartShapeCanvas.qml` owns the reusable vector silhouettes for graph surfaces and library previews; keep its pure-QML host, variant, fallback, and timestamp behavior aligned with `tests/qml_quick/tst_graph_node_host.qml`, while `tests/test_flowchart_visual_polish.py` retains source and Python-integration coverage.
- `tests/qml_quick/tst_graph_node_host.qml` also owns pure-QML annotation host rendering, library flowchart aspect-ratio fitting, and Group backdrop title/chrome checks. Python retains annotation catalogue/metric facts, flowchart geometry and drop-preview integration, and Group catalogue/model/serialization facts.

## Flowchart Body Text Regions And Text Fit
- Each variant's contract `body_text_placement` (`GraphNodeSurfaceMetricContract.json` and its generated `.js` mirror; `surface_contract.py` only validates the names) is resolved against the silhouette by `FlowchartShapeGeometry.js`, which also owns the shape parameters `FlowchartShapeCanvas.qml` draws with, so text regions and outlines cannot drift. Shape-aware placements: decision `inscribed_diamond` (50% x 50%), connector `inscribed_ellipse` (1/sqrt(2) per axis), input/output `between_slants`, document `above_wave`, database `between_caps`, callout `above_tail`, start/end `between_end_caps`, multi-document `front_page`; edges the outline limits keep `TEXT_REGION_PADDING` (6 px) and the other edges keep the variant's contract margins. `center`, `below_shape`, `front_face`, and `cube_front_face` keep the margin-box geometry. Double-click still edits the body anywhere in the old margin box.
- `body_fit` (`clip` default, `grow`, `shrink`; every non-timestamp spec in `nodes/builtins/passive_flowchart.py`) is an Inspector enum and the text toolbar's Text fit group (`text_fit_clip|grow|shrink`, icons `crop`, `fit-height`, `text-decrease`). The timestamp variant keeps its own body contract and has no text fit.
- Grow: `GraphFlowchartNodeSurface.qml` previews growth while the body or its style is being edited (`resizePreviewChanged`, live geometry) and persists it through `resizeFinished` -> `set_node_geometry`, one resize history step after the text commit. It re-checks on surface load, text/style/mode changes, and resize-handle release, never on a bare geometry change, so undoing a growth sticks. Free-aspect shapes grow in height; contract `square` variants scale both axes at their current ratio. While a handle drags, `GraphNodeResizeHandle.qml` asks the surface's `minimumNodeHeightForWidth(width)` so the text stays inside. Read-only, locked, and collapsed nodes never grow.
- Automation drives the same path: `node.fit_text` (see [Automation API And MCP Server](automation_api_mcp.md)) calls the surface's public `settleTextFit()`, which applies a pending grow at once so the resize lands in the op's undo step, and reads `textFitReport()`. Keep both functions and their report keys stable when changing the fit logic.
- Shrink and the overflow mark live in `GraphRichTextBlock.qml` behind opt-in flags (`fitMeasurementEnabled`, `shrinkToFit`, `overflowIndicatorEnabled`; Bare Text and notes leave them off). A hidden probe with the rendered text's font and renderer measures the shown text (the editor draft while editing); shrink picks the largest whole pixel size down to 6 px that fits. Clipped text anchors to the top: plain text keeps whole lines and elides the last one (`overflowMark` `elide`), while markdown, which Qt cannot elide, and side-only clipping show the ellipsis pill (`graphNodeFlowchartBodyOverflowIndicator`, `overflowMark` `pill`).
- Tests: region geometry, grow searches, clip/shrink/grow/square/read-only/toolbar/drag-floor host checks in `tests/qml_quick/tst_graph_node_host.qml` (its text-fit cases use explicit line breaks so they pass with or without `QT_QPA_FONTDIR`); editing preview, commit, and Escape plus scene persistence and undo/redo in `tests/graph_surface/inline_editor_suite.py`; contract placements, square variants, and the `body_fit` spec in `tests/test_flowchart_visual_polish.py`.

## Selected Glow Notes
- Passive selected outline/glow colour is graph-theme-owned in `GraphNodeHostTheme.qml` (`card_selected_border` -> `selectedOutlineColor` -> `selectedGlowColor`); passive `visual_style.border_color` remains the idle outline override, and selected passive borders thicken above the idle width.
- Authored `passive.*` objects expose Lock/Unlock from the node floating toolbar. Locked hosts render below normal nodes at z 10, reject pointer selection by default, and expose only Zoom/Unlock when the session-only locked-object interaction mode is enabled.
- Rectangular passive surfaces use the shared `GraphNodeChromeBackground.qml` `graphNodeSelectedHalo`; flowchart passives keep their shape-aware halo in `GraphFlowchartNodeSurface.qml`.
- Chrome-backed passive nodes share the same flat title row as action/viewer nodes: no category accent strip or separate header fill/gradient. Passive `visual_style` keeps fill, border, text, body-gradient, geometry, and typography fields; retired `accent_color`, `header_color`, and `header_gradient_*` keys are stripped from node styles and project-local presets during schema-4 document normalization.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_boundary_suite.py --ignore=venv -q
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode gui --dry-run
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QUICK_CONTROLS_STYLE = "Basic"
& (Join-Path $env:QT_ROOT "bin\qmltestrunner.exe") -input tests/qml_quick/tst_graph_node_host.qml -eventdelay 0 -keydelay 0 -mousedelay 0 -o -,txt
Remove-Item Env:QT_QPA_PLATFORM, Env:QT_QUICK_CONTROLS_STYLE -ErrorAction SilentlyContinue
.\venv\Scripts\python.exe -m pytest tests/test_passive_node_contracts.py tests/test_passive_graph_surface_host.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_flowchart_surfaces.py tests/test_flowchart_visual_polish.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/graph_surface/inline_editor_suite.py -k "flowchart" --ignore=venv -q -n 0
.\venv\Scripts\python.exe -m pytest tests/test_annotation_catalog.py tests/test_group_backdrop_contracts.py --ignore=venv -q -n 0
.\venv\Scripts\python.exe -m pytest tests/test_panel_surface.py --ignore=venv -q
```

`tests/test_passive_graph_surface_host.py` aggregates its leaf suites, including
`tests/graph_surface/p03_passive_host_entrypoint_suite.py`. Run the aggregate or
an individual leaf suite, never both in one command.

## Breadcrumbs
- [Passive, Media, And Tabular Surfaces](../subsystems/passive_media_tabular_surfaces.md)
- [Surface Input And Inline Controls](surface_input_and_inline_controls.md)

## Update Triggers
Update when surface contracts, passive host selection, host viewport visibility, buffered look-ahead loading, flowchart variants, body text placements or text fit, metrics, passive loading tests, or aggregate/leaf test routing changes.
