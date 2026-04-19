## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/addon-manager-backend-preparation/p02-addon-manager-entry-and-open-request-plumbing`
- Commit Owner: `worker`
- Commit SHA: `0bf01e34f3738b1928cdb944f9ce34c2f13a664f`
- Changed Files: `docs/specs/work_packets/addon_manager_backend_preparation/P02_addon_manager_entry_and_open_request_plumbing_WRAPUP.md`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/window_actions.py`, `ea_node_editor/ui_qml/MainShell.qml`, `tests/main_window_shell/shell_basics_and_search.py`, `tests/test_main_window_shell.py`
- Artifacts Produced: `docs/specs/work_packets/addon_manager_backend_preparation/P02_addon_manager_entry_and_open_request_plumbing_WRAPUP.md`

- Added a top-level `Add-On Manager` menubar action with stable shell action naming and placement before `Settings`, preserving the existing workflow-settings and shell startup paths.
- Introduced a shell-owned add-on manager request seam on `ShellWindow` that preserves `open`, `focus_addon_id`, and a monotonic request serial so later graph affordances and the final manager surface can reopen or retarget the same add-on deterministically.
- Added a narrow QML-facing `AddonManagerBridge` and a temporary packet-owned overlay in `MainShell.qml` so the new entry point is observable now without spending `P07` scope on the final Variant 4 surface.
- Expanded the shell regression anchors to cover menubar placement, request-state preservation, context registration, repeated open requests, and the temporary overlay contract.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree build from `C:\w\ea_node_ed-p02-c09971` with `.\venv\Scripts\python.exe main.py` in a normal desktop session.

1. Menubar entry smoke
Action: start the app and inspect the top-level menubar entries.
Expected result: `Add-On Manager` appears as its own top-level menubar entry before `Settings`, and the existing `Settings` menu still contains `Workflow Settings` and `Graphics Settings`.

2. Open and close request smoke
Action: click `Add-On Manager`, confirm the temporary shell overlay appears, then close it by clicking `Close` or outside the panel.
Expected result: the placeholder overlay opens and closes cleanly without disturbing the current workspace, graph state, or the existing shell overlays.

3. Internal focus-target follow-up
Action: treat automated verification as the primary validation for add-on-targeted focus in this packet.
Expected result: the packet-owned tests prove repeated open requests retain the latest `focus_addon_id` and advance the request serial even though no graph-node entry point exists yet.

## Residual Risks

- The packet-owned overlay is intentionally temporary and does not implement the final Variant 4 inspector-style manager; `P07` still needs to replace it with the real surface on top of this request seam.
- No catalog-backed validation of `focus_addon_id` exists yet in this worktree, so the shell preserves requested ids generically and defers add-on resolution to later packets.
- Ambient ANSYS DPF deprecation warnings still surface during the inherited shell test suite and remain outside this packet's write scope.

## Ready for Integration

- Yes: the new menubar entry, shell request contract, temporary observable surface, and packet-owned regressions all passed the required verification and review-gate commands, and the remaining work is explicitly deferred to later add-on-manager packets.
