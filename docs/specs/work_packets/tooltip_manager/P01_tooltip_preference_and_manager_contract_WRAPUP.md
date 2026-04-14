# P01 Tooltip Preference and Manager Contract Wrap-Up

## Implementation Summary
Packet: P01
Branch Label: codex/tooltip-manager/p01-tooltip-preference-and-manager-contract
Commit Owner: worker
Commit SHA: d08869c0c7a5e93f41a2a9a62314a79f6396204a
Changed Files:
- ea_node_editor/settings.py
- ea_node_editor/app_preferences.py
- ea_node_editor/ui/shell/tooltip_manager.py
- ea_node_editor/ui/shell/presenters/state.py
- ea_node_editor/ui/shell/presenters/workspace_presenter.py
- ea_node_editor/ui/shell/window_state/context_properties.py
- ea_node_editor/ui/shell/window_state/run_and_style_state.py
- ea_node_editor/ui/shell/window_state_helpers.py
- ea_node_editor/ui/shell/window.py
- tests/test_graphics_settings_preferences.py
Artifacts Produced:
- ea_node_editor/ui/shell/tooltip_manager.py
- tests/test_graphics_settings_preferences.py
- docs/specs/work_packets/tooltip_manager/P01_tooltip_preference_and_manager_contract_WRAPUP.md

Added the persisted `graphics.shell.show_tooltips` preference with a locked default of `true`, normalized missing or invalid values back to `true`, and kept it inside the existing app-preferences load/save pipeline. Mirrored the resolved value into shell workspace UI state, exposed `graphics_show_tooltips` on `ShellWindow`, and added the packet-local `set_graphics_show_tooltips` shell entry point plus a future-facing action sync helper without creating the `View > Show Tooltips` action in this packet.

Added the shell-owned `TooltipManager` contract so informational tooltips follow the global preference while warning and inactive explanations stay independently available. Extended the graphics preferences regression suite with `tooltip`-named coverage for defaulting, invalid normalization, persistence, runtime host application, the shell entry point, and the manager contract.

## Verification
PASS: .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py --ignore=venv -q
PASS: .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py -k tooltip --ignore=venv -q
Final Verification Verdict: PASS

## Manual Test Directives
Too soon for manual testing.

- Blocker: P01 does not add the `View > Show Tooltips` action.
- Blocker: P01 does not wire any existing QML tooltip surfaces to the new policy yet.
- Current validation is primarily automated through the graphics-preferences regression suite and the tooltip-only review gate.
- Manual testing becomes worthwhile once P02 lands the action and tooltip-surface adoption against `ShellWindow.graphics_show_tooltips`.

## Residual Risks
- Tooltip visibility is now persisted and surfaced through shell runtime state, but no user-visible tooltip surfaces consume it until P02.
- The regression coverage exercises the production preference pipeline and shell runtime adapter with a lightweight host harness, not a full bootstrapped `ShellWindow`.
- Both pytest commands exited successfully, but pytest emitted a non-fatal Windows temp-directory cleanup `PermissionError` in `pytest-current` during process shutdown.

## Ready for Integration
Yes: P01 is ready for downstream packets to consume. The preference schema, runtime shell property, shell entry point, and tooltip manager contract are in place and verified.
