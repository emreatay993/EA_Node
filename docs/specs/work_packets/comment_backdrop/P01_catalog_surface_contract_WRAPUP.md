# P01 Catalog + Surface Contract Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/comment-backdrop/p01-catalog-surface-contract`
- Commit Owner: `worker`
- Commit SHA: `d1638f5e599037bb002462d07fdf795a7225bbd8`
- Changed Files: `ea_node_editor/nodes/builtins/passive_annotation.py`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`, `ea_node_editor/ui_qml/graph_surface_metrics.py`, `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`, `tests/test_comment_backdrop_contracts.py`, `tests/test_registry_filters.py`, `docs/specs/work_packets/comment_backdrop/P01_catalog_surface_contract_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/comment_backdrop/P01_catalog_surface_contract_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`, `tests/test_comment_backdrop_contracts.py`

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_contracts.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_registry_filters.py --ignore=venv -k "annotation" -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the application from `codex/comment-backdrop/p01-catalog-surface-contract` and open any workspace with the node library available.
- Add `Comment Backdrop` from the `Annotation` category. Expected: it appears as a large collapsible zero-port backdrop with the dedicated `comment_backdrop` surface, not as a sticky-note or callout card.
- Select the backdrop and edit the `Body` property in the inspector. Expected: the backdrop surface body text updates on the canvas while the node still exposes no ports and keeps its collapse affordance.
- Save and reload a project containing the backdrop. Expected: the backdrop reloads from the normal workspace node list with its title/body preserved and no persisted membership list fields.

## Residual Risks

- The new `comment_backdrop` surface family is enabled from the passive annotation module to stay inside packet scope; later centralized surface-family validation work must preserve that contract explicitly.
- The backdrop still renders through the regular node host path and layer in P01; dedicated under-edge layer placement, ownership, nested motion, and collapse routing remain for later packets.

## Ready for Integration

- Yes: the packet registers the new backdrop type, locks its surface and metric contract, verifies serializer round-tripping on the normal document path, and keeps the branch diff inside P01 scope.
