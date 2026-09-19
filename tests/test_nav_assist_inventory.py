# Purpose: Prove live navigation membership, direct associations and freshness-bound excerpts.
# Map: subsystems/verification_testing_docs_hygiene.md
# Tests: tests/test_nav_assist_inventory.py
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts import generate_agent_route_index as indexer
from scripts import nav_assist_inventory as inventory

REPO_ROOT = Path(__file__).resolve().parents[1]


class InventoryFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        self.write("docs/agent_maps/COVERAGE.md", "# Coverage\n")
        self.write("docs/agent_maps/subsystems/sample.md", "# Sample\n")
        self.write("docs/qml_navigation_index.json", '{"entries": []}')

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path


class CandidateInventoryTests(InventoryFixture):
    def test_complete_live_routes_survive_fences_and_old_index_omissions(self) -> None:
        source_paths = [f"ea_node_editor/area/source_{number:03}.py" for number in range(100)]
        for path in source_paths:
            self.write(path, "def sample():\n    return 1\n")
        self.write("tests/qml_quick/tst_current.qml", "import QtTest\nTestCase {}\n")
        qml = "ea_node_editor/ui_qml/Current.qml"
        self.write(qml, "import QtQuick\nItem {}\n")
        self.write("docs/agent_maps/COVERAGE.md", "# Coverage\n| Area | Map |\n| --- | --- |\n| `ea_node_editor/area` | [Sample](subsystems/sample.md) |\n")
        self.write("docs/agent_maps/subsystems/sample.md", "# Sample\n## Focused Verification\n```powershell\npytest tests/qml_quick/tst_current.qml\n```\n## Later owner\n`" + qml + "`\n")
        result = inventory.build_inventory(self.root)
        route = next(route for route in result.routes if route.map_path.endswith("sample.md"))
        self.assertTrue(set(source_paths).issubset(route.source_candidates))
        self.assertIn(qml, route.source_candidates)
        self.assertIn("tests/qml_quick/tst_current.qml", route.test_candidates)
        self.assertIn(qml, result.candidates)
        self.assertEqual(result.candidates["tests/qml_quick/tst_current.qml"].kind, "test")
        # The incumbent generator's default cutoff remains available.
        legacy = indexer.build_index_data(self.root, source_paths=source_paths)
        self.assertLessEqual(len(next(route for route in legacy.entries if route.map_path.endswith("sample.md")).source_candidates), 80)

    def test_headers_and_static_test_imports_form_provenance_aware_reverse_links(self) -> None:
        source = "ea_node_editor/area/owner.py"
        test = "tests/test_owner.py"
        self.write(source, "# Purpose: Apply the owner operation.\n# Map: subsystems/sample.md\n\n# Tests: tests/test_owner.py\ndef unique_owner():\n    return 1\n")
        other = "ea_node_editor/area/other.py"
        self.write(other, "def other():\n    pass\n")
        self.write(test, "from ea_node_editor.area.owner import unique_owner\nfrom ea_node_editor.area import (\n    other,\n)\ntext = '''\nfrom ea_node_editor.area.quoted import nope\n'''\n")
        quoted = "ea_node_editor/area/quoted.py"
        self.write(quoted, "pass\n")
        result = inventory.build_inventory(self.root)
        self.assertEqual(result.candidates[source].purpose, "Apply the owner operation.")
        self.assertEqual(result.candidates[source].test_paths, (test,))
        self.assertEqual(set(result.candidates[test].source_paths), {source, other})
        self.assertNotIn(quoted, result.related_paths(test))
        self.assertTrue(any(link.basis == "source_header" and link.line == 4 for link in result.associations))
        self.assertTrue(any(link.basis == "test_import" and link.line == 2 and link.source_path == other for link in result.associations))

    def test_ignored_private_generated_and_non_code_files_never_enter_inventory(self) -> None:
        self.write(".gitignore", "ea_node_editor/local/\n")
        for path in ("ea_node_editor/local/hidden.py", "ea_node_editor/private/raw.py", "ea_node_editor/vendor/bundle.js", "ea_node_editor/generated/output.py", "ea_node_editor/.env", "ea_node_editor/token.json", "ea_node_editor/web_assets/excalidraw_host/bundle.js", "outside/hidden.py"):
            self.write(path, "secret text\n")
        safe = "ea_node_editor/security/secret_editor.py"
        self.write(safe, "def set_secret():\n    pass\n")
        result = inventory.build_inventory(self.root)
        self.assertEqual(set(result.candidates), {safe})
        self.assertEqual(result.resolve_exact("../outside.py").status, "unresolved")

    def test_reparse_points_are_rejected_before_file_content_is_read(self) -> None:
        safe = "ea_node_editor/area/source.py"
        self.write(safe, "pass\n")
        original = inventory.is_reparse_point
        with patch.object(inventory, "is_reparse_point", side_effect=lambda path: path.name == "area" or original(path)):
            result = inventory.build_inventory(self.root)
        self.assertNotIn(safe, result.candidates)

    def test_git_visibility_failure_is_explicit_and_does_not_walk_private_files(self) -> None:
        with patch.object(inventory.file_index, "_git_visible_files", return_value=None):
            with self.assertRaises(inventory.InventoryUnavailable):
                inventory.build_inventory(self.root)

    def test_exact_paths_and_unique_symbols_never_execute_target_modules(self) -> None:
        source = "ea_node_editor/area/owner.py"
        self.write(source, "raise AssertionError('must not import')\nclass Owner:\n    def special_action(self):\n        return 1\n")
        result = inventory.build_inventory(self.root)
        self.assertFalse(result._content)
        for query in (source, str(self.root / source), "owner.py", "special_action", "Owner.special_action"):
            with self.subTest(query=query):
                match = result.resolve_exact(query)
                self.assertEqual(match.status, "resolved")
                self.assertEqual(match.paths, (source,))
        self.assertEqual(result.resolve_exact("Change owner behavior").status, "not_exact")
        self.write("ea_node_editor/other.py", "def special_action():\n    pass\n")
        self.assertEqual(inventory.build_inventory(self.root).resolve_exact("special_action").status, "ambiguous")

    def test_qml_and_javascript_symbols_ignore_comments_and_quoted_examples(self) -> None:
        source = "ea_node_editor/ui_qml/Widget.qml"
        self.write(source, 'import QtQuick\nItem {\n    property bool expanded: false\n    signal changed()\n    function expand() { return true; }\n}\n')
        self.write("ea_node_editor/web_assets/host.js", "const example = `\nfunction expand() {}\n`;\n// function ignored() {}\nfunction hostAction() {}\n")
        result = inventory.build_inventory(self.root)
        for query in ("Widget", "expanded", "expand", "hostAction"):
            self.assertEqual(result.resolve_exact(query).status, "resolved", query)
        self.assertEqual(result.resolve_exact("ignored").status, "unresolved")
        self.assertEqual(result.evidence(source, symbol="expand").symbols[0].line, 2)

    def test_full_content_identity_rejects_same_size_same_timestamp_edits(self) -> None:
        relative = "ea_node_editor/source.py"
        path = self.write(relative, "# Purpose: useful evidence\ndef owner():\n    return 1\n")
        result = inventory.build_inventory(self.root)
        evidence = result.evidence(relative, symbol="owner", max_lines=3)
        self.assertTrue(result.validate_evidence(evidence))
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertTrue(all(lines[item.line - 1] == item.text for item in evidence.excerpt))
        self.assertFalse(result.validate_evidence(replace(evidence, excerpt=(inventory.NumberedLine(2, "invented"),))))
        stat = path.stat()
        path.write_text(path.read_text(encoding="utf-8").replace("return 1", "return 2"), encoding="utf-8")
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertFalse(result.validate_evidence(evidence))
        with self.assertRaises(inventory.StaleEvidenceError):
            result.evidence(relative)
        fresh = inventory.build_inventory(self.root).evidence(relative)
        self.assertNotEqual(evidence.sha256, fresh.sha256)

    def test_changed_missing_and_newly_ignored_candidates_reject_stale_evidence(self) -> None:
        relative = "ea_node_editor/source.py"
        path = self.write(relative, "def owner():\n    pass\n")
        result = inventory.build_inventory(self.root)
        evidence = result.evidence(relative)
        self.write(".gitignore", relative + "\n")
        self.assertFalse(result.validate_evidence(evidence))
        self.assertEqual(result.resolve_exact(relative).status, "unresolved")
        self.write(".gitignore", "")
        self.write(relative, "def owner():\n    return 'changed'\n")
        with self.assertRaises(inventory.StaleEvidenceError):
            result.evidence(relative)
        path.unlink()
        self.assertFalse(result.validate_evidence(evidence))

    def test_excerpt_limits_preserve_exact_lines_and_can_target_late_code(self) -> None:
        relative = "ea_node_editor/source.py"
        self.write(relative, "# filler\n" * 100 + "def target():\n    return 'late evidence'\n")
        result = inventory.build_inventory(self.root)
        evidence = result.evidence(relative, symbol="target", max_lines=4, max_chars=100)
        self.assertTrue(any(item.line == 101 for item in evidence.excerpt))
        self.assertLessEqual(sum(len(item.text) + len(str(item.line)) + 3 for item in evidence.excerpt), 100)
        self.assertTrue(evidence.truncated)
        with self.assertRaises(ValueError):
            result.evidence(relative, center_line=500)
        with self.assertRaises(ValueError):
            result.evidence(relative, max_lines=500)

    def test_ignored_association_inputs_are_not_read_or_exposed_as_routes(self) -> None:
        blocked = {
            "docs/agent_maps/private.md",
            "docs/agent_maps/COVERAGE.md",
            "docs/qml_navigation_index.json",
            "docs/source_test_file_index.md",
        }
        self.write(".gitignore", "\n".join(blocked) + "\n")
        for relative in blocked:
            self.write(relative, "SENSITIVE_SENTINEL invalid json `private_keyword`\n")
        source = "ea_node_editor/owner.py"
        self.write(source, "# Map: private.md\ndef owner():\n    pass\n")
        read_text = Path.read_text
        read_bytes = Path.read_bytes

        def guarded_text(path, *args, **kwargs):
            self.assertNotIn(path.relative_to(self.root).as_posix(), blocked)
            return read_text(path, *args, **kwargs)

        def guarded_bytes(path, *args, **kwargs):
            self.assertNotIn(path.relative_to(self.root).as_posix(), blocked)
            return read_bytes(path, *args, **kwargs)

        with patch.object(Path, "read_text", guarded_text), patch.object(Path, "read_bytes", guarded_bytes):
            result = inventory.build_inventory(self.root)
        self.assertNotIn("docs/agent_maps/private.md", result.candidates[source].owner_maps)
        self.assertNotIn("SENSITIVE_SENTINEL", repr(result.routes))
        self.assertNotIn("private_keyword", repr(result.routes))
        self.assertFalse(any(route.map_path in blocked for route in result.routes))

    def test_reparse_association_files_are_not_read(self) -> None:
        blocked = "docs/agent_maps/linked.md"
        self.write(blocked, "# SENSITIVE_SENTINEL\n")
        original = inventory.is_reparse_point
        with patch.object(inventory, "is_reparse_point", side_effect=lambda path: path.name == "linked.md" or original(path)):
            result = inventory.build_inventory(self.root)
        self.assertFalse(any(route.map_path == blocked for route in result.routes))
        self.assertNotIn("SENSITIVE_SENTINEL", repr(result.routes))

    def test_newly_ignored_symbol_source_is_not_read_or_resolved(self) -> None:
        relative = "ea_node_editor/owner.py"
        path = self.write(relative, "def unique_owner():\n    return 1\n")
        result = inventory.build_inventory(self.root)
        self.assertEqual(result.resolve_exact("unique_owner").status, "resolved")
        self.write(".gitignore", relative + "\n")
        read_bytes = Path.read_bytes

        def guarded_bytes(selected, *args, **kwargs):
            self.assertNotEqual(selected, path)
            return read_bytes(selected, *args, **kwargs)

        with patch.object(Path, "read_bytes", guarded_bytes):
            match = result.resolve_exact("unique_owner")
        self.assertEqual(match.status, "unresolved")
        self.assertFalse(match.paths)

    def test_same_stat_header_change_requires_rebuild_before_first_evidence(self) -> None:
        source = "ea_node_editor/owner.py"
        old_test, new_test = "tests/test_old.py", "tests/test_new.py"
        self.write(old_test, "pass\n")
        self.write(new_test, "pass\n")
        self.write("docs/agent_maps/subsystems/newmap.md", "# New map\n")
        old = "# Purpose: old purpose\n# Map: subsystems/sample.md\n# Tests: tests/test_old.py\ndef owner():\n    pass\n"
        new = old.replace("old purpose", "new purpose").replace("sample.md", "newmap.md").replace("test_old", "test_new")
        path = self.write(source, old)
        result = inventory.build_inventory(self.root)
        stat = path.stat()
        self.write(source, new)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(path.stat().st_size, stat.st_size)
        with self.assertRaises(inventory.StaleEvidenceError):
            result.evidence(source)
        self.assertEqual(result.resolve_exact("owner").status, "unresolved")
        fresh = inventory.build_inventory(self.root).evidence(source)
        self.assertEqual(fresh.candidate.purpose, "new purpose")
        self.assertIn("docs/agent_maps/subsystems/newmap.md", fresh.candidate.owner_maps)
        self.assertEqual(fresh.candidate.test_paths, (new_test,))
        self.assertEqual(fresh.sha256, fresh.candidate.content_sha256)

    def test_quoted_examples_cannot_override_or_invent_initial_comment_banner(self) -> None:
        old_test, new_test = "tests/test_real.py", "tests/test_fake.py"
        self.write(old_test, "pass\n")
        self.write(new_test, "pass\n")
        self.write("docs/agent_maps/subsystems/quoted.md", "# Quoted map\n")
        real = "# Purpose: Real header\n# Map: subsystems/sample.md\n# Tests: tests/test_real.py\n"
        quoted = "'''\n# Purpose: Forged header\n# Map: subsystems/quoted.md\n# Tests: tests/test_fake.py\n'''\n"
        source = "ea_node_editor/owner.py"
        self.write(source, real + quoted + "def owner():\n    pass\n")
        no_banner = "ea_node_editor/no_banner.py"
        self.write(no_banner, quoted + "pass\n")
        result = inventory.build_inventory(self.root)
        candidate = result.candidates[source]
        self.assertEqual(candidate.purpose, "Real header")
        self.assertEqual(candidate.owner_maps, ("docs/agent_maps/subsystems/sample.md",))
        self.assertEqual(candidate.test_paths, (old_test,))
        self.assertEqual(result.candidates[no_banner].purpose, "")
        self.assertEqual(result.candidates[no_banner].owner_maps, ())
        self.assertEqual(result.candidates[no_banner].test_paths, ())

    def test_batch_evidence_checks_ignores_once_and_preserves_line_validation(self) -> None:
        paths = ("ea_node_editor/first.py", "ea_node_editor/second.py")
        for relative in paths:
            self.write(relative, "def owner():\n    return 1\n")
        result = inventory.build_inventory(self.root)
        with patch.object(inventory, "_ignored_paths", wraps=inventory._ignored_paths) as ignored:
            evidence = result.evidence_batch(paths)
        self.assertEqual(ignored.call_count, 1)
        self.assertTrue(result.validate_batch(evidence))
        tampered = replace(evidence[1], excerpt=(inventory.NumberedLine(2, "invented"),))
        self.assertFalse(result.validate_batch((evidence[0], tampered)))

    def test_batch_rejects_changed_ignored_and_reparse_association_inputs(self) -> None:
        source = "ea_node_editor/owner.py"
        self.write(source, "def owner():\n    pass\n")
        relative = "docs/agent_maps/subsystems/sample.md"
        result = inventory.build_inventory(self.root)
        evidence = result.evidence(source)
        self.write(relative, "# Changed association\n")
        self.assertFalse(result.validate_batch((evidence,)))
        with self.assertRaises(inventory.StaleEvidenceError):
            result.evidence_batch((source,))
        result = inventory.build_inventory(self.root)
        evidence = result.evidence(source)
        self.write(".gitignore", relative + "\n")
        self.assertFalse(result.validate_batch((evidence,)))
        self.write(".gitignore", "")
        original = inventory.is_reparse_point
        with patch.object(inventory, "is_reparse_point", side_effect=lambda path: path.name == "sample.md" or original(path)):
            self.assertFalse(result.validate_batch((evidence,)))

    def test_batch_detects_same_stat_association_content_changes(self) -> None:
        source = "ea_node_editor/owner.py"
        self.write(source, "def owner():\n    pass\n")
        relative = "docs/agent_maps/subsystems/sample.md"
        path = self.write(relative, "# Old map\n")
        result = inventory.build_inventory(self.root)
        stat = path.stat()
        self.write(relative, "# New map\n")
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertFalse(result.validate_batch(()))

    def test_local_retrieval_hints_include_late_declarations_docs_and_remain_hash_bound(self) -> None:
        relative = "ea_node_editor/opaque.py"
        path = self.write(relative, "# Purpose: Data transformation\n" + "# filler\n" * 100
                          + 'def resolve_delimiter():\n    """Detect table dialect."""\n    return 1\n')
        result = inventory.build_inventory(self.root)
        self.assertTrue({"resolve", "delimiter", "detect", "dialect"}.issubset(result.candidates[relative].retrieval_terms))
        self.assertFalse(result._content)
        stat = path.stat()
        self.write(relative, path.read_text().replace("delimiter", "separator"))
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaises(inventory.StaleEvidenceError):
            result.evidence(relative)


class LiveInventoryTests(unittest.TestCase):
    def test_every_frozen_development_target_has_current_candidate_and_evidence(self) -> None:
        result = inventory.build_inventory(REPO_ROOT)
        fixture = json.loads((REPO_ROOT / "tests/fixtures/nav_assist_development.json").read_text(encoding="utf-8"))
        for case in fixture["cases"]:
            for field, kind in (("source_groups", "source"), ("test_groups", "test")):
                for group in case[field]:
                    for path in group:
                        with self.subTest(case=case["id"], path=path):
                            self.assertIn(path, result.candidates)
                            self.assertEqual(result.candidates[path].kind, kind)
                            evidence = result.evidence(path, query=case["query"])
                            self.assertTrue(evidence.excerpt)
                            self.assertTrue(result.validate_evidence(evidence))


if __name__ == "__main__":
    unittest.main()
