# SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR Work Packet Manifest

- Date: `2026-04-05`
- Integration base: `main`
- Published packet window: `P00` through `P04`
- Scope baseline: convert the selected-workspace run-control plan at [docs/PLANS/Selected_Workspace_Run_Control_States.md](../../../PLANS/Selected_Workspace_Run_Control_States.md) into an execution-ready, sequential refactor program that makes Run, Pause, and Stop selected-workspace aware across shared run-flow, QAction, presenter or bridge, and QML toolbar surfaces without reintroducing direct QML ownership on `ShellWindow`, changing the single-run backend contract, or regressing the existing single-run warning path.

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- [docs/PLANS/Selected_Workspace_Run_Control_States.md](../../../PLANS/Selected_Workspace_Run_Control_States.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_bootstrap.md`
2. `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P01_run_flow_selected_workspace_projection.md`
3. `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P02_qaction_refresh_and_workspace_switch_sync.md`
4. `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P03_presenter_bridge_run_control_projection.md`
5. `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P04_qml_toolbar_workspace_run_states.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/selected-workspace-run-control-states-refactor/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and git tracking for the selected-workspace run-control refactor |
| P01 Run Flow Selected Workspace Projection | `codex/selected-workspace-run-control-states-refactor/p01-run-flow-selected-workspace-projection` | Expand `run_flow.py` into the shared selected-workspace run-control projection and add direct unit coverage for the new pure-state seam |
| P02 QAction Refresh And Workspace Switch Sync | `codex/selected-workspace-run-control-states-refactor/p02-qaction-refresh-and-workspace-switch-sync` | Make the three QActions consume the shared projection, add a dedicated run-controls signal, and refresh action state immediately when workspace selection changes |
| P03 Presenter Bridge Run Control Projection | `codex/selected-workspace-run-control-states-refactor/p03-presenter-bridge-run-control-projection` | Project the selected-workspace run-control state through the current presenter and bridge stack with a dedicated run-controls signal and bridge contract coverage |
| P04 QML Toolbar Workspace Run States | `codex/selected-workspace-run-control-states-refactor/p04-qml-toolbar-workspace-run-states` | Bind the shell toolbar buttons to the new bridge properties, add stable button object names, and make disabled controls look disabled while preserving the single-run warning path |

## Locked Defaults

- This packet set is a UI and control-state refactor program, not a backend execution or protocol change.
- Preserve the current global single-run rule and keep the existing single-run warning if the user clicks `Run` while another workspace already owns the only active run.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- After `P01`, the selected-workspace run-control projection lives in `ea_node_editor/ui/shell/run_flow.py` and is consumed by both QAction and presenter or bridge surfaces rather than duplicated in QML.
- After `P02`, QAction refresh stays on the shared `RunController` plus `WorkspaceViewNavOps` path rather than being reimplemented in menu, toolbar, or workspace-tab code.
- After `P03`, the current presenter and bridge stack owns the QML-facing run-control projection; the bridge must not become a second packet-owned interpreter of QAction semantics.
- Packet-owned QML continues to consume run-control state through `shellWorkspaceBridge`; do not reintroduce direct `mainWindowRef` or `ShellWindow` run-control ownership in QML.
- `Run` remains enabled on a non-owning selected workspace even when another workspace owns the active run; the existing run-start guard still enforces the single-run rule.
- `Pause` uses the `Resume` label only when the selected workspace owns the active run and that run is paused.
- No packet expands the scope into viewer-session, backend worker, serializer, or execution-protocol behavior.
- When a later packet changes a seam already asserted by an earlier packet's test, the later packet inherits and updates that earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

## Retained Handoff Artifacts

- Scope baseline: `docs/PLANS/Selected_Workspace_Run_Control_States.md`
- Spec contract: `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_bootstrap.md` through `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P04_qml_toolbar_workspace_run_states.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P04`
- Packet wrap-ups: `P01_run_flow_selected_workspace_projection_WRAPUP.md` through `P04_qml_toolbar_workspace_run_states_WRAPUP.md`
- Status ledger: [SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md](./SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md)

## Standard Thread Prompt Shell

`Implement SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_PXX_<name>.md exactly. Before editing, read SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md, SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md, and SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
