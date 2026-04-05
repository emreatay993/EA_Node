# UI_CONTEXT_SCALABILITY_FOLLOWUP P06: Graph Surface Test Packetization

## Objective

- Break the graph-surface host and input-contract umbrellas into focused regression suites plus shared support while keeping the top-level regression entrypoints stable.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P05`

## Target Subsystems

- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/graph_surface/__init__.py`
- `tests/graph_surface/environment.py`
- `tests/graph_surface/pointer_and_modal_suite.py`
- `tests/graph_surface/inline_editor_suite.py`
- `tests/graph_surface/media_and_scope_suite.py`
- `tests/graph_surface/passive_host_boundary_suite.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`

## Conservative Write Scope

- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/graph_surface/__init__.py`
- `tests/graph_surface/environment.py`
- `tests/graph_surface/pointer_and_modal_suite.py`
- `tests/graph_surface/inline_editor_suite.py`
- `tests/graph_surface/media_and_scope_suite.py`
- `tests/graph_surface/passive_host_boundary_suite.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P06_graph_surface_test_packetization_WRAPUP.md`

## Required Behavior

- Split `tests/test_passive_graph_surface_host.py` and `tests/test_graph_surface_input_contract.py` into focused regression suites with these support files:
  - `tests/graph_surface/environment.py`
  - `tests/graph_surface/pointer_and_modal_suite.py`
  - `tests/graph_surface/inline_editor_suite.py`
  - `tests/graph_surface/media_and_scope_suite.py`
  - `tests/graph_surface/passive_host_boundary_suite.py`
  - `tests/graph_surface/passive_host_interaction_suite.py`
- Keep `tests/test_passive_graph_surface_host.py` as the stable regression entrypoint for passive host coverage.
- Keep `tests/test_graph_surface_input_contract.py` as the stable regression entrypoint for graph-surface contract coverage.
- End each of those top-level entry files at or below `200` lines.
- Preserve the current regression entry commands and the host, pointer, inline-editor, media, scope, and boundary coverage they already prove.
- Update inherited graph-surface regression anchors in place when suite ownership or shared fixtures move.

## Non-Goals

- No source refactors in this packet.
- No Track-B regression packetization yet.
- No new graph-surface behavior.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_contract.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P06_graph_surface_test_packetization_WRAPUP.md`
- `tests/graph_surface/environment.py`
- `tests/graph_surface/passive_host_interaction_suite.py`

## Acceptance Criteria

- The graph-surface regression coverage moves into focused suites behind the stable top-level entrypoints.
- `tests/test_passive_graph_surface_host.py` is at or below `200` lines.
- `tests/test_graph_surface_input_contract.py` is at or below `200` lines.
- The inherited graph-surface regression anchors pass.

## Handoff Notes

- `P08` must update the canonical packet docs so future graph-surface UI work names this regression packet explicitly instead of regrowing the umbrella tests.
