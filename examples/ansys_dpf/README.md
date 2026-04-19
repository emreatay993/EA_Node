# Ansys DPF examples

Visual reproductions of common `ansys.dpf.core` Python snippets as EA Node Editor projects.

## `displacement_min_max.sfe`

Reproduces this DPF Python workflow as a visual graph:

```python
from ansys.dpf import core as dpf
from ansys.dpf.core import examples

disp_op   = dpf.operators.result.displacement()
max_fc_op = dpf.operators.min_max.min_max_fc(disp_op)

data_src = dpf.DataSources(examples.find_multishells_rst())
# (same idea as the imperative Workflow object — but the graph is the workflow)

# field_min and field_max are the outputs of max_fc_op
```

### How it maps

| Python | Node in the graph |
|---|---|
| `dpf.DataSources(<path>)` | **DPF Data Sources** (`dpf.helper.data_sources.data_sources`) — set the **Result File** property to your `.rst` |
| `dpf.operators.result.displacement()` | **Displacement** (`dpf.op.result.displacement`) |
| `dpf.operators.min_max.min_max_fc(disp_op)` | **Min Max FC** (`dpf.op.min_max.min_max_fc`) |
| Passing `disp_op` into `min_max_fc(...)` | edge from `Displacement.fields_container` → `Min Max FC.fields_container` |
| `disp_op.inputs.data_sources = data_src` | edge from `DPF Data Sources.data_sources` → `Displacement.data_sources` |
| `max_fc_op.outputs.field_min` / `field_max` | the `field_min` / `field_max` output ports on **Min Max FC** |

The **Start** node and exec edges trigger the chain at run time.

> Note: in the editor, the displacement node's *output* is labelled `fields_container_2` because the DPF spec also defines an optional *input* pin with the same name, and the node generator de-collides the keys. The visible label still reads "Fields Container".

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/displacement_min_max.sfe`.
3. Select the **DPF Data Sources** node and edit its **Result File** property — the file ships with the placeholder `C:/path/to/your/file.rst`. Point it at a real `.rst`, e.g. one of the files under `tests/ansys_dpf_core/example_outputs/`.
4. Press **Run**. `field_min` and `field_max` materialise on the **Min Max FC** node.

### Why no explicit `dpf.Workflow()` node

In the imperative Python API you build a `Workflow` object and call `add_operators` / `set_input_name` / `set_output_name` to wire it up. In a node editor, the connections between nodes already encode all of that — the graph **is** the workflow. There's a `DPF Workflow` constructor node available too (under **Workflow → Build**), but it only matters if you want a reusable `dpf.Workflow` *object* to hand to external Python code.

## `stress_x_plus_stress_y_at_node_1.sfe`

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
2. **File → Open** → `examples/ansys_dpf/stress_x_plus_stress_y_at_node_1.sfe`.
3. Select the **DPF Data Sources** node and edit its **Result File** property — the file ships with the placeholder `C:/path/to/your/file.rst`. Point it at a real `.rst`.
4. Press **Run**. The **Add** node's `field` output contains `stress_X + stress_Y` at node 1.

### `ExtAPI` vs. standalone

The Mechanical snippet uses `ExtAPI.DataModel.Project.Model.Analyses[0].ResultFileName` to fetch the result path from the live Mechanical session. The Node Editor runs pyDPF standalone, so you paste the path into the **DPF Data Sources** node once (copy it out of Mechanical, or use any saved `.rst`).

## `modal_superposition.sfe`

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
2. **File → Open** → `examples/ansys_dpf/modal_superposition.sfe`.
3. Edit the **Result File** property on each data-sources node and on the Set-Result-File-Path node to point at your `.rfrq`, `.mode`, and `.rst` files respectively. The file ships with `C:/path/to/your/file.<ext>` placeholders.
4. Press **Run**. The **DPF Viewer** will render the displacement field on the model's mesh.

## `stress_xy_named_selection_add_fc.sfe`

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

This differs from `stress_x_plus_y_on_named_selection.sfe` in three ways: (1) it uses the `on_named_selection` *operator* rather than a `dpf.scoping.mesh` foundational node with `NAMED_SELECTION` mode; (2) it adds a time scoping covering all time sets; (3) it uses `add_fc` (multi-step) instead of `add` (single-field).

### How it maps

| Python | Node in the graph |
|---|---|
| `dpf.DataSources(); SetResultFilePath(...)` | **DPF Data Sources** (`dpf.helper.data_sources.data_sources`) — set the **Result File** property to your `.rst` |
| `dpf.Model(dataSources)` | **DPF Model** (`dpf.helper.model.model`) |
| `time_scoping.Ids = range(1, model.TimeFreqSupport.NumberSets + 1)` | **Scoping On All Time Freqs** (`dpf.helper.time_freq_scoping_factory.scoping_on_all_time_freqs`) — takes the **Model** directly; no need to read `NumberSets` by hand |
| `dpf.operators.scoping.on_named_selection(...)` | **Scoping On Named Selection** (`dpf.op.scoping.on_named_selection`) with properties `Requested Location = Nodal`, `Named Selection Name = NODE1` |
| `dpf.operators.result.stress_X()` / `stress_Y()` | **Stress X** / **Stress Y** (`dpf.op.result.stress_x`, `dpf.op.result.stress_y`) — same lower-cased-type-id note as above |
| `dpf.operators.math.add_fc(sX, sY)` | **Add FC** (`dpf.op.math.add_fc`) — see the limitation note below |

### ⚠ `add_fc` and DPF's variadic pin

DPF's `add_fc` is *variadic*: in raw Python you call `addOp.inputs.fields_container1.Connect(sX)`, `.fields_container2.Connect(sY)`, etc. — all of those bind to the same underlying pin (pin index 0). The DPF specification only declares **one** input pin named `fields_container`, so the editor's auto-generated catalog node also has only one input port. The runtime in [operations.py:64-75](../../ea_node_editor/execution/dpf_runtime/operations.py:64) explicitly rejects multiple edges that bind to the same pin name.

The example wires both `Stress X.fields_container_2` and `Stress Y.fields_container_2` into the single `Add FC.fields_container` port, so the **visual** structure mirrors the snippet — but pressing Run on the Add FC node will currently raise `received multiple explicit values for DPF input pin 'fields_container'`. The Stress X and Stress Y outputs themselves are independently usable.

To make Add FC actually evaluate, you need either:

1. A small extension to [ansys_dpf_operator_catalog.py](../../ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py) + [operations.py](../../ea_node_editor/execution/dpf_runtime/operations.py) that detects DPF variadic (ellipsis) pins and exposes them as numbered ports `fields_container1`, `fields_container2`, … with per-name binding — mirroring `op.inputs.fields_container1.connect(...)` from the native API; **or**
2. A custom 2-input "Add Fields Containers" wrapper plugin node with two distinct input ports, executing `add_fc(a, b)` internally.

Once one of those lands, this example will run end-to-end with no graph changes.

### Using it

1. Open EA Node Editor.
2. **File → Open** → `examples/ansys_dpf/stress_xy_named_selection_add_fc.sfe`.
3. Edit the **DPF Data Sources** node's **Result File** property — point it at a real `.rst`.
4. If your named selection isn't called `NODE1`, edit **Scoping On Named Selection.Named Selection Name**.
5. Press **Run**. Stress X and Stress Y resolve; **Add FC** will fail until the variadic-pin gap is closed (see above).

## `multistage_cyclic_advanced.sfe`

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
2. **File → Open** → `examples/ansys_dpf/multistage_cyclic_advanced.sfe`.
3. The **DPF Data Sources** node ships pre-wired to the bundled `examples/ansys_dpf/multistage.rst` (a copy of the file `ansys.dpf.core.examples.download_multi_stage_cyclic_result()` would fetch). Repoint it if you prefer your own copy.
4. Press **Run**. All 10 operator nodes complete cleanly and the **DPF Viewer** session opens on the selected-sectors expanded mesh with the |U| field applied.

> The bundled `multistage.rst` (~4 MB) is a redistribution of the result file shipped with `pyansys-dpf-core` under its MIT license (see `venv/Lib/site-packages/ansys/dpf/core/examples/result_files/multistage/multistage.rst`).
