# UI_CONTEXT_SCALABILITY_REFACTOR P08: Subsystem Packet Docs

## Objective

- Publish reusable subsystem packet contracts and a feature-packet template so future UI work starts from clear ownership, allowed dependencies, invariants, and test anchors instead of rediscovering the same seams.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P07`

## Target Subsystems

- `ARCHITECTURE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SHELL_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/PRESENTERS_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/EDGE_RENDERING_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/VIEWER_PACKET.md`
- `tests/test_markdown_hygiene.py`

## Conservative Write Scope

- `ARCHITECTURE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SHELL_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/PRESENTERS_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/EDGE_RENDERING_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/VIEWER_PACKET.md`
- `tests/test_markdown_hygiene.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P08_subsystem_packet_docs_WRAPUP.md`

## Required Behavior

- Add `SUBSYSTEM_PACKET_INDEX.md` that maps the packet-owned UI subsystems to their contract docs and primary verification anchors.
- Add `FEATURE_PACKET_TEMPLATE.md` that future UI feature packets must follow.
- Add one contract doc each for shell, presenters, graph scene, graph canvas, edge rendering, and viewer.
- Each subsystem contract doc must state owner files, public entry points, state owner, allowed dependencies, invariants, forbidden shortcuts, and required tests.
- Update `ARCHITECTURE.md` so the packet docs are part of the normal engineering entry path for UI changes.

## Non-Goals

- No further product-code refactoring.
- No QA matrix or traceability closeout yet; that belongs to `P09`.
- No markdown cleanup outside the packet-owned docs.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_markdown_hygiene.py --ignore=venv -q
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P08_subsystem_packet_docs_WRAPUP.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SHELL_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/PRESENTERS_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_SCENE_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/EDGE_RENDERING_PACKET.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/VIEWER_PACKET.md`

## Acceptance Criteria

- Future UI feature work has explicit subsystem packet docs and a reusable feature-packet template.
- `ARCHITECTURE.md` points engineers to the packet docs before they modify packet-owned UI seams.
- Markdown hygiene and link checks pass.

## Handoff Notes

- `P09` should close the packet set with QA evidence and traceability updates that point at the new docs and guardrails instead of duplicating them.
