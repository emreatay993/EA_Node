# Purpose: Generate a portable synthetic multi-array composition and Signal Plot example.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_example.py
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from ea_node_editor.common.artifact_refs import format_managed_artifact_ref
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.graph.records import EdgeInstance, NodeInstance
from ea_node_editor.graph.record_payloads import edge_instance_to_mapping, node_instance_to_mapping


def _node(**values):
    return node_instance_to_mapping(NodeInstance(**values))


def _edge(*values):
    return edge_instance_to_mapping(EdgeInstance(*values))


def generate(directory: Path) -> Path:
    project_path = directory / "tabular_composer.cxproj"
    data_path = directory / "tabular_composer.data" / "nodes" / "composer" / "in" / "signals.npz"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    time = np.arange(301, dtype=np.float64)
    temperature = np.column_stack((25 + 0.08 * time, 30 + 0.05 * time, 28 + 0.06 * time))
    heat_flow = np.column_stack((10 + 0.1 * time, 8 + 0.07 * time))
    np.savez_compressed(data_path, time_s=time, temperature=temperature, heat_flow=heat_flow,
                        sensor_names=np.array(["Housing", "Shaft", "Gear"]), interface_names=np.array(["Interface A", "Interface B"]))
    source_ref = format_managed_artifact_ref("tabular_source.composer")
    definitions = [
        ("temperature", "Temperature history", [{"id": "temperature", "member": "temperature", "labels_member": "sensor_names", "unit": "C"}], {}),
        ("heatflow", "Heat-flow history", [{"id": "flow", "member": "heat_flow", "labels_member": "interface_names", "unit": "W"}], {}),
        ("combined", "Combined / warm housing", [{"id": "temperature", "member": "temperature", "labels_member": "sensor_names", "unit": "C"},
                                                  {"id": "flow", "member": "heat_flow", "labels_member": "interface_names", "unit": "W"}],
         {"filters": [{"column": "Housing", "op": "gt", "value": "40"}], "sort": [{"column": "time_s", "descending": False}]}),
    ]
    nodes, edges = [], []
    for index, (key, title, blocks, query) in enumerate(definitions):
        definition = {"version": 1, "mode": "table", "segments": [{"blocks": blocks, "coordinate": {"member": "time_s", "name": "time_s", "unit": "s"}}], "query": query}
        nodes.append(_node(node_id=f"input_{key}", type_id="tabular.input", title=title, x=0, y=index * 320,
                           properties={"path": source_ref, "data_view": definition, "data_view_name": title},
                           exposed_ports={"table_data": True}, custom_width=430, custom_height=255))
        nodes.append(_node(node_id=f"plot_{key}", type_id="plot.signal", title=title + " plot", x=560, y=index * 320,
                           properties={"x_mode": "column", "x_column": "time_s", "show_legend": True, "title": title,
                                       "y_columns": ["Interface A", "Interface B"] if key == "heatflow" else ["Housing", "Shaft", "Gear"]},
                           exposed_ports={"values": True}, custom_width=500, custom_height=280))
        edges.append(_edge(f"edge_{key}", f"input_{key}", "table_data", f"plot_{key}", "values"))
    document = {"schema_version": SCHEMA_VERSION, "project_id": "project_tabular_composer", "name": "Tabular Composer",
                "active_workspace_id": "workspace_composer", "workspace_order": ["workspace_composer"],
                "workspaces": [{"workspace_id": "workspace_composer", "name": "Composition examples", "dirty": False,
                                "active_view_id": "view_composer", "views": [{"view_id": "view_composer", "name": "Composer", "zoom": 0.8,
                                                                              "pan_x": 45, "pan_y": 45, "scope_path": [], "hide_optional_ports": True}],
                                "nodes": nodes, "edges": edges}],
                "metadata": {"artifact_store": {"artifacts": {"tabular_source.composer": {"artifact_kind": "tabular_source", "relative_path": "nodes/composer/in/signals.npz"}}, "staged": {}}}}
    serializer = JsonProjectSerializer(build_default_registry(include_public_plugins=False))
    project = serializer.from_document(document)
    serializer.save_document(str(project_path), serializer.to_persistent_document(project))
    return project_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1] / "examples")
    args = parser.parse_args()
    print(generate(args.directory))
