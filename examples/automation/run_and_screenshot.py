# Purpose: Automation example: fresh project, two cheap active nodes (core.constant -> core.logger) checked against the catalog, run and wait, print status, screenshot.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_docgen.py
"""Run a tiny workflow via the COREX automation API.

Run from the repository root::

    .\\venv\\Scripts\\python.exe examples\\automation\\run_and_screenshot.py
    .\\venv\\Scripts\\python.exe examples\\automation\\run_and_screenshot.py --run-timeout 180 --output-dir C:\\temp\\corex

``core.constant`` publishes a JSON value and its text form (``as_text``);
``core.logger`` writes its ``message`` input to the run log. The script checks
both port keys with ``catalog.describe_node_type`` before wiring them, runs the
workspace with ``run.start(wait=true)``, prints the final status and log tail,
and exits 1 unless the run completed. In ``private`` mode it starts from a new
blank project; with ``attach`` / ``auto`` it works in a new workspace instead
so the user's project is never replaced.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

try:
    from ea_node_editor.automation.client import CorexClient
except ImportError:  # running from a checkout without an editable install
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ea_node_editor.automation.client import CorexClient

from ea_node_editor.automation.errors import AutomationOpError

WORKSPACE_NAME = "Run example"
SOURCE_TYPE = "core.constant"
SOURCE_PORT = "as_text"
SOURCE_PROPERTY = "value"
SINK_TYPE = "core.logger"
SINK_PORT = "message"
MESSAGE = "hello from COREX automation"


class ExampleFailure(RuntimeError):
    """A check in this example failed."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wire two active COREX nodes, run them, and screenshot the result.")
    parser.add_argument("--mode", choices=("auto", "attach", "private"), default="private", help="launch mode (default: private)")
    parser.add_argument("--headless", dest="headless", action="store_true", default=True, help="private mode renders offscreen (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="private mode opens a real window")
    parser.add_argument("--output-dir", type=Path, default=None, help="where the PNG goes (default: a new temp folder)")
    parser.add_argument("--instance-id", default=None, help="attach to this discovery instance id")
    parser.add_argument("--startup-timeout", type=float, default=120.0, help="seconds to wait for a spawned instance")
    parser.add_argument("--run-timeout", type=float, default=90.0, help="seconds to wait for the run to finish")
    return parser.parse_args(argv)


def is_sandbox(corex: CorexClient) -> bool:
    handle = corex.handle
    return handle is not None and handle.owned and handle.private


def prepare_workspace(corex: CorexClient, sandbox: bool) -> None:
    status = corex.app.status()
    busy = {key: value for key, value in (status.get("busy") or {}).items() if value}
    if busy:
        raise ExampleFailure(f"COREX is busy ({', '.join(sorted(busy))}); close dialogs or wait, then retry")
    if not (status.get("run") or {}).get("idle", True):
        raise ExampleFailure("a run is already active; stop it (run.control stop) or wait, then retry")
    if sandbox:
        corex.project.new(discard_unsaved=True)
    else:
        corex.workspaces.create(WORKSPACE_NAME)


def require_port(description: dict, key: str, direction: str) -> dict:
    for port in description.get("ports", []):
        if port.get("key") == key and port.get("direction") == direction:
            return port
    available = [(port.get("key"), port.get("direction")) for port in description.get("ports", [])]
    raise ExampleFailure(f"{description.get('type_id')} has no {direction} port '{key}' (ports: {available})")


def run(corex: CorexClient, output_dir: Path, run_timeout_s: float) -> dict[str, str]:
    prepare_workspace(corex, is_sandbox(corex))

    source_spec = corex.catalog.describe_node_type(SOURCE_TYPE)
    sink_spec = corex.catalog.describe_node_type(SINK_TYPE)
    require_port(source_spec, SOURCE_PORT, "out")
    require_port(sink_spec, SINK_PORT, "in")
    if SOURCE_PROPERTY not in {prop.get("key") for prop in source_spec.get("properties", [])}:
        raise ExampleFailure(f"{SOURCE_TYPE} has no '{SOURCE_PROPERTY}' property")
    print(f"{SOURCE_TYPE} ({source_spec.get('runtime_behavior')}) -> {SINK_TYPE} ({sink_spec.get('runtime_behavior')})")

    source = corex.nodes.add(SOURCE_TYPE, 0, 0, title="Greeting", properties={SOURCE_PROPERTY: MESSAGE})
    sink = corex.nodes.add(SINK_TYPE, 420, 0, title="Log greeting")
    sink_ports = {port.get("key"): port for port in corex.graph.get_node(sink["node_id"]).get("ports", [])}
    if not sink_ports.get(SINK_PORT, {}).get("exposed", True):
        corex.nodes.update(sink["node_id"], exposed_ports={SINK_PORT: True})
    edge = corex.edges.connect(source["node_id"], SOURCE_PORT, sink["node_id"], SINK_PORT)
    print(f"edge {edge['edge_id']}: {SOURCE_PORT} -> {SINK_PORT}")

    # In the default auto solution mode, adding active nodes queues an auto-run, and
    # run.start refuses with RUN_ACTIVE while that submission is in flight. Let it settle first.
    settled = corex.run.wait(timeout_s=run_timeout_s)
    if not settled.get("idle"):
        raise ExampleFailure(f"the queued auto-run did not settle within {run_timeout_s:.0f} s")
    status = corex.run.run_and_wait(timeout_s=run_timeout_s, log_tail=20)
    print(f"run outcome: {status.get('outcome')} (engine {status.get('engine_state')}, "
          f"waited {float(status.get('waited_s') or 0):.1f} s, timed_out={bool(status.get('timed_out'))})")
    print(f"completed: {status.get('completed_node_ids', [])}  failed: {status.get('failed_node_ids', [])}")
    for error in status.get("root_errors", []):
        print(f"  error: {json.dumps(error, default=str)[:300]}")
    for line in status.get("log_tail", []):
        print(f"  log | {line}")

    corex.workspaces.frame_all()
    shot = corex.capture.screenshot_to(output_dir)
    paths = [path for path in shot.get("saved_paths", []) if Path(path).is_file()]
    if not paths:
        raise ExampleFailure("capture.screenshot produced no PNG file")
    if status.get("timed_out") or status.get("outcome") != "completed":
        raise ExampleFailure(f"the run did not complete (outcome={status.get('outcome')!r}); screenshot: {paths[0]}")
    artifacts = {f"screenshot_{index}": path for index, path in enumerate(paths, start=1)}
    artifacts["fidelity"] = str(shot.get("fidelity", ""))
    artifacts["outcome"] = str(status.get("outcome"))
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = (args.output_dir or Path(tempfile.mkdtemp(prefix="corex-run-"))).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with CorexClient.launch(
            args.mode,
            headless=args.headless,
            instance_id=args.instance_id,
            startup_timeout_s=args.startup_timeout,
        ) as corex:
            artifacts = run(corex, output_dir, args.run_timeout)
    except AutomationOpError as exc:
        print(f"FAILED {exc.code}: {exc.message}", file=sys.stderr)
        print(f"  hint: {exc.hint}", file=sys.stderr)
        if exc.details:
            print(f"  details: {json.dumps(exc.details, default=str)[:1200]}", file=sys.stderr)
        return 1
    except ExampleFailure as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    for label, value in artifacts.items():
        print(f"{label}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
