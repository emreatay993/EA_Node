#!/usr/bin/env python3
"""Run split verification phases for the COREX Node Editor repo."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

try:
    import verification_manifest as manifest
except ModuleNotFoundError:
    import scripts.verification_manifest as manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_VENV_PYTHON = REPO_ROOT / "venv" / "Scripts" / "python.exe"
_MODULE_AVAILABLE_PROBE = (
    "import importlib, sys; "
    "importlib.import_module(sys.argv[1])"
)
_PYTEST_STARTUP_PROBE_ARGS = (
    "-m",
    "pytest",
    "--collect-only",
    "-q",
    "tests/test_run_verification.py",
    "--ignore=venv",
)
_MISSING_MODULE_PATTERN = re.compile(r"No module named ['\"]([^'\"]+)['\"]")
_PIP_CHECK_MISSING_REQUIREMENT_PATTERN = re.compile(
    r"^(?P<dist>[A-Za-z0-9_.-]+)\s+\S+\s+requires\s+(?P<requirement>.+), which is not installed\.$"
)
_PIP_CHECK_INCOMPATIBLE_REQUIREMENT_PATTERN = re.compile(
    r"^(?P<dist>[A-Za-z0-9_.-]+)\s+\S+\s+has requirement\s+"
    r"(?P<requirement>.+), but you have .+\.$"
)
_PYTEST_CORE_DISTS = frozenset({"pytest", "pytest-xdist"})
_PYTEST_STACK_REPAIR_PACKAGES = {
    "_pytest": "pytest",
    "pytest": "pytest",
    "colorama": "colorama",
    "coverage": "coverage[toml]",
    "execnet": "execnet>=2.1",
    "exceptiongroup": "exceptiongroup",
    "iniconfig": "iniconfig",
    "packaging": "packaging",
    "pluggy": "pluggy",
    "pygments": "pygments",
    "tomli": "tomli",
    "typing_extensions": "typing-extensions",
}


@dataclass(frozen=True)
class CommandSpec:
    """One concrete verification command."""

    phase: str
    argv: tuple[str, ...]
    display_argv: tuple[str, ...]
    env: dict[str, str]
    notice: str | None = None


def local_venv_python_exists() -> bool:
    try:
        return LOCAL_VENV_PYTHON.exists()
    except OSError:
        return False


def current_python_matches_project_venv() -> bool:
    return Path(sys.executable).as_posix().lower().endswith("/venv/scripts/python.exe")


def resolve_python() -> tuple[str, str]:
    if local_venv_python_exists():
        return str(LOCAL_VENV_PYTHON), manifest.LOCAL_VENV_PYTHON_DISPLAY
    if current_python_matches_project_venv():
        return sys.executable, manifest.LOCAL_VENV_PYTHON_DISPLAY
    return sys.executable, sys.executable


def python_module_available(python_exec: str, module_name: str) -> bool:
    completed = subprocess.run(
        [python_exec, "-c", _MODULE_AVAILABLE_PROBE, module_name],
        cwd=REPO_ROOT,
        check=False,
    )
    return completed.returncode == 0


def pytest_xdist_available(python_exec: str) -> bool:
    return python_module_available(python_exec, "xdist.newhooks")


def probe_pytest_startup(python_exec: str) -> tuple[bool, str]:
    completed = subprocess.run(
        [python_exec, *_PYTEST_STARTUP_PROBE_ARGS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return True, ""

    return (
        False,
        "\n".join(
            part.strip()
            for part in (completed.stderr, completed.stdout)
            if part and part.strip()
        ).strip(),
    )


def missing_module_from_output(failure_output: str) -> str | None:
    match = _MISSING_MODULE_PATTERN.search(failure_output)
    return None if match is None else match.group(1)


def pytest_related_unmet_requirements(
    python_exec: str, *, include_plugins: bool = True
) -> tuple[str, ...]:
    completed = subprocess.run(
        [python_exec, "-m", "pip", "--disable-pip-version-check", "check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return ()

    requirements: list[str] = []
    lines = [
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part and part.strip()
    ]
    for output in lines:
        for line in output.splitlines():
            stripped = line.strip()
            match = _PIP_CHECK_MISSING_REQUIREMENT_PATTERN.match(stripped)
            if match is None:
                match = _PIP_CHECK_INCOMPATIBLE_REQUIREMENT_PATTERN.match(stripped)
            if match is None:
                continue
            dist_name = match.group("dist").lower()
            is_relevant = (
                dist_name.startswith("pytest")
                if include_plugins
                else dist_name in _PYTEST_CORE_DISTS
            )
            if not is_relevant:
                continue
            requirement = match.group("requirement").strip()
            if requirement not in requirements:
                requirements.append(requirement)
    return tuple(requirements)


def install_python_packages(python_exec: str, *packages: str) -> int:
    completed = subprocess.run(
        [
            python_exec,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            *packages,
        ],
        cwd=REPO_ROOT,
        check=False,
    )
    return completed.returncode


def ensure_pytest_stack_ready(python_exec: str) -> bool:
    attempted_repairs: set[str] = set()
    repaired = False
    max_attempts = len(_PYTEST_STACK_REPAIR_PACKAGES) + 1

    for _ in range(max_attempts):
        core_unmet_requirements = tuple(
            requirement
            for requirement in pytest_related_unmet_requirements(
                python_exec, include_plugins=False
            )
            if requirement not in attempted_repairs
        )
        if core_unmet_requirements:
            print(
                "NOTE: pip check found broken core pytest requirements in the project "
                "venv. Installing "
                + ", ".join(f"'{requirement}'" for requirement in core_unmet_requirements)
                + " and retrying."
            )
            install_return_code = install_python_packages(python_exec, *core_unmet_requirements)
            if install_return_code != 0:
                raise RuntimeError(
                    "Automatic pytest-stack repair failed while installing core pip-check "
                    f"requirements (exit code {install_return_code})."
                )
            attempted_repairs.update(core_unmet_requirements)
            repaired = True
            continue

        startup_ok, failure_output = probe_pytest_startup(python_exec)
        if startup_ok:
            return repaired

        missing_module = missing_module_from_output(failure_output)
        package_name = None if missing_module is None else _PYTEST_STACK_REPAIR_PACKAGES.get(
            missing_module
        )
        if package_name is not None and package_name not in attempted_repairs:
            print(
                "NOTE: pytest startup failed because "
                f"'{missing_module}' is missing in the project venv. "
                f"Installing '{package_name}' and retrying."
            )
            install_return_code = install_python_packages(python_exec, package_name)
            if install_return_code != 0:
                raise RuntimeError(
                    f"Automatic pytest-stack repair failed while installing '{package_name}' "
                    f"(exit code {install_return_code})."
                )
            attempted_repairs.add(package_name)
            repaired = True
            continue

        unmet_requirements = tuple(
            requirement
            for requirement in pytest_related_unmet_requirements(
                python_exec, include_plugins=True
            )
            if requirement not in attempted_repairs
        )
        if unmet_requirements:
            print(
                "NOTE: pip check found broken pytest-related requirements in the project "
                "venv. Installing "
                + ", ".join(f"'{requirement}'" for requirement in unmet_requirements)
                + " and retrying."
            )
            install_return_code = install_python_packages(python_exec, *unmet_requirements)
            if install_return_code != 0:
                raise RuntimeError(
                    "Automatic pytest-stack repair failed while installing pip-check "
                    f"requirements (exit code {install_return_code})."
                )
            attempted_repairs.update(unmet_requirements)
            repaired = True
            continue

        raise RuntimeError(
            "pytest is not startup-ready in the project venv after the automatic repair "
            "attempt.\n"
            f"{failure_output}"
        )

    raise RuntimeError("pytest remains unavailable in the project venv after repair attempts.")


def resolve_max_parallel_workers() -> int:
    if importlib.util.find_spec("psutil") is not None:
        import psutil

        resolved = psutil.cpu_count(logical=True)
        if resolved is not None:
            return resolved
    return os.cpu_count() or 1


def resolve_gui_parallel_workers(max_parallel_workers: int) -> int:
    return max(1, min(max_parallel_workers, manifest.MAX_GUI_PARALLEL_WORKERS))


def build_pytest_command(
    *,
    phase: str,
    marker_expression: str,
    python_exec: str,
    python_display: str,
    use_xdist: bool,
    worker_count: int,
    notice: str | None = None,
) -> CommandSpec:
    argv = [python_exec, "-m", "pytest"]
    display_argv = [python_display, "-m", "pytest"]
    if use_xdist:
        argv.extend(["-n", str(worker_count), "--dist", "load"])
        display_argv.extend(["-n", str(worker_count), "--dist", "load"])
    argv.extend(["-m", marker_expression])
    display_argv.extend(["-m", marker_expression])
    for ignore_arg in manifest.worktree_pytest_ignore_args():
        argv.append(ignore_arg)
        display_argv.append(ignore_arg)
    for ignore_arg in manifest.non_shell_pytest_ignore_args():
        argv.append(ignore_arg)
        display_argv.append(ignore_arg)
    return CommandSpec(
        phase=phase,
        argv=tuple(argv),
        display_argv=tuple(display_argv),
        env=manifest.OFFSCREEN_ENV,
        notice=notice,
    )


def build_shell_isolation_phase_command(
    *,
    python_exec: str,
    python_display: str,
    use_xdist: bool,
    worker_count: int,
    notice: str | None = None,
) -> CommandSpec:
    phase_args = manifest.shell_isolation_phase_pytest_args(
        worker_count if use_xdist else None
    )
    argv = [python_exec, *phase_args]
    display_argv = [python_display, *phase_args]
    return CommandSpec(
        phase=manifest.SHELL_ISOLATION_SPEC.phase,
        argv=tuple(argv),
        display_argv=tuple(display_argv),
        env=manifest.OFFSCREEN_ENV,
        notice=notice,
    )


def build_context_budget_command(
    *,
    python_exec: str,
    python_display: str,
) -> CommandSpec:
    return CommandSpec(
        phase=manifest.CONTEXT_BUDGET_PHASE,
        argv=(python_exec, manifest.CHECK_CONTEXT_BUDGETS_SCRIPT),
        display_argv=(python_display, manifest.CHECK_CONTEXT_BUDGETS_SCRIPT),
        env={},
    )


def build_commands(mode: str) -> list[CommandSpec]:
    python_exec, python_display = resolve_python()
    xdist_available = pytest_xdist_available(python_exec)
    worker_count = resolve_max_parallel_workers()
    notices = {
        "fast": "pytest-xdist is unavailable; falling back to serial pytest for fast mode.",
        "gui": "pytest-xdist is unavailable; falling back to serial pytest for gui mode.",
        manifest.SHELL_ISOLATION_PHASE_KEY: (
            "pytest-xdist is unavailable; falling back to serial pytest for the shell-isolation phase."
        ),
    }

    commands_by_key: dict[str, CommandSpec] = {}
    for phase_key in manifest.RUN_VERIFICATION_MODE_SEQUENCE["full"]:
        if phase_key == manifest.CONTEXT_BUDGET_PHASE_KEY:
            commands_by_key[phase_key] = build_context_budget_command(
                python_exec=python_exec,
                python_display=python_display,
            )
            continue
        if phase_key == manifest.SHELL_ISOLATION_PHASE_KEY:
            commands_by_key[phase_key] = build_shell_isolation_phase_command(
                python_exec=python_exec,
                python_display=python_display,
                use_xdist=xdist_available,
                worker_count=worker_count,
                notice=None if xdist_available else notices[phase_key],
            )
            continue

        phase_spec = manifest.PYTEST_PHASE_SPECS_BY_MODE[phase_key]
        phase_worker_count = worker_count
        if phase_key == "gui":
            phase_worker_count = resolve_gui_parallel_workers(worker_count)
        commands_by_key[phase_key] = build_pytest_command(
            phase=phase_spec.phase,
            marker_expression=phase_spec.marker_expression,
            python_exec=python_exec,
            python_display=python_display,
            use_xdist=xdist_available and phase_spec.uses_xdist,
            worker_count=phase_worker_count,
            notice=None if xdist_available else notices.get(phase_key),
        )

    return [commands_by_key[phase_key] for phase_key in manifest.RUN_VERIFICATION_MODE_SEQUENCE[mode]]


def format_command(command: CommandSpec) -> str:
    if os.name == "nt":
        env_prefix = " ".join(
            f"$env:{name}={_powershell_quote(value)};" for name, value in sorted(command.env.items())
        )
        display_argv = tuple(_powershell_display_arg(part) for part in command.display_argv)
        argv = " ".join(_powershell_quote(part) for part in display_argv)
        if env_prefix:
            return f"{env_prefix} & {argv}"
        return f"& {argv}"

    env_prefix = " ".join(
        f"{name}={shlex.quote(value)}" for name, value in sorted(command.env.items())
    )
    argv = " ".join(shlex.quote(part) for part in command.display_argv)
    if env_prefix:
        return f"{env_prefix} {argv}"
    return argv


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _powershell_display_arg(value: str) -> str:
    if value.startswith("./"):
        return ".\\" + value[2:].replace("/", "\\")
    return value


def run_command(command: CommandSpec) -> int:
    env = os.environ.copy()
    env.update(command.env)
    completed = subprocess.run(command.argv, cwd=REPO_ROOT, env=env, check=False)
    return completed.returncode


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        required=True,
        choices=manifest.MODE_NAMES,
        help="verification phase selection",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the concrete commands without executing them",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    python_exec, _python_display = resolve_python()
    if not args.dry_run:
        try:
            ensure_pytest_stack_ready(python_exec)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    commands = build_commands(args.mode)
    for command in commands:
        print(f"[{command.phase}]")
        if command.notice:
            print(f"NOTE: {command.notice}")
        print(format_command(command))
        if args.dry_run:
            continue
        return_code = run_command(command)
        if return_code != 0:
            return return_code
    if args.dry_run:
        print("Dry run only; no commands executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
