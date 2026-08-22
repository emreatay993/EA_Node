---
category: metadata
plugin: core
license: None
---

# metadata:csv::stream_provider

**Version: 0.0.0**

## Description

Create CSV streams (cached file handles) from data sources.
Extracts the CSV file path from the input data sources, creates a CSV stream object, and wraps it in a DPF streams container. The stream enables repeated access to the CSV file without re-opening it.
Throws a logic error if the data sources do not contain a file with 'csv' extension.

## Inputs

| Input | Name | Expected type(s) | Description |
|-------|-------|------------------|-------------|
| <strong>Pin 4</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  data_sources |[`data_sources`](../../core-concepts/dpf-types.md#data-sources) | Data sources containing at least one file with 'csv' extension. The CSV file path is retrieved using the 'csv' key. |

## Outputs

| Output |  Name | Expected type(s) | Description |
|-------|------|------------------|-------------|
|  **Pin 0**| streams_container |[`streams_container`](../../core-concepts/dpf-types.md#streams-container) | DPF streams container with a single 'csv' stream pointing to the CSV file from the input data sources. |

## Configurations

| Name| Expected type(s) | Default value | Description |
|-----|------|----------|-------------|
| **mutex** |[`bool`](../../core-concepts/dpf-types.md#standard-types) | false | If this option is set to true, the shared memory is prevented from being simultaneously accessed by multiple threads. |

## Scripting

 **Category**: metadata

 **Plugin**: core

 **Scripting name**: None

 **Full name**: None

 **Internal name**: csv::stream_provider

 **License**: None

## Examples

<details>
<summary>C++</summary>

```cpp
#include "dpf_api.h"

ansys::dpf::Operator op("csv::stream_provider"); // operator instantiation
op.connect(4, my_data_sources);
ansys::dpf::Streams my_streams_container = op.getOutput<ansys::dpf::Streams>(0);
```
</details>

<details>
<summary>CPython</summary>

```python
import ansys.dpf.core as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.data_sources.connect(my_data_sources)
my_streams_container = op.outputs.streams_container()
```
</details>

<details>
<summary>IPython</summary>

```python
import mech_dpf
import Ans.DataProcessing as dpf

op = dpf.operators.metadata.None() # operator instantiation
op.inputs.data_sources.Connect(my_data_sources)
my_streams_container = op.outputs.streams_container.GetData()
```
</details>
<br>

## Changelog

- Version 0.0.0: Initial release.