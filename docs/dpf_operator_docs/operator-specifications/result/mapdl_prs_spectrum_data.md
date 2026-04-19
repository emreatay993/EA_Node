---
category: result
plugin: mapdl
license: None
---

# result:spectrum data

**Version: 0.0.0**

## Description

Read participation factors from prs file.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 3</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | Streams Container (must contain at least one psd file). |
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Data_sources (must contain at least one prs file). |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| participation_factors |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container holding participation factors. |
|  **Pin 1**| mode_coefficients |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container holding mode coefficients. |
|  **Pin 2**| damping_ratios |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container holding damping ratios. |
|  **Pin 3**| global_damping |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container holding for each spectrum: Global Damping Ratio, Damping Stiffness Coefficient & Damping Mass Coefficient. |
|  **Pin 4**| missing_mass |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container holding for each spectrum: Missing Mass Mode (0: None, 1: Active), Missing Mass Effect ZPA. |
|  **Pin 5**| rigid_response |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container holding for each spectrum: Rigid Response Mode (0: None, 1: Gupta, 2: Lindley), Freq Begin (Gupta) / ZPA (Lindley), Freq End (Gupta). |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mapdl::prs::spectrum_data

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mapdl::prs::spectrum_data"); // operator instantiation
op.connect(3, my_streams_container);
op.connect(4, my_data_sources);
ansys::dpf::FieldsContainer my_participation_factors = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::FieldsContainer my_mode_coefficients = op.getOutput<ansys::dpf::FieldsContainer>(1);
ansys::dpf::FieldsContainer my_damping_ratios = op.getOutput<ansys::dpf::FieldsContainer>(2);
ansys::dpf::FieldsContainer my_global_damping = op.getOutput<ansys::dpf::FieldsContainer>(3);
ansys::dpf::FieldsContainer my_missing_mass = op.getOutput<ansys::dpf::FieldsContainer>(4);
ansys::dpf::FieldsContainer my_rigid_response = op.getOutput<ansys::dpf::FieldsContainer>(5);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.streams_container.connect(my_streams_container)
op.inputs.data_sources.connect(my_data_sources)
my_participation_factors = op.outputs.participation_factors()
my_mode_coefficients = op.outputs.mode_coefficients()
my_damping_ratios = op.outputs.damping_ratios()
my_global_damping = op.outputs.global_damping()
my_missing_mass = op.outputs.missing_mass()
my_rigid_response = op.outputs.rigid_response()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.None() # operator instantiation
op.inputs.streams_container.Connect(my_streams_container)
op.inputs.data_sources.Connect(my_data_sources)
my_participation_factors = op.outputs.participation_factors.GetData()
my_mode_coefficients = op.outputs.mode_coefficients.GetData()
my_damping_ratios = op.outputs.damping_ratios.GetData()
my_global_damping = op.outputs.global_damping.GetData()
my_missing_mass = op.outputs.missing_mass.GetData()
my_rigid_response = op.outputs.rigid_response.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.