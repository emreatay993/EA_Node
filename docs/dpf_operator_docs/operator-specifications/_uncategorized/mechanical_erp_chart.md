---
category: None
plugin: N/A
license: None
---

# mechanical::erp_chart

**Version: 0.0.0**

## Description

Create erp chart over time

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |
| <strong>Pin 5</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  averaging_type |[`string`](../../core-concepts/dpf-types.md#standard-types) | ERP, ERPL, ERPW, ERPLW |
| <strong>Pin 9</strong>|  calculate_panel_contribution |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Default is false |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| waterfall_table |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |
|  **Pin 1**| panel_contribution_raw |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | One field for each panel containing the raw value at different freq |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: mechanical::erp_chart

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("mechanical::erp_chart"); // operator instantiation
op.connect(0, my_fields_container);
op.connect(5, my_averaging_type);
op.connect(9, my_calculate_panel_contribution);
ansys::dpf::FieldsContainer my_waterfall_table = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::FieldsContainer my_panel_contribution_raw = op.getOutput<ansys::dpf::FieldsContainer>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.fields_container.connect(my_fields_container)
op.inputs.averaging_type.connect(my_averaging_type)
op.inputs.calculate_panel_contribution.connect(my_calculate_panel_contribution)
my_waterfall_table = op.outputs.waterfall_table()
my_panel_contribution_raw = op.outputs.panel_contribution_raw()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.fields_container.Connect(my_fields_container)
op.inputs.averaging_type.Connect(my_averaging_type)
op.inputs.calculate_panel_contribution.Connect(my_calculate_panel_contribution)
my_waterfall_table = op.outputs.waterfall_table.GetData()
my_panel_contribution_raw = op.outputs.panel_contribution_raw.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.