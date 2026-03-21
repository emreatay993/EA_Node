# FLOWCHART_CARDINAL_PORTS P01: Neutral Port Contract

## Objective
- Add the neutral flowchart port contract, migrate the built-in passive flowchart catalog to four stored cardinal ports, and preserve directed edge storage plus non-flowchart validation behavior.

## Preconditions
- `P00` is marked `PASS` in [FLOWCHART_CARDINAL_PORTS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md).
- No later `FLOWCHART_CARDINAL_PORTS` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/builtins/passive_flowchart.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/graph/rules.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- targeted flowchart contract and graph-core tests

## Conservative Write Scope
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/builtins/passive_flowchart.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/graph/rules.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `tests/test_passive_flowchart_catalog.py`
- `tests/test_passive_node_contracts.py`
- `tests/test_registry_validation.py`
- `tests/graph_track_b/scene_and_model.py`
- `docs/specs/work_packets/flowchart_cardinal_ports/P01_neutral_port_contract_WRAPUP.md`

## Required Behavior
- Extend the port-direction contract to allow a new `neutral` token without weakening existing validation for `in` / `out` ports.
- Migrate all nine built-in passive flowchart node types to four stored ports with keys `top`, `right`, `bottom`, and `left`.
- Mark those four flowchart ports as `direction="neutral"`, `kind="flow"`, `data_type="flow"`, and `allow_multiple_connections=True`.
- Add a cardinal `side` field to flowchart port payloads/effective-port data and keep it aligned with the stored key for every passive flowchart node.
- Remove the legacy flowchart port keys from the built-in catalog and its contract tests.
- Do not preserve decision-branch meaning in port identity; after `branch_a` / `branch_b` removal, any decision semantics must live in edge labels or styling rather than in the port contract.
- Preserve directed edge storage: edges still serialize and persist as source node/port plus target node/port even though the flowchart ports themselves are neutral.
- Update core graph validation and authoring helpers so:
  - neutral flowchart-to-flowchart connections validate by explicit edge order plus kind/data-type compatibility
  - non-flowchart nodes continue enforcing the current `out -> in` rules unchanged
  - any convenience graph connect path that does not receive gesture order still chooses a deterministic source/target orientation for neutral flowchart nodes rather than failing
- For non-gesture connect actions (`connect_nodes` or equivalent helper paths), preserve the current left-to-right / top-to-bottom heuristic to choose source vs target, then select the nearest-facing cardinal ports on both nodes.
- Keep passive runtime exclusion behavior unchanged: passive flowchart nodes and passive `flow` edges remain authored/document objects only.

## Non-Goals
- No flowchart geometry or anchor-position rewrite yet. `P02` owns that.
- No GraphCanvas live drag or pending-port interaction rewrite yet. `P03` owns that.
- No quick-insert, dropped-node auto-connect, or edge-insert update yet. `P04` owns those flows.
- No requirement/traceability/fixture refresh yet. `P05` owns that.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_passive_flowchart_catalog.py tests/test_passive_node_contracts.py tests/test_registry_validation.py --ignore=venv -q`
2. `./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "flowchart or connect_nodes" -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_passive_flowchart_catalog.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/flowchart_cardinal_ports/P01_neutral_port_contract_WRAPUP.md`

## Acceptance Criteria
- Registry validation accepts `neutral` only where intended and continues rejecting invalid port directions.
- All nine built-in passive flowchart types publish exactly four neutral flow ports keyed `top`, `right`, `bottom`, and `left`.
- Flowchart port payloads expose a stable `side` field that matches the stored cardinal key.
- Graph-core connect and validation helpers accept neutral flowchart edges without regressing non-flowchart direction validation.
- Non-gesture neutral-flowchart connect helpers still resolve deterministic source/target order through the existing left-to-right / top-to-bottom heuristic plus nearest-facing cardinal-port selection.
- The persisted edge shape remains directed source/target storage rather than introducing a new edge schema.

## Handoff Notes
- Record the exact neutral-port helper names, `side` payload field names, and any non-gesture flowchart source/target heuristic chosen here so `P03` and `P04` reuse them instead of inventing parallel rules.
- Do not reintroduce legacy key aliases in later packets; later packets must build on the new cardinal-port contract directly.
