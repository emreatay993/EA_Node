# COMMENT_FLOATING_POPOVER Work Packet Manifest

- Date: `2026-04-24`
- Integration base: `main`
- Published packet window: `P00` through `P03`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/COREX Comment Floating Popover Plan.md](../../../../PLANS_TO_IMPLEMENT/in_progress/COREX%20Comment%20Floating%20Popover%20Plan.md) into an execution-ready packet set that adds the COREX `Floating Popover (03)` interaction to comment backdrop nodes as a QML-only, node-anchored popover with transient canvas state, comment-specific action wiring, shared `body` commit flow, and focused regressions for visibility, dismissal, synchronization, and non-persistence.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/COREX Comment Floating Popover Plan.md](../../../../PLANS_TO_IMPLEMENT/in_progress/COREX%20Comment%20Floating%20Popover%20Plan.md)
- Design baseline: `mockups/COREX Comments - Unified Variants.standalone.html`, variant `Floating Popover (03)`

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `COMMENT_FLOATING_POPOVER_P00_bootstrap.md`
2. `COMMENT_FLOATING_POPOVER_P01_overlay_shell.md`
3. `COMMENT_FLOATING_POPOVER_P02_action_wiring_and_commit_flow.md`
4. `COMMENT_FLOATING_POPOVER_P03_tests_and_verification.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/comment-floating-popover/p00-bootstrap` | Establish packet docs, status ledger, execution waves, and spec-index registration |
| P01 Overlay Shell | `codex/comment-floating-popover/p01-overlay-shell` | Add the QML popover component, transient canvas state, host anchoring, positioning, styling, object names, and dismissal shell |
| P02 Action Wiring and Commit Flow | `codex/comment-floating-popover/p02-action-wiring-and-commit-flow` | Expose a comment-backdrop-only popover action through the surface/action path and reuse the existing `body` property commit route |
| P03 Tests and Verification | `codex/comment-floating-popover/p03-tests-and-verification` | Add focused regressions for toolbar/context visibility, open/close behavior, body edit sync, non-persistence, and existing `Peek Inside` behavior |

## Worker Agent Defaults

- Implementation workers for `P01` through `P03` must be spawned with `model="gpt-5.5"` and `reasoning_effort="xhigh"`.
- This packet-set override supersedes the executor skill's default worker model for implementation subagents.
- The executor/orchestrator may still use the executor skill normally; only packet worker subagents are overridden.

## Locked Defaults

- The feature applies to `comment_backdrop` surface-family nodes only. Do not broaden it to generic annotations, notes, callouts, section headers, or normal graph nodes unless a later plan explicitly asks for that.
- `Peek Inside` remains a separate focused-view feature. Do not rename, remove, or route the new popover through comment-peek state or `scope_path`.
- The popover state is transient canvas/QML state, expected to be shaped like `activeCommentPopoverNodeId`. It must not be persisted into project documents, graph scene payloads, app preferences, or serializer fields.
- The visual mount belongs under the graph overlay stack and should follow the same pan/zoom anchoring model as the existing node floating toolbar.
- The popover must expose stable object names, including `graphCommentFloatingPopover` for the panel and a stable body editor field object name for tests.
- The surface action source belongs on `GraphCommentBackdropSurface.qml` through the existing surface action contract. Do not add this action to `GraphNodeHost.commonNodeActions`.
- Popover body edits reuse the existing `body` property commit flow through `inlinePropertyCommitted` and the graph canvas node surface bridge. Do not create a separate comment-thread persistence model.
- Closing must be available through the panel close affordance, Escape, click-away/canvas press, and loss of the active node host.
- Packet execution is sequential because the packets intentionally share QML canvas surface boundaries and later test anchors.
- When a later packet changes a seam already asserted by an earlier packet's test, that later packet inherits and updates the earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/COREX Comment Floating Popover Plan.md`
- Design baseline: `mockups/COREX Comments - Unified Variants.standalone.html`
- Discovery anchors: `GraphCanvasRootLayers.qml`, `GraphCanvasInteractionState.qml`, `GraphNodeFloatingToolbar.qml`, `GraphCommentBackdropSurface.qml`, `GraphCanvasNodeDelegate.qml`, `GraphCanvasContextMenus.qml`
- Regression anchors: `tests/main_window_shell/comment_backdrop_workflows.py`, `tests/test_main_window_shell.py`, `tests/test_comment_backdrop_layer.py`, `tests/test_comment_backdrop_contracts.py`, `tests/test_serializer.py`
- Spec contract: `COMMENT_FLOATING_POPOVER_P00_bootstrap.md` through `COMMENT_FLOATING_POPOVER_P03_tests_and_verification.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P03`
- Packet wrap-ups: `P01_overlay_shell_WRAPUP.md` through `P03_tests_and_verification_WRAPUP.md`
- Status ledger: [COMMENT_FLOATING_POPOVER_STATUS.md](./COMMENT_FLOATING_POPOVER_STATUS.md)

## Standard Thread Prompt Shell

```text
Implement COMMENT_FLOATING_POPOVER_PXX_<name>.md exactly. Before editing, read COMMENT_FLOATING_POPOVER_MANIFEST.md, COMMENT_FLOATING_POPOVER_STATUS.md, and COMMENT_FLOATING_POPOVER_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update COMMENT_FLOATING_POPOVER_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.
```

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
- Executor-spawned implementation workers must use `gpt-5.5` with `xhigh` reasoning for this packet set.
