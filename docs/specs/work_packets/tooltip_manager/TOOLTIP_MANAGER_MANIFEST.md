# TOOLTIP_MANAGER Work Packet Manifest

- Date: `2026-04-13`
- Integration base: `main`
- Published packet window: `P00` through `P03`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/tooltip_manager.md](../../../../PLANS_TO_IMPLEMENT/in_progress/tooltip_manager.md) into an execution-ready packet set that adds a shell-wide tooltip policy, persists `graphics.shell.show_tooltips`, exposes the policy through shell and graph QML state, gates current informational tooltip surfaces while preserving warning/inactive explanations, and ships first-wave collision-avoidance help text in Graphics Settings.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/tooltip_manager.md](../../../../PLANS_TO_IMPLEMENT/in_progress/tooltip_manager.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `TOOLTIP_MANAGER_P00_bootstrap.md`
2. `TOOLTIP_MANAGER_P01_tooltip_preference_and_manager_contract.md`
3. `TOOLTIP_MANAGER_P02_view_menu_and_tooltip_surface_adoption.md`
4. `TOOLTIP_MANAGER_P03_collision_avoidance_tooltip_copy.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/tooltip-manager/p00-bootstrap` | Establish packet docs, status ledger, execution waves, and spec-index registration |
| P01 Tooltip Preference and Manager Contract | `codex/tooltip-manager/p01-tooltip-preference-and-manager-contract` | Add the persistent tooltip preference, shell-owned manager, shell state contract, and preference tests |
| P02 View Menu and Tooltip Surface Adoption | `codex/tooltip-manager/p02-view-menu-and-tooltip-surface-adoption` | Add the `View > Show Tooltips` action and gate current informational shell, graph, recent-project, and graph-theme tooltip surfaces |
| P03 Collision-Avoidance Tooltip Copy | `codex/tooltip-manager/p03-collision-avoidance-tooltip-copy` | Add collision-avoidance control help text in Graphics Settings and pass the current tooltip policy into the modal dialog |

## Locked Defaults

- `graphics.shell.show_tooltips` is an app-wide persistent boolean preference with default `true`.
- Missing or invalid values normalize to `true` for existing and new users.
- The shell owns one small `TooltipManager` contract that distinguishes informational tooltip visibility from warning/inactive-state explanations.
- The global toggle hides informational/help tooltips only. Warning and inactive-state explanations remain visible.
- `graphics_show_tooltips` is exposed on `ShellWindow` and the graph canvas state bridge as the runtime QML-facing policy.
- `View > Show Tooltips` is checkable, appears near the existing `Port Labels` view action, stays synchronized with resolved preferences, and persists through the existing app-preferences pipeline.
- The v1 adoption set is limited to the currently discovered tooltip surfaces named in `P02`; no broad audit of hover text, status text, or non-tooltip hints is in scope.
- `GraphicsSettingsDialog(..., tooltips_enabled: bool = True)` applies the policy at modal-dialog construction time. V1 does not live-update an already-open modal dialog.
- `P02` and `P03` both depend on the `P01` contract. They may run in parallel after `P01` is accepted because their source write scopes are disjoint.
- When a later packet changes a seam already asserted by an earlier packet's test, that later packet inherits and updates the earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`
- `P03`

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/tooltip_manager.md`
- Style baseline: `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_MANIFEST.md`
- Prompt and wave precedent: `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md`
- Spec contract: `TOOLTIP_MANAGER_P00_bootstrap.md` through `TOOLTIP_MANAGER_P03_collision_avoidance_tooltip_copy.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P03`
- Packet wrap-ups: `P01_tooltip_preference_and_manager_contract_WRAPUP.md` through `P03_collision_avoidance_tooltip_copy_WRAPUP.md`
- Status ledger: [TOOLTIP_MANAGER_STATUS.md](./TOOLTIP_MANAGER_STATUS.md)

## Standard Thread Prompt Shell

`Implement TOOLTIP_MANAGER_PXX_<name>.md exactly. Before editing, read TOOLTIP_MANAGER_MANIFEST.md, TOOLTIP_MANAGER_STATUS.md, and TOOLTIP_MANAGER_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update TOOLTIP_MANAGER_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
