# Wire DPF operator nodes to F1 / context-menu help

## Context

We just generated 2,270 Markdown operator specification files under
[docs/dpf_operator_docs/operator-specifications/](docs/dpf_operator_docs/operator-specifications/)
via [scripts/generate_dpf_operator_docs.py](scripts/generate_dpf_operator_docs.py).
Each file contains the complete spec for one DPF operator (description, inputs, outputs
with types, configurations, changelog) — the same content the Ansys Developer Portal
renders to HTML.

Instead of hand-authoring per-node help text, wire the generated DPF operator nodes to
their corresponding `.md` file so the user can open the full operator spec directly from
the node (F1 or right-click → Help) inside an in-app side pane.

**User choices (already confirmed):**
- Viewer: in-app QML side panel rendered via Qt's native Markdown support.
- Trigger: F1 key **and** right-click → Help menu entry.
- Scope: only auto-generated DPF operator nodes (`type_id` prefix `dpf.op.`). Helpers,
  I/O, groups, etc. are out of scope.

## Approach

### 1. Emit a JSON index alongside the Markdown

Extend [scripts/generate_dpf_operator_docs.py](scripts/generate_dpf_operator_docs.py) to
also write `docs/dpf_operator_docs/doc_index.json` during the same generation pass:

```json
{
  "displacement": "result/displacement.md",
  "merge::fields_container": "utility/merge_fields_containers.md",
  "blas_gemm": "_uncategorized/blas_gemm.md",
  ...
}
```

Keyed on the DPF **internal operator name** (`operator.name`), which is exactly what
the catalog persists on each `NodeTypeSpec` via
`source_metadata.variants[0].operator_name`
([ansys_dpf_operator_catalog.py:534-545](ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py#L534)).
No re-query of DPF needed at runtime — a dict lookup is the whole story.

### 2. Runtime lookup helper

New module `ea_node_editor/help/dpf_operator_docs.py` with:

- `docs_root() -> Path` — resolves `docs/dpf_operator_docs/` in both dev checkout and
  PyInstaller `_MEIPASS` layouts. (Packaging is a follow-up; the dev path is primary.)
- `markdown_for_type_id(type_id: str, host) -> str | None` — looks up the spec via the
  existing `host.registry.get_spec(type_id)` (pattern already used at
  [ansys_dpf_operator_catalog.py:235](ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py#L235)),
  extracts `spec.source_metadata.variants[0].operator_name`, indexes into the JSON, and
  returns the file contents. Returns `None` for non-DPF nodes or index misses.

Loading the index is lazy + cached (`functools.lru_cache`).

### 3. QML help pane

New `ea_node_editor/ui_qml/components/shell/HelpPane.qml`:

```qml
ScrollView {
    TextArea {
        readOnly: true
        textFormat: TextEdit.MarkdownText
        text: helpBridge.markdown
    }
}
```

Slot it into the existing inspector shell as a new tab alongside the current inspector
bodies ([InspectorPane.qml](ea_node_editor/ui_qml/components/shell/InspectorPane.qml)).
No new dockable window — reuse the inspector container to minimize shell churn.

### 4. Python bridge

New `ea_node_editor/help/help_bridge.py` — a `QObject` exposed to QML, modeled on
[shell_inspector_bridge.py](ea_node_editor/ui_qml/shell_inspector_bridge.py):

- `Property(str) markdown` — current Markdown text.
- `Property(str) title` — operator display name (for the tab header).
- `Signal markdownChanged`.
- `Slot() showHelpForNode(node_id: str)` — resolves node → type_id → Markdown via the
  helper above; emits the signal; switches the inspector to the Help tab.

### 5. F1 shortcut

Register a `QShortcut(QKeySequence.HelpContents, graph_view)` on the graph view
container. Handler resolves the currently selected node (one — if zero or many selected,
no-op with a status-bar hint) and calls `HelpBridge.showHelpForNode`.

### 6. Right-click → Help

The QML gesture layer already emits `nodeContextRequested(nodeId, x, y)` at
[GraphNodeHostGestureLayer.qml:37](ea_node_editor/ui_qml/components/graph_canvas/GraphNodeHostGestureLayer.qml#L37)
but the signal is not connected on the Python side. Connect it, build a QML `Menu` (or
extend an existing one), and add a **Help** `MenuItem`. Enable it only when
`type_id.startswith("dpf.op.")` — for other nodes, hide or disable the entry.

## Critical files

| Change | File |
|---|---|
| Emit index | [scripts/generate_dpf_operator_docs.py](scripts/generate_dpf_operator_docs.py) |
| Lookup helper (new) | `ea_node_editor/help/dpf_operator_docs.py` |
| Bridge (new) | `ea_node_editor/help/help_bridge.py` |
| Pane (new) | `ea_node_editor/ui_qml/components/shell/HelpPane.qml` |
| Add Help tab | [ea_node_editor/ui_qml/components/shell/InspectorPane.qml](ea_node_editor/ui_qml/components/shell/InspectorPane.qml) |
| Connect context signal + add menu entry | [ea_node_editor/ui_qml/components/graph_canvas/GraphNodeHostGestureLayer.qml](ea_node_editor/ui_qml/components/graph_canvas/GraphNodeHostGestureLayer.qml), [GraphCanvasContextMenus.qml](ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml) |
| F1 shortcut | graph view host (search `QShortcut` / `QKeySequence` in `ea_node_editor/ui/` for existing pattern; if none, add in the graph view widget) |
| Bridge registration | wherever the QML context is set up (same place as `shell_inspector_bridge`) |

## Reused existing pieces

- Catalog spec lookup: `host.registry.get_spec(type_id)` — already the authoritative
  way to resolve a node to its `NodeTypeSpec`.
- `DpfOperatorSourceSpec.variants[0].operator_name` — already persisted per operator
  node, matches the key we write into the JSON index.
- QML `nodeContextRequested` signal is already emitted — we only need to connect and
  extend the menu.
- Inspector shell already houses multi-tabbed content — add Help tab instead of a new
  window.

## Non-goals

- Helper nodes (Data Sources, Model, Streams Container) — user scoped to operator nodes
  only.
- HTML rendering via MkDocs/DocFX — Qt's MarkdownText handles the 2,270 files directly;
  HTML build remains a separate follow-up if ever wanted.
- PyInstaller packaging of the docs tree — note it in release-notes, but not this PR.

## Verification

- Unit: new `tests/test_dpf_operator_help_lookup.py` — for every `type_id` starting with
  `dpf.op.` in the registry, `markdown_for_type_id` returns non-empty text beginning
  with `# ` (a rendered operator page). Run with `pytest -n auto`.
- Regression: `pytest -n auto tests/test_dpf_generated_helper_catalog.py` must still
  pass (catalog unchanged structurally).
- Manual: launch the app, drop a `result.displacement` node, select it, press **F1** —
  side pane shows the displacement spec with inputs/outputs tables rendered.
  Right-click the same node → Help entry present → triggers the same pane.
  Right-click a non-DPF node → Help entry hidden or disabled.
- Edge: `merge::fields_container` (a `::` sanitization case) and a `_uncategorized`
  operator both open correctly.
