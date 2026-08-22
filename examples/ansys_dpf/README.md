# Ansys DPF examples

Visual reproductions of common `ansys.dpf.core` Python snippets as EA Node Editor projects.

## Library layout

The Ansys DPF node library is workflow-first:

* **Ansys DPF → Workflow** — nine curated nodes covering the common post-processing recipes: `DPF Result Source`, `DPF Result Fields`, `DPF Result Viewer`, `DPF Min/Max Envelope`, `DPF Time History Probe`, `DPF Stress Invariants`, `DPF Mode Shape Viewer`, `DPF Field Math`, and `DPF Table Export`.
* **Ansys DPF → Helpers / Viewer / Plot / Inputs** — scoping helpers, the data-sources chain (for multi-file workflows like modal superposition), the standalone viewer, and the typed plot nodes.
* **Ansys DPF → Advanced → Raw API Mirror → \<Family\>** — every auto-generated `dpf.op.*` operator mirror, one category per DPF family (Result, Math, Min Max, …).
* **Ansys DPF → Advanced → Building Blocks** — the atomic `dpf.result_file`, `dpf.model`, and `dpf.mesh_extract` nodes whose jobs the curated Workflow nodes already cover.

Reach for a Workflow node first; drop down to the Raw API Mirror when you need an operator the curated set does not wrap. Both tiers mix freely in one graph (see `stress_xy_named_selection_add_fc.cxproj`).

## `displacement_min_max.cxproj`

The classic "min/max of a result over time" question as a two-node graph:

```python
from ansys.dpf import core as dpf

model = dpf.Model("<path>.rst")
disp  = model.results.displacement.on_all_time_freqs().eval()
# norm-reduce, then per-entity envelope over sets + per-set and overall extremes
```

### How it maps

| Python | Node in the graph |
|---|---|
| `dpf.Model(<path>)` | **DPF Result Source** (`dpf.workflow.result_source`) — ships pointed at the bundled bolted-joint fixture |
| everything else | **DPF Min/Max Envelope** (`dpf.workflow.min_max_envelope`) with **Result Type** = `displacement` and an empty time selection (= all sets) |

Outputs on the envelope node:

* `envelope_min` / `envelope_max` — per-node min/max fields over all sets, viewer-ready.
* `per_set_table` — one row per set: min/max value plus the node id where it occurs.
* `summary` — the overall extremes, each with value, node id, set, time, and nodal coordinates.

Vector results are norm-reduced automatically; for stress tensors, derive an invariant first with **DPF Stress Invariants** and chain its `fields` output into other consumers.

> Earlier revisions of this example wired the raw `dpf.op.result.displacement` mirror into `dpf.op.min_max.min_max_fc`, which could never run: `min_max_fc` uses a variadic DPF pin that graph edges cannot bind. The curated node performs the reduction in-process, so the graph now executes end to end.

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/displacement_min_max.cxproj`.
3. Press **Run** — the project ships pointed at the bundled bolted-joint fixture. Repoint **DPF Result Source.Result File** at your own `.rst` to reuse the recipe.

### Why no explicit `dpf.Workflow()` node

In the imperative Python API you build a `Workflow` object and call `add_operators` / `set_input_name` / `set_output_name` to wire it up. In a node editor, the connections between nodes already encode all of that — the graph **is** the workflow. There's a `DPF Workflow` constructor node available too (under **Workflow → Build**), but it only matters if you want a reusable `dpf.Workflow` *object* to hand to external Python code.

## `stress_x_plus_stress_y_at_node_1.cxproj`

Reproduces this Mechanical IronPython snippet as a visual graph:

```python
import mech_dpf
import Ans.DataProcessing as dpf
mech_dpf.setExtAPI(ExtAPI)

analysis = ExtAPI.DataModel.Project.Model.Analyses[0]
dataSources = dpf.DataSources()
dataSources.SetResultFilePath(analysis.ResultFileName)

scoping = dpf.Scoping()
scoping.Ids = [1]
scoping.Location = 'Nodal'

stressXOp = dpf.operators.result.stress_X()
stressXOp.inputs.data_sources.Connect(dataSources)
stressXOp.inputs.mesh_scoping.Connect(scoping)
sX = stressXOp.outputs.fields_container.GetData()

stressYOp = dpf.operators.result.stress_Y()
stressYOp.inputs.data_sources.Connect(dataSources)
stressYOp.inputs.mesh_scoping.Connect(scoping)
sY = stressYOp.outputs.fields_container.GetData()

addOp = dpf.operators.math.add()
addOp.inputs.fieldA.Connect(sX)
addOp.inputs.fieldB.Connect(sY)
addSxSy = addOp.outputs.field.GetData()
print(addSxSy.Data)
```

### How it maps

| Python | Node in the graph |
|---|---|
| `dpf.DataSources(); SetResultFilePath(...)` | **DPF Data Sources** (`dpf.helper.data_sources.data_sources`) — set the **Result File** property to your `.rst` |
| `scoping.Ids = [1]; scoping.Location = 'Nodal'` | **DPF Mesh Scoping** (`dpf.scoping.mesh`) with `Selection Mode = Node IDs`, `Node IDs = 1`, `Location = Nodal` |
| `dpf.operators.result.stress_X()` / `stress_Y()` | **Stress X** / **Stress Y** (`dpf.op.result.stress_x`, `dpf.op.result.stress_y` — note the type_id is lower-cased even though the DPF Python class keeps `stress_X`) |
| `.inputs.data_sources.Connect(dataSources)` | edge from `DPF Data Sources.data_sources` → `Stress X/Y.data_sources` |
| `.inputs.mesh_scoping.Connect(scoping)` | edge from `DPF Mesh Scoping.scoping` → `Stress X/Y.mesh_scoping` |
| `addOp.inputs.fieldA / fieldB.Connect(...)` | **Add** (`dpf.op.math.add`) with edges from `Stress X.fields_container_2` → `Add.fielda` and `Stress Y.fields_container_2` → `Add.fieldb` |
| `addOp.outputs.field.GetData()` | the `field` output port on **Add** — wire it to a **DPF Viewer** or **DPF Export** node to see / persist the result |

As with the displacement example, the stress output ports are labelled `fields_container_2` because the DPF spec also defines an optional *input* pin named `fields_container`; the visible label on the port still reads "Fields Container".

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/stress_x_plus_stress_y_at_node_1.cxproj`.
3. Select the **DPF Data Sources** node and edit its **Result File** property — the file ships with the placeholder `C:/path/to/your/file.rst`. Point it at a real `.rst`.
4. Press **Run**. The **Add** node's `field` output contains `stress_X + stress_Y` at node 1.

### `ExtAPI` vs. standalone

The Mechanical snippet uses `ExtAPI.DataModel.Project.Model.Analyses[0].ResultFileName` to fetch the result path from the live Mechanical session. The Node Editor runs pyDPF standalone, so you paste the path into the **DPF Data Sources** node once (copy it out of Mechanical, or use any saved `.rst`).

## `modal_superposition.cxproj`

Reproduces the [PyDPF-Core modal-superposition harmonic-analysis example](https://dpf.docs.pyansys.com/version/stable/examples/03-harmonic_analyses/01-modal_superposition.html) as a visual graph:

```python
from ansys.dpf import core as dpf
from ansys.dpf.core import examples

msup_files = examples.download_msup_files_to_dict()
data_sources           = dpf.DataSources(msup_files["rfrq"])
up_stream_data_sources = dpf.DataSources(msup_files["mode"])
up_stream_data_sources.add_file_path(msup_files["rst"])
data_sources.add_upstream(up_stream_data_sources)

model = dpf.Model(data_sources)
disp  = model.results.displacement.on_all_time_freqs.eval()

freq_scoping = disp.get_time_scoping()
for freq_set in freq_scoping:
    model.metadata.meshed_region.plot(disp.get_field_by_time_complex_ids(freq_set, 0))
```

### How it maps

| Python | Node in the graph |
|---|---|
| `dpf.DataSources(msup_files["rfrq"])` | **DPF Data Sources (rfrq)** (`dpf.helper.data_sources.data_sources`) — set the **Result File** property to your `.rfrq` |
| `dpf.DataSources(msup_files["mode"])` | **DPF Data Sources (upstream mode)** (`dpf.helper.data_sources.data_sources`) — set the **Result File** property to your `.mode` |
| `up_stream_data_sources.add_file_path(msup_files["rst"])` | **DPF Set Result File Path** (`dpf.helper.data_sources.set_result_file_path`) with **Result File** = `.rst` and **Key** = `rst`, receiver wired from the upstream data sources |
| `data_sources.add_upstream(up_stream_data_sources)` | **DPF Add Upstream Data Sources** (`dpf.helper.data_sources.add_upstream`) — `receiver` ← primary data sources, `upstream_data_sources` ← `DPF Set Result File Path.updated_receiver`; the node's `updated_receiver` port carries the *chained* primary DS downstream |
| `dpf.Model(data_sources)` | **DPF Model** (`dpf.helper.model.model`) — `data_sources` ← **DPF Add Upstream Data Sources.updated_receiver** (so the upstream chain reaches the solver) |
| `disp.get_time_scoping()` / `.on_all_time_freqs` | **All Time Freq Scoping** (`dpf.helper.time_freq_scoping_factory.scoping_on_all_time_freqs`) — `obj` ← `Model.model` |
| `model.results.displacement.on_all_time_freqs.eval()` | **Displacement** (`dpf.op.result.displacement`) — `data_sources` ← **DPF Add Upstream Data Sources.updated_receiver**, `time_scoping` ← **All Time Freq Scoping** |
| `model.metadata.meshed_region.plot(disp.get_field_by_time_complex_ids(freq_set, 0))` | **DPF Viewer** (`dpf.viewer`) — `field` ← `Displacement.fields_container_2`, `model` ← `Model.model` |

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/modal_superposition.cxproj`.
3. Edit the **Result File** property on each data-sources node and on the Set-Result-File-Path node to point at your `.rfrq`, `.mode`, and `.rst` files respectively. The file ships with `C:/path/to/your/file.<ext>` placeholders.
4. Press **Run**. The **DPF Viewer** will render the displacement field on the model's mesh.

## `named_selection_time_result_viewer.cxproj`

A small runnable viewer workflow for the common question: show one result type, on one named selection, at one result time.

It ships pointed at the repo's bolted-joint fixture:

```text
../../tests/ansys_dpf_core/example_outputs/static_analysis_1_bolted_joint/file.rst
```

The default graph renders **displacement** on named selection `BOLT_NODES` at time value `2.0` in the embedded **DPF Viewer**.

### How it maps

| Goal | Node in the graph |
|---|---|
| Pick the `.rst` / `.rth` file | **DPF Result File** (`dpf.result_file`) with **Result File** = `../../tests/ansys_dpf_core/example_outputs/static_analysis_1_bolted_joint/file.rst` |
| Build the loaded DPF model | **DPF Model** (`dpf.model`) from the result-file handle |
| Scope to a named selection | **DPF Mesh Scoping** (`dpf.scoping.mesh`) with **Selection Mode** = `named_selection`, **Named Selection** = `BOLT_NODES` |
| Pick the result and time | **DPF Result Field** (`dpf.result_field`) with **Result Name** = `displacement`, **Time Values** = `2.0`; use **Set IDs** instead if you prefer DPF set ids |
| Keep the displayed mesh scoped to the same selection | **DPF Mesh Extract** (`dpf.mesh_extract`) receives the same mesh scoping |
| Show the result interactively | **DPF Viewer** (`dpf.viewer`) receives the field, model, and scoped mesh |

### Using it

1. Open EA Node Editor from the repo root.
2. **File > Open** > `examples/ansys_dpf/named_selection_time_result_viewer.cxproj`.
3. To use your own solve, edit **DPF Result File.Result File** to your `.rst` or `.rth`.
4. Edit **DPF Mesh Scoping.Named Selection**, **DPF Result Field.Result Name**, and **DPF Result Field.Time Values**. If you choose **Set IDs** instead, leave **Time Values** blank.
5. Press **Run**. The **DPF Viewer** renders the scoped result.

## `curated_result_viewer.cxproj`

A smaller version of the same viewer workflow using the curated **DPF Result Viewer** node.
It keeps file loading, result type, named-selection scoping, time scoping, and viewer launch on one node.

It ships pointed at the same bolted-joint fixture:

```text
../../tests/ansys_dpf_core/example_outputs/static_analysis_1_bolted_joint/file.rst
```

The default graph renders **displacement** on named selection `BOLT_NODES` at time value `2.0`, with mesh edges enabled in the embedded viewer.

### How it maps

| Goal | Node in the graph |
|---|---|
| Pick the `.rst` / `.rth` file | **DPF Result Viewer** (`dpf.workflow.result_viewer`) with **Result File** set to the fixture path |
| Pick the result and time | Same node, **Result Type** = `displacement`, **Time Scope** = `time_values`, **Time Values** = `2.0` |
| Scope to a named selection | Same node, **Scoping** = `named_selection`, **Named Selection** = `BOLT_NODES`, **Location** = `nodal` |
| Show the result interactively | Same node opens the embedded **DPF Viewer** and emits `session`, stable `fields`, scoping handles, and model/file handles |

### Using it

1. Open EA Node Editor from the repo root.
2. **File > Open** > `examples/ansys_dpf/curated_result_viewer.cxproj`.
3. To use your own solve, edit **DPF Result Viewer.Result File** to your `.rst` or `.rth`.
4. Edit **Result Type**, **Scoping**, **Named Selection**, and **Time Scope**; fill **Time Values** or **Set IDs** only when that mode is selected.
5. Press **Run**. The curated node loads the model, extracts the result fields, and opens the viewer.

## `stress_xy_named_selection_add_fc.cxproj`

A more faithful 1:1 reproduction of the Mechanical (`mech_dpf` / `Ans.DataProcessing`) snippet — Stress X + Stress Y, scoped on the `NODE1` named selection via the `on_named_selection` operator, across **all time sets**, summed via `add_fc`:

```python
import mech_dpf
import Ans.DataProcessing as dpf
mech_dpf.setExtAPI(ExtAPI)

analysis = ExtAPI.DataModel.Project.Model.Analyses[0]
dataSources = dpf.DataSources()
dataSources.SetResultFilePath(analysis.ResultFileName)

model = dpf.Model(dataSources)

time_scoping = dpf.Scoping()
time_scoping.Ids = range(1, model.TimeFreqSupport.NumberSets + 1)

scoping_on_ns = dpf.operators.scoping.on_named_selection()
scoping_on_ns.inputs.requested_location.Connect('Nodal')
scoping_on_ns.inputs.named_selection_name.Connect('NODE1')
scoping_on_ns.inputs.data_sources.Connect(dataSources)
my_mesh_scoping = scoping_on_ns.outputs.mesh_scoping.GetData()

stressXOp = dpf.operators.result.stress_X()
stressXOp.inputs.data_sources.Connect(dataSources)
stressXOp.inputs.mesh_scoping.Connect(my_mesh_scoping)
stressXOp.inputs.time_scoping.Connect(time_scoping)
sX = stressXOp.outputs.fields_container.GetData()

stressYOp = dpf.operators.result.stress_Y()
stressYOp.inputs.data_sources.Connect(dataSources)
stressYOp.inputs.mesh_scoping.Connect(my_mesh_scoping)
stressYOp.inputs.time_scoping.Connect(time_scoping)
sY = stressYOp.outputs.fields_container.GetData()

addOp = dpf.operators.math.add_fc()
addOp.inputs.fields_container1.Connect(sX)
addOp.inputs.fields_container2.Connect(sY)
addSxSy = addOp.outputs.fields_container.GetData()
```

This differs from `stress_x_plus_y_on_named_selection.cxproj` in three ways: (1) it uses the `on_named_selection` *operator* rather than a `dpf.scoping.mesh` foundational node with `NAMED_SELECTION` mode; (2) it adds a time scoping covering all time sets; (3) it uses `add_fc` (multi-step) instead of `add` (single-field).

### How it maps

| Python | Node in the graph |
|---|---|
| `dpf.DataSources(); SetResultFilePath(...)` | **DPF Data Sources** (`dpf.helper.data_sources.data_sources`) — set the **Result File** property to your `.rst` |
| `dpf.Model(dataSources)` | **DPF Model** (`dpf.helper.model.model`) |
| `time_scoping.Ids = range(1, model.TimeFreqSupport.NumberSets + 1)` | **Scoping On All Time Freqs** (`dpf.helper.time_freq_scoping_factory.scoping_on_all_time_freqs`) — takes the **Model** directly; no need to read `NumberSets` by hand |
| `dpf.operators.scoping.on_named_selection(...)` | **Scoping On Named Selection** (`dpf.op.scoping.on_named_selection`) with properties `Requested Location = Nodal`, `Named Selection Name = NODE1` |
| `dpf.operators.result.stress_X()` / `stress_Y()` | **Stress X** / **Stress Y** (`dpf.op.result.stress_x`, `dpf.op.result.stress_y`) — same lower-cased-type-id note as above |
| `dpf.operators.math.add_fc(sX, sY)` | **DPF Field Math** (`dpf.workflow.field_math`) with **Operation** = `add`, inputs `A` ← Stress X, `B` ← Stress Y |

### `add_fc` and DPF's variadic pin — solved by DPF Field Math

DPF's `add_fc` is *variadic*: in raw Python you call `addOp.inputs.fields_container1.Connect(sX)`, `.fields_container2.Connect(sY)`, etc. — all of those bind to the same underlying pin (pin index 0). The DPF specification only declares **one** input pin named `fields_container`, so the auto-generated `dpf.op.math.add_fc` mirror also has only one input port, and the runtime rejects two edges into the same pin.

The curated **DPF Field Math** node closes that gap: it exposes two distinct `A` / `B` ports (each accepting a `dpf.field` or `dpf.fields_container`) and binds `fields_container1` / `fields_container2` in-process. It also covers `subtract`, component-wise `multiply` / `divide`, and `scale` by a constant — the usual load-case combination toolkit.

This example intentionally keeps the raw-mirror extraction chain (`dpf.op.result.stress_x` / `stress_y` under **Advanced → Raw API Mirror**) and finishes with the Workflow-tier Field Math node, showing how the two tiers mix in one graph.

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/stress_xy_named_selection_add_fc.cxproj`.
3. Press **Run** — the project ships pointed at the bundled bolted-joint fixture (named selection `NODE1`). Repoint the **DPF Data Sources** node's **Result File** and the named selection to reuse the recipe.
4. The **DPF Field Math** node's `fields` output carries `stress_X + stress_Y` on the named selection across all time sets.

## `multistage_cyclic_advanced.cxproj`

Reproduces the PyAnsys DPF tutorial [*Multi-stage Cyclic Symmetry - Advanced Options*](https://dpf.docs.pyansys.com/version/stable/examples/04-advanced/00-multistage_advanced_options.html) as a visual graph:

```python
from ansys.dpf import core as dpf
from ansys.dpf.core import examples, operators as ops

cyc   = examples.download_multi_stage_cyclic_result()
model = dpf.Model(cyc)

# Expand displacement on selected sectors with read_cyclic=2
UCyc = dpf.operators.result.displacement()
UCyc.inputs.data_sources(model.metadata.data_sources)
UCyc.inputs.sectors_to_expand([0, 1, 2])
UCyc.inputs.read_cyclic(2)

# Total deformation (|U|)
nrm = dpf.Operator("norm_fc")
nrm.inputs.connect(UCyc.outputs)
fields = nrm.outputs.fields_container()

# Fully-expanded mesh (whole model)
mesh_provider = model.metadata.mesh_provider
mesh_provider.inputs.read_cyclic(2)
mesh = mesh_provider.outputs.mesh()

# Selected-sectors expanded mesh (alternative expansion path)
cyc_support_provider = ops.metadata.cyclic_support_provider(
    data_sources=model.metadata.data_sources
)
cyc_support_provider.inputs.sectors_to_expand(<scoping of sector ids>)
mesh_exp = ops.metadata.cyclic_mesh_expansion(cyclic_support=cyc_support_provider)
selected_sectors_mesh = mesh_exp.outputs.meshed_region()
```

### How it maps

| Python | Node in the graph |
|---|---|
| `examples.download_multi_stage_cyclic_result()` | **DPF Data Sources** (`dpf.helper.data_sources.data_sources`) — pre-pointed at the bundled `examples/ansys_dpf/multistage.rst` |
| `dpf.Model(cyc)` | **DPF Model** (`dpf.helper.model.model`) — feeds the viewer |
| `[0, 1, 2]` sector list | **Sectors Scoping** (`dpf.scoping.mesh`) with `Selection Mode = Node IDs`, `Node IDs = "0, 1, 2"` |
| `dpf.operators.result.displacement()` + `read_cyclic(2)` + `sectors_to_expand(...)` | **Displacement (cyclic expansion)** (`dpf.op.result.displacement`), `read_cyclic = 2`, sectors wired from the **Sectors Scoping** node |
| `dpf.Operator("norm_fc")` chained to displacement | **Norm Fields Container** (`dpf.op.math.norm_fc`), `scalar_int = 2` (L2 norm) |
| single-field unwrap (viewer needs a `dpf.field`, not a container) | **Extract Field** (`dpf.op.utility.extract_field`) — fields container → single field |
| `ops.metadata.cyclic_support_provider(...)` + `sectors_to_expand(...)` | **Cyclic Support Provider** (`dpf.op.metadata.cyclic_support_provider`), fed by the sectors scoping |
| `ops.metadata.cyclic_mesh_expansion(cyclic_support=...)` | **Cyclic Mesh Expansion** (`dpf.op.metadata.cyclic_mesh_expansion`), fed by the support provider |
| `mesh.plot(fields)` / `selected_sectors_mesh.plot(fields)` | **DPF Viewer** (`dpf.viewer`) — `field` ← Extract Field, `model` ← DPF Model, `mesh` ← Cyclic Mesh Expansion |

The **DPF Viewer** renders the total deformation (|U|) on the expanded selected-sectors mesh. The **Cyclic Mesh Expansion**'s `meshed_region` output is also available independently if you want to branch off another consumer.

### Things that don't translate 1:1

* The tutorial's *per-stage* variant uses `dpf.ScopingsContainer` with one `Scoping` per stage. There's no dedicated `ScopingsContainer` builder node in the catalog, so the graph uses a single `dpf.Scoping` of sector ids applied to both the support provider and the displacement operator. If you need per-stage selection, drive `sectors_to_expand` from Python instead.
* The pure-inspection blocks (`print(result_info)`, `cyc_support.base_nodes_scoping(0)`, `cyc_support.expand_node_id(...)`) have no graph equivalent — they're `print` calls, not operators in the DPF graph.
* The tutorial also calls `mesh = model.metadata.mesh_provider.outputs.mesh()` for the fully-expanded whole-model mesh. The generated `dpf.op.mesh.mesh_provider` node has a `time_scoping` property that currently can't be bound unless explicitly connected, so the whole-model-mesh branch is omitted here — the viewer uses the selected-sectors expanded mesh from **Cyclic Mesh Expansion** instead (equivalent to the tutorial's second `plot(...)` call).

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/multistage_cyclic_advanced.cxproj`.
3. The **DPF Data Sources** node ships pre-wired to the bundled `examples/ansys_dpf/multistage.rst` (a copy of the file `ansys.dpf.core.examples.download_multi_stage_cyclic_result()` would fetch). Repoint it if you prefer your own copy.
4. Press **Run**. All 10 operator nodes complete cleanly and the **DPF Viewer** session opens on the selected-sectors expanded mesh with the |U| field applied.

> The bundled `multistage.rst` (~4 MB) is a redistribution of the result file shipped with `pyansys-dpf-core` under its MIT license (see `venv/Lib/site-packages/ansys/dpf/core/examples/result_files/multistage/multistage.rst`).

## `mode_shape_viewer.cxproj`

Opens a modal result, extracts one mode shape, reports its natural frequency, and renders it in the embedded viewer — one node:

```python
from ansys.dpf import core as dpf

model = dpf.Model("<modal>.rst")
disp  = model.results.displacement.on_time_scoping(
    dpf.Scoping(ids=[2], location=dpf.locations.time_freq)).eval()
freq  = model.metadata.time_freq_support.time_frequencies.data[1]
```

### How it maps

| Goal | Node in the graph |
|---|---|
| Pick the modal `.rst` and mode | **DPF Mode Shape Viewer** (`dpf.workflow.mode_shape_viewer`) — **Result File** = the bundled modal bolted-joint fixture, **Mode** = `2` |
| Read the natural frequency | the node's `frequency` output (Hz for a modal file) |
| Show the mode shape | the same node opens the embedded **DPF Viewer** session |

Once a modal file is selected, the **Mode** dropdown lists every available mode. Scoping (named selection / node ids) is optional and defaults to the whole model.

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/mode_shape_viewer.cxproj`.
3. Press **Run** — the viewer opens on mode 2 (~2241 Hz for the bundled fixture). Change **Mode** and re-run to step through the modes.

## `time_history_probe_line_plot.cxproj`

Probes a result at a named selection across all result sets and plots one curve per node with real time values on the X axis:

```python
ns   = model.metadata.named_selection("BOLT_NODES")
disp = model.results.displacement.on_all_time_freqs()
disp.inputs.mesh_scoping(ns)
# transpose per-set fields into one curve per probed node
```

### How it maps

| Goal | Node in the graph |
|---|---|
| Load the result file | **DPF Result Source** (`dpf.workflow.result_source`) |
| Probe the named selection over time | **DPF Time History Probe** (`dpf.workflow.time_history_probe`) — **Scoping** = `named_selection`, **Named Selection** = `BOLT_NODES`, **Time Scope** = `all_sets` |
| Plot the curves | **DPF Line Plot** (`dpf.plot.line`) — `series` ← the probe's `series` output |

The probe's `series` output carries one curve per probed entity with `x_axis = time` metadata, so the plot's X axis shows real time/frequency values instead of set ids. The probe also emits a long-form `table` (set, time, entity, value) and the resolved `time_values`.

> **Frame Selector matters:** the plot's **Frame Selector** ships as `all` in this example so every probed node draws its own curve. The plot-node default of `1` would show only the first curve.

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/time_history_probe_line_plot.cxproj`.
3. Press **Run** — one displacement-magnitude curve per `BOLT_NODES` node appears in the line plot. Swap **Result Type** or the named selection to reuse the recipe.

## `stress_invariants_table_export.cxproj`

Derives von Mises stress at a named selection over selected sets and stages it as a CSV table with node ids and coordinates:

```python
stress = model.results.stress(...BOLT_NODES..., sets=[1, 2]).eval()
vm     = dpf.operators.invariant.von_mises_eqv_fc(stress)
# tabulate: node id, x/y/z, set, time, value -> CSV
```

### How it maps

| Goal | Node in the graph |
|---|---|
| Load the result file | **DPF Result Source** (`dpf.workflow.result_source`) |
| Extract stress and derive the invariant | **DPF Stress Invariants** (`dpf.workflow.stress_invariants`) — **Invariant** = `von_mises`, **Location** = `nodal`, **Named Selection** = `BOLT_NODES`, **Time Scope** = `set_ids`, **Set IDs** = `1,2` |
| Tabulate and stage the CSV | **DPF Table Export** (`dpf.workflow.table_export`) — `fields` ← the invariants node, `model` ← the source |

The invariant selector also offers principal `S1`/`S2`/`S3` (descending, `S1 ≥ S2 ≥ S3`), `intensity` (`S1 − S3`), and `max_shear` (`intensity / 2`). Table Export writes one row per node and set — `entity_id, x, y, z, set_id, time_value, value` — and stages the CSV in the project artifact store; its `table` output carries the same rows in-memory.

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/stress_invariants_table_export.cxproj`.
3. Press **Run**. The staged CSV path is on the **DPF Table Export** node's `csv` output; the `table` output holds the rows for downstream nodes.
