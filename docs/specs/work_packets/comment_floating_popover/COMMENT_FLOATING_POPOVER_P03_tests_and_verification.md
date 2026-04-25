# COMMENT_FLOATING_POPOVER P03: Tests and Verification

## Packet Metadata

- Packet: `P03`
- Title: `Tests and Verification`
- Execution Dependencies: `COMMENT_FLOATING_POPOVER_P02_action_wiring_and_commit_flow.md`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Add the final regression coverage for the comment floating popover and close out packet-scoped verification without widening the feature beyond comment backdrop nodes.

## Preconditions

- `P01` and `P02` are `PASS`.
- The popover shell, transient state, action wiring, and body commit route exist on the packet branch base for this wave.
- Existing comment backdrop, serializer, and main-window shell tests are available through the project venv.

## Execution Dependencies

- `COMMENT_FLOATING_POPOVER_P02_action_wiring_and_commit_flow.md`

## Target Subsystems

- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_main_window_shell.py`
- `tests/test_comment_backdrop_layer.py`
- `tests/test_comment_backdrop_contracts.py`
- `tests/test_serializer.py`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`

## Conservative Write Scope

- `docs/specs/work_packets/comment_floating_popover/P03_tests_and_verification_WRAPUP.md`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_main_window_shell.py`
- `tests/test_comment_backdrop_layer.py`
- `tests/test_comment_backdrop_contracts.py`
- `tests/test_serializer.py`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`

## Required Behavior

- Add focused tests for comment popover visibility and stable object names, including `graphCommentFloatingPopover`.
- Verify the popover opens from the comment-specific toolbar/surface action and, if implemented, the comment-specific context-menu action.
- Verify non-comment nodes do not expose the popover action.
- Verify Escape, close button, and click-away/canvas press clear the transient active popover node id.
- Verify popover body edits commit through the existing `body` property path and remain synchronized with inspector and inline editor updates.
- Verify the popover active node id is transient and is not serialized into project documents, preferences, graph scene payloads, or serializer round trips.
- Verify existing `Peek Inside` behavior still exposes `Peek Inside` / `Exit Peek` separately and remains independent from the popover active node id.
- If this packet discovers stale or incomplete assertions added in `P01` or `P02`, update those inherited regression anchors in this packet instead of duplicating the same assertion elsewhere.

## Non-Goals

- Do not add new user-facing behavior beyond completing tests and small source fixes needed to satisfy the documented feature contract.
- Do not introduce a new persistence model, Python bridge API, or preference setting.
- Do not broaden the feature to non-comment annotation surfaces.
- Do not update requirement modules or performance docs unless the executor explicitly asks for a separate closeout packet.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py tests/test_main_window_shell.py tests/test_comment_backdrop_layer.py tests/test_comment_backdrop_contracts.py tests/test_serializer.py --ignore=venv -q
```

2. GUI verification runner dry-run:

```powershell
.\venv\Scripts\python.exe scripts/run_verification.py --mode gui --dry-run
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py -k "popover or peek_inside or inline_body_commit" --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/comment_floating_popover/P03_tests_and_verification_WRAPUP.md`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_main_window_shell.py`
- `tests/test_comment_backdrop_layer.py`
- `tests/test_comment_backdrop_contracts.py`
- `tests/test_serializer.py`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`

## Acceptance Criteria

- Tests prove open, close, Escape, click-away, body commit sync, inspector sync, non-comment action absence, and non-persistence.
- Existing `Peek Inside` behavior remains covered and independent.
- Packet-owned tests use stable object names rather than brittle visual coordinates wherever possible.
- The full packet verification commands pass.
- The review gate passes.
- The wrap-up records all commands, tests, changed files, produced artifacts, and residual risks.

## Handoff Notes

- This is the final implementation packet in the set.
- If broad traceability or UI spec updates are desired after execution, publish a separate closeout packet set rather than widening this packet.
