# P05 Regression Docs Traceability Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/flowchart-cardinal-ports/p05-regression-docs-traceability`
- Commit Owner: `worker`
- Commit SHA: `9b9a6aa529a51c9c2d2fd7c7758515cca5a74464`
- Changed Files: `ARCHITECTURE.md`, `docs/specs/requirements/20_UI_UX.md`, `docs/specs/requirements/30_GRAPH_MODEL.md`, `docs/specs/requirements/40_NODE_SDK.md`, `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`, `docs/specs/requirements/90_QA_ACCEPTANCE.md`, `docs/specs/requirements/TRACEABILITY_MATRIX.md`, `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`, `tests/fixtures/passive_nodes/reference_flowchart.sfe`, `docs/specs/work_packets/flowchart_cardinal_ports/P05_regression_docs_traceability_WRAPUP.md`
- Artifacts Produced: `ARCHITECTURE.md`, `docs/specs/requirements/20_UI_UX.md`, `docs/specs/requirements/30_GRAPH_MODEL.md`, `docs/specs/requirements/40_NODE_SDK.md`, `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`, `docs/specs/requirements/90_QA_ACCEPTANCE.md`, `docs/specs/requirements/TRACEABILITY_MATRIX.md`, `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md`, `tests/fixtures/passive_nodes/reference_flowchart.sfe`, `docs/specs/work_packets/flowchart_cardinal_ports/P05_regression_docs_traceability_WRAPUP.md`
- Architecture, requirements, QA, and traceability docs now describe the passive flowchart neutral-port contract explicitly: four stored cardinal ports (`top/right/bottom/left`), `direction="neutral"`, cardinal `side`, `origin_side` interaction payloads, gesture-ordered source/target authoring, exact silhouette perimeter anchors, retired legacy decision-port identity, and preserved non-flowchart fixed-direction behavior.
- `tests/fixtures/passive_nodes/reference_flowchart.sfe` now uses only cardinal flowchart port keys, explicitly exposes all four flowchart handles, and loads under the current serializer with `13` nodes and `8` surviving flowchart edges instead of silently dropping legacy-key edges.
- `docs/specs/perf/PASSIVE_NODES_VISUAL_CHECKLIST.md` now matches the updated reference workspace by calling out four-handle flowchart rendering, branch labels over branch-specific port names, the passive-only mainline path, and the optional file-level cardinal-key spot-check.
- Exact requirement carve-out for future maintainers: Passive flowchart ports with `direction="neutral"`, `kind="flow"`, `data_type="flow"`, and a cardinal `side` field are the only exception: when both endpoints are neutral flowchart ports, gesture order defines source and target while non-flowchart nodes keep fixed `in` / `out` validation.
- Acceptance on the integrated branch also includes executor remediation commit `c77f74332effcaa8bf6a6d64a8cd52286a49a7a0`, which isolates `GraphCanvasQmlPreferenceBindingTests` per subprocess in `tests/graph_track_b/qml_preference_bindings.py` and `tests/test_graph_track_b.py` so the packet's required Windows/Qt aggregate gate can complete reliably.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graph_track_b tests.test_passive_node_contracts tests.test_passive_runtime_wiring tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_passive_flowchart_catalog tests.test_flowchart_visual_polish -v` (`Ran 116 tests in 46.621s`, `OK`)
- PASS: `./venv/Scripts/python.exe scripts/check_traceability.py`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.graph_track_b.qml_preference_bindings -v` (`Ran 14 tests in 39.481s`, `OK`)
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch, open `tests/fixtures/passive_nodes/reference_flowchart.sfe`, and relink `reference_preview.png` / `reference_preview.pdf` in the inspector if the absolute fixture paths no longer resolve on this machine.
- Open the reference workspace. Expected: the canvas is passive-only, every flowchart node shows four handles, and the decision routes are distinguished by the `Review` and `Needs input` edge labels rather than branch-specific port names.
- Follow the main path from `Start` to `Complete`. Expected: the labeled flowchart remains readable after open, while the `Needs input` branch still lands on `Stakeholder Input`.
- Save and reopen the workspace. Expected: the image preview, PDF preview, node colors, edge labels, and four-handle flowchart layout all persist.
- Open a passive node style dialog and a flow-edge style dialog. Expected: `Review Accent` and `Review Loop` are available, apply/reset works, and reopen preserves the chosen style state.
- Click `Run`. Expected: the passive-only workspace produces no executable runtime graph side effects.
- Optional file spot-check: inspect `tests/fixtures/passive_nodes/reference_flowchart.sfe`. Expected: flowchart edges and exposed-port overrides use only `top`, `right`, `bottom`, and `left`.

## Residual Risks

- `tests.graph_track_b.qml_preference_bindings` now relies on per-test subprocess isolation to avoid a preexisting Windows/Qt interpreter-lifetime crash, so future in-process expansions of that suite still need explicit lifecycle cleanup or continued isolation.
- The passive reference workspace still stores absolute Windows media paths, so users on a moved checkout or different machine must relink the preview assets before running the manual checklist.

## Ready for Integration

- Yes: the required aggregate unittest command, the direct QML preference-binding rerun, and the traceability gate all pass on the integrated branch.
