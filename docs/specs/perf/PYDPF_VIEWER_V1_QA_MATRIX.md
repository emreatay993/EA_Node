# PYDPF Viewer V1 QA Matrix

- Updated: `2026-03-25`
- Packet set: `PYDPF_VIEWER_V1` (`P01` through `P15`)
- Scope: final closeout matrix for the shipped PyDPF runtime-handle, DPF materialization, viewer-session, packaging, and docs/traceability surface.

## Locked Scope

- `RuntimeHandleRef` transport and worker-local handle/viewer registries remain the approved boundary for DPF-backed runtime values.
- The shipped DPF node family covers `dpf.result_file`, `dpf.model`, `dpf.scoping.mesh`, `dpf.scoping.time`, `dpf.result_field`, `dpf.field_ops`, `dpf.mesh_extract`, `dpf.export`, and `dpf.viewer`; live viewer state stays session-owned instead of flowing as ordinary graph payloads.
- `viewerSessionBridge` plus `EmbeddedViewerOverlayManager` remain the shell-owned orchestration seam for proxy/live viewer behavior, including default `focus_only` one-live behavior and explicit `keep_live` opt-in.
- Optional PyDPF viewer dependencies stay isolated behind the `ansys` and `viewer` extras plus the Windows `base` versus `viewer` packaging profile.
- Packet-owned smoke inputs remain the repo-local DPF fixtures addressed by `tests/ansys_dpf_core/fixture_paths.py`: `static_analysis_1_bolted_joint/file.rst`, `modal_analysis_1_bolted_joint/file.rst`, and `steady_state_thermal_analysis_1_bolted_joint/file.rth`.

## Final Regression Commands

| Coverage Area | Primary Requirement Anchors | Command | Expected Coverage |
|---|---|---|---|
| Final packet regression | `REQ-INT-008`, `REQ-NODE-025`, `REQ-NODE-026`, `REQ-UI-032`, `REQ-QA-023` | `./venv/Scripts/python.exe -m pytest tests/test_dpf_viewer_node.py tests/test_dpf_node_catalog.py tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py tests/test_packaging_configuration.py tests/test_traceability_checker.py --ignore=venv -q` | Revalidates the shipped PyDPF viewer closeout surface covered by the packet fast lane: viewer-node catalog and execution, bridge/session-state behavior, viewer-surface contract, packaging configuration, and packet-owned docs/traceability coverage |
| Proof audit / review gate | `REQ-QA-024` | `./venv/Scripts/python.exe scripts/check_traceability.py` | Confirms the refreshed index, requirements, QA matrix, and traceability docs stay aligned with the published proof layer |

## Focused Narrow Reruns

| Coverage Area | Command | When To Use It |
|---|---|---|
| DPF viewer live policy | `./venv/Scripts/python.exe -m pytest tests/test_dpf_viewer_node.py tests/test_dpf_node_catalog.py tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q` | Use for `dpf.viewer`, bridge, or viewer-surface behavior changes |
| Overlay manager + handle boundary | `./venv/Scripts/python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py tests/test_execution_handle_refs.py --ignore=venv -q` | Use for `EmbeddedViewerOverlayManager` geometry/visibility changes or runtime-handle boundary changes claimed by `REQ-ARCH-016` |
| Optional packaging profile | `./venv/Scripts/python.exe -m pytest tests/test_packaging_configuration.py --ignore=venv -q` | Use for `ansys` / `viewer` extras, `ea_node_editor.spec`, or Windows packaging-script updates |
| Docs and traceability | `./venv/Scripts/python.exe scripts/check_traceability.py` | Use after editing the public requirements, traceability matrix, or this QA matrix |
| Traceability checker contract | `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Use when packet-owned doc tokens, QA matrix facts, or traceability rows change |

## 2026-03-25 Execution Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_dpf_viewer_node.py tests/test_dpf_node_catalog.py tests/test_viewer_session_bridge.py tests/test_viewer_surface_host.py --ignore=venv -q` | PASS | Viewer-node, catalog, bridge, and viewer-surface packet closeout rerun passed in the project venv |
| `./venv/Scripts/python.exe -m pytest tests/test_embedded_viewer_overlay_manager.py tests/test_execution_handle_refs.py --ignore=venv -q` | PASS | Overlay-manager geometry/visibility coverage plus runtime-handle boundary checks passed after the focused overlay alignment, coalesced manager sync, and geometry-only edge-change bridge fix |
| `./venv/Scripts/python.exe -m pytest tests/test_packaging_configuration.py --ignore=venv -q` | PASS | Optional `ansys` / `viewer` dependency-group and Windows packaging-profile wiring remained aligned with the shipped packet scope |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the PyDPF viewer docs, QA matrix, and traceability refresh |
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the PyDPF viewer documentation anchors remain present |

## Remaining Manual Smoke Checks

1. Repo-local DPF fixture smoke: run a workspace against `tests/ansys_dpf_core/example_outputs/static_analysis_1_bolted_joint/file.rst`, `tests/ansys_dpf_core/example_outputs/modal_analysis_1_bolted_joint/file.rst`, and `tests/ansys_dpf_core/example_outputs/steady_state_thermal_analysis_1_bolted_joint/file.rth` and confirm `dpf.viewer` can reopen proxy/live state against those authoritative smoke inputs.
2. Windows packaged viewer build: from a venv with `.[ansys,viewer]` or `.[dev]`, run `.\scripts\build_windows_package.ps1 -PackageProfile viewer -Clean -SkipSmoke` and verify the emitted package includes DPF gate DLLs, `vtk.libs`, and PyVistaQt runtime data.
3. Windows packaged installer follow-up: run `.\scripts\build_windows_installer.ps1 -PackageProfile viewer` against the viewer dist output and verify the installer manifest records `package_profile: viewer`.
4. Large-model manual viewer check: exercise a representative larger DPF result outside the repo fixtures and confirm that proxy/live transitions, reopen state, and overlay attachment remain usable without claiming that coverage in the automated fast lane.

## Future-Scope Deferrals

- True per-step multi-set DPF requery still depends on the worker session-source contract outside the packet-owned docs surface.
- The repo does not yet automate a full viewer-profile PyInstaller smoke build inside the fast lane; packaged DPF/VTK runtime validation remains manual.
- Large-model viewer performance characterization remains a manual follow-up rather than a checked-in benchmark workflow.
