# Purpose: Automation example: build a 10-node engineering flowchart with one graph.apply batch, style both branches, label edges, tidy (center-align + straighten wires), save, and screenshot.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_docgen.py
"""Engineering flowchart via the COREX automation API.

Run from the repository root::

    .\\venv\\Scripts\\python.exe examples\\automation\\flowchart.py
    .\\venv\\Scripts\\python.exe examples\\automation\\flowchart.py --mode private --no-headless
    .\\venv\\Scripts\\python.exe examples\\automation\\flowchart.py --mode attach --output-dir C:\\temp\\corex

The default ``--mode private`` spawns an isolated COREX, builds the chart in a
fresh project, saves ``flowchart.cxproj``, writes a PNG, and quits the
instance. With ``attach`` / ``auto`` the chart goes into a new workspace of the
running COREX and the project is not saved (it belongs to the user).
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

WORKSPACE_NAME = "Flowchart example"
COLUMN = 320  # horizontal grid pitch
ROW = 240  # vertical pitch for the loop row
YES_STYLE = {"fill_color": "#E8F5E9", "border_color": "#2E7D32", "text_color": "#1B5E20", "border_width": 2}
NO_STYLE = {"fill_color": "#FFF3E0", "border_color": "#EF6C00", "text_color": "#E65100", "border_width": 2}

# (batch id, type id, title, column, row)
NODES = (
    ("start", "passive.flowchart.start", "Start", 0, 0),
    ("import_cad", "passive.flowchart.input_output", "Import CAD", 1, 0),
    ("clean", "passive.flowchart.process", "Clean geometry", 2, 0),
    ("mesh", "passive.flowchart.process", "Mesh", 3, 0),
    ("solve", "passive.flowchart.predefined_process", "Solve", 4, 0),
    ("converged", "passive.flowchart.decision", "Converged?", 5, 0),
    ("export", "passive.flowchart.document", "Export results", 6, 0),
    ("archive", "passive.flowchart.database", "Archive to PDM", 7, 0),
    ("end", "passive.flowchart.end", "End", 8, 0),
    ("refine", "passive.flowchart.process", "Refine mesh", 5, 1),
)
# (batch id, source, source port, target, target port, label)
EDGES = (
    ("e_import", "start", "right", "import_cad", "left", ""),
    ("e_clean", "import_cad", "right", "clean", "left", ""),
    ("e_mesh", "clean", "right", "mesh", "left", ""),
    ("e_solve", "mesh", "right", "solve", "left", ""),
    ("e_check", "solve", "right", "converged", "left", ""),
    ("e_yes", "converged", "right", "export", "left", "yes"),
    ("e_archive", "export", "right", "archive", "left", ""),
    ("e_end", "archive", "right", "end", "left", ""),
    ("e_no", "converged", "bottom", "refine", "top", "no"),
    ("e_loop", "refine", "left", "mesh", "bottom", ""),
)
# The loop leaves refine's left side and enters mesh from below: an elbow that stays bent by design.
ELBOW_EDGES = frozenset({"e_loop"})


class ExampleFailure(RuntimeError):
    """A check in this example failed."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an engineering flowchart in COREX through the automation API.")
    parser.add_argument("--mode", choices=("auto", "attach", "private"), default="private", help="launch mode (default: private)")
    parser.add_argument("--headless", dest="headless", action="store_true", default=True, help="private mode renders offscreen (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="private mode opens a real window")
    parser.add_argument("--output-dir", type=Path, default=None, help="where the .cxproj and PNG go (default: a new temp folder)")
    parser.add_argument("--instance-id", default=None, help="attach to this discovery instance id")
    parser.add_argument("--startup-timeout", type=float, default=120.0, help="seconds to wait for a spawned instance")
    return parser.parse_args(argv)


def is_sandbox(corex: CorexClient) -> bool:
    """True for a private instance this script spawned (safe to replace its project and save)."""
    handle = corex.handle
    return handle is not None and handle.owned and handle.private


def prepare_workspace(corex: CorexClient, sandbox: bool) -> str:
    status = corex.app.status()
    busy = {key: value for key, value in (status.get("busy") or {}).items() if value}
    if busy:
        raise ExampleFailure(f"COREX is busy ({', '.join(sorted(busy))}); close dialogs or wait, then retry")
    if not sandbox:
        return str(corex.workspaces.create(WORKSPACE_NAME)["workspace_id"])
    project = corex.project.new(discard_unsaved=True)
    workspace_id = str(project["active_workspace_id"])
    try:
        corex.workspaces.rename(workspace_id, WORKSPACE_NAME)
    except AutomationOpError as exc:
        if exc.code != "NO_EFFECT":
            raise
    return workspace_id


def build_batch(corex: CorexClient):
    batch = corex.apply.batch()
    refs: dict[str, str] = {}
    for batch_id, type_id, title, column, row in NODES:
        refs[batch_id] = batch.add(
            "node.add",
            {
                "type_id": type_id,
                "x": column * COLUMN,
                "y": row * ROW,
                "title": title,
                "properties": {"body": title},  # flowchart shapes draw their body text
            },
            id=batch_id,
        )
    for batch_id, source, source_port, target, target_port, label in EDGES:
        params = {
            "source_node_id": refs[source],
            "source_port": source_port,
            "target_node_id": refs[target],
            "target_port": target_port,
        }
        if label:
            params["label"] = label
        batch.add("edge.connect", params, id=batch_id)
    return batch


def tidy(corex: CorexClient, ids: dict[str, str]) -> None:
    """Center the main row (shapes have different heights), then straighten every wire in the scope."""
    main_row = [ids[batch_id] for batch_id, _type_id, _title, _column, row in NODES if row == 0]
    corex.structure.align(main_row, "center_y")
    report = corex.structure.straighten()
    names = {edge_id: batch_id for batch_id, edge_id in ids.items()}
    skipped = {names.get(entry["edge_id"], entry["edge_id"]): entry["reason"] for entry in report["skipped_edges"]}
    print(f"layout.straighten: {len(report['straightened_edge_ids'])} straight wires, skipped {skipped}")
    if set(skipped) != ELBOW_EDGES:
        raise ExampleFailure(f"expected only {sorted(ELBOW_EDGES)} to stay bent, got {skipped}")
    if report["overlapping_node_pairs"]:
        raise ExampleFailure(f"tidying stacked nodes: {report['overlapping_node_pairs']}")


def run(corex: CorexClient, output_dir: Path) -> dict[str, str]:
    sandbox = is_sandbox(corex)
    prepare_workspace(corex, sandbox)

    outcome = build_batch(corex).run(label="Build engineering flowchart")
    ids: dict[str, str] = outcome["ids"]
    if outcome.get("failed_index", -1) != -1 or len(ids) != len(NODES) + len(EDGES):
        raise ExampleFailure(f"graph.apply did not apply every op: {json.dumps(outcome.get('results', []))[:400]}")
    print(f"graph.apply: {outcome['applied']} ops in one undo step")

    for batch_id in ("export", "archive", "end"):
        corex.nodes.set_style(ids[batch_id], YES_STYLE)
    corex.nodes.set_style(ids["refine"], NO_STYLE)
    corex.edges.update(ids["e_yes"], style={"color": "#2E7D32", "width": 2, "label_color": "#1B5E20"})
    corex.edges.update(ids["e_no"], style={"color": "#EF6C00", "width": 2, "label_color": "#E65100"})
    corex.edges.update(ids["e_loop"], label="re-mesh", style={"color": "#EF6C00", "pattern": "dashed"})

    tidy(corex, ids)

    graph = corex.graph.get()
    if len(graph["nodes"]) != len(NODES) or len(graph["edges"]) != len(EDGES):
        raise ExampleFailure(f"expected {len(NODES)} nodes / {len(EDGES)} edges, got {len(graph['nodes'])} / {len(graph['edges'])}")

    corex.workspaces.frame_all()
    artifacts: dict[str, str] = {}
    if sandbox:
        saved = corex.project.save_as(output_dir / "flowchart.cxproj")
        artifacts["project"] = str(saved.get("project_path") or output_dir / "flowchart.cxproj")
    else:
        print("skipped project save: the attached COREX belongs to the user (use --mode private to save)")
    shot = corex.capture.screenshot_to(output_dir)
    paths = [path for path in shot.get("saved_paths", []) if Path(path).is_file()]
    if not paths:
        raise ExampleFailure("capture.screenshot produced no PNG file")
    for index, path in enumerate(paths, start=1):
        artifacts[f"screenshot_{index}"] = path
    artifacts["fidelity"] = str(shot.get("fidelity", ""))
    return artifacts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = (args.output_dir or Path(tempfile.mkdtemp(prefix="corex-flowchart-"))).resolve()
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
