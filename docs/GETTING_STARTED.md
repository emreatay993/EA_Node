# Getting Started

This guide is the fastest way to get COREX Node Editor running locally with the
current Windows-first workflow.

## Prerequisites

- Windows 10 or Windows 11
- Python 3.10 or newer
- Git
- Network access for `pip install` and optional architecture-diagram export

## Local Setup

From the repository root:

```powershell
py -3.10 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -e ".[all,dev]"
```

Notes:

- `.[all,dev]` installs the optional spreadsheet/HPC dependencies plus the local dev tools used in this repo.
- The repo uses a Windows-style virtualenv layout even when opened from `bash`, so prefer `./venv/Scripts/python.exe` over a shell-default `python`.
- The examples below use native PowerShell path syntax. If you are in `bash`, use the same interpreter path with `./venv/Scripts/python.exe`.
- Editable install also exposes the `corex-node-editor` console entry point inside `venv/Scripts/`.

## First Launch

Start the application from the repository root:

```powershell
.\venv\Scripts\python.exe .\main.py
```

You should see:

- The QML main shell with library, canvas, inspector, workspace tabs, and console areas
- The default shell theme and graph theme resolved from `app_preferences.json`
- An empty workspace ready for either executable nodes or passive visual nodes

## Useful First Checks

Create a quick regression pass before doing larger changes:

```powershell
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast
```

Before merge, inspect or run the full workflow:

```powershell
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full
```

- After editing packet-owned verification docs, perf reports, or traceability
  links, run `.\venv\Scripts\python.exe .\scripts\check_traceability.py` to audit
  the proof layer.
- After editing canonical markdown docs or spec-index links, run
  `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` to catch broken
  local references before handoff.
- The canonical script paths remain `scripts/check_traceability.py` and
  `scripts/check_markdown_links.py`; the PowerShell form simply prefixes them
  with `.\`.
- The current architecture/docs closeout evidence is summarized in
  `ARCHITECTURE.md`, `docs/specs/INDEX.md`,
  `docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md`,
  `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`, and
  `docs/specs/requirements/TRACEABILITY_MATRIX.md`.
- The runner applies `QT_QPA_PLATFORM=offscreen` to its child verification
  commands.
- Direct `.\venv\Scripts\python.exe -m pytest` now auto-parallelizes only the
  safe non-GUI path. Broad invocations default to the `not gui and not slow`
  slice, while focused GUI, slow, and shell-backed targets stay off that
  automatic parallel path to avoid Qt/QML RAM bloat.
- `fast` and the dedicated `full` shell-isolation phase use
  `-n <resolved_count> --dist load` when `pytest-xdist` is installed in the
  project venv, where `<resolved_count>` resolves as
  `psutil.cpu_count(logical=True)` when available, else `os.cpu_count()`,
  else `1`.
- `gui` uses the same resolution path, then caps the worker count at `6`
  before passing `-n <gui_resolved_count> --dist load` because the QML-heavy
  slice regresses when it over-saturates the host.
- When `pytest-xdist` is unavailable, all xdist-enabled phases fall back to
  serial pytest automatically and the runner prints the notice.
- `full` keeps the non-shell pytest phases first, then runs
  `tests/test_shell_isolation_phase.py` as the dedicated fresh-process
  shell-isolation phase; the target catalogs cover the shell-backed suites
  from `tests.test_main_window_shell`, `tests.test_script_editor_dock`,
  `tests.test_shell_run_controller`, and
  `tests.test_shell_project_session_controller`.
- The direct module-level shell `unittest` commands remain supported for
  focused manual reruns, but they are no longer the documented `full`
  workflow.
- The previously documented serializer spot-check
  `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q`
  now passes in the project venv, so the QA matrix no longer carries that
  caveat as an open out-of-scope baseline.

If you only need the graph-surface gate:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m unittest `
  tests.test_graph_surface_input_contract `
  tests.test_graph_surface_input_inline `
  tests.test_passive_graph_surface_host `
  tests.test_passive_image_nodes -v
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

Manual passive-media fixture:

- Open `tests/fixtures/passive_nodes/reference_flowchart.sfe` to check passive nodes, `flow` edges, and local image/PDF preview behavior.

## Common Paths

- User data directory: `%APPDATA%\COREX_Node_Editor\`
- Plugin directory root: `%APPDATA%\COREX_Node_Editor\plugins\`
- App-wide graphics preferences: `%APPDATA%\COREX_Node_Editor\app_preferences.json`
- Session state: `%APPDATA%\COREX_Node_Editor\last_session.json`
- Autosave project: `%APPDATA%\COREX_Node_Editor\autosave.sfe`

## Plugins and Node Packages

- Raw plugin drop-ins live directly under `%APPDATA%\COREX_Node_Editor\plugins\` as public `*.py` files. Files whose names start with `_` are ignored.
- For new plugin modules or installed packages, prefer `PLUGIN_DESCRIPTORS` so loader registration and package export can use descriptor provenance instead of constructor probing. Legacy class discovery remains supported for older plugins.
- Imported `.eanp` packages install as `%APPDATA%\COREX_Node_Editor\plugins\<package_name>\`. Each archive must contain `node_package.json` plus top-level `.py` files only; nested directories and non-Python payload files are rejected.
- File > Export Node Package only exports sources already loaded from the user plugins directory. The shell can package one public root `.py` drop-in or one installed package directory at a time; it does not build an archive from arbitrary node selections or built-in nodes.
- File > Import Node Package reloads user plugins after install. If the imported package replaces node types that were already loaded in the current session, restart the app before assuming the replacements took effect.

## Repo Orientation

- [README.md](../README.md): top-level feature summary, structure map, and doc links
- [ARCHITECTURE.md](../ARCHITECTURE.md): runtime architecture, QML composition, and Mermaid diagrams
- [docs/specs/INDEX.md](./specs/INDEX.md): canonical requirements, ADRs, and traceability
- [docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md](./specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md): final docs/release/manual-check matrix and archived-evidence boundaries
- [docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md](./specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md): short manual passive-node validation pass
- [docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md](./specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md): current graph-surface regression matrix and shell-module verification status
- [docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md](./specs/perf/VERIFICATION_SPEED_QA_MATRIX.md): approved verification-runner modes, dedicated shell-isolation phase, benchmark evidence, proof-audit command, and baseline-status notes
- `docs/specs/INDEX.md` lists the retained work-packet manifests, status ledgers, and closeout QA matrices that stay canonical on this branch.

## Updating Architecture Diagrams

The generated architecture assets under `docs/architecture_diagrams/` come from
the Mermaid blocks in `ARCHITECTURE.md`.

Regenerate them with:

```powershell
.\venv\Scripts\python.exe .\scripts\export_architecture_diagrams.py
```

That exporter writes `.mmd`, `.svg`, and `.png` files and uses the Kroki
Mermaid rendering service, so it requires network access.
