# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P11: Cross-Cutting Services

## Objective

Promote settings/preferences, shell theme, graph theme, telemetry/status, project-session I/O support, and viewer-presentation coordination into explicit application services where they currently leak through shell/QML adapters.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and service/theme/status tests needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P10_plugin_addon_descriptor` is `PASS`.

## Execution Dependencies

- `P10_plugin_addon_descriptor`

## Target Subsystems

- Application preferences and settings normalization
- Shell theme and graph theme services
- Telemetry/status collection and presentation
- Project-session support services
- Viewer presentation coordinator handoffs left by `P08` or `P10`

## Conservative Write Scope

- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/telemetry/**`
- `ea_node_editor/ui/theme/**`
- `ea_node_editor/ui/graph_theme/**`
- `ea_node_editor/ui/support/**`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_services_support/**`
- `ea_node_editor/ui/shell/host_presenter.py`
- `ea_node_editor/ui_qml/theme_bridge.py`
- `ea_node_editor/ui_qml/graph_theme_bridge.py`
- `tests/test_shell_theme.py`
- `tests/test_graph_theme_preferences.py`
- `tests/test_project_session_controller_unit.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P11_cross_cutting_services_WRAPUP.md`

## Required Behavior

- Keep `AppPreferencesStore` service-like and tighten its boundary instead of adding duplicate configuration state.
- Split shell theme and graph theme resolution into explicit services, with QML bridges as thin adapters.
- Extract telemetry/status collection and formatting away from broad shell presenter/window-state modules where feasible.
- Preserve graphics preferences, live theme behavior, project-session save/load flows, and status presentation behavior.

## Non-Goals

- Do not reopen persistence schema changes owned by `P04`.
- Do not reopen shell composition structure owned by `P05` unless this packet only moves service implementation behind existing interfaces.
- Do not move viewer overlay geometry owned by `P08`.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_shell_theme.py tests/test_graph_theme_preferences.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_project_session_controller_unit.py tests/test_main_window_shell.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_graph_theme_preferences.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P11_cross_cutting_services_WRAPUP.md`

## Acceptance Criteria

- Cross-cutting behavior has clearer service ownership and thinner presentation adapters.
- Existing preferences, theme, status, and project-session behavior remains compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If this packet discovers a service split that would force broad shell/QML rewrites, leave an adapter and document the future work instead of expanding scope.
