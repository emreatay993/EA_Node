from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import generate_agent_route_index as indexer
from scripts import nav


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO_ROOT / "tests" / "fixtures" / "nav_owner_corpus.json"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


ROUTE_ENTRIES = [
    {
        "route_key": "feature_route:feature-routes-plotter-nodes",
        "kind": "feature_route",
        "title": "Plotter Nodes",
        "map_path": "docs/agent_maps/feature_routes/plotter_nodes.md",
        "source_candidates": ["ea_node_editor/nodes/builtins/plot/generic.py"],
        "test_candidates": ["tests/test_plotter_nodes.py"],
        "qml_candidates": [],
        "keywords": ["plotter", "plot", "nodes"],
        "aliases": ["plotter nodes"],
        "focused_verification": ["pytest tests/test_plotter_nodes.py"],
        "start_here": [
            "ea_node_editor/nodes/builtins/plot/generic.py",
            "tests/test_plotter_nodes.py",
        ],
        "do_not_start_here": ["ea_node_editor/ui_qml/"],
        "section_anchors": ["Plotter Nodes"],
    },
    {
        "route_key": "subsystem:subsystems-graph-domain",
        "kind": "subsystem",
        "title": "Graph Domain",
        "map_path": "docs/agent_maps/subsystems/graph_domain.md",
        "source_candidates": ["ea_node_editor/graph/records.py"],
        "test_candidates": [],
        "qml_candidates": [],
        "keywords": ["graph", "domain", "mutation"],
        "aliases": [],
        "focused_verification": [],
        "start_here": ["ea_node_editor/graph/records.py"],
        "do_not_start_here": [],
        "section_anchors": [],
    },
]

QML_ROUTE_ENTRIES = [
    {
        "route_key": "feature_route:feature-routes-workspace-ui",
        "kind": "feature_route",
        "title": "Workspace UI",
        "map_path": "docs/agent_maps/feature_routes/workspace_ui.md",
        "source_candidates": [
            "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml"
        ],
        "test_candidates": ["tests/test_quick_insert.py"],
        "qml_candidates": [
            "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml"
        ],
        "keywords": ["workspace", "library"],
        "aliases": [],
        "focused_verification": ["pytest tests/test_quick_insert.py -q"],
        "start_here": [
            "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml"
        ],
        "do_not_start_here": [],
        "section_anchors": [],
    },
    {
        "route_key": "qml:connectionquickinsertoverlay",
        "kind": "qml_component",
        "title": "ConnectionQuickInsertOverlay.qml",
        "map_path": "docs/agent_maps/subsystems/qml_shell_and_bridges.md",
        "source_candidates": [
            "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml"
        ],
        "test_candidates": [],
        "qml_candidates": [
            "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml"
        ],
        "keywords": [
            "connectionquickinsertoverlay",
            "opennodebrowserrequested",
        ],
        "aliases": [],
        "focused_verification": [],
        "start_here": [],
        "do_not_start_here": [],
        "section_anchors": [],
    },
]

QML_ENTRIES = [
    {
        "component_name": "ManagedToolTip",
        "path": "ea_node_editor/ui_qml/components/common/ManagedToolTip.qml",
        "aliases": ["ManagedToolTip", "ManagedToolTip.qml"],
        "root_component": "ToolTip",
        "symbol_anchors": [
            {
                "anchor": "ManagedToolTipPropertyPolicyBridge",
                "kind": "property",
                "name": "policyBridge",
            }
        ],
    },
    {
        "component_name": "ConnectionQuickInsertOverlay",
        "path": "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml",
        "aliases": ["ConnectionQuickInsertOverlay", "ConnectionQuickInsertOverlay.qml"],
        "root_component": "Rectangle",
        "signals": [{"name": "openNodeBrowserRequested"}],
        "symbol_anchors": [],
    },
]


class NavSearchTests(unittest.TestCase):
    def test_search_routes_ranks_exact_route_key_first(self) -> None:
        results = nav.search_routes(ROUTE_ENTRIES, "plotter-nodes")
        self.assertTrue(results)
        self.assertEqual(results[0]["route_key"], "feature_route:feature-routes-plotter-nodes")

    def test_search_routes_filters_non_matches(self) -> None:
        self.assertEqual(nav.search_routes(ROUTE_ENTRIES, "nonexistent-xyz"), [])

    def test_search_routes_requires_every_meaningful_query_token(self) -> None:
        self.assertEqual(nav.search_routes(ROUTE_ENTRIES, "plotter mutation"), [])

    def test_short_tokens_remain_meaningful_and_empty_tokens_never_match(self) -> None:
        short_entry = {
            **ROUTE_ENTRIES[0],
            "route_key": "feature_route:short",
            "keywords": ["ui", "io", "id", "qt"],
            "do_not_start_here": [],
        }
        for token in ("ui", "io", "id", "qt"):
            with self.subTest(token=token):
                self.assertEqual(nav.search_routes([short_entry], token), [short_entry])
        self.assertEqual(nav.search_routes([short_entry], "the and"), [])
        self.assertEqual(nav.search_source(["ea_node_editor/a.py"], [], [], "the"), [])

    def test_do_not_start_here_is_not_positive_route_evidence(self) -> None:
        self.assertEqual(nav.search_routes(ROUTE_ENTRIES, "ui"), [])

    def test_search_routes_returns_all_tied_top_owners(self) -> None:
        first = {
            **ROUTE_ENTRIES[0],
            "route_key": "feature_route:first",
            "map_path": "docs/agent_maps/feature_routes/first.md",
            "aliases": ["shared lookup"],
        }
        second = {
            **ROUTE_ENTRIES[0],
            "route_key": "feature_route:second",
            "map_path": "docs/agent_maps/feature_routes/second.md",
            "aliases": ["shared lookup"],
        }
        results = nav.search_routes([first, second], "shared lookup")
        self.assertEqual(
            [item["route_key"] for item in results],
            ["feature_route:first", "feature_route:second"],
        )

    def test_search_routes_skips_qml_kind(self) -> None:
        mixed = [*ROUTE_ENTRIES, {"route_key": "qml:x", "kind": "qml_component", "title": "plotter"}]
        results = nav.search_routes(mixed, "plotter")
        self.assertTrue(all(r.get("kind") != "qml_component" for r in results))

    def test_search_qml_matches_component_and_alias(self) -> None:
        by_name = nav.search_qml(QML_ENTRIES, "ManagedToolTip")
        self.assertEqual(by_name[0]["component_name"], "ManagedToolTip")
        self.assertTrue(nav.search_qml(QML_ENTRIES, "managedtooltip.qml"))

    def test_search_qml_matches_generated_symbol_metadata(self) -> None:
        results = nav.search_qml(QML_ENTRIES, "open node browser requested")
        self.assertEqual(results[0]["component_name"], "ConnectionQuickInsertOverlay")

    def test_search_source_reports_owner_maps(self) -> None:
        source = ["ea_node_editor/nodes/builtins/plot/generic.py"]
        tests = ["tests/test_plotter_nodes.py"]
        items = nav.search_source(source, tests, ROUTE_ENTRIES, "generic")
        self.assertEqual(items[0]["path"], "ea_node_editor/nodes/builtins/plot/generic.py")
        self.assertIn(
            "docs/agent_maps/feature_routes/plotter_nodes.md", items[0]["owner_maps"]
        )


class NavCliTests(unittest.TestCase):
    def _make_repo(self, temp_dir: str) -> Path:
        repo_root = Path(temp_dir)
        _write(
            repo_root / nav.ROUTE_INDEX_REL,
            json.dumps(
                {"version": 1, "entries": [*ROUTE_ENTRIES, *QML_ROUTE_ENTRIES]}
            ),
        )
        _write(
            repo_root / nav.QML_INDEX_REL,
            json.dumps({"version": 3, "entries": QML_ENTRIES}),
        )
        _write(
            repo_root / nav.SOURCE_TEST_INDEX_REL,
            "\n".join(
                [
                    "## Source Code",
                    "| Path |",
                    "| --- |",
                    "| `ea_node_editor/nodes/builtins/plot/generic.py` |",
                    "## Test Modules",
                    "| Path |",
                    "| --- |",
                    "| `tests/test_plotter_nodes.py` |",
                ]
            ),
        )
        return repo_root

    def test_route_json_output_is_valid_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            captured = io.StringIO()
            with redirect_stdout(captured):
                code = nav.main(["--repo-root", str(repo_root), "route", "plotter", "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(captured.getvalue())
            self.assertEqual(
                payload[0]["map_path"], "docs/agent_maps/feature_routes/plotter_nodes.md"
            )

    def test_find_defaults_to_compact_owner_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            captured = io.StringIO()
            with redirect_stdout(captured):
                code = nav.main(["--repo-root", str(repo_root), "find", "plot"])
            self.assertEqual(code, 0)
            out = captured.getvalue()
            self.assertIn("Likely owner:", out)
            self.assertIn("tests/test_plotter_nodes.py", out)
            self.assertNotIn("== Source/Test ==", out)

    def test_find_routes_qml_component_to_owning_map_and_test(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            captured = io.StringIO()
            with redirect_stdout(captured):
                code = nav.main(
                    ["--repo-root", str(repo_root), "find", "quick", "insert"]
                )
            self.assertEqual(code, 0)
            out = captured.getvalue()
            self.assertIn("docs/agent_maps/feature_routes/workspace_ui.md", out)
            self.assertIn("ConnectionQuickInsertOverlay.qml", out)
            self.assertIn("tests/test_quick_insert.py", out)

    def test_find_prefers_exact_route_aliases_before_qml_owner_heuristic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            exact_z = {
                **ROUTE_ENTRIES[0],
                "route_key": "feature_route:exact-z",
                "title": "Exact Z",
                "map_path": "docs/agent_maps/feature_routes/exact_z.md",
                "aliases": ["bounded rich preview"],
            }
            exact_a = {
                **ROUTE_ENTRIES[0],
                "route_key": "feature_route:exact-a",
                "title": "Exact A",
                "map_path": "docs/agent_maps/feature_routes/exact_a.md",
                "aliases": ["bounded rich preview"],
            }
            competing_qml = {
                **QML_ROUTE_ENTRIES[1],
                "route_key": "qml:boundedrichpreview",
                "title": "BoundedRichPreview.qml",
                "keywords": ["bounded", "rich", "preview"],
            }
            _write(
                repo_root / nav.ROUTE_INDEX_REL,
                json.dumps(
                    {
                        "version": 1,
                        "entries": [
                            *ROUTE_ENTRIES,
                            QML_ROUTE_ENTRIES[0],
                            competing_qml,
                            exact_z,
                            exact_a,
                        ],
                    }
                ),
            )

            captured = io.StringIO()
            with redirect_stdout(captured):
                code = nav.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "find",
                        "bounded",
                        "rich",
                        "preview",
                        "--json",
                    ]
                )

            self.assertEqual(code, 0)
            payload = json.loads(captured.getvalue())
            self.assertEqual(
                [owner["owner_map"] for owner in payload["owners"]],
                [
                    "docs/agent_maps/feature_routes/exact_a.md",
                    "docs/agent_maps/feature_routes/exact_z.md",
                ],
            )
            self.assertNotIn(
                "docs/agent_maps/feature_routes/workspace_ui.md",
                [owner["owner_map"] for owner in payload["owners"]],
            )

    def test_find_expand_preserves_broad_discovery_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            captured = io.StringIO()
            with redirect_stdout(captured):
                code = nav.main(
                    ["--repo-root", str(repo_root), "find", "plot", "--expand"]
                )
            self.assertEqual(code, 0)
            out = captured.getvalue()
            self.assertIn("== Routes ==", out)
            self.assertIn("== Source/Test ==", out)

    def test_find_default_json_is_a_compact_owner_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            captured = io.StringIO()
            with redirect_stdout(captured):
                code = nav.main(
                    ["--repo-root", str(repo_root), "find", "plotter", "--json"]
                )
            self.assertEqual(code, 0)
            payload = json.loads(captured.getvalue())
            self.assertEqual(payload["query"], "plotter")
            self.assertEqual(len(payload["owners"]), 1)
            self.assertEqual(
                payload["owners"][0]["owner_map"],
                "docs/agent_maps/feature_routes/plotter_nodes.md",
            )
            self.assertLessEqual(
                len(captured.getvalue().encode("utf-8")), nav.MAX_DEFAULT_OUTPUT_BYTES
            )

    def test_find_no_match_json_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            captured = io.StringIO()
            with redirect_stdout(captured):
                code = nav.main(
                    ["--repo-root", str(repo_root), "find", "missing", "--json"]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(captured.getvalue()),
                {"query": "missing", "owners": []},
            )

    def test_no_matches_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            captured = io.StringIO()
            with redirect_stdout(captured):
                nav.main(["--repo-root", str(repo_root), "route", "zzz-no-match"])
            self.assertIn("No matches.", captured.getvalue())

    def test_line_resolves_current_map_qml_and_source_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            map_path = repo_root / "docs" / "agent_maps" / "sample.md"
            qml_path = repo_root / "ea_node_editor" / "ui_qml" / "Sample.qml"
            source_path = repo_root / "ea_node_editor" / "sample.py"
            _write(map_path, "# Sample\n\n## Start Here\n")
            _write(qml_path, "Item {\n    property string title: \"sample\"\n}\n")
            _write(source_path, "def build_sample():\n    return True\n")

            cases = (
                ("docs/agent_maps/sample.md", "Start Here", 3),
                ("ea_node_editor/ui_qml/Sample.qml", "title", 2),
                ("ea_node_editor/sample.py", "build_sample", 1),
            )
            for selected_path, anchor, expected_line in cases:
                with self.subTest(path=selected_path):
                    captured = io.StringIO()
                    with redirect_stdout(captured):
                        code = nav.main(
                            [
                                "--repo-root",
                                str(repo_root),
                                "line",
                                selected_path,
                                anchor,
                                "--json",
                            ]
                        )
                    self.assertEqual(code, 0)
                    payload = json.loads(captured.getvalue())
                    self.assertEqual(payload["line"], expected_line)
                    self.assertEqual(payload["path"], selected_path)

    def test_qml_anchor_output_round_trips_to_exact_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self._make_repo(temp_dir)
            qml_path = repo_root / QML_ENTRIES[0]["path"]
            _write(qml_path, "Item {\n    property var policyBridge: null\n}\n")

            captured = io.StringIO()
            with redirect_stdout(captured):
                nav.main(
                    ["--repo-root", str(repo_root), "qml", "ManagedToolTip"]
                )
            self.assertIn("symbols: policyBridge", captured.getvalue())
            self.assertNotIn("ManagedToolTipPropertyPolicyBridge", captured.getvalue())

            result = nav.resolve_current_line(
                repo_root,
                QML_ENTRIES[0]["path"],
                "ManagedToolTipPropertyPolicyBridge",
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["line"], 2)

    def test_line_resolution_is_exact_and_rejects_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            repo_root = self._make_repo(temp_dir)
            qml_path = repo_root / "ea_node_editor/ui_qml/Exact.qml"
            _write(
                qml_path,
                "\n".join(
                    (
                        "Item {",
                        "    // commentOnly width",
                        "    property real defaultPanelWidth: parent.width",
                        "    width: 42",
                        "    property real panelWidth: 0",
                        "}",
                    )
                ),
            )

            width = nav.resolve_current_line(repo_root, str(qml_path), "width")
            self.assertIsNotNone(width)
            self.assertEqual(width["line"], 4)
            self.assertIsNone(nav.resolve_current_line(repo_root, str(qml_path), "PANELWIDTH"))
            self.assertIsNone(nav.resolve_current_line(repo_root, str(qml_path), "commentOnly"))
            with self.assertRaisesRegex(ValueError, "must not be blank"):
                nav.resolve_current_line(repo_root, str(qml_path), "   ")

            outside_path = Path(outside_dir) / "outside.py"
            _write(outside_path, "outside = True\n")
            with self.assertRaisesRegex(ValueError, "inside the repository"):
                nav.resolve_current_line(repo_root, str(outside_path), "outside")
            traversal = Path("..") / Path(outside_dir).name / outside_path.name
            with self.assertRaisesRegex(ValueError, "inside the repository"):
                nav.resolve_current_line(repo_root, str(traversal), "outside")

    def test_tied_owner_budget_keeps_primary_capsule_complete(self) -> None:
        entries = []
        for index in range(5):
            entries.append(
                {
                    **ROUTE_ENTRIES[0],
                    "route_key": f"feature_route:tied-{index}",
                    "title": f"Tied Owner {index}",
                    "map_path": f"docs/agent_maps/feature_routes/tied_{index}.md",
                    "start_here": [
                        f"ea_node_editor/tied_{index}.py",
                        f"tests/test_tied_{index}.py",
                    ],
                    "test_candidates": [f"tests/test_tied_{index}.py"],
                    "do_not_start_here": [],
                }
            )

        capsules = nav.build_owner_capsules(entries, "shared")
        self.assertEqual(capsules[0]["owner_map"], entries[0]["map_path"])
        self.assertEqual(capsules[0]["path"], "ea_node_editor/tied_0.py")
        self.assertEqual(capsules[0]["focused_test"], "tests/test_tied_0.py")
        self.assertIn("verification", capsules[0])
        paths = {
            str(value)
            for capsule in capsules
            for field in ("owner_map", "path", "focused_test")
            if (value := capsule.get(field))
        }
        self.assertLessEqual(len(paths), nav.MAX_DEFAULT_PATHS)
        for as_json in (False, True):
            captured = io.StringIO()
            with redirect_stdout(captured):
                nav._emit_owner_capsules("shared", capsules, as_json)
            self.assertLessEqual(
                len(captured.getvalue().encode("utf-8")),
                nav.MAX_DEFAULT_OUTPUT_BYTES,
            )


class NavOwnerCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        index_data = indexer.build_index_data(REPO_ROOT)
        cls.entries = [indexer.route_entry_to_dict(entry) for entry in index_data.entries]
        cls.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    def test_owner_corpus_accuracy_and_default_output_budgets(self) -> None:
        cases = self.corpus["cases"]
        self.assertEqual(self.corpus["version"], 1)
        self.assertGreaterEqual(len(cases), 10)
        top_one_matches = 0

        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertLessEqual(len(case["secondary_owners"]), 2)
                ranked = nav.rank_routes(self.entries, case["query"])
                ranked_maps = [entry["map_path"] for entry in ranked]
                self.assertTrue(ranked_maps)
                self.assertIn(case["primary_owner"], ranked_maps[:3])
                top_one_matches += ranked_maps[0] == case["primary_owner"]

                owners = nav.search_routes(self.entries, case["query"])
                capsules = nav.build_owner_capsules(owners, case["query"])
                paths: set[str] = set()
                for capsule in capsules:
                    for field in ("owner_map", "path", "focused_test"):
                        if capsule.get(field):
                            paths.add(str(capsule[field]))
                    paths.update(capsule.get("do_not_start_here", []))
                self.assertLessEqual(len(paths), nav.MAX_DEFAULT_PATHS)

                for as_json in (False, True):
                    captured = io.StringIO()
                    with redirect_stdout(captured):
                        nav._emit_owner_capsules(case["query"], capsules, as_json)
                    self.assertLessEqual(
                        len(captured.getvalue().encode("utf-8")),
                        nav.MAX_DEFAULT_OUTPUT_BYTES,
                    )

                primary_capsule = nav.build_owner_capsules(
                    [ranked[0]], case["query"]
                )[0]
                if expected_primary_path := case.get("primary_path"):
                    self.assertEqual(ranked_maps[0], case["primary_owner"])
                    self.assertEqual(
                        primary_capsule.get("path"), expected_primary_path
                    )
                if ranked_maps[0] == case["primary_owner"]:
                    self.assertEqual(
                        primary_capsule.get("focused_test"), case["focused_test"]
                    )
                self.assertNotIn(
                    primary_capsule.get("path"), case["not_first_paths"]
                )

        self.assertGreaterEqual(top_one_matches, len(cases) - 2)


if __name__ == "__main__":
    unittest.main()
