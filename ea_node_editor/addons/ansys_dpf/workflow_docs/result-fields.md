# DPF Result Fields

## Use this when

Extract a result quantity as a reusable DPF Fields Container before viewing, reducing, comparing, or exporting it.

## Required wiring

Connect a DPF Result Source **Model** output to **Model**. Then choose the result type, spatial scope, time scope, and location in the Inspector.

## Defaults

The default quantity is displacement. Spatial scope is the whole model, location stays native, and Time Scope is **First set**. Use **Last set**, **All sets**, **Set IDs**, or **Time values** when the task needs another selection. Set IDs and time values are alternative modes; only the active selector is used.

## Outputs

- **Fields** is always a DPF Fields Container, even when one set is selected.
- **Mesh Scoping** is available when a named selection or explicit entity IDs define the scope.
- **Time Scoping** records the resolved set selection.

## If it fails

Connect **Model** first. For Named Selection, Node IDs, Element IDs, Set IDs, or Time Values modes, provide the corresponding value. If the requested result is unavailable in the file, choose one of the result quantities reported by the file metadata.

## Mini recipe

Connect **DPF Result Source · Model** to **DPF Result Fields · Model**, select Stress and All sets, then connect **Fields** to DPF Table Export or DPF Field Math.
