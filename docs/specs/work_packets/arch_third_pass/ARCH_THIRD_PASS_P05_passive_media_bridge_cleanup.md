# ARCH_THIRD_PASS P05: Passive Media Bridge Cleanup

## Objective
- Remove direct raw `mainWindow` and `sceneBridge` dependence from `GraphMediaPanelSurface.qml`, migrate it to explicit bridge contracts, and then trim compatibility exports if no packet-owned QML consumer still requires them.

## Preconditions
- `P00` through `P04` are marked `PASS` in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md).
- No later `ARCH_THIRD_PASS` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- packet-owned bridge additions in `ea_node_editor/ui_qml/`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_passive_image_nodes.py`
- `tests/main_window_shell/passive_image_nodes.py`
- `tests/test_pdf_preview_provider.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- packet-owned bridge additions in `ea_node_editor/ui_qml/`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_passive_image_nodes.py`
- `tests/main_window_shell/passive_image_nodes.py`
- `tests/test_pdf_preview_provider.py`

## Required Behavior
- Replace packet-owned raw `mainWindow` and `sceneBridge` dependence inside `GraphMediaPanelSurface.qml` with explicit bridge contracts or bridge-backed helper APIs.
- Preserve existing media preview, crop/edit, browse, and graph-surface interaction behavior from the user perspective.
- Keep `GraphCanvas.qml` and shell context bootstrap aligned with the packet-owned media bridge contract, trimming compatibility exports only when packet-owned consumers no longer require them.
- Preserve graph-surface input ownership rules introduced by earlier packet sets; do not reintroduce raw hover-proxy or click-swallowing patterns.
- Keep media preview provider interactions stable for current local image/PDF workflows.

## Non-Goals
- No new passive media authoring features.
- No broader `GraphCanvas.qml` visual decomposition or scene-core refactor reopen.
- No execution, persistence, or schema changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host tests.test_passive_image_nodes tests.main_window_shell.passive_image_nodes tests.test_pdf_preview_provider -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_third_pass/P05_passive_media_bridge_cleanup_WRAPUP.md`

## Acceptance Criteria
- `GraphMediaPanelSurface.qml` no longer depends directly on raw shell/scene context objects for packet-owned concerns.
- Any packet-owned compatibility exports removed by this packet are proven unused by packet-owned QML consumers.
- Passive media surface and preview regressions pass.

## Handoff Notes
- `P06` begins runtime worker refactoring; keep passive-media bridge work isolated from execution/runtime logic.
- If a non-packet-owned QML consumer still needs a compatibility export, leave it in place and record that residual in the wrap-up instead of widening scope.
