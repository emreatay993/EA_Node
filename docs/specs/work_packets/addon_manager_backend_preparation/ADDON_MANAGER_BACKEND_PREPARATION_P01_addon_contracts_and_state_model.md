# ADDON_MANAGER_BACKEND_PREPARATION P01: Add-on Contracts And State Model

## Objective

- Establish the generic add-on record, apply-policy model, and persisted state contract that later packets use for locked-node messaging, DPF lifecycle, and Add-On Manager presentation.

## Preconditions

- `P00` is marked `PASS` in [ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md](./ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md).
- No later `ADDON_MANAGER_BACKEND_PREPARATION` packet is in progress.

## Execution Dependencies

- `P00`

## Target Subsystems

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/addons/**`
- `tests/test_plugin_loader.py`

## Conservative Write Scope

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/addons/**`
- `tests/test_plugin_loader.py`
- `docs/specs/work_packets/addon_manager_backend_preparation/P01_addon_contracts_and_state_model_WRAPUP.md`

## Required Behavior

- Introduce a generic add-on metadata contract that can represent installed, disabled, unavailable, and pending-restart add-ons without special-casing DPF.
- Define per-add-on `apply_policy` with exactly two values in this packet set: `hot_apply` and `restart_required`.
- Preserve compatibility with the current plugin discovery path and current project/workflow settings while adding a richer add-on state model in app preferences or a dedicated add-on state store.
- Make the contract capable of listing provided node types, add-on version/vendor metadata, dependencies, and summary/detail text for later UI packets.
- Preserve current startup behavior for non-add-on node families and existing plugin loading outside the new metadata layer.

## Non-Goals

- No menubar or QML surface work yet; that belongs to `P02` and `P07`.
- No unresolved-node canvas projection yet; that belongs to `P03`.
- No DPF extraction or runtime rebuild yet; those belong to `P05` and `P06`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/addon_manager_backend_preparation/P01_addon_contracts_and_state_model_WRAPUP.md`

## Acceptance Criteria

- Core code can describe add-ons with stable metadata and apply policy without assuming DPF-specific keys.
- Persisted app state can remember enabled/disabled intent plus restart-pending state for later packets.
- Plugin discovery and existing non-DPF plugin loading remain functional under the new contract.
- The inherited plugin-loader regression anchor passes.

## Handoff Notes

- `P02`, `P03`, `P05`, `P06`, and `P07` all consume this contract. Do not reopen field names or policy semantics later unless their inherited regression anchors prove it is necessary.
