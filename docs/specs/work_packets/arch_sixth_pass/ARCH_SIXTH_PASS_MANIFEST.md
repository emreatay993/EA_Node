# ARCH_SIXTH_PASS Work Packet Manifest

- Date: `2026-03-20`
- Scope baseline: sequential residual-architecture cleanup follow-up after `ARCH_FIFTH_PASS` and an eight-subagent repo review, preserving exact user-facing behavior while removing remaining compatibility adapters, clarifying ownership boundaries, and aligning verification/docs with the current bridge-first and runtime-snapshot architecture.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Node Execution Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/45_NODE_EXECUTION_MODEL.md)
  - [Execution Engine](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/50_EXECUTION_ENGINE.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [Performance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/80_PERFORMANCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
  - [Traceability Matrix](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/TRACEABILITY_MATRIX.md)
- Runtime baseline:
  - `ea_node_editor/ui/shell/composition.py` still assembles and injects the shell object graph through reflective bootstrap bundles.
  - `ea_node_editor/ui/shell/window.py` and `ea_node_editor/ui/shell/presenters.py` still carry broad passthrough and compatibility surfaces.
  - `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`, and `ea_node_editor/ui_qml/components/GraphCanvas.qml` still preserve a compatibility-heavy canvas bridge surface even though raw context globals are gone.
  - `ea_node_editor/graph/transforms.py` and `ea_node_editor/ui_qml/graph_scene_mutation_history.py` still keep complex authoring rewrites outside the primary validated mutation boundary.
  - `ea_node_editor/execution/runtime_snapshot.py`, `ea_node_editor/execution/client.py`, `ea_node_editor/execution/protocol.py`, `ea_node_editor/execution/worker.py`, and `ea_node_editor/persistence/session_store.py` still carry `project_doc` fallback or document-centric transport seams.
  - `ea_node_editor/persistence/overlay.py`, `ea_node_editor/graph/model.py`, and `ea_node_editor/persistence/project_codec.py` still keep persistence-only overlay ownership attached to live workspace objects through compatibility properties and weakref sidecars.
  - `ea_node_editor/nodes/plugin_loader.py`, `ea_node_editor/nodes/package_manager.py`, and `ea_node_editor/ui/shell/controllers/workspace_io_ops.py` still couple plugin/package discovery and export to import-time execution and registry internals.
  - `ea_node_editor/workspace/manager.py` and `ea_node_editor/graph/model.py` still split workspace lifecycle authority.
  - `scripts/run_verification.py`, `scripts/check_traceability.py`, `tests/main_window_shell/base.py`, and `ARCHITECTURE.md` still encode shell-lifetime isolation and some stale architecture claims.

## Packet Order (Strict)

1. `ARCH_SIXTH_PASS_P00_bootstrap.md`
2. `ARCH_SIXTH_PASS_P01_shell_bootstrap_contract.md`
3. `ARCH_SIXTH_PASS_P02_shell_window_facade_contraction.md`
4. `ARCH_SIXTH_PASS_P03_shell_contract_hardening.md`
5. `ARCH_SIXTH_PASS_P04_canvas_contract_completion.md`
6. `ARCH_SIXTH_PASS_P05_graph_authoring_transaction_core.md`
7. `ARCH_SIXTH_PASS_P06_workspace_state_history_boundary.md`
8. `ARCH_SIXTH_PASS_P07_workspace_lifecycle_authority.md`
9. `ARCH_SIXTH_PASS_P08_execution_boundary_hardening.md`
10. `ARCH_SIXTH_PASS_P09_persistence_overlay_ownership.md`
11. `ARCH_SIXTH_PASS_P10_plugin_package_provenance_hardening.md`
12. `ARCH_SIXTH_PASS_P11_shell_verification_lifecycle_hardening.md`
13. `ARCH_SIXTH_PASS_P12_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/arch-sixth-pass/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Shell Bootstrap Contract | `codex/arch-sixth-pass/p01-shell-bootstrap-contract` | Replace reflective shell bootstrap wiring with an explicit composition contract |
| P02 ShellWindow Facade Contraction | `codex/arch-sixth-pass/p02-shell-window-facade-contraction` | Shrink `ShellWindow` and the shell presenter surface toward a real host facade |
| P03 Shell Contract Hardening | `codex/arch-sixth-pass/p03-shell-contract-hardening` | Replace soft bridge/controller fallback dispatch with explicit shell-facing contracts |
| P04 Canvas Contract Completion | `codex/arch-sixth-pass/p04-canvas-contract-completion` | Remove the broad `GraphCanvasBridge` compatibility layer and finish the state/command bridge split |
| P05 Graph Authoring Transaction Core | `codex/arch-sixth-pass/p05-graph-authoring-transaction-core` | Move complex graph rewrites onto a graph-owned authoring transaction boundary |
| P06 Workspace State And History Boundary | `codex/arch-sixth-pass/p06-workspace-state-history-boundary` | Separate undo/clipboard/persistence-facing workspace state from live authoring orchestration |
| P07 Workspace Lifecycle Authority | `codex/arch-sixth-pass/p07-workspace-lifecycle-authority` | Make `WorkspaceManager` the single public authority for workspace lifecycle flows |
| P08 Execution Boundary Hardening | `codex/arch-sixth-pass/p08-execution-boundary-hardening` | Make `RuntimeSnapshot` the only packet-owned run payload contract |
| P09 Persistence Overlay Ownership | `codex/arch-sixth-pass/p09-persistence-overlay-ownership` | Replace weakref-style overlay ownership and narrow autosave/session persistence boundaries |
| P10 Plugin Package Provenance Hardening | `codex/arch-sixth-pass/p10-plugin-package-provenance-hardening` | Make plugin/package metadata and provenance explicit without import-time registry poking |
| P11 Shell Verification Lifecycle Hardening | `codex/arch-sixth-pass/p11-shell-verification-lifecycle-hardening` | Consolidate shell-backed verification around one honest fresh-process contract |
| P12 Docs And Traceability Closeout | `codex/arch-sixth-pass/p12-docs-traceability-closeout` | Close the packet set with aligned architecture docs, QA evidence, and traceability updates |

## Locked Defaults

- Preserve exact user-facing behavior, UI/UX, runtime semantics, and current-schema `.sfe` behavior throughout this packet set.
- This packet set is cleanup and contract hardening only. No intentional new end-user features are allowed.
- Prefer explicit protocols, factories, and authoritative services over reflective host mutation, `getattr` or `_invoke` fallback dispatch, or broad compatibility adapters when packet scope permits.
- Do not remove a compatibility surface until all packet-owned callers, tests, and docs are migrated in the same or earlier packet.
- Use the project venv for verification commands: `./venv/Scripts/python.exe`.
- Execution waves are authoritative and strictly sequential for this packet set.
- Target merge branch defaults to `main`.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

### Wave 5
- `P05`

### Wave 6
- `P06`

### Wave 7
- `P07`

### Wave 8
- `P08`

### Wave 9
- `P09`

### Wave 10
- `P10`

### Wave 11
- `P11`

### Wave 12
- `P12`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `ARCH_SIXTH_PASS_Pxx_<name>.md`
- Implementation prompt: `ARCH_SIXTH_PASS_Pxx_<name>_PROMPT.md`
- Status ledger update in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md):
  - branch label
  - accepted commit sha
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement ARCH_SIXTH_PASS_PXX_<name>.md exactly. Before editing, read ARCH_SIXTH_PASS_MANIFEST.md, ARCH_SIXTH_PASS_STATUS.md, and ARCH_SIXTH_PASS_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, runtime semantics, and current-schema \`.sfe\` behavior, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the packet wrap-up, update ARCH_SIXTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must tell the agent to run the full `Verification Commands`, run the packet `Review Gate` when it is not `none`, create the packet wrap-up, update the shared status ledger, and stop after that packet.
- `P00` is documentation-only. `P01` through `P12` may change source, test, script, and docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Prefer the narrowest stable verification slice that proves the packet. Do not substitute repo-wide workflows for narrower packet-owned proof unless the packet explicitly requires the broader gate.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
