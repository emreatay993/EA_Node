---
name: corex-automation
description: Author COREX flowcharts, boards, and node workflows through the corex MCP tools (corex_status, graph_apply, node_*, edge_*, capture_screenshot) or the Python CorexClient. Use when the user asks to build, style, annotate, group, nest, save, run, or screenshot a COREX graph programmatically.
---

# COREX automation

COREX exposes a local, opt-in automation API: 56 ops, each an MCP tool of the
`corex` server and a `CorexClient` call. Full guide:
`docs/AUTOMATION_API_GUIDE.md` in the COREX repository (setup, concepts, UI
parity, walkthroughs, generated op reference). Runnable examples:
`examples/automation/`.

## Workflow

1. **Check the instance.** Call `corex_status` first. If `busy.modal_dialog`,
   `busy.document_io`, or a running `run` is reported, wait or ask the user.
   Read the `corex://guide` resource once per session; `corex://ops`,
   `corex://styles`, and `corex://node-types` hold the details.
2. **Plan on a grid.** Pick type ids with `catalog_list_node_types`
   (`runtime_behavior=passive` for diagrams) and check ports/properties with
   `catalog_describe_node_type`. Lay nodes out on a 320 x 160 grid (x to the
   right, y down, top-left corner coordinates).
3. **Build in one batch.** Send one `graph_apply` with every `node.add` /
   `edge.connect` / `group.wrap` op, naming ops with `id` and wiring later ops
   with `$id` (or `$id.field`). The batch is one undo step; with `atomic=true`
   (default) any failure rolls everything back and raises `APPLY_FAILED`.
   `$ref` works only in id fields, never inside titles or markdown.
4. **Style and annotate.** `node_set_style` (passive nodes only; aliases like
   `fill_color_end`), `edge_update` (`label`, `path_mode`, `display_mode`, and a
   `style` object whose keys accept aliases like `color`, `width`, `pattern`), `node_add_text` for markdown notes, `comment_upsert`,
   `link_upsert`, `group_wrap` with a title, `subnode_create` for nested scopes.
   Moving a Group with `node_update(x=, y=)` moves everything inside it
   (`carried_node_ids`); `move_contents=false` moves or reshapes only its frame.
   Role swimlanes: `swimlane_create_pool(x, y, lanes=[...])`, then
   `swimlane_assign(node_ids, lane_node_id)` and `layout_tidy([pool_node_id])`
   (layers along the flow, one row per lane); `swimlane_describe` lists lanes.
5. **Tidy.** `layout_tidy()` lays the open scope (or `node_ids`) out from its
   wires: rows and columns centered so wires run straight, direction detected
   (or `direction="left_to_right"` / `"top_to_bottom"`), loops kept as elbows,
   Group backdrops kept intact; `mode="in_place"` only straightens the rows and
   columns you already have. For fine control use `layout_arrange`
   (`align_center_y` rows, `align_center_x` columns, `align_*`, `distribute_*`,
   `match_width` / `match_height`) and `layout_straighten()`. Check
   `skipped_edges` for unintended elbows (loops are expected) and spread out
   any `overlapping_node_pairs`.
6. **Save and show.** `view_set_camera(frame=all)`, `project_save` (pass
   `path` for Save As), then `capture_screenshot` and look at the image.

## Rules that avoid mistakes

- Graph ops act on the active workspace and the open scope. Enter a subnode
  with `scope_navigate(target=node)` before adding inside it; return with
  `target=root`.
- Passive flow ports are `top`, `right`, `bottom`, `left`. Data ports use the
  keys from `catalog_describe_node_type`.
- Flowchart shapes draw their `body` property. On the classic shapes (start, end,
  process, decision, document, ...) `title` also sets an untouched `body`, so passing
  `title` is enough; on card, callout, message and timestamp set `properties.body`. The
  bare text node (`passive.annotation.text`) stores content under `text`.
- Long flowchart text: `node_fit_text(node_id, mode=grow|shrink|clip)` grows the shape or
  shrinks the font to fit, as one undo step, and reports `text_fit.overflowing`. The shape
  must be drawn: frame an off-screen one with `view_set_camera` first.
- Every mutating op is one undo step; `corex_history(action=undo)` reverts it.
- `NO_EFFECT` means nothing changed: read `details.reasons`, do not blindly
  retry.
- Never call `corex_quit` or `project_open` with `discard_unsaved=true` on an
  instance you attached to; it belongs to the user.

## Errors

Every error has `code`, `message`, `hint`, `details`, `retryable`. Follow the
`hint`. Retry only `APP_BUSY`, `APP_BUSY_MODAL`, and `TIMEOUT` (for a modal,
ask the user to close the dialog). `NOT_FOUND` / `WRONG_SCOPE` /
`WRONG_WORKSPACE`: refresh ids with `graph_get`, then navigate or activate.
`INVALID_PARAMS` / `UNKNOWN_NODE_TYPE`: fix the request from
`details.problems` or `details.suggestions`.

## Limits

- Loopback only, off by default: COREX must run with `--automation`, or the
  MCP server spawns one (`--mode auto` visible, `--mode private` isolated).
- Offscreen (headless private) screenshots are layout evidence
  (`fidelity=offscreen_layout`); web panels and 3D viewers render blank there.
- `graph_apply` rollback does not undo staged files; max 500 ops per batch.
- Clipboard, dialogs, OS launches, port modifiers, and plugin editing are not
  exposed.

## Python equivalent

```python
from ea_node_editor.automation.client import CorexClient

with CorexClient.launch("private") as corex:
    batch = corex.apply.batch()
    start = batch.add("node.add", {"type_id": "passive.flowchart.start", "x": 0, "y": 0, "title": "Start"}, id="start")
    mesh = batch.add("node.add", {"type_id": "passive.flowchart.process", "x": 320, "y": 0, "title": "Mesh"}, id="mesh")
    batch.add("edge.connect", {"source_node_id": start, "source_port": "right", "target_node_id": mesh, "target_port": "left"})
    ids = batch.run(label="Build flowchart")["ids"]
    corex.workspaces.frame_all()
    print(corex.capture.screenshot_to("C:/temp/corex")["saved_paths"])
```
