# Add-on Manager

## Purpose
Use this for add-on catalog metadata, add-on manager shell/QML payloads, dependency display, managed-package installation, and add-on tab behavior.

## Start Here
- `ea_node_editor/addons/catalog.py`
- `ea_node_editor/addons/hot_apply.py`
- `ea_node_editor/ui/shell/controllers/addon_manager_controller.py`
- `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`
- `ea_node_editor/ui/shell/presenters/_addon_manager_payloads.py`
- `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`
- `ea_node_editor/ui_qml/components/shell/AddOnManagerPane.qml`
- `ea_node_editor/execution/managed_runtime.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`

## Contracts
- Managed package setup has no default five-minute ceiling. The runtime command runner streams its latest phase/output line through the install worker and bridge to `AddOnManagerPane.qml`.
- Add-on setup reports the exact selected COREX Python path. Source runs use the active interpreter; frozen runs use the app-managed AppData interpreter.
- Keep progress transient and bridge-owned: QML displays only the latest line while installation is active, and thread cleanup clears it.
- Hot-apply registry replacement commits in this order: runtime services, graph scene, shell registry/serializer consumers, then the persisted enabled-state preference. A failed graph-scene replacement leaves the active scene/shell registry, serializers, and stored preference unchanged.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_managed_runtime.py tests/test_addon_manager_install.py tests/test_plugin_loader.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q
```

## Breadcrumbs
- [Add-ons](../subsystems/addons.md)
- [Tabular Data Add-on And Preview](tabular_data_addon_preview.md)
- [Ansys DPF Operator Nodes, Viewer, And Transport](ansys_dpf_operator_viewer_transport.md)
- [MARS Solver Add-on](mars_solver_addon.md)

## Update Triggers
Update when add-on catalog records, dependency/install metadata, asynchronous install behavior, add-on manager payloads, or add-on manager tests change.

## 2026-07-11 Performance Ownership

- `AddOnManagerPane` is a retained URL-backed loader: first open creates it, later opens reuse the same object. Preserve object name, geometry, z-order, focus, and close behavior.
