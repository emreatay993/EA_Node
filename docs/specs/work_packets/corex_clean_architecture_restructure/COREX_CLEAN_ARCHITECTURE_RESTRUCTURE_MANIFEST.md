# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE Work Packet Manifest

- Date: 2026-04-24
- Integration base: `main`
- Published packet window: `P00` through `P12`
- Scope baseline: behavior-preserving clean architecture restructure layered on top of the completed COREX no-legacy cleanup contracts.
- Review baseline: existing no-legacy guardrails, package import direction tests, packet validator, packet-local review gates, and packet wrap-up artifacts.

## Requirement Anchors

- `ARCHITECTURE.md`: startup flow, shell/scene boundary ownership, graph action entry-point ownership, data contracts, and enforced architecture rules.
- `docs/specs/requirements/10_ARCHITECTURE.md`: `REQ-ARCH-002`, `REQ-ARCH-004`, `REQ-ARCH-006`, `REQ-ARCH-007`, `REQ-ARCH-008`, `REQ-ARCH-010`, `REQ-ARCH-011`, `REQ-ARCH-012`, `REQ-ARCH-013`, `REQ-ARCH-014`, `REQ-ARCH-015`, `REQ-ARCH-016`.
- `docs/specs/requirements/20_UI_UX.md`: `REQ-UI-001`, `REQ-UI-016`, `REQ-UI-017`, `REQ-UI-018`, `REQ-UI-020`, `REQ-UI-023`, `REQ-UI-032`.
- `docs/specs/requirements/30_GRAPH_MODEL.md`: `REQ-GRAPH-003`, `REQ-GRAPH-006`, `REQ-GRAPH-010`, `REQ-GRAPH-012`, `REQ-GRAPH-016`, `REQ-GRAPH-020`.
- `docs/specs/requirements/40_NODE_SDK.md` and `45_NODE_EXECUTION_MODEL.md`: `REQ-NODE-001`, `REQ-NODE-002`, `REQ-NODE-003`, `REQ-NODE-016`, `REQ-NODE-018`, `REQ-NODE-023`, `REQ-NODE-025`, `REQ-NODE-026`.
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`: `REQ-EXEC-001`, `REQ-EXEC-002`, `REQ-EXEC-003`, `REQ-EXEC-009`, `REQ-EXEC-010`, `REQ-EXEC-013`.
- `docs/specs/requirements/60_PERSISTENCE.md`: `REQ-PERSIST-001`, `REQ-PERSIST-004`, `REQ-PERSIST-005`, `REQ-PERSIST-008`, `REQ-PERSIST-011`, `REQ-PERSIST-012`, `REQ-PERSIST-015`, `REQ-PERSIST-016`, `REQ-PERSIST-020`, `REQ-PERSIST-023`.
- `docs/specs/requirements/80_PERFORMANCE.md` and `90_QA_ACCEPTANCE.md`: `REQ-PERF-004`, `REQ-PERF-006`, `REQ-PERF-007`, `REQ-QA-008`, `REQ-QA-014`, `REQ-QA-017`, `REQ-QA-021`, `REQ-QA-023`, `REQ-QA-042`.

## Retained Packet Order

1. `P00_bootstrap`: publish packet docs, status ledger, and index registration.
2. `P01_runtime_contracts`: make runtime contracts passive and process-neutral.
3. `P02_graph_domain_mutation`: centralize graph mutation and graph-state invariants.
4. `P03_workspace_custom_workflows`: isolate workspace authority and workflow identity rules.
5. `P04_current_schema_persistence`: narrow authored document, artifact, and session persistence boundaries.
6. `P05_shell_composition`: reduce `ShellWindow` and shell state modules to host/adapters.
7. `P06_qml_shell_roots`: make shell-level QML ports explicit and reduce `shellContext` reach.
8. `P07_qml_graph_canvas_core`: make graph canvas and graph-scene ports feature-owned.
9. `P08_passive_viewer_overlays`: split passive media, viewer session, fullscreen, and overlay presentation services.
10. `P09_nodes_sdk_registry`: make node SDK, descriptor, registry, and taxonomy ownership explicit.
11. `P10_plugin_addon_descriptor`: split add-on enablement/hot-apply from node discovery and validation.
12. `P11_cross_cutting_services`: promote preferences, themes, telemetry/status, and presentation services.
13. `P12_docs_traceability_closeout`: update architecture docs, QA matrix, traceability, and public API notes.

## Branch Labels

- `P01`: `codex/corex-clean-architecture-restructure/p01-runtime-contracts`
- `P02`: `codex/corex-clean-architecture-restructure/p02-graph-domain-mutation`
- `P03`: `codex/corex-clean-architecture-restructure/p03-workspace-custom-workflows`
- `P04`: `codex/corex-clean-architecture-restructure/p04-current-schema-persistence`
- `P05`: `codex/corex-clean-architecture-restructure/p05-shell-composition`
- `P06`: `codex/corex-clean-architecture-restructure/p06-qml-shell-roots`
- `P07`: `codex/corex-clean-architecture-restructure/p07-qml-graph-canvas-core`
- `P08`: `codex/corex-clean-architecture-restructure/p08-passive-viewer-overlays`
- `P09`: `codex/corex-clean-architecture-restructure/p09-nodes-sdk-registry`
- `P10`: `codex/corex-clean-architecture-restructure/p10-plugin-addon-descriptor`
- `P11`: `codex/corex-clean-architecture-restructure/p11-cross-cutting-services`
- `P12`: `codex/corex-clean-architecture-restructure/p12-docs-traceability-closeout`

## Worker Agent Defaults

- Implementation and remediation workers: `gpt-5.5` with `xhigh`
- Non-editing exploration: `gpt-5.4-mini` with `xhigh` by default
- Spark exploration: `gpt-5.3-codex-spark` with `xhigh` only for one exact lookup in a known area
- Spawn all executor workers with `fork_context=false`; pass packet docs, branch labels, worktree paths, and narrow scopes instead of prior-chat history.

## Locked Defaults

- Preserve current `.sfe` behavior, descriptor-first plugins, runtime snapshots, typed viewer transport, launch path, menu labels, shortcuts, and QML affordances.
- Do not reopen the completed `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP` baseline unless a packet explicitly owns that contract change.
- Treat active user work around comment popover and embedded viewer overlays as user-owned state that must be inspected and preserved.
- Use the project venv in packet verification: `.\venv\Scripts\python.exe` on PowerShell or `./venv/Scripts/python.exe` in bash/WSL.
- Add `--ignore=venv` to direct `pytest` commands intended for packet worktrees.

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

## Recommended Fresh-Thread Executor Groups

- Thread 1: waves 1-3 (`P01` through `P03`)
- Thread 2: wave 4 (`P04`)
- Thread 3: wave 5 (`P05`)
- Thread 4: waves 6-7 (`P06` through `P07`)
- Thread 5: wave 8 (`P08`)
- Thread 6: waves 9-12 (`P09` through `P12`)

These groups keep heavy shell/QML/viewer work in separate fresh contexts while avoiding one top-level executor thread carrying all packet transcripts.

## Retained Handoff Artifacts

- `PLANS_TO_IMPLEMENT/in_progress/COREX Clean Architecture Restructure.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_MANIFEST.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_STATUS.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_Pxx_*.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_Pxx_*_PROMPT.md`

## Standard Thread Prompt Shell

Read `COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_MANIFEST.md`, `COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_STATUS.md`, and the target packet spec before editing. Implement exactly the target packet, run its full `Verification Commands`, run its `Review Gate` when not `none`, create the packet wrap-up artifact, commit packet-local changes on the packet branch, update the shared status ledger only when acting as a standalone packet runner, and stop after that packet.
