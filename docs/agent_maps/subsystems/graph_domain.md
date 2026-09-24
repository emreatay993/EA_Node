# Graph Domain, Mutation, Transforms, And Hierarchy

## Purpose

The [Python Script authoring route](../feature_routes/python_script_authoring.md)
uses `prepare_python_script` for detached impact and `apply_python_script` for
freshly validated commits. Explicit key transfers preserve compatible edges and
saved state, including compound name reuse; generic dynamic-key rename keeps
its pruning behavior. Port-state projection remains pure.

Use this for graph data structures, invariants, mutation services, transforms, hierarchy, ports, and comment geometry.

## Start Here
- `ea_node_editor/graph/model.py` for `GraphModel` and private graph record writers.
- `ea_node_editor/graph/project_state.py` for `ProjectData`.
- `ea_node_editor/graph/workspace_state.py` for `WorkspaceData`, `WorkspaceSnapshot`, and `ViewState`.
- `ea_node_editor/graph/records.py` for `NodeInstance` and `EdgeInstance`.
- `ea_node_editor/graph/record_payloads.py` for node/edge mapping codecs.
- `ea_node_editor/graph/fragment_payloads.py` for clipboard/fragment payload normalization and validation.
- `ea_node_editor/graph/invariant_kernel.py` for graph-local edge compatibility, exposed-port, capacity, and registry edge checks.
- `ea_node_editor/graph/registry_normalization.py` for project/workspace normalization against the active node registry.
- `ea_node_editor/graph/node_port_state.py` for pure Script Apply and registry-load port-state projections; caller-specific settings-group and wire policies stay outside this owner.
- `ea_node_editor/graph/registry_compatibility.py` for read-only open-session registry replacement checks.
- `ea_node_editor/graph/property_validation.py` for saved/default property validation shared by reload safety and Python Script Apply.
- `ea_node_editor/graph/validated_mutation.py` for registry-backed node, edge, endpoint reassignment, Python Script Apply, dynamic-port insert/remove/rename, property, parent, exposed-port, and view-filter mutations.
- `ea_node_editor/graph/record_mutation_ops.py` for record-level graph edits that intentionally use private `GraphModel` record writers.
- `ea_node_editor/graph/workspace_view_ops.py` for workspace view lifecycle and camera-state mutations.
- `ea_node_editor/graph/group_backdrop_mutation_ops.py` for group-backdrop wrapping transactions.
- `ea_node_editor/graph/ids.py` for generated graph/project/workspace/view IDs.
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/graph/type_forwarding.py` for immutable topology-derived source contracts and all-member compatibility.
- `ea_node_editor/graph/edge_rewire.py` for prepared read-only batch endpoint proposals shared by preview and mutation.
- `ea_node_editor/graph/hierarchy.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/transform_layout_ops.py`
- `ea_node_editor/graph/transform_tidy_layout.py` for the pure Tidy layout (layered auto-layout from the wires, in-place clean-up, group refit) over plain `TidyItem` / `TidyWire` data; `tests/test_transform_tidy_layout.py` owns it.
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/graph/transform_grouping_ops.py`
- `ea_node_editor/graph/group_backdrop_geometry.py`
- `scripts/benchmark_graph_node_reconciliation.py` for source-selected 100/1,200-node mutation baselines with reset outside timing and separate copy/resolution/pruning counters.
- `tests/test_plot_graph_ownership_benchmarks.py` for measurement source isolation and counter integrity.
- `tests/graph_mutation_fixtures.py` for shared dynamic-port registry construction without assertions.
- `tests/test_graph_node_reconciliation.py` for direct Script Apply/dynamic/property mutation, sparse state, and Script/load policy differences.
- `tests/test_graph_registry_normalization.py` for load normalization, idempotency, dynamic labels, and effective-port memo reuse.
- `tests/test_python_script_scene_integration.py` for real scene actions, history, and settings payloads; parser-only checks remain in `tests/test_python_script_declaration.py`.

## Do Not Start Here
- UI bridge code when the invariant belongs in graph.
- Public raw-write helpers; use graph-owned mutation paths.

## Common Changes
- Preserve graph independence from UI and persistence implementation details.
- Registry replacement uses `check_registry_compatibility(...)` as a read-only reload-safety gate; it must never call destructive registry normalization. It checks every open workspace, effective port, incident edge, saved/default property, persistence/sensitivity field, and candidate-catalog carrier while preserving project/workspace revisions and dirty state.
- Import graph state from the focused owner modules instead of using `ea_node_editor.graph.model` as a catch-all; `graph/model.py` owns `GraphModel` only.
- Import graph normalization behavior from the focused owner modules; the retired `graph/normalization.py` path is not an internal compatibility surface.
- Use focused graph mutation modules and private model record writers consistently; `WorkspaceMutationService` is retired.
- Parent topology is a graph-domain invariant. Use `hierarchy.py` parent helpers through validated mutation, private record writers, workspace sanitization, and fragment insertion so self-parents, missing parents, and parent cycles do not enter workspace state.
- `EdgeInstance.enabled` and `input_order` are durable graph state. Normal data drops validate first and atomically replace every edge at the target input; Shift-drop appends in persisted order; exact duplicates are no-ops. Disabled edges stay connected, selectable, ordered, serialized, and undoable while contributing no dependency or value.
- Endpoint rewiring is graph-owned and atomic in `ValidatedGraphMutation.rewire_edges`: move or disconnect an ordered existing-edge batch while preserving each moved edge's identity, state, metadata, and unaffected ordering. A copy is accepted only for one selected edge and creates one new edge while preserving the original. `request_rewire_edges(...)` owns the one-step history boundary; replacement/append does not compose public remove-plus-add calls.
- Active input defaults are spec-declared and stored only in `NodeInstance.properties`; graph records carry no active-port lock or second default state. `ViewState.hide_optional_ports` remains view-local, while `hide_locked_ports` is retired.
- `NodeRegistry.data_types.compatibility(...)` is the single semantic data-port authority. `effective_ports.port_compatibility(...)` returns its structured result plus kind/flow reasons; `ports_compatible(...)` is only the Boolean adapter. The full target primary/accepted union chooses exact assignment, parent/interface assignment, direct conversion, runtime check, first unresolved, then incompatible, retaining declaration-order ties. Data edges still accept `assignable`, `convertible`, and `runtime_check`; they reject `incompatible` and `unresolved`. The graph never performs conversion. Flow ports bypass semantic typing after the structural kind check. Derived subnode/grouping ports preserve the union and exact type-ID casing.
- `GraphTypeResolver` snapshots declarations and enabled topology; `source_contract()` keeps possible output types separate from declared runtime ports and input accepted alternatives. It follows explicit `type_from_input` relationships and Any subnode mappings, preserving typed boundary authority, disconnected declared defaults, and deterministic cycle handling without node execution or cached-value inference. `source_port_compatibility()` requires every source member to satisfy the existing catalog relation.
- Forwarding edits prune newly incompatible downstream wires within the initiating history action. Rebuild inferred facts after topology, semantic properties/dynamic ports, registry, and history changes; derived types never enter project documents.
- `ValidatedGraphMutation.prepare_rewire_edges()` creates one `PreparedEdgeRewire` per candidate batch. `GraphTypeResolver.with_input_connections()` shares base declarations/topology and lazily resolves proposal ancestor closures, avoiding full-graph construction per hover candidate. Commit prepares a fresh session and uses the same proposal gate.
- Current-registry load normalization prunes newly incompatible edges in memory and marks the workspace dirty without writing the source file. `tests/serializer/round_trip_cases.py` proves Geometry Group-to-File Write pruning while JsonValue-to-File Write, Force-to-ILoad, and intentional Any edges remain; explicit save alone updates disk.
- Registry-backed add, endpoint rewire, edge re-enable, dynamic-output edits, semantic property changes, and fragment insertion preflight resolved catalog IDs before writing. `GraphInteractions.rewire_edges(...)` also runs port-availability preflight for every proposed new connection before it reaches graph mutation. Fragment preflight covers every resolved data port, including edge-free dynamic ports; flow ports are not catalog-validated as data. Bulk edge-enable preflights the whole requested batch against a temporary edge view before changing records or history. Failed mutations leave graph state, fan-in order, revision, and history unchanged. Semantic port changes prune newly invalid incident and downstream forwarding edges; registry normalization and registry-backed compilation prune incompatible or unresolved edges.
- `NodeInstance.port_modifiers` stores sparse per-port Graft/Flatten/Simplify/Reverse/Clean state and `principal_input_port_id` stores one mutually exclusive eligible input. Route these, edge Enable, and generic dynamic-port insert/remove/rename through validated record mutation/history. Toggling an inner subnode-pin edge expands upward through matching shell-port edge segments, including nested shells, within the same validation and history action. Dynamic mutations alone write ordered backing properties: they preflight node-owned resolvers and key callbacks, preserve unchanged stable keys and state, and prune removed, structurally renamed, or incompatible keys with incident wires and sparse per-port state. Direct backing-property writes are rejected; label rename preserves the stable key and wires.
- `ValidatedGraphMutation.apply_python_script(...)` owns one candidate-first Apply action for `core.python_script`. Resolve the source before writing, then reconcile ordinary settings, resolved ports, per-port state, wires, and `expanded_settings_group_ids` together. A failed parse or validation leaves the existing applied node untouched; one successful Apply is one undo/redo entry.
- `node_port_state.py` returns detached port-state dictionaries without registry resolution, graph copies, edge traversal, or writes. Apply preserves authored modifier order and resets semantic changes; load normalization canonicalizes modifiers and dynamic label permissions. Only data-access changes force compatible wires to be removed; other semantic changes use kernel compatibility.
- Property entry points retain singular/bulk normalization and return contracts, then share `_commit_normalized_property_updates`. Dynamic entry points validate before `_commit_dynamic_port_keys`, preserving incident-edge removal, backing-property write, removed-key cleanup, and downstream pruning order. Source-backed Script edits route through one atomic Apply.
- Source-backed dynamic groups preflight their property editor against the candidate resolved spec. Python Script handle edits commit through the same atomic Apply action; generic backing-property writes remain restricted to validated dynamic mutations.
- `NodeInstance.expanded_settings_group_ids` stores ordered per-node expansion state for spec-declared named settings groups. Registry normalization removes unknown IDs and restores declaration order; node mappings and graph fragments preserve the tuple. Presentation moves grouped input anchors without changing their real port identities or edges.
- `NodeInstance.locked` is graph-owned authored state for `passive.*` canvas objects. Record mutation/history owns changes; node mappings and graph fragments preserve it. It is separate from the removed active-port lock state and the missing-add-on `locked_state` payload.
- `NodeInstance.visual_style` is passive-only authored state. Validated insertion and fragment paste clear it for registered active and `compile_only` types; unresolved types retain it so unavailable nodes can round-trip until their real type is known.
- Node links are ordered durable node records. Use graph-owned upsert/remove/move mutation operations so ordering, history replay, persistence, and node payload projection stay aligned. Node links keep string `target` while carrying explicit `target_workspace_id` and `target_node_id` for cross-workspace jumps.
- Optimization Parameter/Response Setup-to-Pool relationships are exact semantic roles on those same persisted node links. They remain ordinary graph state and mutation/history records; runtime ordering is a downstream execution projection, not a second graph relationship store.
- `WorkspaceData.mutation_revision` is runtime-only state for history snapshot memoing. Bump it from graph/view mutation boundaries and snapshot restore paths; keep it out of `WorkspaceSnapshot` equality and persistence documents.
- `ProjectData.project_document_revision` is runtime-only state for autosave document-epoch gating. Bump it for project metadata, workspace order, active-workspace, and workspace create/duplicate/close changes; combine it with each workspace's document epoch part instead of reusing run-state epochs.
- `RegistryValidationPassMemo` is scoped to one registry-validation pass. Use it from prune/validation loops to reuse resolved node views, effective-port lookups, and edge tuples; invalidate the edge tuple immediately when a prune pass removes an edge.
- Keep transform and hierarchy tests focused before running broader UI gates.
- `transform_tidy_layout.py` stays UI-free: callers pass port sides and anchor offsets as plain data. It lays out one level at a time (groups deepest first, then the top level) in a left-to-right frame; top-to-bottom transposes each level in and out, so keep the two directions one code path. Rows are assigned per column by desired row first (then drawn position), and the cell directly below a node is reserved for its first same-column branch child, so a decision's second branch never has another node between it and the decision. Straightening reuses `transform_layout_ops.build_port_alignment_offsets` (also behind Straighten Connections). Group blocks move as units, so a wire into a nested member is straightened with that member's real port offset. The level is then shifted back to its anchored top-left, so a repeated Tidy is a no-op, and the straightening is discarded when it would create an overlap. In-place clean-up groups rows and columns by overlap with their first item (at least half the smaller size) rather than by centre distance, so mixed-height shapes stay in one row. It measures gaps between cells (median centre ± half the largest size), so straightening cannot make reruns creep. Results are deterministic under shuffled input.
- `transform_layout_ops.build_collision_avoidance_position_updates` is the several-blocker collision solver (Tidy's neighbour push and obstacle clearing); `build_expand_collision_avoidance_position_updates` is its single-blocker case. When the nearest-blocker steps bounce between blockers, `_separate_from_bounds` falls back to the smallest single-axis move that clears all of them.

## Focused Verification
- Forwarding and rewire ownership: `tests/test_type_forwarding.py`, `tests/test_type_forwarding_integration.py`, and `tests/test_rewire_validation.py`.
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_transform_layout_ops.py tests/test_transform_tidy_layout.py tests/test_workspace_manager.py tests/test_port_availability.py tests/test_default_port_values.py tests/test_group_backdrop_contracts.py --ignore=venv -q
.\venv\Scripts\python.exe -m unittest tests.graph_track_b.scene_model_graph_model_suite -q
.\venv\Scripts\python.exe -m pytest tests/test_dataflow_graph_persistence.py tests/test_data_tree_ui.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_type_enforcement.py tests/test_data_type_catalog.py tests/test_registry_validation.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_graph_node_reconciliation.py tests/test_graph_registry_normalization.py tests/test_python_script_scene_integration.py tests/test_registry_compatibility.py --ignore=venv -q
```

## Breadcrumbs
- [Nested Node Categories, Subnodes, And Grouping](../feature_routes/nested_node_categories_subnodes_grouping.md)
- [Group Backdrops, Peek, And Membership](../feature_routes/group_backdrops_peek_membership.md)
- [Clipboard, Undo, Redo, And Mutation History](../feature_routes/clipboard_undo_redo_mutation_history.md)
- [Plotter Nodes](../feature_routes/plotter_nodes.md)
- [Durable Node Linking](../feature_routes/durable_node_linking.md)

## Update Triggers
Update when forwarding inference, batched rewire validation, domain invariants, ordered/enabled edge state, data-port modifiers or Principal, dynamic-port declarations/resolution/mutations, registry normalization, validated mutation, record mutation ops, durable or semantic node link records, workspace view mutation ops, fragment payloads, mutation boundaries, hierarchy rules, transforms, effective-port logic, graph state module ownership, or project data ownership changes.

## 2026-07-11 Performance Ownership

- Registry normalization owns one invocation-scoped `GraphInvariantKernel` and `RegistryValidationPassMemo`; `effective_ports_for(...)` shares materialized ports between state projection and pruning. Prune-time edge removal invalidates the memo immediately. `tests/test_registry_validation.py` and `tests/test_graph_registry_normalization.py` own reuse and invalidation parity.
