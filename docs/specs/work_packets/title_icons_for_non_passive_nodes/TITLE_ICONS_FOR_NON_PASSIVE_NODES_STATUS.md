# TITLE_ICONS_FOR_NON_PASSIVE_NODES Status Ledger

- Updated: `2026-04-13`
- Integration base: `main`
- Published packet window: `P00` through `P05`
- Execution note: use the manifest `Execution Waves` as the authoritative parallelism contract. Later waves remain blocked until every packet in the current wave reaches a terminal result.

| Packet | Branch Label | Status | Commit SHA | Commands | Tests | Artifacts | Residual Risks |
|---|---|---|---|---|---|---|---|
| P00 Bootstrap | `codex/title-icons-for-non-passive-nodes/p00-bootstrap` | PASS | `67c74c5d27d5a2a82a05bd15c17e70acd03b8219` | planner: `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_FILE_GATE_PASS`; planner review gate: `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_STATUS_PASS` | PASS (`TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_FILE_GATE_PASS`; `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_STATUS_PASS`) | `docs/specs/INDEX.md`, `docs/specs/work_packets/title_icons_for_non_passive_nodes/*` | Accepted bootstrap docs are committed on `main`; later packet waves remain pending and unexecuted |
| P01 Path Resolver and Payload Contract | `codex/title-icons-for-non-passive-nodes/p01-path-resolver-and-payload-contract` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/title_icons_for_non_passive_nodes/P01_path_resolver_and_payload_contract_WRAPUP.md` | Blocked until execution starts |
| P02 Icon Size Preferences and Bridge | `codex/title-icons-for-non-passive-nodes/p02-icon-size-preferences-and-bridge` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/title_icons_for_non_passive_nodes/P02_icon_size_preferences_and_bridge_WRAPUP.md` | Blocked until execution starts |
| P03 QML Header Icon Rendering | `codex/title-icons-for-non-passive-nodes/p03-qml-header-icon-rendering` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/title_icons_for_non_passive_nodes/P03_qml_header_icon_rendering_WRAPUP.md` | Blocked until `P01` and `P02` are `PASS` |
| P04 Built-In Node Icon Assets and Migration | `codex/title-icons-for-non-passive-nodes/p04-builtin-node-icon-assets-and-migration` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/title_icons_for_non_passive_nodes/P04_builtin_node_icon_assets_and_migration_WRAPUP.md` | Blocked until `P01` is `PASS` |
| P05 Verification Docs Traceability Closeout | `codex/title-icons-for-non-passive-nodes/p05-verification-docs-traceability-closeout` | PENDING | `pending` | pending | pending | `docs/specs/work_packets/title_icons_for_non_passive_nodes/P05_verification_docs_traceability_closeout_WRAPUP.md` | Blocked until `P01` through `P04` are `PASS` |
