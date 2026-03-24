# P07 File Issue Node Repair Wrap-Up

## Implementation Summary

- Packet: `P07`
- Branch Label: `codex/project-managed-files/p07-file-issue-node-repair`
- Commit Owner: `worker`
- Commit SHA: `33d8dfee33e3f0f36034c44123c67f38b82f0861`
- Changed Files: `ea_node_editor/graph/file_issue_state.py`, `ea_node_editor/ui/shell/presenters.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/window_library_inspector.py`, `ea_node_editor/ui_qml/components/shell/InspectorPropertyEditor.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`, `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelHeaderControls.qml`, `tests/test_project_file_issues.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_passive_graph_surface_host.py`, `docs/specs/work_packets/project_managed_files/P07_file_issue_node_repair_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/project_managed_files/P07_file_issue_node_repair_WRAPUP.md`, `ea_node_editor/graph/file_issue_state.py`, `tests/test_project_file_issues.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_passive_graph_surface_host.py`
- Warning-State Source of Truth: `ea_node_editor/graph/file_issue_state.py` now owns tracked missing-file detection, repair-request encoding, repair-mode policy, and node/property issue payloads for passive media plus File Read / Excel Read source paths.
- Repair Entry Points: inspector path issue banners call `browse_selected_node_property_path(...)` with encoded repair requests; passive media header repair buttons call `GraphMediaPanelSurface.repairFile()` and route through `host.browseNodePropertyPath(...)`; both paths converge in `ShellWindow._repair_property_path_dialog(...)` via `ShellInspectorPresenter`.
- Repair Flow Summary: passive media sources can relink as either managed copies or external links from one `Repair file...` action, including missing `artifact-stage://...` media sources now reusing the existing artifact id when repaired in managed-copy mode; File Read and Excel Read repairs intentionally remain external-only until later runtime artifact-ref adoption lands.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_file_issues.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_project_file_issues.py --ignore=venv -q`
- PASS: remediation verification `./venv/Scripts/python.exe -m pytest tests/test_project_file_issues.py --ignore=venv -q`
- PASS: remediation review gate `./venv/Scripts/python.exe -m pytest tests/test_project_file_issues.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch this branch from a writable workspace and use a saved `.sfe` project path when checking managed-media repair so staged replacements can be written into the project sidecar.
- Passive media repair: open or create an Image Panel or PDF Panel with a missing source, confirm the node shows a `Missing file` badge and `Repair file...`, repair it, and confirm the warning clears and the preview becomes usable without reopening the project.
- Inspector repair on consumer nodes: select a File Read or Excel Read node whose `File Path` is missing, confirm the inspector shows the missing-file banner, use `Repair file...`, and confirm the property updates to the chosen external file and the warning clears immediately.
- Managed vs external choice: on a missing Image Panel or PDF Panel source, run `Repair file...` twice, once choosing `Managed Copy` and once choosing `External Link`, and confirm the property stores an `artifact-stage://...` ref for the managed repair and a raw absolute path for the external relink.

## Residual Risks

- Tracked file issues are intentionally limited to this packet’s source/consumer scope: passive media `source_path` plus File Read / Excel Read `path`. Other path-like properties remain outside the issue model until later packets define broader semantics.
- File Read and Excel Read repairs intentionally stay on external relinks. Managed refs for those runtime consumers still need later execution-layer adoption before managed-copy repair would be safe end to end.
- Repairing a missing staged media ref now preserves the existing staged artifact id, but cleanup of superseded staged payloads still remains under the later save/prune lifecycle.

## Ready for Integration

- Yes: packet-owned issue detection, owner/consumer warning surfaces, node-level repair actions, and packet regression tests are committed and passing on the assigned P07 branch.
