# P07 Graph Persistence Overlay Removal Wrap-Up

## Implementation Summary

- Packet: `P07`
- Branch Label: `codex/corex-no-legacy-architecture-cleanup/p07-graph-persistence-overlay-removal`
- Commit Owner: `worker`
- Commit SHA: `966fcbd1a7f03476ed2287e6f96eb927d3fe4a28`
- Changed Files: `ea_node_editor/graph/model.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/persistence/overlay.py`, `ea_node_editor/persistence/project_codec.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/test_architecture_boundaries.py`, `tests/test_project_file_issues.py`, `tests/test_registry_validation.py`, `tests/test_serializer.py`, `tests/test_workspace_manager.py`, `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P07_graph_persistence_overlay_removal_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P07_graph_persistence_overlay_removal_WRAPUP.md`

Removed graph-owned persistence overlay accessors, snapshot/clone capture and restore paths, normalization preservation of missing add-on authored payloads, and QML payload projection from workspace sidecars. Persistence now serializes only live graph nodes and edges, rejects runtime overlay metadata, and leaves unavailable-add-on UI projection deferred to the later add-on/viewer cleanup packets.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py tests/test_serializer.py tests/test_project_file_issues.py tests/test_workspace_manager.py --ignore=venv -q` (`87 passed, 32 warnings, 15 subtests passed`)
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_registry_validation.py --ignore=venv -q` (`48 passed, 16 warnings, 15 subtests passed`)
- PASS: `git diff --check`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Open a current saved project containing only registered node types, save it again, and reopen it. Expected result: workspaces, views, live nodes, live edges, passive media nodes, comment backdrops, hierarchy, and managed-file references remain intact.
2. Open a current project that contains node types not registered in this branch. Expected result: unavailable nodes and their dependent edges are pruned instead of appearing as read-only graph placeholders; the remaining live graph opens without persistence-overlay metadata.
3. Duplicate a workspace with live nodes and edges. Expected result: the duplicate contains independent live graph data only, with no unresolved sidecar state.

## Residual Risks

- Unavailable-add-on visual placeholder projection is intentionally deferred to P10/P12 rather than carried through graph-owned persistence sidecars.
- Existing Ansys DPF deprecation warnings appeared during verification and are unrelated to this packet.

## Ready for Integration

- Yes: P07 code changes are committed, verification passes, and the remaining risks are deferred to the planned later packets.
