# P04 Graph Boundary Adapters Wrap-Up

## Implementation Summary
- Packet: `P04`
- Branch Label: `codex/architecture-refactor/p04-graph-boundary-adapters`
- Commit Owner: `worker`
- Commit SHA: `d5f8ce5c4e9a48fa1335fbeff3e4ad05a187d29f`
- Changed Files: `ea_node_editor/graph/boundary_adapters.py`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/ui_qml/graph_scene_bridge.py`, `tests/test_architecture_boundaries.py`
- Artifacts Produced: `docs/specs/work_packets/architecture_refactor/P04_graph_boundary_adapters_WRAPUP.md`, `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md`
- Added a graph-owned boundary adapter registry so mutation-time graph code can resolve node geometry and PDF page normalization without importing UI/QML modules directly.
- Removed the direct `ea_node_editor.ui.pdf_preview_provider` and `ea_node_editor.ui_qml.edge_routing` imports from `WorkspaceMutationService` and routed those concerns through graph-owned adapter callables instead.
- Wired `GraphSceneBridge` to install the concrete UI-layer geometry and PDF adapters at composition time, preserving the current app behavior while keeping the graph mutation path isolated from UI imports.
- Added a packet-owned architecture-boundary regression that checks the graph mutation seam no longer imports UI/QML helpers directly and that the scene bridge owns the adapter installation seam.
- Preserved persisted graph shape, comment-backdrop wrapping, and PDF page clamping behavior in the scene-backed authoring path.

## Verification
- PASS: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_port_labels.py tests/test_comment_backdrop_membership.py tests/test_pdf_preview_provider.py tests/test_flow_edge_labels.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Residual Risks
- The graph boundary adapter registry keeps a fallback implementation for non-scene callers; any future non-Qt mutation entrypoint that needs scene-accurate node sizing or PDF clamping should install explicit adapters rather than relying on the fallback defaults.
- The packet guardrail currently covers the mutation-service seam and scene-bridge wiring; later graph decomposition work may want a broader import-boundary check across neighboring graph payload modules.

## Ready for Integration
- Yes: the packet verification and review gate both passed, the worktree is clean, and the accepted substantive SHA is recorded above.
