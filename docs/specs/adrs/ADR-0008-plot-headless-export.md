# ADR-0008: Plot Headless Export

- Status: Proposed
- Date: 2026-05-01
- Initiative: [PLOTTER_NODES](../work_packets/plotter_nodes/PLOTTER_NODES_MANIFEST.md)

## Decision
Plot nodes support **export-only** headless rendering. `execute()` produces static-image and underlying-data export artifacts (PNG / SVG / PDF / CSV / Parquet / HDF5 as the backend supports) with no `QApplication` present, by routing through a backend whose registry capability flags include `static_export` or `data_export` and that is documented as headless-safe (matplotlib Agg by default for 2D; PyVista off-screen for 3D where supported).

Live and embedded surfaces continue to require Qt and are skipped in headless contexts. Cross-backend pixel parity between live and export rendering is not promised; image-snapshot tests target one declared headless-safe backend (matplotlib Agg) only.

## Rationale
- pyqtgraph has no headless mode — it is a Qt widget and cannot render without a `QApplication` and an underlying display surface. A blanket "first-class headless rendering for all backends" requirement would either rule pyqtgraph out as the live 2D backend, or force live and headless paths through different code, breaking pixel parity in either case.
- VTK off-screen rendering on Windows is fragile: OSMesa builds for VTK on Windows are not first-class, and CI runners without GPUs commonly fall back to slow software OpenGL. Promising every 3D backend a no-Qt no-GPU path is more contract surface than the realistic CI need (saving a PNG from a scheduled job) requires.
- Compiled-language backends (Rust / C++ / wgpu) bring their own headless stories (swiftshader, lavapipe, etc.); requiring each backend to ship a no-Qt no-GPU code path discourages backend contributions and complicates the verification registry (P04) matrix.
- Export-only headless covers the actual CI / batch-report use case: a scheduled run produces export artifacts, archived to `ctx.artifact_store`, that downstream tooling consumes. Interactive headless rendering is not required for that workflow.

## Consequences
- Backend capability flags must distinguish `live`, `static_export`, and `data_export` so headless paths can resolve only to backends that are actually safe without Qt.
- The plotter packet's verification suite includes a "headless export" mode that runs `execute()` with `QT_QPA_PLATFORM=offscreen` unset and asserts that export artifacts are produced for a chosen subset of `(plot_type, family)` pairs through matplotlib Agg.
- Image-snapshot tests pin one backend per plot type (the documented headless-safe one) rather than asserting parity across backends.
- The future P11 execution-backends packet may expose this headless export path through the headless runtime API; this ADR does not block that work because the export path is already non-Qt by design.
- A user who wants interactive headless rendering must wait for a future packet that adds backend-specific off-screen support; this is recorded in the v1 packet's Handoff Notes.
