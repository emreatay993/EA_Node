from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ea_node_editor.common import build_info
from scripts.resolve_build_id import resolve_build_id


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("Git is required for provenance integration tests")
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "Initial"],
        check=True, capture_output=True,
    )
    return root


def test_source_identity_and_local_resolution(repo):
    info = build_info.source_build_info(repo)
    assert info.revision == 1
    assert info.dirty is False
    assert info.build_id.startswith("CX-1-")
    assert info.commit[:12] not in info.label
    assert resolve_build_id(repo, info.build_id) == [info.commit]
    (repo / "uncommitted.py").write_text("# pending change\n")
    dirty = build_info.source_build_info(repo)
    assert dirty.build_id == info.build_id
    assert dirty.label.endswith(" · dirty")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    assert build_info.source_build_info(repo).dirty is True


def test_shallow_history_omits_misleading_count(repo, tmp_path):
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "--depth=1", repo.as_uri(), str(clone)], check=True, capture_output=True)
    info = build_info.source_build_info(clone)
    assert info.revision is None
    assert resolve_build_id(repo, info.build_id) == [info.commit]


def test_worktree_identity(repo, tmp_path):
    worktree = tmp_path / "worktree"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree)],
                   check=True, capture_output=True)
    assert (worktree / ".git").is_file()
    assert build_info.source_build_info(worktree) == build_info.source_build_info(repo)


def test_source_launch_captures_its_own_checkout_once(repo, monkeypatch):
    monkeypatch.setattr(build_info.sys, "frozen", False, raising=False)
    monkeypatch.setattr(build_info, "__file__", str(repo / "ea_node_editor" / "common" / "build_info.py"))
    build_info.get_build_info.cache_clear()
    try:
        original = build_info.get_build_info()
        assert original.commit == build_info.source_build_info(repo).commit
        (repo / "edited_after_launch.py").write_text("# pending")
        assert build_info.get_build_info().dirty is False
        build_info.get_build_info.cache_clear()  # A fresh process sees the new checkout state.
        assert build_info.get_build_info().dirty is True
    finally:
        build_info.get_build_info.cache_clear()


def test_missing_git_does_not_break_source_startup(repo, monkeypatch):
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("git")
    monkeypatch.setattr(build_info.subprocess, "run", unavailable)
    assert build_info.source_build_info(repo).label.endswith("commit unknown")
    with pytest.raises(RuntimeError, match="Cannot identify"):
        build_info.write_build_info(repo, repo / "stamp.json", "base")


def test_non_checkout_does_not_inherit_parent_git(repo):
    nested = repo / "unpacked"
    nested.mkdir()
    assert build_info.source_build_info(nested).commit is None


def test_packaged_identity_survives_source_changes_without_git(repo, tmp_path, monkeypatch):
    package = tmp_path / "bundle" / "ea_node_editor"
    stamp = build_info.write_build_info(repo, package / "build_info.json", "base")
    payload = json.loads(stamp.read_text())
    assert payload["profile"] == "base"
    assert payload["built_at"].endswith("+00:00")
    (repo / "later.py").write_text("# after build")
    monkeypatch.setattr(build_info.sys, "frozen", True, raising=False)
    monkeypatch.setattr(build_info, "__file__", str(package / "common" / "build_info.py"))
    def forbidden(*args, **kwargs):
        pytest.fail("Frozen runtime must never query Git")
    monkeypatch.setattr(build_info.subprocess, "run", forbidden)
    build_info.get_build_info.cache_clear()
    try:
        info = build_info.get_build_info()
        assert info.commit == payload["commit"]
        assert info.dirty is False
    finally:
        build_info.get_build_info.cache_clear()


def test_frozen_missing_stamp_does_not_query_git(tmp_path, monkeypatch):
    monkeypatch.setattr(build_info.sys, "frozen", True, raising=False)
    monkeypatch.setattr(build_info, "__file__", str(tmp_path / "common" / "build_info.py"))
    monkeypatch.setattr(build_info, "source_build_info", lambda _: pytest.fail("Unexpected source fallback"))
    build_info.get_build_info.cache_clear()
    try:
        assert build_info.get_build_info().commit is None
    finally:
        build_info.get_build_info.cache_clear()


def test_pyinstaller_stamp_is_created_and_collected(repo, tmp_path):
    spec = Path(__file__).resolve().parents[1] / "ea_node_editor.spec"
    tree = ast.parse(spec.read_text(encoding="utf-8"))
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                   and isinstance(node.targets[0], ast.Name)
                   and node.targets[0].id in {"build_info_path", "datas"}]
    namespace = dict(PROJECT_ROOT=repo, WORKPATH=str(tmp_path / "build"), Path=Path,
                     write_build_info=build_info.write_build_info, _package_profile=lambda: "base")
    exec(compile(ast.Module(body=assignments[:2], type_ignores=[]), str(spec), "exec"), namespace)
    stamp = tmp_path / "build" / "build_info.json"
    assert namespace["datas"] == [(str(stamp), "ea_node_editor")]
    assert json.loads(stamp.read_text())["commit"] == build_info.source_build_info(repo).commit
