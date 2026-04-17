# MEDIA_VIEWER_CONTENT_FULLSCREEN P01: Fullscreen State Contract

## Objective

- Add the shell-owned `contentFullscreenBridge` request/state contract for opening, toggling, and closing transient content fullscreen for eligible media and DPF viewer nodes.

## Preconditions

- `P00` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- No later `MEDIA_VIEWER_CONTENT_FULLSCREEN` packet is in progress.

## Execution Dependencies

- none

## Target Subsystems

- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_content_fullscreen_bridge.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_window_lifecycle.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_content_fullscreen_bridge.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_window_lifecycle.py`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P01_fullscreen_state_contract_WRAPUP.md`

## Required Behavior

- Add a `contentFullscreenBridge` QML context property during shell composition/bootstrap.
- Keep fullscreen state shell-owned and transient. Do not add or require any project persistence field.
- Expose read-only bridge state for `open`, `node_id`, `workspace_id`, `content_kind`, `title`, `media_payload`, `viewer_payload`, and `last_error`.
- Emit a `content_fullscreen_changed` signal whenever externally visible bridge state changes.
- Add slots:
  - `request_open_node(node_id) -> bool`
  - `request_toggle_for_node(node_id) -> bool`
  - `request_close()`
  - `can_open_node(node_id) -> bool`
- Treat image media, PDF media, and DPF viewer nodes as eligible. Treat missing nodes, unsupported node kinds, missing media paths, and ambiguous workspace state as ineligible.
- Normalize media payloads using the same source, crop, fit, and PDF preview/page semantics already used by graph media previews.
- Populate viewer payloads with the current workspace/node identifiers and enough status metadata for later QML and native viewer packets to render a fullscreen proxy or live viewer target without duplicating node lookup logic.
- Enforce a one-active-fullscreen invariant. Opening a new eligible node replaces the previous fullscreen state atomically.
- Close and clear state on explicit close, workspace switch, graph teardown, and node deletion.
- Keep graph scene payloads and `.sfe` project data free of fullscreen state.
- Add packet-owned tests whose names include `content_fullscreen` so the targeted verification commands remain stable.

## Non-Goals

- No QML overlay rendering in this packet.
- No media fullscreen button, viewer toolbar button, `F11`, or graph hint UI changes.
- No native viewer widget retargeting.
- No icon registry or SVG asset changes.
- No saved-project schema or migration changes.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_main_window_shell.py tests/test_shell_window_lifecycle.py -k content_fullscreen --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py -k content_fullscreen --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/media_viewer_content_fullscreen/P01_fullscreen_state_contract_WRAPUP.md`
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `tests/test_content_fullscreen_bridge.py`

## Acceptance Criteria

- The shell exposes `contentFullscreenBridge` to QML without regressing existing shell context properties.
- Eligible image, PDF, and viewer nodes can be opened through the bridge.
- Ineligible nodes return `False`, keep fullscreen closed, and leave a useful bridge error state.
- Media payloads preserve existing preview path, PDF page/preview, crop, and fit interpretation.
- Fullscreen state closes on workspace switch and node deletion.
- Only one fullscreen state is active at a time.
- No project serialization, saved document payload, or graph model persistence test needs to change for fullscreen state.

## Handoff Notes

- `P02` consumes `media_payload`, `viewer_payload`, and bridge close semantics in QML. Any rename or payload-shape change after this packet must inherit and update `tests/test_content_fullscreen_bridge.py`.
- `P03` consumes `request_toggle_for_node`, `request_open_node`, `request_close`, and `can_open_node` from graph-surface controls and shortcut handling.
- `P04` consumes `viewer_payload` and the bridge lifecycle for native viewer retargeting. If P04 changes the viewer payload or close lifecycle contract, it must inherit and update `tests/test_content_fullscreen_bridge.py`.
