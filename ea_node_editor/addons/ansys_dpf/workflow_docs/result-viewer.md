# DPF Result Viewer

## Use this when

Open a scoped result directly from a Mechanical result file without assembling separate source, extraction, and viewer nodes.

## Required wiring

Choose **Result File** in the Inspector. No model connection is required because this node loads its own model.

## Defaults

The default quantity is displacement. Spatial scope is the whole model, location stays native, Time Scope is **First set**, deformation is off, and Output Mode is **Both** so the result can be viewed and reused.

## Outputs

- **Session** opens the embedded DPF Viewer.
- **Fields** is the stable DPF Fields Container result for downstream nodes.
- **Result File**, **Model**, **Mesh Scoping**, **Time Scoping**, **Mesh**, and **Normalized Path** expose the resolved workflow parts when available.

## If it fails

Choose a valid result file and make sure the selected result, set, and spatial scope exist. A named-selection mode also requires a valid named selection. If DPF is unavailable, install or enable the Ansys DPF add-on runtime before running the node.

## Mini recipe

Drop DPF Result Viewer, choose an `.rst` file, select Stress and a named selection, then run the node and open the embedded viewer.
