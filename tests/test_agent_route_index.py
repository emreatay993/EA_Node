from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import generate_agent_route_index as indexer


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class AgentRouteIndexTests(unittest.TestCase):
    def test_build_index_links_coverage_maps_sources_tests_and_qml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            maps_root = repo_root / "docs" / "agent_maps"
            route_path = maps_root / "feature_routes" / "graph_actions_and_context_menus.md"
            _write(
                maps_root / "COVERAGE.md",
                "\n".join(
                    [
                        "# Agent Map Coverage Matrix",
                        "",
                        "| Area | Primary map | Route coverage |",
                        "| --- | --- | --- |",
                        "| `ea_node_editor/ui_qml`, `components/graph` | [Graph Canvas](subsystems/graph_canvas.md) | [Graph Actions](feature_routes/graph_actions_and_context_menus.md) |",
                        "| `tests/test_graph_action_contracts.py` | [Docs Tests](testing/docs_traceability_hygiene.md) | [Graph Actions](feature_routes/graph_actions_and_context_menus.md) |",
                    ]
                ),
            )
            _write(
                maps_root / "subsystems" / "graph_canvas.md",
                "# Graph Canvas\n\n## Focused Verification\n```powershell\npytest tests/test_graph_action_contracts.py\n```\n",
            )
            _write(
                route_path,
                "\n".join(
                    [
                        "# Graph Actions And Context Menus",
                        "",
                        "Lookup aliases: `graph action ownership`.",
                        "",
                        "## Start Here",
                        "- `ea_node_editor/ui/shell/graph_action_contracts.py`",
                        "- `tests/test_graph_action_contracts.py`",
                        "",
                        "## Do Not Start Here",
                        "- `ea_node_editor/persistence/` for UI action routing.",
                        "",
                    ]
                ),
            )
            _write(maps_root / "testing" / "docs_traceability_hygiene.md", "# Docs Tests\n")
            _write(
                repo_root / "docs" / "source_test_file_index.md",
                "\n".join(
                    [
                        "# Source And Test File Index",
                        "",
                        "## Source Code",
                        "",
                        "| Path |",
                        "| --- |",
                        "| `ea_node_editor/ui/shell/graph_action_contracts.py` |",
                        "| `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml` |",
                        "",
                        "## Test Modules",
                        "",
                        "| Path |",
                        "| --- |",
                        "| `tests/test_graph_action_contracts.py` |",
                    ]
                ),
            )
            _write(
                repo_root / "docs" / "qml_navigation_index.json",
                json.dumps(
                    {
                        "version": 3,
                        "entries": [
                            {
                                "path": "ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml",
                                "component_name": "GraphNodeHost",
                                "aliases": [
                                    "GraphNodeHost",
                                    "GraphNodeHost.qml",
                                    "ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml",
                                ],
                                "root_component": "Item",
                                "properties": [{"kind": "bool", "name": "selected"}],
                            }
                        ],
                    }
                ),
            )

            index_data = indexer.build_index_data(repo_root)

        entries_by_key = {entry.route_key: entry for entry in index_data.entries}
        route_entry = entries_by_key["feature_route:feature-routes-graph-actions-and-context-menus"]
        self.assertIn(
            "ea_node_editor/ui/shell/graph_action_contracts.py",
            route_entry.source_candidates,
        )
        self.assertIn("tests/test_graph_action_contracts.py", route_entry.test_candidates)
        self.assertIn(
            "ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml",
            route_entry.qml_candidates,
        )
        self.assertIn("graph", route_entry.keywords)
        self.assertEqual(route_entry.aliases, ("graph action ownership",))
        self.assertEqual(
            route_entry.start_here,
            (
                "ea_node_editor/ui/shell/graph_action_contracts.py",
                "tests/test_graph_action_contracts.py",
            ),
        )
        self.assertEqual(
            route_entry.do_not_start_here, ("ea_node_editor/persistence/",)
        )
        serialized = indexer.route_entry_to_dict(route_entry)
        self.assertEqual(serialized["aliases"], ["graph action ownership"])
        self.assertEqual(
            serialized["start_here"],
            [
                "ea_node_editor/ui/shell/graph_action_contracts.py",
                "tests/test_graph_action_contracts.py",
            ],
        )

        qml_entry = entries_by_key["qml:graphnodehost"]
        self.assertEqual(qml_entry.kind, "qml_component")
        self.assertEqual(qml_entry.map_path, "docs/agent_maps/subsystems/graph_canvas.md")
        self.assertIn("selected", qml_entry.keywords)

    def test_multiline_backtick_span_splits_into_separate_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            maps_root = repo_root / "docs" / "agent_maps"
            _write(maps_root / "COVERAGE.md", "# Agent Map Coverage Matrix\n")
            # A single backtick span wrapping two paths across a newline used to be
            # captured as one glued blob with an embedded newline. It must now split.
            _write(
                maps_root / "feature_routes" / "multi_path.md",
                "# Multi Path\n\n`ea_node_editor/alpha.py\nea_node_editor/beta.py`\n",
            )
            _write(repo_root / "docs" / "source_test_file_index.md", "# Source And Test File Index\n")
            _write(repo_root / "docs" / "qml_navigation_index.json", json.dumps({"entries": []}))

            index_data = indexer.build_index_data(repo_root)

        entries_by_key = {entry.route_key: entry for entry in index_data.entries}
        entry = entries_by_key["feature_route:feature-routes-multi-path"]
        self.assertIn("ea_node_editor/alpha.py", entry.source_candidates)
        self.assertIn("ea_node_editor/beta.py", entry.source_candidates)
        for candidate in (*entry.source_candidates, *entry.test_candidates, *entry.qml_candidates):
            self.assertNotIn("\n", candidate)

    def test_do_not_start_here_tokens_are_negative_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            maps_root = repo_root / "docs" / "agent_maps"
            _write(maps_root / "COVERAGE.md", "# Agent Map Coverage Matrix\n")
            _write(
                maps_root / "feature_routes" / "sample.md",
                "\n".join(
                    [
                        "# Sample Route",
                        "",
                        "## Start Here",
                        "- `ea_node_editor/primaryonlytoken.py`",
                        "",
                        "## Do Not Start Here",
                        "- `ea_node_editor/quarantinedonlytoken.py`",
                        "- `tests/test_excludedonlytoken.py`",
                        "- `ea_node_editor/ui_qml/components/AvoidOnlyRoute.qml`",
                        "- `neverrankthistoken`",
                        "",
                    ]
                ),
            )
            _write(
                repo_root / "docs" / "source_test_file_index.md",
                "# Source And Test File Index\n",
            )
            _write(
                repo_root / "docs" / "qml_navigation_index.json",
                json.dumps({"entries": []}),
            )

            index_data = indexer.build_index_data(repo_root)

        entry = {e.route_key: e for e in index_data.entries}[
            "feature_route:feature-routes-sample"
        ]
        self.assertIn("ea_node_editor/primaryonlytoken.py", entry.source_candidates)
        self.assertNotIn(
            "ea_node_editor/quarantinedonlytoken.py", entry.source_candidates
        )
        self.assertNotIn("tests/test_excludedonlytoken.py", entry.test_candidates)
        self.assertNotIn(
            "ea_node_editor/ui_qml/components/AvoidOnlyRoute.qml",
            entry.qml_candidates,
        )
        self.assertNotIn("quarantinedonlytoken", entry.keywords)
        self.assertNotIn("excludedonlytoken", entry.keywords)
        self.assertNotIn("avoidonlyroute", entry.keywords)
        self.assertNotIn("neverrankthistoken", entry.keywords)
        self.assertEqual(
            entry.do_not_start_here,
            (
                "ea_node_editor/quarantinedonlytoken.py",
                "tests/test_excludedonlytoken.py",
                "ea_node_editor/ui_qml/components/AvoidOnlyRoute.qml",
                "neverrankthistoken",
            ),
        )

    def test_section_anchors_are_stable_when_lines_shift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            maps_root = repo_root / "docs" / "agent_maps"
            _write(maps_root / "COVERAGE.md", "# Agent Map Coverage Matrix\n")
            map_path = maps_root / "subsystems" / "sample.md"
            _write(map_path, "# Sample Subsystem\n\nIntro.\n\n## Insertion Points\n\nBody.\n")
            _write(repo_root / "docs" / "source_test_file_index.md", "# Source And Test File Index\n")
            _write(repo_root / "docs" / "qml_navigation_index.json", json.dumps({"entries": []}))

            before = indexer.build_index_data(repo_root)
            before_json = indexer.render_json(before)
            _write(
                map_path,
                "<!-- leading comment -->\n\n\n# Sample Subsystem\n\nIntro.\n\n"
                "## Insertion Points\n\nBody.\n",
            )
            after = indexer.build_index_data(repo_root)

        entry = {e.route_key: e for e in after.entries}["subsystem:subsystems-sample"]
        self.assertEqual(
            entry.section_anchors, ("Sample Subsystem", "Insertion Points")
        )
        self.assertEqual(
            indexer.route_entry_to_dict(entry)["section_anchors"],
            ["Sample Subsystem", "Insertion Points"],
        )
        self.assertEqual(before_json, indexer.render_json(after))

    def test_main_writes_outputs_and_check_detects_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            output_path = repo_root / "docs" / "agent_route_index.md"
            json_path = repo_root / "docs" / "agent_route_index.json"
            maps_root = repo_root / "docs" / "agent_maps"
            _write(maps_root / "INDEX.md", "# Agent Map Atlas\n")
            _write(maps_root / "COVERAGE.md", "# Agent Map Coverage Matrix\n")
            _write(repo_root / "docs" / "source_test_file_index.md", "# Source And Test File Index\n")
            _write(repo_root / "docs" / "qml_navigation_index.json", json.dumps({"entries": []}))

            captured = io.StringIO()
            with redirect_stdout(captured):
                write_code = indexer.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--output",
                        str(output_path),
                        "--json-output",
                        str(json_path),
                    ]
                )
            self.assertEqual(write_code, 0)
            self.assertIn("Wrote docs/agent_route_index.md", captured.getvalue())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], 2)
            self.assertEqual(payload["summary"]["map_entries"], 2)

            with redirect_stdout(io.StringIO()):
                check_code = indexer.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--output",
                        str(output_path),
                        "--json-output",
                        str(json_path),
                        "--check",
                    ]
                )
            self.assertEqual(check_code, 0)

            output_path.write_text("stale\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                stale_code = indexer.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--output",
                        str(output_path),
                        "--json-output",
                        str(json_path),
                        "--check",
                    ]
                )
            self.assertEqual(stale_code, 1)


if __name__ == "__main__":
    unittest.main()
