---
category: utility
plugin: core
license: None
---

# utility:merge generic support

**Version: 0.0.0**

## Description

Merges a list of generic supports. For each property, the merge operation is forwarded to the correct merge Operator.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  generic_support |`class dataProcessing::GenericSupport`, `vector<shared_ptr<class dataProcessing::GenericSupport>>` | Either a vector of generic supports or generic supports from pin 0 to ... to merge. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| generic_support |`class dataProcessing::GenericSupport` |  |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: merge_generic_support

 **Full name**: utility.merge_generic_support

 **Internal name**: merge::generic_support

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("merge::generic_support"); // operator instantiation
op.connect(0, my_generic_support);
ansys::dpf::Class Dataprocessing::Genericsupport my_generic_support = op.getOutput<ansys::dpf::Class Dataprocessing::Genericsupport>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.merge_generic_support() # operator instantiation
op.inputs.generic_support1.connect(my_generic_support1)
op.inputs.generic_support2.connect(my_generic_support2)
my_generic_support = op.outputs.generic_support()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.merge_generic_support() # operator instantiation
op.inputs.generic_support.Connect(my_generic_support)
my_generic_support = op.outputs.generic_support.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.