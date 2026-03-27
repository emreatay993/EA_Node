from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_markdown_links.py"


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
