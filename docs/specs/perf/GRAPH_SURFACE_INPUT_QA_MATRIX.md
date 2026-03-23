# Graph Surface Input QA Matrix

- Updated: `2026-03-18`
- Packet set: `GRAPH_SURFACE_INPUT` (`P01` through `P09`)
- Scope: final close-out matrix for the locked host/surface input-routing pattern used by graph-surface controls and media tools.

## Locked Pattern

- `GraphNodeHost.qml` keeps node-body drag/select/open/context handling beneath the loaded surface content.
- `embeddedInteractiveRects` is the ordinary local-control ownership contract. Surfaces publish host-local rects for buttons, editors, and handles that must bypass host body behavior.
- `blocksHostInteraction` is reserved for whole-surface modal tools such as crop mode. It is not the default mechanism for ordinary inline editors.
- Reusable graph-surface buttons and editors live under `ea_node_editor/ui_qml/components/graph/surface_controls/`.
- Hover-only affordances use `HoverHandler` or `MouseArea { acceptedButtons: Qt.NoButton }`; they do not reintroduce click-swallowing proxy overlays.

## Shell Verification Policy

- Use these shell verification commands for the shell-backed graph-surface cases:
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v`
- Both module-level shell wrappers passed directly on `2026-03-18`, so no
  per-test fresh-process fallback is currently required.
- The broader verification workflow still keeps shell-backed suites on isolated
  module-level processes rather than sharing a long-lived `ShellWindow()`
  harness. Keep that subprocess boundary in place until a later packet proves a
  different model is stable.

## Final Matrix

| Coverage Area | Primary Requirement Anchors | Command | Expected Coverage |
|---|---|---|---|
| Host body routing and local embedded-rect ownership | `REQ-UI-020`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | Host/body click-open-context behavior still works outside embedded rects, interactive controls bypass host drag, modal whole-surface locks still work, and the media surface keeps direct control ownership without hover-proxy shims |
| Shared inline controls and node-id routed graph-surface editors | `REQ-UI-023`, `REQ-NODE-017`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | Shared toggle/enum/text/number/textarea/path controls publish `embeddedInteractiveRects`, and graph-surface commits/browse actions stay on the explicit `nodeId` path |
| Media-surface direct ownership and crop-mode whole-surface lock | `REQ-UI-022`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | Crop button, crop handles, apply/cancel actions, caption editor, and path editor publish direct ownership while crop mode still locks host interactions through `blocksHostInteraction` |
| Shell image-node graph-surface workflows | `REQ-UI-022`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v` | Fresh-process shell coverage for image-node inline path editing, crop-button ownership, and crop apply/cancel flows |
| Shell PDF-node graph-surface workflows | `REQ-UI-022`, `REQ-UI-023`, `REQ-QA-013` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v` | Fresh-process shell coverage for PDF-node inline path editing plus selected-node-independent browse/commit flows |

## 2026-03-18 Execution Results

| Command | Result | Notes |
|---|---|---|
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v` | PASS (`40/40`) | Aggregate QML/unit/media regression gate exited cleanly with no fallback needed |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes -v` | PASS (`8/8`) | Module-level image-shell wrapper passed directly under `QT_QPA_PLATFORM=offscreen` |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes -v` | PASS (`4/4`) | Module-level PDF-shell wrapper passed directly under `QT_QPA_PLATFORM=offscreen` |

## Result Recording

- Record the exact pass counts and fallback usage in this matrix and any local work-packet notes you keep outside Git.
- `scripts/check_traceability.py` validates that this matrix remains linked from
  the packet-owned onboarding and traceability docs.
- If a future environment reintroduces wrapper instability, rerun the three
  shell commands above and update this matrix before restoring any narrower
  fallback guidance.
