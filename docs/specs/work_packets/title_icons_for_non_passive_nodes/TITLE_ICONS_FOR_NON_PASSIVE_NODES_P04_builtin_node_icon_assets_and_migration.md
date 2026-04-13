# TITLE_ICONS_FOR_NON_PASSIVE_NODES P04: Built-In Node Icon Assets and Migration

## Objective
- Add repo-managed node-title icon assets and migrate supported active and `compile_only` built-in node specs from symbolic icon names to stable path-based image references.

## Preconditions
- `P01` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- No later `TITLE_ICONS_FOR_NON_PASSIVE_NODES` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/assets/node_title_icons/**`
- `ea_node_editor/nodes/builtins/core.py`
- `ea_node_editor/nodes/builtins/hpc.py`
- `ea_node_editor/nodes/builtins/integrations_email.py`
- `ea_node_editor/nodes/builtins/integrations_file_io.py`
- `ea_node_editor/nodes/builtins/integrations_process.py`
- `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`
- `ea_node_editor/nodes/builtins/subnode.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer.py`
- `pyproject.toml`
- `ea_node_editor.spec`
- `tests/test_node_title_icon_assets.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_registry_validation.py`
- `tests/test_passive_node_contracts.py`
- `tests/test_passive_flowchart_catalog.py`

## Conservative Write Scope
- `ea_node_editor/assets/node_title_icons/**`
- `ea_node_editor/nodes/builtins/core.py`
- `ea_node_editor/nodes/builtins/hpc.py`
- `ea_node_editor/nodes/builtins/integrations_email.py`
- `ea_node_editor/nodes/builtins/integrations_file_io.py`
- `ea_node_editor/nodes/builtins/integrations_process.py`
- `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`
- `ea_node_editor/nodes/builtins/subnode.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer.py`
- `pyproject.toml`
- `ea_node_editor.spec`
- `tests/test_node_title_icon_assets.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_registry_validation.py`
- `tests/test_passive_node_contracts.py`
- `tests/test_passive_flowchart_catalog.py`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P04_builtin_node_icon_assets_and_migration_WRAPUP.md`

## Required Behavior
- Add a dedicated packaged asset family at `ea_node_editor/assets/node_title_icons/`.
- Prefer SVG assets for built-in title icons. Use PNG/JPG/JPEG only when an SVG is not practical.
- Name assets predictably from their migrated icon meaning so built-in specs reference stable relative paths.
- Update packaging metadata so the new asset family is included in installed packages and PyInstaller builds.
- Migrate only active and `compile_only` built-in node specs that should show title icons.
- Leave passive built-in icon metadata unchanged unless a passive metadata test needs a non-behavioral expectation update.
- Do not migrate symbolic names used only by passive title/body rendering, shell icons, node-library tiles, or inspector metadata.
- Keep every migrated built-in `icon` value as a resolver-compatible relative path under the P01 built-in asset root.
- Do not use the existing tintable `image://ui-icons` provider for node-title icon assets.
- Add packet-owned asset inventory tests whose names include `title_icon` and prove:
  - all migrated non-passive built-ins reference existing supported local files
  - symbolic icon names remain unrendered unless converted to paths
  - packaged asset metadata includes the new asset family
  - passive built-in nodes remain title-icon ineligible

## Non-Goals
- No resolver or payload-shape changes except tests inheriting the P01 contract if asset-root expectations need adjustment.
- No QML header rendering changes.
- No icon-size preference changes.
- No node-library or inspector migration.
- No passive-node title-icon rollout.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_assets.py tests/test_registry_validation.py -k title_icon --ignore=venv -q`
2. `.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_passive_node_contracts.py tests/test_passive_flowchart_catalog.py -k title_icon --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_assets.py -k title_icon --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P04_builtin_node_icon_assets_and_migration_WRAPUP.md`
- `ea_node_editor/assets/node_title_icons/*.svg`
- `tests/test_node_title_icon_assets.py`

## Acceptance Criteria
- The dedicated `ea_node_editor/assets/node_title_icons/` family exists and is packaged.
- Migrated active and `compile_only` built-in node specs reference resolver-compatible asset paths.
- All migrated asset paths exist and use supported suffixes.
- Passive built-in nodes remain title-icon ineligible.
- Existing shell/theme icon registry behavior remains separate from node-title icon assets.
- Packet-owned `title_icon` asset and catalog regressions pass.

## Handoff Notes
- P04 may run in the same execution wave as P03 because their primary source write scopes are disjoint, but it must not change P03's QML title layout or object names.
- Any later packet that changes built-in asset root, packaged asset metadata, or migrated built-in icon paths must inherit and update `tests/test_node_title_icon_assets.py`.
