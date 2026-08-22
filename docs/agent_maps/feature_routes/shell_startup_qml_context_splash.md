# Shell Startup, QML Context, And Splash

## Purpose
Use this for startup handoff, QML context bootstrap, shell root loading, splash screen behavior, and app lifecycle.

## Start Here
- `ea_node_editor/bootstrap.py`
- `ea_node_editor/app.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/qml_host_factory.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui/splash/opening_screen.py`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/main_window_shell/test_qml_shell_roots.py --ignore=venv -q
```

## Breadcrumbs
- [Startup, Bootstrap, And App Lifecycle](../subsystems/startup_and_bootstrap.md)
- [QML Shell And Bridge Layer](../subsystems/qml_shell_and_bridges.md)

## Update Triggers
Update when launch path, shell context, splash handoff, or QML root loading changes.

## 2026-05-31 Shell Services Bundle Update

- `create_shell_window()` and direct `ShellWindow()` construction still build through shell composition, but `ShellWindowComposition` now attaches a single `ShellServices` reference to the host.
- `_build_shell_qml_host()` reads context-property and image-provider bindings from `host.shell_services.qml_context`; QML context names remain unchanged.

## 2026-06-01 Splash Z-Order Update

- `OpeningSplash` remains a frameless splash window, but it no longer uses `WindowStaysOnTopHint`; tests assert the normal desktop z-order behavior in `tests/test_main_bootstrap.py`.

## 2026-06-10 Shell Composition Package Update

- `create_shell_window()` (splash registry hand-in included) lives in `ea_node_editor/ui/shell/composition/bootstrap.py`; the QML context-property and image-provider bindings are built in `composition/qml_context.py` and still read from `host.shell_services.qml_context`. QML context names are unchanged.

## 2026-07-11 Performance Ownership

- Startup explicitly preloads PyArrow before QML construction and records QML `setSource()` separately. App import, process wall, shell create, QML load, and first-frame phases must remain distinct in reports.
