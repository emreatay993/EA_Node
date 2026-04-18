# P01 Versioned Plugin Lifecycle Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/ansys-dpf-full-plugin-rollout/p01-versioned-plugin-lifecycle`
- Commit Owner: `executor`
- Commit SHA: `46aa710bbeff264b85757e507b320dcbc793d137`
- Changed Files:
  - `ea_node_editor/settings.py`
  - `ea_node_editor/app_preferences.py`
  - `ea_node_editor/nodes/bootstrap.py`
  - `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
  - `tests/test_app_preferences.py`
  - `tests/test_dpf_node_catalog.py`
- Artifacts Produced:
  - `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P01_versioned_plugin_lifecycle_WRAPUP.md`
  - `ea_node_editor/settings.py`
  - `ea_node_editor/app_preferences.py`
  - `ea_node_editor/nodes/bootstrap.py`
  - `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
  - `tests/test_app_preferences.py`
  - `tests/test_dpf_node_catalog.py`

## Implementation Notes

- Added app-global DPF plugin state under app preferences so the exact installed `ansys.dpf.core.__version__` string and the DPF descriptor-cache version token are persisted outside project documents.
- Added a version-keyed in-process descriptor cache for the builtin DPF catalog, plus explicit invalidation and startup synchronization hooks.
- Updated bootstrap so DPF version synchronization runs before builtin DPF backend registration, which primes the descriptor cache only when the recorded version changes.
- Added packet-owned tests for app-preferences normalization and for startup behavior across version-changed, version-unchanged, and dependency-missing paths.

## Verification

- `.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_dpf_node_catalog.py --ignore=venv -q`
  - Result: `20 passed, 9 subtests passed in 20.41s`
- `.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py --ignore=venv -q`
  - Result: `3 passed in 10.20s`
- Final Verification Verdict: PASS

## Residual Risks

- The packet only persists the DPF version and descriptor-cache version token; later packets still need to decide where descriptor payloads themselves live once generated catalog persistence is introduced.
- Same-version startup avoids the extra cache-prime step, but registry construction still materializes descriptors when the builtin DPF backend is actually registered.

## Ready for Integration

Yes: DPF startup now records the exact installed version, refreshes the builtin descriptor cache on version change, and preserves the missing-dependency path without touching `.sfe` documents.
