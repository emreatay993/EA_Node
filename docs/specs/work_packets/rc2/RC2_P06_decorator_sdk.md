# RC2 P06: Decorator Node SDK

## Objective
- Add decorator-based helpers for node specs while preserving backward compatibility for existing class-based plugins.

## Inputs
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`

## Allowed Files
- `ea_node_editor/nodes/decorators.py`
- `ea_node_editor/nodes/__init__.py`
- `ea_node_editor/nodes/builtins/core.py`
- `tests/test_decorator_sdk_rc2.py`
- `tests/test_registry_validation.py`
- `docs/specs/requirements/40_NODE_SDK.md`

## Do Not Touch
- `ea_node_editor/execution/*`

## Verification
1. `venv\Scripts\python -m unittest tests.test_registry_validation tests.test_decorator_sdk_rc2 -v`

## Output Artifacts
- Updated Node SDK docs with decorator usage examples.

## Merge Gate
- Registry validation remains green.
- New decorator SDK tests pass.

