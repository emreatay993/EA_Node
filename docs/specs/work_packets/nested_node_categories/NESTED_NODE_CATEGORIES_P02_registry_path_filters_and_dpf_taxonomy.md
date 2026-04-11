# NESTED_NODE_CATEGORIES P02: Registry Path Filters and DPF Taxonomy

## Objective
- Move registry discovery and category filtering onto descendant-inclusive path semantics, publish the shipped nested Ansys DPF catalog family, and keep graph-theme accents rooted at the first category segment.

## Preconditions
- `P01` is marked `PASS` in [NESTED_NODE_CATEGORIES_STATUS.md](./NESTED_NODE_CATEGORIES_STATUS.md).
- `P01` landed the packet-owned category-path helper and SDK contract without reopening flat string storage.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/nodes/category_paths.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_*.py`
- `ea_node_editor/ui/graph_theme/presentation.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_registry_filters.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_registry_validation.py`

## Conservative Write Scope
- `ea_node_editor/nodes/category_paths.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_*.py`
- `ea_node_editor/ui/graph_theme/presentation.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_registry_filters.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md`
- `docs/specs/work_packets/nested_node_categories/P02_registry_path_filters_and_dpf_taxonomy_WRAPUP.md`

## Required Behavior
- Make path-aware registry filtering canonical and descendant-inclusive so selecting a parent path returns all descendant nodes.
- If packet-external callers still need a compatibility `category=` filter alias, route it through the path helper contract instead of reviving exact string matching as authoritative logic.
- Publish a stable path-backed category discovery surface that later shell/library packets can consume without reparsing display strings.
- Move the built-in Ansys DPF catalog onto a real nested family:
  - compute nodes under `("Ansys DPF", "Compute", ...)`
  - viewer nodes under `("Ansys DPF", "Viewer", ...)`
- Leave non-DPF catalog families effectively flat in this packet unless a packet-local test forces a safe one-segment tuple migration touch-up.
- Resolve graph-theme category accents from the root segment so nested DPF children keep the same accent family as the prior flat `Ansys DPF` category.
- Add packet-owned regression tests whose names include `nested_category_registry` so the targeted verification commands below remain stable.

## Non-Goals
- No Python library trie/grouped-row rewrite yet.
- No QML nested category rendering or collapse behavior yet.
- No README or requirements updates yet.
- No broader node-catalog re-taxonomy beyond Ansys DPF.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_registry_filters.py tests/test_dpf_node_catalog.py tests/test_graph_theme_shell.py -k nested_category_registry --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_registry_filters.py tests/test_dpf_node_catalog.py -k nested_category_registry --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/nested_node_categories/P02_registry_path_filters_and_dpf_taxonomy_WRAPUP.md`

## Acceptance Criteria
- Registry filtering accepts parent `category_path` selections and returns descendants without relying on exact string equality.
- Leaf-path filtering remains precise and stable for the nested Ansys DPF subtree.
- Built-in Ansys DPF catalog entries publish the approved nested taxonomy while non-DPF families remain stable.
- Root-segment accent resolution preserves the current Ansys DPF color family for nested children.
- The packet-owned `nested_category_registry` regressions pass and prove the new filter/taxonomy behavior.

## Handoff Notes
- `P03` consumes the path-backed registry outputs and must not reverse this packet back to string-parsing logic.
- Any later packet that changes category-option payload values or the DPF nested labels must inherit and update the `nested_category_registry` regressions.
