# P09 Node SDK Registry Cleanup Wrap-Up

## Implementation Summary

- Packet: `P09`
- Branch Label: `codex/corex-no-legacy-architecture-cleanup/p09-node-sdk-registry-cleanup`
- Commit Owner: `worker`
- Commit SHA: `2c5f7000f6698b167eccf1b4a69c7cee3d823a6e`
- Changed Files: `ea_node_editor/nodes/bootstrap.py`, `ea_node_editor/nodes/builtins/core.py`, `ea_node_editor/nodes/builtins/hpc.py`, `ea_node_editor/nodes/builtins/integrations.py`, `ea_node_editor/nodes/builtins/integrations_email.py`, `ea_node_editor/nodes/builtins/integrations_file_io.py`, `ea_node_editor/nodes/builtins/integrations_process.py`, `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`, `ea_node_editor/nodes/builtins/passive_annotation.py`, `ea_node_editor/nodes/builtins/passive_flowchart.py`, `ea_node_editor/nodes/builtins/passive_media.py`, `ea_node_editor/nodes/builtins/passive_planning.py`, `ea_node_editor/nodes/builtins/subnode.py`, `ea_node_editor/nodes/decorators.py`, `ea_node_editor/nodes/registry.py`, `ea_node_editor/nodes/types.py`, `tests/test_execution_artifact_refs.py`, `tests/test_port_labels.py`, `tests/test_registry_filters.py`, `tests/test_registry_validation.py`, `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P09_node_sdk_registry_cleanup_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P09_node_sdk_registry_cleanup_WRAPUP.md`

Removed descendant matching through legacy flat `category` filters while preserving `category_path` prefix filtering. Moved packet-owned built-in registration to descriptor tables consumed by `build_default_registry()`, narrowed the public `nodes.types.__all__` SDK surface, and updated packet-owned registry/serialization tests to author current `category_path` fields and stop asserting missing-field compatibility.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_registry_filters.py tests/test_passive_node_contracts.py tests/test_port_labels.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py --ignore=venv -q` (`83 passed, 5 subtests passed, 32 warnings`)
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_registry_filters.py --ignore=venv -q` (`53 passed, 5 subtests passed, 32 warnings`)
- PASS: `git diff --check`
Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing.

- Prerequisite: run the application from this branch with the project virtual environment.
- Open the node library and select the `Flowchart`, `Planning`, `Annotation`, and `Input / Output` category paths; expected result: the same built-in nodes appear as before and can still be added to the graph.
- Open the DPF category tree and select the root `Ansys DPF` path, then a leaf path such as `Ansys DPF > Viewer`; expected result: the root path includes descendants, while leaf paths only show nodes in that leaf.
- Save and reload a small graph containing a built-in active node, a passive node, and a renamed port label; expected result: node IDs, port IDs, passive behavior, and serialized `port_labels` output remain stable.

## Residual Risks

- Existing Ansys DPF operator rename deprecation warnings still appear during verification and are unrelated to this packet.
- `NodeRegistry.register()` remains for current plugin loader compatibility; P09 removes class-first built-in bootstrap usage, while P10 owns third-party plugin/add-on loader cleanup.
- The non-strict graph model helper still defaults absent `port_labels` to an empty mapping outside P09's source scope; P09 removed the packet-owned missing-field compatibility assertion and kept current serializer output stable.

## Ready for Integration

Yes: P09 code, packet-owned tests, wrap-up artifact, full verification command, and review gate are complete on the assigned packet branch.
