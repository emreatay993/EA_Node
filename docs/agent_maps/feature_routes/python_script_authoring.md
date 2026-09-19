# Python Script Authoring

## Purpose

Use for the Python Script builder/editor, decorator assistance, data-type picker,
guided rename, sections, session drafts, Apply impact, and isolated node preview.

## Lookup Aliases

- `Python Script builder`
- `script editor`
- `decorator controls`
- `script sections`
- `script type picker`

## Start Here

- `ea_node_editor/ui_qml/script_editor_model.py`
- `ea_node_editor/ui_qml/components/shell/ScriptCodeEditorPane.qml`
- `ea_node_editor/nodes/python_script_authoring.py`

## Source Owners

- `ea_node_editor/nodes/python_script_declaration.py` parses bounded literal metadata without executing source and resolves the ordinary node spec.
- `ea_node_editor/nodes/python_script_authoring.py` owns source analysis, field editing, atomic section edits and signature synchronization.
- `ea_node_editor/nodes/python_script_authoring_source.py` owns token/AST source spans; `ea_node_editor/nodes/python_script_authoring_rename.py` owns scope-aware rename safety.
- `ea_node_editor/ui/support/python_script_authoring.py` projects native form descriptors, catalog choices and incomplete-code completion.
- `ea_node_editor/graph/validated_mutation.py` prepares and applies source plus explicit rename identities; `ea_node_editor/graph/node_port_state.py` remains pure state projection.
- `ea_node_editor/ui_qml/script_editor_model.py` owns source/native-field buffers, per-context drafts, local undo, UTF-16 selection, diagnostics, completion and guarded Apply.
- `ea_node_editor/ui/shell/controllers/workspace_edit_controller.py` binds current graph context and UI effects; `ea_node_editor/ui/shell/controllers/run_controller.py` consumes unapplied source/native fields only for explicit runs.
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py` and `ea_node_editor/ui_qml/graph_scene_mutation_history.py` retain one scene-history action per Apply.
- `ea_node_editor/ui_qml/components/shell/ScriptCodeEditorPane.qml` shares the responsive workspace between docked and fullscreen hosts.
- `ea_node_editor/ui_qml/components/shell/ScriptInterfacePane.qml` owns the outline and selected item; `ea_node_editor/ui_qml/components/shell/ScriptAuthoringForm.qml` and `ea_node_editor/ui_qml/components/shell/ScriptAuthoringRows.qml` own native forms.
- `ea_node_editor/ui_qml/components/shell/ScriptAuthoringAddPopup.qml`, `ea_node_editor/ui_qml/components/shell/ScriptAuthoringTypePicker.qml` and `ea_node_editor/ui_qml/components/shell/ScriptAuthoringPreview.qml` own creation, type selection and preview views.
- `ea_node_editor/ui_qml/components/shell/ScriptAuthoringButton.qml`, `ea_node_editor/ui_qml/components/shell/ScriptAuthoringTextField.qml`, `ea_node_editor/ui_qml/components/shell/ScriptAuthoringComboBox.qml` and `ea_node_editor/ui_qml/components/shell/ScriptAuthoringTab.qml` preserve local desktop styling without changing the rest of the app.
- `ea_node_editor/ui_qml/python_script_preview.py` owns detached temporary values and expansion. `ea_node_editor/ui_qml/graph_scene_payload/builder.py` uses the normal payload factory and `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` for rendering.
- `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`, `ea_node_editor/ui_qml/graph_scene_payload/factory.py`, `ea_node_editor/ui_qml/components/graph/GraphNodeSettingsGroupsLayer.qml` and `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml` share compact control geometry and blank-label behavior with actual canvas nodes.

## Boundaries

- Python source is authoritative; no second persisted builder definition. `section=` groups existing inputs/controls, never outputs or empty sections.
- Guided rename alone carries identity transfer. Arbitrary typed renames do not inherit saved values/wires. Candidate preparation is detached; commit checks freshness and prepares again.
- Generic dynamic-port rename still prunes old wires/state. Script Apply and project-load normalization keep their separate policies.
- `has_unapplied_edits` includes current native fields for explicit-run and canvas-port guards. Source `dirty` retains its original meaning. Pending fields follow the shared model across node/pane changes; hidden views cannot leave an inaccessible blocking owner.
- Numeric form intent crosses the Qt boundary explicitly: JavaScript `1.0` alone becomes an integer QVariant. Whole mode must reject fractions instead of truncating.
- Preview cannot dispatch user code or mutate the live graph. Updates immediately hide stale payloads. Use as default is an ordinary draft edit.
- `SettingsGroupSpec.show_header` defaults true. Python Script unsectioned controls use the reserved `script.controls` group with no header, aggregate socket or expansion state; shared rows always remain expanded below plain ports. A control socket does not change its row geometry.

## Focused Tests

- `tests/test_python_script_authoring.py`, `tests/test_python_script_authoring_completion.py`, `tests/test_python_script_declaration.py`
- `tests/test_graph_node_reconciliation.py`, `tests/test_graph_registry_normalization.py`
- `tests/test_script_editor_authoring_model.py`, `tests/test_python_script_scene_integration.py`, `tests/test_python_script_persistence.py`
- `tests/test_python_script_authoring_ui.py` for real Qt input, native buffers, sections, preview isolation, responsive/DPI renders and icons.
- `tests/test_script_editor_dock.py`, `tests/test_content_fullscreen_bridge.py` for retained shell/draft/editor behavior.
- `tests/qml_quick/tst_graph_node_host.qml` for shared headerless rows, labels and interaction geometry.

## Focused Verification

```powershell
.\venv\Scripts\python.exe -m pytest -q tests/test_python_script_authoring.py tests/test_script_editor_authoring_model.py tests/test_python_script_authoring_ui.py
```

## Guides And Evidence

- [Python Script guide](../../PYTHON_SCRIPT_GUIDE.md)
- [Implementation and verification](../../PLAN_PYTHON_SCRIPT_AUTHORING.md)
- [Shared surface controls](surface_input_and_inline_controls.md)

## Update Triggers

Update when authoring operations, native-field ownership, completion/type choices,
source spans, rename/Apply identity, sections, shared preview or control placement change.
