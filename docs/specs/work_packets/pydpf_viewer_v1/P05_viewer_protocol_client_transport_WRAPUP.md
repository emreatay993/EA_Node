# P05 Viewer Protocol Client Transport Wrap-Up

## Implementation Summary
- Packet: `P05`
- Branch Label: `codex/pydpf-viewer-v1/p05-viewer-protocol-client-transport`
- Commit Owner: `executor`
- Commit SHA: `a09c17635dc903847928939417e3e99704e0f146`
- Changed Files: `ea_node_editor/execution/protocol.py, ea_node_editor/execution/client.py, tests/test_execution_viewer_protocol.py, tests/test_execution_client.py, docs/specs/work_packets/pydpf_viewer_v1/P05_viewer_protocol_client_transport_WRAPUP.md`
- Artifacts Produced: `ea_node_editor/execution/protocol.py, ea_node_editor/execution/client.py, tests/test_execution_viewer_protocol.py, tests/test_execution_client.py, docs/specs/work_packets/pydpf_viewer_v1/P05_viewer_protocol_client_transport_WRAPUP.md`
- Added additive viewer transport DTOs for `open_viewer_session`, `update_viewer_session`, `close_viewer_session`, and `materialize_viewer_data`, plus viewer success and failure events.
- Added viewer-payload guards so `data_refs`, `summary`, and `options` stay JSON-safe and only carry scalars, lists, dictionaries, `handle_ref`, or `artifact_ref` values.
- Extended `ProcessExecutionClient` with correlated viewer request ids, packet-owned viewer APIs, and derived `viewer_session_failed` routing for worker-side `protocol_error` responses without changing existing run lifecycle dispatch.
- Final command payload shapes:
  - `open_viewer_session` and `update_viewer_session`: `{type, request_id, workspace_id, node_id, session_id, data_refs, summary, options}`
  - `close_viewer_session` and `materialize_viewer_data`: `{type, request_id, workspace_id, node_id, session_id, options}`
- Final event payload shapes:
  - `viewer_session_opened`, `viewer_session_updated`, and `viewer_data_materialized`: `{type, request_id, workspace_id, node_id, session_id, data_refs, summary, options}`
  - `viewer_session_closed`: `{type, request_id, workspace_id, node_id, session_id, summary, options}`
  - `viewer_session_failed`: `{type, request_id, workspace_id, node_id, session_id, command, error}`

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_execution_client.py --ignore=venv -q` (`11 passed, 9 subtests passed in 4.99s`)
- PASS: Review Gate `./venv/Scripts/python.exe -m pytest tests/test_execution_viewer_protocol.py --ignore=venv -q` (`3 passed, 9 subtests passed in 0.06s`)
- Final Verification Verdict: PASS

## Manual Test Directives
Too soon for manual testing

- Blocker: `P05` only adds protocol and client transport; `P06` still has to implement worker-side handling for the new viewer commands.
- Blocker: No shell bridge, QML surface, or native viewer session consumer exists in this packet, so there is no end-to-end user workflow to exercise manually.
- Next worthwhile milestone: run manual transport and viewer smoke checks after `P06` can answer the new commands, or after later shell/UI packets expose the viewer session path.

## Residual Risks
- Until `P06` lands, the worker still treats viewer commands as unknown operations and answers with `protocol_error`; the client now correlates that back into `viewer_session_failed`, but there is no successful worker execution path yet.
- The payload contract is transport-stable, but later packets must keep the documented field names unchanged because `P10` and `P13` will bind to them from the UI side.

## Ready for Integration
- Yes: The viewer protocol and client transport surface are implemented, verified, and ready for `P06` to attach worker-side behavior on the exact command and event names documented above.
