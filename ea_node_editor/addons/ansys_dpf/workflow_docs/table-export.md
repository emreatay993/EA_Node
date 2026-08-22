# DPF Table Export

## Use this when

Turn a DPF result into rows for inspection or CSV export, including entity, set, time, components, magnitude, and optional nodal coordinates.

## Required wiring

Connect a DPF Field or Fields Container to **Fields** and the matching DPF model to **Model**. Both inputs are required so entity and coordinate information can be resolved consistently.

## Defaults

Include Coordinates is on, Artifact Key is generated when blank, and Output Mode is **Stored** so a CSV artifact is produced by default.

## Outputs

- **CSV** is the staged CSV path or artifact reference when storage is enabled.
- **Table** is the row-oriented result data for in-app consumers.
- **Exports** identifies the produced CSV artifact.

## If it fails

Connect both required inputs and ensure the model matches the result fields. If CSV creation fails, check the project artifact location and write access. Turn off Include Coordinates only when coordinates are unnecessary or unavailable.

## Mini recipe

Connect DPF Result Source to DPF Stress Invariants, then connect **Stress Invariants · Fields** and **Result Source · Model** to DPF Table Export and run the workflow.
