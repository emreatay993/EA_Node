# GRAPHICS_PERFORMANCE_MODES P06: Node Render Quality Contract

## Objective
- Extend the Node SDK and scene payload contract with declarative render-quality metadata so future heavy nodes can participate in graphics performance modes without bespoke canvas-only hacks.

## Preconditions
- `P00` through `P05` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/nodes/types.py`
- decorator/registry surfaces that construct or validate `NodeTypeSpec`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- targeted Node SDK and scene-payload regression tests

## Conservative Write Scope
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/decorators.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_registry_validation.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_node_contracts.py`
- `docs/specs/work_packets/graphics_performance_modes/P06_node_render_quality_contract_WRAPUP.md`

## Required Behavior
- Add a declarative `NodeRenderQualitySpec` surface to `NodeTypeSpec` with the v1 fields approved in the plan: `weight_class`, `max_performance_strategy`, and `supported_quality_tiers`.
- Keep existing node authorship compatible: legacy specs without render-quality data must continue to load with safe defaults and must not require source edits.
- Ensure decorator-authored and class-spec-authored nodes can both publish or inherit the new metadata.
- Propagate normalized render-quality metadata through the scene payload builder so QML host/surface packets can consume it later.
- Add or update tests that lock validation/defaulting behavior plus scene-payload publication of the new metadata.

## Non-Goals
- No host/surface consumption of the new metadata yet. `P07` owns that.
- No built-in heavy-node adoption yet. `P08` owns that.
- No docs/traceability updates yet. `P10` owns that.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_registry_validation.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
3. `./venv/Scripts/python.exe -m pytest tests/test_passive_node_contracts.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_registry_validation.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P06_node_render_quality_contract_WRAPUP.md`

## Acceptance Criteria
- `NodeTypeSpec` exposes normalized render-quality metadata with backward-compatible defaults.
- Registry/decorator pathways continue to accept existing node definitions without required source changes.
- Scene payloads carry the normalized render-quality contract for later QML consumption.
- Node SDK and payload regression tests pass.

## Handoff Notes
- Record the exact default render-quality values in the wrap-up so `P08` can classify built-in media nodes consistently.
- If validation had to reject any metadata shapes, document them explicitly for future plugin authors.
