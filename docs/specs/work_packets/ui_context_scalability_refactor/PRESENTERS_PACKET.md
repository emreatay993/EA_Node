# Presenters Packet

Baseline packet: `P02 Presenter Family Split`.

Use this contract when a change affects presenter projection, presenter package imports, shell workspace UI projection state, or packet-owned presenter coordination between library, workspace, inspector, and graph-canvas surfaces.

## Owner Files

- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui/shell/presenters/contracts.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/presenters/inspector_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_host_presenter.py`

## Public Entry Points

- The curated `ea_node_editor.ui.shell.presenters` package surface
- `ShellLibraryPresenter`
- `ShellWorkspacePresenter`
- `ShellInspectorPresenter`
- `GraphCanvasPresenter`
- `GraphCanvasHostPresenter`
- `ShellWorkspaceUiState`
- `build_default_shell_workspace_ui_state()`

## State Owner

- Presenter code owns projection and presentation state only.
- `ShellWorkspaceUiState` in `state.py` is the packet-owned shared UI state carrier.
- Authoritative graph, project, run, and session state remains on shell controllers, bridges, and the underlying model rather than inside presenter modules.

## Allowed Dependencies

- Presenter modules may depend on shell host adapters, packet-owned shared state, normalized preference helpers, and library-inspector projection helpers.
- Presenter modules may project bridge or controller state into QML-friendly structures, but they do not become graph or persistence authorities.
- Packet-owned imports should use the curated package surface whenever a caller only needs the public presenter API.

## Invariants

- One presenter implementation file per presenter family.
- Shared presenter protocols stay in `contracts.py`, and shared UI-state dataclasses stay in `state.py`.
- Packet-owned callers treat `ea_node_editor.ui.shell.presenters` as the stable import surface.
- Presenter code projects host state; it does not create a second canonical store for library, workspace, inspector, or graph-canvas state.

## Forbidden Shortcuts

- Do not reintroduce an omnibus `presenters.py` implementation file.
- Do not let packet-owned callers bypass the curated package surface without a documented reason.
- Do not move authoritative graph or shell workflow state into presenter-local caches.
- Do not couple one presenter to another through undocumented private state when the host or shared state contract should carry the value.

## Required Tests

- `tests/test_main_window_shell.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/shell_basics_and_search.py`
