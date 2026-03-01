# RC2 Stitch Fidelity Checklist

## Base Shell (Mockup 1)

- [x] Dark stitched shell with menu/toolbar/panels/status layout.
- [x] Node library + canvas + inspector + console + bottom workspace tabs.
- [x] Accent-highlighted status bar segments.
- Evidence: `docs/specs/perf/rc2/shell_idle.png`

## Canvas and Nodes

- [x] Grid canvas with node chrome accents.
- [x] Edge and port visuals updated.
- [x] Zoom-aware rendering simplification.
- Evidence: `docs/specs/perf/rc2/canvas_nodes.png`

## Library and Inspector

- [x] Category-first library browsing behavior.
- [x] Inspector remains property/edit focused.
- Evidence: `docs/specs/perf/rc2/library_inspector.png`

## Settings Modal (Mockup 2 Surface)

- [x] Workflow settings dialog with section navigation and editable fields.
- [x] Persisted to metadata and consumed by run trigger.
- Evidence: `docs/specs/perf/rc2/settings_modal.png`

## Script Editor (Mockup 3 Surface)

- [x] Dockable script editor bound to Python Script nodes.
- [x] Syntax highlighting + line/column indicator + modified/apply flow.
- Evidence: `docs/specs/perf/rc2/script_editor.png`

## Failure UX

- [x] Existing failure focus + error dialog behavior retained.
- Evidence: `tests/test_main_window_shell.py::test_run_failed_event_centers_failed_node_and_reports_exception_details`

