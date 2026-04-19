---
category: result
plugin: mapdl
license: None
---

# result:psd covariance matrices provider

**Version: 0.0.0**

## Description

Reads covariance matrices from a psd file

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  signif |[`double`](../../core-concepts/dpf-types.md#standard-types) | Default = 0.0001. Any mode combination with a significance level above this value. The significance level is defined as the modal covariance matrix term, divided by the maximum modal covariance matrix term |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Data_sources (must contain at least one psd file). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| rel_rel_displacement |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for displacement mode-mode shapes |
|  **Pin 1**| rel_rel_velocity |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for velocity mode-mode shapes |
|  **Pin 2**| rel_rel_acceleration |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for acceleration mode-mode shapes |
|  **Pin 3**| sta_sta_displacement |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for displacement static-static shapes |
|  **Pin 4**| sta_sta_velocity |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for velocity static-static shapes |
|  **Pin 5**| sta_sta_acceleration |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for acceleration static-static shapes |
|  **Pin 6**| rel_sta_displacement |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for displacement mode-static shapes |
|  **Pin 7**| rel_sta_velocity |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for velocity mode-static shapes |
|  **Pin 8**| rel_sta_acceleration |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | returns the covariance matrix terms for acceleration mode-static shapes |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: psd_covariance_matrices_provider

 **Full name**: result.psd_covariance_matrices_provider

 **Internal name**: psd_matrices_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("psd_matrices_provider"); // operator instantiation
op.connect(0, my_signif);
op.connect(4, my_data_sources);
ansys::dpf::FieldsContainer my_rel_rel_displacement = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::FieldsContainer my_rel_rel_velocity = op.getOutput<ansys::dpf::FieldsContainer>(1);
ansys::dpf::FieldsContainer my_rel_rel_acceleration = op.getOutput<ansys::dpf::FieldsContainer>(2);
ansys::dpf::FieldsContainer my_sta_sta_displacement = op.getOutput<ansys::dpf::FieldsContainer>(3);
ansys::dpf::FieldsContainer my_sta_sta_velocity = op.getOutput<ansys::dpf::FieldsContainer>(4);
ansys::dpf::FieldsContainer my_sta_sta_acceleration = op.getOutput<ansys::dpf::FieldsContainer>(5);
ansys::dpf::FieldsContainer my_rel_sta_displacement = op.getOutput<ansys::dpf::FieldsContainer>(6);
ansys::dpf::FieldsContainer my_rel_sta_velocity = op.getOutput<ansys::dpf::FieldsContainer>(7);
ansys::dpf::FieldsContainer my_rel_sta_acceleration = op.getOutput<ansys::dpf::FieldsContainer>(8);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.psd_covariance_matrices_provider() # operator instantiation
op.inputs.signif.connect(my_signif)
op.inputs.data_sources.connect(my_data_sources)
my_rel_rel_displacement = op.outputs.rel_rel_displacement()
my_rel_rel_velocity = op.outputs.rel_rel_velocity()
my_rel_rel_acceleration = op.outputs.rel_rel_acceleration()
my_sta_sta_displacement = op.outputs.sta_sta_displacement()
my_sta_sta_velocity = op.outputs.sta_sta_velocity()
my_sta_sta_acceleration = op.outputs.sta_sta_acceleration()
my_rel_sta_displacement = op.outputs.rel_sta_displacement()
my_rel_sta_velocity = op.outputs.rel_sta_velocity()
my_rel_sta_acceleration = op.outputs.rel_sta_acceleration()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.psd_covariance_matrices_provider() # operator instantiation
op.inputs.signif.Connect(my_signif)
op.inputs.data_sources.Connect(my_data_sources)
my_rel_rel_displacement = op.outputs.rel_rel_displacement.GetData()
my_rel_rel_velocity = op.outputs.rel_rel_velocity.GetData()
my_rel_rel_acceleration = op.outputs.rel_rel_acceleration.GetData()
my_sta_sta_displacement = op.outputs.sta_sta_displacement.GetData()
my_sta_sta_velocity = op.outputs.sta_sta_velocity.GetData()
my_sta_sta_acceleration = op.outputs.sta_sta_acceleration.GetData()
my_rel_sta_displacement = op.outputs.rel_sta_displacement.GetData()
my_rel_sta_velocity = op.outputs.rel_sta_velocity.GetData()
my_rel_sta_acceleration = op.outputs.rel_sta_acceleration.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.