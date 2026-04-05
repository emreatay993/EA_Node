# P06 Graph Surface Test Packetization Wrap-Up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/ui-context-scalability-followup/p06-graph-surface-test-packetization`
- Commit Owner: `worker`
- Commit SHA: `728df1933b3dde0c9eaab8c5aa510979fff39cba`
- Changed Files: `docs/specs/work_packets/ui_context_scalability_followup/P06_graph_surface_test_packetization_WRAPUP.md`, `tests/graph_surface/__init__.py`, `tests/graph_surface/environment.py`, `tests/graph_surface/inline_editor_suite.py`, `tests/graph_surface/media_and_scope_suite.py`, `tests/graph_surface/passive_host_boundary_suite.py`, `tests/graph_surface/passive_host_interaction_suite.py`, `tests/graph_surface/pointer_and_modal_suite.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_passive_graph_surface_host.py`
- Artifacts Produced: `docs/specs/work_packets/ui_context_scalability_followup/P06_graph_surface_test_packetization_WRAPUP.md`, `tests/graph_surface/__init__.py`, `tests/graph_surface/environment.py`, `tests/graph_surface/inline_editor_suite.py`, `tests/graph_surface/media_and_scope_suite.py`, `tests/graph_surface/passive_host_boundary_suite.py`, `tests/graph_surface/passive_host_interaction_suite.py`, `tests/graph_surface/pointer_and_modal_suite.py`

- Replaced the two oversized graph-surface regression umbrellas with thin stable entrypoints that import focused packet-owned suites from `tests/graph_surface/`.
- Centralized the shared QML probe/runtime harnesses in `tests/graph_surface/environment.py`, then regrouped the existing host and input-contract cases into boundary, inline-editor, media-and-scope, pointer-and-modal, and passive-host interaction suites without changing the asserted behaviors.
- Added packet boundary checks that keep `tests/test_passive_graph_surface_host.py` and `tests/test_graph_surface_input_contract.py` under the packet cap and ensure they stay packetized import surfaces instead of regrowing local probe bodies.
- Kept the known QML subprocess crash guard in the shared environment and raised the retry count so the packetized suites remain stable under the existing offscreen Qt probe behavior.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_contract.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

1. Launch the graph canvas and verify a standard node, a passive flowchart node, a scoped passive node, and a media node still expose the same hover, title-edit, body-edit, and port-hit behavior after the suite split.
2. Exercise a media crop flow and a missing-file repair flow once, then confirm the crop buttons, crop handles, and repair browse path still route through the canvas contract with the expected node IDs.
3. Open a viewer-family node and a scoped passive node from the graph canvas, then confirm the viewer surface control rects and scoped open-badge interactions still behave the same with the packetized regression entrypoints.

## Residual Risks

- The graph-surface packet now depends on wildcard imports from `tests/graph_surface/environment.py` so the extracted test methods can keep their original module-level symbol lookups; later packets that move helper symbols need to update that export surface together with the focused suites.
- Offscreen Qt probes still have a known transient `3221226505` subprocess crash path, so the shared retry helper remains part of the packetized environment and should stay aligned with future graph-surface QML probe changes.

## Ready for Integration

- Yes: the packetized graph-surface suites are in place behind the stable entry files, both stable entrypoints are well under 200 lines, and the packet verification plus review gate both pass on the assigned branch.
