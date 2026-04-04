from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from scripts import verification_manifest as manifest
from tests.shell_isolation_runtime import format_child_output
from tests.shell_isolation_runtime import list_target_ids
from tests.shell_isolation_runtime import load_target_registry
from tests.shell_isolation_runtime import resolve_target
from tests.shell_isolation_runtime import run_shell_isolation_target
from tests.shell_isolation_runtime import shell_lifecycle_contract

REPO_ROOT = Path(__file__).resolve().parents[1]


def _target_params():
    target_ids = list_target_ids()
    if target_ids:
        return [pytest.param(target_id, id=target_id) for target_id in target_ids]
    return [
        pytest.param(
            "",
            id="no-targets",
            marks=pytest.mark.skip(reason="Shell isolation target catalogs are empty in P01."),
        )
    ]


def _parse_module(relative_path: str) -> ast.Module:
    path = REPO_ROOT / relative_path
    return ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)


def _public_test_classes(relative_path: str) -> tuple[str, ...]:
    tree = _parse_module(relative_path)
    names = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_") and node.name.endswith("Tests")
    ]
    return tuple(sorted(names))


def _test_methods(relative_path: str, class_name: str) -> tuple[str, ...]:
    tree = _parse_module(relative_path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return tuple(
                sorted(
                    item.name
                    for item in node.body
                    if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
                )
            )
    raise AssertionError(f"Missing test class {class_name!r} in {relative_path}.")


def _discovered_shell_sources() -> set[str]:
    discovered: set[str] = set()
    main_window_dir = REPO_ROOT / "tests" / "main_window_shell"
    for path in sorted(main_window_dir.glob("*.py")):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        if relative_path.endswith(("__init__.py", "base.py")):
            continue
        if _public_test_classes(relative_path):
            discovered.add(relative_path)
    for relative_path in (
        "tests/test_main_window_shell.py",
        "tests/test_script_editor_dock.py",
        "tests/test_shell_run_controller.py",
        "tests/test_shell_project_session_controller.py",
    ):
        if _public_test_classes(relative_path):
            discovered.add(relative_path)
    return discovered


def _dotted_module_to_path(module_name: str) -> str:
    return f"{module_name.replace('.', '/')}.py"


def _target_index():
    registry = load_target_registry()
    ignore_count = len(manifest.worktree_pytest_ignore_args())
    module_targets: set[str] = set()
    pytest_class_targets: dict[str, set[str]] = defaultdict(set)
    unittest_method_targets: dict[tuple[str, str], set[str]] = defaultdict(set)
    scenario_targets: dict[tuple[str, str], set[str]] = defaultdict(set)

    for target in registry.values():
        command = target.command
        if command[:3] == (sys.executable, "-m", "unittest"):
            for dotted_target in command[3:]:
                parts = dotted_target.split(".")
                if parts[-1].startswith("test_"):
                    source_path = _dotted_module_to_path(".".join(parts[:-2]))
                    unittest_method_targets[(source_path, parts[-2])].add(parts[-1])
                else:
                    module_targets.add(_dotted_module_to_path(dotted_target))
            continue

        if (
            len(command) == 5
            and command[:3] == (sys.executable, "-m", "tests.test_shell_project_session_controller")
            and command[3] == "--scenario"
        ):
            scenario_targets[
                ("tests/test_shell_project_session_controller.py", "ShellProjectSessionControllerTests")
            ].add(command[4])
            continue

        if command[0] != sys.executable or command[1:3] != ("-m", "pytest"):
            continue
        nodeids = command[3 + ignore_count : -1]
        for nodeid in nodeids:
            parts = nodeid.replace("\\", "/").split("::")
            if len(parts) >= 2:
                pytest_class_targets[parts[0]].add(parts[1])

    return module_targets, pytest_class_targets, unittest_method_targets, scenario_targets


def _assert_ownership_rule(
    spec: manifest.ShellIsolationOwnershipSpec,
    *,
    module_targets: set[str],
    pytest_class_targets: dict[str, set[str]],
    unittest_method_targets: dict[tuple[str, str], set[str]],
    scenario_targets: dict[tuple[str, str], set[str]],
) -> None:
    if spec.coverage_kind == "module_target":
        assert spec.source_path in module_targets
        return

    if spec.coverage_kind == "class_targets":
        discovered = set(_public_test_classes(spec.source_path))
        expected = {
            name
            for name in spec.covered_names
            if not name.startswith("_")
        } | set(spec.excluded_names)
        assert discovered == expected
        assert set(spec.covered_names) <= pytest_class_targets.get(spec.source_path, set())
        return

    if spec.coverage_kind == "method_targets":
        assert spec.owner_name is not None
        discovered = set(_test_methods(spec.source_path, spec.owner_name))
        expected = set(spec.covered_names) | set(spec.excluded_names)
        assert discovered == expected
        assert set(spec.covered_names) <= unittest_method_targets.get(
            (spec.source_path, spec.owner_name),
            set(),
        )
        return

    if spec.coverage_kind == "scenario_targets":
        assert spec.owner_name is not None
        discovered = set(_test_methods(spec.source_path, spec.owner_name))
        expected = set(spec.covered_names) | set(spec.excluded_names)
        assert discovered == expected
        assert set(spec.covered_names) <= scenario_targets.get(
            (spec.source_path, spec.owner_name),
            set(),
        )
        return

    raise AssertionError(f"Unknown shell-isolation coverage kind: {spec.coverage_kind}")


def test_shell_isolation_target_catalogs_follow_manifest_owned_prefixes() -> None:
    registry = load_target_registry()

    assert registry
    allowed_prefixes = manifest.shell_isolation_target_id_prefixes()
    for target_id in registry:
        assert target_id.startswith(allowed_prefixes)


def test_shell_isolation_pytest_targets_use_manifest_owned_pytest_args() -> None:
    registry = load_target_registry()
    ignore_count = len(manifest.worktree_pytest_ignore_args())
    pytest_targets = [
        target
        for target in registry.values()
        if target.command[0] == sys.executable and target.command[1:3] == ("-m", "pytest")
    ]

    assert pytest_targets
    for target in pytest_targets:
        nodeids = target.command[3 + ignore_count : -1]
        expected = (sys.executable, *manifest.shell_isolation_target_pytest_args(*nodeids))
        assert target.command == expected


def test_shell_isolation_catalog_ownership_rules_cover_current_shell_surfaces() -> None:
    discovered = _discovered_shell_sources()
    owned = set(manifest.shell_isolation_ownership_specs_by_path())

    assert discovered == owned


def test_shell_isolation_catalogs_cover_manifest_owned_shell_surfaces() -> None:
    (
        module_targets,
        pytest_class_targets,
        unittest_method_targets,
        scenario_targets,
    ) = _target_index()

    for spec in manifest.SHELL_ISOLATION_OWNERSHIP_SPECS:
        _assert_ownership_rule(
            spec,
            module_targets=module_targets,
            pytest_class_targets=pytest_class_targets,
            unittest_method_targets=unittest_method_targets,
            scenario_targets=scenario_targets,
        )


def test_shell_lifecycle_contract_registers_packet_owned_gui_regression() -> None:
    contract = shell_lifecycle_contract()
    lifecycle_test_path = Path(contract["lifecycle_test_path"])

    assert contract["truth"]
    assert contract["shared_window_scope"]
    assert lifecycle_test_path.is_file()
    assert lifecycle_test_path.as_posix() in manifest.GUI_TEST_PATHS


@pytest.mark.parametrize(
    "target_id",
    _target_params(),
)
def test_shell_isolation_target(target_id: str) -> None:
    target = resolve_target(target_id)
    completed = run_shell_isolation_target(target)
    if completed.returncode == 0:
        return
    pytest.fail(
        "Shell isolation child process failed "
        f"for {target_id} (exit={completed.returncode}).\n"
        f"Command: {' '.join(target.command)}\n"
        f"{format_child_output(completed)}",
        pytrace=False,
    )
