Implement GRAPH_CANVAS_INTERACTION_PERF_P09_evidence_refresh_traceability.md exactly. Before editing, read GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md, GRAPH_CANVAS_INTERACTION_PERF_STATUS.md, and GRAPH_CANVAS_INTERACTION_PERF_P09_evidence_refresh_traceability.md. Implement only P09. Stay inside the packet write scope, preserve locked defaults and current full-fidelity visuals unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update GRAPH_CANVAS_INTERACTION_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P09; do not start any later packet.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- `Commit Owner` must be one of `worker`, `executor`, or `executor-pending`; do not write a username or email address.
- `Commit SHA` must be the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or prose placeholder text.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and any ledger entry using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Execution discipline:
- Prefer the narrowest packet-owned rerun during development and remediation; do not substitute broader repo-wide verification unless this packet explicitly requires it.
- This is the only packet allowed to refresh checked-in perf evidence and canonical artifact outputs, and it must complete the same-machine offscreen full/max/node-drag captures plus the Windows desktop/manual exit gate before closing. Do not pull runtime optimization work into this packet unless a tiny in-scope truthfulness fix is strictly required.

Notes:
- Target branch: `codex/graph-canvas-interaction-perf/p09-evidence-refresh-traceability`
- Review Gate: `./venv/Scripts/python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/graph_canvas_interaction_perf/P09_evidence_refresh_traceability_WRAPUP.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_interaction_perf_p09_full_fidelity/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_interaction_perf_p09_full_fidelity/track_h_benchmark_report.json`
  - `artifacts/graph_canvas_interaction_perf_p09_max_performance/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_interaction_perf_p09_max_performance/track_h_benchmark_report.json`
  - `artifacts/graph_canvas_interaction_perf_p09_node_drag_control/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_interaction_perf_p09_node_drag_control/track_h_benchmark_report.json`
  - `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json`
  - `artifacts/graphics_performance_modes_docs/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json`
