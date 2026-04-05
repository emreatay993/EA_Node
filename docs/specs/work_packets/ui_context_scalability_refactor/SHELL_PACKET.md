# Shell Packet

Baseline packet: `P01 Shell Window Facade Collapse`.

Use this contract when a UI change touches shell lifecycle, QML context-property export, top-level actions or menus, host teardown, or the final shell-to-bridge wiring path.

## Owner Files

- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state_helpers.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`

## Public Entry Points

- `ShellWindow`
- `create_shell_window()`
- `build_shell_window_composition()`
- `bootstrap_shell_window()`
- The `ShellContextPropertyBindings` export surface consumed by `bootstrap_shell_qml_context()`

## State Owner

- `ShellWindow` owns Qt lifecycle, top-level widget ownership, context-property attachment, and final signal wiring.
- `ShellState`, the controllers assembled in `composition.py`, and the exported bridges own workflow-specific state; the shell host delegates to them instead of becoming a second source of truth.

## Allowed Dependencies

- Shell packet code may compose controllers, presenters, bridges, theme or preference services, session stores, and execution clients.
- Shell packet code may consume graph-canvas and viewer public interfaces, but it must do so through their documented bridge or host surfaces.
- Shell packet docs or tests may update inherited lifecycle and bridge anchors when exported host contracts change.

## Invariants

- `window.py` stays lifecycle-first and Qt-first.
- Menu and action construction stays in `window_actions.py`.
- Graph-search, quick-insert, graph-hint, and graphics-preference helper logic stays in `window_state_helpers.py`.
- Packet-owned QML receives focused bridges and context-property bindings rather than new raw host globals.
- Shell teardown clears viewer and session state before execution shutdown completes.

## Forbidden Shortcuts

- Do not move packet-owned workflow logic back into `window.py`.
- Do not export new raw host globals to packet-owned QML when a focused bridge exists or should be added.
- Do not duplicate graphics, search, or quick-insert state between shell host code and presenters.
- Do not bypass `bootstrap_shell_qml_context()` or the composition path when wiring packet-owned context properties.

## Required Tests

- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_window_lifecycle.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`
