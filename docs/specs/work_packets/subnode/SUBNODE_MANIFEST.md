# Subnode Work Packet Manifest

- Date: `2026-03-08`
- Scope baseline: nested subnode containers, scope navigation, and project-local custom workflow snapshots for the graph workspace
- Canonical requirements: [docs/specs/INDEX.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node Execution Model](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/45_NODE_EXECUTION_MODEL.md)
  - [Persistence](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
- Runtime baseline: schema `3` persistence support for `ViewState.scope_path` and `metadata.custom_workflows` is present after `P01`; no subnode runtime/UI behavior exists yet.

## Packet Order (Strict)

1. `SUBNODE_P00_bootstrap.md`
2. `SUBNODE_P01_hierarchy_persistence.md`
3. `SUBNODE_P02_dynamic_port_resolution.md`
4. `SUBNODE_P03_scope_navigation.md`
5. `SUBNODE_P04_group_and_ungroup.md`
6. `SUBNODE_P05_hierarchy_graph_ops.md`
7. `SUBNODE_P06_pin_editing_ux.md`
8. `SUBNODE_P07_execution_compiler.md`
9. `SUBNODE_P08_custom_workflow_library.md`
10. `SUBNODE_P09_import_export_qa.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/subnode/p00-bootstrap` | Save the packet set into the repo and register it in the spec index |
| P01 Hierarchy Persistence | `codex/subnode/p01-hierarchy-persistence` | Add schema v3 persistence for scope paths and custom workflows |
| P02 Dynamic Port Resolution | `codex/subnode/p02-dynamic-port-resolution` | Introduce subnode shell/pin types and one shared effective-port resolver |
| P03 Scope Navigation | `codex/subnode/p03-scope-navigation` | Make the canvas scope-aware and add breadcrumb navigation |
| P04 Group And Ungroup | `codex/subnode/p04-group-and-ungroup` | Group visible same-scope selections into subnodes and reverse them |
| P05 Hierarchy Graph Ops | `codex/subnode/p05-hierarchy-graph-ops` | Retrofit duplicate, clipboard, search, layout, and focus behavior for hierarchy |
| P06 Pin Editing UX | `codex/subnode/p06-pin-editing-ux` | Expose subnode pin nodes in the library and inspector |
| P07 Execution Compiler | `codex/subnode/p07-execution-compiler` | Flatten nested subnodes into the existing execution model at run time |
| P08 Custom Workflow Library | `codex/subnode/p08-custom-workflow-library` | Add project-local custom workflow publishing and placement |
| P09 Import Export QA | `codex/subnode/p09-import-export-qa` | Add `.eawf` import/export and close the roadmap with QA/traceability |

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `SUBNODE_Pxx_<name>.md`
- Implementation prompt: `SUBNODE_Pxx_<name>_PROMPT.md`
- Status ledger update in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md):
  - branch label
  - commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Packet Template Rules

- Every packet spec must include: objective, preconditions, target subsystems, required behavior, non-goals, verification commands, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Do not start packet `N+1` before packet `N` is marked `PASS` in the status ledger.
- `P00` is documentation-only. `P01` changes persistence/data-model code only. `P02` through `P09` may change runtime/UI/execution behavior, but each thread must implement exactly one packet.
- Keep hierarchy traversal and scope helpers in dedicated graph modules rather than QML/controller ad hoc logic.
- Keep effective-port resolution centralized once introduced in `P02`; later packets must reuse it.
- Keep custom workflow persistence in `ea_node_editor/custom_workflows/*`; do not fold it into the node package manager.
