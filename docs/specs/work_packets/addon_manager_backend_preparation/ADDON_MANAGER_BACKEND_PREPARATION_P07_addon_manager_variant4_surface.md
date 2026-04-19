# ADDON_MANAGER_BACKEND_PREPARATION P07: Add-On Manager Variant 4 Surface

## Objective

- Build the faithful Variant 4 inspector-style Add-On Manager opened from the menubar, backed by the add-on contracts from `P01`, the shell entry point from `P02`, and the live DPF toggle behavior from `P06`.

## Preconditions

- `P00` is marked `PASS`.
- `P01` is marked `PASS`.
- `P02` is marked `PASS`.
- `P06` is marked `PASS`.
- No later `ADDON_MANAGER_BACKEND_PREPARATION` packet is in progress.

## Execution Dependencies

- `P00`
- `P01`
- `P02`
- `P06`

## Target Subsystems

- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui/shell/presenters/_addon_manager_payloads.py`
- `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`
- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`

## Conservative Write Scope

- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui/shell/presenters/_addon_manager_payloads.py`
- `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`
- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_basics_and_search.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P07_addon_manager_variant4_surface.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/P07_addon_manager_variant4_surface_WRAPUP.md`

## Required Behavior

- Render the manager as a faithful Variant 4 inspector-style two-pane surface rather than a modal settings page or another mockup variant.
- Open the manager from the menubar entry from `P02` and honor open requests that target a specific add-on id.
- Drive the left-side add-on list and right-side detail tabs from the stable add-on contract in `P01`.
- Surface `restart_required` and pending-restart status with the Variant 4 banner/badge semantics, and surface live DPF `hot_apply` toggles through the lifecycle from `P06`.
- Keep the current workflow-settings plugin list as temporary fallback unless a change is strictly required for consistency.

## Non-Goals

- No marketplace/discovery variants.
- No second add-on migration beyond DPF.
- No further graph lock-state changes beyond consuming the affordance hook from `P04`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_basics_and_search.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/addon_manager_backend_preparation/P07_addon_manager_variant4_surface_WRAPUP.md`

## Acceptance Criteria

- The shell opens a faithful Variant 4 Add-On Manager from the menubar.
- Add-on list, detail pane, tabs, restart states, and DPF toggle behavior are backed by the real add-on contract and lifecycle.
- Locked-node affordances can focus the manager on the relevant add-on.
- The inherited shell/QML bridge regression anchors pass.

## Handoff Notes

- `P08` documents the final user-visible and verification evidence for the implemented manager and DPF lifecycle. Keep this packet focused on product surface and shell wiring, not on closeout docs.
