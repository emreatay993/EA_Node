# ADDON_MANAGER_BACKEND_PREPARATION Work Packet Manifest

- Date: `2026-04-19`
- Integration base: `main`
- Published packet window: `P00` through `P08`
- Scope baseline: convert the approved add-on backend preparation plan into a fresh-context packet set that introduces a generic add-on catalog and apply-policy model, adds a menubar `Add-On Manager` entry, projects missing add-on nodes as locked placeholders, enforces Mockup B locked-node behavior in the graph, extracts ANSYS DPF into a self-contained repo-local add-on, enables rebuild-based hot apply for DPF, and lands a Variant 4 inspector-style Add-On Manager surface without widening into marketplace/discovery work.
- Design anchors:
  - [docs/concepts/design_handoffs/claude/corex-deactivated-nodes/project/Deactivated Nodes.html](../../../../concepts/design_handoffs/claude/corex-deactivated-nodes/project/Deactivated%20Nodes.html)
  - [docs/concepts/design_handoffs/claude/corex-add-on-manager/project/Add-on Manager.html](../../../../concepts/design_handoffs/claude/corex-add-on-manager/project/Add-on%20Manager.html)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `ADDON_MANAGER_BACKEND_PREPARATION_P00_bootstrap.md`
2. `ADDON_MANAGER_BACKEND_PREPARATION_P01_addon_contracts_and_state_model.md`
3. `ADDON_MANAGER_BACKEND_PREPARATION_P02_addon_manager_entry_and_open_request_plumbing.md`
4. `ADDON_MANAGER_BACKEND_PREPARATION_P03_generic_missing_addon_placeholder_projection.md`
5. `ADDON_MANAGER_BACKEND_PREPARATION_P04_locked_node_graph_host_and_mockup_b_visuals.md`
6. `ADDON_MANAGER_BACKEND_PREPARATION_P05_ansys_dpf_addon_package_extraction.md`
7. `ADDON_MANAGER_BACKEND_PREPARATION_P06_dpf_hot_apply_registry_and_runtime_rebuild.md`
8. `ADDON_MANAGER_BACKEND_PREPARATION_P07_addon_manager_variant4_surface.md`
9. `ADDON_MANAGER_BACKEND_PREPARATION_P08_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/addon-manager-backend-preparation/p00-bootstrap` | Create the packet docs, status ledger, spec-index registration, and tracking artifacts |
| P01 Add-on Contracts And State Model | `codex/addon-manager-backend-preparation/p01-addon-contracts-and-state-model` | Establish the generic add-on record, apply-policy model, and persisted state contract |
| P02 Add-On Manager Entry And Open-Request Plumbing | `codex/addon-manager-backend-preparation/p02-addon-manager-entry-and-open-request-plumbing` | Add the menubar entry and shell-side open-manager plumbing without building the final surface yet |
| P03 Generic Missing-Add-On Placeholder Projection | `codex/addon-manager-backend-preparation/p03-generic-missing-addon-placeholder-projection` | Generalize unresolved-node projection so missing add-on nodes remain visible on canvas |
| P04 Locked Node Graph Host And Mockup B Visuals | `codex/addon-manager-backend-preparation/p04-locked-node-graph-host-and-mockup-b-visuals` | Enforce locked-node interaction blocking and land the Mockup B graph treatment |
| P05 ANSYS DPF Add-On Package Extraction | `codex/addon-manager-backend-preparation/p05-ansys-dpf-addon-package-extraction` | Move DPF descriptors, helpers, docs, and glue behind a repo-local add-on package |
| P06 DPF Hot Apply Registry And Runtime Rebuild | `codex/addon-manager-backend-preparation/p06-dpf-hot-apply-registry-and-runtime-rebuild` | Rebuild registries and services so DPF can be enabled or disabled in-session |
| P07 Add-On Manager Variant 4 Surface | `codex/addon-manager-backend-preparation/p07-addon-manager-variant4-surface` | Build the faithful Variant 4 inspector-style Add-On Manager surface on the new shell seam |
| P08 Verification Docs Traceability Closeout | `codex/addon-manager-backend-preparation/p08-verification-docs-traceability-closeout` | Publish QA evidence, requirement traceability, and closeout guidance for the preparation pass |

## Locked Defaults

- The new top-level entry is `Add-On Manager` in the menubar. Do not replace it with workflow-settings-only access.
- Variant 4 means the inspector-style two-pane manager described in the add-on-manager handoff. Do not substitute other mockup variants.
- Mockup B means the conservative locked-node treatment from the deactivated-nodes handoff. Keep the normal node silhouette and graph context.
- Missing add-on nodes must remain visible on the canvas as locked placeholders. They must not disappear into persistence-only sidecars.
- Add-ons declare one apply policy each: `hot_apply` for node/library-style add-ons and `restart_required` for cross-cutting features.
- ANSYS DPF is the first `hot_apply` reference add-on.
- Restart-required add-ons may persist pending state and surface a restart banner, but this packet set does not require true in-session unload for them.
- Marketplace/discovery, remote install flows, and other add-on-manager variants remain out of scope.
- Preserve `.sfe` compatibility, unresolved-doc rebind behavior, and non-DPF workflows throughout.
- When a later packet changes an earlier packet's asserted seam, the later packet inherits and updates that earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`
- `P02`

### Wave 2
- `P03`

### Wave 3
- `P04`
- `P05`

### Wave 4
- `P06`

### Wave 5
- `P07`

### Wave 6
- `P08`

## Retained Handoff Artifacts

- Design anchors:
  - `docs/concepts/design_handoffs/claude/corex-deactivated-nodes/project/Deactivated Nodes.html`
  - `docs/concepts/design_handoffs/claude/corex-add-on-manager/project/Add-on Manager.html`
- Packet specs: `ADDON_MANAGER_BACKEND_PREPARATION_P00_bootstrap.md` through `ADDON_MANAGER_BACKEND_PREPARATION_P08_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P08`
- Packet wrap-ups: `P01_addon_contracts_and_state_model_WRAPUP.md` through `P08_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md`
- Status ledger: [ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md](./ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md)

## Standard Thread Prompt Shell

`Implement ADDON_MANAGER_BACKEND_PREPARATION_PXX_<name>.md exactly. Before editing, read ADDON_MANAGER_BACKEND_PREPARATION_MANIFEST.md, ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md, and ADDON_MANAGER_BACKEND_PREPARATION_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
