# Add-On Manager Backend Preparation QA Matrix

- Updated: `2026-04-20`
- Packet set: retained `ADDON_MANAGER_BACKEND_PREPARATION` (`P01` through `P08`)
- Scope: final closeout matrix for the generic add-on catalog and apply-policy model, Add-On Manager shell surface, locked missing-add-on placeholder behavior, repo-local ANSYS DPF add-on lifecycle, and retained docs or traceability evidence.

## Locked Scope

- `Add-On Manager` remains the top-level menubar entry and the shipped manager stays the Variant 4 inspector-style right drawer rather than a settings-only flow or another mockup variant.
- Missing add-on nodes remain visible on the canvas as locked placeholders. They keep the normal node silhouette, Mockup B locked chrome, add-on requirement affordances, and read-only interaction boundaries instead of disappearing into persistence-only state.
- Add-ons publish one apply policy each: `hot_apply` for node and library style add-ons and `restart_required` for cross-cutting features. Restart-required add-ons may persist pending state and surface restart messaging, but this closeout does not claim true in-session unload for them.
- ANSYS DPF is the first repo-local `hot_apply` reference add-on. Toggling it rebuilds registry and runtime state, invalidates viewer and worker caches, and lets missing-node projection move between live DPF nodes and locked placeholders without widening into marketplace or discovery work.
- The packet closeout is docs-and-proof only. It does not reopen runtime, QML, or DPF implementation beyond the retained `P01` through `P07` packet evidence and the exact `P08` traceability or markdown commands below.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Generic add-on contract, apply-policy state model, and persisted enabled or pending-restart settings | `P01` | `REQ-PERSIST-023`, `REQ-INT-011`, `REQ-QA-040` | `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py --ignore=venv -q` | PASS in `docs/specs/work_packets/addon_manager_backend_preparation/P01_addon_contracts_and_state_model_WRAPUP.md` (`f3ed4af0c7d026bb1d4a940bd2b9665d554d7e1f`) |
| Top-level Add-On Manager menubar entry, shell open-request plumbing, and focus-target preservation | `P02` | `REQ-UI-041`, `REQ-INT-011`, `REQ-QA-040` | `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_basics_and_search.py --ignore=venv -q` | PASS in `docs/specs/work_packets/addon_manager_backend_preparation/P02_addon_manager_entry_and_open_request_plumbing_WRAPUP.md` (`0bf01e34f3738b1928cdb944f9ce34c2f13a664f`) |
| Missing add-on placeholder projection, reopen portability, and rebind-safe serializer flow | `P03` | `REQ-PERSIST-023`, `REQ-UI-042`, `REQ-QA-040` | `.\venv\Scripts\python.exe -m pytest tests/test_serializer.py tests/test_serializer_schema_migration.py tests/test_registry_validation.py tests/test_graph_scene_bridge_bind_regression.py --ignore=venv -q` | PASS in `docs/specs/work_packets/addon_manager_backend_preparation/P03_generic_missing_addon_placeholder_projection_WRAPUP.md` (`2f41ad61d961fa875e44187364a50b409245eb99`) |
| Mockup B locked-node chrome, blocked mutation interactions, and aggregate locked-node recovery affordances | `P04` | `REQ-UI-042`, `REQ-QA-040` | `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py --ignore=venv -q` | PASS in `docs/specs/work_packets/addon_manager_backend_preparation/P04_locked_node_graph_host_and_mockup_b_visuals_WRAPUP.md` (`61c308e54e98c48b715c589b543b5b1b59190336`) |
| Repo-local ANSYS DPF add-on extraction, package-owned catalogs, and retained operator or helper docs lookup | `P05` | `REQ-INT-012`, `REQ-QA-040` | `.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_generated_helper_catalog.py tests/test_dpf_generated_operator_catalog.py tests/test_dpf_operator_help_lookup.py --ignore=venv -q` | PASS in `docs/specs/work_packets/addon_manager_backend_preparation/P05_ansys_dpf_addon_package_extraction_WRAPUP.md` (`fad1be551084ae7db07d293df5eacdf9c62da076`) |
| Hot-apply registry rebuild, DPF runtime or viewer cache invalidation, and disable-to-placeholder lifecycle plumbing | `P06` | `REQ-INT-011`, `REQ-INT-012`, `REQ-QA-040` | `./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_execution_viewer_service.py tests/test_viewer_host_service.py tests/test_dpf_viewer_node.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q` | PASS in `docs/specs/work_packets/addon_manager_backend_preparation/P06_dpf_hot_apply_registry_and_runtime_rebuild_WRAPUP.md` (`b24def0fbc0ad52a97417184616085f3f6e00309`) |
| Variant 4 Add-On Manager drawer fidelity, toggle projection, and live shell focus or selection refresh | `P07` | `REQ-UI-041`, `REQ-INT-011`, `REQ-QA-040` | `.\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py tests/main_window_shell/shell_basics_and_search.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q` | PASS in `docs/specs/work_packets/addon_manager_backend_preparation/P07_addon_manager_variant4_surface_WRAPUP.md` (`68f9aa8fe56e165967ca2a6730d9c0ec6594c526`) |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q` | Packet-owned traceability and markdown-hygiene regression for the Add-On Manager backend preparation closeout surface |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | Review-gate proof audit for the refreshed README, architecture, requirements, spec index, QA matrix, and traceability rows |
| `./venv/Scripts/python.exe scripts/check_markdown_links.py` | Local Markdown-link audit for the canonical add-on backend closeout docs and linked packet evidence |

## 2026-04-20 Execution Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q` | PASS | Packet-owned closeout tests confirmed the new QA matrix, spec-index registration, updated README and architecture guidance, retained requirement anchors, and the new traceability rows for the shipped add-on backend preparation baseline |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the add-on closeout docs, requirement lines, QA matrix, and traceability rows were refreshed in the packet worktree |
| `./venv/Scripts/python.exe scripts/check_markdown_links.py` | PASS | Canonical Markdown docs resolved to existing local targets and valid headings after the add-on QA matrix and closeout links were added |

## Remaining Manual Desktop Checks

1. Add-On Manager entry and drawer: launch the app in a normal desktop session, confirm `Add-On Manager` appears as a top-level menubar entry, open it, and close it with both the scrim and `Esc`; the expected result is the Variant 4 right drawer opens without disturbing the active workspace and the selected add-on stays focused while the existing disabled update/install/restart affordances remain visible.
2. Locked missing-add-on placeholder recovery: open a project that contains add-on-backed nodes while the corresponding add-on is unavailable; the expected result is the nodes stay visible as locked Mockup B placeholders with the `LOCKED` badge, add-on requirement ribbon, lighter `Load...` affordance, aggregate `Load missing add-ons` canvas ribbon, and blocked edit, drag, and resize interactions.
3. Placeholder persistence and rebind: save the missing-add-on project, reopen it in the same unavailable session, then reopen it again with the add-on restored; the expected result is placeholder nodes keep their saved titles, values, hidden-port state, and edges while unavailable, then rebind to live nodes without losing graph structure when the add-on returns.
4. ANSYS DPF toggle lifecycle: in an environment where `ansys.dpf.core` is installed, open `Add-On Manager`, inspect the `ANSYS DPF` entry, toggle it off and back on, and verify the node library plus any open DPF-backed graph/viewer state refresh; the expected result is hot-apply changes stay in the drawer, unavailable DPF nodes fall back to locked placeholders while disabled, and re-enabling restores live DPF availability without requiring a full app restart.

## Residual Risks

- `P08` is docs-and-proof only. It does not rerun a new broad aggregate beyond the retained packet commands and the exact closeout gates above.
- The current live catalog is intentionally narrow and still centers on ANSYS DPF as the reference add-on, so richer restart-required permutations remain represented mostly by the stable contract and UI state instead of multiple shipped add-ons.
- `Check for updates`, `Install from File...`, and restart-oriented manager actions remain intentionally disabled in the shipped Variant 4 surface pending follow-on backend work.
- Marketplace or discovery flows, true in-session unload for restart-required add-ons, and broader add-on migrations remain out of scope for this packet set.
