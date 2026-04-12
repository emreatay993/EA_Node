# Port Value Locking QA Matrix

- Updated: `2026-04-12`
- Packet set: retained `PORT_VALUE_LOCKING` (`P01` through `P06`)
- Scope: final closeout matrix for the shipped persisted primitive-port lock state, one-way auto-lock, locked incoming-edge rejection, manual lock toggle, per-view `hide_locked_ports` / `hide_optional_ports` decluttering controls, empty-canvas gestures, persistence, undo/redo, and traceability/docs evidence.

## Locked Scope

- A port is lockable only when it is an input data port with `data_type` in `{"int", "float", "bool", "str"}` and a same-key `PropertySpec` exists on the owning node type.
- One-way auto-lock remains the shipped rule: meaningful inline/default values may set a lock, but returning the property to zero or empty does not auto-unlock the port.
- Manual lock and unlock do not rewrite property values. They change only incoming-edge eligibility and the locked-row chrome.
- Locked primitive rows keep their inline editors and padlock affordance while suppressing incoming-edge drop eligibility and stale drag-target acceptance.
- `hide_locked_ports` and `hide_optional_ports` remain `ViewState` flags. They hide only active-view rows and do not rewrite node data or global project defaults.
- Empty-canvas decluttering gestures remain `Ctrl-double-click`, middle-mouse plus left-click for `hide_locked_ports`, and middle-mouse plus right-click for `hide_optional_ports`.

## Retained Automated Verification

| Coverage Area | Packet | Primary Requirement Anchors | Command | Recorded Source |
|---|---|---|---|---|
| Durable `locked_ports`, `hide_locked_ports`, and `hide_optional_ports` round-trip through codec and serializer paths | `P01` | `REQ-PERSIST-021`, `AC-REQ-PERSIST-021-01` | `.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py tests/test_serializer.py --ignore=venv -q` | Accepted `P01` packet commit `dfef8d2f5110d3893c09ba17a170853c8ead7cc6` |
| One-way auto-lock, locked incoming-edge rejection, manual backend toggle, and fragment-retention invariants | `P02` | `REQ-GRAPH-019`, `AC-REQ-GRAPH-019-01` | `.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py tests/graph_track_b/scene_model_graph_scene_suite.py --ignore=venv -q` | Accepted `P02` packet commit `1f513f155fbc3577cad82b5fee2168b9e1a908b3` |
| Scene command exposure, locked/optional payload projection, active-view filtering, and undo/redo-safe view-local state | `P03` | `REQ-GRAPH-020`, `AC-REQ-GRAPH-020-01`, `REQ-PERF-012` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/main_window_shell/view_library_inspector.py tests/graph_surface/passive_host_boundary_suite.py --ignore=venv -q` | Accepted `P03` packet commit `32be122133585ac75acb1630dd4bf320356d68e0` |
| Locked-row chrome, suppressed locked targets, and node-surface manual toggle behavior without losing inline editors | `P04` | `REQ-UI-036`, `AC-REQ-UI-036-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py --ignore=venv -q` | Accepted `P04` packet commit `d8a86c0da41276600febbed81acaefccc86fd03e` |
| Empty-canvas `hide_locked_ports` / `hide_optional_ports` gestures, canvas routing, and active-view decluttering persistence | `P05` | `REQ-UI-037`, `AC-REQ-UI-037-01`, `AC-REQ-PERF-012-01` | `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/pointer_and_modal_suite.py tests/graph_track_b/qml_preference_performance_suite.py --ignore=venv -q` | Accepted `P05` packet commit `0fd842953f464795190c1d6f199dcdcaae82cbad` |

## Final Closeout Commands

| Command | Purpose |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Packet-owned traceability regression for the canonical port value locking closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | Review-gate proof audit for the retained requirement, QA, index, and traceability docs |

## 2026-04-12 Execution Results

| Command | Result | Notes |
|---|---|---|
| `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability tests confirmed the new QA matrix, spec-index registration, requirement anchors, and traceability rows for the port value locking closeout surface |
| `.\venv\Scripts\python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the index, requirements, QA matrix, and traceability updates landed in this packet worktree |

## Remaining Manual Smoke Checks

1. Auto-lock and rejection check: start a desktop Qt session, add `core.logger`, and confirm the default `message` input starts locked from its non-empty default value and rejects a new incoming connection until you unlock it.
2. Manual toggle and property-preservation check: double-click the lock affordance on a lockable primitive input, confirm the row chrome flips immediately, and verify the underlying property value stays unchanged while connection eligibility changes.
3. View-local decluttering check: create a second view, hide locked and optional rows there, switch between views, and confirm each view preserves its own row visibility without mutating the other view.
4. Empty-canvas gesture check: on empty canvas space, verify `Ctrl-double-click`, middle-mouse plus left-click, and middle-mouse plus right-click toggle the expected decluttering state without opening quick insert, starting box zoom, or beginning a pan.
5. Persistence and history check: save and reopen the project, confirm locked state and view-local hide filters survive, then use undo/redo on manual lock toggles and hide-filter changes to confirm the payload and canvas return to the prior state cleanly.

## Residual Desktop-Only Validation

- Offscreen automated coverage does not validate final padlock chrome contrast, row tint perception, or the feel of the empty-canvas chords on physical mouse hardware in a real Windows desktop compositor.
- The feature intentionally keeps locked rows on the existing inline-editor host surface, so manual desktop checks should still confirm dense nodes do not clip, shift, or crowd when lock state changes repeatedly.
- View-local decluttering is covered by automated payload/history tests, but manual desktop acceptance should still confirm there is no confusion when one view hides rows that remain visible in another.

## Residual Risks

- The closeout matrix depends on retained `P01` through `P05` packet-local regressions and accepted packet commits because `P06` is intentionally docs-and-traceability-only.
- Physical mouse ergonomics for the empty-canvas gestures and final visual polish for the locked-row chrome remain desktop-only validation even though the offscreen packet regressions passed.
