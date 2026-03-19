# ARCH_FIFTH_PASS P02: Shell Composition Root

## Objective
- Move shell object construction out of `ShellWindow` into an explicit composition module so `ShellWindow` becomes a host/facade that receives prebuilt collaborators while preserving exact runtime behavior.

## Preconditions
- `P01` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- shell composition root and bootstrap bundle creation
- `ShellWindow` initialization and collaborator ownership
- shell startup regression coverage

## Conservative Write Scope
- `ea_node_editor/app.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_project_session_controller.py`
- `docs/specs/work_packets/arch_fifth_pass/P02_shell_composition_root_WRAPUP.md`

## Required Behavior
- Introduce a dedicated shell composition module that constructs registry, serializer, stores, model, history, bridges, presenters, controllers, timers, and QML widget dependencies before `ShellWindow` uses them.
- Change `ShellWindow` so it accepts the prebuilt shell bundle instead of constructing those objects directly.
- Keep `ShellWindow` responsible for native window lifecycle, top-level signal wiring, and public host slots/properties, but not for assembling the application graph.
- Preserve the current `ShellWindow` behavioral surface, runtime ordering, startup signals, and test-visible shell context behavior exactly.

## Non-Goals
- No controller splitting in this packet; `P03` owns that.
- No QML bridge contract cleanup in this packet; `P04` and `P05` own that.
- No mutation-boundary or persistence/runtime changes in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/test_shell_run_controller.py tests/test_shell_project_session_controller.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P02_shell_composition_root_WRAPUP.md`

## Acceptance Criteria
- `ShellWindow` no longer directly constructs the application graph that the composition module can build beforehand.
- Startup, shell context bootstrapping, run-control behavior, and session behavior remain exactly unchanged from the user/test point of view.
- Packet verification passes in the project venv under offscreen Qt.

## Handoff Notes
- Keep any compatibility constructors or helpers internal to the packet scope; do not widen public API churn.
- `P03` assumes the new composition root exists and can inject focused controller surfaces cleanly.
