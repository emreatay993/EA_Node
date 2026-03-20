# GRAPHICS_PERFORMANCE_MODES P08: Media Surface Proxy Adoption

## Objective
- Move the built-in image/PDF media nodes onto the heavy-node render-quality path so `Max Performance` improves real heavy-media interaction now while leaving a clear pattern for future CAD/mesh-style nodes.

## Preconditions
- `P00` through `P07` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- built-in passive media node specs under `ea_node_editor/nodes/builtins/`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml`
- targeted passive image/PDF/media-surface regression tests

## Conservative Write Scope
- `ea_node_editor/nodes/builtins/passive_media.py`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelPreviewViewport.qml`
- `tests/test_passive_image_nodes.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/graphics_performance_modes/P08_media_surface_proxy_adoption_WRAPUP.md`

## Required Behavior
- Mark the built-in image and PDF panel nodes as heavy nodes that participate in the render-quality contract from `P06`.
- Adopt the host/surface quality seam from `P07` inside the built-in media surfaces so `Max Performance` can use a lighter interaction/proxy path while idle fidelity still returns automatically.
- Preserve existing media-node edit/crop/path/preview behaviors in idle/full-fidelity state.
- Keep the media-surface implementation aligned with the hybrid architecture: generic fallback still works, but built-in media nodes should exercise the richer proxy strategy path.
- Add or update focused media regressions that lock the quality/proxy behavior for image/PDF nodes.

## Non-Goals
- No new CAD/mesh node implementation in this packet.
- No benchmark/report or docs work yet. `P09` and `P10` own those.
- No change to non-media node families beyond contract consumption already introduced earlier.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_image_nodes.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_pdf_preview_provider.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "media and (performance_mode or proxy)" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_image_nodes.py --ignore=venv -k "performance_mode or proxy" -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P08_media_surface_proxy_adoption_WRAPUP.md`

## Acceptance Criteria
- Built-in image/PDF nodes publish the heavy-node render-quality metadata expected by the host/surface seam.
- Media surfaces honor the resolved quality tier in `Max Performance` while preserving idle/full-fidelity behavior.
- Focused image/PDF/media-host regressions pass.
- The resulting pattern is documented clearly enough in the wrap-up for future heavy-node authors to follow.

## Handoff Notes
- Record the exact built-in media defaults and proxy behavior in the wrap-up so future CAD/mesh packets can mirror them.
- If any media behavior had to remain on the generic fallback path, note why explicitly.
