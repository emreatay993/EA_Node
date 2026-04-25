# V1_CLASSIC_EXPLORER_FOLDER_NODE Work Packet Manifest

- Date: `2026-04-26`
- Integration base: `main`
- Integration base revision: `9a93777c25e8e3efd79092e2df1bcccd40705e38`
- Published packet window: `P00` through `P07`
- Scope baseline: create an execution-ready packet set for the `V1 - Classic Explorer Variant` from `artifacts/design/COREX - Folder Management.zip`, implementing a real-filesystem Explorer-style folder node with navigation, breadcrumb, details list, context menu, drag/drop path-pointer creation, and confirmed Windows-style file mutations.
- Review baseline: `artifacts/design/COREX - Folder Management.zip` entries `corex-folder-management/README.md`, `corex-folder-management/project/Folder Node Variants.html`, and `corex-folder-management/project/src/variant-classic.jsx`.

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `artifacts/design/COREX - Folder Management.zip`
- `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_MANIFEST.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md`

## Retained Packet Order

1. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_bootstrap.md`
2. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P01_node_contract.md`
3. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P02_filesystem_service.md`
4. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P03_bridge_actions.md`
5. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P04_qml_surface.md`
6. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P05_shell_inspector_library.md`
7. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P06_integration_tests.md`
8. `V1_CLASSIC_EXPLORER_FOLDER_NODE_P07_closeout_verification.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/v1-classic-explorer-folder-node/p00-bootstrap` | Establish packet docs, status ledger, execution waves, and spec-index registration |
| P01 Node Contract | `codex/v1-classic-explorer-folder-node/p01-node-contract` | Add the passive built-in `io.folder_explorer` node contract, registry exposure, persistence shape, and focused domain regressions |
| P02 Filesystem Service | `codex/v1-classic-explorer-folder-node/p02-filesystem-service` | Add a testable filesystem browsing and confirmed-mutation service without UI dependencies |
| P03 Bridge Actions | `codex/v1-classic-explorer-folder-node/p03-bridge-actions` | Wire graph-surface commands, confirmations, clipboard/open-in-OS actions, and Path Pointer spawning through existing mutation boundaries |
| P04 QML Surface | `codex/v1-classic-explorer-folder-node/p04-qml-surface` | Render the V1 Classic Explorer graph surface and route it through the node-surface loader |
| P05 Shell Inspector Library | `codex/v1-classic-explorer-folder-node/p05-shell-inspector-library` | Expose the node in the library and inspector while keeping transient Explorer state out of project persistence |
| P06 Integration Tests | `codex/v1-classic-explorer-folder-node/p06-integration-tests` | Add focused graph-surface, action-contract, shell, persistence, and mutation-confirmation regressions |
| P07 Closeout Verification | `codex/v1-classic-explorer-folder-node/p07-closeout-verification` | Publish packet QA evidence, run final docs/proof checks, and close the packet set |

## Locked Defaults

- V1 browses the real local filesystem, not a mocked project-only tree.
- Windows-style commands perform real file mutations only after explicit user confirmation.
- `io.folder_explorer` is passive; it is a graph-visible filesystem source and browser, not an execution node.
- The node persists only semantic project state, primarily the selected/current folder path and stable node properties.
- Navigation history, search text, sort column, selection, context-menu position, maximized state, tree expansion, and browse defaults are transient UI/session state and must not be written to `.sfe`.
- `io.path_pointer` remains the target for drag-out and `Send to COREX as Path Pointer`.
- Graph mutation stays behind existing graph mutation services; no public raw-record write helpers are introduced.
- The filesystem service is UI-independent and testable with temporary directories.
- QML uses existing graph-surface and shell bridge patterns instead of adding global UI imports into `ea_node_editor.graph`.
- Direct packet-owned pytest commands include `--ignore=venv`; Qt/QML commands set `QT_QPA_PLATFORM=offscreen`.
- Packet workers may expand write scope only minimally, must document the reason in wrap-up, and must stop if the expansion conflicts with another active packet or shared public contract.

## Execution Waves

### Wave 1
- `P01`
- `P02`

### Wave 2
- `P03`

### Wave 3
- `P04`

### Wave 4
- `P05`

### Wave 5
- `P06`

### Wave 6
- `P07`

Executor routing note: use three fresh top-level executor threads to avoid context bloat while preserving these sequential waves. Thread 1 executes Wave 1. Thread 2 executes Waves 2 through 4 sequentially. Thread 3 executes Waves 5 through 6 sequentially. Do not parallelize `P03`, `P04`, or `P05`; their bridge, QML, shell, and inspector surfaces intentionally depend on prior packet results.

## Retained Handoff Artifacts

- Design archive: `artifacts/design/COREX - Folder Management.zip`
- Packet manifest: `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md`
- Status ledger: [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md)
- Packet specs and prompts: `V1_CLASSIC_EXPLORER_FOLDER_NODE_P00_bootstrap.md` through `V1_CLASSIC_EXPLORER_FOLDER_NODE_P07_closeout_verification_PROMPT.md`
- Packet wrap-ups: `P01_node_contract_WRAPUP.md` through `P07_closeout_verification_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/V1_CLASSIC_EXPLORER_FOLDER_NODE_QA_MATRIX.md`

## Standard Thread Prompt Shell

`Implement V1_CLASSIC_EXPLORER_FOLDER_NODE_PXX_<name>.md exactly. Before editing, read V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md, V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md, and V1_CLASSIC_EXPLORER_FOLDER_NODE_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
