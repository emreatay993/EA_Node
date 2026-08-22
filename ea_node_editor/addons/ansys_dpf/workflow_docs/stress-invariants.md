# DPF Stress Invariants

## Use this when

Extract stress and convert the tensor to von Mises, principal S1/S2/S3, intensity, or maximum shear before viewing, enveloping, comparing, or exporting it.

## Required wiring

Connect a DPF Result Source **Model** output to **Model**. Choose the invariant and any spatial or time scope in the Inspector.

## Defaults

The default invariant is von Mises. Spatial scope is the whole model, location stays native, and Time Scope is **First set**.

## Outputs

- **Fields** is always the derived DPF Fields Container.
- **Mesh Scoping** and **Time Scoping** expose the resolved selections when available.

## If it fails

Connect **Model** and confirm that stress exists in the file. Named Selection, explicit entity, Set IDs, and Time Values modes require matching values. Principal and shear results may be unavailable when the source stress tensor is incomplete at the requested location.

## Mini recipe

Connect DPF Result Source to DPF Stress Invariants, choose von Mises and All sets, then connect **Fields** and the source **Model** to DPF Table Export.
