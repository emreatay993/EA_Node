Implement GRAPHICS_PERFORMANCE_MODES_P00_bootstrap.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/graphics_performance_modes/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p00-bootstrap`.
- Review Gate: run the exact `GRAPHICS_PERFORMANCE_MODES_P00_STATUS_PASS` inline Python command from `GRAPHICS_PERFORMANCE_MODES_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_MANIFEST.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P00_bootstrap.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P08_media_surface_proxy_adoption.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P08_media_surface_proxy_adoption_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P09_perf_harness_modes_heavy_media_PROMPT.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P10_docs_traceability.md`
  - `docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_P10_docs_traceability_PROMPT.md`
- This packet is documentation-only bootstrap work.
- Add only the narrow `.gitignore` exception required for this packet directory.
