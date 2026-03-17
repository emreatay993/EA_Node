# Getting Started

This guide is the fastest way to get EA Node Editor running locally with the
current Windows-first workflow.

## Prerequisites

- Windows 10 or Windows 11
- Python 3.10 or newer
- Git
- Network access for `pip install` and optional architecture-diagram export

## Local Setup

From the repository root:

```bash
py -3.10 -m venv venv
./venv/Scripts/python.exe -m pip install --upgrade pip
./venv/Scripts/python.exe -m pip install -e ".[all,dev]"
```

Notes:

- `.[all,dev]` installs the optional spreadsheet/HPC dependencies plus the local dev tools used in this repo.
- The repo uses a Windows-style virtualenv layout even when opened from `bash`, so prefer `./venv/Scripts/python.exe` over a shell-default `python`.
- Editable install also exposes the `ea-node-editor` console entry point inside `venv/Scripts/`.

## First Launch

Start the application from the repository root:

```bash
./venv/Scripts/python.exe main.py
```

You should see:

- The QML main shell with library, canvas, inspector, workspace tabs, and console areas
- The default shell theme and graph theme resolved from `app_preferences.json`
- An empty workspace ready for either executable nodes or passive visual nodes

## Useful First Checks

Create a quick regression pass before doing larger changes:

```bash
QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest discover -s tests -v
```

If you only need the graph-surface gate:

```bash
QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest \
  tests.test_graph_surface_input_contract \
  tests.test_graph_surface_input_inline \
  tests.test_passive_graph_surface_host \
  tests.test_passive_image_nodes -v
```

Manual passive-media fixture:

- Open `tests/fixtures/passive_nodes/reference_flowchart.sfe` to check passive nodes, `flow` edges, and local image/PDF preview behavior.

## Common Paths

- User data directory: `%APPDATA%\EA_Node_Editor\`
- Plugin drop-in directory: `%APPDATA%\EA_Node_Editor\plugins\`
- App-wide graphics preferences: `%APPDATA%\EA_Node_Editor\app_preferences.json`
- Session state: `%APPDATA%\EA_Node_Editor\last_session.json`
- Autosave project: `%APPDATA%\EA_Node_Editor\autosave.sfe`

## Repo Orientation

- [README.md](../README.md): top-level feature summary, structure map, and doc links
- [ARCHITECTURE.md](../ARCHITECTURE.md): runtime architecture, QML composition, and Mermaid diagrams
- [docs/specs/INDEX.md](./specs/INDEX.md): canonical requirements, ADRs, and traceability
- [docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md](./specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md): short manual passive-node validation pass
- [docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md](./specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md): current graph-surface regression matrix and approved shell fallback

## Updating Architecture Diagrams

The generated architecture assets under `docs/architecture_diagrams/` come from
the Mermaid blocks in `ARCHITECTURE.md`.

Regenerate them with:

```bash
./venv/Scripts/python.exe scripts/export_architecture_diagrams.py
```

That exporter writes `.mmd`, `.svg`, and `.png` files and uses the Kroki
Mermaid rendering service, so it requires network access.
