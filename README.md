# EA Node Editor

A visual node editor for building engineering dataflow pipelines. Connect nodes to
read/write files, run calculations, monitor HPC cluster jobs, and automate
multi-step engineering workflows -- all through a drag-and-drop canvas.

## Quick Start

```bash
# 1. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install the project and its dependencies
pip install -e ".[all,dev]"

# 3. Run the application
python main.py
```

## Project Structure

```
ea_node_editor/
  app.py                  # Application entry point
  settings.py             # Paths, defaults, autosave interval

  graph/                  # Graph domain model + graph rules
    model.py              # ProjectData, WorkspaceData, NodeInstance, EdgeInstance
    rules.py              # Canonical port/data compatibility and exposure helpers

  nodes/                  # Node type system
    types.py              # PortSpec, PropertySpec, NodeTypeSpec, NodePlugin protocol
    registry.py           # Central registry of all available node types
    decorators.py         # @node_type, in_port, out_port, prop_* helpers
    bootstrap.py          # Registers built-in nodes at startup
    plugin_loader.py      # Discovers and loads user plugins from disk
    package_manager.py    # Import / export .eanp node packages
    builtins/
      core.py             # Start, End, Constant, Logger, Python Script
      integrations.py     # Compatibility facade (re-exports integration plugins)
      integrations_spreadsheet.py
      integrations_file_io.py
      integrations_email.py
      integrations_process.py
      hpc.py              # HPC Submit, Monitor, On Status, Fetch Results

  execution/              # Workflow run engine
    protocol.py           # Typed event/command protocol + queue adapters
    worker.py             # Runs the workflow in a separate process
    client.py             # UI-side client that talks to the worker process

  persistence/
    serializer.py         # Backward-compatible facade for load/save/to/from/migrate
    migration.py          # Schema migration + normalization
    project_codec.py      # ProjectData <-> document codec
    session_store.py      # Session/autosave storage + recovery helpers

  ui/                     # User interface shell orchestration
    shell/
      window.py           # ShellWindow (QMainWindow host + orchestration)
      project_flow.py     # Project/session helpers (merge/defaults/fingerprints/persistence)
      run_flow.py         # Run lifecycle helpers (event scoping + action-state derivation)
      workspace_flow.py   # Workspace/view tab helpers
      inspector_flow.py   # Inspector property coercion helpers
      library_flow.py     # Library drop/autowire helper selection
    graph_interactions.py # Connect, delete, rename operations
    dialogs/              # Workflow settings dialog
    theme/                # Dark theme tokens and stylesheets
    editor/               # Code editor widget

  ui_qml/                 # QML shell + bridge/state models
    graph_scene_bridge.py # GraphSceneBridge (nodes/edges/selection)
    viewport_bridge.py    # ViewportBridge (zoom/pan/camera)
    edge_routing.py       # Edge geometry and payload routing helpers
    console_model.py
    script_editor_model.py
    status_model.py
    workspace_tabs_model.py
  workspace/              # Workspace ordering and lifecycle
  telemetry/              # CPU/RAM metrics, performance harness

tests/                    # Unit and integration tests
docs/specs/               # Requirements, ADRs, work packets
```

## Creating a Custom Node

Drop a Python file into the plugins folder (`~/.ea_node_editor/plugins/` on
Windows that is `%APPDATA%/EA_Node_Editor/plugins/`). The file should define one
or more classes that follow the `NodePlugin` protocol:

```python
from ea_node_editor.nodes import node_type, in_port, out_port, prop_float
from ea_node_editor.nodes.types import ExecutionContext, NodeResult

@node_type(
    type_id="custom.multiply",
    display_name="Multiply",
    category="Math",
    icon="calculate",
    ports=(
        in_port("a", data_type="float"),
        in_port("b", data_type="float"),
        out_port("result", data_type="float"),
    ),
    properties=(
        prop_float("factor", 1.0, "Scale Factor"),
    ),
    description="Multiplies two numbers and applies a scale factor.",
)
class MultiplyNode:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        a = float(ctx.inputs.get("a", 0))
        b = float(ctx.inputs.get("b", 0))
        factor = float(ctx.properties.get("factor", 1.0))
        return NodeResult(outputs={"result": a * b * factor})
```

Restart the application and the node will appear in the Node Library under the
"Math" category.

## Sharing Node Packages

- **Export:** File > Export Node Package -- bundles selected nodes into a `.eanp` file
- **Import:** File > Import Node Package -- installs a `.eanp` file into your plugins folder

## Running Tests

```bash
python -m pytest tests/ -v
```

## Building a Windows Installer

See [docs/PACKAGING_WINDOWS.md](docs/PACKAGING_WINDOWS.md) for PyInstaller
packaging, installer creation, and code signing instructions.

## Documentation

- [Spec Pack Index](docs/specs/INDEX.md) -- requirements, ADRs, traceability
- [Release Notes](RELEASE_NOTES.md) -- shipped capabilities and known risks
- [Pilot Runbook](docs/PILOT_RUNBOOK.md) -- validation steps for pilot deployments
