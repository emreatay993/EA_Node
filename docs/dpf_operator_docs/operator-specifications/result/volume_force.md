---
category: result
plugin: mapdl
license: None
---

# result:volume force

**Version: 0.0.0**

## Description

Compute centroid of field1 and field2.fieldOut = fieldIn*(1. - fact) + Field2*(fact)

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  fieldA |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 1</strong>|  fieldB |[`field`](../../core-concepts/dpf-types.md#field) |  |
| <strong>Pin 3</strong>|  int32 |[`int32`](../../core-concepts/dpf-types.md#standard-types), [`double`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| field |[`field`](../../core-concepts/dpf-types.md#field) |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: result

 **Plugin**: mapdl

 **Scripting name**: volume_force

 **Full name**: result.volume_force

 **Internal name**: VolumeForce

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("VolumeForce"); // operator instantiation
op.connect(0, my_fieldA);
op.connect(1, my_fieldB);
op.connect(3, my_int32);
ansys::dpf::Field my_field = op.getOutput<ansys::dpf::Field>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.result.volume_force() # operator instantiation
op.inputs.fieldA.connect(my_fieldA)
op.inputs.fieldB.connect(my_fieldB)
op.inputs.int32.connect(my_int32)
my_field = op.outputs.field()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.result.volume_force() # operator instantiation
op.inputs.fieldA.Connect(my_fieldA)
op.inputs.fieldB.Connect(my_fieldB)
op.inputs.int32.Connect(my_int32)
my_field = op.outputs.field.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.