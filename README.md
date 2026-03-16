# EA Node Editor

A visual node editor for building engineering dataflow pipelines. Connect nodes to
read/write files, run calculations, monitor HPC cluster jobs, and automate
multi-step engineering workflows -- all through a drag-and-drop canvas.

Recent UI/UX architecture highlights:

- App-wide Graphics Settings modal for grid, minimap, snap-to-grid default, shell-theme selection, and graph-theme follow-shell or explicit selection
- Split shell/chrome theming (`ThemeBridge` + `stitch_dark` / `stitch_light`) from node/edge graph theming (`graphThemeBridge` + built-in/custom graph themes)
- Custom graph-theme library/editor with built-in read-only themes, custom duplication/CRUD, and live apply for the active explicit custom theme
- Graphics preferences now persist in `app_preferences.json` separately from project `.sfe` files and `last_session.json`
- Passive visual node families now ship in the main graph model for flowcharting, planning, annotation, and local image/PDF presentation
- Passive `flow` edges support labels and per-edge style overrides while remaining excluded from runtime compilation and worker execution
- Passive node and flow-edge style overrides can be edited from context menus and saved as project-local presets in `.sfe` metadata
- Connection-aware quick insert from a dangling wire drag
- Inline node controls for fast editing of selected property types
- Python-side compatibility filtering so quick insert follows the same effective-port rules as graph connections
- Inspector and script editing surfaces now use user-facing node labels and sequential IDs instead of exposing internal `node_*` references

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
      passive_annotation.py
      passive_flowchart.py
      passive_media.py
      passive_planning.py
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
    graph_theme/
      presentation.py
      registry.py
      runtime.py
      tokens.py
    dialogs/
      flow_edge_style_dialog.py
      graph_theme_editor_dialog.py
      graphics_settings_dialog.py
      passive_node_style_dialog.py
      passive_style_controls.py
      sectioned_settings_dialog.py
      workflow_settings_dialog.py
    editor/
      code_editor.py
    media_preview_provider.py
    passive_style_presets.py
    pdf_preview_provider.py
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
        app_preferences_controller.py
        run_controller.py
        project_session_controller.py
        workspace_library_controller.py
        workspace_view_nav_ops.py
        workspace_edit_ops.py
        workspace_drop_connect_ops.py
        workspace_io_ops.py
        result.py
    theme/
      registry.py
      styles.py
      tokens.py
  ui_qml/
    MainShell.qml
    graph_scene_bridge.py
    graph_theme_bridge.py
    viewport_bridge.py
    edge_routing.py
    console_model.py
    script_editor_model.py
    status_model.py
    syntax_bridge.py
    theme_bridge.py
    workspace_tabs_model.py
    components/
      GraphCanvas.qml
      graph/
        EdgeLayer.qml
        GraphNodeHost.qml
        GraphNodeSurfaceLoader.qml
        EdgeMath.js
        NodeCard.qml
        passive/
          GraphAnnotationNoteSurface.qml
          GraphFlowchartNodeSurface.qml
          GraphMediaPanelSurface.qml
          GraphPlanningCardSurface.qml
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

## Graphics Settings

- Open `Settings > Graphics Settings` to configure the grid overlay, minimap visibility/default expansion, snap-to-grid default, shell theme, graph-theme follow-shell behavior, and explicit graph-theme selection.
- Use `Manage Graph Themes...` to duplicate built-in graph themes into editable custom themes, edit node/edge/category-accent/port-kind tokens, and choose an explicit graph theme.
- Shell-theme changes apply live to QWidget styling and QML shell/canvas chrome surfaces. Node and edge visuals resolve through the active graph theme.
- Graph themes affect `NodeCard` and `EdgeLayer` only; background, grid, minimap, marquee, and drop-preview chrome stay on the shell theme path.
- App-wide graphics preferences, including the inline custom graph-theme library, persist in `%APPDATA%\EA_Node_Editor\app_preferences.json` and stay separate from project `.sfe` files and `last_session.json`.

## Passive Visual Authoring

- Passive flowchart, planning, annotation, image, and PDF nodes stay in the normal workspace graph and save into the same `.sfe` document as executable nodes.
- `flow` edges are presentation-only graph connections. They support labels, branch styling, and multi-incoming targets where the target port spec allows it, but they do not reach the compiler or worker runtime graph.
- Passive nodes render through the graph host/factory path, which keeps standard `NodeCard` contracts stable while loading specialized flowchart, planning, annotation, and media surfaces.
- Right-click a passive node or `flow` edge to edit style overrides, copy/paste them, reset to defaults, or save them as project-local presets stored under `metadata.ui.passive_style_presets`.
- Image and PDF panels resolve local filesystem sources only. PDF panels intentionally stay in single-page preview mode.

## Running Tests

```bash
QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest discover -s tests -v
```

## Interaction Notes

- Graphics settings are app-wide rather than project-local, so reopening the app restores the last saved grid/minimap/snap/theme choices.
- Standalone graph-theme editing previews only apply live when the edited theme is already the active explicit custom theme; Graph Themes opened from Graphics Settings do not mutate the running graph until Graphics Settings is accepted.
- Drag from a port to empty canvas space to open the connection-aware quick insert overlay.
- Quick insert only shows node types that can auto-connect to the dragged source port using the same compatibility rules as normal graph connections.
- Some node types expose inline property controls directly in the node card for faster editing, while the inspector remains the full editing surface.
- Graph Search is intentionally user-facing: it matches node titles and node types, not internal runtime IDs.
- Inspector header metadata uses sequential per-type IDs for orientation, while internal node IDs stay implementation-only.
- The passive-node reference workspace used for manual visual checks lives at `tests/fixtures/passive_nodes/reference_flowchart.sfe`.

## Building a Windows Installer

See [docs/PACKAGING_WINDOWS.md](docs/PACKAGING_WINDOWS.md) for PyInstaller
packaging, installer creation, and code signing instructions.

## Documentation

- [Architecture Guide](ARCHITECTURE.md) -- runtime/component architecture and flow maps
- [Architecture Diagrams](docs/architecture_diagrams/) -- generated Mermaid exports (`.mmd`, `.svg`, `.png`)
- [Spec Pack Index](docs/specs/INDEX.md) -- requirements, ADRs, traceability
- [Release Notes](RELEASE_NOTES.md) -- shipped capabilities and known risks
- [Pilot Runbook](docs/PILOT_RUNBOOK.md) -- validation steps for pilot deployments
- [Passive Visual Checklist](docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md) -- short manual pass for passive flowchart/media styling and reopen checks

Regenerate architecture diagrams after updating Mermaid blocks in `ARCHITECTURE.md`:

```bash
python3 scripts/export_architecture_diagrams.py
```
