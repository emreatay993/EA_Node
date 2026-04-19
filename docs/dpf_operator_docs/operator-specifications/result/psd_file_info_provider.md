---
category: result
plugin: mapdl
license: None
---

# result:psd file info provider

**Version: 0.0.0**

## Description

Reads information from a psd file

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Data_sources (must contain at least one psd file). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| num_modes |[`int32`](../../core-concepts/dpf-types.md#standard-types) | returns the number of modes selected for evaluation |
|  **Pin 1**| wave_key |[`int32`](../../core-concepts/dpf-types.md#standard-types) | returns the wave key (wave propagation or spatial) |
|  **Pin 2**| num_base |[`int32`](../../core-concepts/dpf-types.md#standard-types) | returns the number of base excitation tables |
|  **Pin 3**| num_psd |[`int32`](../../core-concepts/dpf-types.md#standard-types) | returns the total number of psd tables |
|  **Pin 4**| displacement_key |[`int32`](../../core-concepts/dpf-types.md#standard-types) | returns the displacement key |
|  **Pin 5**| velocity_key |[`int32`](../../core-concepts/dpf-types.md#standard-types) | returns the velocity key |
|  **Pin 6**| acceleration_key |[`int32`](../../core-concepts/dpf-types.md#standard-types) | returns the acceleration key |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: psd_file_info_provider

 **Full name**: result.psd_file_info_provider

 **Internal name**: psd_file_info_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("psd_file_info_provider"); // operator instantiation
op.connect(4, my_data_sources);
int my_num_modes = op.getOutput<int>(0);
int my_wave_key = op.getOutput<int>(1);
int my_num_base = op.getOutput<int>(2);
int my_num_psd = op.getOutput<int>(3);
int my_displacement_key = op.getOutput<int>(4);
int my_velocity_key = op.getOutput<int>(5);
int my_acceleration_key = op.getOutput<int>(6);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.psd_file_info_provider() # operator instantiation
op.inputs.data_sources.connect(my_data_sources)
my_num_modes = op.outputs.num_modes()
my_wave_key = op.outputs.wave_key()
my_num_base = op.outputs.num_base()
my_num_psd = op.outputs.num_psd()
my_displacement_key = op.outputs.displacement_key()
my_velocity_key = op.outputs.velocity_key()
my_acceleration_key = op.outputs.acceleration_key()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.psd_file_info_provider() # operator instantiation
op.inputs.data_sources.Connect(my_data_sources)
my_num_modes = op.outputs.num_modes.GetData()
my_wave_key = op.outputs.wave_key.GetData()
my_num_base = op.outputs.num_base.GetData()
my_num_psd = op.outputs.num_psd.GetData()
my_displacement_key = op.outputs.displacement_key.GetData()
my_velocity_key = op.outputs.velocity_key.GetData()
my_acceleration_key = op.outputs.acceleration_key.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.