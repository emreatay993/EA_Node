# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P05: Shell Composition

## Objective

Keep `composition.py` as the only full shell object-graph assembly root, reduce `ShellWindow` to a thin Qt host/compatibility surface, and move feature behavior into explicit controllers, presenters, or application services.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and shell/test files needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P04_current_schema_persistence` is `PASS`.

## Execution Dependencies

- `P04_current_schema_persistence`

## Target Subsystems

- Shell composition and dependency factory
- `ShellWindow` compatibility methods
- Shell controllers and presenters
- Window action/state modules
- Main-window shell tests and shell-isolated controller targets

## Conservative Write Scope

- `ea_node_editor/ui/shell/**`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/**`
- `tests/test_shell_window_lifecycle.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_isolation_phase.py`
- `tests/shell_isolation_*`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P05_shell_composition_WRAPUP.md`

## Required Behavior

- Keep `ShellWindow` lifecycle, signals, top-level properties, and compatibility slots stable.
- Move non-host feature behavior from `ShellWindow`/`window_state/*` into owning controllers, presenters, or services.
- Keep `GraphActionController` routing-only and avoid adding feature logic there.
- Preserve menus, shortcuts, status behavior, project/session flow, and shell/QML bridge contracts.

## Non-Goals

- Do not restructure QML files; those are owned by later packets.
- Do not change graph mutation or persistence semantics unless a shell API handoff requires a minimal adapter.
- Do not run broad shell-isolation phases unless packet-local shell commands are insufficient.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/test_shell_window_lifecycle.py tests/test_shell_project_session_controller.py tests/test_shell_run_controller.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_shell_isolation_phase.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P05_shell_composition_WRAPUP.md`

## Acceptance Criteria

- Shell host behavior remains compatible while feature behavior has clearer owners.
- Shell composition remains the only full object-graph wiring point.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If a shell compatibility method must remain, leave it as a one-line delegate to the owning controller/service and record the remaining compatibility reason.
