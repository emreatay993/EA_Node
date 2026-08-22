# Clipboard, Undo, Redo, And Mutation History

## Purpose
Use this for graph mutation history, undo/redo, clipboard fragments, runtime clipboard, and mutation replay routing.

## Start Here
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui/shell/controllers/mutation_ui_effects.py`
- `ea_node_editor/graph/fragment_payloads.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/graph/record_mutation_ops.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/ui/shell/runtime_clipboard.py`
- `ea_node_editor/ui/shell/clipboard_paste_nodes.py`
- `ea_node_editor/ui/shell/runtime_history.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_group_backdrop_clipboard.py tests/graph_track_b/scene_model_graph_scene_suite.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/workspace_library_controller_unit/core_ops.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_data_tree_ui.py tests/test_dataflow_graph_persistence.py --ignore=venv -q
```

## Mutation Routing Notes
- Fragment insertion is called directly through `ea_node_editor.graph.transform_fragment_ops.insert_graph_fragment`.
- `WorkspaceEditOps.paste_nodes_from_clipboard()` gives `GRAPH_FRAGMENT_MIME_TYPE` priority. Only when that MIME is absent does it classify OS clipboard files, URLs, raw media bytes, HTML, or text through `clipboard_paste_nodes.py` and create populated existing node types from the viewport center. Excel-style table clipboard data is detected before generic HTML/plain text and prompts for either a staged `tabular.input` TSV source or a markdown `passive.annotation.text` table.
- Local clipboard file URLs with `.eml`, `.msg`, or `.oft` suffixes create `passive.media.mail_panel` nodes by setting `source_path`; OS file drops use the same type only through the explicit file-drop command path so folder-explorer path-pointer drags keep their old behavior.
- Graph-fragment paste retargets fragment root nodes to `scope_parent_id(scene.active_scope_path)` before scene insertion, so copy/paste into and out of `core.subnode` scopes follows the visible canvas. Internal parent links inside the copied fragment stay unchanged.
- Fragment validation rejects internal self-parent and parent-cycle payloads. Direct fragment insertion still sanitizes remapped parent links before writing, dropping malformed parents to root while preserving valid internal and external parent links.
- Scene history uses focused validated and record mutation boundaries rather than the retired `WorkspaceMutationService`.
- Graph-scene grouped history uses opt-in `commit_if` gates for grouped operations that can prove they made no change after entering the history group. A false gate skips the expensive after-snapshot capture while preserving normal `RuntimeGraphHistory` snapshot equality for committed mutations.
- A settings-group toggle is one `toggle-settings-group` history entry containing declaration-ordered expansion state, exact custom-height correction, and any collision-avoidance neighbor moves. Toggling while the whole node is collapsed measures the hidden band with an isolated globally-expanded presentation probe so reopening preserves specialized body height.
- Dynamic group commands record `insert-dynamic-port`, `remove-dynamic-port`, or `rename-dynamic-port`. Each successful request is one history entry; invalid and no-op requests record none. Undo/redo restores the exact ordered keys, wires, labels, modifiers, and Principal state.
- `RuntimeGraphHistory.capture_workspace()` memoizes snapshots by exact `WorkspaceData.mutation_revision` and workspace object identity. Graph/view mutations and snapshot restore bump the runtime-only revision; undo/redo still replay full `WorkspaceSnapshot` entries.
- Undo/redo shell aftermath routes through `MutationUiEffects.after_history_replayed(...)`, which performs the full scene refresh, runtime elapsed/cache invalidation hook, and workspace-tab refresh. History replay deltas and model rebuild decisions remain graph-scene-owned.

## Breadcrumbs
- [Graph Domain, Mutation, Transforms, And Hierarchy](../subsystems/graph_domain.md)
- [Graph Scene Payload And Projection](graph_scene_payload_and_projection.md)

## Update Triggers
Update when clipboard payload normalization/validation, dynamic-port history actions, undo/redo behavior, mutation history, or transform tests change.
