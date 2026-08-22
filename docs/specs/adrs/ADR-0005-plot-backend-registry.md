# ADR-0005: Plot Backend Registry

- Status: Proposed
- Date: 2026-05-01
- Initiative: [PLOTTER_NODES](../work_packets/plotter_nodes/PLOTTER_NODES_MANIFEST.md)

## Decision
Introduce a pluggable plot-backend registry analogous to the existing viewer backend registry (`ea_node_editor/execution/viewer_backend.py`). Each backend declares capability flags as a set of `(plot_type, surface)` pairs where `surface ∈ {"live", "static_export", "data_export"}`. Backends may be partial. Each plot node carries a `backend: str` property whose `"auto"` value resolves through a workspace-global default kept in user preferences. The UI's per-node backend dropdown is gated by the capability flags reported for the node's `plot_type`.

## Rationale
- Mirrors the precedent set by `ViewerWidgetBinder` and the viewer backend registry, so plot backends use a familiar contract for binders, factories, and addon registration via `ea_node_editor/addons/catalog.py`.
- Per-`(plot_type, surface)` capability flags allow specialized backends — for example a future Rust line-only backend, or a plotly-class backend that only ships HTML export — to register without satisfying every possible plot type or output surface.
- Per-node backend selection plus a workspace-global default lets advanced users compare backends side by side while keeping the common case one decision wide.
- Aligns with the COREX modernization Locked Default that compiled foreign-language nodes are prepared through descriptor contracts before native build execution lands; the registry is the descriptor surface for plot rendering.

## Consequences
- A new public extension surface: backend implementers register a factory and capability set; the registry resolves nodes to backends at runtime.
- The verification registry (P04) gains a backend matrix entry covering `(plot_type, family, backend, surface)` so each backend's claimed capabilities are exercised.
- The plotter property panel introduces a backend dropdown gated by capability flags; saved projects record the selected backend per node, matching strict-persistence rules from P02.
- Future Rust/C++/wgpu/plotly+QWebEngine backends register through this surface without modifying core plot nodes.
