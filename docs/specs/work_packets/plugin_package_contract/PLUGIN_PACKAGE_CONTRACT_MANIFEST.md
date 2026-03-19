# PLUGIN_PACKAGE_CONTRACT Work Packet Manifest

- Date: `2026-03-19`
- Scope baseline: resolve plugin package layout/discovery/install/export mismatches so imported `.eanp` packages remain discoverable and loadable by the runtime loader contract.
- Canonical requirements:
  - [Node SDK](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Persistence](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Target merge branch: `main`
- Packet set name: `PLUGIN_PACKAGE_CONTRACT`
- Packet count: `6`

## Packet Order (Strict)

1. `PLUGIN_PACKAGE_CONTRACT_P00_bootstrap.md`
2. `PLUGIN_PACKAGE_CONTRACT_P01_loader_directory_contract.md`
3. `PLUGIN_PACKAGE_CONTRACT_P02_package_import_layout.md`
4. `PLUGIN_PACKAGE_CONTRACT_P03_package_export_contract.md`
5. `PLUGIN_PACKAGE_CONTRACT_P04_shell_package_workflows.md`
6. `PLUGIN_PACKAGE_CONTRACT_P05_docs_traceability.md`

## Execution Waves

- This packet set is intentionally sequential; every execution wave contains exactly one implementation packet.
- Wave 1: `P01`
- Wave 2: `P02`
- Wave 3: `P03`
- Wave 4: `P04`
- Wave 5: `P05`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/plugin-package-contract/p00-bootstrap` | Save this packet set in the repo and register it in the spec index |
| P01 Loader Directory Contract | `codex/plugin-package-contract/p01-loader-directory-contract` | Canonicalize loader discovery across single-file plugins and package directories |
| P02 Package Import Layout | `codex/plugin-package-contract/p02-package-import-layout` | Make `.eanp` import/install/list/uninstall match the canonical loader contract |
| P03 Package Export Contract | `codex/plugin-package-contract/p03-package-export-contract` | Make lower-level export contracts round-trip through import/discovery |
| P04 Shell Package Workflows | `codex/plugin-package-contract/p04-shell-package-workflows` | Align shell package import/export workflows with repaired contracts |
| P05 Docs And Traceability | `codex/plugin-package-contract/p05-docs-traceability` | Close docs, traceability, and truthful contract wording |

## Packet Template Rules

- Every packet spec must include objective, preconditions, target subsystems, required behavior, non-goals, verification commands, review gate (or `none`), acceptance criteria, and handoff notes.
- Every packet prompt must instruct agents to read manifest, status, and packet before editing.
- Do not execute packets out of order. Do not start a later wave until every packet in the current wave is `PASS`.
- Keep each packet implementation within its scope to preserve sequential integrity.
- Keep source/test and status entries in scope for their packet.
- `P00` is docs/bootstrap-only.

## Packet-Set Obligations
- Every packet spec must include explicit conservative write scopes and acceptance criteria.
- Every packet prompt must include status ledger update rules and required artifacts.
- Every packet must produce a `<slug>_WRAPUP.md` file in this directory.
- Packet status updates must remain in [PLUGIN_PACKAGE_CONTRACT_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md).
