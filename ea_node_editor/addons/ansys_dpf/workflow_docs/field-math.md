# DPF Field Math

## Use this when

Add, subtract, multiply, divide, or scale DPF results without wiring raw variadic DPF operators.

## Required wiring

Connect a DPF Field or Fields Container to **A**. Add, Subtract, Multiply, and Divide also require a compatible result on **B**. Scale uses **A** and the Scalar property; **B** is ignored.

## Defaults

Operation defaults to Add and Scalar defaults to 1. Inputs should have compatible scoping, set labels, component shape, and location.

## Outputs

- **Fields** is always the resulting DPF Fields Container.

## If it fails

Connect **A** first. For binary operations, connect **B** and make sure both inputs represent compatible entities, sets, components, and locations. Division can also fail or produce non-finite values where B is zero.

## Mini recipe

Extract the same quantity at First set and Last set with two DPF Result Fields nodes, connect them to A and B, and choose Subtract to compute the change.
