# NESTED_NODE_CATEGORIES Work Packet Manifest

- Date: `2026-04-11`
- Integration base: `main`
- Published packet window: `P00` through `P05`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md](../../../../PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md) into an execution-ready, strictly sequential packet set that introduces a path-based node category schema with maximum depth `10`, migrates node authoring and registry discovery from flat category strings to normalized `category_path` tuples, ships one real nested catalog family for Ansys DPF while leaving the rest of the built-in catalog effectively flat, rebuilds library grouping/filtering around a flattened trie instead of a `TreeView`, preserves custom workflows as a single-segment category family, keeps graph-theme accents keyed by the root category segment, and closes with retained documentation, traceability, and QA evidence.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md](../../../../PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `NESTED_NODE_CATEGORIES_P00_bootstrap.md`
2. `NESTED_NODE_CATEGORIES_P01_sdk_category_path_contract.md`
3. `NESTED_NODE_CATEGORIES_P02_registry_path_filters_and_dpf_taxonomy.md`
4. `NESTED_NODE_CATEGORIES_P03_library_tree_payload_projection.md`
5. `NESTED_NODE_CATEGORIES_P04_qml_nested_library_presentation.md`
6. `NESTED_NODE_CATEGORIES_P05_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/nested-node-categories/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and execution contract for the nested-node-category rollout |
| P01 SDK Category Path Contract | `codex/nested-node-categories/p01-sdk-category-path-contract` | Introduce `category_path` as the authoritative SDK schema, validation, and helper contract while keeping packet-external string consumers functional through a read-only compatibility display |
| P02 Registry Path Filters and DPF Taxonomy | `codex/nested-node-categories/p02-registry-path-filters-and-dpf-taxonomy` | Move registry discovery onto descendant-inclusive path filters, publish the nested Ansys DPF catalog family, and keep graph-theme accents anchored to the root segment |
| P03 Library Tree Payload Projection | `codex/nested-node-categories/p03-library-tree-payload-projection` | Rebuild Python-side library payloads, grouping rows, category options, quick insert, and adjacent metadata around path-backed tree rows and full-path displays |
| P04 QML Nested Library Presentation | `codex/nested-node-categories/p04-qml-nested-library-presentation` | Keep `NodeLibraryPane` on `ListView` while adding nested indentation, ancestor-aware collapse, and category-key-driven expand/collapse semantics |
| P05 Verification Docs Traceability Closeout | `codex/nested-node-categories/p05-verification-docs-traceability-closeout` | Publish README, requirements, QA-matrix, and traceability closeout for the shipped nested node category contract |

## Locked Defaults

- `category_path: tuple[str, ...]` is the only mutable source of truth for node categories in this packet set.
- Category-path normalization is locked to `1..10` non-empty trimmed segments. Existing labels such as `Input / Output` remain one segment and are never split on `/`.
- The category helper contract remains centralized and packet-owned:
  - `category_display(path)` joins normalized segments with ` > `
  - `category_key(path)` returns a stable internal key derived from normalized segments
  - descendant-inclusive filtering uses prefix matching on normalized paths instead of exact string equality
- The ` > ` display delimiter is presentation-only and is retained specifically to avoid ambiguity with existing single-segment labels such as `Input / Output`.
- A read-only compatibility `category` string may remain on specs or payloads when packet-external consumers still need display text, but grouping, sorting, filtering, collapse state, and registry discovery must not treat that display string as authoritative.
- The shipped nested catalog scope is intentionally narrow in this packet set:
  - Ansys DPF compute nodes move under `("Ansys DPF", "Compute", ...)`
  - Ansys DPF viewer nodes move under `("Ansys DPF", "Viewer", ...)`
  - other built-in families remain one-segment paths unless a packet explicitly documents a safe expansion
- The library pane remains a flat `ListView` backed by pre-flattened tree rows. Do not replace it with `TreeView` or introduce a second library surface.
- Python-side grouping must build a trie, synthesize missing intermediate category rows, flatten the result in preorder, sort segment-by-segment, and emit category rows before direct node rows inside the same subtree.
- QML collapse state is keyed by `category_key`, not by rendered label text, and all categories default to collapsed when the pane resets or initializes.
- Graph-theme category accent resolution remains rooted at the first category segment so nested families keep their existing color family.
- Custom workflows stay at `("Custom Workflows",)` in this packet set.
- This is a breaking node-authoring change for external plugins and in-repo docs because `category` becomes `category_path`; `P05` must call that out explicitly in the retained docs/examples.
- No `.sfe` serializer migration or node-instance data migration is expected because node category metadata is not persisted on node instances.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- When a later packet changes a seam asserted by an earlier packet's test, that later packet inherits and updates the earlier test file inside its own write scope.

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

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/nested_node_categories.md`
- Spec contract: `NESTED_NODE_CATEGORIES_P00_bootstrap.md` through `NESTED_NODE_CATEGORIES_P05_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P05`
- Packet wrap-ups: `P01_sdk_category_path_contract_WRAPUP.md` through `P05_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/NESTED_NODE_CATEGORIES_QA_MATRIX.md`
- Status ledger: [NESTED_NODE_CATEGORIES_STATUS.md](./NESTED_NODE_CATEGORIES_STATUS.md)

## Standard Thread Prompt Shell

`Implement NESTED_NODE_CATEGORIES_PXX_<name>.md exactly. Before editing, read NESTED_NODE_CATEGORIES_MANIFEST.md, NESTED_NODE_CATEGORIES_STATUS.md, and NESTED_NODE_CATEGORIES_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update NESTED_NODE_CATEGORIES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
