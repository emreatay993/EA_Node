# NESTED_NODE_CATEGORIES P01: SDK Category Path Contract

## Objective
- Introduce `category_path` as the authoritative node-category schema, validation contract, and helper API so later registry, library, and QML packets can migrate off flat string categories without breaking packet-external display consumers immediately.

## Preconditions
- `P00` is marked `PASS` in [NESTED_NODE_CATEGORIES_STATUS.md](./NESTED_NODE_CATEGORIES_STATUS.md).
- No later `NESTED_NODE_CATEGORIES` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/nodes/category_paths.py`
- `ea_node_editor/nodes/node_specs.py`
- `ea_node_editor/nodes/decorators.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/builtins/**/*.py`
- `tests/test_decorator_sdk.py`
- `tests/test_registry_validation.py`

## Conservative Write Scope
- `ea_node_editor/nodes/category_paths.py`
- `ea_node_editor/nodes/node_specs.py`
- `ea_node_editor/nodes/decorators.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/builtins/**/*.py`
- `tests/test_decorator_sdk.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/nested_node_categories/NESTED_NODE_CATEGORIES_STATUS.md`
- `docs/specs/work_packets/nested_node_categories/P01_sdk_category_path_contract_WRAPUP.md`

## Required Behavior
- Add one packet-owned helper surface for category paths that later packets reuse for normalization, display, stable keys, and prefix matching.
- Replace mutable `NodeTypeSpec.category` storage with `category_path` tuple storage as the only authoritative category field.
- Validate category paths as `1..10` non-empty trimmed segments and reject empty, whitespace-only, or `11`-segment inputs.
- Preserve a read-only compatibility `category` display string for packet-external consumers that still need rendered text before later library/QML packets finish migrating.
- Update decorator authoring to accept `category_path=` and migrate in-repo built-in node declarations under the packet write scope to tuple paths.
- If a temporary `category=` compatibility shim is needed to keep packet-local tests green, keep it packet-local, document it in the wrap-up, and ensure no in-repo built-in declarations still rely on it when this packet is done.
- Keep most built-in families single-segment after the migration in this packet. The real nested Ansys DPF taxonomy is deferred to `P02`.
- Add packet-owned regression tests whose names include `nested_category_sdk` so the targeted verification commands below remain stable, including explicit proof that `1`-level and `10`-level paths are accepted while `11`-level paths are rejected.

## Non-Goals
- No descendant-inclusive registry filtering yet beyond helper-level primitives needed for later packets.
- No Python library trie/grouped-row rewrite yet.
- No QML nested category rendering yet.
- No documentation or requirements updates yet.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_decorator_sdk.py tests/test_registry_validation.py -k nested_category_sdk --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py -k nested_category_sdk --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/nested_node_categories/P01_sdk_category_path_contract_WRAPUP.md`

## Acceptance Criteria
- `NodeTypeSpec` stores normalized `category_path` tuples and rejects invalid depth or segment content.
- Packet-owned regressions explicitly prove `1`-level and `10`-level paths are accepted and `11`-level paths are rejected.
- The decorator authoring surface and built-in node declarations inside packet scope use `category_path=`.
- A read-only compatibility display string still exists for packet-external consumers that have not migrated yet, but the packet wrap-up makes clear that it is not authoritative state.
- The packet-owned `nested_category_sdk` regressions pass and prove the schema/default validation behavior.

## Handoff Notes
- `P02` consumes the packet-owned helper API for descendant-inclusive registry filtering and DPF taxonomy expansion. Do not rename helper entry points after this packet.
- Any later packet that removes or narrows the temporary compatibility display path must inherit and update the `nested_category_sdk` regressions.
