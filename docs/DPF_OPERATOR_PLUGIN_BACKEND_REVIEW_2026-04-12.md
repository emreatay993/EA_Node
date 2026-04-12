# DPF Operator Plugin Backend Review 2026-04-12

## Scope

- Prepare the backend for a future optional `ansys-dpf-core` operator plugin.
- Keep this pass focused on infrastructure only; do not mass-expose DPF operators yet.
- Design for machines that do not have DPF installed while preserving the ability to reopen projects that already contain DPF-backed nodes.

## Current Repo Reality

- The node system is already descriptor-first and plugin-first through `ea_node_editor/nodes/plugin_loader.py`, `ea_node_editor/nodes/plugin_contracts.py`, `ea_node_editor/nodes/registry.py`, and `ea_node_editor/nodes/node_specs.py`.
- The shipped DPF support is still handwritten through `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`, `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`, and `ea_node_editor/execution/dpf_runtime/operations.py`.
- Optional ports already exist structurally through `required` and `exposed`, but there is no first-class binding contract for omitted operator defaults, mutually exclusive pin groups, or source pin metadata.
- Persistence already preserves unresolved node documents through `ea_node_editor/persistence/project_codec.py` and `ea_node_editor/persistence/overlay.py`, but the runtime graph does not yet have a first-class read-only missing-plugin placeholder state.

## Locked Defaults

- `ansys-dpf-core` remains optional. Startup without DPF must keep the rest of the app fully usable.
- Backend preparation is operators-first. Non-operator `ansys.dpf.core` surfaces stay out of scope in this packet set.
- Missing-plugin DPF nodes must remain visible as read-only placeholders with saved ports, values, labels, and connectivity, but they cannot execute or expose live schema editing until the plugin is available again.
- Generated-port semantics must distinguish:
  - required inputs
  - optional inputs
  - omitted operator-default inputs
  - explicit literal values
  - mutually exclusive input groups
- Existing `.sfe` persistence compatibility, existing non-DPF node IDs, and current handwritten DPF node behavior must remain intact during this preparation pass.

## Recommended Refactor Order

1. Optional plugin lifecycle and availability contract.
2. DPF operator metadata normalization and port-binding contract.
3. Generic DPF runtime adapter for operator-backed compute paths.
4. Missing-plugin placeholder portability for saved projects.
5. Verification, QA, and architecture closeout that freezes the backend contract for the later operator rollout.
