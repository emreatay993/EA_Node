# DPF Time History Probe

## Use this when

Build result-versus-time or result-versus-frequency curves for selected nodes, elements, or a named selection.

## Required wiring

Connect a DPF Result Source **Model** output to **Model**. New nodes start at **Choose scope**: select Named Selection, Node IDs, or Element IDs and provide the matching value before running.

## Defaults

The default quantity is displacement, location stays native, and Time Scope is **All sets**. Use explicit Set IDs or Time Values to shorten the history.

## Outputs

- **Series** contains one DPF curve field per resolved entity for compatible DPF plot nodes.
- **Table** contains the row-oriented history data.
- **Time Values** contains the physical time or frequency coordinates used on the X axis.

## If it fails

The node cannot run while scope remains unconfigured. Check that the named selection exists or that the entity IDs match the chosen node/element mode. Also verify that the selected time sets exist and that the result is available at the requested location.

## Mini recipe

Connect DPF Result Source to DPF Time History Probe, choose one node ID and All sets, then connect **Series** to the DPF line-plot node.
