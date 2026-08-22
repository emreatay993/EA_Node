# ADR-0007: Plot Data Coupling

- Status: Proposed
- Date: 2026-05-01
- Initiative: [PLOTTER_NODES](../work_packets/plotter_nodes/PLOTTER_NODES_MANIFEST.md)

## 2026-05-23 Direct Tabular Follow-Up

Generic `plot.<type>` nodes now accept `TabularDataRef` and `ArrayDataRef` values in addition to raw lists, arrays, and dict series. The backend contract remains unchanged: plot execution reopens refs through the tabular loader service and materializes them into the existing `x`, `y`, `values`, and point/grid shapes before calling a backend.

Tabular input nodes own durable selection hints (`tabular_selected_columns` for table columns and `array_slice_2d` for dense arrays). Plot nodes own plot-type interpretation plus optional `tabular_mapping` overrides. This keeps the common table-to-plot workflow adapter-free while preserving the separation between generic plot nodes and DPF-typed plot nodes. Plotly/resampler-style downsampling remains future backend work.

## Decision
Plot nodes ship as two parallel families with the same plot-type set:

- `plot.<type>` — generic family. Inputs use `"any"` ports with a documented runtime shape contract (numpy arrays, lists of numbers, dict-of-arrays). Lives under the palette category "Plot".
- `dpf.plot.<type>` — DPF-typed family. Inputs use the existing `dpf_field`, `dpf_fields_container`, `dpf_mesh`, and `dpf_scoping` data types declared in `ea_node_editor/nodes/node_specs.py`. Lives under the palette sub-category "DPF › Plot", matching the `dpf.*` prefix convention already used by `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`.

Polymorphic single-family plot nodes (one node type accepting either generic arrays or DPF objects via `"any"`) are explicitly rejected.

Series composition uses a variadic `series` input port: each connection contributes one curve or point set. Per-connection style (color, label, line / marker) is resolved from the source node's metadata where present and falls back to the plot's color cycle.

## Rationale
- DPF inputs carry structurally different metadata (location, scoping, mesh attachment, time / frequency / mode set association) that drive plot semantics — for example axis labels, default colormap range, and the time-series scrubber. Generic numeric inputs do not carry that metadata. Polymorphic nodes would either ignore DPF metadata (worse UX) or branch on type at runtime (obscures port contracts and complicates verification).
- Two families keep port `data_type` declarations honest: a `dpf.plot.line` declares `dpf_field` / `dpf_fields_container` ports, so connections are validated by the same machinery that already validates `dpf.field_ops` and `dpf.export`.
- The `dpf.*` prefix is an existing user-visible convention; reusing it makes the palette grouping immediately recognizable to users already working with DPF nodes.
- Variadic series ports follow the existing node-graph composition idiom: more series means more connections, not a separate "series builder" intermediate node, and per-connection style fits cleanly into the connection-metadata model.

## Consequences
- The plot node count is two times the plot-type count — for the v1 plot-type set this is 18 node types instead of 9. The trade-off is clearer per-type tests and per-port type validation.
- Documentation must explain the families when adding new plot types so future plot work creates both a `plot.<type>` and a `dpf.plot.<type>` entry by default.
- The variadic series contract requires the registry's port-spec system to support a "variadic" port kind. If the existing port kind set is not yet sufficient, the v1 packet must extend it (recorded as a Required Behavior in the work packet).
- Per-connection style metadata propagates through the canonical action vocabulary (P03) so style edits are first-class graph mutations and survive strict persistence (P02).
