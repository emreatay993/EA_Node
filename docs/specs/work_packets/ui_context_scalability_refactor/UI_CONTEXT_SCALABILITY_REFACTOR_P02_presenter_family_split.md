# UI_CONTEXT_SCALABILITY_REFACTOR P02: Presenter Family Split

## Objective

- Replace the monolithic presenter module with one presenter per file behind a curated package import surface so ordinary shell UI work no longer requires loading every presenter family into one context.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P01`

## Target Subsystems

- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui/shell/presenters/contracts.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/presenters/inspector_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_host_presenter.py`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_main_window_shell.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/shell_basics_and_search.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/presenters.py`
- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui/shell/presenters/contracts.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/presenters/inspector_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_host_presenter.py`
- `ea_node_editor/ui/shell/composition.py`
- `tests/test_main_window_shell.py`
- `tests/test_window_library_inspector.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P02_presenter_family_split_WRAPUP.md`

## Required Behavior

- Replace `ea_node_editor/ui/shell/presenters.py` with a package surface rooted at `ea_node_editor/ui/shell/presenters/`.
- Move shared protocols into `contracts.py` and shared UI-state dataclasses into `state.py`.
- Put each presenter class in its own module: `library_presenter.py`, `workspace_presenter.py`, `inspector_presenter.py`, `graph_canvas_presenter.py`, and `graph_canvas_host_presenter.py`.
- Keep `ea_node_editor.ui.shell.presenters` as the curated import surface via `__init__.py`; update packet-owned imports to use the package surface rather than direct file paths.
- End each presenter implementation file at or below `450` lines and keep `__init__.py` at or below `120` lines.

## Non-Goals

- No graph-scene or graph-canvas packetization yet.
- No new presenter behavior, signals, or QML surface features.
- No viewer-specific cleanup yet.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_window_library_inspector.py tests/main_window_shell/bridge_contracts.py tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_window_library_inspector.py tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P02_presenter_family_split_WRAPUP.md`
- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui/shell/presenters/contracts.py`
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/presenters/inspector_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_host_presenter.py`

## Acceptance Criteria

- Packet-owned presenter code no longer lives in one omnibus file.
- The curated `ea_node_editor.ui.shell.presenters` import surface remains stable for packet-owned callers.
- The inherited shell basics, bridge, and inspector anchors pass.

## Handoff Notes

- `P03` should build graph-scene packetization on top of the slimmer shell and presenter surfaces from `P01` and `P02`.
