# PORT_LABEL_VISIBILITY Work Packet Manifest

- Date: `2026-03-22`
- Scope baseline: add an app-wide `graphics.canvas.show_port_labels` preference, expose it through both the View menu and Graphics Settings, and replace the static expanded-standard-node minimum width floor with a preference-aware title/port layout contract, while leaving passive families, flowchart neutral-handle rules, collapsed widths, and stored port-label data unchanged.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/settings.py`, `ea_node_editor/app_preferences.py`, `ea_node_editor/ui/shell/presenters.py`, and the canvas bridge surfaces already persist and publish app-wide graphics settings, but there is no `graphics.canvas.show_port_labels` field or `graphics_show_port_labels` runtime surface yet.
  - `ea_node_editor/ui/shell/window_actions.py` exposes `Graphics Settings` from `&Settings`, but `&View` has no port-label visibility action and `ea_node_editor/ui/dialogs/graphics_settings_dialog.py` still limits the Canvas page to grid, minimap, and node-shadow controls.
  - `ea_node_editor/ui_qml/graph_surface_metrics.py` still gives standard nodes a static `120.0` `min_width`, `ea_node_editor/ui_qml/edge_routing.py::node_size(...)` does not clamp default/custom widths to a computed minimum, and `ea_node_editor/ui_qml/graph_scene_mutation_history.py::set_node_geometry(...)` only clamps against the current static metric payload.
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` and `GraphNodePortsLayer.qml` currently keep standard-node labels visible whenever the surface is not using the flowchart neutral-handle rule, and there is no tooltip-only port-label mode for expanded standard nodes.

## Packet Order (Strict)

1. `PORT_LABEL_VISIBILITY_P00_bootstrap.md`
2. `PORT_LABEL_VISIBILITY_P01_preferences_bridge_contract.md`
3. `PORT_LABEL_VISIBILITY_P02_shell_ui_toggle_sync.md`
4. `PORT_LABEL_VISIBILITY_P03_standard_node_width_policy.md`
5. `PORT_LABEL_VISIBILITY_P04_qml_label_presentation_rollout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/port-label-visibility/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Preferences + Bridge Contract | `codex/port-label-visibility/p01-preferences-bridge-contract` | Add the additive persisted preference plus shell/canvas getter-setter surfaces without changing visuals yet |
| P02 Shell UI Toggle Sync | `codex/port-label-visibility/p02-shell-ui-toggle-sync` | Add the View-menu action and Graphics Settings editor over the shared preference path and keep them synchronized |
| P03 Standard Node Width Policy | `codex/port-label-visibility/p03-standard-node-width-policy` | Replace the static expanded-standard-node width floor with a preference-aware scene metric and resize-clamp contract |
| P04 QML Label Presentation Rollout | `codex/port-label-visibility/p04-qml-label-presentation-rollout` | Apply the standard-node label-hide and tooltip-only presentation behavior in QML using the packet-owned bridge and metric seams |

## Locked Defaults

- `graphics.canvas.show_port_labels` defaults to `true` on fresh installs.
- `View > Port Labels` and `Graphics Settings > Canvas` are two views over the same persisted app-preferences field; neither surface may introduce a session-only override.
- Only expanded standard non-passive nodes change behavior in this packet set. Passive families, flowchart neutral-handle label suppression, collapsed nodes, and stored `port_labels` data stay on their current rules unless a packet explicitly says otherwise.
- Minimum-width authority stays in scene metrics plus mutation clamping. QML may consume packet-owned metric fields for presentation, but it must not introduce a second width-policy authority.
- Re-enabling port labels may expand affected standard nodes immediately through effective rendered-width clamping, but it must not rewrite stored custom widths in project data.
- Tooltip-only fallback is limited to the standard-node path when the preference is off. Surfaces that already hide labels for family-specific reasons must not gain a tooltip-only replacement in this scope.
- This packet set is intentionally sequential. No implementation wave contains more than one packet.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `PORT_LABEL_VISIBILITY_Pxx_<name>.md`
- Implementation prompt: `PORT_LABEL_VISIBILITY_Pxx_<name>_PROMPT.md`
- Packet wrap-up artifact for each implementation packet: `docs/specs/work_packets/port_label_visibility/Pxx_<slug>_WRAPUP.md`
- Status ledger update in [PORT_LABEL_VISIBILITY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/port_label_visibility/PORT_LABEL_VISIBILITY_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement PORT_LABEL_VISIBILITY_PXX_<name>.md exactly. Before editing, read PORT_LABEL_VISIBILITY_MANIFEST.md, PORT_LABEL_VISIBILITY_STATUS.md, and PORT_LABEL_VISIBILITY_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node-surface contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update PORT_LABEL_VISIBILITY_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P04` may change source/test files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep public `ShellWindow`, `GraphCanvasStateBridge`, `GraphCanvasBridge`, `GraphCanvas.qml`, `graphNodeCard`, and `graphCanvas` discoverability contracts stable unless the owning packet explicitly introduces the new port-label preference surface or metric field it owns.
- Reuse the existing graphics-settings, shell-scene boundary, node-inline-title, and graph-surface host seams instead of reopening monolithic code paths without a packet-owned reason.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
