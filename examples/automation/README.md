# COREX Automation Examples

Four runnable scripts that drive COREX through the automation API with only
`ea_node_editor.automation.client.CorexClient` and the standard library. The
walkthroughs and every op they use are explained in the
[Automation API Guide](../../docs/AUTOMATION_API_GUIDE.md#walkthroughs).

| Script | What it builds | Artifacts |
| --- | --- | --- |
| [flowchart.py](flowchart.py) | Ten-node engineering flowchart (Start, Import CAD, Clean geometry, Mesh, Solve, Converged?, Export results, Archive to PDM, End, Refine mesh) in one `graph.apply` batch with `$refs`, styled yes/no branches, labelled edges | `flowchart.cxproj`, canvas PNG |
| [annotated_media_board.py](annotated_media_board.py) | Markdown text node, media panel of a generated PNG, path pointer, panel, all wrapped in a titled group; threaded comments and a URL link | `mesh_preview.png`, `annotated_media_board.cxproj`, canvas PNG |
| [subnode_workflow.py](subnode_workflow.py) | Five-step chain, two steps collapsed into a subnode with a spare output pin, a node added inside the subnode scope, one undo and one redo | PNGs of the subnode scope and the root scope |
| [run_and_screenshot.py](run_and_screenshot.py) | `core.constant` wired to `core.logger` (port keys checked with `catalog.describe_node_type`), run with `run.start(wait=true)`, status and log tail printed | canvas PNG |

## Prerequisites

- The project venv with COREX installed: `.\venv\Scripts\python.exe -m pip install -e ".[all,dev]"`
  (the `[mcp]` extra is not needed for these scripts).
- No running COREX is needed for the default `--mode private`: the launcher
  spawns an isolated instance with its own session state and quits it when the
  script ends, also on failure.
- For `--mode attach`, start COREX first with
  `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap --automation`.

## Run

From the repository root:

```powershell
.\venv\Scripts\python.exe examples\automation\flowchart.py
.\venv\Scripts\python.exe examples\automation\annotated_media_board.py --output-dir C:\temp\corex-board
.\venv\Scripts\python.exe examples\automation\subnode_workflow.py --no-headless
.\venv\Scripts\python.exe examples\automation\run_and_screenshot.py --mode attach
```

Every script accepts:

| Option | Default | Meaning |
| --- | --- | --- |
| `--mode auto\|attach\|private` | `private` | Launch mode (see the guide's launch-mode table). |
| `--headless` / `--no-headless` | headless | Private instances render offscreen by default; `--no-headless` opens a real window for native fidelity (web and 3D panels render). |
| `--output-dir DIR` | new temp folder | Where projects and PNGs are written. |
| `--instance-id ID` | newest live | Attach to one specific discovery instance. |
| `--startup-timeout S` | `120` | Seconds to wait for a spawned instance. |

`run_and_screenshot.py` also takes `--run-timeout S` (default `90`).

Each script prints its artifact paths (`project: ...`, `screenshot_1: ...`,
`fidelity: ...`) and exits `0` on success. Any `AutomationOpError` is printed as
`FAILED <code>: <message>` with the hint and details, and the exit code is `1`.

## Attached instances

With `--mode attach`, or `auto` when a COREX is already running, the scripts
treat the instance as the user's: they build in a new workspace tab, never
replace or save the open project, and never quit the app. Only a private
instance the script spawned gets a fresh project and a Save As into
`--output-dir`.

## How integration runs use them

The integration task (T13) and the end-to-end automation test run each script
against a private headless instance and assert a zero exit code plus the
printed artifact files, for example:

```powershell
.\venv\Scripts\python.exe examples\automation\flowchart.py --mode private --output-dir artifacts\automation_examples\flowchart
```

Offscreen screenshots report `fidelity: offscreen_layout`; they prove layout,
titles, edges, and styles, not pixel-exact native rendering.
`tests/automation/test_docgen.py` keeps the scripts compiling and checks that
each exposes `--mode`.
