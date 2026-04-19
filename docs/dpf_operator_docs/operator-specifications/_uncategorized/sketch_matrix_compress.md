---
category: None
plugin: N/A
license: None
---

# sketch_matrix_compress

**Version: 0.0.0**

## Description

Compress fields container using an orthonormal randomized (Gaussian distribution) sketch matrix.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  dataIn |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | Fields container to be compressed. It is assumed that all fields have the same structure (scoping, num_entities). |
| <strong>Pin 1</strong>|  sketch_matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field containing the sketch matrix. |
| <strong>Pin 2</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  rank |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Rank of the output matrix fields_container. |
| <strong>Pin 3</strong>|  random_generator_seed |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Value used as the seed for the random number generator. Default = 0. |
| <strong>Pin 4</strong>|  mean |[`double`](../../core-concepts/dpf-types.md#standard-types) | Mean value of the random numbers matrix. Default = 0.0. |
| <strong>Pin 5</strong>|  standard_deviation |[`double`](../../core-concepts/dpf-types.md#standard-types) | Standard deviation of the random numbers matrix. Default = 1.0. |
| <strong>Pin 6</strong>|  othogonalized |[`bool`](../../core-concepts/dpf-types.md#standard-types) | Orthogonalize matrix. Default = True. |
| <strong>Pin 7</strong>|  power_iterations |[`int32`](../../core-concepts/dpf-types.md#standard-types) | Number of power iterations to perform. A larger number of iterations impact performance, but increase the accuracy. Default = 0. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| dataOut |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | the output matrix is a 'fields_container';                     each field correspond to the multiplication of the sketch matrix by the original fields. |
|  **Pin 1**| sketch_matrix |[`custom_type_field`](../../core-concepts/dpf-types.md#custom-type-field) | Field containing the sketch matrix. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: None

 **Plugin**: N/A

 **Scripting name**: None

 **Full name**: None

 **Internal name**: sketch_matrix_compress

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("sketch_matrix_compress"); // operator instantiation
op.connect(0, my_dataIn);
op.connect(1, my_sketch_matrix);
op.connect(2, my_rank);
op.connect(3, my_random_generator_seed);
op.connect(4, my_mean);
op.connect(5, my_standard_deviation);
op.connect(6, my_othogonalized);
op.connect(7, my_power_iterations);
ansys::dpf::FieldsContainer my_dataOut = op.getOutput<ansys::dpf::FieldsContainer>(0);
ansys::dpf::CustomTypeField my_sketch_matrix = op.getOutput<ansys::dpf::CustomTypeField>(1);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.dataIn.connect(my_dataIn)
op.inputs.sketch_matrix.connect(my_sketch_matrix)
op.inputs.rank.connect(my_rank)
op.inputs.random_generator_seed.connect(my_random_generator_seed)
op.inputs.mean.connect(my_mean)
op.inputs.standard_deviation.connect(my_standard_deviation)
op.inputs.othogonalized.connect(my_othogonalized)
op.inputs.power_iterations.connect(my_power_iterations)
my_dataOut = op.outputs.dataOut()
my_sketch_matrix = op.outputs.sketch_matrix()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.None.None() # operator instantiation
op.inputs.dataIn.Connect(my_dataIn)
op.inputs.sketch_matrix.Connect(my_sketch_matrix)
op.inputs.rank.Connect(my_rank)
op.inputs.random_generator_seed.Connect(my_random_generator_seed)
op.inputs.mean.Connect(my_mean)
op.inputs.standard_deviation.Connect(my_standard_deviation)
op.inputs.othogonalized.Connect(my_othogonalized)
op.inputs.power_iterations.Connect(my_power_iterations)
my_dataOut = op.outputs.dataOut.GetData()
my_sketch_matrix = op.outputs.sketch_matrix.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.