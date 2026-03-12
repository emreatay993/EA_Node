# EA Node Editor

A visual node editor for building engineering dataflow pipelines. Connect nodes to
read/write files, run calculations, monitor HPC cluster jobs, and automate
multi-step engineering workflows -- all through a drag-and-drop canvas.

Recent UI/UX architecture highlights:

- Connection-aware quick insert from a dangling wire drag
- Inline node controls for fast editing of selected property types
- Python-side compatibility filtering so quick insert follows the same effective-port rules as graph connections

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

Core source layout (package `__init__.py` files omitted for brevity):

```text
ea_node_editor/
  app.py
  settings.py
  custom_workflows/
    codec.py
    file_codec.py
    global_store.py
  execution/
    client.py
    compiler.py
    protocol.py
    worker.py
  graph/
    effective_ports.py
    hierarchy.py
    model.py
    normalization.py
    rules.py
    transforms.py
  nodes/
    bootstrap.py
    decorators.py
    package_manager.py
    plugin_loader.py
    registry.py
    types.py
    builtins/
      core.py
      hpc.py
      integrations.py
      integrations_common.py
      integrations_email.py
      integrations_file_io.py
      integrations_process.py
      integrations_spreadsheet.py
      subnode.py
  persistence/
    migration.py
    project_codec.py
    serializer.py
    session_store.py
    utils.py
  telemetry/
    performance_harness.py
    system_metrics.py
  ui/
    graph_interactions.py
    dialogs/
      workflow_settings_dialog.py
    editor/
      code_editor.py
    shell/
      state.py
      run_flow.py
      workspace_flow.py
      inspector_flow.py
      library_flow.py
      runtime_history.py
      runtime_clipboard.py
      window.py
      window_actions.py
      window_library_inspector.py
      window_search_scope_state.py
      controllers/
        run_controller.py
        project_session_controller.py
        workspace_library_controller.py
        workspace_view_nav_ops.py
        workspace_edit_ops.py
        workspace_drop_connect_ops.py
        workspace_io_ops.py
        result.py
    theme/
      styles.py
      tokens.py
  ui_qml/
    MainShell.qml
    graph_scene_bridge.py
    viewport_bridge.py
    edge_routing.py
    console_model.py
    script_editor_model.py
    status_model.py
    syntax_bridge.py
    workspace_tabs_model.py
    components/
      GraphCanvas.qml
      graph/
        EdgeLayer.qml
        EdgeMath.js
        NodeCard.qml
      graph_canvas/
        GraphCanvasBackground.qml
        GraphCanvasContextMenus.qml
        GraphCanvasDropPreview.qml
        GraphCanvasInputLayers.qml
        GraphCanvasLogic.js
        GraphCanvasMinimapOverlay.qml
      shell/
        ConnectionQuickInsertOverlay.qml
        GraphHintOverlay.qml
        GraphSearchOverlay.qml
        InspectorPane.qml
        LibraryWorkflowContextPopup.qml
        MainShellUtils.js
        NodeLibraryPane.qml
        ScriptEditorOverlay.qml
        ShellButton.qml
        ShellRunToolbar.qml
        ShellStatusStrip.qml
        ShellTitleBar.qml
        WorkspaceCenterPane.qml
  workspace/
    manager.py

tests/
docs/specs/
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

## Interaction Notes

- Drag from a port to empty canvas space to open the connection-aware quick insert overlay.
- Quick insert only shows node types that can auto-connect to the dragged source port using the same compatibility rules as normal graph connections.
- Some node types expose inline property controls directly in the node card for faster editing, while the inspector remains the full editing surface.

## Building a Windows Installer

See [docs/PACKAGING_WINDOWS.md](docs/PACKAGING_WINDOWS.md) for PyInstaller
packaging, installer creation, and code signing instructions.

## Documentation

- [Architecture Guide](ARCHITECTURE.md) -- runtime/component architecture and flow maps
- [Architecture Diagrams](docs/architecture_diagrams/) -- generated Mermaid exports (`.mmd`, `.svg`, `.png`)
- [Spec Pack Index](docs/specs/INDEX.md) -- requirements, ADRs, traceability
- [Release Notes](RELEASE_NOTES.md) -- shipped capabilities and known risks
- [Pilot Runbook](docs/PILOT_RUNBOOK.md) -- validation steps for pilot deployments

Regenerate architecture diagrams after updating Mermaid blocks in `ARCHITECTURE.md`:

```bash
python3 scripts/export_architecture_diagrams.py
```
