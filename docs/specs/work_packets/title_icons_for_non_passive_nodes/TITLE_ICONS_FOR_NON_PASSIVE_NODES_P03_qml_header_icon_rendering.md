# TITLE_ICONS_FOR_NON_PASSIVE_NODES P03: QML Header Icon Rendering

## Objective
- Render a path-based title-leading image for eligible non-passive nodes using `nodeData.icon_source`, while preserving existing title layout, editing, centered-title behavior, elision, and collapsed comment-backdrop icon behavior.

## Preconditions
- `P01` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- `P02` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- No later `TITLE_ICONS_FOR_NON_PASSIVE_NODES` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostLayout.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`
- `tests/graph_surface/inline_editor_suite.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/test_icon_registry.py`
- `tests/test_comment_backdrop_contracts.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostLayout.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`
- `tests/graph_surface/inline_editor_suite.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_rendering_suite.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/test_icon_registry.py`
- `tests/test_comment_backdrop_contracts.py`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P03_qml_header_icon_rendering_WRAPUP.md`

## Required Behavior
- Add a title-leading `Image` in `GraphNodeHeaderLayer.qml` that uses `nodeData.icon_source`.
- Render the image only when:
  - `headerTitleVisible` is true
  - the title display is not editing
  - `nodeData.icon_source` is non-empty
  - the host is not a passive node
- Use the P02 shared effective node-title icon size property for width, height, and `sourceSize`.
- Use `Image.PreserveAspectFit`, `smooth: true`, and `mipmap: true`; do not theme-tint the image.
- Keep the authored image colors intact.
- Keep title elision stable by reserving icon width and spacing before the title text.
- Keep centered titles visually centered with icon reserve width accounted for.
- Keep `titleHitRegion`, `titleEditorInteractionRegion`, and title edit behavior aligned with the displayed text and icon reserve.
- Preserve the existing collapsed comment-backdrop icon path and behavior:
  - do not replace `commentTitleIconSource`
  - do not remove the current `uiIcons.sourceSized("comment", ...)` contract
  - keep collapsed comment backdrops using the existing symbolic/tintable comment icon
- Preserve existing object names used by tests: `graphNodeTitleDisplay`, `graphNodeTitle`, `graphNodeTitleEditor`, `graphNodeCard`, and `graphCommentBackdropInputCard`.
- Add packet-owned regression tests whose names include `title_icon` so the targeted verification commands below remain stable.

## Non-Goals
- No Python resolver or payload changes.
- No settings, dialog, or bridge changes.
- No built-in asset migration.
- No node-library or inspector icon rendering.
- No changes to passive body/title visual-style authority.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/inline_editor_suite.py tests/graph_surface/passive_host_interaction_suite.py tests/graph_track_b/qml_preference_rendering_suite.py -k title_icon --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py tests/main_window_shell/shell_runtime_contracts.py tests/test_icon_registry.py tests/test_comment_backdrop_contracts.py -k title_icon --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k title_icon --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P03_qml_header_icon_rendering_WRAPUP.md`

## Acceptance Criteria
- Expanded active and `compile_only` nodes render a valid `icon_source` before the title.
- Passive nodes do not render a title icon.
- Long titles still elide without shifting the header layout.
- Centered titles remain centered while leaving appropriate icon reserve.
- Title editing and title hit regions remain usable.
- Collapsed comment-backdrop icons still render through the existing `uiIcons` comment path.
- Packet-owned `title_icon` QML/graph-surface regressions pass.

## Handoff Notes
- `P04` may add built-in assets that flow through this renderer after migration, but P04 must not rename QML object names or rework the title layout.
- Any later packet that changes title reserve math, title object names, icon visibility, or the collapsed comment-backdrop icon path must inherit and update the tests listed in this packet.
