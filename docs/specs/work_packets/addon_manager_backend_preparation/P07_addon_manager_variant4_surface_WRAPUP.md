# P07 Add-On Manager Variant 4 Surface Wrap-Up

## Implementation Summary

- Packet: `P07`
- Branch Label: `codex/addon-manager-backend-preparation/p07-addon-manager-variant4-surface`
- Commit Owner: `worker`
- Commit SHA: `36cd6f4eafcf3032d23fd5286ac0974669033531`
- Changed Files: `docs/specs/work_packets/addon_manager_backend_preparation/P07_addon_manager_variant4_surface_WRAPUP.md`, `ea_node_editor/ui/shell/presenters/__init__.py`, `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`, `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`, `tests/test_main_window_shell.py`, `tests/main_window_shell/shell_basics_and_search.py`, `tests/main_window_shell/bridge_qml_boundaries.py`
- Artifacts Produced: `docs/specs/work_packets/addon_manager_backend_preparation/P07_addon_manager_variant4_surface_WRAPUP.md`, `ea_node_editor/ui/shell/presenters/__init__.py`, `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`, `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`, `tests/test_main_window_shell.py`, `tests/main_window_shell/shell_basics_and_search.py`, `tests/main_window_shell/bridge_qml_boundaries.py`

- Replaced the temporary P02 placeholder overlay with a packet-owned Variant 4 inspector-style Add-On Manager surface wired into `MainShell.qml`, including the left list, right detail pane, badge/banner semantics, tabs, close path, and the retained Workflow Settings fallback entry.
- Added a packet-owned presenter plus Python/QML bridge that read the P01 add-on contract, resolve add-on focus requests from the shell entry point introduced in P02, and project stable row/detail payloads for the manager surface.
- Wired the DPF add-on toggle through the P06 hot-apply lifecycle so the manager can refresh add-on state, rebuild the live registry, update serializer/session references, and surface restart/pending-restart status in the Variant 4 UI.
- Refreshed the packet-owned shell tests to validate the new surface, bridge registration, presenter package export, and the menubar-to-surface open/focus flow for the canonical DPF add-on id.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py -k addon_manager -q --ignore=venv`
- FAIL: `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_basics_and_search.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q` (`tests/test_main_window_shell.py::MainWindowShellCommentBackdropWorkflowTests::test_backdrop_resize_recomputes_nested_membership_without_moving_unrelated_nodes` timed out waiting for backdrop resize to update the workspace model)
- PASS: `.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
- Final Verification Verdict: FAIL

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree from `C:\w\ea_node_ed-p07` with `.\venv\Scripts\python.exe main.py` in a normal desktop session. Keep manual focus on the Add-On Manager surface; the known automated failure in this worktree is in an unrelated comment-backdrop resize path.

1. Menubar open and close
Action: start the app, open `Add-On Manager` from the top-level menubar, then close it with the surface `Close` button and with `Esc`.
Expected result: the Variant 4 inspector-style manager opens between the main toolbar and status strip, the workspace row is hidden while it is open, and the previous shell layout returns when it closes.

2. Variant 4 detail surface smoke
Action: reopen `Add-On Manager`, select the `ANSYS DPF` row in the left pane, and inspect the right pane.
Expected result: the right pane shows the `ANSYS DPF` title, vendor/id metadata, the policy badge, the `About`, `Dependencies`, `Nodes`, and `Changelog` tabs, and the dependency/node content reflects the live add-on contract instead of placeholder copy.

3. DPF toggle lifecycle
Action: if the `ANSYS DPF` row is available, use the row toggle or the primary `Enable`/`Disable` button to flip its enabled state, then flip it back.
Expected result: the manager stays open, the selected add-on stays focused, the enabled state updates in place, and the shell remains responsive while the live registry-backed surface refreshes. If the add-on is unavailable in the local environment, the toggle remains disabled and the availability message explains why.

## Residual Risks

- The required full packet verification command is blocked by `tests/test_main_window_shell.py::MainWindowShellCommentBackdropWorkflowTests::test_backdrop_resize_recomputes_nested_membership_without_moving_unrelated_nodes`, which exercises comment-backdrop resize behavior outside this packet's write scope.
- The current catalog in this worktree still exposes only the DPF-backed add-on path, so the restart-required badge/banner semantics remain exercised primarily through the stable contract and UI projection rather than through a second live restart-only add-on.
- The `Workflow Settings` button remains a temporary fallback path until a later packet replaces the legacy plugin list with the manager-native configuration flow.

## Ready for Integration

- No: the packet-owned Add-On Manager implementation and review gate pass, but the required full verification command still fails on an unrelated comment-backdrop resize test outside the packet scope.
