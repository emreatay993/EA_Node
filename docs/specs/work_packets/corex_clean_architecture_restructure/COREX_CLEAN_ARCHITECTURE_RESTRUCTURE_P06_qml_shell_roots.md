# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P06: QML Shell Roots

## Objective

Make shell-level QML ports explicit so `MainShell.qml` and shell pane roots pass narrow feature references instead of leaf QML reaching into ambient `shellContext`.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and QML shell/bridge files needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P05_shell_composition` is `PASS`.

## Execution Dependencies

- `P05_shell_composition`

## Target Subsystems

- QML shell root and shell components
- Shell context bootstrap
- Feature-owned shell bridge properties
- Shell/QML contract tests

## Conservative Write Scope

- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/components/shell/**`
- `ea_node_editor/ui_qml/shell_*_bridge.py`
- `ea_node_editor/ui_qml/theme_bridge.py`
- `ea_node_editor/ui_qml/graph_theme_bridge.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/**`
- `tests/test_graph_action_contracts.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P06_qml_shell_roots_WRAPUP.md`

## Required Behavior

- Keep `shell_context_bootstrap.py` as the only root context-property fanout.
- Pass shell, workspace, library, theme, graph-theme, fullscreen, help, and viewer references from feature roots rather than leaf globals.
- Preserve existing QML affordances, menu labels, actions, shortcuts, and bridge names required by tests.
- Add or adjust tests that prevent new leaf-level `shellContext` reach for migrated shell surfaces.

## Non-Goals

- Do not refactor graph-canvas internals; that is `P07`.
- Do not move viewer/overlay policy; that is `P08`.
- Do not rename public bridge methods unless compatibility is retained.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_action_contracts.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/main_window_shell --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P06_qml_shell_roots_WRAPUP.md`

## Acceptance Criteria

- Shell root QML owns service distribution; migrated leaf components use explicit properties.
- Existing shell/QML contracts remain compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If a non-graph QML global still owns real feature behavior, leave it in place and record the reason instead of forcing a broad move.
