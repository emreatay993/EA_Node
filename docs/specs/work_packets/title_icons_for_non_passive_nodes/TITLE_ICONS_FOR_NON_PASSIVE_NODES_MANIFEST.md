# TITLE_ICONS_FOR_NON_PASSIVE_NODES Work Packet Manifest

- Date: `2026-04-13`
- Integration base: `main`
- Published packet window: `P00` through `P05`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md](../../../../PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md) into an execution-ready packet set that adds path-based title-leading icons for active and `compile_only` nodes, keeps passive nodes iconless in the title row, introduces an app-global nullable icon-size override, migrates supported built-in non-passive node icons to repo-managed image paths, preserves collapsed comment-backdrop icon behavior, and closes with retained QA and traceability evidence.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md](../../../../PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md`
- `docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_MANIFEST.md`

## Retained Packet Order

1. `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_bootstrap.md`
2. `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P01_path_resolver_and_payload_contract.md`
3. `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P02_icon_size_preferences_and_bridge.md`
4. `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P03_qml_header_icon_rendering.md`
5. `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P04_builtin_node_icon_assets_and_migration.md`
6. `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P05_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/title-icons-for-non-passive-nodes/p00-bootstrap` | Establish packet docs, status ledger, execution waves, and spec-index registration |
| P01 Path Resolver and Payload Contract | `codex/title-icons-for-non-passive-nodes/p01-path-resolver-and-payload-contract` | Add the central local-file title-icon resolver and expose `icon_source` only for eligible live graph node payloads |
| P02 Icon Size Preferences and Bridge | `codex/title-icons-for-non-passive-nodes/p02-icon-size-preferences-and-bridge` | Add the nullable `graph_node_icon_pixel_size_override` preference and project the effective node-title icon size through shell, bridge, and QML typography bindings |
| P03 QML Header Icon Rendering | `codex/title-icons-for-non-passive-nodes/p03-qml-header-icon-rendering` | Render `nodeData.icon_source` before standard non-passive titles without regressing title centering, elision, editing, or collapsed comment-backdrop icons |
| P04 Built-In Node Icon Assets and Migration | `codex/title-icons-for-non-passive-nodes/p04-builtin-node-icon-assets-and-migration` | Add packaged node-title icon assets and migrate supported active and `compile_only` built-in node specs from symbolic icon names to stable asset paths |
| P05 Verification Docs Traceability Closeout | `codex/title-icons-for-non-passive-nodes/p05-verification-docs-traceability-closeout` | Publish retained QA evidence, requirement updates, and traceability closeout for the shipped title-icon feature |

## Locked Defaults

- `NodeTypeSpec.icon` remains the authoring field, but node-header rendering treats it as a local image-path reference only.
- Supported title-icon file suffixes are `.svg`, `.png`, `.jpg`, and `.jpeg`, case-insensitive.
- Empty strings, missing files, unreadable files, unsupported suffixes, remote URLs, data URIs, and symbolic icon names resolve to no title icon.
- Built-in relative icon paths resolve from the repo-managed node-title icon asset root.
- File and package plugin relative icon paths resolve from plugin provenance when a safe root is available. Absolute plugin paths are supported when they exist and use a supported suffix.
- Entry-point plugins without a discoverable package root must not gain an unsafe cwd-relative fallback.
- `icon_source` is a derived live graph payload field. It is not persisted into `.sfe` project files.
- `icon_source` is populated only when `runtime_behavior` is `active` or `compile_only` and the resolver returns a non-empty local QML source URL.
- Passive nodes remain title-iconless even when their specs carry `icon` metadata.
- The existing collapsed comment-backdrop title icon stays on the current `uiIcons` / `comment.svg` path and is not converted to this feature's image-path contract.
- `graphics.typography.graph_node_icon_pixel_size_override` is a nullable app-global integer preference. `null` means the effective icon size follows the current `graph_label_pixel_size`.
- Non-null icon-size overrides clamp with the same inclusive `8..18` bounds used by `graph_label_pixel_size`.
- QML rendering uses authored image colors and no theme tinting.
- The feature scope excludes node-library tiles, inspector rendering, remote image loading, and symbolic icon-name rendering in node headers.
- P01 and P02 may run in parallel because their source write scopes are disjoint. P03 must wait for both. P04 must wait for P01 but may run alongside P03. P05 must wait for every implementation packet.

## Execution Waves

### Wave 1
- `P01`
- `P02`

### Wave 2
- `P03`
- `P04`

### Wave 3
- `P05`

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/title_icons_for_non_passive_nodes.md`
- Planning precedent: `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md`
- Rendering precedent: `docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_MANIFEST.md`
- Spec contract: `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P00_bootstrap.md` through `TITLE_ICONS_FOR_NON_PASSIVE_NODES_P05_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P05`
- Packet wrap-ups: `P01_path_resolver_and_payload_contract_WRAPUP.md` through `P05_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/TITLE_ICONS_FOR_NON_PASSIVE_NODES_QA_MATRIX.md`
- Status ledger: [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md)

## Standard Thread Prompt Shell

`Implement TITLE_ICONS_FOR_NON_PASSIVE_NODES_PXX_<name>.md exactly. Before editing, read TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md, TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md, and TITLE_ICONS_FOR_NON_PASSIVE_NODES_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
