---
category: None
plugin: core
license: None
---

# +

**Version: 0.0.0**

## Description

Take a list of equation of the form lhs1=rhs1;lhs2=rhs2 and parse it into a workflow.lhs are parsed as workflow's output pins, while symbol used within rhs are parsed as input pins.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  string_equation |[`string`](../../core-concepts/dpf-types.md#standard-types) | set of equation of form lhs=rhs separated by ";".  |
| <strong>Pin 1</strong>|  name_mapping | | map between exposed operators name and dpf operator. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| workflow |[`workflow`](../../core-concepts/dpf-types.md#workflow) |  |
|  **Pin 1**| symbols |[`string`](../../core-concepts/dpf-types.md#standard-types) | list of all input pins of the generated workflow. |
|  **Pin 2**| operators |[`string`](../../core-concepts/dpf-types.md#standard-types) | list of all the operators types used within the workflow. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: native::equation_parser

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("native::equation_parser"); // operator instantiation
op.connect(0, my_string_equation);
op.connect(1, my_name_mapping);
ansys::dpf::Workflow my_workflow = op.getOutput<ansys::dpf::Workflow>(0);
std::string my_symbols = op.getOutput<std::string>(1);
std::string my_operators = op.getOutput<std::string>(2);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.string_equation.connect(my_string_equation)
op.inputs.name_mapping.connect(my_name_mapping)
my_workflow = op.outputs.workflow()
my_symbols = op.outputs.symbols()
my_operators = op.outputs.operators()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.string_equation.Connect(my_string_equation)
op.inputs.name_mapping.Connect(my_name_mapping)
my_workflow = op.outputs.workflow.GetData()
my_symbols = op.outputs.symbols.GetData()
my_operators = op.outputs.operators.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.