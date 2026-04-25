# COREX Comment Floating Popover Plan

## Summary

- Apply the `Floating Popover (03)` concept from `mockups/COREX Comments - Unified Variants.standalone.html`.
- Concept anchors: badge/toolbar entry opens a lightweight node-anchored thread popover, no panel jump, compact header with comment icon + node title + count pill, scrollable body, footer editor, 8px radius, strong shadow, comment-yellow accent.
- Current repo maps this to comment backdrop nodes, not a separate React-style comment-thread controller.
- No files were created in this thread because Plan Mode forbids repo mutation; create the packet set at `docs/specs/work_packets/comment_floating_popover/` in an execution-enabled planner/executor thread.

## Key Changes

- Add a QML-only floating comment popover overlay under `ea_node_editor/ui_qml/components/graph/overlay/`, anchored to the active comment backdrop host and following pan/zoom like `GraphNodeFloatingToolbar`.
- Add transient canvas state such as `activeCommentPopoverNodeId`; do not persist this into project files, preferences, or graph scene payload.
- Add a comment-specific toolbar/context entry, e.g. `openCommentPopover`, for comment backdrops. Preserve existing `Peek Inside` focused-view behavior unless the packet explicitly changes it.
- Reuse existing `body` property commit flow so edits in the popover stay in sync with the inspector and current inline editor.
- Match the mockup visual language: comment accent, compact header, count pill, panel-alt background, border, 8px radius, `shadow-pop`-style depth, scrollable body, close button, Escape/click-away dismissal.

## Packet Set

- `P00 Bootstrap`: create manifest, status ledger, packet specs/prompts, register in `docs/specs/INDEX.md`, mark `P00` as `PASS`.
- `P01 Overlay Shell`: implement popover component, positioning, object names, close behavior, and visual styling.
- `P02 Action Wiring`: expose/open/close popover from comment backdrop toolbar/context path and keep commit flow wired to existing node property updates.
- `P03 Tests + Verification`: add shell/QML regressions for open, close, body edit sync, no persistence, and no regression of current `Peek Inside`.

## Tests

- Use project venv: `.\venv\Scripts\python.exe`.
- Main verification should include:
  - `tests/main_window_shell/comment_backdrop_workflows.py`
  - relevant graph canvas bridge/surface tests
  - QML surface/input tests that cover floating toolbar/action behavior
  - `--ignore=venv -q`
- Add assertions for stable object names like `graphCommentFloatingPopover`, visible state, active node id, editor commit, Escape/click-away close.

## Assumptions

- “Floating Popover (03)” means applying the mockup’s node-anchored popover interaction to existing COREX comment backdrop nodes.
- Existing `Peek Inside` remains a separate focused-view feature.
- Executor target merge branch is `main`.

## Exact Fresh-Thread Prompt

```text
Use C:\Users\emre_\.codex\skills\subagent-work-packet-executor\SKILL.md.

Target merge branch: main.

Execute the already-planned packet set for COREX comment Floating Popover (03) at:

docs/specs/work_packets/comment_floating_popover/

Treat the saved packet docs as the only source of truth. Confirm P00 is present and PASS, confirm the manifest has Execution Waves, then execute the first pending wave using worker subagents as defined by the executor skill. Preserve the design intent from mockups/COREX Comments - Unified Variants.standalone.html, variant 03 “Floating Popover”: a lightweight comment popover anchored to the comment node/backdrop, with compact header, comment accent, count pill, scrollable body, footer editor, no panel jump, and Escape/click-away dismissal.

Use the project venv for packet verification commands. Stay inside each packet’s Conservative Write Scope, require wrap-up artifacts, run validators and Review Gates, update the shared status ledger only from the executor, and stop when the packet set is either ready for merge into main or blocked by a terminal packet failure.
```
