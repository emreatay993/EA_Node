#!/usr/bin/env python3
"""Run split verification phases for the EA Node Editor repo."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

try:
    from verification_manifest import LOCAL_VENV_PYTHON_DISPLAY
    from verification_manifest import MAX_GUI_PARALLEL_WORKERS
    from verification_manifest import MODE_NAMES
    from verification_manifest import NON_SHELL_PYTEST_IGNORES
    from verification_manifest import OFFSCREEN_ENV
    from verification_manifest import PYTEST_PHASE_SPECS_BY_MODE
    from verification_manifest import SHELL_ISOLATION_SPEC
except ModuleNotFoundError:
    from scripts.verification_manifest import LOCAL_VENV_PYTHON_DISPLAY
    from scripts.verification_manifest import MAX_GUI_PARALLEL_WORKERS
    from scripts.verification_manifest import MODE_NAMES
    from scripts.verification_manifest import NON_SHELL_PYTEST_IGNORES
    from scripts.verification_manifest import OFFSCREEN_ENV
    from scripts.verification_manifest import PYTEST_PHASE_SPECS_BY_MODE
    from scripts.verification_manifest import SHELL_ISOLATION_SPEC

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_VENV_PYTHON = REPO_ROOT / "venv" / "Scripts" / "python.exe"


@dataclass(frozen=True)
class CommandSpec:
    """One concrete verification command."""

    phase: str
    argv: tuple[str, ...]
    display_argv: tuple[str, ...]
    env: dict[str, str]
    notice: str | None = None


def resolve_python() -> tuple[str, str]:
    if LOCAL_VENV_PYTHON.exists():
        return str(LOCAL_VENV_PYTHON), LOCAL_VENV_PYTHON_DISPLAY
    return sys.executable, sys.executable


def pytest_xdist_available() -> bool:
    return importlib.util.find_spec("xdist") is not None


def resolve_max_parallel_workers() -> int:
    if importlib.util.find_spec("psutil") is not None:
        import psutil

        resolved = psutil.cpu_count(logical=True)
        if resolved is not None:
            return resolved
    return os.cpu_count() or 1


def resolve_gui_parallel_workers(max_parallel_workers: int) -> int:
    return max(1, min(max_parallel_workers, MAX_GUI_PARALLEL_WORKERS))


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
    for test_file in NON_SHELL_PYTEST_IGNORES:
        ignore_arg = f"--ignore={test_file}"
        argv.append(ignore_arg)
        display_argv.append(ignore_arg)
    return CommandSpec(
        phase=phase,
        argv=tuple(argv),
        display_argv=tuple(display_argv),
        env=OFFSCREEN_ENV,
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
    argv = [python_exec, "-m", "pytest", SHELL_ISOLATION_SPEC.test_path, "-q"]
    display_argv = [python_display, "-m", "pytest", SHELL_ISOLATION_SPEC.test_path, "-q"]
    if use_xdist:
        argv.extend(["-n", str(worker_count), "--dist", "load"])
        display_argv.extend(["-n", str(worker_count), "--dist", "load"])
    return CommandSpec(
        phase=SHELL_ISOLATION_SPEC.phase,
        argv=tuple(argv),
        display_argv=tuple(display_argv),
        env=OFFSCREEN_ENV,
        notice=notice,
    )


def build_commands(mode: str) -> list[CommandSpec]:
    python_exec, python_display = resolve_python()
    xdist_available = pytest_xdist_available()
    worker_count = resolve_max_parallel_workers()
    gui_worker_count = resolve_gui_parallel_workers(worker_count)
    fast_notice = None
    if not xdist_available:
        fast_notice = "pytest-xdist is unavailable; falling back to serial pytest for fast mode."
    gui_notice = None
    if not xdist_available:
        gui_notice = "pytest-xdist is unavailable; falling back to serial pytest for gui mode."

    fast_spec = PYTEST_PHASE_SPECS_BY_MODE["fast"]
    fast_command = build_pytest_command(
        phase=fast_spec.phase,
        marker_expression=fast_spec.marker_expression,
        python_exec=python_exec,
        python_display=python_display,
        use_xdist=xdist_available and fast_spec.uses_xdist,
        worker_count=worker_count,
        notice=fast_notice,
    )
    gui_spec = PYTEST_PHASE_SPECS_BY_MODE["gui"]
    gui_command = build_pytest_command(
        phase=gui_spec.phase,
        marker_expression=gui_spec.marker_expression,
        python_exec=python_exec,
        python_display=python_display,
        use_xdist=xdist_available and gui_spec.uses_xdist,
        worker_count=gui_worker_count,
        notice=gui_notice,
    )
    slow_spec = PYTEST_PHASE_SPECS_BY_MODE["slow"]
    slow_command = build_pytest_command(
        phase=slow_spec.phase,
        marker_expression=slow_spec.marker_expression,
        python_exec=python_exec,
        python_display=python_display,
        use_xdist=xdist_available and slow_spec.uses_xdist,
        worker_count=worker_count,
    )
    shell_notice = None
    if not xdist_available:
        shell_notice = (
            "pytest-xdist is unavailable; falling back to serial pytest for the shell-isolation phase."
        )
    shell_command = build_shell_isolation_phase_command(
        python_exec=python_exec,
        python_display=python_display,
        use_xdist=xdist_available,
        worker_count=worker_count,
        notice=shell_notice,
    )

    if mode == "fast":
        return [fast_command]
    if mode == "gui":
        return [gui_command]
    if mode == "slow":
        return [slow_command]

    return [fast_command, gui_command, slow_command, shell_command]


def format_command(command: CommandSpec) -> str:
    env_prefix = " ".join(
        f"{name}={shlex.quote(value)}" for name, value in sorted(command.env.items())
    )
    argv = " ".join(shlex.quote(part) for part in command.display_argv)
    if env_prefix:
        return f"{env_prefix} {argv}"
    return argv


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
        choices=MODE_NAMES,
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
