# EA Node Editor

A Windows-first visual node editor for engineering dataflow pipelines. Build
graphs on a QML canvas, run workflows in a separate worker process, author
passive visual layouts on the same graph, and automate file, spreadsheet,
process, and HPC-oriented tasks from a single desktop shell.

Recent UI/UX architecture highlights:

- App-wide Graphics Settings modal for grid, minimap, snap-to-grid default, shell-theme selection, and graph-theme follow-shell or explicit selection
- Split shell/chrome theming (`ThemeBridge` + `stitch_dark` / `stitch_light`) from node/edge graph theming (`graphThemeBridge` + built-in/custom graph themes)
- Custom graph-theme library/editor with built-in read-only themes, custom duplication/CRUD, and live apply for the active explicit custom theme
- Graphics preferences now persist in `app_preferences.json` separately from project `.sfe` files and `last_session.json`
- Passive visual node families now ship in the main graph model for flowcharting, planning, annotation, and local image/PDF presentation
- Passive `flow` edges support labels and per-edge style overrides while remaining excluded from runtime compilation and worker execution
- Passive node and flow-edge style overrides can be edited from context menus and saved as project-local presets in `.sfe` metadata
- Graph-surface input routing now keeps host body gestures under loaded surfaces, uses `embeddedInteractiveRects` for local control ownership, and reserves `blocksHostInteraction` for whole-surface modal tools such as crop mode
- Connection-aware quick insert from a dangling wire drag
- Shared graph-surface controls now cover inline `toggle`, `enum`, `text`, `number`, `textarea`, and `path` editors without depending on selected-node timing
- Python-side compatibility filtering so quick insert follows the same effective-port rules as graph connections
- Inspector and script editing surfaces now use user-facing node labels and sequential IDs instead of exposing internal `node_*` references

## Getting Started

```bash
# 1. Create the project virtual environment (Windows-first layout)
py -3.10 -m venv venv

# 2. Install runtime + developer dependencies into that venv
./venv/Scripts/python.exe -m pip install --upgrade pip
./venv/Scripts/python.exe -m pip install -e ".[all,dev]"

# 3. Launch the app
./venv/Scripts/python.exe main.py
```

- For a fuller setup and orientation guide, see [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).
- On Windows, user data lives under `%APPDATA%\EA_Node_Editor\`; public single-file plugin drop-ins live directly in `%APPDATA%\EA_Node_Editor\plugins\`, and imported `.eanp` packages install as subdirectories beneath that same root.
- The console entry point installed by editable mode is `ea-node-editor`.

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
        GraphInlinePropertiesLayer.qml
        GraphNodeHost.qml
        GraphNodeSurfaceMetrics.js
        GraphNodeSurfaceLoader.qml
        EdgeMath.js
        NodeCard.qml
        passive/
          FlowchartShapeCanvas.qml
          GraphAnnotationNoteSurface.qml
          GraphFlowchartNodeSurface.qml
          GraphMediaPanelSurface.qml
          GraphPlanningCardSurface.qml
        surface_controls/
          GraphSurfaceButton.qml
          GraphSurfaceCheckBox.qml
          GraphSurfaceComboBox.qml
          GraphSurfaceInteractiveRegion.qml
          GraphSurfacePathEditor.qml
          GraphSurfaceTextArea.qml
          GraphSurfaceTextField.qml
          GraphSurfaceTextareaEditor.qml
          SurfaceControlGeometry.js
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
        ShellCollapsibleSidePane.qml
        ShellContextMenu.qml
        ShellCreateButton.qml
        ShellLabeledTabStrip.qml
        ShellRunToolbar.qml
        ShellStatusStrip.qml
        ShellTitleBar.qml
        WorkspaceCenterPane.qml
        icons/
          *.svg
  workspace/
    manager.py

tests/
docs/specs/
```

## Creating a Custom Node

Drop a public Python file into the plugins folder at `%APPDATA%/EA_Node_Editor/plugins/`
(or the fallback user-data directory returned by `ea_node_editor.settings.plugins_dir()`).
The loader reads top-level `*.py` files whose filenames do not start with `_`.
The file should define one or more classes that follow the `NodePlugin` protocol:

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

Installed `.eanp` packages use the same plugin root, but each package lives in
its own public subdirectory named after `node_package.json` `name`. Supported
package contents are `node_package.json` plus top-level `.py` modules only.

## Sharing Node Packages

- **Export:** File > Export Node Package -- packages one current user-plugin source candidate into a `.eanp` archive. Export candidates come from the user plugins directory only: either one top-level `.py` drop-in or one installed package directory's top-level `.py` files.
- **Import:** File > Import Node Package -- installs a `.eanp` archive as `%APPDATA%/EA_Node_Editor/plugins/<package_name>/` with `node_package.json` plus top-level `.py` files, then reloads user plugins for the current session.
- **Current limitation:** If an imported package replaces node types that were already loaded earlier in the session, restart the application before relying on the replacement definitions.

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
./venv/Scripts/python.exe scripts/run_verification.py --mode fast
```

Use the repo-owned runner for the default day-to-day loop. It keeps the
`fast`, `gui`, `slow`, and `full` workflow stable, applies
`QT_QPA_PLATFORM=offscreen` to its child verification commands, and keeps the
shell-backed suites on a dedicated fresh-process shell-isolation phase in
`full` mode.

Inspect or run the full workflow with:

```bash
./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run
./venv/Scripts/python.exe scripts/run_verification.py --mode full
```

When you change verification docs or packet-owned proof links, audit them with:

```bash
./venv/Scripts/python.exe scripts/check_traceability.py
```

- `fast` targets `pytest -m "not gui and not slow"` and, when
  `pytest-xdist` is available in the project venv, resolves an explicit worker
  count as `psutil.cpu_count(logical=True)`, else `os.cpu_count()`, else `1`,
  then passes `-n <resolved_count> --dist load`. If `pytest-xdist` is
  unavailable, it falls back to serial pytest and prints the runner notice.
- `gui` and `slow` keep the QML-heavy phases explicit:
  `./venv/Scripts/python.exe scripts/run_verification.py --mode gui` and
  `./venv/Scripts/python.exe scripts/run_verification.py --mode slow`. The
  `gui` phase also uses `-n <gui_resolved_count> --dist load` when
  `pytest-xdist` is available, where `<gui_resolved_count>` is capped at `6`
  workers to avoid over-saturating the QML-heavy slice; `slow` remains serial
  by design.
- `full` runs the three non-shell pytest phases first, then executes
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_isolation_phase.py -q -n <resolved_count> --dist load`
  as the dedicated shell-isolation phase when `pytest-xdist` is available.
  Each parametrized target still launches its own fresh child process across
  the `tests.test_main_window_shell`, `tests.test_script_editor_dock`,
  `tests.test_shell_run_controller`, and
  `tests.test_shell_project_session_controller` catalogs; without
  `pytest-xdist`, the same phase falls back to serial pytest and preserves the
  fresh-process model.
- The direct module-level shell `unittest` commands listed in
  `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` remain supported for
  focused reruns outside the published `full` workflow.
- See `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` for the approved mode
  shapes, dedicated shell-isolation phase, benchmark evidence, companion
  proof-audit command, and current baseline-status notes.

Focused graph-surface regression gate:

```bash
QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest \
  tests.test_graph_surface_input_contract \
  tests.test_graph_surface_input_inline \
  tests.test_passive_graph_surface_host \
  tests.test_passive_image_nodes -v
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

- [Getting Started](docs/GETTING_STARTED.md) -- environment setup, first launch, smoke checks, and common paths
- [Architecture Guide](ARCHITECTURE.md) -- runtime/component architecture and flow maps
- [Architecture Diagrams](docs/architecture_diagrams/) -- generated Mermaid exports (`.mmd`, `.svg`, `.png`)
- [Spec Pack Index](docs/specs/INDEX.md) -- requirements, ADRs, traceability
- [Release Notes](RELEASE_NOTES.md) -- shipped capabilities and known risks
- [Pilot Runbook](docs/PILOT_RUNBOOK.md) -- validation steps for pilot deployments
- [Passive Visual Checklist](docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md) -- short manual pass for passive flowchart/media styling and reopen checks
- [Graph Surface Input QA Matrix](docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md) -- current host/inline/media/shell coverage and shell-module verification status
- [Verification Speed QA Matrix](docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md) -- approved `fast`/`gui`/`slow`/`full` workflow, dedicated shell-isolation phase, benchmark evidence, proof-audit command, and baseline-status notes
- [ARCH_FIFTH_PASS QA Matrix](docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_QA_MATRIX.md) -- accepted fifth-pass packet outcomes, carried verification anchors, final traceability evidence, and residual risks

Regenerate architecture diagrams after updating Mermaid blocks in `ARCHITECTURE.md`:

```bash
./venv/Scripts/python.exe scripts/export_architecture_diagrams.py
```

The exporter writes `.mmd`, `.svg`, and `.png` assets into `docs/architecture_diagrams/` and uses the Kroki Mermaid rendering service, so it requires network access.
