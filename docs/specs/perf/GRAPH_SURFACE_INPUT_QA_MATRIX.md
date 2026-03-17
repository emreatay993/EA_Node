# Graph Surface Input QA Matrix

- Updated: `2026-03-17`
- Packet set: `GRAPH_SURFACE_INPUT` (`P01` through `P09`)
- Scope: final close-out matrix for the locked host/surface input-routing pattern used by graph-surface controls and media tools.

## Locked Pattern

- `GraphNodeHost.qml` keeps node-body drag/select/open/context handling beneath the loaded surface content.
- `embeddedInteractiveRects` is the ordinary local-control ownership contract. Surfaces publish host-local rects for buttons, editors, and handles that must bypass host body behavior.
- `blocksHostInteraction` is reserved for whole-surface modal tools such as crop mode. It is not the default mechanism for ordinary inline editors.
- Reusable graph-surface buttons and editors live under `ea_node_editor/ui_qml/components/graph/surface_controls/`.
- Hover-only affordances use `HoverHandler` or `MouseArea { acceptedButtons: Qt.NoButton }`; they do not reintroduce click-swallowing proxy overlays.

## Approved Shell Fallback

- Requested shell verification commands for this packet are:
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v`
- In environments where either module-level wrapper exits with code `5`, the approved fallback is to rerun every shell case in its own fresh process with `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest <test-id> -v`.
- The `2026-03-17` gate used that fallback for complete shell coverage with these test ids:
  - Image suite: `test_image_panel_inspector_exposes_locked_editor_modes`, `test_image_panel_path_editor_browse_commits_selected_path`, `test_image_panel_inline_path_editor_commits_without_node_drag`, `test_image_panel_crop_apply_persists_hidden_normalized_rect`, `test_image_panel_crop_button_click_does_not_start_host_drag`, `test_image_panel_crop_apply_closes_when_crop_is_unchanged`, `test_image_panel_crop_apply_and_cancel_clicks_bypass_host_drag`, `test_image_panel_crop_handles_report_expected_cursor_and_hover`
  - PDF suite: `test_pdf_panel_inspector_exposes_locked_editor_modes`, `test_pdf_panel_path_editor_browse_commits_selected_path`, `test_pdf_panel_inline_path_editor_commits_without_node_drag`, `test_pdf_panel_out_of_range_page_is_rewritten_after_pdf_resolves`

## Final Matrix

| Coverage Area | Primary Requirement Anchors | Command | Expected Coverage |
|---|---|---|---|
| Host body routing and local embedded-rect ownership | `REQ-UI-020`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | Host/body click-open-context behavior still works outside embedded rects, interactive controls bypass host drag, modal whole-surface locks still work, and the media surface keeps direct control ownership without hover-proxy shims |
| Shared inline controls and node-id routed graph-surface editors | `REQ-UI-023`, `REQ-NODE-017`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | Shared toggle/enum/text/number/textarea/path controls publish `embeddedInteractiveRects`, and graph-surface commits/browse actions stay on the explicit `nodeId` path |
| Media-surface direct ownership and crop-mode whole-surface lock | `REQ-UI-022`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | Crop button, crop handles, apply/cancel actions, caption editor, and path editor publish direct ownership while crop mode still locks host interactions through `blocksHostInteraction` |
| Shell image-node graph-surface workflows | `REQ-UI-022`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v` | Fresh-process shell coverage for image-node inline path editing, crop-button ownership, and crop apply/cancel flows |
| Shell PDF-node graph-surface workflows | `REQ-UI-022`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v` | Fresh-process shell coverage for PDF-node inline path editing plus selected-node-independent browse/commit flows |

## 2026-03-17 Execution Results

| Command | Result | Notes |
|---|---|---|
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | PASS (`37/37`) | Aggregate QML/unit/media regression gate exited cleanly with no fallback needed |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v` | wrapper instability (`code 5`) | The module wrapper exited after `test_image_panel_crop_apply_and_cancel_clicks_bypass_host_drag` passed and `test_image_panel_crop_apply_closes_when_crop_is_unchanged` started; approved fresh-process fallback completed `8/8` image-shell cases |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v` | wrapper instability (`code 5`) | The module wrapper exited after `test_pdf_panel_inline_path_editor_commits_without_node_drag` passed and `test_pdf_panel_inspector_exposes_locked_editor_modes` started; approved fresh-process fallback completed `4/4` PDF-shell cases |

## Result Recording

- Record the exact pass counts and fallback usage in `docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md`.
- If a future environment runs the module-level shell commands cleanly, note that the fallback was not needed. If they continue to exit with code `5`, keep the per-test fresh-process rerun as the approved gate so the targeted matrix remains complete.
