---
category: result
plugin: mapdl
license: None
---

# result:mapdl::filter_mesh

**Version: 0.0.0**

## Description

Filter MAPDL mesh degenerated elements.
This operator will recreate the mesh with the following property fields assigned for the supported elements:
  - connectivity: The connectivity without duplicate nodes of degenerated elements
  - eltype: The resulting element type (the original eltype is ignored)
  - elprops: The element properties bitfield (the original elprops is ignored)
  - degenerated_connectivity: The original connectivity
  - apdl_element_type: The MAPDL routine number
  
The unsupported elements are skipped and will be assigned to a property field "unsupported_apdl_element_type".

The other elemental properties will be forwarded for supported elements.

It needs the following property fields on the input mesh:
  - apdl_tshape
  - mapdl_element_type_id
  - section

It also requires the element_types_provider operator implemented on the data source.


## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  abstract_meshed_region |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |
| <strong>Pin 3</strong>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container), `stream` |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| abstract_meshed_region |[`abstract_meshed_region`](../../core-concepts/dpf-types.md#meshed-region) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::filter_mesh

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::filter_mesh"); // operator instantiation
op.connect(0, my_abstract_meshed_region);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
ansys::dpf::MeshedRegion my_abstract_meshed_region = op.getOutput<ansys::dpf::MeshedRegion>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.abstract_meshed_region.connect(my_abstract_meshed_region)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_abstract_meshed_region = op.outputs.abstract_meshed_region()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.abstract_meshed_region.Connect(my_abstract_meshed_region)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_abstract_meshed_region = op.outputs.abstract_meshed_region.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.