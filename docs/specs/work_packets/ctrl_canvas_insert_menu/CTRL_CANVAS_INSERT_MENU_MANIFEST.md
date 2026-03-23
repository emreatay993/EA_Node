# CTRL_CANVAS_INSERT_MENU Work Packet Manifest

- Date: `2026-03-23`
- Scope baseline: preserve the existing empty-canvas double-click quick insert while adding a `Ctrl+Double Left Click` anchored canvas insert menu, a new passive plain-text annotation node with typography-aware styling and inline editing, and a non-persistent stylus coming-soon placeholder, without introducing a second canvas-artifact model or a second overlay bridge.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml` currently routes empty-canvas double-click straight to `request_open_canvas_quick_insert(...)` without a modifier branch.
  - `ea_node_editor/ui/shell/state.py`, `ea_node_editor/ui/shell/presenters.py`, and `ea_node_editor/ui_qml/shell_library_bridge.py` currently expose graph search, connection quick insert, and graph hint state only; `ea_node_editor/ui_qml/MainShell.qml` only hosts the search, quick insert, script editor, and graph hint overlays.
  - `ea_node_editor/nodes/builtins/passive_annotation.py` has no `passive.annotation.text` built-in, and note-style annotations still use the shared `GraphAnnotationNoteSurface.qml` with sticky/callout/section-header-only presentation.
  - `ea_node_editor/passive_style_normalization.py`, `ea_node_editor/ui/dialogs/passive_style_controls.py`, and `ea_node_editor/ui/dialogs/passive_node_style_dialog.py` only normalize and edit passive-node colors, border width/radius, font size, and bold.
  - The existing pending-surface-action and `nodeOpenRequested` patterns already exist in `GraphSceneBridge`, `GraphCanvas.qml`, media surfaces, and comment backdrop editing flows; this roadmap must reuse those seams rather than create a second canvas edit API.

## Packet Order (Strict)

1. `CTRL_CANVAS_INSERT_MENU_P00_bootstrap.md`
2. `CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography.md`
3. `CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell.md`
4. `CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow.md`
5. `CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/ctrl-canvas-insert-menu/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Text Annotation Contract and Typography | `codex/ctrl-canvas-insert-menu/p01-text-annotation-contract-and-typography` | Add `passive.annotation.text`, extend passive typography styling, and lock the text-annotation render contract |
| P02 Ctrl Canvas Insert Menu Shell | `codex/ctrl-canvas-insert-menu/p02-ctrl-canvas-insert-menu-shell` | Add the shell-owned Ctrl+double-click canvas insert menu, static Text/Stylus actions, and the stylus placeholder hint path |
| P03 Text Inline Editing Workflow | `codex/ctrl-canvas-insert-menu/p03-text-inline-editing-workflow` | Auto-open inline text editing after insertion, reuse body double-click reopen, and keep inspector and inline editing on the same `body` property |
| P04 Regression Docs Traceability | `codex/ctrl-canvas-insert-menu/p04-regression-docs-traceability` | Refresh requirements, QA/traceability docs, and packet-scoped final regression evidence for the feature |

## Locked Defaults

- Plain empty-canvas double left click keeps the current canvas quick-insert gesture.
- `Ctrl+Double Left Click` on empty canvas opens a new anchored canvas insert menu; node-body double-click behavior on existing nodes remains unchanged.
- Canvas insert menu state lives on the existing shell state/presenter/bridge path. Do not introduce a second overlay bridge or raw `mainWindow` fallback.
- `Text` creates `passive.annotation.text` inside the existing graph node document path. It is not a second canvas-artifact layer.
- `Stylus` is a non-persistent placeholder only. It does not add drawing behavior, tool-mode persistence, or a new preferences schema in this packet set.
- The clicked scene point remains the inserted text node's origin, matching the current canvas-insert behavior.
- `passive.annotation.text` is a passive annotation node with `surface_family="annotation"`, `surface_variant="text"`, no ports, `collapsible=False`, and a multiline `body` property defaulting to `"Text"`.
- Typography style fields are additive and inherit-capable: `font_family`, `font_italic`, `text_wrap`, `text_align`, and `line_height`.
- Rendered text must honor font family, size, bold, italic, wrap, alignment, and line height. The inline editor mirrors the same fields except `line_height`, which stays display-only because Qt `TextArea` does not support it.
- Auto-open editing reuses the existing pending-surface-action pattern after insertion, and body double-click reuses the current passive-surface `nodeOpenRequested` path rather than adding a second canvas-level edit API.
- Existing graph search, connection quick insert, context menus, comment backdrop flows, media inline editors, and passive-node style actions remain stable.
- This packet set is intentionally sequential because later packets inherit packet-local shell and surface regression anchors from earlier waves.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `CTRL_CANVAS_INSERT_MENU_Pxx_<name>.md`
- Implementation prompt: `CTRL_CANVAS_INSERT_MENU_Pxx_<name>_PROMPT.md`
- Packet wrap-up artifact for each implementation packet: `docs/specs/work_packets/ctrl_canvas_insert_menu/Pxx_<slug>_WRAPUP.md`
- Status ledger update in [CTRL_CANVAS_INSERT_MENU_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement CTRL_CANVAS_INSERT_MENU_PXX_<name>.md exactly. Before editing, read CTRL_CANVAS_INSERT_MENU_MANIFEST.md, CTRL_CANVAS_INSERT_MENU_STATUS.md, and CTRL_CANVAS_INSERT_MENU_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and public graph/shell/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update CTRL_CANVAS_INSERT_MENU_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P04` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- When a later packet changes a packet-owned test expectation from an earlier wave, that later packet must update the inherited earlier test file in-scope instead of leaving the stale assertion behind.
- Keep `graphCanvas`, `graphNodeCard`, the existing shell-library bridge, and current passive/media/comment-backdrop surface contracts stable unless a packet explicitly changes an owned seam.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
