# PROJECT_MANAGED_FILES P02: Media Resolution Adoption

## Objective
- Route current media and path-facing consumers through the central artifact/path resolver so image previews, PDF previews, page clamping, sizing, and browse seed paths work for both external files and project-managed refs.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/media_preview_provider.py`
- `ea_node_editor/ui/pdf_preview_provider.py`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSourceUtils.js`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_project_artifact_resolution.py`

## Conservative Write Scope
- `ea_node_editor/ui/media_preview_provider.py`
- `ea_node_editor/ui/pdf_preview_provider.py`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSourceUtils.js`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_project_artifact_resolution.py`
- `docs/specs/work_packets/project_managed_files/P02_media_resolution_adoption_WRAPUP.md`

## Required Behavior
- Adopt the `P01` resolver at every current media/path edge consumer that presently expects an absolute local path.
- Keep the rest of the app receiving absolute local paths at the final boundary even when authored node properties contain project-managed refs.
- Route image preview loading, PDF preview metadata, PDF page clamping, and media auto-sizing through the resolver.
- Include the final passive image-panel QML source-normalization seam so managed refs resolve to local file URLs before preview binding.
- Route browse-dialog seed path derivation through the resolver so managed refs reopen from a sensible project-local source root rather than from cwd.
- Preserve existing behavior for raw absolute paths, local file URLs, and current external-file projects.
- Add or update narrow regression tests that prove managed refs are accepted by the media/PDF surface path and do not break the existing external-path path.

## Non-Goals
- No managed-copy import flow yet. `P06` owns source browse defaults and import/copy behavior.
- No missing-file warning UX yet. `P07` owns broken-node surfacing and repair actions.
- No staging, save, or Save As behavior changes yet.
- No execution protocol changes yet. File-backed runtime resolution is handled later by `P09` and `P10`.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_pdf_preview_provider.py tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_contract.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_pdf_preview_provider.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/project_managed_files/P02_media_resolution_adoption_WRAPUP.md`

## Acceptance Criteria
- Image and PDF passive nodes can preview and size correctly when their `source_path` is a project-managed ref.
- PDF page normalization and browse seed-path behavior stay correct for both managed refs and existing external paths.
- Existing absolute-path and local-file-url projects continue to behave as before.

## Handoff Notes
- `P06` reuses the browse-path adoption landed here when it adds managed-copy imports.
- Record every resolver adoption seam in the wrap-up so later packets do not bypass it with new direct `Path(...)` reads.
