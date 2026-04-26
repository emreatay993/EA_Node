# V1 Classic Explorer Folder Node QA Matrix

- Updated: `2026-04-27`
- Packet set: `V1_CLASSIC_EXPLORER_FOLDER_NODE` (`P01` through `P07`)
- Scope: final closeout matrix for the shipped V1 Classic Explorer folder node, including the passive `io.folder_explorer` node contract, real-filesystem browsing service, graph-surface command bridge, QML surface, shell/library/inspector exposure, integration regressions, manual smoke directives, and final docs/proof checks.

## Locked Scope

- `io.folder_explorer` is a passive graph-visible filesystem source and browser, not an execution node.
- The node browses the real local filesystem; it is not a mocked project-only tree.
- The node persists semantic project state only, primarily `current_path`; navigation history, search text, sort column, selection, context-menu position, maximized state, tree expansion, and browse defaults remain transient UI/session state and are not written to `.sfe`.
- Windows-style filesystem mutations such as new folder, rename, delete, cut, copy, and paste route through the UI-independent filesystem service and require explicit user confirmation before mutating real files.
- Drag-out and `Send to COREX as Path Pointer` create or target `io.path_pointer` nodes rather than widening the folder explorer into a general persistence or artifact manager.
- Graph mutations stay behind existing graph scene and command-bridge mutation services; the packet set does not add public raw model-record writers or UI imports into `ea_node_editor.graph`.
- QML behavior follows the existing graph-surface host/action-router pattern and keeps surface-local browsing state out of persisted node properties.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Passive built-in `io.folder_explorer` node contract, `current_path` property, path output, runtime exclusion, and serializer round trip | `P01` | `REQ-NODE-029`, `REQ-INT-013`, `REQ-QA-043` | `.\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py tests/test_passive_runtime_wiring.py tests/test_serializer.py --ignore=venv -q` | PASS in `docs/specs/work_packets/v1_classic_explorer_folder_node/P01_node_contract_WRAPUP.md` (`723d56d86640d5b347b8cebb29f9b6eab222d372`) |
| UI-independent filesystem service, breadcrumb/list DTOs, filtering, sorting, path-copy formatting, and guarded filesystem mutations | `P02` | `REQ-INT-013`, `REQ-QA-043` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_folder_explorer_filesystem_service.py tests/test_project_artifact_store.py tests/test_project_files_dialog.py --ignore=venv -q` | PASS in `docs/specs/work_packets/v1_classic_explorer_folder_node/P02_filesystem_service_WRAPUP.md` (`2772746d62a45ab8a974b4318e272b24fad7cc5a`) |
| Graph action contract, command payload normalization, explicit confirmation seam, clipboard/open seams, and Path Pointer or new Explorer node creation routing | `P03` | `REQ-UI-043`, `REQ-INT-013`, `REQ-QA-043` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py --ignore=venv -q` | PASS in `docs/specs/work_packets/v1_classic_explorer_folder_node/P03_bridge_actions_WRAPUP.md` (`ca7f4ab511a2e86bf737fd374f85b79b673451e0`) |
| Classic Explorer passive QML surface, breadcrumb/search/sort/details/context menu rendering, drag payloads, close/maximize controls, and transient-state locality | `P04` | `REQ-UI-043`, `REQ-QA-043` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py tests/test_graph_surface_input_inline.py tests/graph_surface/passive_host_interaction_suite.py -k "folder_explorer or graph_surface" --ignore=venv -q` | PASS in `docs/specs/work_packets/v1_classic_explorer_folder_node/P04_qml_surface_WRAPUP.md` (`900e3d366590597a8db66ae69f0c8b89e031221f`) |
| Shell library discovery, inspector folder picker, surface current-path mutation route, and persistence proof that transient Explorer state is discarded | `P05` | `REQ-UI-043`, `REQ-NODE-029`, `REQ-QA-043` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_window_library_inspector.py tests/main_window_shell/passive_property_editors.py tests/test_graph_surface_input_inline.py tests/test_serializer.py --ignore=venv -q` | PASS in `docs/specs/work_packets/v1_classic_explorer_folder_node/P05_shell_inspector_library_WRAPUP.md` (`d4f1d5a5eeb54abf9a87e0babd86ff6a91004b4d`) |
| Integrated graph-surface, action-contract, shell, persistence, and confirmed-mutation regressions across the completed feature | `P06` | `REQ-UI-043`, `REQ-NODE-029`, `REQ-INT-013`, `REQ-QA-043` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py tests/test_folder_explorer_filesystem_service.py tests/test_graph_action_contracts.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py tests/test_window_library_inspector.py tests/main_window_shell/passive_property_editors.py tests/test_serializer.py --ignore=venv -q` | PASS in `docs/specs/work_packets/v1_classic_explorer_folder_node/P06_integration_tests_WRAPUP.md` (`5a9927d54e33ca9b740c3d80e330364f7f716f10`) |
| Final closeout proof, canonical QA matrix, requirement traceability, markdown links, context-budget audit, and fast verification gate | `P07` | `REQ-QA-044`, `AC-REQ-QA-044-01` | `.\venv\Scripts\python.exe scripts\run_verification.py --mode fast`; `.\venv\Scripts\python.exe scripts\check_traceability.py`; `.\venv\Scripts\python.exe scripts\check_markdown_links.py`; `.\venv\Scripts\python.exe scripts\check_context_budgets.py` | PASS in this packet: non-budget fast pytest passes, traceability and markdown checks pass, and context-budget failures are waived by user directive |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe scripts\run_verification.py --mode fast` | Final fast regression gate after the accepted P01 through P06 state and P07 docs/proof refresh |
| `.\venv\Scripts\python.exe scripts\check_traceability.py` | Proof audit for refreshed requirements, traceability rows, spec index registration, and closeout evidence |
| `.\venv\Scripts\python.exe scripts\check_markdown_links.py` | Markdown-link audit for the QA matrix, packet evidence links, and spec index registration |
| `.\venv\Scripts\python.exe scripts\check_context_budgets.py` | Context-budget proof check for retained packet and docs surfaces |
| `.\venv\Scripts\python.exe scripts\check_markdown_links.py` | P07 review gate before executor handoff |

## 2026-04-27 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe scripts\run_verification.py --mode fast` | WAIVED | Stops in `fast.context_budgets`; the user explicitly waived context-budget failures for the rest of this plan on 2026-04-27 |
| Direct non-budget fast pytest slice with context-budget guardrail deselected | PASS | `989 passed, 5 skipped, 56 warnings` |
| `.\venv\Scripts\python.exe scripts\check_traceability.py` | PASS | `TRACEABILITY CHECK PASS` after the requirements, traceability, index, and QA matrix refresh |
| `.\venv\Scripts\python.exe scripts\check_markdown_links.py` | PASS | `MARKDOWN LINK CHECK PASS` after the QA matrix and index registration landed |
| `.\venv\Scripts\python.exe scripts\check_context_budgets.py` | WAIVED | Same context-budget blocker as the fast gate, waived by user directive |
| `.\venv\Scripts\python.exe scripts\check_markdown_links.py` | PASS | P07 review gate passed after wrap-up refresh |

## Manual Test Directives

Ready for manual testing

1. Prerequisite: launch the app from this branch with `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap` in a normal desktop Qt session.
2. Library and inspector smoke: add `Folder Explorer` from `Input / Output`, select it, use the inspector `Current Path` browse control to choose a disposable folder, and expect the selected directory to persist as `current_path` on the node.
3. Browse and navigation smoke: create a temporary folder containing at least one file and one child folder, set it as `Current Path`, and expect the Classic Explorer surface to show details rows, breadcrumbs, refresh, search, and sort without mutating files.
4. Path Pointer smoke: use a row context action or drag-out flow to send a listed file or folder to COREX as a Path Pointer, and expect an `io.path_pointer` node carrying the selected path with the correct file/folder mode.
5. Confirmed mutation smoke: in a disposable temporary folder, use rename/delete or cut/paste once and accept the confirmation, then repeat once and cancel the confirmation; expect only the accepted operation to mutate the selected temp path, with sibling files untouched.
6. Persistence smoke: save and reopen the project after changing search, sort, selection, context menu state, maximized state, and navigation history; expect only `current_path` to restore while transient Classic Explorer UI state resets.

## Residual Desktop-Only Validation

- Offscreen automated tests cover command contracts, QML payloads, persistence shape, and filesystem-service behavior, but final visual balance, native folder picker behavior, and OS shell integration should still be smoke-tested in a real Windows desktop session.
- Real filesystem mutation checks must use disposable temporary folders. The packet evidence intentionally does not cover destructive operations against user data.

## Residual Risks

- Existing dependency warnings from optional Ansys DPF packages may still appear during focused or fast verification and are unrelated to the Classic Explorer folder node.
- Context-budget guardrail failures are intentionally waived for the rest of this plan.
- P07 follow-up remediation touched source and tests solely to clear closeout verification failures; retained P01 through P06 packet evidence remains the primary feature evidence.
- Future work that expands Folder Explorer into a project artifact manager, adds project-only virtual trees, or changes Path Pointer semantics requires a separate packet set.

## Packet Evidence Links

- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_MANIFEST.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P01_node_contract_WRAPUP.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P02_filesystem_service_WRAPUP.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P03_bridge_actions_WRAPUP.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P04_qml_surface_WRAPUP.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P05_shell_inspector_library_WRAPUP.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P06_integration_tests_WRAPUP.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P07_closeout_verification_WRAPUP.md`
