# ADR-0006: Plot Display Surfaces

- Status: Proposed
- Date: 2026-05-01
- Initiative: [PLOTTER_NODES](../work_packets/plotter_nodes/PLOTTER_NODES_MANIFEST.md)
- Depends on: COREX_ARCHITECTURE_MODERNIZATION P07 (`SurfaceSpec` and content-fullscreen contracts)

## Decision
Plot nodes expose three active display surfaces, hosted by a single widget instance through a `PlotHostService` modelled on `ea_node_editor/ui_qml/viewer_host_service.py`:

1. **Embedded** - thumbnail rendered inside the node body via the P07 `SurfaceSpec` contract. Surface family `"plot"`, surface variant `<plot_type>`. The embedded surface is interactive (pan / zoom / hover-readout) only while focused or hovered; on focus loss it auto-reverts to a static raster, regardless of execute state.
2. **Fullscreen overlay** - the same widget hoisted into the content-fullscreen overlay introduced in P07, with a full toolbar (pan / zoom / select / reset / export) and the time-series scrubber controls when applicable.
3. **Detached single-plot window** - a top-level `QWindow` for one plot, useful for multi-monitor setups.

The persistent multi-plot session window is deprecated and disabled. Sink mode is a per-node `render_in_canvas: bool` property that suppresses embedded rendering. The node still computes and caches; opening fullscreen or detached presentation triggers an on-demand render. A workspace-level "lightweight canvas" preference forces sink mode for every plot at once.

## Rationale
- Hosting one widget instance through a `PlotHostService` reuses the embedded/fullscreen/detached pattern already proven by the DPF viewer, so no per-surface widget duplication is required.
- The auto-static-on-blur rule keeps idle canvas cost low when many plots are visible simultaneously, while still letting the focused plot behave like a real interactive viewer.
- Sink mode plus the global preference give users a coarse and a fine-grained control over canvas load without sacrificing the ability to inspect a plot when wanted.
- Reusing P07's `SurfaceSpec` keeps surface selection data-driven (P07 acceptance criterion 1) and avoids reintroducing a QML branch per plot type.

## Consequences
- Plot session UI entry points must remain disabled; inline live previews should continue to use the embedded native overlay path.
- Sink mode and the global preference must round-trip through the canonical action vocabulary (P03) so toggling them is recorded canonically and is undoable.
- Auto-static-on-blur transitions are driven by Qt focus and hover events, not by execute lifecycle, so the rendering policy is independent of whether a node has new data.
