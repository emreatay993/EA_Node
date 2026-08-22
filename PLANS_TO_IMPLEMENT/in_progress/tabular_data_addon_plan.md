# Tabular Data Add-On Plan

## Summary
Build a repo-shipped optional `tabular data` app add-on, not a base built-in node. V1 adds one `Tabular Data Input` source node with a `path` input, broad file support, lazy runtime refs, managed cache, and a read-only high-performance fullscreen table/array viewer.

The implementation handoff must start by saving this plan to `PLANS_TO_IMPLEMENT/in_progress/tabular_data_addon_plan.md`, then converting it to work packets with `$subagent-work-packet-planner`, then producing one fresh GPT-5.5 xhigh worker-thread prompt per packet, with each worker doing its own edits and optionally using explorers.

## Key Changes
- Add an in-repo add-on under the existing add-on catalog, dependency-gated behind one `tabular` extra containing `numpy`, `pandas`, `polars`, `pyarrow`, `duckdb`, `openpyxl`, `h5py`, and `tables`.
- Add one `Tabular Data Input` node:
  - `path` input port/property.
  - Output is `TabularDataRef` for tables or `ArrayDataRef` for dense arrays.
  - No eager pandas/polars/numpy output ports in v1.
  - Ref resolver APIs support bounded `numpy`, `pandas`, `polars`, Arrow, rows, schema, preview windows, and array slices for future solvers/visualizers/filters.
- Support broad v1 formats:
  - CSV, TSV, delimited TXT with inference plus overrides for delimiter, encoding, header row, skip rows, and schema/type hints.
  - XLSX/XLSM through workbook/sheet selection.
  - Parquet as the preferred durable table/cache format.
  - HDF5 arrays via `h5py` and HDF5 tables via pandas/PyTables.
  - NPY via NumPy mmap where possible.
  - NPZ as import/export/archive for related arrays, not as the default huge interactive backend.
- Use report-backed backend policy:
  - Parquet + DuckDB/Polars lazy + Arrow for large tables.
  - NPY mmap for dense numeric arrays.
  - pandas only for small compatibility paths, Excel, and explicit bounded materialization.
  - Warn above `1 GiB`; require explicit full materialization above `5 GiB`.
- Use hybrid object selection:
  - Auto-select only when a file contains exactly one usable sheet/key/dataset.
  - For multi-sheet Excel, multi-key NPZ, or multi-dataset HDF5, require and persist the selected object.
- Use app-managed Parquet cache by default, keyed by source path/options/mtime.
- Add explicit "make project-managed" behavior for portability:
  - Default project persistence stores path/options/metadata, not cache data.
  - When requested, copy chosen source data or selected exported/cache artifact into the existing `<project>.data/` sidecar and persist an artifact ref.
- Add read-only native QML fullscreen UI:
  - Virtualized grid with row and column windowing.
  - 50-row inline preview.
  - Fullscreen first paint loads schema plus visible window only.
  - Sort/filter/search/copy/selection and schema sidebar.
  - Multi-dimensional arrays show selectable 2D slices, not full flattening.
- Add warning state UX:
  - Errors keep existing red highlight and focus/zoom behavior.
  - Warnings use golden node border/elapsed-time styling, do not auto-focus/zoom, and write warning text to COREX warning logs.

## Public Interface Changes
- Add the optional repo-local `tabular data` add-on package and dependency extra.
- Add one user-facing `Tabular Data Input` source node with a path input, selector/options properties, lazy `TabularDataRef` or `ArrayDataRef` outputs, and an execution passthrough output.
- Add bounded resolver APIs and read-only fullscreen/inline viewer surfaces that consume refs without eager full-table materialization.
- Add project-managed artifact actions and warning-state/logging behavior without changing `.cxproj` persistence defaults.

## Execution Tasks
- T01: Save this plan to `PLANS_TO_IMPLEMENT/in_progress/tabular_data_addon_plan.md`.
- T02: Use `$subagent-work-packet-planner` to convert it into a packet set.
- T03: Estimate fresh worker-thread count from the generated packets.
- T04: Provide exact copy-paste prompts for one fresh GPT-5.5 xhigh worker thread per packet.
- T05: Stop the planning thread without implementing code.

## Work Packet Conversion Map
- P00 Bootstrap: save the plan, create packet docs, initialize status, and register the packet set.
- P01 Add-on Dependency Contract: add optional add-on shell, dependency gating, install/build declarations, and catalog tests.
- P02 Runtime Refs: add `TabularDataRef` and `ArrayDataRef` contracts plus bounded resolver APIs.
- P03 Loader Cache Service: add format loaders, selector scanning, backend policy, and app-managed cache service.
- P04 Input Node Contract: add the `Tabular Data Input` node descriptor, execution behavior, selector properties, and registry/library tests.
- P05 Project Managed Data: add explicit source/cache portability through the existing artifact sidecar.
- P06 Preview Fullscreen Bridge: add Python bridge/presenter contracts for bounded preview windows and fullscreen payloads.
- P07 QML Table Surface: add native QML virtualized table/array surface and fullscreen UI.
- P08 Warning State Logs: add warning execution/node-chrome UX and COREX warning log routing without focus/zoom.
- P09 Perf Packaging Closeout: add performance gates, package/frozen-build proof, docs/traceability, and final QA evidence.

## Test Plan
- Add unit coverage for add-on catalog loading, missing dependency availability, node descriptor/ports, path property, selector behavior, and registry visibility.
- Add loader/ref tests for CSV/TSV/TXT, XLSX, Parquet, HDF5 arrays/tables, NPY mmap, NPZ key selection/gating, schema inference, bounded previews, and resolver APIs.
- Add persistence tests proving `.cxproj` stores semantic path/options/metadata only, and project-managed data uses the existing `.data` artifact sidecar.
- Add UI/QML tests for graph-surface integration, fullscreen bridge payloads, virtualized row/column windows, warning node state, COREX logs, and no fullscreen state persistence.
- Add performance tests based on the large-memory report: no full materialization for preview, bounded RSS for preview/window fetches, warnings above `1 GiB`, explicit materialization gate above `5 GiB`, and NPZ large-preview gating.

## Assumptions
- V1 is read-only for table editing; save/writeback and formula-like spreadsheet editing are later features.
- Arbitrary pandas pickle input is out of scope for v1 because it is unsafe as a general data import format.
- The named large-memory report exists under `artifacts/tabular_large_memory_benchmark/COMPREHENSIVE_LARGE_MEMORY_REPORT.md` and its findings are authoritative for backend and memory policy.
- Worker threads may use explorer subagents, but each GPT-5.5 worker remains the main code editor for its packet.
