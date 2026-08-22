# Neutral CAD/FE Engineering Viewer

## Purpose
Use this route for neutral engineering geometry, prepared scenes, viewer
sessions, selection, clipping, export, and the shared fullscreen/detached host.

## Start Here
- `ea_node_editor/nodes/builtins/engineering_viewer.py`
- `ea_node_editor/nodes/builtins/geometry_primitives.py`
- `ea_node_editor/execution/prepared_scene_runtime.py`
- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/components/graph/viewer/`

## Behavior
- Model Viewer accepts supported engineering carriers and produces an owned
  prepared scene without exposing live worker objects to QML.
- Viewer sessions own camera, selection, clipping, display options, and export
  state through validated handles.
- Fullscreen and detached views retarget the same session rather than creating
  a second authoritative viewer.
- Optional topology remains lazy, asynchronous, and cached; points remain the
  fast default.
- Static Structural result geometry uses actual selected-set displacement when
  deformation is available and never claims deformed evidence from reference
  geometry.

## Boundaries
- Keep CAD/FE preparation in execution and UI projection in the viewer bridge.
- Keep project serialization limited to stable configuration and saved view
  facts; native scene and worker identities never persist.
- Keep identifiers, comments, tests, maps, and verification records functional.

## Focused Tests
- `tests/test_engineering_viewer_backend.py`
- `tests/test_engineering_viewer_node.py`
- `tests/test_engineering_viewer_widget_binder.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_control_bridge.py`
- `tests/test_content_fullscreen_bridge.py`

## Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_engineering_viewer_backend.py tests/test_engineering_viewer_node.py tests/test_viewer_session_bridge.py tests/test_viewer_control_bridge.py -q
```
