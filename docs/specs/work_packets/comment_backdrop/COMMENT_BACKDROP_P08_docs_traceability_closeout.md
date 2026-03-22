# COMMENT_BACKDROP P08: Docs + Traceability Closeout

## Objective
- Refresh the public docs, requirements, and traceability after the comment-backdrop packets land and freeze the accepted verification anchors for the new feature.

## Preconditions
- `P07` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- `README.md`
- `ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md`

## Conservative Write Scope
- `README.md`
- `ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/comment_backdrop/P08_docs_traceability_closeout_WRAPUP.md`

## Required Behavior
- Update the public docs and requirements to describe:
  - the dedicated zero-port comment backdrop node
  - the dedicated under-edge backdrop layer
  - geometry-owned membership with nesting
  - wrap-selection creation through shortcut `C`
  - collapse hiding and boundary-edge rerouting
  - expanded versus collapsed clipboard and delete semantics
- Refresh traceability so the new code paths and targeted regressions are linked from the relevant requirement and acceptance rows.
- Record the accepted comment-backdrop verification anchors in requirements or traceability docs using the packet-owned focused test files from `P01` through `P07`.
- Keep the docs closeout behavior-preserving. No runtime feature changes belong in this packet.

## Non-Goals
- No new runtime code or tests except doc-driven traceability edits.
- No new `.gitignore` exceptions or packet-external manifest rewrites.
- No executor or merge automation changes.

## Verification Commands
1. `./venv/Scripts/python.exe scripts/check_traceability.py`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_contracts.py tests/test_comment_backdrop_layer.py tests/test_comment_backdrop_membership.py tests/test_comment_backdrop_interactions.py tests/test_comment_backdrop_collapse.py tests/test_comment_backdrop_clipboard.py tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P08_docs_traceability_closeout_WRAPUP.md`

## Acceptance Criteria
- Public docs and requirements describe the landed comment-backdrop behavior using the final packet-owned terminology.
- Traceability rows point at the new code and test anchors introduced by the packet set.
- The accepted comment-backdrop verification anchors are documented without claiming broader unproven coverage.
- The packet makes no runtime behavior changes outside documentation and traceability.

## Handoff Notes
- When this packet passes, the packet set is ready for executor-driven merge readiness reporting.
- Use the wrap-up to summarize the final accepted verification anchor list so future packet sets can reuse it instead of inventing a second regression matrix.
