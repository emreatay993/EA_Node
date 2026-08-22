---
category: None
plugin: core
license: any_dpf_supported_increments
---

# volume averaged stress

**Version: 0.0.0**

## Description

Computes averaged volume stress.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 1</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  scoping |[`scoping`](../../core-concepts/dpf-types.md#scoping) |  |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  stress_fields |[`fields_container`](../../core-concepts/dpf-types.md#fields-container), [`field`](../../core-concepts/dpf-types.md#field) | scalar stress field or fields container with only one field is expected |
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  volume_fields |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | field or fields container with only one field is expected |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  volume |[`double`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| stress_volume_fields |[`field`](../../core-concepts/dpf-types.md#field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: volume_averaged_stress

 **Full name**: None

 **Internal name**: volume_stress

 **License**: any_dpf_supported_increments

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("volume_stress"); // operator instantiation
op.connect(1, my_scoping);
op.connect(2, my_stress_fields);
op.connect(3, my_volume_fields);
op.connect(4, my_volume);
ansys::dpf::Field my_stress_volume_fields = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.volume_averaged_stress() # operator instantiation
op.inputs.scoping.connect(my_scoping)
op.inputs.stress_fields.connect(my_stress_fields)
op.inputs.volume_fields.connect(my_volume_fields)
op.inputs.volume.connect(my_volume)
my_stress_volume_fields = op.outputs.stress_volume_fields()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.volume_averaged_stress() # operator instantiation
op.inputs.scoping.Connect(my_scoping)
op.inputs.stress_fields.Connect(my_stress_fields)
op.inputs.volume_fields.Connect(my_volume_fields)
op.inputs.volume.Connect(my_volume)
my_stress_volume_fields = op.outputs.stress_volume_fields.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.