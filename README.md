# COREX Node Editor

A Windows-first visual node editor for engineering dataflow pipelines. Build
graphs on a QML canvas, run workflows in a separate worker process, author
passive visual layouts on the same graph, and automate file, spreadsheet,
process, and HPC-oriented tasks from a single desktop shell.

Recent UI/UX architecture highlights:

- App-wide Graphics Settings modal for grid, minimap, snap-to-grid default, shell-theme selection, and graph-theme follow-shell or explicit selection
- Split shell/chrome theming (`ThemeBridge` + `stitch_dark` / `stitch_light`) from node/edge graph theming (`graphThemeBridge` + built-in/custom graph themes)
- Bridge-first shell/canvas QML context using `shellLibraryBridge`, `shellWorkspaceBridge`, `shellInspectorBridge`, `graphCanvasStateBridge`, `graphCanvasCommandBridge`, `graphActionBridge`, and typed viewer/add-on/status bridges instead of raw `mainWindow` / `sceneBridge` / `viewBridge` globals
- Custom graph-theme library/editor with built-in read-only themes, custom duplication/CRUD, and live apply for the active explicit custom theme
- Graphics preferences now persist in `app_preferences.json` separately from project `.sfe` files and `last_session.json`
- Passive visual node families now ship in the main graph model for flowcharting, planning, annotation, and local image/PDF presentation
- Dedicated `Comment Backdrop` passive grouping nodes render on an under-edge layer, wrap the current selection with shortcut `C`, derive nested membership from geometry, and keep collapse/clipboard behavior distinct from note-style annotation cards
- Passive `flow` edges support labels and per-edge style overrides while remaining excluded from runtime compilation and worker execution
- Passive node and flow-edge style overrides can be edited from context menus and saved as project-local presets in `.sfe` metadata
- Graph-surface input routing now keeps host body gestures under loaded surfaces, uses `embeddedInteractiveRects` for local control ownership, and reserves `blocksHostInteraction` for whole-surface modal tools such as crop mode
- Shared header inline title editing now spans standard, passive, collapsed, and scope-capable node shells, reusing the existing rename/history path while keeping a dedicated `OPEN` badge for subnode scope entry
- Connection-aware quick insert from a dangling wire drag
- Shared graph-surface controls now cover inline `toggle`, `enum`, `text`, `number`, `textarea`, and `path` editors without depending on selected-node timing
- Python-side compatibility filtering so quick insert follows the same effective-port rules as graph connections
- Inspector and script editing surfaces now use user-facing node labels and sequential IDs instead of exposing internal `node_*` references

## Getting Started

```powershell
# 1. Create the project virtual environment (Windows-first layout)
py -3.10 -m venv venv

# 2. Install runtime + developer dependencies into that venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -e ".[all,dev]"

# 3. Launch the app
.\venv\Scripts\python.exe -m ea_node_editor.bootstrap
```

- For a fuller setup and orientation guide, see [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).
- The package-module command above is the source/dev launch path. For packaged Windows builds and installer bundles, use [docs/PACKAGING_WINDOWS.md](docs/PACKAGING_WINDOWS.md).
- On Windows, user data lives under `%APPDATA%\COREX_Node_Editor\`; public single-file plugin drop-ins live directly in `%APPDATA%\COREX_Node_Editor\plugins\`, and imported `.eanp` packages install as subdirectories beneath that same root.
- The console entry point installed by editable mode is `corex-node-editor`.
- PowerShell examples are shown here. If you still open the repo from `bash`, use the same `venv/Scripts/python.exe` interpreter with `./...` path syntax.

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
    frame_rate.py
    startup_profile.py
    system_metrics.py
  ui/perf/
    performance_harness.py
  ui/
    app_icon.py
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
  assets/
    app_icon/
      corex_app.svg
      corex_app_*.png
      corex_app_transparent.svg
      corex_app_transparent_*.png
      corex_app_minimal.svg
      corex_app_minimal_*.png
      corex_app.ico
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

Drop a public Python file into the plugins folder at `%APPDATA%/COREX_Node_Editor/plugins/`
(or the fallback user-data directory returned by `ea_node_editor.settings.plugins_dir()`).
The loader reads top-level `*.py` files whose filenames do not start with `_`.
The file should define one or more classes that follow the `NodePlugin` protocol.
The example below assumes `numpy` and `scipy` are installed in the same virtual
environment as the application:

```python
import numpy as np
from scipy import signal

from ea_node_editor.nodes import (
    in_port,
    node_type,
    out_port,
    prop_enum,
    prop_float,
    prop_int,
)
from ea_node_editor.nodes.types import ExecutionContext, NodeResult


def _signal_packet(ctx: ExecutionContext, key: str = "signal") -> tuple[np.ndarray, float]:
    packet = dict(ctx.inputs.get(key) or {})
    samples = np.asarray(packet.get("samples", ()), dtype=np.float64)
    if samples.ndim != 1:
        raise ValueError("signal packets must provide a 1D 'samples' array.")
    sample_rate_hz = float(packet.get("sample_rate_hz", 48000.0))
    return samples, sample_rate_hz


@node_type(
    type_id="custom.bandpass_filter",
    display_name="Bandpass Filter",
    category_path=("Signal Processing", "Filters", "Bandpass"),
    icon="tune",
    ports=(
        in_port("signal", data_type="dsp.signal", required=True),
        out_port("filtered_signal", data_type="dsp.signal"),
    ),
    properties=(
        prop_float("low_cut_hz", 300.0, "Low Cut (Hz)"),
        prop_float("high_cut_hz", 3400.0, "High Cut (Hz)"),
        prop_int("filter_order", 4, "Filter Order"),
    ),
    description="Applies a zero-phase SciPy bandpass filter to a signal packet.",
)
class BandpassFilterNode:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        samples, sample_rate_hz = _signal_packet(ctx)
        low_cut_hz = float(ctx.properties.get("low_cut_hz", 300.0))
        high_cut_hz = float(ctx.properties.get("high_cut_hz", 3400.0))
        filter_order = int(ctx.properties.get("filter_order", 4))
        nyquist_hz = 0.5 * sample_rate_hz
        sos = signal.butter(
            filter_order,
            [low_cut_hz / nyquist_hz, high_cut_hz / nyquist_hz],
            btype="bandpass",
            output="sos",
        )
        filtered = signal.sosfiltfilt(sos, samples)
        return NodeResult(
            outputs={
                "filtered_signal": {
                    "samples": filtered,
                    "sample_rate_hz": sample_rate_hz,
                }
            }
        )


@node_type(
    type_id="custom.magnitude_spectrum",
    display_name="Magnitude Spectrum",
    category_path=("Signal Processing", "Analysis", "FFT"),
    icon="show_chart",
    ports=(
        in_port("signal", data_type="dsp.signal", required=True),
        out_port("spectrum", data_type="dsp.spectrum"),
    ),
    properties=(
        prop_int("fft_size", 2048, "FFT Size"),
        prop_enum("window", "hann", "Window", values=("hann", "hamming", "blackman")),
    ),
    description="Computes a NumPy/SciPy windowed FFT and emits a spectrum packet.",
)
class MagnitudeSpectrumNode:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        samples, sample_rate_hz = _signal_packet(ctx)
        fft_size = int(ctx.properties.get("fft_size", 2048))
        window_name = str(ctx.properties.get("window", "hann"))
        clipped = samples[:fft_size]
        if clipped.size < fft_size:
            clipped = np.pad(clipped, (0, fft_size - clipped.size))
        window = signal.get_window(window_name, fft_size, fftbins=True)
        spectrum = np.fft.rfft(clipped * window)
        frequencies_hz = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate_hz)
        magnitude_db = 20.0 * np.log10(np.maximum(np.abs(spectrum), 1e-12))
        return NodeResult(
            outputs={
                "spectrum": {
                    "frequencies_hz": frequencies_hz,
                    "magnitude_db": magnitude_db,
                    "sample_rate_hz": sample_rate_hz,
                }
            }
        )
```

Restart the application and the nodes will appear in the Node Library under
`Signal Processing > Filters > Bandpass` and
`Signal Processing > Analysis > FFT`. The `dsp.signal` and `dsp.spectrum`
values are custom `data_type` labels; use the same spelling on downstream ports
if you want them to connect directly.

Node authoring now uses `category_path=` instead of `category=`. This is a
breaking change for external plugins and node packages: update decorator calls
and direct `NodeTypeSpec` construction to pass a tuple of non-empty category
segments, such as `("Math",)` or `("Simulation", "Signals")`. The rendered
category label is derived from `category_path` for presentation only; grouping
and filtering never parse display text.

Nested library categories are path-backed. Parent category filters include all
descendants, the shipped Ansys DPF family appears under `Ansys DPF > Compute`
and `Ansys DPF > Viewer`, and custom workflows remain under the single
`Custom Workflows` segment. The rendered ` > ` separator is display-only and is
chosen so existing single labels such as `Input / Output` are not confused with
path segments; do not parse display text to recover category paths.

The shipped DPF backend remains optional, and `ansys-dpf-core` is optional at startup, but the built-in surface is now workflow-first rather than compute-only. Foundational helpers and inputs live under `Ansys DPF > Inputs`, `Ansys DPF > Workflow`, and `Ansys DPF > Helpers > ...`, generated operator wrappers live under `Ansys DPF > Operators > <Family>`, and `dpf.viewer` stays under `Ansys DPF > Viewer`. Built-in DPF registration is descriptor-first, add-on-owned, and version-aware, so startup refreshes the shipped descriptor cache when the installed `ansys-dpf-core` version changes. Saved DPF nodes reopen as locked unavailable-add-on projections when the backend is disabled or unavailable, and the earlier preparation contract still records that broad autogenerated operator exposure plus non-operator reflection remain deferred. On the shipped rollout, only the `Ansys DPF > Advanced > Raw API Mirror` / non-operator reflection surface remains deferred. See the
[DPF operator backend review](docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md)
and the
[DPF operator backend QA matrix](docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md)
for the frozen preparation contract, and the
[ANSYS DPF Full Plugin Rollout QA Matrix](docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md)
for the retained rollout proof surface.

The shipped add-on backend now exposes `Add-On Manager` as a top-level menubar entry and ships the Variant 4 inspector-style drawer on top of the generic add-on catalog. Add-ons carry stable ids, dependency facts, and exactly one apply policy (`hot_apply` or `restart_required`); unavailable add-on nodes stay visible as locked Mockup B projections instead of disappearing from the canvas; and ANSYS DPF is the first repo-local `hot_apply` add-on wired through the rebuild-based lifecycle. The retained packet evidence, closeout commands, and manual smoke guidance for that archived baseline live in the [Add-On Manager Backend Preparation QA Matrix](docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md).

Plugin modules and installed packages must export `PLUGIN_DESCRIPTORS`,
`PLUGIN_BACKENDS`, or package/entry-point descriptors that the loader can
register with provenance. Constructor probing and class scanning are not part
of the current plugin contract.

Installed `.eanp` packages use the same plugin root, but each package lives in
its own public subdirectory named after `node_package.json` `name`. Supported
package contents are `node_package.json` plus top-level `.py` modules only.

## Sharing Node Packages

- **Export:** File > Export Node Package -- packages one current user-plugin source candidate into a `.eanp` archive. Export candidates come from descriptor provenance in the user plugins directory only: either one top-level `.py` drop-in or one installed package directory's top-level `.py` files.
- **Import:** File > Import Node Package -- installs a `.eanp` archive as `%APPDATA%/COREX_Node_Editor/plugins/<package_name>/` with `node_package.json` plus top-level `.py` files, then reloads user plugins for the current session.
- **Current limitation:** If an imported package replaces node types that were already loaded earlier in the session, restart the application before relying on the replacement definitions.

## Graphics Settings

- Open `Settings > Graphics Settings` to configure the grid overlay, minimap visibility/default expansion, snap-to-grid default, shell theme, graph-theme follow-shell behavior, and explicit graph-theme selection.
- Use `Manage Graph Themes...` to duplicate built-in graph themes into editable custom themes, edit node/edge/category-accent/port-kind tokens, and choose an explicit graph theme.
- Shell-theme changes apply live to QWidget styling and QML shell/canvas chrome surfaces. Node and edge visuals resolve through the active graph theme.
- Graph themes affect `NodeCard` and `EdgeLayer` only; background, grid, minimap, marquee, and drop-preview chrome stay on the shell theme path.
- App-wide graphics preferences, including the inline custom graph-theme library, persist in `%APPDATA%\COREX_Node_Editor\app_preferences.json` and stay separate from project `.sfe` files and `last_session.json`.

## Passive Visual Authoring

- Passive flowchart, planning, annotation, image, and PDF nodes stay in the normal workspace graph and save into the same `.sfe` document as executable nodes.
- Passive visual nodes now share the same four logical-flow handles (`top`, `right`, `bottom`, `left`) for presentation-only `flow` authoring across flowchart, planning, annotation, and media families.
- `flow` edges are presentation-only graph connections. They support labels, branch styling, and multi-incoming targets where the target port spec allows it, but they do not reach the compiler or worker runtime graph.
- Passive nodes render through the graph host/factory path, which keeps standard `NodeCard` contracts stable while loading specialized flowchart, planning, annotation, and media surfaces.
- Right-click a passive node or `flow` edge to edit style overrides, copy/paste them, reset to defaults, or save them as project-local presets stored under `metadata.ui.passive_style_presets`.
- Image and PDF panels resolve local filesystem sources only. PDF panels intentionally stay in single-page preview mode.

## Running Tests

```powershell
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast
```

Use the repo-owned runner for the default day-to-day loop. It keeps the
`fast`, `gui`, `slow`, and `full` workflow stable, applies
`QT_QPA_PLATFORM=offscreen` to its child verification commands, and keeps the
shell-backed suites on a dedicated fresh-process shell-isolation phase in
`full` mode.

If the project venv has a partial `pytest` install and early startup fails
with `ModuleNotFoundError` for a direct `pytest` dependency such as
`iniconfig` or `exceptiongroup`, run any `scripts/run_verification.py` mode
once. The runner now repairs the missing package in `venv` before launching
the requested phase.

Inspect or run the full workflow with:

```powershell
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run
.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full
```

When you change verification docs, release docs, or packet-owned proof links,
audit them with:

```powershell
.\venv\Scripts\python.exe .\scripts\check_traceability.py
.\venv\Scripts\python.exe .\scripts\check_markdown_links.py
```

The canonical script paths remain `scripts/check_traceability.py` and
`scripts/check_markdown_links.py`; the PowerShell form simply prefixes them
with `.\`.

- The current no-legacy architecture/docs closeout evidence is summarized in
  `ARCHITECTURE.md`, `docs/specs/INDEX.md`,
  `docs/specs/perf/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md`,
  `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`, and
  `docs/specs/requirements/TRACEABILITY_MATRIX.md`.
- `fast` targets `pytest -m "not gui and not slow"` and, when
  `pytest-xdist` is available in the project venv, resolves an explicit worker
  count as `psutil.cpu_count(logical=True)`, else `os.cpu_count()`, else `1`,
  then passes `-n <resolved_count> --dist load`. If `pytest-xdist` is
  unavailable, it falls back to serial pytest and prints the runner notice.
- The repo-owned runner also preflights the project venv's direct `pytest`
  dependencies before phase execution. If a package such as `iniconfig` or
  `exceptiongroup` is missing, it installs the missing dependency into `venv`
  and retries automatically.
- Direct `.\venv\Scripts\python.exe -m pytest` runs now auto-enable xdist only
  for the safe non-GUI path. Broad invocations default to the same
  `not gui and not slow` slice, and focused GUI, slow, or shell-backed targets
  stay off that automatic parallel path to avoid Qt/QML RAM bloat.
- `gui` and `slow` keep the QML-heavy phases explicit:
  `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode gui` and
  `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode slow`. The
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
  fresh-process model. The manifest-owned contract for that phase now lives in
  `scripts/verification_manifest.py` (`SHELL_ISOLATION_SPEC` plus
  `SHELL_ISOLATION_CATALOG_SPECS`) and is executed through
  `tests/shell_isolation_runtime.py`.
- The direct module-level shell `unittest` commands listed in
  `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` remain supported for
  focused reruns outside the published `full` workflow.
- See `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md` for the approved mode
  shapes, dedicated shell-isolation phase, benchmark evidence, companion
  proof-audit command, and current baseline-status notes.

Focused graph-surface regression gate in PowerShell:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m unittest `
  tests.test_graph_surface_input_contract `
  tests.test_graph_surface_input_inline `
  tests.test_passive_graph_surface_host `
  tests.test_passive_image_nodes -v
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

## Interaction Notes

- Graphics settings are app-wide rather than project-local, so reopening the app restores the last saved grid/minimap/snap/theme choices.
- Standalone graph-theme editing previews only apply live when the edited theme is already the active explicit custom theme; Graph Themes opened from Graphics Settings do not mutate the running graph until Graphics Settings is accepted.
- Drag from a port to empty canvas space to open the connection-aware quick insert overlay.
- Quick insert only shows node types that can auto-connect to the dragged source port using the same compatibility rules as normal graph connections.
- Some node types expose inline property controls directly in the node card for faster editing, while the inspector remains the full editing surface.
- Graph Search is intentionally user-facing: it matches node titles, node types, safe note-like content, and exposed port labels, not internal runtime IDs.
- Inspector header metadata uses sequential per-type IDs for orientation, while internal node IDs stay implementation-only.
- The passive-node reference workspace used for manual visual checks lives at `tests/fixtures/passive_nodes/reference_flowchart.sfe`.

## Building a Windows Installer

Build Windows releases from PowerShell using the project-local virtual
environment and the repo packaging scripts:

```powershell
# From a fresh clone
py -3.10 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -e ".[all,dev]"

# Build the default/base packaged app bundle
.\scripts\build_windows_package.ps1 -PackageProfile base -Clean

# Wrap that bundle into the distributable installer package
.\scripts\build_windows_installer.ps1 -PackageProfile base
```

Key outputs:

- Packaged app bundle:
  `artifacts\pyinstaller\dist\base\COREX_Node_Editor\COREX_Node_Editor.exe`
- Installer bundle zip:
  `artifacts\releases\installer\base\<runId>\COREX_Node_Editor_installer_bundle_<runId>.zip`

Notes:

- Use `venv\Scripts\python.exe`; the packaging scripts expect the project-local
  Windows-style virtual environment.
- This is a one-folder PyInstaller build, not a single-file standalone `.exe`.
- `build_windows_package.ps1` runs a short offscreen smoke test by default.
  Add `-SkipSmoke` if you need to bypass it.
- Keep the same `-PackageProfile` across all packaging steps. The default
  profile is `base`.

Viewer packaging uses the same flow with `-PackageProfile viewer`:

```powershell
.\scripts\build_windows_package.ps1 -PackageProfile viewer -Clean -SkipSmoke
.\scripts\build_windows_installer.ps1 -PackageProfile viewer
```

The `viewer` profile requires the optional viewer/runtime imports to exist in
the project venv, including `ansys.dpf.core`, `pyvista`, `pyvistaqt`, and
`vtk`.

Optional code signing happens after the installer bundle is created:

```powershell
$env:EA_SIGN_CERT_THUMBPRINT = "YOUR_CERT_THUMBPRINT"
$env:EA_SIGN_TIMESTAMP_URL = "https://your.timestamp.server"
$env:EA_SIGN_REQUIRE_SIGNED = "1"
.\scripts\sign_release_artifacts.ps1 -PackageProfile base
```

For the full packaging reference, installer layout, and signing details, see
[docs/PACKAGING_WINDOWS.md](docs/PACKAGING_WINDOWS.md).

Regenerate the committed app icon asset set with:

```powershell
.\venv\Scripts\python.exe .\scripts\generate_app_icons.py
```

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) -- environment setup, first launch, smoke checks, and common paths
- [Architecture Guide](ARCHITECTURE.md) -- runtime/component architecture and flow maps
- [Architecture Diagrams](docs/architecture_diagrams/) -- generated Mermaid exports (`.mmd`, `.svg`, `.png`)
- [Spec Pack Index](docs/specs/INDEX.md) -- requirements, ADRs, traceability
- [Release Notes](RELEASE_NOTES.md) -- shipped capabilities and known risks
- [Pilot Runbook](docs/PILOT_RUNBOOK.md) -- validation steps for pilot deployments
- [Architecture Maintainability Refactor QA Matrix](docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md) -- current docs/release guardrails, shell-isolation contract, historical pointers, and Windows-only follow-ups
- [COREX No-Legacy Architecture Cleanup QA Matrix](docs/specs/perf/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md) -- active no-legacy architecture closeout proof for focused bridges, current-schema persistence, descriptor-only loading, snapshot-only runtime payloads, typed viewer transport, and canonical launch/import paths
- [DPF Operator Backend Review](docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md) -- locked optional-DPF preparation contract, explicit deferrals, and later operator-rollout assumptions
- [DPF Operator Backend QA Matrix](docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md) -- retained `P01` through `P04` DPF backend verification plus the `P05` traceability and markdown closeout commands
- [ANSYS DPF Full Plugin Rollout QA Matrix](docs/specs/perf/ANSYS_DPF_FULL_PLUGIN_ROLLOUT_QA_MATRIX.md) -- retained `P00` through `P07` rollout verification, workflow-first taxonomy proof, generated operator/helper evidence, and the remaining raw-API deferral
- [Add-On Manager Backend Preparation QA Matrix](docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md) -- retained `P01` through `P07` add-on backend verification, Variant 4 manager proof, locked-projection behavior, DPF hot-apply lifecycle evidence, and the exact `P08` closeout commands
- [Passive Visual Checklist](docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md) -- short manual pass for passive flowchart/media styling and reopen checks
- [Graph Surface Input QA Matrix](docs/specs/perf/GRAPH_SURFACE_INPUT_QA_MATRIX.md) -- current host/inline/media/shell coverage and shell-module verification status
- [Verification Speed QA Matrix](docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md) -- approved `fast`/`gui`/`slow`/`full` workflow, dedicated shell-isolation phase, benchmark evidence, proof-audit command, and baseline-status notes
- [Nested Node Categories QA Matrix](docs/specs/perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md) -- retained SDK, registry, library, QML, manual, and traceability evidence for `category_path` node authoring
- The Spec Pack Index lists the retained work-packet manifests, status ledgers, and closeout QA matrices that remain canonical on this branch.

Regenerate architecture diagrams after updating Mermaid blocks in `ARCHITECTURE.md`:

```powershell
.\venv\Scripts\python.exe .\scripts\export_architecture_diagrams.py
```

The exporter writes `.mmd`, `.svg`, and `.png` assets into `docs/architecture_diagrams/` and uses the Kroki Mermaid rendering service, so it requires network access.
