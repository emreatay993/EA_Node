# UI_CONTEXT_SCALABILITY_REFACTOR P06: Viewer Surface Isolation

## Objective

- Isolate viewer-specific UI and session-projection seams so ordinary graph-editing packets no longer need the viewer stack in context to make generic canvas changes.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P05`

## Target Subsystems

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`
- `tests/test_dpf_viewer_node.py`

## Conservative Write Scope

- `ea_node_editor/execution/viewer_session_service.py`
- `ea_node_editor/ui_qml/viewer_session_bridge.py`
- `ea_node_editor/ui_qml/viewer_host_service.py`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_viewer_session_bridge.py`
- `tests/test_viewer_host_service.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_surface_host.py`
- `tests/test_dpf_viewer_node.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P06_viewer_surface_isolation_WRAPUP.md`

## Required Behavior

- Keep generic graph-editing packets viewer-agnostic by moving viewer-specific projection and surface state behind focused viewer-only seams.
- Reduce bridge-side packet-owned workflow state so `viewer_session_bridge.py` projects authoritative service state plus explicitly local pending UI state only.
- Reduce packet-owned surface logic in `GraphViewerSurface.qml` so generic graph-surface behavior does not depend on viewer-only concerns.
- End `viewer_session_bridge.py` at or below `550` lines, `viewer_session_service.py` at or below `700` lines, and `GraphViewerSurface.qml` at or below `600` lines.
- Preserve documented viewer-family behavior and update inherited viewer regression anchors in place.

## Non-Goals

- No new viewer features or UX changes.
- No DPF transport or backend protocol redesign.
- No changes to the packet-owned generic edge or graph-canvas contracts outside viewer isolation.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_service.py tests/test_viewer_session_bridge.py tests/test_viewer_host_service.py tests/test_viewer_surface_contract.py tests/test_viewer_surface_host.py tests/test_dpf_viewer_node.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P06_viewer_surface_isolation_WRAPUP.md`

## Acceptance Criteria

- Generic graph-editing packets no longer depend on viewer-specific UI or projection seams.
- `viewer_session_bridge.py`, `viewer_session_service.py`, and `GraphViewerSurface.qml` meet the packet-owned size caps.
- The inherited viewer service, bridge, host, surface, and DPF-node anchors pass.

## Handoff Notes

- `P07` should codify the new hotspot budgets and ownership guardrails after the main packet-owned UI hot spots are shrunk.
