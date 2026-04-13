# TITLE_ICONS_FOR_NON_PASSIVE_NODES P01: Path Resolver and Payload Contract

## Objective
- Add the central Python resolver for node-title icon paths and expose a derived live graph payload field, `icon_source`, only for non-passive nodes with valid local image paths.

## Preconditions
- `P00` is marked `PASS` in [TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md](./TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md).
- No later `TITLE_ICONS_FOR_NON_PASSIVE_NODES` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/ui_qml/node_title_icon_sources.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_node_title_icon_sources.py`
- `tests/test_registry_validation.py`
- `tests/test_passive_visual_metadata.py`

## Conservative Write Scope
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/ui_qml/node_title_icon_sources.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_node_title_icon_sources.py`
- `tests/test_registry_validation.py`
- `tests/test_passive_visual_metadata.py`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/TITLE_ICONS_FOR_NON_PASSIVE_NODES_STATUS.md`
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P01_path_resolver_and_payload_contract_WRAPUP.md`

## Required Behavior
- Keep `NodeTypeSpec.icon: str` unchanged as the authoring field.
- Add one central resolver that accepts the authored icon string plus enough registry or plugin provenance context to resolve:
  - absolute local paths when the file exists, is readable, and has a supported suffix
  - built-in relative paths from a dedicated node-title icon asset root
  - file and package plugin relative paths from safe plugin provenance roots when available
- Return a QML-safe local source URL string for valid paths and `""` for empty values, missing files, unreadable files, unsupported suffixes, remote URLs, data URIs, symbolic icon names, or plugin-relative paths without a safe root.
- Do not add cwd-relative fallback behavior.
- Thread registry descriptor/provenance information into live scene payload construction without persisting any new `.sfe` field.
- Add `icon_source` to each live graph node payload with a non-empty value only when:
  - `spec.runtime_behavior` is `active` or `compile_only`
  - the resolver returns a non-empty local source URL
- Ensure passive nodes get `icon_source == ""` even when their specs carry valid-looking icon metadata.
- Preserve existing payload fields including `icon` if they are currently emitted for library or compatibility callers, but do not make QML title rendering depend on symbolic names.
- Add packet-owned regression tests whose names include `title_icon` so the targeted verification commands below remain stable.

## Non-Goals
- No QML rendering changes in this packet.
- No Graphics Settings or icon-size preference changes.
- No built-in node spec migration and no new packaged node-title assets yet.
- No project-file persistence or `.sfe` schema migration.
- No node-library or inspector icon behavior changes.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_sources.py tests/test_registry_validation.py tests/test_passive_visual_metadata.py -k title_icon --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_node_title_icon_sources.py -k title_icon --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/title_icons_for_non_passive_nodes/P01_path_resolver_and_payload_contract_WRAPUP.md`
- `ea_node_editor/ui_qml/node_title_icon_sources.py`
- `tests/test_node_title_icon_sources.py`

## Acceptance Criteria
- Valid absolute SVG, PNG, JPG, and JPEG paths resolve to QML-safe local source URLs.
- Valid plugin-root-relative SVG, PNG, JPG, and JPEG paths resolve when plugin provenance supplies a safe root.
- Missing files, unreadable files, unsupported suffixes, remote/data URLs, empty strings, and symbolic names resolve to `""`.
- Active and `compile_only` node payloads with valid paths include non-empty `icon_source`.
- Passive node payloads keep `icon_source == ""`.
- No project persistence tests or saved document payloads require changes for this derived field.

## Handoff Notes
- `P03` consumes the `icon_source` payload field. Any rename or payload-shape change after this packet must inherit and update `tests/test_passive_visual_metadata.py` and `tests/test_node_title_icon_sources.py`.
- `P04` consumes the resolver's built-in asset-root contract when migrating built-in non-passive specs. If P04 changes the asset root or relative-path convention, it must inherit and update `tests/test_node_title_icon_sources.py`.
