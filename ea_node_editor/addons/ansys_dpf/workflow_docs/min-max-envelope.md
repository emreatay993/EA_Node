# DPF Min/Max Envelope

## Use this when

Find per-entity minima and maxima across several result sets and identify the overall extreme without wiring raw DPF reduction operators.

## Required wiring

Connect a DPF Result Source **Model** output to **Model**. Choose the result quantity and, when needed, a spatial scope.

## Defaults

The default quantity is displacement. Spatial scope is the whole model, location stays native, and Time Scope is **All sets**. Vector results are reduced by magnitude. Reduce stress tensors with DPF Stress Invariants first when a scalar stress measure is required.

## Outputs

- **Envelope Min** and **Envelope Max** are the per-entity envelope fields.
- **Fields** preserves the extracted Fields Container used by the reduction.
- **Per Set Table** contains the extrema for each selected set.
- **Summary** identifies the overall extreme, entity, set, and location when available.

## If it fails

Connect **Model** and check that the selected sets and spatial scope exist. Set IDs and Time Values modes require values. For tensor results, derive a scalar invariant before interpreting a single min/max envelope.

## Mini recipe

Connect DPF Result Source to DPF Min/Max Envelope, keep All sets, choose Displacement, and inspect **Summary** for the governing entity and set.
