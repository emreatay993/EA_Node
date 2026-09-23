# Purpose: Automation example: build a chain, collapse part of it into a subnode, add a pin, edit inside the subnode scope, undo/redo once, and screenshot.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_docgen.py
"""Subnode workflow via the COREX automation API.

Run from the repository root::

    .\\venv\\Scripts\\python.exe examples\\automation\\subnode_workflow.py
    .\\venv\\Scripts\\python.exe examples\\automation\\subnode_workflow.py --no-headless --output-dir C:\\temp\\corex

Shows scope rules: graph ops act on the open scope, so the script enters the
subnode with ``scope.navigate`` before adding a node inside it, then returns to
the root. One ``app.history`` undo removes that node and one redo restores it.
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

WORKSPACE_NAME = "Subnode example"
INNER_TITLE = "Quality gate"
CHAIN = (
    ("start", "passive.flowchart.start", "Start"),
    ("prepare", "passive.flowchart.process", "Prepare geometry"),
    ("mesh", "passive.flowchart.process", "Mesh"),
    ("solve", "passive.flowchart.predefined_process", "Solve"),
    ("end", "passive.flowchart.end", "End"),
)


class ExampleFailure(RuntimeError):
    """A check in this example failed."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collapse part of a COREX chain into a subnode through the automation API.")
    parser.add_argument("--mode", choices=("auto", "attach", "private"), default="private", help="launch mode (default: private)")
    parser.add_argument("--headless", dest="headless", action="store_true", default=True, help="private mode renders offscreen (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="private mode opens a real window")
    parser.add_argument("--output-dir", type=Path, default=None, help="where the PNGs go (default: a new temp folder)")
    parser.add_argument("--instance-id", default=None, help="attach to this discovery instance id")
    parser.add_argument("--startup-timeout", type=float, default=120.0, help="seconds to wait for a spawned instance")
    return parser.parse_args(argv)


def is_sandbox(corex: CorexClient) -> bool:
    handle = corex.handle
    return handle is not None and handle.owned and handle.private


def prepare_workspace(corex: CorexClient, sandbox: bool) -> None:
    status = corex.app.status()
    busy = {key: value for key, value in (status.get("busy") or {}).items() if value}
    if busy:
        raise ExampleFailure(f"COREX is busy ({', '.join(sorted(busy))}); close dialogs or wait, then retry")
    if not sandbox:
        corex.workspaces.create(WORKSPACE_NAME)
        return
    project = corex.project.new(discard_unsaved=True)
    try:
        corex.workspaces.rename(str(project["active_workspace_id"]), WORKSPACE_NAME)
    except AutomationOpError as exc:
        if exc.code != "NO_EFFECT":
            raise


def inner_nodes(corex: CorexClient) -> list[dict]:
    return list(corex.graph.find_nodes(title=INNER_TITLE, scope="all").get("nodes", []))


def screenshot(corex: CorexClient, target: Path, artifacts: dict[str, str], label: str) -> None:
    corex.workspaces.frame_all()
    shot = corex.capture.screenshot_to(target)
    paths = [path for path in shot.get("saved_paths", []) if Path(path).is_file()]
    if not paths:
        raise ExampleFailure(f"capture.screenshot produced no PNG file for the {label} scope")
    artifacts[f"screenshot_{label}"] = paths[0]
    artifacts["fidelity"] = str(shot.get("fidelity", ""))


def run(corex: CorexClient, output_dir: Path) -> dict[str, str]:
    prepare_workspace(corex, is_sandbox(corex))

    batch = corex.apply.batch()
    refs = {
        batch_id: batch.add(
            "node.add",
            {"type_id": type_id, "x": index * 320, "y": 0, "title": title, "properties": {"body": title}},
            id=batch_id,
        )
        for index, (batch_id, type_id, title) in enumerate(CHAIN)
    }
    for (source, *_), (target, *_) in zip(CHAIN, CHAIN[1:]):
        batch.add(
            "edge.connect",
            {"source_node_id": refs[source], "source_port": "right", "target_node_id": refs[target], "target_port": "left"},
        )
    ids = batch.run(label="Build pipeline")["ids"]

    created = corex.structure.create_subnode([ids["prepare"], ids["mesh"]], title="Preprocess")
    shell_id = str(created["shell_node_id"])
    print(f"subnode {shell_id}: members {created['member_node_ids']}, "
          f"input pins {created['input_pin_ids']}, output pins {created['output_pin_ids']}")
    spare = corex.structure.add_output_pin(shell_id)
    print(f"spare output pin: {spare['pin_node_id']}")

    corex.structure.open_subnode(shell_id)
    inside = corex.graph.get(scope="active")
    lowest = max((float(node["y"]) + float(node.get("height") or 0) for node in inside["nodes"]), default=0.0)
    leftmost = min((float(node["x"]) for node in inside["nodes"]), default=0.0)
    inner = corex.nodes.add(
        "passive.flowchart.decision",
        leftmost,
        lowest + 120,
        title=INNER_TITLE,
        properties={"body": INNER_TITLE},
    )
    if inner["node"].get("parent_node_id") != shell_id:
        raise ExampleFailure(f"the inner node was not created inside {shell_id}: {inner['node']}")

    artifacts: dict[str, str] = {}
    screenshot(corex, output_dir / "inside_subnode", artifacts, "inside")
    corex.structure.navigate_root()

    undone = corex.app.undo()
    if not undone.get("applied") or inner_nodes(corex):
        raise ExampleFailure(f"undo did not remove the inner node: {undone}")
    redone = corex.app.redo()
    restored = inner_nodes(corex)
    if not redone.get("applied") or len(restored) != 1 or restored[0].get("parent_node_id") != shell_id:
        raise ExampleFailure(f"redo did not restore the inner node inside the subnode: {redone} / {restored}")
    print(f"undo/redo ok ({undone.get('action_type', '')!r}); history depth {redone.get('undo_depth')}")

    if corex.graph.get(scope="active").get("scope_path"):
        corex.structure.navigate_root()  # undo/redo may reopen the edited scope
    screenshot(corex, output_dir / "root", artifacts, "root")
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = (args.output_dir or Path(tempfile.mkdtemp(prefix="corex-subnode-"))).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with CorexClient.launch(
            args.mode,
            headless=args.headless,
            instance_id=args.instance_id,
            startup_timeout_s=args.startup_timeout,
        ) as corex:
            artifacts = run(corex, output_dir)
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
