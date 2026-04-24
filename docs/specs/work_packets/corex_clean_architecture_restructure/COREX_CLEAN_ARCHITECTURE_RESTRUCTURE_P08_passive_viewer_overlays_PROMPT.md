# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P08 Passive Viewer Overlays Prompt

Read the manifest, status ledger, and `COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_P08_passive_viewer_overlays.md` before editing. Implement exactly `P08_passive_viewer_overlays`.

Before editing, inspect current user-owned changes in `ea_node_editor/ui_qml/embedded_viewer_overlay_manager.py`, `tests/test_embedded_viewer_overlay_manager.py`, and any comment-popover files touched in the worktree. Preserve and work with those changes.

Prefer the narrowest packet-owned rerun during development and remediation. Do not substitute whole shell-isolation or full verification runs unless the packet spec requires it.

## Wrap-up and commit requirements

Create `docs/specs/work_packets/corex_clean_architecture_restructure/P08_passive_viewer_overlays_WRAPUP.md`.

The wrap-up `Implementation Summary` must begin with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`. `Commit Owner` must be `worker`, `executor`, or `executor-pending`; it is not a person or email. `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit.

Run every `Verification Commands` entry and the `Review Gate`. End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`. Begin `Ready for Integration` with `Yes:` or `No:`.

Commit packet-local changes on `codex/corex-clean-architecture-restructure/p08-passive-viewer-overlays`, update the shared status ledger only if you are running this prompt standalone, and stop after this packet.
