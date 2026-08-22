# QML Bridge Wiring

## Purpose
Use this for Python/QML bridge ownership, context properties, invokable methods, and bridge boundary tests.
Graph canvas toolbar mutations that bypass modal graph actions, including flow-edge label/style updates, are exposed through `GraphCanvasCommandBridge` and should be covered here.
Text annotation style copy/paste is also exposed through `GraphCanvasCommandBridge` as an internal app/session clipboard, not the OS clipboard.
Durable node link actions are split by owner: inspector rows/actions route through `ShellInspectorBridge`, while graph-canvas hover/open/delete actions route through `GraphCanvasCommandBridge` and the graph scene command source.
Video Panel trim-save is bridge-owned too: inline QML calls `GraphCanvasCommandBridge`, fullscreen QML calls `ContentFullscreenBridge`, and both forward to `GraphCanvasPresenter`.
Dynamic-port authoring follows `GraphNodePortsLayer.qml` / `GraphCanvasContextMenus.qml` -> `graph_canvas_command.scene_mutation_ops` -> `GraphSceneCommandBridge` -> `graph_scene_mutation.selection_and_scope_ops` -> `ValidatedGraphMutation`; QML never writes the hidden backing properties.
Sensitive-property authoring follows graph/Inspector `SecretEditor.qml` -> dedicated `set/clear_*_secret` slots -> `GraphSceneMutationHistory` -> `selection_and_scope_ops`; generic property setters reject sensitive keys, so plaintext is DPAPI-protected before graph mutation or history capture.
Optimization Setup-to-Pool authoring follows `GraphCanvasContextMenus.qml` -> `graph_canvas_command.scene_mutation_ops` -> `GraphSceneMutationHistory` -> graph-owned node-link mutation, so semantic links persist and undo/redo without a QML-only store.

## Start Here
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state/` — state bridge package. The composition root (`__init__.py`) owns construction + source resolution ONLY; a new QML-visible canvas fact is one `@pyqtProperty` in the matching projection mixin (`graphics_preferences_props`, `execution_state_props`, `scene_models_props`, `view_state_props`) — each property must live with its notify signal's mixin. Viewport-virtualization logic (hysteresis/bucketing/delta sync and the `visible_*` projections) lives in `visible_scene_service.py`.
- `ea_node_editor/ui_qml/graph_canvas_command/` — command bridge package. The composition root (`__init__.py`) owns construction + source resolution ONLY; a new canvas command is one `@pyqtSlot` in the matching per-domain ops module (`graphics_settings_ops`, `viewport_ops`, `scene_mutation_ops`, `media_video_ops`, `node_creation_ops`, `annotation_style_ops`, `canvas_host_ops`, `folder_explorer_ops`) plus its protocol entry (same file or `protocols.py`). `tests/test_graph_canvas_command_ops_modules.py` guards mixin slot registration and cross-domain name collisions.
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/policy_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/`
- `ea_node_editor/ui_qml/graph_scene_mutation/policy.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui/shell/controllers/mutation_ui_effects.py`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui/shell/context_bridges.py`
- `tests/test_data_type_ui_projection.py`

## Frozen QML-Visible Surface
- The QML-visible meta-object surface of the graph-canvas bridge family (slots, properties, signals on `GraphCanvasBridge`, `GraphCanvasStateBridge`, `GraphCanvasCommandBridge`, `ViewportBridge`, the graph-scene read/command/policy bridges, `GraphSceneBridge`, and `ShellContextBundle`) is snapshot-frozen by `tests/test_graph_canvas_bridge_surface_snapshot.py` against `tests/fixtures/graph_canvas_bridge_surface_snapshot.json`. Additions are allowed (regenerate with `--write`); removals/renames fail.
- The snapshot includes `insert_dynamic_port`, `remove_dynamic_port`, and `rename_dynamic_port` on the graph command/scene chain.
- Dedicated `set_node_secret` and `clear_node_secret` slots are part of the graph-scene bridge chain; Inspector wrappers forward to the same owner.
- Drag compatibility follows `GraphSceneMutationPolicy.compatible_endpoint_snapshot(...)` -> `GraphScenePolicyBridge` -> `graph_canvas_state/scene_models_props.py` -> `GraphCanvasInteractionState.wireDragState`. The bridge publishes one fingerprinted endpoint identity snapshot per real gesture; it does not publish the catalog or compatibility graph.
- Bridge slots/properties/signals may live in plain-Python mixin modules composed with QObject; `tests/test_bridge_mixin_meta_registration.py` permanently pins the PyQt6 meta-object registration guarantees (including double-decorated overload slots and property/notify pairs) that the mixin packages rely on.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_bridge_surface_snapshot.py tests/test_bridge_mixin_meta_registration.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_data_type_ui_projection.py tests/test_graph_surface_input_controls.py -k "compatible_endpoint or ctrl_drag_reassigns" --ignore=venv -q
```

## Breadcrumbs
- [QML Shell And Bridge Layer](../subsystems/qml_shell_and_bridges.md)
- [Graph Scene Payload And Projection](graph_scene_payload_and_projection.md)
- [Durable Node Linking](durable_node_linking.md)
- [SSH/SFTP Nodes](ssh_sftp_nodes.md)

## Update Triggers
Update when bridge APIs, compatible-endpoint snapshot wiring, dynamic-port, sensitive-property, or optimization semantic-link command methods, durable node link bridge methods, fullscreen content bridge persistence or trim methods, context setup, QML bindings, or bridge tests change.

## 2026-05-31 Mutation UI Effects Update

- QML graph-scene mutation helpers still own payload rebuilds, node/edge delta publication, selection signals, and history replay deltas. Shell-only aftermath for graph edit actions now lives in `MutationUiEffects`; do not move QML scene publishers into the shell effect layer.

## 2026-07-11 Performance Ownership

- Stable bridge QObjects remain context-bound while their heavyweight internals allocate on first use. Fullscreen and Add-On Manager panes are retained URL-backed loaders; public context names, bridge types, focus, close, and object identity remain unchanged.
