"""Generate a large flowchart project for edge-renderer performance runs.

A grid of flowchart shapes joined by flow edges: right-hand neighbours, every
other column downwards, and diagonal skips across both (``gap_break``
material). The edges mix default, dashed, and dotted strokes, start and open
arrowheads, custom colours and widths, bezier path overrides, labels (some
path-following or dragged along the path). Everything goes through the normal
scene mutation paths, so styles are normalized exactly as in the app, and the
project is saved with ``JsonProjectSerializer``.

Usage
-----
    venv\\Scripts\\python.exe scripts\\generate_flowchart_perf_fixture.py
    venv\\Scripts\\python.exe -m ea_node_editor.ui.perf.performance_harness --project-path artifacts\\perf_fixtures\\flowchart_edge_perf.cxproj --load-iterations 1 --interaction-samples 10 --interaction-warmup-samples 3 --interaction-zoom-min 0.3 --interaction-zoom-max 0.35 --baseline-runs 1 --qt-platform windows --qsg-rhi-backend d3d11 --baseline-mode interactive

The default 24 x 24 grid gives 576 nodes and 920 flow edges.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUTPUT = _REPO_ROOT / "artifacts" / "perf_fixtures" / "flowchart_edge_perf.cxproj"
_SHAPE_TYPES = (
    "passive.flowchart.process",
    "passive.flowchart.decision",
    "passive.flowchart.document",
    "passive.flowchart.input_output",
    "passive.flowchart.database",
    "passive.flowchart.predefined_process",
)
_LABELS = ("Yes", "No", "Approved", "Retry", "On failure", "Next step", "Validated\nby QA", "Timeout", "Escalate")


def build_project(columns: int, rows: int, seed: int):
    rng = random.Random(seed)
    registry = build_default_registry()
    model = GraphModel()
    model.project.name = "flowchart_edge_perf"
    scene = GraphSceneBridge()
    workspace_id = model.active_workspace.workspace_id
    scene.set_workspace(model, registry, workspace_id)

    grid: dict[tuple[int, int], str] = {}
    for row in range(rows):
        for column in range(columns):
            type_id = _SHAPE_TYPES[(row * 7 + column * 3) % len(_SHAPE_TYPES)]
            grid[(row, column)] = scene.add_node_from_type(type_id, column * 320.0, row * 220.0)

    edge_ids: list[str] = []

    def connect(source: tuple[int, int], source_port: str, target: tuple[int, int], target_port: str) -> None:
        if source in grid and target in grid:
            edge_id = scene.add_edge(grid[source], source_port, grid[target], target_port)
            if edge_id:
                edge_ids.append(edge_id)

    for row in range(rows):
        for column in range(columns):
            connect((row, column), "right", (row, column + 1), "left")
            if column % 2 == 0:
                connect((row, column), "bottom", (row + 1, column), "top")
            if column % 3 == 0:
                connect((row, column), "bottom", (row + 1, column + 2), "top")

    for index, edge_id in enumerate(edge_ids):
        style: dict[str, object] = {}
        roll = rng.random()
        if roll < 0.15:
            style["stroke_pattern"] = "dashed"
        elif roll < 0.25:
            style["stroke_pattern"] = "dotted"
        if rng.random() < 0.12:
            style["arrow_tail"] = "filled"
        if rng.random() < 0.10:
            style["arrow_head"] = "open"
        if rng.random() < 0.10:
            style["stroke_color"] = rng.choice(("#4f8fd6", "#d9822b", "#3aa876", "#c0504d"))
            style["stroke_width"] = rng.choice((3, 4))
        if rng.random() < 0.10:
            style["path_mode"] = "bezier"
        if style:
            scene.set_edge_visual_style(edge_id, style)
        if index % 9 in (0, 2, 5, 7):
            scene.set_edge_label(edge_id, _LABELS[index % len(_LABELS)])
            if rng.random() < 0.2:
                label_style = dict(style)
                label_style["label_orientation"] = "follow_path"
                if rng.random() < 0.5:
                    label_style["label_position"] = round(rng.uniform(0.25, 0.75), 3)
                scene.set_edge_visual_style(edge_id, label_style)
    return registry, model, workspace_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT, help="Project path to write.")
    parser.add_argument("--columns", type=int, default=24)
    parser.add_argument("--rows", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260926)
    args = parser.parse_args(argv)
    registry, model, workspace_id = build_project(args.columns, args.rows, args.seed)
    workspace = model.project.workspaces[workspace_id]
    JsonProjectSerializer(registry).save(str(args.output), model.project)
    print(f"Wrote {args.output} ({len(workspace.nodes)} nodes, {len(workspace.edges)} flow edges).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
