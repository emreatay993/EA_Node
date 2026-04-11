# Nested Node Categories QA Matrix

- Updated: `2026-04-11`
- Packet set: retained `NESTED_NODE_CATEGORIES` (`P01` through `P05`)
- Scope: final closeout matrix for the shipped path-backed node category schema, registry and library descendant filtering, nested Ansys DPF taxonomy, QML nested library presentation, external-plugin authoring migration, and traceability/docs evidence.

## Locked Scope

- `category_path: tuple[str, ...]` is the authoritative source of truth for node categories. Paths normalize to `1..10` non-empty trimmed string segments.
- Node authoring uses `category_path=` in decorator calls and direct `NodeTypeSpec` construction. `category=` is a breaking change for external plugins and node packages and must be migrated.
- `category` may still appear as read-only display text on specs and payloads for compatibility, but grouping, sorting, filtering, collapse state, and registry discovery use normalized paths and `category_key`.
- The display separator is ` > `. It is presentation-only and intentionally avoids ambiguity with existing single-segment labels such as `Input / Output`; display text must not be parsed to recover a category path.
- Registry and library filters are descendant-inclusive: filtering by `("Ansys DPF",)` includes descendants under `("Ansys DPF", "Compute")` and `("Ansys DPF", "Viewer")`.
- The shipped nested catalog scope is narrow. Ansys DPF compute nodes live under `Ansys DPF > Compute`, the viewer node lives under `Ansys DPF > Viewer`, other built-in families remain effectively flat, and custom workflows stay under `Custom Workflows`.
- The library pane remains a flat `ListView` over pre-flattened trie rows. Category rows are synthesized, sorted segment-by-segment, emitted before direct node rows, and default collapsed with QML collapse state keyed by `category_key`.
- Graph-theme category accents remain rooted at the first category segment so nested families keep the root category color family.
- No `.sfe` serializer migration or node-instance migration is required because node category metadata is not persisted on node instances.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| SDK helper contract, `category_path` normalization, read-only display compatibility, decorator authoring, and validation bounds | `P01` | `REQ-NODE-003`, `REQ-NODE-007`, `AC-REQ-NODE-008-01` | `.\venv\Scripts\python.exe -m pytest tests/test_decorator_sdk.py tests/test_registry_validation.py -k nested_category_sdk --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P01_sdk_category_path_contract_WRAPUP.md` (`00b41faba08e19d45648b519980feda1ed81d546`) |
| Review gate for SDK validation and helper behavior | `P01` | `AC-REQ-NODE-003-01` | `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py -k nested_category_sdk --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P01_sdk_category_path_contract_WRAPUP.md` (`00b41faba08e19d45648b519980feda1ed81d546`) |
| Registry path filters, descendant-inclusive parent matching, nested Ansys DPF taxonomy, and root-segment graph-theme accents | `P02` | `REQ-NODE-003`, `REQ-NODE-025`, `REQ-INT-008` | `.\venv\Scripts\python.exe -m pytest tests/test_registry_filters.py tests/test_dpf_node_catalog.py tests/test_graph_theme_shell.py -k nested_category_registry --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P02_registry_path_filters_and_dpf_taxonomy_WRAPUP.md` (`95d9b47ce4397253c87dba4d24b6a6d3fc95d25e`) |
| Registry and DPF review gate for path filters and shipped taxonomy | `P02` | `AC-REQ-NODE-003-01`, `AC-REQ-NODE-025-01`, `AC-REQ-INT-008-01` | `.\venv\Scripts\python.exe -m pytest tests/test_registry_filters.py tests/test_dpf_node_catalog.py -k nested_category_registry --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P02_registry_path_filters_and_dpf_taxonomy_WRAPUP.md` (`95d9b47ce4397253c87dba4d24b6a6d3fc95d25e`) |
| Python-side library payload projection, trie-flattened category rows, full-path displays, category options, quick insert metadata, and custom workflow category retention | `P03` | `REQ-UI-006`, `REQ-NODE-003` | `.\venv\Scripts\python.exe -m pytest tests/test_window_library_inspector.py tests/main_window_shell/bridge_support.py -k nested_category_library_payload --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P03_library_tree_payload_projection_WRAPUP.md` (`0b68d8630c0efd4d4afd8de8892483c60213476b`) |
| Shell library drop/connect review gate for payload compatibility with node insertion flows | `P03` | `AC-REQ-UI-006-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py -k nested_category_library_payload --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P03_library_tree_payload_projection_WRAPUP.md` (`0b68d8630c0efd4d4afd8de8892483c60213476b`) |
| QML `ListView` presentation, indentation by `depth`, ancestor-aware visibility, default collapsed state, and node-row drag/drop guardrails | `P04` | `REQ-UI-006`, `AC-REQ-UI-006-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py tests/main_window_shell/drop_connect_and_workflow_io.py tests/test_main_window_shell.py -k nested_category_qml --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P04_qml_nested_library_presentation_WRAPUP.md` (`21d3de58d09e0c0bfd5d9aa1d10a5bae0fd36b0a`) |
| QML review gate for category-key collapse semantics and preserved node click/drop paths | `P04` | `AC-REQ-UI-006-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/drop_connect_and_workflow_io.py -k nested_category_qml --ignore=venv -q` | PASS in `docs/specs/work_packets/nested_node_categories/P04_qml_nested_library_presentation_WRAPUP.md` (`21d3de58d09e0c0bfd5d9aa1d10a5bae0fd36b0a`) |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Packet-owned traceability regression for the nested node categories closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Review-gate proof audit for retained requirement, QA, index, and traceability docs |

## 2026-04-11 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the new QA matrix, spec-index registration, requirement anchors, README/getting-started authoring guidance, and traceability rows for the nested node categories closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the index, requirement docs, QA matrix, and traceability refresh landed in the packet worktree |

## Retained Manual Evidence

1. SDK authoring check: create a `NodeTypeSpec` with `category_path=("Root", "Child")` and confirm it exposes `category_path` as `("Root", "Child")` and read-only `category` display as `Root > Child`.
2. Registry descendant-filter check: filter the default registry with `category_path=("Ansys DPF",)` and confirm DPF compute nodes plus `dpf.viewer` are returned.
3. Taxonomy check: inspect `dpf.result_file` and `dpf.viewer` and confirm their paths are `("Ansys DPF", "Compute")` and `("Ansys DPF", "Viewer")`.
4. Library payload check: build grouped library items and confirm category rows for `Ansys DPF`, `Ansys DPF > Compute`, and `Ansys DPF > Viewer` appear with increasing depth.
5. Category-option filter check: filter by the `category_key(("Ansys DPF",))` option and confirm descendants from both DPF child categories remain visible.
6. Custom workflow check: build a custom workflow library item and confirm its path remains `("Custom Workflows",)`.
7. Desktop QML check: launch the app, expand `Ansys DPF`, then expand `Compute`, and confirm child category rows are indented, child categories remain collapsed until clicked, and visible node rows still click or drag to the canvas.

## Residual Risks

- Retained packet verification commands passed with exit code `0`, but P01 through P04 wrap-ups recorded the known ignored Windows pytest temp-directory cleanup `PermissionError` after success in this environment.
- P05 is docs-and-traceability-only. It does not rerun a new broad aggregate suite beyond the declared traceability regression and review gate.
- External plugins that still pass `category=` to `@node_type(...)` or `NodeTypeSpec(...)` need a source update to `category_path=` before they load under the shipped authoring contract.
- The QML nested-library behavior is covered by offscreen boundary tests and retained manual desktop directives; final release validation should still include a native Windows library smoke check for visual indentation, collapse, and drag/drop feel.
