# DPF Mode Shape Viewer

## Use this when

Display one displacement mode shape from a modal result file and report its natural frequency.

## Required wiring

Choose a modal `.rst` or `.rth` file in **Result File**, then select a positive mode number. No upstream model connection is required.

## Defaults

Mode defaults to 1, spatial scope is the whole model, location stays native, deformation is **Auto**, and Output Mode is **Both**.

## Outputs

- **Session** opens the embedded mode-shape viewer.
- **Fields** is the stable displacement Fields Container for the chosen mode.
- **Frequency** reports the mode frequency when the result file provides it.
- **Result File**, **Model**, **Mesh Scoping**, **Time Scoping**, **Mesh**, and **Normalized Path** expose the resolved workflow parts when available.

## If it fails

Confirm that the file contains modal results and that the mode is a positive number within the available set range. A missing frequency can mean the file lacks frequency metadata even when the displacement mode can be read.

## Mini recipe

Choose a modal result file, keep Mode 1 and Auto deformation, run the node, then use the viewer playback and camera controls to inspect the shape.
