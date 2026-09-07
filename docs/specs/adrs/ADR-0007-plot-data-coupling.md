# ADR-0007: Plot Data Coupling

- Status: Proposed
- Date: 2026-05-01
- Initiative: [PLOTTER_NODES](../work_packets/plotter_nodes/PLOTTER_NODES_MANIFEST.md)

## 2026-05-23 Direct Tabular Follow-Up

Generic `plot.<type>` nodes now accept `TabularDataRef` and `ArrayDataRef` values in addition to raw lists, arrays, and dict series. The backend contract remains unchanged: plot execution reopens refs through the tabular loader service and materializes them into the existing `x`, `y`, `values`, and point/grid shapes before calling a backend.

Tabular input nodes own durable selection hints (`tabular_selected_columns` for table columns and `array_slice_2d` for dense arrays). Plot nodes own plot-type interpretation plus optional `tabular_mapping` overrides. This keeps the common table-to-plot workflow adapter-free. Plotly/resampler-style downsampling remains future backend work.

## Decision
Plot nodes ship as the `plot.<type>` generic family under the palette category "Plot". Inputs use the documented runtime shape contract for arrays, lists of numbers, dictionary series, and supported compact tabular/array refs.

Series composition uses a variadic `series` input port: each connection contributes one curve or point set. Per-connection style (color, label, line / marker) is resolved from the source node's metadata where present and falls back to the plot's color cycle.

## Rationale
- Generic plot inputs are normalized into one backend request shape before rendering, keeping backend contracts independent of source adapters.
- Variadic series ports follow the existing node-graph composition idiom: more series means more connections, not a separate "series builder" intermediate node, and per-connection style fits cleanly into the connection-metadata model.

## Consequences
- New plot types extend only the generic family and its backend normalization contract.
- The variadic series contract requires the registry's port-spec system to support a "variadic" port kind. If the existing port kind set is not yet sufficient, the v1 packet must extend it (recorded as a Required Behavior in the work packet).
- Per-connection style metadata propagates through the canonical action vocabulary (P03) so style edits are first-class graph mutations and survive strict persistence (P02).
