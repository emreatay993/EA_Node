Implement MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md exactly. Before editing, read MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md, MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md, and MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/media_viewer_content_fullscreen/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/media-viewer-content-fullscreen/p00-bootstrap` from `main`.
- Review Gate: run the exact `MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_STATUS_PASS` inline Python command from `MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_MANIFEST.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P01_fullscreen_state_contract.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P01_fullscreen_state_contract_PROMPT.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P02_shell_overlay_and_media_renderer.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P02_shell_overlay_and_media_renderer_PROMPT.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P03_surface_buttons_and_shortcut.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P03_surface_buttons_and_shortcut_PROMPT.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P04_interactive_live_viewer_retargeting.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P04_interactive_live_viewer_retargeting_PROMPT.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout.md`
  - `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_P05_regression_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist updates needed to keep packet docs, future wrap-ups, and the future QA matrix trackable.
