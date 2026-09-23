from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


_BOOTSTRAP_SENTINEL = "EA_NODE_EDITOR_BOOTSTRAPPED"
_QT_QUICK_CONTROLS_STYLE = "Basic"

# Automation API launch flags (docs/AUTOMATION_API_GUIDE.md). They are promoted to
# the COREX_AUTOMATION_* environment read once by ea_node_editor.automation.gate,
# then stripped from argv so nothing downstream sees them. The re-exec in
# _bootstrap_python passes the environment through, so flags survive it.
AUTOMATION_FLAG = "--automation"
AUTOMATION_PORT_FLAG = "--automation-port"
AUTOMATION_INSTANCE_ID_FLAG = "--automation-instance-id"
_AUTOMATION_ENV_ENABLED = "COREX_AUTOMATION_ENABLED"
_AUTOMATION_ENV_PORT = "COREX_AUTOMATION_PORT"
_AUTOMATION_ENV_INSTANCE_ID = "COREX_AUTOMATION_INSTANCE_ID"


class AutomationFlagError(ValueError):
    """Raised for malformed --automation* command-line flags."""


def extract_automation_flags(argv: list[str]) -> tuple[list[str], dict[str, str]]:
    """Split ``--automation`` flags out of ``argv`` (program name included).

    Returns the remaining argv and the environment updates to apply. ``--automation``
    enables the server; ``--automation-port N`` and ``--automation-instance-id ID``
    (also ``--flag=value``) are only meaningful with it and imply it.
    """
    remaining: list[str] = []
    env: dict[str, str] = {}
    enabled = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if index == 0:
            remaining.append(arg)
            index += 1
            continue
        if arg == AUTOMATION_FLAG:
            enabled = True
            index += 1
            continue
        key, has_inline, inline_value = arg.partition("=")
        if key in (AUTOMATION_PORT_FLAG, AUTOMATION_INSTANCE_ID_FLAG):
            if has_inline:
                value = inline_value
            elif index + 1 < len(argv):
                value = argv[index + 1]
                index += 1
            else:
                raise AutomationFlagError(f"{key} requires a value")
            value = value.strip()
            if key == AUTOMATION_PORT_FLAG:
                try:
                    port = int(value)
                except ValueError:
                    raise AutomationFlagError(f"{key} expects an integer port, got {value!r}") from None
                if port < 0 or port > 65535:
                    raise AutomationFlagError(f"{key} must be between 0 and 65535, got {port}")
                env[_AUTOMATION_ENV_PORT] = str(port)
            else:
                if not value:
                    raise AutomationFlagError(f"{key} requires a non-empty id")
                env[_AUTOMATION_ENV_INSTANCE_ID] = value
            enabled = True
            index += 1
            continue
        remaining.append(arg)
        index += 1
    if enabled:
        env[_AUTOMATION_ENV_ENABLED] = "1"
    return remaining, env


def _apply_automation_flags() -> None:
    remaining, env = extract_automation_flags(list(sys.argv))
    if env:
        os.environ.update(env)
    if remaining != list(sys.argv):
        sys.argv[:] = remaining


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_worktree_python(repo_root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return None

    repo_root_key = _path_key(repo_root)
    for line in result.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        worktree_path = Path(line[len("worktree ") :].strip())
        if _path_key(worktree_path) == repo_root_key:
            continue
        candidate = worktree_path / "venv" / "Scripts" / "python.exe"
        if candidate.is_file():
            return candidate
    return None


def _preferred_python(repo_root: Path) -> Path | None:
    local_python = repo_root / "venv" / "Scripts" / "python.exe"
    if local_python.is_file():
        return local_python
    return _find_worktree_python(repo_root)


def _bootstrap_python(module_name: str = "ea_node_editor.bootstrap") -> None:
    if getattr(sys, "frozen", False):
        return

    if os.environ.get(_BOOTSTRAP_SENTINEL) == "1":
        return

    repo_root = _repo_root()
    preferred_python = _preferred_python(repo_root)
    if preferred_python is None:
        return

    if _path_key(Path(sys.executable)) == _path_key(preferred_python):
        return

    env = os.environ.copy()
    env[_BOOTSTRAP_SENTINEL] = "1"
    os.chdir(repo_root)
    os.execvpe(
        str(preferred_python),
        [str(preferred_python), "-m", module_name, *sys.argv[1:]],
        env,
    )


def configure_qquick_controls_runtime() -> None:
    if sys.platform != "win32":
        return
    if os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        return
    os.environ["QT_QUICK_CONTROLS_STYLE"] = _QT_QUICK_CONTROLS_STYLE


def main() -> int:
    if len(sys.argv) == 6 and sys.argv[1] == "--private-mechanical-owner" and sys.argv[2] == "--owner-child":
        from ea_node_editor.addons.mechanical.owner_process import _child
        return _child(int(sys.argv[3]), sys.argv[4], sys.argv[5])
    try:
        _apply_automation_flags()
    except AutomationFlagError as exc:
        print(f"corex-node-editor: {exc}", file=sys.stderr)
        return 2
    _bootstrap_python()
    # Read the automation gate now (after the re-exec, before any worker/Jupyter/script
    # subprocess is spawned) so COREX_AUTOMATION_TOKEN is popped from the environment
    # that children inherit. The module is Qt-free and cheap.
    import ea_node_editor.automation.gate  # noqa: F401

    configure_qquick_controls_runtime()
    from ea_node_editor.telemetry.startup_profile import phase

    with phase("bootstrap.import app"):
        from ea_node_editor.app import run

    return run()


def headless_main() -> int:
    _bootstrap_python("ea_node_editor.execution.runtime_cli")
    from ea_node_editor.execution.runtime_cli import main as run_headless_runtime

    return run_headless_runtime(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
