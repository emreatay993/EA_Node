# ARCH_FIFTH_PASS P01: Startup And Preferences Boundary

## Objective
- Unify all app startup entrypoints behind one package-local bootstrap path, isolate startup preferences resolution from UI-host concerns, and relocate the QML performance harness behind an honest package boundary without changing any observable startup or benchmark behavior.

## Preconditions
- `P00` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- startup entrypoints and package bootstrap
- app-preferences persistence/normalization boundary
- performance-harness module ownership and compatibility surface
- startup and preferences regression tests

## Conservative Write Scope
- `main.py`
- `pyproject.toml`
- `ea_node_editor/bootstrap.py`
- `ea_node_editor/app.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/perf/__init__.py`
- `ea_node_editor/ui/perf/performance_harness.py`
- `ea_node_editor/telemetry/performance_harness.py`
- `tests/test_main_bootstrap.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graph_theme_preferences.py`
- `tests/test_track_h_perf_harness.py`
- `docs/specs/work_packets/arch_fifth_pass/P01_startup_preferences_boundary_WRAPUP.md`

## Required Behavior
- Introduce a package-local bootstrap module that becomes the single startup path for both source execution and the installed console script.
- Change the installed console script target to the package-local bootstrap path so source launch and installed launch share the same control flow.
- Extract UI-independent app-preferences persistence/normalization and startup-theme resolution into a pure service module.
- Keep `AppPreferencesController` as the UI-facing adapter for host application behavior, but remove startup bootstrap dependence on it.
- Move the concrete QML performance harness implementation out of `ea_node_editor.telemetry` into a non-telemetry module while preserving the public import path `ea_node_editor.telemetry.performance_harness` via a compatibility shim or equivalent adapter.
- Preserve the current startup theme selection, app launch flow, benchmark behavior, and public CLI behavior exactly.

## Non-Goals
- No `ShellWindow` composition-root extraction in this packet.
- No shell/controller decomposition in this packet.
- No QML bridge or graph mutation changes in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_graphics_settings_preferences.py tests/test_graph_theme_preferences.py tests/test_track_h_perf_harness.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P01_startup_preferences_boundary_WRAPUP.md`

## Acceptance Criteria
- Source launch and installed console launch resolve through the same package-local bootstrap path.
- Startup theme resolution no longer depends on the UI controller layer.
- The performance harness public import path continues to work while its concrete implementation no longer lives in the `telemetry` package.
- Packet verification passes in the project venv with no user-visible startup or benchmark behavior changes.

## Handoff Notes
- `P02` owns the full shell composition-root extraction; keep this packet limited to startup/bootstrap and preferences boundary work.
- Preserve compatibility shims rather than forcing call-site churn outside the packet scope.
