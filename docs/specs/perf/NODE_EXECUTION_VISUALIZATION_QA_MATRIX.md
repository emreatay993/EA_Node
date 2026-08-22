# Node Execution Visualization QA Matrix

- Updated: `2026-07-18`
- Status: retained closeout evidence for fixed active-node semantic colors and the dependency-driven DataTree cutover
- Scope: fixed light/dark active-node state colors, glow-free lifecycle presentation, unchanged passive styling, semantic port states, data-wire color boundaries, transient timing/output facts, and removal of executable control surfaces
- Requirement anchors: `REQ-EXEC-007`, `REQ-UI-034`, `REQ-NODE-027`, `REQ-PERF-010`, `REQ-QA-027`, and `REQ-QA-028`

## Locked Contract

- `node_started` begins node-owned running presentation. `node_settled` is the typed per-node settlement event and carries `completed`, `empty`, `failed`, or `blocked` status plus settled outputs, root errors, warnings, and `elapsed_ms` where available.
- Active and `compile_only` node chrome uses one fixed palette per shell brightness rather than graph-theme or per-instance colors. Failed nodes use the fixed red/pink body and error badge; warning nodes use the fixed yellow body and warning badge; selected active nodes use the fixed blue body and outline. Selection outranks the reserved disabled state, then failure, warning, and neutral styling; diagnostic badges remain visible on selected nodes.
- Running keeps its existing progress and live elapsed presentation without a glow. Default, running, completed, and fresh-run nodes use the same neutral body. Every active-node lifecycle/preview/selection halo, pulse, flash, and glow is absent.
- Passive `visual_style`, graph-theme node defaults, selected outline, and selected glow remain unchanged. Custom graph-theme node controls are labeled `Passive Node Defaults` and do not override active or `compile_only` chrome.
- A disabled active-node palette is resolved and tested for future adoption, but no disabled-node model field, command, persistence, or execution semantics are introduced.
- Known active and `compile_only` `visual_style` is ignored at mutation/projection boundaries, removed by schema-5 normalization, and omitted from saved documents and scene payloads. Passive and unresolved styles remain intact; there is no schema bump.
- Node progress, completion, failure, elapsed time, error inspection, and authored-node focus remain available. Root-error identity remains attached to the originating node rather than producing cascade errors on dependents.
- Node lifecycle state and cached elapsed/output facts are session-only and per workspace. They add no `.cxproj` fields, durable solution claim, second output cache, or second execution-state channel.
- Ordinary data wires never represent runtime failure or progress. They do not turn red when a producer or consumer fails; red grips and wires mean invalid type compatibility only.
- A required input waiting for data is yellow. An empty or inactive output is gray. A current value uses a filled green output grip, and a defaulted input uses an outlined green input grip.
- Item, List, and Tree wires retain one-, two-, and three-stroke structure styling. Empty and disabled wires remain hittable and render gray/dashed; selection and preview styling remain interaction-owned.
- There are no execution/failure grips, no dedicated failure-routing port, no control Settings row, and no execution/control edge animation. Data and passive authoring wires do not receive lifecycle flashes.
- Run termination, Stop, fatal infrastructure reset, project replacement, and workspace/session replacement clear transient node presentation according to the run-controller contract. Non-fatal terminal reporting may retain the last inspectable node context without coloring ordinary wires.

## State Acceptance Matrix

| Runtime or port state | Required presentation | Forbidden presentation |
|---|---|---|
| Default active node | Fixed neutral body/outline/text for the current shell brightness | Graph-theme or per-instance body colors |
| Running active node | Neutral body plus non-glow node-owned progress and live elapsed time | Pulse, halo, flash, glow, or lifecycle color on connected data wires |
| Completed or fresh-run active node | Neutral body and cached `elapsed_ms` where available | Completion/fresh fill, halo, pulse, flash, or edge effect |
| Warning active node | Fixed yellow body, warning outline, and warning badge | Warning halo, pulse, or ordinary-wire color |
| Failed active node | Fixed red/pink body, error outline, error badge, root-error inspection, and authored-node focus | Error halo/pulse, red ordinary data wires, or dependent cascade errors |
| Selected active node | Fixed blue body and outline with diagnostic badge retained | Selection halo/glow or graph-theme selected color |
| Future disabled active node | Reserved muted body/outline/text palette, test-resolvable only | Reachable disabled semantics, persistence, or commands |
| Selected passive node | Existing graph-theme selected outline/glow | Active-node fixed blue fill replacing passive authored styling |
| Required input waiting | Yellow input grip | Failure red |
| Empty or inactive output | Gray output grip and gray/dashed connected wire | Successful-value green |
| Current output value | Filled green output grip | Full runtime value copied into QML scene payloads |
| Input using a default | Outlined green input grip | Filled output-value treatment |
| Invalid element type | Red grip/wire type error | Runtime-failure interpretation |
| Disabled wire | Selectable, hittable, ordered, gray/dashed | Dependency, path, or item contribution |

## Fixed Active-Node Palette

| Theme | State | Body start -> end | Outline | Title / ports |
| --- | --- | --- | --- | --- |
| Light | Default | `#F6F8F8` -> `#F9FBFC` | `#6B7277` | `#17174B` / `#43436D` |
| Light | Warning | `#FADB8E` -> `#FCDD90` | `#F0B72D` | `#17174B` / `#43436D` |
| Light | Error | `#FAA59A` -> `#FCA79C` | `#E15949` | `#17174B` / `#43436D` |
| Light | Disabled | `#CDD0D1` -> `#CFD2D3` | `#BDC3C7` | `#9697A8` / `#A2A4B2` |
| Light | Selected | `#ACDCF0` -> `#ADDDF1` | `#009EE0` | `#17174B` / `#43436D` |
| Dark | Default | `#403C2D` -> `#3A372A` | `#81795C` | `#F3F3F1` / `#D7D5CE` |
| Dark | Warning | `#5A4A28` -> `#4E4024` | `#D9A93C` | `#F8F4E8` / `#E6D6B1` |
| Dark | Error | `#5D2F30` -> `#51292A` | `#E36155` | `#FBEAE8` / `#E7C2BE` |
| Dark | Disabled | `#404244` -> `#393B3D` | `#5D6164` | `#B3B7BC` / `#9EA3A8` |
| Dark | Selected | `#1F5369` -> `#1A485B` | `#00A5E4` | `#F2F7FA` / `#C9E8F3` |

## Retained Automated Verification

| Coverage area | Primary requirements | Current proof |
|---|---|---|
| Typed lifecycle events, root failures, warnings, and timing metadata | `REQ-EXEC-007`, `REQ-NODE-027` | `tests/test_execution_worker.py`, `tests/test_execution_client.py` |
| Run-controller node state, failure focus, cleanup, and session-only elapsed/output facts | `REQ-UI-034`, `REQ-NODE-027` | `tests/test_run_controller_unit.py`, `tests/test_shell_run_controller.py`, `tests/test_project_session_controller_unit.py` |
| Fixed light/dark active palettes, state priority, selected fill, reserved disabled colors, and complete execution-glow removal | `REQ-UI-018`, `REQ-UI-034`, `REQ-QA-010`, `REQ-QA-028` | `tests/graph_surface/passive_host_interaction_suite.py`, `tests/graph_track_b/qml_preference_bindings.py`, `tests/graph_track_b/qml_preference_rendering_suite.py`, `tests/test_node_restyle_mockup.py` |
| Passive-only theme defaults and known non-passive `visual_style` removal/omission | `REQ-UI-019`, `REQ-PERSIST-012` | `tests/test_graph_theme_editor_dialog.py`, `tests/test_graph_theme_preferences.py`, `tests/test_serializer.py`, `tests/test_serializer_schema_migration.py` |
| Waiting, empty, failed, current, stale, and default port projection | `REQ-UI-034`, `REQ-QA-028` | `tests/test_port_flow_state.py`, `tests/test_graph_scene_bridge_bind_regression.py` |
| Invalid-type-only red wire treatment, disabled/empty hit behavior, and absence of runtime wire state | `REQ-UI-034`, `REQ-PERF-010` | `tests/test_flow_edge_labels.py`, `tests/test_graph_canvas_native_renderer.py`, `tests/graph_track_b/qml_preference_rendering_suite.py` |
| Complete absence of executable control grips, rows, actions, and edge animation | `REQ-QA-028` | `tests/test_track_h_perf_harness.py`, `tests/test_graph_action_contracts.py`, `tests/test_traceability_checker.py` |
| Retained requirement, traceability, and Markdown-link consistency | `REQ-QA-027` | `scripts/check_traceability.py`, `scripts/check_markdown_links.py`, `tests/test_traceability_checker.py` |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py tests/graph_track_b/qml_preference_bindings.py tests/graph_track_b/qml_preference_rendering_suite.py tests/test_node_restyle_mockup.py --ignore=venv -q` | Prove fixed active palettes, glow removal, and unchanged passive selection behavior |
| `./venv/Scripts/python.exe -m pytest tests/test_graph_theme_editor_dialog.py tests/test_graph_theme_preferences.py tests/test_serializer.py tests/test_serializer_schema_migration.py --ignore=venv -q` | Prove passive-only theme controls and non-passive `visual_style` removal/omission |
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py -k node_execution_visualization_qa_matrix_records_node_only_contract -q` | Prove this retained matrix records the node-only contract and contains no retired edge-progress language |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | Validate requirement and acceptance coverage |
| `./venv/Scripts/python.exe scripts/check_markdown_links.py` | Validate local documentation links and anchors |
| `git diff --check -- README.md docs/GETTING_STARTED.md docs/specs/INDEX.md docs/specs/requirements/TRACEABILITY_MATRIX.md docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md` | Reject whitespace and patch-format defects in this documentation slice |
| `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --summarize-output` | Final coordinated graph/execution/persistence/catalog/QML gate, run once at overall cutover closeout |

## Manual Desktop Checks

1. In light and dark shells, inspect Default, Running, Warning, Error, and Selected active nodes; confirm exact fills/outlines remain unchanged when custom graph themes change, selected nodes use blue fill without glow, and warning/error badges remain legible when selected.
2. Run and complete a simple active data chain; confirm running keeps non-glow progress/elapsed presentation, completed/fresh nodes return to neutral, no lifecycle/preview halo or flash appears, and connected data wires keep their normal semantic style.
3. Select styled rectangular and flowchart passive nodes; confirm their authored bodies and existing graph-theme selection glows remain unchanged.
4. Fail an authored node and confirm the red/pink body, badge, root error, and focus target identify that node while ordinary incoming and outgoing data wires do not become failure-red.
5. Inspect required-waiting, defaulted, current-value, empty, inactive, disabled, and invalid-type ports at normal and dense zoom levels; confirm the locked yellow, outlined/filled green, gray/dashed, and invalid-only red treatments remain distinct.
6. Switch workspaces, stop a run, replace the project, and reopen a saved project; confirm transient lifecycle state and cached timing/output facts remain workspace/session scoped, and stale known-active `visual_style` never reappears from persistence.
7. Open node and edge authoring menus and confirm no active-node color editor, executable control port, control row, failure-routing surface, or lifecycle edge-animation action is present.

## Residual Desktop-Only Validation

- Offscreen automation cannot judge final palette contrast, gradient quality, or diagnostic-badge legibility under real Windows compositing and dense graph zoom.
- Desktop acceptance should check only presentation quality. Palette values, absence of glow items/animations, disabled-state unreachability, protocol semantics, state priority, cache lifetime, wire-state exclusion, and control-surface absence remain automated contracts.
