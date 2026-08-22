# DPF Result Source

## Use this when

Start here when several post-processing nodes should share one Mechanical `.rst` or `.rth` file. The node loads the file once and exposes the DPF model used by extraction, reduction, probing, and export nodes.

## Required wiring

Choose **Result File** in the Inspector. Connect **Model** to workflow nodes such as DPF Result Fields, DPF Min/Max Envelope, DPF Time History Probe, or DPF Stress Invariants.

## Defaults

The result-file path is empty on a new node, so the node is incomplete until a file is selected.

## Outputs

- **Result File** is the loaded DPF data-source handle.
- **Model** is the reusable DPF model handle for downstream workflow nodes.
- **Normalized Path** is the resolved local path.

## If it fails

Check that the path exists, the file is a supported result file, and the installed DPF runtime can read the file version. An empty path means the node still needs a result file; it does not mean the file contains no results.

## Mini recipe

Connect **DPF Result Source · Model** to **DPF Result Fields · Model**, then choose the quantity, scope, and time on DPF Result Fields.
