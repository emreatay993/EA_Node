# VERIFICATION_SPEED P01: Pytest Selection Classification

## Objective
- Centralize pytest `gui` and `slow` classification so fast, GUI, and slow verification phases can be split without changing product code or editing dozens of test modules by hand.

## Preconditions
- `P00` is marked `PASS` in [VERIFICATION_SPEED_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md).
- No later `VERIFICATION_SPEED` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `tests/conftest.py`
- pytest collection/marker behavior for representative non-GUI, GUI, and slow modules

## Conservative Write Scope
- `tests/conftest.py`

## Required Behavior
- Add a centralized pytest collection hook in `tests/conftest.py` that applies the existing `gui` and `slow` markers by stable nodeid or path patterns.
- Keep the existing session-scoped `QApplication` fixture and `ShellTestEnvironment` behavior unchanged.
- Ensure `gui` classification covers the repo's Qt/QML-heavy suites used by the planned runner, including at least:
  - `tests/test_shell_theme.py`
  - `tests/test_flow_edge_labels.py`
  - `tests/test_flowchart_surfaces.py`
  - `tests/test_flowchart_visual_polish.py`
  - `tests/test_graph_surface_input_controls.py`
  - `tests/test_passive_graph_surface_host.py`
  - `tests/test_passive_image_nodes.py`
  - `tests/test_passive_style_dialogs.py`
  - `tests/test_passive_style_presets.py`
  - `tests/test_pdf_preview_provider.py`
  - `tests/test_planning_annotation_catalog.py`
  - the four shell-isolated wrapper modules covered in `P02`
- Ensure `slow` classification covers `tests/test_track_h_perf_harness.py`.
- Keep unmarked non-GUI tests eligible for the future `fast` phase.
- Do not modify production code, shell wrapper logic, or test assertions in this packet.

## Non-Goals
- No shell-wrapper collection suppression yet. `P02` owns that.
- No verification runner script yet. `P03` owns that.
- No GUI wait-loop cleanup yet. `P04` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_work_packet_runner.py --collect-only -q -m "not gui and not slow"`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_theme.py tests/test_passive_graph_surface_host.py --collect-only -q -m gui`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --collect-only -q -m slow`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_theme.py tests/test_passive_graph_surface_host.py --collect-only -q -m gui`

## Expected Artifacts
- `docs/specs/work_packets/verification_speed/P01_pytest_selection_classification_WRAPUP.md`

## Acceptance Criteria
- The representative non-GUI command still collects the unmarked module when filtered by `not gui and not slow`.
- The representative GUI command only collects the GUI-tagged modules when filtered by `gui`.
- The representative slow command only collects the performance harness when filtered by `slow`.
- No production files under `ea_node_editor/**` are modified.

## Handoff Notes
- `P02` handles pytest helper-class suppression separately; do not mix wrapper collection fixes into this packet.
- Keep the classification logic centralized so later packets do not need to chase per-file decorator drift.
