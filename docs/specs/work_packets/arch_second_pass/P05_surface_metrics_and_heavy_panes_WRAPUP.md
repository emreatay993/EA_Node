# P05 Surface Metrics And Heavy Panes Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/arch-second-pass/recovery-p05-20260318`
- Commit Owner: `worker`
- Commit SHA: `3f0910f`
- Changed Files: `ea_node_editor/ui_qml/graph_surface_metrics.py`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelGeometry.js`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewPlaceholder.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSourceUtils.js`, `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`, `ea_node_editor/ui_qml/components/shell/InspectorSectionCard.qml`, `ea_node_editor/ui_qml/components/shell/InspectorMetadataChip.qml`, `ea_node_editor/ui_qml/components/shell/InspectorButton.qml`, `ea_node_editor/ui_qml/components/shell/InspectorSegmentButton.qml`, `ea_node_editor/ui_qml/components/shell/InspectorCheckBox.qml`, `ea_node_editor/ui_qml/components/shell/InspectorTextField.qml`, `ea_node_editor/ui_qml/components/shell/InspectorTextArea.qml`, `ea_node_editor/ui_qml/components/shell/InspectorComboBox.qml`, `ea_node_editor/ui_qml/components/shell/InspectorEditableComboBox.qml`, `ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml`, `ea_node_editor/ui_qml/components/shell/InspectorPortRow.qml`, `ea_node_editor/ui_qml/components/shell/InspectorNodeDefinitionSection.qml`, `ea_node_editor/ui_qml/components/shell/InspectorPortManagementSection.qml`, `tests/test_passive_image_nodes.py`, `tests/main_window_shell/passive_image_nodes.py`, `tests/main_window_shell/passive_pdf_nodes.py`
- Artifacts Produced: `docs/specs/work_packets/arch_second_pass/P05_surface_metrics_and_heavy_panes_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.json`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetricContract.js`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelGeometry.js`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewPlaceholder.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSourceUtils.js`, `ea_node_editor/ui_qml/components/shell/InspectorSectionCard.qml`, `ea_node_editor/ui_qml/components/shell/InspectorMetadataChip.qml`, `ea_node_editor/ui_qml/components/shell/InspectorButton.qml`, `ea_node_editor/ui_qml/components/shell/InspectorSegmentButton.qml`, `ea_node_editor/ui_qml/components/shell/InspectorCheckBox.qml`, `ea_node_editor/ui_qml/components/shell/InspectorTextField.qml`, `ea_node_editor/ui_qml/components/shell/InspectorTextArea.qml`, `ea_node_editor/ui_qml/components/shell/InspectorComboBox.qml`, `ea_node_editor/ui_qml/components/shell/InspectorEditableComboBox.qml`, `ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml`, `ea_node_editor/ui_qml/components/shell/InspectorPortRow.qml`, `ea_node_editor/ui_qml/components/shell/InspectorNodeDefinitionSection.qml`, `ea_node_editor/ui_qml/components/shell/InspectorPortManagementSection.qml`

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m unittest tests.test_inspector_reflection tests.test_passive_image_nodes -v`
- PASS: `QT_QPA_PLATFORM=offscreen /mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_inline tests.test_passive_image_nodes tests.test_pdf_preview_provider tests.test_inspector_reflection tests.main_window_shell.passive_image_nodes tests.main_window_shell.passive_pdf_nodes -v`
- PASS: `git diff --check`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Open the main window shell, select a passive image node, and compare the graph surface with the inspector panel. Expected result: the image surface layout, crop controls, and inspector path/property editors behave the same as before while the pane content still appears in the same order and with the same object names.
2. Select a passive PDF node and use both the inline path editor and the inspector path browse flow. Expected result: the selected file path commits immediately, the preview updates cleanly, and interacting with the editors does not start a node drag.
3. Select a subnode shell and exercise the port management section by switching tabs, renaming a port, toggling exposure, adding a port, and deleting the selected port. Expected result: the inspector keeps the same controls and behaviors after the helper split, and the selected port state stays synchronized while editing.

## Residual Risks

- `GraphNodeSurfaceMetricContract.js` is a generated mirror of the authoritative JSON contract, so future metric changes need regeneration discipline to avoid drift.
- The Windows shell smoke tests are stabilized by subprocess isolation; repeated in-process shell teardown and recreation remains a known sensitive area outside this packet's scope.

## Ready for Integration

- Yes: Packet-owned changes stay inside scope, the accepted substantive commit is recorded above, and both the review gate and full verification command passed on the final state.
