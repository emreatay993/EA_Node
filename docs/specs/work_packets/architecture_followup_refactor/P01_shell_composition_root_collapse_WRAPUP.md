## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/architecture-followup-refactor/p01-shell-composition-root-collapse`
- Commit Owner: `worker`
- Commit SHA: `c80c68cf5232ca9dd6cee5141cfd94e9bed264cc`
- Changed Files: `docs/specs/work_packets/architecture_followup_refactor/P01_shell_composition_root_collapse_WRAPUP.md`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `tests/main_window_shell/bridge_contracts.py`, `tests/main_window_shell/shell_runtime_contracts.py`, `tests/test_main_bootstrap.py`, `tests/test_main_window_shell.py`
- Artifacts Produced: `docs/specs/work_packets/architecture_followup_refactor/P01_shell_composition_root_collapse_WRAPUP.md`

- Added `ShellRuntimeDependencies` so `composition.py` now constructs and attaches viewer-session and viewer-host services instead of leaving `ShellWindow` to synthesize them lazily.
- Moved packet-owned host alias attachment for split canvas bridges and workspace-library controller sub-surfaces into `ShellControllerDependencies` and `ShellContextBridgeDependencies`, keeping the composition bundle as the packet-owned startup authority.
- Replaced the host-side QML context binding factory with an explicit composition-built binding tuple and trimmed `shell_context_bootstrap.py` down to QML bootstrap responsibilities only.
- Slimmed `ShellWindow` by removing packet-owned composition and alias-property setup while preserving top-level widget ownership, embedded viewer overlay lifecycle handling, and final event wiring.
- Updated the packet-owned bootstrap and runtime regression anchors to assert that viewer runtime services are exported through the composition-owned context-property bundle and remain synchronized with host aliases.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree build from `C:\Users\emre_\w\ea-node-editor-p01` with `.\venv\Scripts\python.exe main.py` in a normal desktop session.

1. Startup smoke
Action: open the application and let the main shell finish loading.
Expected result: the shell window opens without a QML error dialog, the main canvas is visible, and the library/workspace/inspector panels populate normally.

2. Embedded viewer host smoke
Action: if a viewer-backed node is available in the registry, add one to the graph, trigger the path that shows its embedded viewer, then switch focus away from and back to the window.
Expected result: the embedded viewer stays attached to the shell surface, focus changes do not leave a stale overlay behind, and no startup or runtime error banner appears.

## Residual Risks

- `ShellWindow` still carries broad command and controller delegation methods by design; that remaining facade narrowing is deferred to `P02`.
- The packet verification set covered the inherited bootstrap and runtime anchors, but it did not rerun the broader viewer-specific suites outside the packet-owned command list.

## Ready for Integration

- Yes: the packet-owned composition root is singular for shell startup, the required regression anchors passed, and the remaining host-surface narrowing is an explicit `P02` follow-up.
