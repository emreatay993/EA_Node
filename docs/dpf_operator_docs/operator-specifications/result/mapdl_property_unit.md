---
category: result
plugin: mapdl
license: None
---

# result:mapdl property unit

**Version: 0.0.0**

## Description

Read unit from the rst file wrapper for a given property string. The following keys can be used: 
Young's modulus (keys: EX, EY, EZ), Poisson's ratio (keys: NUXY, NUYZ, NUXZ), Shear Modulus (keys: GXY, GYZ, GXZ), 
Coefficient of Thermal Expansion (keys: ALPX, ALPY, ALPZ), Volumic Mass (key: DENS), second Lame's coefficient (key: MU), 
Damping coefficient (key: DAMP), thermal Conductivity (keys: KXX, KYY, KZZ), Resistivity (keys: RSVX, RSVY, RSVZ), 
Specific heat in constant volume (key: C), Film coefficient (key: HF), Viscosity (key: VISC), Emissivity (key: EMIS). 


## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  property_name |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) |  |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| unit |`class dataProcessing::unit::CUnit` |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: mapdl_property_unit

 **Full name**: result.mapdl_property_unit

 **Internal name**: mapdl_property_unit

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl_property_unit"); // operator instantiation
op.connect(0, my_property_name);
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
ansys::dpf::Class Dataprocessing::Unit::Cunit my_unit = op.getOutput<ansys::dpf::Class Dataprocessing::Unit::Cunit>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.mapdl_property_unit() # operator instantiation
op.inputs.property_name.connect(my_property_name)
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_unit = op.outputs.unit()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.mapdl_property_unit() # operator instantiation
op.inputs.property_name.Connect(my_property_name)
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_unit = op.outputs.unit.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.