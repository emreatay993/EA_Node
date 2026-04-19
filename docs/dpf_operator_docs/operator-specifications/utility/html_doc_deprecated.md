---
category: utility
plugin: core
license: None
---

# utility:html doc deprecated

**Version: 0.0.0**

## Description

Create dpf's html documentation. Deprecated version.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 0</strong>|  output_path |[`string`](../../core-concepts/dpf-types.md#standard-types) |  |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: utility

 **Plugin**: core

 **Scripting name**: html_doc_deprecated

 **Full name**: utility.html_doc_deprecated

 **Internal name**: html_doc_deprecated

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("html_doc_deprecated"); // operator instantiation
op.connect(0, my_output_path);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.utility.html_doc_deprecated() # operator instantiation
op.inputs.output_path.connect(my_output_path)
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.utility.html_doc_deprecated() # operator instantiation
op.inputs.output_path.Connect(my_output_path)
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.