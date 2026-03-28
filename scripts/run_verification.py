#!/usr/bin/env python3
"""Run split verification phases for the COREX Node Editor repo."""

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
    import verification_manifest as manifest
except ModuleNotFoundError:
    import scripts.verification_manifest as manifest

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


def build_commands(mode: str) -> list[CommandSpec]:
    python_exec, python_display = resolve_python()
    xdist_available = pytest_xdist_available()
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
