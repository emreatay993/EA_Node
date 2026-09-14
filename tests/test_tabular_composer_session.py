# Purpose: Prove isolated drafts, atomic apply, conflicts, virtual catalogues and late-result rejection.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_session.py
import copy
import time

import numpy as np
import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService
from ea_node_editor.ui.tabular_composer_session import TabularCatalogueModel, TabularComposerSession
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider


@pytest.fixture
def app():
    application = QApplication.instance() or QApplication([])
    yield application


def wait_for(app, predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while not predicate():
        app.processEvents()
        if time.monotonic() >= deadline:
            raise AssertionError("Composer operation did not finish")
        QTest.qWait(10)


@pytest.fixture
def composer(tmp_path, app):
    source = tmp_path / "source.npz"
    np.savez(source, values=np.arange(12).reshape(4, 3), labels=np.array(["A", "B", "C"]), time=np.arange(4))
    props = {"path": str(source), "data_view": {"version": 1, "mode": "source", "member": "values"}}
    changes = []
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    def apply(values):
        changes.append(copy.deepcopy(values))
        props.update(copy.deepcopy(values))
        session.observe(props)
        return True
    session = TabularComposerSession(read_properties=lambda: props, apply_properties=apply,
                                     project_context=lambda: (None, None),
                                     provider_factory=lambda **kw: TabularPreviewProvider(service_factory=lambda: loader, **kw))
    session.begin(props)
    wait_for(app, lambda: not session.state["busy"])
    assert session.state["valid"], session.state
    yield session, props, changes
    session.shutdown()


def definition():
    return {"version": 1, "mode": "table", "segments": [{"blocks": [{"member": "values", "labels_member": "labels"}],
                                                         "coordinate": {"member": "time", "name": "Time"}}]}


def test_draft_apply_is_one_mutation_and_unrelated_properties_do_not_conflict(composer, app):
    session, props, changes = composer
    before = copy.deepcopy(props)
    session.update_definition(definition())
    session.edit_property("data_view_name", "History")
    props["tabular_table_view_state"] = {"column_widths": {"A": 160}}
    session.observe(props)
    assert not session.state["conflict"]
    assert props["data_view"] == before["data_view"]
    wait_for(app, lambda: not session.state["busy"])
    assert session.apply()
    assert len(changes) == 1
    assert set(changes[0]) == {"data_view", "data_view_name"}
    assert props["data_view"] == definition()
    assert not session.state["dirty"]


def test_conflict_blocks_apply_until_explicit_reload(composer, app):
    session, props, changes = composer
    session.edit_property("data_view_name", "Draft")
    props["data_view_name"] = "Elsewhere"
    session.observe(props)
    assert session.state["conflict"] and not session.apply()
    assert not changes
    session.reload_current()
    wait_for(app, lambda: not session.state["busy"])
    assert session.state["draft"]["data_view_name"] == "Elsewhere"
    assert not session.state["dirty"]


def test_cancel_and_dirty_close_do_not_mutate_properties(composer):
    session, props, changes = composer
    session.edit_property("data_view_name", "Unapplied")
    closed = []
    session.close_ready.connect(lambda: closed.append(True))
    session.request_close()
    assert session.state["close_pending"] and not closed
    session.keep_editing()
    assert not session.state["close_pending"]
    session.discard()
    assert closed and not changes
    assert "data_view_name" not in props


def test_late_results_and_retired_sessions_cannot_replace_current_preview(composer, app):
    session, _, _ = composer
    old_generation = session._generation
    session.update_definition(definition())
    session._pending[str(old_generation)] = {"preview": {"state": "ready", "message": "stale"}}
    session._finished(str(old_generation), "")
    assert session.state["preview"].get("message") != "stale"
    wait_for(app, lambda: not session.state["busy"])
    assert session.state["preview"]["preview_kind"] == "table"
    session.retire()
    assert not session.active and not session.apply()


def test_preview_requests_do_not_modify_draft_output(composer, app):
    session, props, changes = composer
    before = copy.deepcopy(session.state["draft"])
    session.request_preview({"row_offset": 2, "row_limit": 1, "column_offset": 1, "column_limit": 1})
    wait_for(app, lambda: not session.state["busy"])
    assert session.state["draft"] == before
    assert not changes and not session.state["dirty"]


def test_catalogue_does_not_truncate_and_preserves_case_sensitive_identity(app):
    model = TabularCatalogueModel()
    model.replace([{"object_id": f"Array{i}", "display_name": f"Array{i}", "kind": "array", "shape": [5, 2]}
                   for i in range(1328)])
    assert model.rowCount() == 1328
    model.search("Array1327")
    assert model.rowCount() == 1
    model.search("")
    assert model.rowCount() == 1328


def test_composer_apply_uses_real_graph_one_step_undo_redo(tmp_path, app):
    from ea_node_editor.graph.model import GraphModel
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

    source = tmp_path / "data.csv"
    source.write_text("Time,Value\n0,20\n1,21\n", encoding="utf-8")
    model = GraphModel()
    registry = build_default_registry()
    workspace = model.active_workspace
    scene = GraphSceneBridge()
    scene.set_workspace(model, registry, workspace.workspace_id)
    node_id = scene.add_node_from_type("tabular.input", 0, 0)
    scene.set_node_properties(node_id, {"path": str(source)})
    history = RuntimeGraphHistory()
    scene.bind_runtime_history(history)
    before = copy.deepcopy(workspace.nodes[node_id].properties)
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    session = TabularComposerSession(read_properties=lambda: workspace.nodes[node_id].properties,
                                     apply_properties=lambda values: scene.set_node_properties(node_id, values),
                                     project_context=lambda: (None, None),
                                     provider_factory=lambda **kw: TabularPreviewProvider(service_factory=lambda: loader, **kw))
    try:
        session.begin(before)
        wait_for(app, lambda: not session.state["busy"])
        session.update_definition({"version": 1, "mode": "source", "output": {"columns": ["Value"]}})
        session.edit_property("data_view_name", "Selected value")
        wait_for(app, lambda: not session.state["busy"])
        assert session.apply(), session.state
        assert history.undo_depth(workspace.workspace_id) == 1
        assert history.undo_workspace(workspace.workspace_id, workspace) is not None
        assert workspace.nodes[node_id].properties == before
        assert history.redo_workspace(workspace.workspace_id, workspace) is not None
        assert workspace.nodes[node_id].properties["data_view_name"] == "Selected value"
    finally:
        session.shutdown()


def test_raw_nd_plane_is_explicit_and_never_changes_output(tmp_path, app):
    source = tmp_path / "cube.npy"
    data = np.arange(4 * 5 * 6).reshape(4, 5, 6)
    np.save(source, data)
    props = {"path": str(source), "data_view": {"version": 1, "mode": "array"}}
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    session = TabularComposerSession(read_properties=lambda: props, apply_properties=lambda values: True,
                                     project_context=lambda: (None, None),
                                     provider_factory=lambda **kw: TabularPreviewProvider(service_factory=lambda: loader, **kw))
    try:
        session.begin(props)
        wait_for(app, lambda: not session.state["busy"])
        assert session.state["preview"]["state"] == "array_axes_required"
        assert "slice_2d" not in session.state["preview"]
        session.set_preview_axes({"row": 2, "column": 0, "fixed": {"1": 3}})
        wait_for(app, lambda: not session.state["busy"])
        np.testing.assert_array_equal(session.state["preview"]["slice_2d"]["values"], data[:, 3, :].T)
        assert session.state["draft"]["data_view"] == props["data_view"]
        assert not session.dirty
    finally:
        session.shutdown()


def test_suggestions_only_fill_unambiguous_candidates(composer, app):
    session, _, _ = composer
    session.suggest_mapping()
    wait_for(app, lambda: not session.state["busy"])
    view = session.state["draft"]["data_view"]
    assert view["segments"][0]["blocks"][0]["labels_member"] == "labels"
    assert view["segments"][0]["coordinate"]["member"] == "time"
    assert session.dirty


def test_managed_copy_is_staged_only_on_apply_and_discarded_after_failed_commit(composer, app):
    session, props, _ = composer
    staged, discarded = [], []
    source = props["path"]
    session._stage_source = lambda path: staged.append(path) or "temp://new_composer_source"
    session._discard_source = lambda ref: discarded.append(ref)
    session.set_source(source, True)
    session.select_member("values")
    # set_source cleared the catalogue; use the canonical choice directly.
    session.update_definition({"version": 1, "mode": "source", "member": "values"})
    wait_for(app, lambda: not session.state["busy"])
    assert session.state["valid"]
    assert not staged
    session._apply_properties = lambda values: False
    assert not session.apply()
    assert staged == [source]
    assert discarded == ["temp://new_composer_source"]
    assert props["path"] == source


def test_mapping_change_resets_preview_page_and_search(composer, app):
    session, _, _ = composer
    session.request_preview({"row_offset": 2, "row_limit": 1, "column_offset": 0, "column_limit": 1, "search": "old"})
    wait_for(app, lambda: not session.state["busy"])
    session.update_definition(definition())
    wait_for(app, lambda: not session.state["busy"])
    assert session.state["preview_request"]["row_offset"] == 0
    assert "search" not in session.state["preview_request"]
    assert session.state["preview"]["window"]["row_offset"] == 0
