# P07 Add-On Manager Variant 4 Surface Wrap-Up

## Implementation Summary

- Packet: `P07`
- Branch Label: `codex/addon-manager-backend-preparation/p07-addon-manager-variant4-surface`
- Commit Owner: `worker`
- Commit SHA: `68f9aa8fe56e165967ca2a6730d9c0ec6594c526`
- Changed Files: `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P07_addon_manager_variant4_surface.md`, `docs/specs/work_packets/addon_manager_backend_preparation/P07_addon_manager_variant4_surface_WRAPUP.md`, `ea_node_editor/ui/shell/presenters/__init__.py`, `ea_node_editor/ui/shell/presenters/_addon_manager_payloads.py`, `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`, `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`, `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`, `tests/main_window_shell/bridge_qml_boundaries.py`, `tests/main_window_shell/shell_basics_and_search.py`, `tests/test_main_window_shell.py`
- Artifacts Produced: `docs/specs/work_packets/addon_manager_backend_preparation/P07_addon_manager_variant4_surface_WRAPUP.md`, `ea_node_editor/ui/shell/presenters/__init__.py`, `ea_node_editor/ui/shell/presenters/_addon_manager_payloads.py`, `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`, `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`, `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`, `tests/main_window_shell/bridge_qml_boundaries.py`, `tests/main_window_shell/shell_basics_and_search.py`, `tests/test_main_window_shell.py`

- Corrected the packet surface toward the authoritative Variant 4 handoff by keeping the Add-On Manager as an inspector-style right drawer, aligning the top action bar semantics, enriching list rows with category/status metadata, and expanding the detail pane tabs with contract-backed dependency, node, runtime, and changelog facts.
- Split the add-on payload shaping into a private presenter helper so the richer Variant 4 data model stays inside the curated presenter package line budget while preserving the packet-owned shell bridge and presenter contract.
- Applied the user-authorized verification stabilization outside the original packet scope in `alignment_and_distribution_ops.py` so direct geometry commits clamp comment backdrops to the same minimum size rules already enforced by the resize path.
- Refreshed the packet-owned shell tests to cover the drawer-style presentation, menu open/focus flow, and updated QML boundary markers for the Variant 4 surface.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py -k addon_manager --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k 'test_backdrop_resize_recomputes_nested_membership_without_moving_unrelated_nodes' --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_basics_and_search.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree from `C:\w\ea_node_ed-p07` with `.\venv\Scripts\python.exe main.py` in a normal desktop session.

1. Drawer open and close
Action: open `Add-On Manager` from the top-level menubar, then dismiss it once by clicking the dark scrim outside the drawer and once by pressing `Esc`.
Expected result: the Variant 4 manager opens as a right-side inspector drawer between the main toolbar and status strip, the workspace row remains in place behind the scrim, and both close paths return the shell to its prior state.

2. Variant 4 fidelity smoke
Action: reopen `Add-On Manager`, select `ANSYS DPF` in the left pane, and inspect the toolbar, row presentation, and detail pane.
Expected result: the toolbar shows `Check for updates`, `Install from File...`, the conditional restart affordance, and the temporary `Workflow Settings` fallback; list rows show category glyphs, summary, version/node metadata, and state badges; the right pane exposes `About`, `Dependencies`, `Nodes`, and `Changelog` with vendor, id, category, dependency, and node facts from the live add-on contract.

3. Toggle and pending-restart behavior
Action: if `ANSYS DPF` is available, use the row toggle or the primary enable/disable action to change its state and then restore it. If a pending-restart state appears, inspect the banner and toolbar restart affordances.
Expected result: the drawer stays open, the selected add-on remains focused, live hot-apply changes refresh the row and detail state in place, unavailable add-ons keep their toggle disabled with an explanation, and pending-restart status appears with the Variant 4 badge/banner semantics while restart controls remain visible until later backend wiring enables them.

## Residual Risks

- `Check for updates`, `Install from File...`, and `Restart Runtime` now match the Variant 4 surface semantics, but they remain intentionally disabled until follow-on backend packets wire those actions.
- The current workspace still exposes a narrow live add-on set, so some richer restart-only permutations are represented through the stable contract and UI state rather than through multiple real add-ons.
- The comment-backdrop clamp fix in `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py` is a user-authorized stabilization outside the original P07 scope; it is intentionally minimal and targeted at the required verification path.

## Ready for Integration

- Yes: the Variant 4 surface is aligned to the authoritative handoff within the current contracts, the required packet verification command passes, and the review gate passes.
