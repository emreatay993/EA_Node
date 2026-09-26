# COREX Automation API Guide

The automation API lets a script or an AI agent (Claude Code, Codex, Claude
Desktop) author COREX flowcharts and workflows: create and style nodes, wire
edges, group and nest, manage workspaces and views, comment and link, save,
run, and screenshot. It is served by the running COREX application over a
loopback socket and exposed two ways: the stdlib Python client
`ea_node_editor.automation.client.CorexClient` and the `corex-mcp` MCP server.

Design and status live in the
[automation plan](PLAN_COREX_AUTOMATION_API_MCP.md); code navigation lives in
the [agent map](agent_maps/feature_routes/automation_api_mcp.md). Runnable
examples are under [examples/automation](../examples/automation/README.md).

## What it is and what it is not

It is a **local, opt-in developer automation surface**:

- Off by default. The server starts only when COREX is launched with
  `--automation` or spawned by the launcher.
- Loopback only (`127.0.0.1`), one per-instance token, protocol version 1,
  NDJSON frames capped at 8 MiB.
- One declarative op catalog: 50 ops, each also a typed MCP tool. The same
  in-app server serves every launch mode.
- Every mutating op is exactly one undo step; `graph.apply` batches are one
  step too.
- Handlers call the existing UI owners and verify the result; silent owner
  no-ops surface as `NO_EFFECT`. No op ever opens a modal dialog.

It is **not** permissioned agent orchestration. `REQ-ARCH-020`, `REQ-EXEC-022`,
and `REQ-UI-058` stay blocked; there is no remote access, no multi-user
permission model, and no sandboxing of what a run executes.

First-pass limits:

- Graph ops act on the active workspace and the open scope. Activate another
  workspace with `workspace.update(activate=true)` and enter a subnode with
  `scope.navigate` first.
- Web panels and 3D viewers are blank in offscreen screenshots
  (`fidelity=offscreen_layout`). Use `private` with `headless=False`, or
  `attach` / `auto` against a visible instance, for native fidelity.
- A failed run refocuses the canvas on the failed node (existing UI behaviour).
- `graph.apply` rollback cannot undo staged files or the title-driven artifact
  folder rename.
- Frozen (PyInstaller) builds include the in-app server (`--automation`) but
  not the `[mcp]` extra: run `corex-mcp` from a Python environment and use
  `attach`.

## Setup

### Start COREX with the automation server

```powershell
.\venv\Scripts\python.exe -m ea_node_editor.bootstrap --automation
.\venv\Scripts\python.exe -m ea_node_editor.bootstrap --automation --automation-port 8765
```

`--automation` enables the server on an ephemeral port. `--automation-port N`
pins the port (`0` means ephemeral) and `--automation-instance-id ID` sets the
discovery id (the launcher uses it; you rarely need it by hand). Both value
flags imply `--automation`. The instance publishes a discovery file (see
[Discovery files](#discovery-files)) that clients use to find the port and
token.

You do not need to start COREX yourself when a client uses the `auto` or
`private` launch mode; the launcher spawns an instance for you.

### Install the MCP extra

```powershell
.\venv\Scripts\python.exe -m pip install -e ".[mcp]"
```

The extra pins `mcp>=1.10,<2` and installs the `corex-mcp` console script
(`venv\Scripts\corex-mcp.exe`). `python -m ea_node_editor.automation.mcp_server`
is the equivalent module form and works from a source checkout without the
console script.

### Register with Claude Code

```powershell
claude mcp add corex -- C:\path\to\EA_Node_Editor\venv\Scripts\python.exe -m ea_node_editor.automation.mcp_server --mode auto
```

With the extra installed you can use the console script instead:

```powershell
claude mcp add corex -- C:\path\to\EA_Node_Editor\venv\Scripts\corex-mcp.exe --mode auto
```

Add `--scope user` to make the server available in every project. Restart
Claude Code, then ask it to call `corex_status`.

`corex-mcp` answers the MCP handshake immediately and contacts COREX on the
first tool call, so a private spawn (10-20 s) never trips a client's startup
timeout. When no instance is reachable the tool call returns `NOT_FOUND` with a
hint instead of the server failing; when COREX closes, the next tool call
reconnects (and, in `auto` or `private` mode, spawns a new instance).
One `corex-mcp` session sends one request at a time, so a long
`run_status(wait=true)` delays later tool calls, including `run_control(stop)`;
use a short `timeout_s` and poll when you may need to stop a run.

### Register with Codex

Add to `~/.codex/config.toml` (`%USERPROFILE%\.codex\config.toml` on Windows):

```toml
[mcp_servers.corex]
command = "C:\\path\\to\\EA_Node_Editor\\venv\\Scripts\\python.exe"
args = ["-m", "ea_node_editor.automation.mcp_server", "--mode", "auto"]
```

### Register with Claude Desktop

Edit `claude_desktop_config.json` (`%APPDATA%\Claude\claude_desktop_config.json`
on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS) and add the server under `mcpServers`:

```json
{
  "mcpServers": {
    "corex": {
      "command": "C:\\path\\to\\EA_Node_Editor\\venv\\Scripts\\python.exe",
      "args": ["-m", "ea_node_editor.automation.mcp_server", "--mode", "auto"]
    }
  }
}
```

Claude Desktop has no terminal, so prefer `--mode auto` (attaches to a COREX
you started with `--automation`, otherwise spawns a visible one) or
`--mode private --no-headless` when you want a throwaway window.

### Install the agent skill

The tracked skill lives at
[docs/automation/skills/corex-automation/SKILL.md](automation/skills/corex-automation/SKILL.md)
because `.claude/` and `.codex/skills/*` are gitignored. Install a copy into
your user skill folders:

```powershell
.\venv\Scripts\python.exe scripts\install_automation_skill.py --claude --codex
.\venv\Scripts\python.exe scripts\install_automation_skill.py --all --dry-run
.\venv\Scripts\python.exe scripts\install_automation_skill.py --all --force
```

`--claude` writes `%USERPROFILE%\.claude\skills\corex-automation`, `--codex`
writes `%USERPROFILE%\.codex\skills\corex-automation`, `--all` does both,
`--dry-run` only prints the plan, and `--force` overwrites an existing copy.
The script is [scripts/install_automation_skill.py](../scripts/install_automation_skill.py).

### Launch modes

| Mode | Behaviour | Use it for |
| --- | --- | --- |
| `auto` | Attach to the newest live visible instance (private instances belong to whoever spawned them); otherwise spawn a visible instance with its own session state (autosave, last session, staging). `CorexClient.close()` quits an auto-spawned instance only when it has no unsaved changes and otherwise leaves it open; `corex-mcp` always leaves visible instances open for you. `headless` is ignored. | Interactive sessions where you watch the canvas. |
| `attach` | Attach only; `NOT_FOUND` when nothing is live. Never spawns. | Driving a COREX you started yourself. |
| `private` | Always spawn an isolated instance with its own session state (autosave, last session, staging). `headless=True` (default) renders offscreen; `headless=False` opens a real window with full rendering fidelity. | Scripts, tests, unattended runs. |

`corex-mcp --mode auto|attach|private [--headless|--no-headless] [--instance-id ID]`
and `CorexClient.launch(mode, headless=..., instance_id=..., port=...,
startup_timeout_s=...)` take the same choices. `CorexClient.connect()` is
`attach` without the launcher.

### Environment variables

| Variable | Read by | Meaning |
| --- | --- | --- |
| `COREX_AUTOMATION_ENABLED=1` | app (`gate.py`) | Start the in-process server. Set by `--automation`. |
| `COREX_AUTOMATION_PORT` | app | Loopback port; `0` or unset means ephemeral. |
| `COREX_AUTOMATION_INSTANCE_ID` | app | Discovery id; generated when unset. |
| `COREX_AUTOMATION_TOKEN` | app | Shared secret. Popped from `os.environ` at import so subprocesses never inherit it; generated when unset. |
| `COREX_AUTOMATION_MODE` | app | `visible` (default) or `private`; reported by `corex_status` and discovery. |
| `COREX_SESSION_STATE_DIR` | app (`settings.py`) | Overrides the folder for autosave, last-session, and staging. The launcher sets a temp dir for private instances. |
| `COREX_AUTOMATION_DISCOVERY_DIR` | app and clients | Overrides the discovery directory (tests, sandboxes). |
| `EA_NODE_EDITOR_BOOTSTRAPPED=1` | bootstrap | Skips the venv re-exec. The launcher sets it so its instance id matches discovery. |
| `QT_QPA_PLATFORM=offscreen`, `QT_QPA_FONTDIR` | Qt | Set by the launcher for headless private instances (Windows fonts dir `C:\Windows\Fonts`). |

The gate is read once at import time, so these variables cannot flip a running
instance.

### Discovery files

Each instance writes `<instances_dir>/<instance_id>.json` with `instance_id`,
`pid`, `port`, `token`, `mode`, `app_version`, `started_at`, and
`project_path`. The directory is
`%LOCALAPPDATA%\COREX_Node_Editor\automation\instances` on Windows (fallback
`%APPDATA%`, then `~/.config`), or `COREX_AUTOMATION_DISCOVERY_DIR`. Files are
written atomically; listing them drops and deletes records whose process is
gone, so a crashed instance never leaves a live token behind. The file is
removed when the instance stops.

### Security notes

- The token is popped from the environment at import, so execution workers,
  Jupyter kernels, and script subprocesses never see it.
- The server binds `127.0.0.1` only, never `0.0.0.0`; the hello frame must
  carry the token and protocol version 1.
- Discovery files are per user and written with owner-only permissions where
  the platform supports it.
- Clients never quit an instance they attached to. `app.quit` is for private
  instances you launched; `CorexClient.close()` only terminates owned spawned
  instances, and `close(quit_owned_instance=False)` detaches instead.
- Private instances never touch your autosave, last session, or staging; their
  temp session dir is deleted when they are terminated.

## Concepts

### Workspaces, views, scope, subnodes

A project holds workspace tabs; each workspace has one or more camera views
and one graph. Graph ops address the active workspace only (other ids raise
`WRONG_WORKSPACE`). Inside a workspace the open *scope* is either the root or
a subnode shell; `graph.get` with `scope=active` lists what the canvas shows,
`scope=all` lists every node with its `parent_node_id`. `subnode.create`
collapses nodes into a shell (`core.subnode`); boundary edges become
`core.subnode_input` / `core.subnode_output` pins. Enter a shell with
`scope.navigate(target=node)` before adding nodes inside it; `parent_node_id`
on `node.add*` must equal the open scope or you get `WRONG_SCOPE`.

### Passive versus active nodes

Passive nodes (`passive.flowchart.*`, `passive.annotation.*`,
`web.page_viewer`, `io.path_pointer`) draw diagrams and boards and never
execute. Active nodes (`core.*`, `math.*`, `data.*`, plugins) run in the
workflow; the board helpers `media.panel` and `data.panel` are active display
nodes too. `catalog.list_node_types(runtime_behavior=passive)` filters the
passive set, and `catalog.describe_node_type` reports `runtime_behavior`,
ports, properties, enums, defaults, and sizes. `node.set_style` and
`node.update(locked=...)` are passive-only (`NOT_PASSIVE`).

### Flow ports

Passive nodes expose four neutral flow ports keyed `top`, `right`, `bottom`,
`left`. `edge.connect` uses them for both ends. Data ports use their spec keys
(`catalog.describe_node_type` or `graph.get_node` list them); single-valued
data inputs reject a second edge with `PORT_INCOMPATIBLE` unless you pass
`replace_existing=true`, which replaces every edge on that port.

### Ids

Nodes are `node_...`, edges `edge_...`, workspaces `ws_...`, views `view_...`.
Ids are stable for the life of the workspace; `graph.get`, `graph.find_nodes`,
and `workspace.list` refresh them. `node.duplicate` returns an `id_map` from
original to copy.

### Undo semantics

Every mutating op is one entry in the workspace history, whatever it touched
internally. `graph.apply` is one entry for the whole batch; an atomic batch
that fails restores the pre-batch workspace, scope, and selection and records
no entry. `app.history` undoes, redoes, or reports depth (`applied=false`, not
an error, when there is nothing to undo); read-only ops (`graph.*`,
`catalog.*`, `scope.navigate`, `selection.set`, `app.status`) never add
entries.

### Batches and $refs

`graph.apply` takes up to 500 `apply_allowed` ops (`{"id"?, "op", "params"}`).
Keep batches to about 200 ops: each batch captures a workspace snapshot for
rollback, so very large batches cost memory and time; split bigger builds.
Everything is validated before anything mutates: unknown op names raise
`UNKNOWN_OP`, every other static problem one `INVALID_PARAMS` listing
`ops[i].<path>` entries. A later op refers to an earlier result with `$id`
(its primary id: `node_id`, `edge_id`, `group_node_id`, `shell_node_id`, ...)
or `$id.field` / `$id.list.0` for nested fields. Tokens are substituted only
in each op's declared id fields, never inside titles or markdown; write `$$`
for a literal leading dollar there. `atomic=true` (default) raises
`APPLY_FAILED` on the first failing op with `details.failed_index`,
`failed_op`, the inner `error`, and `results` so far; `atomic=false` keeps the
earlier ops (one undo step) and returns `failed_index >= 0`. `scope.navigate`
inside a batch changes the scope for the ops after it. The result's `ids` maps
each batch id to its primary id.

### Verify-after and NO_EFFECT

Handlers normalise input, call the owner, then re-read the record. When
nothing changed (the owner ignored the request or every value already
matched), the op fails with `NO_EFFECT` and `details.reasons` explains why,
for example "passive.flowchart.process is not collapsible". `node.update` and
`edge.update` return `changed`, the list of fields that actually moved.

### Titles, text content, media source

- Flowchart, annotation, and Group backdrop titles are property backed: the
  rendered title is `properties["title"]`. `node.add` passes the title as a
  property override and `node.update(title=...)` writes both fields;
  `catalog.describe_node_type` reports `title_is_property`.
- Flowchart shapes draw `properties["body"]` inside the shape. The classic
  shapes (start, end, process, decision, document, connector, input_output,
  predefined_process, database) default `body` to their name, so `node.add` and
  `node.update` also set `body` from `title` while the body is empty, equal to
  the old title, or still the default; an explicit `properties.body` or a
  customised body always wins. Card, callout, message, timestamp and the other
  decorative shapes use `body` as separate content, so set it explicitly there.
  Verify labels with a screenshot.
- Long flowchart bodies follow `properties["body_fit"]` (every shape except
  timestamp): `clip` (default) keeps the size and ends clipped text in an
  ellipsis, `grow` enlarges the shape until the text fits (square shapes such
  as connector keep their aspect ratio), and `shrink` lowers the font, to 6 px
  at the smallest, until the text fits. Set it with `node.fit_text`
  (`node_fit_text`, `NodesApi.fit_text`): the canvas measures the text, so the
  op waits for the shape to be drawn, applies the mode and any growth as one
  undo step, and returns `text_fit` (`overflowing`, `overflow_mark`,
  `rendered_font_size`). Omit `mode` to only check. A shape the canvas never
  draws (off-screen) times out unchanged: frame it with `view.set_camera` first.
  Setting `body_fit` through `node.update` also works, but the canvas then grows
  the shape later as a separate undo step.
- The bare text node (`passive.annotation.text`) stores its content under the
  `text` key with bare style keys (`font_size`, `text_color`, `format`).
  Flowchart shapes and sticky notes use `body` with prefixed slot keys
  (`body_font_size`, `body_format`). `node.add_text` returns `content_key`, and
  `NodesApi.set_text_style(node_id, content_key, **style)` builds the slot keys.
- `node.add_media` stages the file into the project and creates the panel with
  its `source` input port unexposed; expose the port only when a workflow
  should drive it (the property then becomes port-locked).
- `node.add_web_panel` takes exactly one of `url` or `html`. Inline HTML is a
  session scratch file opened as `file://`; it is not packed into the
  `.cxproj` and disappears with the session. For durable content, copy the
  file in with `project.stage_file` and pass its `artifact_ref` as `url`.

### Style keys and aliases

`catalog.style_schema` returns the persisted key sets, enums, saved presets,
and aliases. Aliases are accepted on input; results always use persisted keys.

| Surface | Persisted keys | Aliases | Notes |
| --- | --- | --- | --- |
| Node (`node.set_style`) | `fill_color`, `gradient_enabled`, `gradient_color`, `gradient_direction`, `border_color`, `border_width`, `corner_radius`, `text_color`, `font_size`, `font_weight` | `fill_color_end` -> `gradient_color` | `gradient_enabled=true` requires `gradient_color`; `font_weight` is `normal` or `bold`; `gradient_direction` is `north`, `east`, `south`, `west`, or `radial`. `preset` applies a saved preset by id or name; `clear=true` removes the override; `propagate=true` copies the style to passive nodes connected by edges (not by type). |
| Edge (`edge.connect` / `edge.update`) | `stroke_color`, `stroke_width`, `stroke_pattern`, `arrow_head`, `arrow_tail`, `path_mode`, `display_mode`, `label_text_color`, `label_background_color`, `label_position`, `label_orientation` | `color`, `width`, `pattern`, `end_arrow` -> `arrow_head`, `start_arrow` -> `arrow_tail`, `label_color`, `label_background`, `label_fraction` -> `label_position`, `label_rotation` -> `label_orientation` | `stroke_pattern` is `solid`, `dashed`, or `dotted`; `arrow_head` (target end, default `filled`) and `arrow_tail` (source end, default `none`) are `filled`, `open`, or `none`, so arrows go at the start, the end, or both; arrowheads scale with `stroke_width` and the line stops under them. `label_position` is the label centre as a 0..1 fraction of the path from source to target (omit for automatic placement); `label_orientation` is `horizontal` or `follow_path` (kept upright). `path_mode` is `auto`, `pipe`, or `bezier` (`auto` clears the override); `display_mode` is `default`, `faint`, or `hidden`. `edge.update(reverse=true)` swaps source and target of a flow edge between flowchart ports in one undo step; `label` accepts `\n` for multi-line labels. |
| Text (`node.add_text` style, `set_text_style`) | `format`, `font_family`, `font_size`, `font_weight`, `italic`, `underline`, `strikeout`, `text_color`, `background_color`, `horizontal_alignment`, `vertical_alignment`, `wrap_mode`, `line_height`, `letter_spacing`, `padding`, `opacity` | `color` -> `text_color` | Ranges are clamped by the owner: `font_size` 6..144, `opacity` 0..100, `padding` 0..64, `line_height` 0.5..4.0, `letter_spacing` -10..20; `0` / sentinel values inherit. |

Colours are `#RRGGBB` or `#RRGGBBAA`.

### Coordinates and grid

`x`, `y` are scene coordinates of the node's top-left corner in canvas units
(pixels at zoom 1). Default flowchart shapes are about 200 x 100; a 320 x 160
grid (320 horizontally between columns, 160 vertically between rows) leaves
room for edge labels and the decision diamond. Keep loops on their own row and
tidy afterwards (see [Tidying the layout](#tidying-the-layout)).
`view.set_camera(frame=all)` frames everything before a screenshot.

Default shape heights differ (start and end 78, process 84, input/output and
predefined process 94, document 104, decision and database 128; read
`catalog.describe_node_type` `default_size`). Nodes placed at the same `y`
align their top edges, so their side ports sit at different heights and
horizontal connectors get small jogs. `layout.tidy` centers every row and
column at once; to fix a single row use `layout.arrange(action=align_center_y)`,
or place each node at `y = row_center - height / 2` yourself.

### Tidying the layout

`layout.tidy` is the canvas Tidy command: one call turns a rough flowchart
into a clean layout with straight wires. Without `node_ids` it tidies every
node in the open scope; with `node_ids` (two or more) it tidies those nodes
plus the members of any Group backdrop among them.

- `mode=auto_layout` (default) rebuilds the arrangement from the wires. Nodes
  go into columns along the flow and rows across it, each centered in its
  cell, so `right` to `left` and `bottom` to `top` wires run straight; a
  `bottom` to `top` branch (a decision's second exit) takes the row below.
  Wires that loop back stay elbows and are listed in `loop_edge_ids`. The
  block keeps its current top-left corner.
- `direction=auto` (default) detects the flow from the port sides the wires
  use; `left_to_right` or `top_to_bottom` force it.
- `mode=in_place` keeps your arrangement: nodes that are roughly in one row or
  column snap onto a shared center line, the gaps become even, and the order
  stays. `direction` does not apply and is reported as `""`.
- `column_gap` (default 96) and `row_gap` (default 64) set the spacing in
  canvas pixels along and across the flow. In place, each gap becomes the
  current median gap, clamped between the value and three times the value.
- Group backdrops stay intact. A listed backdrop's members are laid out inside
  it and the backdrop is refitted (`resized_group_ids`); a collapsed Group
  moves as one block with its hidden members and is laid out at its collapsed
  size at every level; listed nodes inside an unlisted backdrop are tidied as
  their own block and that backdrop grows to keep them. An expanded Group owns
  the nodes inside its area, while a collapsed Group keeps exactly the members
  it had when it was collapsed (nodes over its hidden area stay outside it).
  If the new layout would still move a node into or out of a Group, nothing
  changes and the call fails with `NO_EFFECT`
  (`details.membership_conflict_node_ids`); add the Group backdrop to
  `node_ids` so it moves as one block, or tidy its members on their own.
- Locked nodes (unless the "interact with locked objects" preference is on),
  members of a collapsed Group, and nodes outside an open comment peek are
  left alone, and so are Groups that hold a locked node (with their contents)
  and nodes whose locked Group would have to grow. `skipped_nodes` lists them
  with the reason `locked_node`, `hidden_in_collapsed_group`, `not_selectable`,
  or `locked_group`. The new block steps around locked nodes and those Groups
  instead of covering them. Unwired annotations (sticky notes, text) are never
  re-arranged; one inside a laid-out Group is moved just clear of its members.
- Nodes inside a Group are tidied only with other members of that Group. If no
  two of the given nodes share a level, the call fails with `INVALID_PARAMS`
  ("no two of the given nodes can be laid out together"): add the Group
  backdrop to `node_ids` or pick nodes from one level.
- While the Graphics Settings option "Avoid overlaps when expanding collapsed
  items" is on (the default), other nodes the new block would overlap are
  pushed aside and listed in `pushed_node_ids`.

The result also reports `changed` (false when everything was already tidy),
`moved_node_ids`, `positions`, `straightened_edge_ids`, `skipped_edges` (the
reasons are listed under `layout.straighten` below), and
`overlapping_node_pairs`. It is one undo step; with fewer than two nodes to
arrange the call fails with `INVALID_PARAMS`.

For fine control, `layout.arrange` covers the canvas Layout actions for two or
more nodes:

- `align_left`, `align_right`, `align_top`, `align_bottom` line edges up with
  the outermost node.
- `align_center_y` gives every node the vertical center of their combined
  bounds, so a row of mixed shapes has its side ports at one height.
  `align_center_x` does the same for a column. These two exist only in the
  API; the canvas menus do not offer them, and they ignore `snap_to_grid`
  because snapping the corner would undo the centering.
- `distribute_horizontal` and `distribute_vertical` need three or more nodes.
  They equalise the gaps and keep the outer two nodes in place.
- `match_width` and `match_height` resize passive nodes of the same `type_id`
  to the first listed node of that type. Other nodes are listed in
  `ignored_node_ids`; with no same-type passive pair the call fails with
  `INVALID_PARAMS`.

Every result reports `moved_node_ids`, `resized_node_ids`, `skipped_nodes`,
and `overlapping_node_pairs`, so you can spread nodes out when an alignment
stacked them. The layout actions follow the canvas selection rules: locked
nodes (unless the "interact with locked objects" preference is on), members of
a collapsed Group, and nodes outside an open comment peek are left alone and
listed in `skipped_nodes` with the reason `locked_node`,
`hidden_in_collapsed_group`, or `not_selectable`. With fewer than two usable
nodes the call fails with `INVALID_PARAMS`.

`layout.straighten` is Straighten Connections. It moves nodes so the wires
between them run straight. With no ids it covers every wire in the open scope;
`node_ids` limits it to wires between those nodes, and `edge_ids` adds each
wire's endpoints. A wire can be straightened when both ends sit on horizontal
sides (`right` to `left`) or both on vertical sides (`bottom` to `top`). Only
the listed nodes move. Each connected set of wires is solved per axis and
re-centred on its median offset, so the set does not drift; a set whose wires
need contradictory offsets is not moved on that axis. The result lists
`straightened_edge_ids` and `skipped_edges`. Skip reasons:

- `mixed_port_sides`: an elbow such as `right` to `top`. Reconnect it to
  opposite sides if it should be straight.
- `unresolved_offset`: the ends still differ by `offset` pixels. Either the
  wires of that set need contradictory offsets, or a data-node port is drawn
  away from the anchor the solver aligns (ports inside settings groups or
  inline editors). Move one node with `node.update`.
- `locked_node`, `hidden_in_collapsed_group`, `not_selectable`: an end the
  canvas would not move (see `node_id`).

Straightening can stack nodes, so check `overlapping_node_pairs` too.

A typical tidy pass after building a flowchart:

```python
report = corex.structure.tidy()                   # or tidy(node_ids, mode="in_place")
print(report["direction"], report["loop_edge_ids"])
for skipped in report["skipped_edges"]:
    print(skipped["edge_id"], skipped["reason"])
```

The fine-grained equivalent for one row is
`corex.structure.align(row_ids, "center_y")` followed by
`corex.structure.straighten()`.

### Error handling

Every failure is `{code, message, hint, details, retryable}`; the Python client
raises `AutomationOpError` with the same fields. Read `hint` first.

| Code | What to do |
| --- | --- |
| `APP_BUSY`, `APP_BUSY_MODAL` | Retryable. Wait briefly (ask the user to close the dialog for `APP_BUSY_MODAL`), then resend. `app.status` stays answerable while a dialog is open. |
| `TIMEOUT` | Resend only when `retryable` is true (the request expired in COREX's queue, `details.executed=false`). A client-side timeout (`retryable=false`, `details.client_side=true`) means COREX may still finish the op: check `app.status`, `graph.get` or `app.history` first. |
| `INVALID_PARAMS`, `UNKNOWN_OP`, `UNKNOWN_NODE_TYPE` | Fix the request; `details.problems` / `details.suggestions` name the issue. |
| `NOT_FOUND`, `WRONG_SCOPE`, `WRONG_WORKSPACE` | Refresh ids with `graph.get` / `workspace.list`, navigate or activate, then retry. |
| `PORT_INCOMPATIBLE`, `NOT_PASSIVE`, `PROPERTY_LOCKED_BY_PORT` | Inspect the node with `graph.get_node` and choose another port, op, or unexpose the port. |
| `NO_EFFECT` | Nothing changed; read `details.reasons` before retrying with different values. |
| `PROJECT_DIRTY`, `LAST_WORKSPACE`, `LAST_VIEW`, `RUN_ACTIVE` | Save or pass `discard_unsaved`, create another workspace/view, or wait for / stop the run. In the default auto solution mode, adding or editing active nodes queues an auto-run, so call `run.status(wait=true)` before `run.start`. |
| `APPLY_FAILED` | `details.failed_index` / `details.error` name the failing op; atomic batches were rolled back and left no undo entry. |
| `SAVE_FAILED`, `OPEN_FAILED`, `CAPTURE_FAILED` | Check paths and app state; `details` carries the owner's reason code. |
| `UNEXPECTED_DIALOG`, `APP_SHUTTING_DOWN`, `INTERNAL`, `NOT_IMPLEMENTED`, `AUTH_FAILED`, `PROTOCOL_ERROR` | Inspect the app or reconnect; these are not retryable as-is. |

The full table with default hints is in the [generated reference](#error-codes).

### Screenshots and fidelity

`capture.screenshot(mode=views)` renders content-cropped PNGs of one or more
camera views through the canvas export pipeline; `mode=window` grabs the whole
window. Node shadows are switched off for the grab and restored afterwards so
passive bodies render offscreen. The result reports `fidelity`: `native` for
visible instances, `offscreen_layout` for headless private ones. Offscreen
images are layout evidence (shapes, titles, edges, labels, styles); web panels
and 3D viewers stay blank there. `inline=true` (default) adds `png_base64` per
image (the MCP server returns them as images); pass `output_dir` to choose
where the files go.

## Python client quick start

```python
from pathlib import Path

from ea_node_editor.automation.client import CorexClient
from ea_node_editor.automation.errors import AutomationOpError

out = Path(r"C:\temp\corex-demo")
with CorexClient.launch("private") as corex:              # or CorexClient.connect()
    print(corex.app.status()["active_workspace_id"])      # every op also works via corex.call(op, params)

    batch = corex.apply.batch()                           # one graph.apply = one undo step
    start = batch.add("node.add", {"type_id": "passive.flowchart.start", "x": 0, "y": 0, "title": "Start"}, id="start")
    mesh = batch.add("node.add", {"type_id": "passive.flowchart.process", "x": 320, "y": 0,
                                  "title": "Mesh", "properties": {"body": "Mesh"}}, id="mesh")
    batch.add("edge.connect", {"source_node_id": start, "source_port": "right",
                               "target_node_id": mesh, "target_port": "left", "label": "go"}, id="e1")
    ids = batch.run(label="Build flowchart")["ids"]       # {"start": "node_...", "mesh": "node_...", "e1": "edge_..."}

    corex.nodes.set_style(ids["mesh"], {"fill_color": "#FFE0B2", "border_color": "#EF6C00"})
    try:
        corex.nodes.update(ids["mesh"], collapsed=True)
    except AutomationOpError as exc:                      # NO_EFFECT: flowchart shapes are not collapsible
        print(exc.code, exc.details.get("reasons"))

    corex.workspaces.frame_all()
    corex.project.save_as(out / "demo.cxproj")
    shot = corex.capture.screenshot_to(out)
    print(shot["saved_paths"], shot["fidelity"])
```

`CorexClient.launch(mode, headless=True)` spawns or attaches; on `close()` (or
leaving the `with` block) it quits and cleans up an instance it spawned and only
disconnects from one it attached to. `CorexClient.connect(instance_id=None)`
attaches to a live instance from discovery. `call(op, params, timeout_s=30)` is
the universal entry point; the facades below are thin sugar that build the same
params (they never validate on their own, the server does). Every facade also
has `call(op, params)`.

| Facade | Methods |
| --- | --- |
| `corex.app` | `status()`, `history(action)`, `undo()`, `redo()`, `quit(discard_unsaved=)` |
| `corex.catalog` | `list_node_types(query=, category=, runtime_behavior=, limit=)`, `describe_node_type(type_id)`, `style_schema()` |
| `corex.graph` | `get(workspace_id=, scope=, include_style=, include_properties=)`, `get_node(node_id)`, `find_nodes(query=, type_id=, title=, title_contains=, scope=, limit=)` |
| `corex.nodes` | `add(type_id, x, y, title=, width=, height=, parent_node_id=, select=, properties=)`, `add_text(markdown, x, y, format=, style=, ...)`, `add_media(path, x, y, fit_mode=, show_title=, show_frame=, ...)`, `add_web_panel(x, y, url= or html=, display_mode=, ...)`, `update(node_id, title=, x=, y=, width=, height=, properties=, port_labels=, exposed_ports=, collapsed=, locked=)`, `set_style(node_id, style, preset=, replace=, clear=, propagate=)`, `delete(ids)`, `duplicate(ids, offset_x=, offset_y=)`; sugar `add_path_pointer(path, x, y, mode=)`, `add_panel(x, y, ...)`, `set_text_style(node_id, content_key, **style)` |
| `corex.edges` | `connect(source, source_port, target, target_port, replace_existing=, label=, style=)`, `update(edge_id, label=, style=, path_mode=, enabled=, display_mode=, clear_style=, clear_label=)`, `set_label`, `clear_label`, `set_style`, `clear_style`, `set_path_mode`, `set_display_mode`, `set_enabled`, `delete(ids)` |
| `corex.structure` | `wrap_group(ids, title=)`, `create_subnode(ids, title=)`, `ungroup_subnode(shell)`, `add_subnode_pin(shell, direction)`, `add_input_pin`, `add_output_pin`, `navigate_scope(target, node_id=)`, `open_subnode(shell)`, `navigate_parent()`, `navigate_root()`, `set_selection(ids, mode=)`, `select`, `add_to_selection`, `clear_selection`, `arrange(ids, action)`, `align(ids, side)` (side also `center_x` / `center_y`), `distribute(ids, orientation)`, `match_size(ids, dimension)`, `straighten(node_ids=None, edge_ids=)`, `tidy(node_ids=None, mode=, direction=, column_gap=, row_gap=)` |
| `corex.annotations` | `comment_upsert(...)`, `comment(node_id, body)`, `reply(node_id, parent_id, body)`, `resolve(node_id, comment_id)`, `comment_remove`, `link_upsert(...)`, `link_url` / `link_file` / `link_folder` / `link_workspace` / `link_node`, `link_remove` |
| `corex.workspaces` | `list()`, `create(name, duplicate_of=, activate=)`, `duplicate(workspace_id)`, `update`, `rename`, `activate`, `close(workspace_id, discard_unsaved=)`, `create_view`, `update_view`, `activate_view`, `close_view`, `set_camera(zoom=, center_x=, center_y=, frame=, node_ids=)`, `frame_all()`, `frame_selection()`, `frame_nodes(ids)` |
| `corex.project` | `open(path, discard_unsaved=)`, `new(discard_unsaved=)`, `save(path=None)`, `save_as(path)`, `stage_file(path or content=, filename=, subdirectory=, node_id=)`, `stage_bytes(filename, content)` |
| `corex.run` | `start(scope=, node_ids=, wait=, timeout_s=, log_tail=)`, `status(wait=, timeout_s=)`, `control(action)`, `stop()`, `pause()`, `resume()`, `run_and_wait(timeout_s=120, node_ids=)`, `wait(timeout_s=120)` |
| `corex.capture` | `screenshot(mode=, view_ids=, scale=, crop_to_content=, output_dir=, filename_stem=, inline=)`, `screenshot_to(dir or file.png)` (adds `saved_paths`); module helper `save_png(image, path)` |
| `corex.apply` | `apply(ops, atomic=True, label=)`, `batch()` returning a `BatchBuilder` with `add(op, params, id=)` (returns the `$id` token), `.ops`, and `run(atomic=, label=)`; module helper `ref(batch_id, path)` builds `$id.path` tokens |

`RunApi` sends a request timeout a few seconds longer than the wait itself. With
raw `call()`, pass a larger `timeout_s` than the op's own `timeout_s` when you
wait on a run (`corex.call("run.start", {"wait": True, "timeout_s": 120},
timeout_s=135)`).

## UI parity

Every graph, tab, and view action reachable from the COREX UI, and the op that
performs it. "not exposed" means the first pass deliberately leaves it out
(dialogs, the OS clipboard, OS launches, transient overlays).

| UI surface | Action | Automation |
| --- | --- | --- |
| Floating toolbar (node) | Run Selected | `run.start(scope=nodes, node_ids=[...])` |
| Floating toolbar (node) | Expand / Collapse | `node.update(collapsed=...)` |
| Floating toolbar (node) | Lock / Unlock (passive) | `node.update(locked=...)` |
| Floating toolbar (node) | Enter Subnode | `scope.navigate(target=node, node_id=shell)` |
| Floating toolbar (node) | Rename Node | `node.update(title=...)` |
| Floating toolbar (node) | Duplicate Node | `node.duplicate` |
| Floating toolbar (node) | Remove Node | `node.delete` |
| Floating toolbar (node) | Text formatting popovers (font, size, emphasis, alignment, colours) | `node.add_text(style=...)`, `node.update(properties=...)` via `set_text_style` |
| Floating toolbar (node) | Media fit / playback / PDF page controls | `node.update(properties={fit_mode, animation_playback_mode, ...})` |
| Floating toolbar (node) | Path Pointer Open / Open with... | not exposed (OS launch) |
| Floating toolbar (node) | Panel font size / align / fit actions | not exposed (surface-local formatting) |
| Floating toolbar (node) | Python Script Open Script | not exposed (editor) |
| Floating toolbar (edge) | Enable / Disable (Ctrl+E) | `edge.update(enabled=...)` |
| Floating toolbar (edge) | Quick style (colour, width, pattern, arrow) | `edge.update(style=...)` |
| Floating toolbar (edge) | Inline label edit | `edge.update(label=...)` |
| Floating toolbar (selection) | Wrap Selection in Group (C) | `group.wrap` |
| Floating toolbar (selection) | Align Left / Right / Top / Bottom | `layout.arrange(action=align_*)` |
| Floating toolbar (selection) | Distribute Horizontally / Vertically | `layout.arrange(action=distribute_*)` |
| Floating toolbar (selection) | Straighten Connections | `layout.straighten(node_ids=[...])` |
| Floating toolbar (selection) | Tidy (Auto-Layout) | `layout.tidy(node_ids=[...])` |
| Floating toolbar (selection) | Run Selected / Preview Run | `run.start(scope=nodes)`; preview overlay not exposed |
| Node context menu | Edit Style... | `node.set_style(style=... \| preset=...)` |
| Node context menu | Reset Style | `node.set_style(clear=true)` |
| Node context menu | Copy Style / Paste Style | not exposed (clipboard); read `graph.get_node().visual_style`, write `node.set_style(replace=true)` |
| Node context menu | Propagate Style | `node.set_style(propagate=true)` |
| Node context menu | Add Comment | `comment.upsert` |
| Node context menu | Add Link | `link.upsert` |
| Node context menu | Peek Inside / Exit Peek | not exposed (transient overlay) |
| Node context menu | Ungroup Subnode | `subnode.ungroup` |
| Node context menu | Run Settings... | not exposed (dialog) |
| Node context menu | Open Add-On Manager | not exposed (dialog) |
| Node context menu | Add to Workflows | not exposed (dialog) |
| Node context menu | Help (F1) | `catalog.describe_node_type` |
| Node context menu | Settings group toggles | `node.update(properties=...)` where the group is property backed; otherwise not exposed |
| Port context menu | Graft / Flatten / Simplify / Reverse / Clean / Principal | not exposed |
| Port context menu | Dynamic group Add / Insert / Remove / Rename | not exposed |
| Inspector | Port labels, exposed ports | `node.update(port_labels=..., exposed_ports=...)` |
| Inspector | Properties | `node.update(properties=...)` (`PROPERTY_LOCKED_BY_PORT` when a connected or exposed port drives it) |
| Edge context menu | Edit Flow Edge... | `edge.update(style=..., path_mode=...)` |
| Edge context menu | Edit Label... | `edge.update(label=...)` / `clear_label=true` |
| Edge context menu | Reset Style | `edge.update(clear_style=true)` |
| Edge context menu | Copy Style / Paste Style | not exposed (clipboard) |
| Edge context menu | Path: Auto / Pipe / Bezier | `edge.update(path_mode=...)` |
| Edge context menu | Remove Connection | `edge.delete` |
| Canvas / selection context menu | Connect Selected (Ctrl+Shift+L) | `edge.connect` |
| Canvas / selection context menu | Copy / Cut / Paste Selection | not exposed (clipboard); `node.duplicate` copies within the workspace |
| Canvas / selection context menu | Duplicate Selection (Ctrl+D) | `node.duplicate` |
| Canvas / selection context menu | Delete Selection | `node.delete` / `edge.delete`; on a selected collapsed Group the canvas also deletes what it holds, while `node.delete` keeps those nodes and shows them again, so list them too to match |
| Canvas / selection context menu | Group Selection (Ctrl+Alt+G) | `subnode.create` |
| Canvas / selection context menu | Ungroup Selection (Ctrl+Shift+G) | `subnode.ungroup` |
| Canvas / selection context menu | Set Same Width / Height | `layout.arrange(action=match_width \| match_height)` |
| Canvas / selection context menu | Tidy > Auto-Layout (Ctrl+Alt+L) | `layout.tidy(node_ids=[...])` |
| Canvas / selection context menu | Tidy > Auto-Layout Left to Right / Top to Bottom | `layout.tidy(node_ids=[...], direction=left_to_right \| top_to_bottom)` |
| Canvas / selection context menu | Tidy > Clean Up in Place | `layout.tidy(node_ids=[...], mode=in_place)` |
| Canvas / selection context menu | Quick add from the library | `node.add`, `node.add_text`, `node.add_media`, `node.add_web_panel` |
| Canvas options menu (empty canvas) | Tidy whole graph (Ctrl+Alt+Shift+L) | `layout.tidy()` |
| Canvas options menu (empty canvas) | Clean up whole graph in place | `layout.tidy(mode=in_place)` |
| Canvas | Select / marquee | `selection.set(mode=replace \| add \| clear)` |
| Canvas | Drag / resize nodes | `node.update(x=, y=, width=, height=)`; moving a Group carries everything inside it like a drag (`carried_node_ids`), and `move_contents=false` moves or reshapes only an expanded Group's frame, like its corner handles |
| Canvas | Scope Parent (Alt+Left) / Scope Root (Alt+Home) | `scope.navigate(target=parent \| root)` |
| Canvas | Folder Explorer surface actions | not exposed (filesystem) |
| Workspace tab | New / Duplicate workspace | `workspace.create(name=, duplicate_of=)` |
| Workspace tab | Rename / Activate | `workspace.update(name=, activate=true)` |
| Workspace tab | Close | `workspace.close(discard_unsaved=)` |
| Workspace tab | List | `workspace.list` |
| View | New view / Rename / Switch / Close | `view.create`, `view.update`, `view.close` |
| View | Zoom, pan, Frame All / Frame Selection | `view.set_camera(zoom=, center_x=, center_y=, frame=all \| selection \| nodes)` |
| View | Export canvas PNG | `capture.screenshot` |
| Edit menu | Undo / Redo | `app.history(action=undo \| redo)` |
| Edit menu | Layout > Tidy Selection (Ctrl+Alt+L), Tidy Selection Left to Right / Top to Bottom, Clean Up Selection in Place | `layout.tidy(node_ids=[...], direction=..., mode=...)` |
| Edit menu | Layout > Tidy Whole Graph (Ctrl+Alt+Shift+L), Clean Up Whole Graph in Place | `layout.tidy()`, `layout.tidy(mode=in_place)` |
| Edit menu | Snap to Grid | not exposed (session toggle); `node.update` uses the exact x/y given, and `layout.arrange(snap_to_grid=true)` snaps align and distribute results |
| Edit menu | Graph Search (Ctrl+K) | `graph.find_nodes`; the search overlay itself is not exposed (transient overlay) |
| Edit menu | Interact with Locked Objects | not exposed (session toggle) |
| File menu | New / Open project | `project.open(new=true)` / `project.open(path=)` |
| File menu | Save / Save As | `project.save` / `project.save(path=)` |
| File menu | Stage a file into the project | `project.stage_file` |
| File menu | New Plugin, Reload Plugins, Workflow settings | not exposed (dialogs) |
| Run toolbar | Run workflow / Stop / Pause / Resume | `run.start`, `run.control(action=stop \| pause \| resume)`, `run.status` |
| Window | Quit | `app.quit` (private instances only) |

## Walkthroughs

Each walkthrough is a runnable script in
[examples/automation](../examples/automation/README.md). All scripts take
`--mode auto|attach|private` (default `private`), `--headless` /
`--no-headless`, `--output-dir`, `--instance-id`, and `--startup-timeout`,
print the artifact paths, exit non-zero on failure, and never leave a private
instance running (`with CorexClient.launch(...)`). In a private instance they
start from `project.new` and Save As into `--output-dir`; attached to a
running COREX they build in a new workspace tab and do not save.

### 1. Engineering flowchart ([flowchart.py](../examples/automation/flowchart.py))

1. `app.status` confirms the instance is idle; `project.new` and
   `workspace.update` name the workspace.
2. One `graph.apply` (label "Build engineering flowchart", 20 ops, one undo
   step): ten `node.add` ops on a 320-unit column grid (Start, Import CAD,
   Clean geometry, Mesh, Solve, Converged?, Export results, Archive to PDM,
   End on the main row; Refine mesh on a loop row 240 below the decision),
   each with `title` and a matching `body`, then ten `edge.connect` ops wired
   with `$start`, `$mesh`, ... refs. The decision edges carry the labels
   `yes` and `no`; the loop runs from Refine mesh `left` back to Mesh
   `bottom`.
3. `node.set_style` paints the yes branch green and Refine mesh orange;
   `edge.update` colours the branch edges (aliases `color`, `width`,
   `label_color`) and labels and dashes the loop edge.
4. `layout.tidy` (no ids) lays the chart out left to right from its wires:
   the main row shares one center line, Refine mesh sits centered below the
   decision, and the loop back to Mesh is the only elbow (`loop_edge_ids` and
   `skipped_edges` both name it).
5. `graph.get` checks 10 nodes and 10 edges, `view.set_camera(frame=all)`,
   `project.save(path=<output>/flowchart.cxproj)`, `capture.screenshot`.

### 2. Annotated media board ([annotated_media_board.py](../examples/automation/annotated_media_board.py))

1. Write `mesh_preview.png` with stdlib `zlib` / `struct` (no imaging
   library): a gradient under a triangulated grid.
2. `node.add_text` with a markdown brief and a text style (`color` alias);
   `node.add_media` for the PNG (staged into the project, `source` port
   unexposed); `NodesApi.add_path_pointer` (`io.path_pointer`, mode `file`) and
   `add_panel` (`data.panel` with `properties.value`).
3. `group.wrap` around all four with the title "Mesh review board".
4. `comment.upsert` on the media node, a threaded reply (`parent_id`), then
   `AnnotationsApi.resolve`; `link.upsert` (`kind=url`) on the text node.
5. `graph.get_node` confirms two comments and one link, then frame, save, and
   screenshot.

### 3. Subnode workflow ([subnode_workflow.py](../examples/automation/subnode_workflow.py))

1. A `BatchBuilder` batch builds Start -> Prepare geometry -> Mesh -> Solve ->
   End.
2. `subnode.create` on Prepare geometry + Mesh (title "Preprocess"); the two
   boundary edges become one input and one output pin.
   `subnode.add_pin(direction=out)` adds a spare output pin.
3. `scope.navigate(target=node)` enters the shell, `node.add` places the
   "Quality gate" decision below the members (its `parent_node_id` is the
   shell), a screenshot records the inner scope, and
   `scope.navigate(target=root)` returns.
4. `app.history(action=undo)` removes the inner node and `redo` restores it;
   `graph.find_nodes(scope=all)` proves both steps.
5. Screenshot of the root scope.

### 4. Run and screenshot ([run_and_screenshot.py](../examples/automation/run_and_screenshot.py))

1. `project.open(new=true)` for a fresh project (a new workspace when
   attached); refuses to start while another run is active.
2. `catalog.describe_node_type` for `core.constant` and `core.logger` confirms
   the port keys (`as_text` out, `message` in) and the `value` property.
3. `node.add` both (the constant carries a text value), expose `message` if it
   is hidden, and `edge.connect(as_text -> message)`.
4. `RunApi.run_and_wait(timeout_s=90)` (`run.start` with `wait=true`); print
   `outcome`, `engine_state`, completed / failed ids, `root_errors`, and
   `log_tail`.
5. Screenshot; exit 1 unless the outcome is `completed` and the wait did not
   time out.

## Generated reference

This block is generated from the op catalog by
[ea_node_editor/automation/docgen.py](../ea_node_editor/automation/docgen.py).
Do not edit it by hand; run
`.\venv\Scripts\python.exe -m ea_node_editor.automation.docgen --update-guide`
after changing an op spec or error code (`tests/automation/test_docgen.py`
fails on drift). The MCP server renders its own compact `corex://ops` resource
from the same catalog.

<!-- BEGIN GENERATED OP REFERENCE -->
### MCP tool index

| MCP tool | Op | Summary |
| --- | --- | --- |
| `corex_status` | `app.status` | Report instance identity, project, active workspace/view/scope, selection, run state, and busy flags. |
| `corex_history` | `app.history` | Undo or redo the last automation/user step in the active workspace, or report undo/redo depth. |
| `corex_quit` | `app.quit` | Close the COREX instance (refuses with PROJECT_DIRTY unless discard_unsaved=true). |
| `catalog_list_node_types` | `catalog.list_node_types` | List available node types with optional text/category/behaviour filters. |
| `catalog_describe_node_type` | `catalog.describe_node_type` | Describe one node type: ports, properties (types, enums, defaults), sizing, collapsible/resizable flags. |
| `catalog_style_schema` | `catalog.style_schema` | Return the authoritative node-style, edge-style, and text-style key sets, enums, and saved presets. |
| `graph_get` | `graph.get` | Snapshot the active workspace: nodes, edges, views, scope, selection (optionally styles/properties). |
| `graph_get_node` | `graph.get_node` | Full detail for one node: geometry, properties, style, effective ports with connections, links, comments. |
| `graph_find_nodes` | `graph.find_nodes` | Find nodes in the active workspace by title text, exact type id, or free-text query. |
| `node_add` | `node.add` | Create a node of any registered type at (x, y) with optional title, size, and property overrides. |
| `node_add_text` | `node.add_text` | Create a markdown text annotation (passive.annotation.text) with optional text style. |
| `node_add_media` | `node.add_media` | Create a media panel (media.panel) showing an image, video, or PDF file; the file is staged into the project. |
| `node_add_web_panel` | `node.add_web_panel` | Create a web viewer (web.page_viewer) for a URL, or for inline HTML written to a session scratch file. |
| `node_update` | `node.update` | Update title, position, size, properties, port labels, exposed ports, collapsed, or locked on one node. |
| `node_set_style` | `node.set_style` | Set, merge, clear, or propagate a passive node's visual style (or apply a saved preset). |
| `node_fit_text` | `node.fit_text` | Set a flowchart shape's text fit (clip, grow, shrink) and report how its body text fits once drawn. |
| `node_delete` | `node.delete` | Delete one or more nodes (and their edges) from the active workspace. |
| `node_duplicate` | `node.duplicate` | Duplicate a set of nodes (with internal edges) offset from the originals. |
| `edge_connect` | `edge.connect` | Connect two ports. Passive flow ports are top\|right\|bottom\|left; data ports use their spec keys. |
| `edge_update` | `edge.update` | Update an edge's label, style, path mode, enabled flag, or display mode; optionally clear label/style or reverse its direction. |
| `edge_delete` | `edge.delete` | Delete one or more edges. |
| `group_wrap` | `group.wrap` | Wrap nodes in a Group backdrop (passive.annotation.group_backdrop) with an optional title. |
| `subnode_create` | `subnode.create` | Collapse nodes into a subnode shell (nested scope); boundary edges become input/output pins. |
| `subnode_ungroup` | `subnode.ungroup` | Dissolve a subnode shell, restoring its members to the current scope. |
| `subnode_add_pin` | `subnode.add_pin` | Add an input or output pin to a subnode shell. |
| `scope_navigate` | `scope.navigate` | Open a subnode scope (target=node), go up one level (parent), or return to the root scope. |
| `selection_set` | `selection.set` | Replace, extend, or clear the canvas selection. |
| `layout_arrange` | `layout.arrange` | Align, distribute, or match the size of a set of nodes (align left/right/top/bottom/center_x/center_y, distribute horizontal/vertical, match_width/match_height). |
| `layout_straighten` | `layout.straighten` | Move nodes so the wires between them run straight (the Straighten Connections action). |
| `layout_tidy` | `layout.tidy` | Tidy nodes: auto-layout from the wires (left to right / top to bottom) or clean up in place, keeping Group backdrops intact. |
| `comment_upsert` | `comment.upsert` | Add or edit a comment on a node (threaded via parent_id; resolved/pinned flags). |
| `comment_remove` | `comment.remove` | Remove a comment from a node. |
| `link_upsert` | `link.upsert` | Add or edit a link on a node: url, file, folder, workspace, or node targets; optional ordering position. |
| `link_remove` | `link.remove` | Remove a link from a node. |
| `workspace_list` | `workspace.list` | List workspaces (tabs) with their views, dirty flags, and which one is active. |
| `workspace_create` | `workspace.create` | Create a new workspace tab (optionally duplicating an existing one) and activate it by default. |
| `workspace_update` | `workspace.update` | Rename a workspace and/or make it the active tab. |
| `workspace_close` | `workspace.close` | Close a workspace tab (PROJECT_DIRTY unless discard_unsaved=true; LAST_WORKSPACE if it is the only one). |
| `view_create` | `view.create` | Create a new camera view in the active workspace (copies the current camera) and activate it. |
| `view_update` | `view.update` | Rename a view and/or switch to it. |
| `view_close` | `view.close` | Close a view (LAST_VIEW when it is the only one). |
| `view_set_camera` | `view.set_camera` | Set zoom/center explicitly or frame all nodes, the selection, or specific nodes. |
| `project_open` | `project.open` | Open a .cxproj (path) or start a new blank project (new=true); refuses PROJECT_DIRTY unless discard_unsaved. |
| `project_save` | `project.save` | Save the project; pass path to Save As. Staged node files are published into the .data folder. |
| `project_stage_file` | `project.stage_file` | Copy a local file (or write bytes) into the project's staging area and return its artifact ref. |
| `run_start` | `run.start` | Run the active workspace or a set of nodes; optionally wait for completion (wait=true). |
| `run_status` | `run.status` | Report run state and per-node outcomes; wait=true blocks until idle or timeout. |
| `run_control` | `run.control` | Stop, pause, or resume the active run. |
| `capture_screenshot` | `capture.screenshot` | Render canvas views (content-cropped PNGs) or grab the whole window; returns paths and inline PNGs. |
| `graph_apply` | `graph.apply` | Apply up to 500 graph ops as ONE undo step; later ops reference earlier results with $id (or $id.field). |

### app

#### app.status

MCP tool: `corex_status`. Flags: read-only.

Report instance identity, project, active workspace/view/scope, selection, run state, and busy flags.

Call this first. It never mutates anything and tells you whether the app is busy (modal dialog, project IO, active run) before you plan a batch.

No parameters.

Result keys: `app_version`, `protocol`, `instance_id`, `pid`, `mode`, `qt_platform`, `project_path`, `project_dirty`, `active_workspace_id`, `active_workspace_name`, `active_view_id`, `scope_path`, `selected_node_ids`, `run`, `busy`, `node_count`, `edge_count`.

#### app.history

MCP tool: `corex_history`. Flags: read-only.

Undo or redo the last automation/user step in the active workspace, or report undo/redo depth.

Every mutating automation op is exactly one undo step (graph.apply batches are one step). action=status only reads.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `action` | `string` | no | `"status"` | undo \| redo \| status; one of: undo, redo, status |

Result keys: `applied`, `action_type`, `can_undo`, `can_redo`, `undo_depth`, `redo_depth`, `workspace_id`.

#### app.quit

MCP tool: `corex_quit`. Flags: read-only.

Close the COREX instance (refuses with PROJECT_DIRTY unless discard_unsaved=true).

Use only for private instances you launched. Attached visible instances belong to the user.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `discard_unsaved` | `boolean` | no | `false` |  |

Result keys: `quitting`, `project_dirty`.

### catalog

#### catalog.list_node_types

MCP tool: `catalog_list_node_types`. Flags: read-only.

List available node types with optional text/category/behaviour filters.

Flowcharts and boards are built from the passive families (passive.flowchart.\*, passive.annotation.\*, web.page_viewer, io.path_pointer) plus two active display nodes (media.panel, data.panel); node_set_style only accepts passive nodes.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `query` | `string` | no |  | Case-insensitive match against id, name, keywords, category |
| `category` | `string` | no |  | Category path prefix, e.g. 'Flowchart' or 'Utilities/Reporting' |
| `runtime_behavior` | `string` | no | `"any"` | one of: any, active, passive |
| `limit` | `integer` | no | `200` | >= 1 and \<= 500 |

Result keys: `node_types`, `total`.

#### catalog.describe_node_type

MCP tool: `catalog_describe_node_type`. Flags: read-only.

Describe one node type: ports, properties (types, enums, defaults), sizing, collapsible/resizable flags.

Unknown ids return UNKNOWN_NODE_TYPE with close suggestions in details.suggestions.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `type_id` | `string` | yes |  | Node type id, e.g. passive.flowchart.process; non-empty |

Result keys: `type_id`, `display_name`, `category_path`, `description`, `runtime_behavior`, `surface_family`, `surface_variant`, `collapsible`, `resizable`, `default_size`, `min_size`, `ports`, `properties`, `keywords`.

#### catalog.style_schema

MCP tool: `catalog_style_schema`. Flags: read-only.

Return the authoritative node-style, edge-style, and text-style key sets, enums, and saved presets.

Use the returned keys with node.set_style, edge.update, and node.add_text style params.

No parameters.

Result keys: `node_style`, `edge_style`, `text_style`, `presets`.

### graph

#### graph.get

MCP tool: `graph_get`. Flags: read-only.

Snapshot the active workspace: nodes, edges, views, scope, selection (optionally styles/properties).

scope=active (default) returns only nodes visible in the open scope; scope=all returns every node with parent_node_id so you can reason about subnodes.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `workspace_id` | `string` | no |  | Defaults to the active workspace; other ids raise WRONG_WORKSPACE |
| `scope` | `string` | no | `"active"` | one of: active, all |
| `include_style` | `boolean` | no | `false` |  |
| `include_properties` | `boolean` | no | `false` |  |

Result keys: `workspace_id`, `workspace_name`, `dirty`, `scope_path`, `active_view_id`, `views`, `nodes`, `edges`, `selected_node_ids`.

#### graph.get_node

MCP tool: `graph_get_node`. Flags: read-only.

Full detail for one node: geometry, properties, style, effective ports with connections, links, comments.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |

Result keys: `node`, `properties`, `visual_style`, `port_labels`, `exposed_ports`, `ports`, `incident_edges`, `links`, `comments`, `in_active_scope`.

#### graph.find_nodes

MCP tool: `graph_find_nodes`. Flags: read-only.

Find nodes in the active workspace by title text, exact type id, or free-text query.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `query` | `string` | no |  | Case-insensitive match on title, type id, display name |
| `type_id` | `string` | no |  | Node type id, e.g. passive.flowchart.process; non-empty |
| `title` | `string` | no |  | Exact title match |
| `title_contains` | `string` | no |  | Case-insensitive substring of the title |
| `scope` | `string` | no | `"all"` | one of: active, all |
| `limit` | `integer` | no | `100` | >= 1 and \<= 1000 |

Result keys: `nodes`, `total`.

### node

#### node.add

MCP tool: `node_add`. Flags: undo step, apply-allowed.

Create a node of any registered type at (x, y) with optional title, size, and property overrides.

Use catalog.describe_node_type first for property keys. Flowchart shapes: passive.flowchart.start|process|decision|end|document|database|input_output|connector|... Path pointer: io.path_pointer (properties.path, properties.mode=file|folder). Panel: data.panel.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `type_id` | `string` | yes |  | Node type id, e.g. passive.flowchart.process; non-empty |
| `x` | `number` | yes |  | Scene coordinate in canvas units |
| `y` | `number` | yes |  | Scene coordinate in canvas units |
| `title` | `string` | no |  | Node title shown in the header |
| `width` | `number` | no |  | Size in canvas units; >= 1 |
| `height` | `number` | no |  | Size in canvas units; >= 1 |
| `parent_node_id` | `string` | no |  | Create inside this subnode shell (must be the open scope) |
| `select` | `boolean` | no | `false` | Select the new node after creation |
| `properties` | `object` | no |  | Property overrides validated by the registry |

Result keys: `node_id`, `node`.

Example:

```json
{
  "type_id": "passive.flowchart.process",
  "x": 320,
  "y": 120,
  "title": "Mesh the part"
}
```

#### node.add_text

MCP tool: `node_add_text`. Flags: undo step, apply-allowed.

Create a markdown text annotation (passive.annotation.text) with optional text style.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `markdown` | `string` | yes |  | Body text; markdown by default |
| `x` | `number` | yes |  | Scene coordinate in canvas units |
| `y` | `number` | yes |  | Scene coordinate in canvas units |
| `title` | `string` | no |  | Node title shown in the header |
| `width` | `number` | no |  | Size in canvas units; >= 1 |
| `height` | `number` | no |  | Size in canvas units; >= 1 |
| `parent_node_id` | `string` | no |  | Create inside this subnode shell (must be the open scope) |
| `select` | `boolean` | no | `false` | Select the new node after creation |
| `format` | `string` | no | `"markdown"` | one of: markdown, plain |
| `style` | `object` | no |  | Rich text slot style (persisted keys; see catalog.style_schema for aliases and ranges) |

Result keys: `node_id`, `node`.

#### node.add_media

MCP tool: `node_add_media`. Flags: undo step, apply-allowed.

Create a media panel (media.panel) showing an image, video, or PDF file; the file is staged into the project.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `path` | `string` | yes |  | Absolute path to an image/video/PDF; non-empty |
| `x` | `number` | yes |  | Scene coordinate in canvas units |
| `y` | `number` | yes |  | Scene coordinate in canvas units |
| `title` | `string` | no |  | Node title shown in the header |
| `width` | `number` | no |  | Size in canvas units; >= 1 |
| `height` | `number` | no |  | Size in canvas units; >= 1 |
| `parent_node_id` | `string` | no |  | Create inside this subnode shell (must be the open scope) |
| `select` | `boolean` | no | `false` | Select the new node after creation |
| `fit_mode` | `string` | no |  | Media fit mode (see catalog.describe_node_type media.panel) |
| `show_title` | `boolean` | no |  |  |
| `show_frame` | `boolean` | no |  |  |

Result keys: `node_id`, `node`, `artifact_ref`.

#### node.add_web_panel

MCP tool: `node_add_web_panel`. Flags: undo step, apply-allowed.

Create a web viewer (web.page_viewer) for a URL, or for inline HTML written to a session scratch file.

Inline html is written to the project's session staging folder (\<staging>/automation/\<uuid>.html) and opened as a file:// URL. It is NOT packed into the .cxproj on save and is lost with the session (a private instance deletes it on close). For durable content pass url pointing at a file you own, or copy the file in with project.stage_file and pass its artifact_ref (temp://...) as url; the save then packs it into the project (a file:// URL of staged_path is not packed). Web content is not rendered in offscreen (private headless) screenshots.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `url` | `string` | no |  | http(s):// or file:// location |
| `html` | `string` | no |  | Inline HTML document; staged under the project and opened as file:// |
| `x` | `number` | yes |  | Scene coordinate in canvas units |
| `y` | `number` | yes |  | Scene coordinate in canvas units |
| `title` | `string` | no |  | Node title shown in the header |
| `width` | `number` | no |  | Size in canvas units; >= 1 |
| `height` | `number` | no |  | Size in canvas units; >= 1 |
| `parent_node_id` | `string` | no |  | Create inside this subnode shell (must be the open scope) |
| `select` | `boolean` | no | `false` | Select the new node after creation |
| `display_mode` | `string` | no |  | web.page_viewer display mode enum |

Result keys: `node_id`, `node`, `url`.

#### node.update

MCP tool: `node_update`. Flags: undo step, apply-allowed.

Update title, position, size, properties, port labels, exposed ports, collapsed, or locked on one node.

Only supplied fields change; the result lists what actually changed (NO_EFFECT when nothing did). Properties driven by a connected/exposed port return PROPERTY_LOCKED_BY_PORT. Expanding makes room: neighbours move aside and parent Groups grow; it fails with NO_EFFECT when a locked Group would have to grow or no room exists. Moving a Group backdrop (x/y) moves everything inside it by the same amount, nested Groups and locked nodes included, like dragging it on the canvas; carried_node_ids lists those nodes, so do not move them yourself. move_contents=false moves or reshapes only an expanded Group's frame (like its corner handles): the nodes stay, so it can grow up or left around nodes. A collapsed Group always carries what it holds.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `title` | `string` | no |  | Node title shown in the header |
| `x` | `number` | no |  | Scene coordinate in canvas units |
| `y` | `number` | no |  | Scene coordinate in canvas units |
| `width` | `number` | no |  | Size in canvas units; >= 1 |
| `height` | `number` | no |  | Size in canvas units; >= 1 |
| `properties` | `object` | no |  |  |
| `port_labels` | `object` | no |  | port_key -> label ('' clears) |
| `exposed_ports` | `object` | no |  | port_key -> bool |
| `collapsed` | `boolean` | no |  |  |
| `locked` | `boolean` | no |  |  |
| `move_contents` | `boolean` | no | `true` | Group backdrops only: false moves/reshapes the expanded frame without the nodes inside |

Result keys: `node_id`, `changed`, `node`, `carried_node_ids`.

#### node.set_style

MCP tool: `node_set_style`. Flags: undo step, apply-allowed.

Set, merge, clear, or propagate a passive node's visual style (or apply a saved preset).

style merges into the current style unless replace=true; clear=true removes the override; propagate=true copies the node's style to the passive nodes connected to it by edges (result propagated_to lists them). Non-passive nodes return NOT_PASSIVE; keys come from catalog.style_schema.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `style` | `object` | no |  | Passive node style override (persisted keys; see catalog.style_schema for enums and aliases) |
| `preset` | `string` | no |  | Saved node preset id or name (see catalog.style_schema) |
| `replace` | `boolean` | no | `false` |  |
| `clear` | `boolean` | no | `false` |  |
| `propagate` | `boolean` | no | `false` |  |

Result keys: `node_id`, `visual_style`, `propagated_to`.

#### node.fit_text

MCP tool: `node_fit_text`. Flags: undo step, deferred.

Set a flowchart shape's text fit (clip, grow, shrink) and report how its body text fits once drawn.

Every flowchart shape except timestamp stores the mode in properties.body_fit. clip keeps the size and ends clipped text in an ellipsis; grow enlarges the shape until the body fits (square shapes such as connector keep their aspect ratio); shrink lowers the font, to 6 px at the smallest, until it fits. The canvas measures the text, so the shape must be drawn: the op waits up to timeout_s for that (frame an off-screen shape with view.set_camera first) and applies the mode and any growth as one undo step. Omit mode to only report the current fit. A still-true overflowing means the text cannot fit this way: shorten it, widen the shape, or pick another mode.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `mode` | `string` | no |  | Text fit mode; omit to only report; one of: clip, grow, shrink |
| `timeout_s` | `number` | no | `5` | Seconds to wait for the canvas to draw the shape; >= 0 and \<= 120 |

Result keys: `node_id`, `changed`, `node`, `text_fit`.

Example:

```json
{
  "node_id": "node_12",
  "mode": "grow"
}
```

#### node.delete

MCP tool: `node_delete`. Flags: undo step, apply-allowed.

Delete one or more nodes (and their edges) from the active workspace.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | yes |  | Node ids to delete; min 1 item(s) |

Result keys: `deleted_node_ids`, `removed_edge_ids`.

#### node.duplicate

MCP tool: `node_duplicate`. Flags: undo step, apply-allowed.

Duplicate a set of nodes (with internal edges) offset from the originals.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | yes |  | Node ids to duplicate together; min 1 item(s) |
| `offset_x` | `number` | no | `40` |  |
| `offset_y` | `number` | no | `40` |  |

Result keys: `node_ids`, `id_map`.

### edge

#### edge.connect

MCP tool: `edge_connect`. Flags: undo step, apply-allowed.

Connect two ports. Passive flow ports are top|right|bottom|left; data ports use their spec keys.

replace_existing=false (default) appends to inputs that allow multiple connections and returns PORT_INCOMPATIBLE when the target is already occupied and single-valued; replace_existing=true rewires and reports replaced_edge_ids.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `source_node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `source_port` | `string` | yes |  | Port key; passive flow nodes use top\|right\|bottom\|left; non-empty |
| `target_node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `target_port` | `string` | yes |  | Port key; passive flow nodes use top\|right\|bottom\|left; non-empty |
| `replace_existing` | `boolean` | no | `false` |  |
| `label` | `string` | no |  | Optional flow edge label |
| `style` | `object` | no |  | Flow edge style override (persisted keys; see catalog.style_schema for aliases) |

Result keys: `edge_id`, `edge`, `replaced_edge_ids`.

Example:

```json
{
  "source_node_id": "$start",
  "source_port": "right",
  "target_node_id": "$mesh",
  "target_port": "left"
}
```

#### edge.update

MCP tool: `edge_update`. Flags: undo step, apply-allowed.

Update an edge's label, style, path mode, enabled flag, or display mode; optionally clear label/style or reverse its direction.

label may span lines (\n). reverse=true swaps source and target in the same undo step, keeping the edge id, label, and style; it needs ports that accept both directions (passive flowchart ports) and returns PORT_INCOMPATIBLE otherwise.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `edge_id` | `string` | yes |  | Edge id (edge_...); non-empty |
| `label` | `string` | no |  | Flow edge label; newlines make multi-line labels |
| `style` | `object` | no |  | Flow edge style override (persisted keys; see catalog.style_schema for aliases) |
| `path_mode` | `string` | no |  | one of: auto, pipe, bezier |
| `enabled` | `boolean` | no |  |  |
| `display_mode` | `string` | no |  | one of: default, faint, hidden |
| `reverse` | `boolean` | no | `false` | Swap source and target (flip the direction) |
| `clear_style` | `boolean` | no | `false` |  |
| `clear_label` | `boolean` | no | `false` |  |

Result keys: `edge_id`, `changed`, `edge`.

#### edge.delete

MCP tool: `edge_delete`. Flags: undo step, apply-allowed.

Delete one or more edges.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `edge_ids` | `array<string>` | yes |  | Edge ids to delete; min 1 item(s) |

Result keys: `deleted_edge_ids`.

### structure

#### group.wrap

MCP tool: `group_wrap`. Flags: undo step, apply-allowed.

Wrap nodes in a Group backdrop (passive.annotation.group_backdrop) with an optional title.

An expanded Group owns the nodes inside its area (moving a node in or out changes membership); a collapsed Group keeps exactly the members it had when it was collapsed, nodes placed over its hidden area stay outside it, and expanding it makes room around it. The backdrop is sized around the given nodes; moving it (node_update x/y, or a canvas drag) moves them, nested Groups included. Hidden nodes cannot be wrapped.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | yes |  | Nodes to wrap; min 1 item(s) |
| `title` | `string` | no |  | Node title shown in the header |

Result keys: `group_node_id`, `member_node_ids`.

#### subnode.create

MCP tool: `subnode_create`. Flags: undo step, apply-allowed.

Collapse nodes into a subnode shell (nested scope); boundary edges become input/output pins.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | yes |  | Nodes to move into the new subnode; min 1 item(s) |
| `title` | `string` | no |  | Node title shown in the header |

Result keys: `shell_node_id`, `input_pin_ids`, `output_pin_ids`, `member_node_ids`.

#### subnode.ungroup

MCP tool: `subnode_ungroup`. Flags: undo step, apply-allowed.

Dissolve a subnode shell, restoring its members to the current scope.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `shell_node_id` | `string` | yes |  | Node id (node_...); non-empty |

Result keys: `restored_node_ids`.

#### subnode.add_pin

MCP tool: `subnode_add_pin`. Flags: undo step, apply-allowed.

Add an input or output pin to a subnode shell.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `shell_node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `direction` | `string` | yes |  | one of: in, out |

Result keys: `pin_node_id`.

#### scope.navigate

MCP tool: `scope_navigate`. Flags: read-only, apply-allowed.

Open a subnode scope (target=node), go up one level (parent), or return to the root scope.

Graph ops act on the open scope; navigate before adding nodes inside a subnode.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `target` | `string` | yes |  | one of: root, parent, node |
| `node_id` | `string` | no |  | Subnode shell id when target=node |

Result keys: `scope_path`.

#### selection.set

MCP tool: `selection_set`. Flags: read-only, apply-allowed.

Replace, extend, or clear the canvas selection.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | no |  | Nodes to select (ignored for mode=clear) |
| `mode` | `string` | no | `"replace"` | one of: replace, add, clear |

Result keys: `selected_node_ids`.

#### layout.arrange

MCP tool: `layout_arrange`. Flags: undo step, apply-allowed.

Align, distribute, or match the size of a set of nodes (align left/right/top/bottom/center_x/center_y, distribute horizontal/vertical, match_width/match_height).

align_left/right/top/bottom line nodes up with the outermost edge; align_center_y gives every node the vertical center of their combined bounds (a row whose side ports line up), align_center_x the horizontal center (a centered column). distribute_\* needs 3+ nodes and keeps the outer two in place. match_width/match_height resize passive nodes of the same type_id to the first listed node of that type. snap_to_grid applies to align_left/right/top/bottom and distribute_\* only. Locked nodes (unless the 'interact with locked objects' preference is on), members of a collapsed Group, and nodes outside an open comment peek are left alone and listed in skipped_nodes. Results list moved/resized ids and overlapping_node_pairs so you can distribute or nudge afterwards.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | yes |  | Two or more nodes; min 2 item(s) |
| `action` | `string` | yes |  | one of: align_left, align_right, align_top, align_bottom, align_center_x, align_center_y, distribute_horizontal, distribute_vertical, match_width, match_height |
| `snap_to_grid` | `boolean` | no | `false` |  |

Result keys: `moved_node_ids`, `resized_node_ids`, `skipped_nodes`, `overlapping_node_pairs`.

#### layout.straighten

MCP tool: `layout_straighten`. Flags: undo step, apply-allowed.

Move nodes so the wires between them run straight (the Straighten Connections action).

Omit node_ids and edge_ids to straighten every wire in the open scope; edge_ids add their endpoint nodes. A wire can be straightened when both ends sit on horizontal sides (right->left) or both on vertical sides (bottom->top). Only the given nodes move. Each connected set of wires is solved per axis and re-centred on its median offset so it does not drift; a set whose wires need contradictory offsets is not moved on that axis. Read straightened_edge_ids and skipped_edges: mixed_port_sides = an elbow such as right->top; unresolved_offset = the ends still differ by offset px (contradictory wires in the set, or a data-node port drawn away from its layout anchor); locked_node / hidden_in_collapsed_group / not_selectable = an end the scene would not move. Check overlapping_node_pairs in case straightening stacked nodes.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | no |  | Nodes whose wires to straighten (default: every node in the open scope); min 1 item(s) |
| `edge_ids` | `array<string>` | no |  | Wires to straighten; their endpoint nodes join node_ids; min 1 item(s) |

Result keys: `moved_node_ids`, `straightened_edge_ids`, `skipped_edges`, `overlapping_node_pairs`.

#### layout.tidy

MCP tool: `layout_tidy`. Flags: undo step, apply-allowed.

Tidy nodes: auto-layout from the wires (left to right / top to bottom) or clean up in place, keeping Group backdrops intact.

Omit node_ids to tidy every node in the open scope. auto_layout rebuilds the arrangement from the wires (direction auto-detected from the port sides they use, or forced with left_to_right / top_to_bottom): rows and columns are centered so right->left and bottom->top wires run straight, loop-back wires stay elbows (loop_edge_ids), and the block keeps its current top-left; in_place keeps the arrangement and snaps near-aligned rows and columns onto shared center lines with even gaps. Group backdrops stay intact: a listed backdrop's members are laid out inside it and the backdrop is refitted, a collapsed Group moves as one block with its hidden members and is laid out at its collapsed size at every level, and an unlisted backdrop grows to keep listed members; when the result would still move a node into or out of a Group nothing changes and the call fails with NO_EFFECT (details.membership_conflict_node_ids). Locked nodes (unless the 'interact with locked objects' preference is on), members of a collapsed Group, nodes outside an open comment peek, Groups that hold a locked node (with their contents), and nodes whose locked Group would have to grow are left alone and listed in skipped_nodes (the last two as locked_group); the new block steps around locked nodes and those Groups, and unwired annotations are never re-arranged. Other nodes the new block would overlap are pushed aside (pushed_node_ids) while the 'Avoid overlaps when expanding collapsed items' graphics setting is on (the default). Read straightened_edge_ids, skipped_edges, and overlapping_node_pairs afterwards; changed=false means the nodes were already tidy.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_ids` | `array<string>` | no |  | Nodes to tidy (default: every node in the open scope); min 2 item(s) |
| `mode` | `string` | no | `"auto_layout"` | auto_layout rebuilds the arrangement from the wires; in_place keeps it and straightens rows and columns; one of: auto_layout, in_place |
| `direction` | `string` | no | `"auto"` | Flow direction for auto_layout; auto detects it from the port sides the wires use (in_place ignores it); one of: auto, left_to_right, top_to_bottom |
| `column_gap` | `number` | no | `96` | Gap in px between steps along the flow (in_place: between columns, the median current gap clamped to 1x..3x this value); >= 24 and \<= 400 |
| `row_gap` | `number` | no | `64` | Gap in px between rows across the flow (in_place: between rows, the median current gap clamped to 1x..3x this value); >= 16 and \<= 400 |

Result keys: `moved_node_ids`, `resized_group_ids`, `pushed_node_ids`, `skipped_nodes`, `loop_edge_ids`, `membership_conflict_node_ids`, `straightened_edge_ids`, `skipped_edges`, `overlapping_node_pairs`, `direction`, `mode`.

### annotations

#### comment.upsert

MCP tool: `comment_upsert`. Flags: undo step, apply-allowed.

Add or edit a comment on a node (threaded via parent_id; resolved/pinned flags).

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `body` | `string` | yes |  | Comment text (markdown); non-empty |
| `comment_id` | `string` | no |  | Existing comment id to edit; omit to create |
| `author` | `string` | no |  | Author label; new comments default to 'automation', edits keep the stored author |
| `parent_id` | `string` | no |  | Parent comment id for replies (must exist on the same node; fixed once set) |
| `resolved` | `boolean` | no |  | New comments default to false; omit on edit to keep the current value |
| `pinned` | `boolean` | no |  | New comments default to false; omit on edit to keep the current value |

Result keys: `comment_id`, `comment`.

#### comment.remove

MCP tool: `comment_remove`. Flags: undo step, apply-allowed.

Remove a comment from a node.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `comment_id` | `string` | yes |  | non-empty |

Result keys: `removed`.

#### link.upsert

MCP tool: `link_upsert`. Flags: undo step, apply-allowed.

Add or edit a link on a node: url, file, folder, workspace, or node targets; optional ordering position.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `kind` | `string` | yes |  | one of: url, file, folder, workspace, node |
| `title` | `string` | yes |  | non-empty |
| `target` | `string` | no |  | URL / path / workspace id / node id depending on kind |
| `link_id` | `string` | no |  | Existing link id to edit; omit to create |
| `subtitle` | `string` | no |  |  |
| `target_workspace_id` | `string` | no |  | For kind=node: the workspace that owns target_node_id |
| `target_node_id` | `string` | no |  | For kind=node |
| `position` | `integer` | no |  | Zero-based index in the node's link list; >= 0 |

Result keys: `link_id`, `link`.

#### link.remove

MCP tool: `link_remove`. Flags: undo step, apply-allowed.

Remove a link from a node.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `node_id` | `string` | yes |  | Node id (node_...); non-empty |
| `link_id` | `string` | yes |  | non-empty |

Result keys: `removed`.

### workspace

#### workspace.list

MCP tool: `workspace_list`. Flags: read-only.

List workspaces (tabs) with their views, dirty flags, and which one is active.

No parameters.

Result keys: `workspaces`, `active_workspace_id`.

#### workspace.create

MCP tool: `workspace_create`. Flags: read-only.

Create a new workspace tab (optionally duplicating an existing one) and activate it by default.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `name` | `string` | no |  | Tab name; defaults to Workspace N |
| `duplicate_of` | `string` | no |  | Workspace id to duplicate |
| `activate` | `boolean` | no | `true` |  |

Result keys: `workspace_id`, `name`.

#### workspace.update

MCP tool: `workspace_update`. Flags: read-only.

Rename a workspace and/or make it the active tab.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `workspace_id` | `string` | yes |  | Workspace id (ws_...); non-empty |
| `name` | `string` | no |  |  |
| `activate` | `boolean` | no |  |  |

Result keys: `workspace_id`, `changed`.

#### workspace.close

MCP tool: `workspace_close`. Flags: read-only.

Close a workspace tab (PROJECT_DIRTY unless discard_unsaved=true; LAST_WORKSPACE if it is the only one).

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `workspace_id` | `string` | yes |  | Workspace id (ws_...); non-empty |
| `discard_unsaved` | `boolean` | no | `false` |  |

Result keys: `closed`, `active_workspace_id`.

#### view.create

MCP tool: `view_create`. Flags: read-only.

Create a new camera view in the active workspace (copies the current camera) and activate it.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `name` | `string` | no |  |  |
| `activate` | `boolean` | no | `true` |  |

Result keys: `view_id`, `name`.

#### view.update

MCP tool: `view_update`. Flags: read-only.

Rename a view and/or switch to it.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `view_id` | `string` | yes |  | View id (view_...); non-empty |
| `name` | `string` | no |  |  |
| `activate` | `boolean` | no |  |  |

Result keys: `view_id`, `changed`.

#### view.close

MCP tool: `view_close`. Flags: read-only.

Close a view (LAST_VIEW when it is the only one).

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `view_id` | `string` | yes |  | View id (view_...); non-empty |

Result keys: `closed`, `active_view_id`.

#### view.set_camera

MCP tool: `view_set_camera`. Flags: read-only.

Set zoom/center explicitly or frame all nodes, the selection, or specific nodes.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `zoom` | `number` | no |  | 0.1 to 5.0; >= 0.1 and \<= 5.0 |
| `center_x` | `number` | no |  |  |
| `center_y` | `number` | no |  |  |
| `frame` | `string` | no |  | one of: all, selection, nodes |
| `node_ids` | `array<string>` | no |  | Nodes to frame when frame=nodes |

Result keys: `zoom`, `center_x`, `center_y`.

### project

#### project.open

MCP tool: `project_open`. Flags: read-only.

Open a .cxproj (path) or start a new blank project (new=true); refuses PROJECT_DIRTY unless discard_unsaved.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `path` | `string` | no |  | Absolute .cxproj path |
| `new` | `boolean` | no | `false` | Start a blank project instead of opening a file |
| `discard_unsaved` | `boolean` | no | `false` |  |

Result keys: `project_path`, `workspace_ids`, `active_workspace_id`.

#### project.save

MCP tool: `project_save`. Flags: read-only.

Save the project; pass path to Save As. Staged node files are published into the .data folder.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `path` | `string` | no |  | Target .cxproj path for Save As; omit to save in place |

Result keys: `project_path`, `status`, `reason_code`.

#### project.stage_file

MCP tool: `project_stage_file`. Flags: read-only.

Copy a local file (or write bytes) into the project's staging area and return its artifact ref.

Use for media/web assets you want the project to own; refs look like temp://... until saved.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `path` | `string` | no |  | Local file to copy |
| `content_base64` | `string` | no |  | Alternative to path: file bytes |
| `filename` | `string` | no |  | Required with content_base64 |
| `subdirectory` | `string` | no | `"automation"` |  |
| `node_id` | `string` | no |  | Owning node for provenance |

Result keys: `artifact_ref`, `staged_path`.

### run

#### run.start

MCP tool: `run_start`. Flags: read-only, deferred.

Run the active workspace or a set of nodes; optionally wait for completion (wait=true).

RUN_ACTIVE if a run is already in flight. Passive-only graphs complete immediately.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `scope` | `string` | no | `"workspace"` | one of: workspace, nodes |
| `node_ids` | `array<string>` | no |  | Required when scope=nodes |
| `wait` | `boolean` | no | `false` |  |
| `timeout_s` | `number` | no | `120` | >= 0 and \<= 3600 |
| `log_tail` | `integer` | no | `20` | >= 0 and \<= 500 |

Result keys: `idle`, `engine_state`, `active_run_id`, `outcome`, `started`, `running_node_ids`, `completed_node_ids`, `failed_node_ids`, `blocked_node_ids`, `root_errors`, `log_tail`, `waited_s`, `timed_out`.

#### run.status

MCP tool: `run_status`. Flags: read-only, deferred.

Report run state and per-node outcomes; wait=true blocks until idle or timeout.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `wait` | `boolean` | no | `false` |  |
| `timeout_s` | `number` | no | `120` | >= 0 and \<= 3600 |
| `log_tail` | `integer` | no | `20` | >= 0 and \<= 500 |

Result keys: `idle`, `engine_state`, `active_run_id`, `outcome`, `started`, `running_node_ids`, `completed_node_ids`, `failed_node_ids`, `blocked_node_ids`, `root_errors`, `log_tail`, `waited_s`, `timed_out`.

#### run.control

MCP tool: `run_control`. Flags: read-only.

Stop, pause, or resume the active run.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `action` | `string` | yes |  | one of: stop, pause, resume |

Result keys: `applied`, `engine_state`.

### capture

#### capture.screenshot

MCP tool: `capture_screenshot`. Flags: read-only.

Render canvas views (content-cropped PNGs) or grab the whole window; returns paths and inline PNGs.

mode=views uses the canvas export pipeline (node shadows are disabled during the grab so passive bodies render offscreen). Web panels and 3D viewers are blank in offscreen (private headless) instances; the result reports fidelity=offscreen_layout or native.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `mode` | `string` | no | `"views"` | one of: views, window |
| `view_ids` | `array<string>` | no |  | Views to render; defaults to the active view |
| `scale` | `integer` | no | `1` | >= 1 and \<= 4 |
| `crop_to_content` | `boolean` | no | `true` |  |
| `output_dir` | `string` | no |  | Directory for PNG files. Default: a temp folder; for a spawned instance, inside its session folder, which its launcher deletes on close. Pass output_dir to keep files |
| `filename_stem` | `string` | no |  | Optional file stem for mode=window |
| `inline` | `boolean` | no | `true` | Include png_base64 in the result |

Result keys: `images`, `mode`, `fidelity`.

### apply

#### graph.apply

MCP tool: `graph_apply`. Flags: undo step.

Apply up to 500 graph ops as ONE undo step; later ops reference earlier results with $id (or $id.field).

All ops are validated before anything mutates (unknown op names -> UNKNOWN_OP; every other static problem -> one INVALID_PARAMS listing ops[i].\<path> entries). $ref tokens are only resolved in each op's declared ref_fields (never inside markdown or titles); $id is the earlier op's primary id, $id.field / $id.list.0 read nested result fields; write $$ for a literal dollar. atomic=true (default): the first failing op restores the pre-batch workspace snapshot, scope and selection, no undo entry is recorded, and the call raises APPLY_FAILED (details: failed_index, failed_op, error, rolled_back=true, results so far). atomic=false: earlier ops are kept as one undo step and the call returns ok with failed_index >= 0 and the failing row's error in results; it still raises APPLY_FAILED when the very first op fails. The batch runs in the active workspace and the open scope; scope.navigate inside a batch changes the scope for later ops. Staged files and artifact-folder renames do not roll back.

| Param | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ops` | `array<object>` | yes |  | min 1 item(s); max 500 item(s) |
| `atomic` | `boolean` | no | `true` |  |
| `label` | `string` | no |  | Undo history label |

Result keys: `results`, `applied`, `failed_index`, `rolled_back`, `ids`.

Example:

```json
{
  "ops": [
    {
      "id": "start",
      "op": "node.add",
      "params": {
        "type_id": "passive.flowchart.start",
        "x": 0,
        "y": 0,
        "title": "Start"
      }
    },
    {
      "id": "step",
      "op": "node.add",
      "params": {
        "type_id": "passive.flowchart.process",
        "x": 320,
        "y": 0,
        "title": "Mesh"
      }
    },
    {
      "op": "edge.connect",
      "params": {
        "source_node_id": "$start",
        "source_port": "right",
        "target_node_id": "$step",
        "target_port": "left"
      }
    }
  ],
  "label": "Build flowchart"
}
```

### Error codes

| Code | Retryable | Default hint |
| --- | --- | --- |
| `INVALID_PARAMS` | no | Fix the listed parameter problems and resend the request. |
| `UNKNOWN_OP` | no | Read the corex://ops resource (or catalog docs) to list valid operation names. |
| `NOT_FOUND` | no | Refresh ids with graph.get or workspace.list; the id no longer exists in the active workspace. |
| `UNKNOWN_NODE_TYPE` | no | Use catalog.list_node_types (or the suggestions in details) to pick a valid type_id. |
| `WRONG_SCOPE` | no | Navigate with scope.navigate to the scope that owns the node, then retry. |
| `WRONG_WORKSPACE` | no | Activate the owning workspace with workspace.update(activate=true), then retry. |
| `PORT_INCOMPATIBLE` | no | Inspect both nodes with graph.get_node and choose compatible ports (kind and data type). |
| `NOT_PASSIVE` | no | This op only applies to passive nodes (flowchart, annotation, media); use node.update for others. |
| `PROPERTY_LOCKED_BY_PORT` | no | Disconnect or unexpose the port that drives this property before editing it. |
| `NO_EFFECT` | no | The owner rejected or ignored the change; check the details and current node state. |
| `PROJECT_DIRTY` | no | Save with project.save or pass discard_unsaved=true to proceed without saving. |
| `LAST_WORKSPACE` | no | Create another workspace first; the last workspace cannot be closed. |
| `LAST_VIEW` | no | Create another view first; the last view cannot be closed. |
| `SAVE_FAILED` | no | Check the path is writable and ends with .cxproj, then retry project.save. |
| `OPEN_FAILED` | no | Check the path exists and is a readable .cxproj, then retry project.open. |
| `CAPTURE_FAILED` | no | Ensure the canvas has content and the app is idle, then retry capture.screenshot. |
| `RUN_ACTIVE` | no | A run (or the auto-run your edits queued) is in flight: wait with run.status(wait=true) or stop it with run.control(stop), then start again. |
| `TIMEOUT` | yes | Retry with a larger timeout_s, or poll run.status without wait. |
| `APPLY_FAILED` | no | Fix the failing op in the batch; atomic batches were rolled back. |
| `APP_BUSY` | yes | The app is saving or loading a project; retry shortly. |
| `APP_BUSY_MODAL` | yes | A dialog is open in the COREX window; ask the user to close it, then retry. |
| `APP_SHUTTING_DOWN` | no | COREX is closing; reconnect to another instance or relaunch. |
| `UNEXPECTED_DIALOG` | no | An unexpected dialog appeared and was dismissed; inspect the app state before retrying. |
| `NOT_IMPLEMENTED` | no | This op is declared but not implemented in this build. |
| `INTERNAL` | no | Report the details; retry once after checking app state. |
| `AUTH_FAILED` | no | Reconnect using the token from the instance discovery file. |
| `PROTOCOL_ERROR` | no | Send one NDJSON object per line with id, op, and params. |
<!-- END GENERATED OP REFERENCE -->

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `APP_BUSY_MODAL` on every op | A dialog or popup is open in the COREX window (unsaved-changes prompt, file dialog, style editor). | Close it (or ask the user to), then retry; the error is retryable. Use `corex_status.busy` to check first. |
| `NOT_FOUND: No live COREX automation instance` | Nothing is running with `--automation`, or its discovery file was cleaned up because the process died. | Start COREX with `--automation`, or use `--mode private` / `CorexClient.launch("private")`. With `--instance-id`, make sure the id matches the discovery file name. |
| Launch fails with `INTERNAL` and a log tail mentioning the port | `--automation-port` is already in use, or another COREX holds it. | Pick another port or `0` (ephemeral); read `details.log_path`. |
| Launch fails with `TIMEOUT` | The instance did not publish a reachable port within `startup_timeout_s` (default 90 s), often a slow first import. | Raise `startup_timeout_s`, inspect `details.log_tail`, check the venv interpreter. |
| Offscreen screenshots show boxes instead of text | Qt offscreen cannot find fonts. | Set `QT_QPA_FONTDIR` (the launcher sets `C:\Windows\Fonts` on Windows) or use `--no-headless`. |
| Offscreen screenshots show empty web / 3D panels | `fidelity=offscreen_layout`: those surfaces are not rendered offscreen. | Use `private` with `headless=False`, or attach to a visible instance. |
| `Popen.pid` differs from `corex_status.pid` on Windows | `bootstrap` re-execs into the venv interpreter, so the child pid changes. | Expected. The launcher sets `EA_NODE_EDITOR_BOOTSTRAPPED=1` and matches instances by `instance_id`, never by pid. Attach by `instance_id` when several instances run. |
| `NOT_IMPLEMENTED` | The op is declared in the catalog but this build has no handler for it. | Update the checkout; the guide's op reference lists what the catalog declares. |
| `timed_out=true` from `run.start(wait=true)` or `run.status(wait=true)` | The run outlasted `timeout_s`; the call returns the current status instead of failing. | Poll `run.status` again, or raise `timeout_s` (the client waits `timeout_s` plus a margin). |
| `APP_SHUTTING_DOWN` / connection lost | COREX closed or the socket dropped. | Reconnect with `CorexClient.connect()` or launch a new instance; the old client stays disconnected. |
| `PROJECT_DIRTY` on `project.open` / `workspace.close` / `app.quit` | Unsaved changes. | Save first (`project.save`) or pass `discard_unsaved=true` deliberately. |
| Private instance keeps running after a crash | The script exited without `close()`. | Always use `with CorexClient.launch(...) as corex:`; stray instances vanish from discovery when their process exits, and their temp session dirs live under the system temp folder (`corex-automation-*`). |
