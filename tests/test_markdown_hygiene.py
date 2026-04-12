from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import verification_manifest as manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_markdown_links.py"
UI_PACKET_DOCS_ROOT = (
    REPO_ROOT / "docs" / "specs" / "work_packets" / "ui_context_scalability_refactor"
)
UI_SUBSYSTEM_CONTRACT_DOCS = (
    UI_PACKET_DOCS_ROOT / "SHELL_PACKET.md",
    UI_PACKET_DOCS_ROOT / "PRESENTERS_PACKET.md",
    UI_PACKET_DOCS_ROOT / "GRAPH_SCENE_PACKET.md",
    UI_PACKET_DOCS_ROOT / "GRAPH_CANVAS_PACKET.md",
    UI_PACKET_DOCS_ROOT / "EDGE_RENDERING_PACKET.md",
    UI_PACKET_DOCS_ROOT / "VIEWER_PACKET.md",
)
UI_REGRESSION_PACKET_DOCS = (
    UI_PACKET_DOCS_ROOT / "MAIN_WINDOW_SHELL_TEST_PACKET.md",
    UI_PACKET_DOCS_ROOT / "GRAPH_SURFACE_TEST_PACKET.md",
    UI_PACKET_DOCS_ROOT / "TRACK_B_TEST_PACKET.md",
)
PLAN_TEMPLATE_PATH = REPO_ROOT / "PLANS_TO_IMPLEMENT" / "PLAN_TEMPLATE.md"
PLAN_REPO_OVERLAY_PATH = REPO_ROOT / "PLANS_TO_IMPLEMENT" / "PLAN_REPO_OVERLAY.md"
IN_PROGRESS_PLANS_ROOT = REPO_ROOT / "PLANS_TO_IMPLEMENT" / "in_progress"


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_text(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class MarkdownHygieneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checker = load_module("check_markdown_links_for_tests", CHECKER_PATH)

    def test_audit_repository_passes_for_current_repo(self) -> None:
        self.assertEqual([], self.checker.audit_repository(REPO_ROOT))

    def test_spec_index_registers_architecture_residual_matrix_link(self) -> None:
        spec_index_text = (REPO_ROOT / "docs" / "specs" / "INDEX.md").read_text(
            encoding="utf-8-sig"
        )
        matrix_text = (REPO_ROOT / manifest.ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX_DOC).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "[ARCHITECTURE_RESIDUAL_REFACTOR QA Matrix](perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md)",
            spec_index_text,
        )
        self.assertTrue(matrix_text.startswith("# Architecture Residual Refactor QA Matrix"))

    def test_spec_index_registers_ui_context_scalability_matrix_link(self) -> None:
        spec_index_path = REPO_ROOT / "docs" / "specs" / "INDEX.md"
        spec_index_text = spec_index_path.read_text(encoding="utf-8-sig")
        matrix_path = REPO_ROOT / "docs" / "specs" / "perf" / "UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md"
        matrix_text = matrix_path.read_text(encoding="utf-8-sig")

        self.assertIn(
            "[UI_CONTEXT_SCALABILITY_REFACTOR QA Matrix](perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md)",
            spec_index_text,
        )
        self.assertTrue(matrix_text.startswith("# UI Context Scalability Refactor QA Matrix"))
        self.assertEqual([], self.checker.audit_markdown_file(spec_index_path, REPO_ROOT))
        self.assertEqual([], self.checker.audit_markdown_file(matrix_path, REPO_ROOT))

    def test_spec_index_registers_ui_context_scalability_followup_packet_set(self) -> None:
        spec_index_path = REPO_ROOT / "docs" / "specs" / "INDEX.md"
        spec_index_text = spec_index_path.read_text(encoding="utf-8-sig")
        matrix_path = (
            REPO_ROOT / "docs" / "specs" / "perf" / "UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md"
        )
        matrix_text = matrix_path.read_text(encoding="utf-8-sig")

        self.assertIn(
            "[UI_CONTEXT_SCALABILITY_FOLLOWUP Work Packet Manifest](work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md)",
            spec_index_text,
        )
        self.assertIn(
            "[UI_CONTEXT_SCALABILITY_FOLLOWUP Status Ledger](work_packets/ui_context_scalability_followup/UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md)",
            spec_index_text,
        )
        self.assertIn(
            "[UI_CONTEXT_SCALABILITY_FOLLOWUP QA Matrix](perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md)",
            spec_index_text,
        )
        self.assertTrue(matrix_text.startswith("# UI Context Scalability Follow-Up QA Matrix"))
        self.assertEqual([], self.checker.audit_markdown_file(spec_index_path, REPO_ROOT))
        self.assertEqual([], self.checker.audit_markdown_file(matrix_path, REPO_ROOT))

    def test_readme_links_dpf_operator_backend_closeout_docs(self) -> None:
        readme_path = REPO_ROOT / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8-sig")
        review_path = REPO_ROOT / "docs" / "DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md"
        review_text = review_path.read_text(encoding="utf-8-sig")
        matrix_path = (
            REPO_ROOT / "docs" / "specs" / "perf" / "DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md"
        )
        matrix_text = matrix_path.read_text(encoding="utf-8-sig")

        self.assertIn(
            "[DPF Operator Backend Review](docs/DPF_OPERATOR_PLUGIN_BACKEND_REVIEW_2026-04-12.md)",
            readme_text,
        )
        self.assertIn(
            "[DPF Operator Backend QA Matrix](docs/specs/perf/DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_QA_MATRIX.md)",
            readme_text,
        )
        self.assertTrue(review_text.startswith("# DPF Operator Plugin Backend Review 2026-04-12"))
        self.assertTrue(matrix_text.startswith("# DPF Operator Plugin Backend Refactor QA Matrix"))
        self.assertEqual([], self.checker.audit_markdown_file(readme_path, REPO_ROOT))
        self.assertEqual([], self.checker.audit_markdown_file(review_path, REPO_ROOT))
        self.assertEqual([], self.checker.audit_markdown_file(matrix_path, REPO_ROOT))

    def test_architecture_registers_plan_template_and_overlay(self) -> None:
        architecture_text = (REPO_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8-sig")

        self.assertIn(
            "[plan template](PLANS_TO_IMPLEMENT/PLAN_TEMPLATE.md)",
            architecture_text,
        )
        self.assertIn(
            "[planning overlay](PLANS_TO_IMPLEMENT/PLAN_REPO_OVERLAY.md)",
            architecture_text,
        )
        self.assertIn(
            "one primary source owner and one primary regression owner",
            architecture_text,
        )

    def test_plan_template_defines_task_and_packet_conversion_sections(self) -> None:
        template_text = PLAN_TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        required_snippets = (
            "## Required Authoring Rules",
            "## Template Skeleton",
            "## Execution Tasks",
            "## Work Packet Conversion Map",
            "Conservative write scope",
            "Packetization notes",
        )

        for snippet in required_snippets:
            self.assertIn(snippet, template_text)

        self.assertNotIn("docs/specs/INDEX.md", template_text)
        self.assertNotIn("ui_context_scalability_refactor", template_text)
        self.assertEqual([], self.checker.audit_markdown_file(PLAN_TEMPLATE_PATH, REPO_ROOT))

    def test_plan_repo_overlay_registers_local_packetization_anchors(self) -> None:
        overlay_text = PLAN_REPO_OVERLAY_PATH.read_text(encoding="utf-8-sig")

        required_snippets = (
            "## Local Planning Entry Points",
            "## Local Packetization Defaults",
            "## Local Verification Defaults",
            "## Local Ownership Notes",
            "[docs/specs/INDEX.md](../docs/specs/INDEX.md)",
            "[docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md]",
            "[docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md]",
        )

        for snippet in required_snippets:
            self.assertIn(snippet, overlay_text)

        self.assertEqual([], self.checker.audit_markdown_file(PLAN_REPO_OVERLAY_PATH, REPO_ROOT))

    def test_in_progress_plans_include_execution_tasks_and_packet_conversion_map(self) -> None:
        required_headings = (
            "## Summary",
            "## Key Changes",
            "## Public Interface Changes",
            "## Execution Tasks",
            "## Work Packet Conversion Map",
            "## Test Plan",
            "## Assumptions",
        )

        plan_paths = sorted(IN_PROGRESS_PLANS_ROOT.glob("*.md"))
        if not plan_paths:
            return

        for path in plan_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8-sig")

                for heading in required_headings:
                    self.assertIn(heading, text)

                self.assertEqual([], self.checker.audit_markdown_file(path, REPO_ROOT))

    def test_ui_subsystem_packet_contract_docs_have_required_sections(self) -> None:
        required_headings = (
            "## Owner Files",
            "## Public Entry Points",
            "## State Owner",
            "## Allowed Dependencies",
            "## Invariants",
            "## Forbidden Shortcuts",
            "## Required Tests",
        )

        for path in UI_SUBSYSTEM_CONTRACT_DOCS:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8-sig")

                for heading in required_headings:
                    self.assertIn(heading, text)
                self.assertEqual([], self.checker.audit_markdown_file(path, REPO_ROOT))

    def test_ui_regression_packet_contract_docs_have_required_sections(self) -> None:
        required_headings = (
            "## Source Packet Docs",
            "## Owner Files",
            "## Public Entry Points",
            "## State Owner",
            "## Allowed Dependencies",
            "## Invariants",
            "## Forbidden Shortcuts",
            "## Required Tests",
        )

        for path in UI_REGRESSION_PACKET_DOCS:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8-sig")

                for heading in required_headings:
                    self.assertIn(heading, text)
                self.assertEqual([], self.checker.audit_markdown_file(path, REPO_ROOT))

    def test_ui_subsystem_packet_index_maps_contract_docs_and_test_anchors(self) -> None:
        index_path = UI_PACKET_DOCS_ROOT / "SUBSYSTEM_PACKET_INDEX.md"
        index_text = index_path.read_text(encoding="utf-8-sig")

        self.assertIn("[Shell Packet](./SHELL_PACKET.md)", index_text)
        self.assertIn("[Presenters Packet](./PRESENTERS_PACKET.md)", index_text)
        self.assertIn("[Graph Scene Packet](./GRAPH_SCENE_PACKET.md)", index_text)
        self.assertIn("[Graph Canvas Packet](./GRAPH_CANVAS_PACKET.md)", index_text)
        self.assertIn("[Edge Rendering Packet](./EDGE_RENDERING_PACKET.md)", index_text)
        self.assertIn("[Viewer Packet](./VIEWER_PACKET.md)", index_text)
        self.assertIn("[Main Window Shell Test Packet](./MAIN_WINDOW_SHELL_TEST_PACKET.md)", index_text)
        self.assertIn("[Graph Surface Test Packet](./GRAPH_SURFACE_TEST_PACKET.md)", index_text)
        self.assertIn("[Track B Test Packet](./TRACK_B_TEST_PACKET.md)", index_text)
        self.assertIn("[feature packet template](./FEATURE_PACKET_TEMPLATE.md)", index_text)
        self.assertIn("primary source owner and one primary regression owner", index_text)
        self.assertIn("`tests/test_main_window_shell.py`", index_text)
        self.assertIn("`tests/main_window_shell/bridge_contracts.py`", index_text)
        self.assertIn("`tests/test_graph_scene_bridge_bind_regression.py`", index_text)
        self.assertIn("`tests/test_graph_surface_input_contract.py`", index_text)
        self.assertIn("`tests/test_graph_surface_input_controls.py`", index_text)
        self.assertIn("`tests/test_flow_edge_labels.py`", index_text)
        self.assertIn("`tests/test_viewer_session_bridge.py`", index_text)
        self.assertEqual([], self.checker.audit_markdown_file(index_path, REPO_ROOT))

    def test_ui_feature_packet_template_requires_owner_and_inherited_tests(self) -> None:
        template_path = UI_PACKET_DOCS_ROOT / "FEATURE_PACKET_TEMPLATE.md"
        template_text = template_path.read_text(encoding="utf-8-sig")

        self.assertIn("[subsystem packet index](./SUBSYSTEM_PACKET_INDEX.md)", template_text)
        self.assertIn("Owning Source Subsystem Packet", template_text)
        self.assertIn("Owning Regression Packet", template_text)
        self.assertIn("Inherited Secondary Subsystem Docs", template_text)
        self.assertIn("Inherited Secondary Regression Docs", template_text)
        self.assertIn("Regression Public Entry Points", template_text)
        self.assertIn("Required Tests", template_text)
        self.assertIn("Forbidden Shortcuts", template_text)
        self.assertEqual([], self.checker.audit_markdown_file(template_path, REPO_ROOT))

    def test_audit_repository_reports_missing_local_markdown_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            write_text(repo_root, "README.md", "[Broken](docs/missing.md)\n")

            issues = self.checker.audit_repository(repo_root)

        self.assertEqual(
            ["README.md:1: broken markdown link target: docs/missing.md"],
            issues,
        )

    def test_audit_repository_reports_missing_markdown_heading_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            write_text(
                repo_root,
                "README.md",
                "[Setup](docs/GETTING_STARTED.md#missing-anchor)\n",
            )
            write_text(
                repo_root,
                "docs/GETTING_STARTED.md",
                "# Getting Started\n\n## Actual Heading\n",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertEqual(
            [
                "README.md:1: missing markdown heading anchor for "
                "docs/GETTING_STARTED.md#missing-anchor"
            ],
            issues,
        )

    def test_audit_repository_ignores_code_fence_and_external_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            write_text(
                repo_root,
                "README.md",
                "```md\n[Ignored](docs/missing.md)\n```\n"
                "[External](https://example.com)\n",
            )

            issues = self.checker.audit_repository(repo_root)

        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
