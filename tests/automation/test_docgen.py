# Purpose: Pin the generated automation reference (docgen determinism, coverage, guide drift), the skill file + installer, the examples, and the new docs' links.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_docgen.py
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.automation import docgen, op_catalog
from ea_node_editor.automation.errors import ERROR_CODES

REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDE_PATH = REPO_ROOT / "docs" / "AUTOMATION_API_GUIDE.md"
SKILL_DIR = REPO_ROOT / "docs" / "automation" / "skills" / "corex-automation"
SKILL_PATH = SKILL_DIR / "SKILL.md"
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_automation_skill.py"
LINK_CHECKER_PATH = REPO_ROOT / "scripts" / "check_markdown_links.py"
EXAMPLES_DIR = REPO_ROOT / "examples" / "automation"
EXAMPLE_SCRIPTS = ("flowchart.py", "annotated_media_board.py", "subnode_workflow.py", "run_and_screenshot.py")
REGENERATE_MESSAGE = (
    "docs/AUTOMATION_API_GUIDE.md is out of date with the op catalog. Regenerate it with:\n"
    "    .\\venv\\Scripts\\python.exe -m ea_node_editor.automation.docgen --update-guide"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _front_matter(text: str) -> dict[str, str]:
    """Parse simple ``key: value`` YAML front matter (the only form SKILL.md uses)."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if match is None:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


class DocgenOutputTests(unittest.TestCase):
    def test_renderers_are_deterministic_and_newline_terminated(self) -> None:
        for render in (
            docgen.render_tool_index_markdown,
            docgen.render_op_reference_markdown,
            docgen.render_error_reference_markdown,
            docgen.render_generated_reference_markdown,
        ):
            with self.subTest(renderer=render.__name__):
                first = render()
                self.assertEqual(first, render())
                self.assertTrue(first.endswith("\n"))
                self.assertFalse(first.endswith("\n\n"))

    def test_generated_reference_is_the_three_sections_joined(self) -> None:
        expected = "\n".join(
            (
                docgen.render_tool_index_markdown(),
                docgen.render_op_reference_markdown(),
                docgen.render_error_reference_markdown(),
            )
        )
        self.assertEqual(docgen.render_generated_reference_markdown(), expected)

    def test_op_reference_has_one_section_per_domain_and_op_in_catalog_order(self) -> None:
        text = docgen.render_op_reference_markdown()
        domains = re.findall(r"^### (\S+)$", text, re.MULTILINE)
        self.assertEqual(domains, list(op_catalog.ops_by_domain()))
        op_headings = re.findall(r"^#### (\S+)$", text, re.MULTILINE)
        self.assertEqual(op_headings, list(op_catalog.op_names()))

    def test_output_mentions_every_op_tool_and_error_code(self) -> None:
        text = docgen.render_generated_reference_markdown()
        for op in op_catalog.all_ops():
            with self.subTest(op=op.name):
                self.assertIn(f"#### {op.name}", text)
                if op.mcp_tool:
                    self.assertIn(f"`{op.mcp_tool}`", text)
        for code in ERROR_CODES:
            with self.subTest(code=code):
                self.assertIn(f"`{code}`", text)

    def test_op_blocks_carry_flags_params_results_and_examples(self) -> None:
        text = docgen.render_op_reference_markdown()
        apply_block = text.split("#### graph.apply", 1)[1]
        self.assertIn("MCP tool: `graph_apply`. Flags: undo step.", apply_block)
        self.assertIn("| `ops` | `array<object>` | yes |", apply_block)
        self.assertIn("```json", apply_block)
        node_add = text.split("#### node.add\n", 1)[1].split("#### ", 1)[0]
        self.assertIn("Flags: undo step, apply-allowed.", node_add)
        self.assertIn("| `properties` | `object` | no |", node_add)
        self.assertIn("Result keys: `node_id`, `node`.", node_add)
        run_start = text.split("#### run.start\n", 1)[1].split("#### ", 1)[0]
        self.assertIn("Flags: read-only, deferred.", run_start)
        self.assertIn("| `timeout_s` | `number` | no | `120` |", run_start)
        status = text.split("#### app.status\n", 1)[1].split("#### ", 1)[0]
        self.assertIn("No parameters.", status)

    def test_prose_escapes_markdown_significant_characters(self) -> None:
        text = docgen.render_op_reference_markdown()
        self.assertIn("ops[i].\\<path>", text)
        self.assertNotIn("passive.flowchart.*,", text)
        for line in text.splitlines():
            if line.startswith("| `") and "`" in line:
                cells = re.sub(r"`[^`]*`", "", line)
                self.assertNotRegex(cells, r"(?<!\\)<[A-Za-z]", line)

    def test_main_prints_sections_and_updates_a_guide_copy(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(docgen.main(["--section", "errors"]), 0)
        self.assertEqual(buffer.getvalue(), docgen.render_error_reference_markdown())
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "guide.md"
            copy.write_text(f"# Guide\n\n{docgen.GENERATED_BLOCK_BEGIN}\nstale\n{docgen.GENERATED_BLOCK_END}\n\nTail\n", encoding="utf-8")
            self.assertTrue(docgen.update_guide(copy))
            self.assertFalse(docgen.update_guide(copy))
            updated = copy.read_text(encoding="utf-8")
            self.assertTrue(updated.startswith("# Guide\n\n"))
            self.assertTrue(updated.endswith(f"{docgen.GENERATED_BLOCK_END}\n\nTail\n"))
            self.assertEqual(docgen.extract_guide_block(updated), "\n" + docgen.render_generated_reference_markdown())


class GuideDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guide = GUIDE_PATH.read_text(encoding="utf-8")

    def test_generated_block_matches_docgen_byte_for_byte(self) -> None:
        self.assertEqual(self.guide.count(docgen.GENERATED_BLOCK_BEGIN), 1)
        self.assertEqual(self.guide.count(docgen.GENERATED_BLOCK_END), 1)
        block = docgen.extract_guide_block(self.guide)
        self.assertIsNotNone(block, "the guide lost its generated-block markers")
        self.assertEqual(block, "\n" + docgen.render_generated_reference_markdown(), REGENERATE_MESSAGE)

    def test_every_mcp_tool_appears_in_the_guide(self) -> None:
        for op in op_catalog.mcp_tool_ops():
            with self.subTest(tool=op.mcp_tool):
                self.assertIn(str(op.mcp_tool), self.guide)

    def test_hand_written_sections_cover_setup_and_registration(self) -> None:
        manual = self.guide.split(docgen.GENERATED_BLOCK_BEGIN, 1)[0]
        for needle in (
            "--automation",
            "claude mcp add corex",
            "[mcp_servers.corex]",
            "mcpServers",
            "install_automation_skill.py --claude --codex",
            "COREX_AUTOMATION_DISCOVERY_DIR",
            "COREX_SESSION_STATE_DIR",
            "## UI parity",
            "## Troubleshooting",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.guide if needle == "## Troubleshooting" else manual)
        self.assertNotIn("—", self.guide, "keep the guide free of em dashes")

    def test_new_docs_have_resolving_relative_links(self) -> None:
        checker = _load_module("check_markdown_links_for_docgen_tests", LINK_CHECKER_PATH)
        for path in (GUIDE_PATH, EXAMPLES_DIR / "README.md", SKILL_PATH):
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                self.assertEqual(checker.audit_markdown_file(path, REPO_ROOT), [])


class SkillAndInstallerTests(unittest.TestCase):
    def test_skill_front_matter_names_and_describes_the_skill(self) -> None:
        text = SKILL_PATH.read_text(encoding="utf-8")
        fields = _front_matter(text)
        self.assertEqual(fields.get("name"), "corex-automation")
        self.assertGreater(len(fields.get("description", "")), 40)
        self.assertIn("docs/AUTOMATION_API_GUIDE.md", text)
        self.assertIn("corex_status", text)
        self.assertIn("graph_apply", text)

    def test_dry_run_all_lists_both_destinations_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, USERPROFILE=home)
            completed = subprocess.run(
                [sys.executable, str(INSTALLER_PATH), "--all", "--dry-run"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for parts in ((".claude", "skills"), (".codex", "skills")):
                with self.subTest(target=parts[0]):
                    self.assertIn(str(Path(home).joinpath(*parts, "corex-automation")), completed.stdout)
            self.assertIn("nothing was written", completed.stdout)
            self.assertEqual(list(Path(home).iterdir()), [])

    def test_install_copies_skips_existing_and_force_replaces(self) -> None:
        installer = _load_module("install_automation_skill_for_tests", INSTALLER_PATH)
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(installer.main(["--claude", "--home", home]), 0)
            installed = Path(home) / ".claude" / "skills" / "corex-automation" / "SKILL.md"
            self.assertEqual(installed.read_text(encoding="utf-8"), SKILL_PATH.read_text(encoding="utf-8"))
            self.assertFalse((Path(home) / ".codex").exists())
            installed.write_text("stale", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--claude", "--home", home]), 1)
            self.assertEqual(installed.read_text(encoding="utf-8"), "stale")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--claude", "--force", "--home", home]), 0)
            self.assertEqual(installed.read_text(encoding="utf-8"), SKILL_PATH.read_text(encoding="utf-8"))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(installer.main([]), 1)


class ExampleScriptTests(unittest.TestCase):
    def test_examples_compile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for name in EXAMPLE_SCRIPTS:
                with self.subTest(script=name):
                    py_compile.compile(str(EXAMPLES_DIR / name), cfile=str(Path(tmp) / f"{name}c"), doraise=True)

    def test_examples_expose_mode_headless_and_output_dir_options(self) -> None:
        for name in EXAMPLE_SCRIPTS:
            with self.subTest(script=name):
                tree = ast.parse((EXAMPLES_DIR / name).read_text(encoding="utf-8"))
                options: dict[str, ast.Call] = {}
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "add_argument"
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                    ):
                        options[str(node.args[0].value)] = node
                for flag in ("--mode", "--headless", "--no-headless", "--output-dir"):
                    self.assertIn(flag, options)
                keywords = {kw.arg: kw.value for kw in options["--mode"].keywords}
                self.assertEqual(ast.literal_eval(keywords["choices"]), ("auto", "attach", "private"))
                self.assertEqual(ast.literal_eval(keywords["default"]), "private")

    def test_examples_use_only_the_client_and_the_standard_library(self) -> None:
        allowed_project = {"ea_node_editor.automation.client", "ea_node_editor.automation.errors"}
        stdlib = set(sys.stdlib_module_names) | {"__future__"}
        for name in EXAMPLE_SCRIPTS:
            with self.subTest(script=name):
                tree = ast.parse((EXAMPLES_DIR / name).read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    modules: list[str] = []
                    if isinstance(node, ast.Import):
                        modules = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        modules = [node.module]
                    for module in modules:
                        self.assertTrue(
                            module in allowed_project or module.split(".", 1)[0] in stdlib,
                            f"{name} imports {module}",
                        )

    def test_examples_launch_through_the_client_context_manager(self) -> None:
        for name in EXAMPLE_SCRIPTS:
            with self.subTest(script=name):
                text = (EXAMPLES_DIR / name).read_text(encoding="utf-8")
                self.assertIn("with CorexClient.launch(", text)
                self.assertIn("return 1", text)


@unittest.skipUnless(shutil.which("git"), "git is required to check ignore rules")
class TrackedLocationTests(unittest.TestCase):
    def test_skill_source_is_not_gitignored(self) -> None:
        completed = subprocess.run(
            ["git", "check-ignore", "-q", str(SKILL_PATH.relative_to(REPO_ROOT).as_posix())],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 1, "docs/automation/skills/corex-automation/SKILL.md must stay trackable")


if __name__ == "__main__":
    unittest.main()
