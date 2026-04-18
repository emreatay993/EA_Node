# ANSYS_DPF_FULL_PLUGIN_ROLLOUT P01: Versioned Plugin Lifecycle

## Objective

- Make the DPF backend version-aware so startup can detect `ansys.dpf.core` version changes, invalidate or rebuild the generated descriptor cache, and persist the exact library version without mutating saved projects.

## Preconditions

- `P00` is marked `PASS` in [ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md](./ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md).
- No later `ANSYS_DPF_FULL_PLUGIN_ROLLOUT` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `tests/test_app_preferences.py`
- `tests/test_dpf_node_catalog.py`

## Conservative Write Scope

- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `tests/test_app_preferences.py`
- `tests/test_dpf_node_catalog.py`
- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P01_versioned_plugin_lifecycle_WRAPUP.md`

## Required Behavior

- Resolve `ansys.dpf.core.__version__` from the active project venv when the dependency is available.
- Persist the DPF plugin version exactly as the library version string.
- Detect version changes at startup and invalidate or rebuild generated DPF descriptor cache state before later packets rely on it.
- Keep the same-version startup path fast and side-effect-light.
- Preserve startup behavior when DPF is absent and keep project documents untouched.

## Non-Goals

- No node contract expansion yet; that belongs to `P02`.
- No taxonomy or generated catalog rollout yet; that belongs to `P03` through `P05`.
- No runtime or persistence rewrite yet; that belongs to `P06`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_dpf_node_catalog.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py --ignore=venv -q
```

## Expected Artifacts

- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P01_versioned_plugin_lifecycle_WRAPUP.md`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `tests/test_app_preferences.py`
- `tests/test_dpf_node_catalog.py`

## Acceptance Criteria

- Startup records the exact installed DPF version when DPF is available.
- Startup detects a changed DPF version and forces descriptor-cache refresh before generated catalog use.
- Startup with unchanged version avoids unnecessary rebuild.
- Startup without DPF remains usable and does not rewrite project files.

## Handoff Notes

- `P02` may assume that version-aware cache invalidation exists and that app-global plugin version state is available through app preferences.
