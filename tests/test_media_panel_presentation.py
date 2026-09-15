# Purpose: Prove canvas-only previous Plot previews never change source authority.
# Map: feature_routes/media_image_video_pdf_refocus.md
# Tests: tests/test_media_panel_presentation.py
from dataclasses import replace
from types import SimpleNamespace

import pytest

from ea_node_editor.runtime_contracts import PlotProvenance
from ea_node_editor.runtime_contracts.solution_records import SolutionFreshness
from ea_node_editor.ui.media_panel_presentation import MediaPanelPresentation
from ea_node_editor.ui.media_panel_source import resolve_media_panel_source
from tests.test_media_panel_source_resolution import (
    _node,
    _run_state,
    _value_result,
    _workspace,
)
from tests.test_plot_value import plot_value


@pytest.fixture
def preview(monkeypatch):
    monkeypatch.setattr(
        "ea_node_editor.ui.media_panel_source.image_value_preview_source",
        lambda _: "image://plot/old",
    )
    monkeypatch.setattr(
        "ea_node_editor.ui.media_panel_presentation.image_value_preview_source",
        lambda _: "image://plot/old",
    )
    node = _node()
    workspace = _workspace(node, connected=True)
    edge = workspace.edges["edge-1"]
    edge.edge_id = "edge-1"
    edge.source_node_id = "signal"
    edge.source_port_key = "image"
    workspace.nodes["signal"] = SimpleNamespace(node_id="signal", type_id="plot.signal")
    plot = replace(
        plot_value(), provenance=PlotProvenance(workspace.workspace_id, "signal", "run")
    )
    state = _run_state(result=_value_result(plot), state="completed")
    records = state.cached_node_output_records_by_workspace_id[workspace.workspace_id]
    records[node.node_id]["run-1"]["outputs_available"] = True
    records["signal"] = {
        "plot-record": {
            "record_id": "plot-record",
            "outputs_available": True,
            "outputs": {"image": _value_result(plot)},
        }
    }
    facts = state.node_solution_facts_by_workspace_id[workspace.workspace_id]
    facts["signal"] = replace(
        facts[node.node_id], node_id="signal", retained_record_id="plot-record"
    )
    presentation = MediaPanelPresentation()
    project = object()
    presentation.begin(project, workspace, state)

    def resolve():
        strict = resolve_media_panel_source(
            node=node, workspace=workspace, run_state=state
        )
        payload = presentation.project(
            node=node, workspace=workspace, run_state=state, resolution=strict
        )
        assert {
            key: payload[key] for key in strict.to_qml_payload()
        } == strict.to_qml_payload()
        return payload

    assert resolve()["state"] == "ready"
    for key, fact in list(facts.items()):
        facts[key] = replace(
            fact,
            freshness=SolutionFreshness.EXPIRED,
            expiration_reason_code="graph_changed",
            expiration_root_node_ids=("signal",),
        )
    return SimpleNamespace(**locals())


@pytest.mark.parametrize(
    "phase",
    [
        "manual",
        "stopped",
        "queued",
        "preparing",
        "running",
        "other_workspace",
        "unrelated_run",
        "unrelated_preparing",
    ],
)
def test_previous_pixels_are_separate_from_strict_current_authority(preview, phase):
    p = preview
    if phase == "queued":
        p.state.pending_auto_run_workspace_id = p.workspace.workspace_id
        p.state.pending_auto_run_target_node_ids = {"signal"}
    elif phase == "preparing":
        p.state.active_submission_id = "submission"
        p.state.active_submission_workspace_id = p.workspace.workspace_id
        p.state.active_execution_node_ids = {"signal", p.node.node_id}
    elif phase == "running":
        p.state.running_node_ids = {"signal"}
    elif phase == "other_workspace":
        p.state.active_run_id = "other"
        p.state.active_run_workspace_id = "other"
    elif phase in {"unrelated_run", "unrelated_preparing"}:
        kind = "run" if phase == "unrelated_run" else "submission"
        setattr(p.state, f"active_{kind}_id", "unrelated")
        setattr(p.state, f"active_{kind}_workspace_id", p.workspace.workspace_id)
        p.state.active_execution_node_ids = {"different-node"}
    payload = p.resolve()
    assert payload["state"] == "stale"
    assert payload["resolved_source_url"] == payload["preview_source_url"] == ""
    assert payload["media_kind"] == ""
    assert payload["previous_plot_preview"] == {
        "preview_source_url": "image://plot/old",
        "status": "updating"
        if phase in {"queued", "preparing", "running"}
        else "out_of_date",
    }


@pytest.mark.parametrize(
    "failure", ["failed", "blocked", "empty", "unavailable", "evicted"]
)
@pytest.mark.parametrize("node_key", ["media-1", "signal"])
def test_terminal_or_unavailable_output_clears_previous_preview(
    preview, failure, node_key
):
    p = preview
    if failure in {"failed", "blocked", "empty"}:
        setattr(p.state, failure + "_node_ids", {node_key})
    elif failure == "unavailable":
        for record in p.records[node_key].values():
            record["outputs_available"] = False
    else:
        p.records.pop(node_key)
    assert p.resolve()["previous_plot_preview"] == {}


@pytest.mark.parametrize(
    "change",
    [
        "rewire",
        "disconnect",
        "producer_deleted",
        "hidden",
        "project",
        "workspace",
        "superseded",
        "no_initial",
    ],
)
def test_previous_preview_requires_the_same_observed_source_lifetime(preview, change):
    p = preview
    if change == "rewire":
        p.edge.edge_id = "replacement-edge"
    elif change == "disconnect":
        p.workspace.edges.clear()
    elif change == "producer_deleted":
        p.workspace.nodes.pop("signal")
    elif change == "hidden":
        p.node.exposed_ports["source"] = False
    elif change == "project":
        p.presentation.begin(object(), p.workspace, p.state)
    elif change == "workspace":
        p.presentation.begin(p.project, SimpleNamespace(**vars(p.workspace)), p.state)
    elif change == "superseded":
        p.facts[p.node.node_id] = replace(
            p.facts[p.node.node_id], retained_record_id="missing"
        )
    else:
        p.presentation = MediaPanelPresentation()
        return_payload = p.presentation.project(
            node=p.node,
            workspace=p.workspace,
            run_state=p.state,
            resolution=resolve_media_panel_source(
                node=p.node, workspace=p.workspace, run_state=p.state
            ),
        )
        assert return_payload["previous_plot_preview"] == {}
        return
    assert p.resolve()["previous_plot_preview"] == {}


def test_changes_to_producer_inputs_preserve_previous_preview(preview):
    p = preview
    p.workspace.nodes["title"] = SimpleNamespace(node_id="title", type_id="data.panel")
    p.workspace.edges["title-wire"] = SimpleNamespace(
        edge_id="title-wire",
        enabled=True,
        source_node_id="title",
        source_port_key="output",
        target_node_id="signal",
        target_port_key="title",
    )
    assert p.resolve()["previous_plot_preview"]["status"] == "out_of_date"


def test_pass_through_source_binding_cannot_survive_rewiring(preview):
    p = preview
    p.workspace.nodes["forward"] = SimpleNamespace(
        node_id="forward", type_id="core.identity"
    )
    p.edge.source_node_id = "forward"
    p.workspace.edges["forward-edge"] = SimpleNamespace(
        edge_id="forward-edge",
        enabled=True,
        source_node_id="signal",
        source_port_key="image",
        target_node_id="forward",
        target_port_key="input",
    )
    p.records["forward"] = {
        "forward-record": {
            "record_id": "forward-record",
            "outputs_available": True,
            "outputs": {"output": _value_result(p.plot)},
        }
    }
    p.facts["forward"] = replace(
        p.facts[p.node.node_id], node_id="forward", retained_record_id="forward-record"
    )
    for key, fact in list(p.facts.items()):
        p.facts[key] = replace(
            fact,
            freshness=SolutionFreshness.CURRENT,
            expiration_reason_code="",
            expiration_root_node_ids=(),
        )
    assert p.resolve()["state"] == "ready"
    for key, fact in list(p.facts.items()):
        p.facts[key] = replace(
            fact,
            freshness=SolutionFreshness.EXPIRED,
            expiration_reason_code="graph_changed",
            expiration_root_node_ids=("signal",),
        )
    assert p.resolve()["previous_plot_preview"]
    p.workspace.edges["forward-edge"].source_port_key = "other_output"
    assert p.resolve()["previous_plot_preview"] == {}


def test_previous_preview_is_never_recovered_from_arbitrary_cache_history(preview):
    p = preview
    p.records[p.node.node_id]["old-history"] = p.records[p.node.node_id]["run-1"]
    p.records[p.node.node_id].pop("run-1")
    assert p.resolve()["previous_plot_preview"] == {}


def test_new_current_records_can_precede_the_running_visual_notification(preview):
    p = preview
    replacement = replace(p.plot, settings=replace(p.plot.settings, font_size=15))
    p.records[p.node.node_id]["run-1"]["outputs"]["_surface_source"] = _value_result(
        replacement
    )
    p.records["signal"]["plot-record"]["outputs"]["image"] = _value_result(replacement)
    for key, fact in list(p.facts.items()):
        p.facts[key] = replace(
            fact,
            freshness=SolutionFreshness.CURRENT,
            expiration_reason_code="",
            expiration_root_node_ids=(),
        )
    p.state.running_node_ids = {p.node.node_id}
    payload = p.resolve()
    assert payload["state"] == "running"
    assert payload["previous_plot_preview"]["status"] == "updating"
    assert payload["preview_source_url"] == ""


def test_a_different_expired_plot_does_not_rebind_previous_preview(preview):
    p = preview
    replacement = replace(p.plot, settings=replace(p.plot.settings, font_size=15))
    p.records[p.node.node_id]["run-1"]["outputs"]["_surface_source"] = _value_result(
        replacement
    )
    p.state.running_node_ids = {p.node.node_id}
    assert p.resolve()["previous_plot_preview"] == {}


@pytest.mark.parametrize("source_id", ["media-1", "signal"])
def test_new_current_fact_before_cache_arrival_keeps_only_bound_previous_preview(
    preview, source_id
):
    p = preview
    p.state.active_run_id = "new-run"
    p.state.active_run_workspace_id = p.workspace.workspace_id
    p.state.active_execution_node_ids = {p.node.node_id}
    p.facts[source_id] = replace(
        p.facts[source_id],
        freshness=SolutionFreshness.CURRENT,
        retained_record_id="not-arrived",
        expiration_reason_code="",
        expiration_root_node_ids=(),
    )
    payload = p.resolve()
    assert payload["state"] != "ready"
    assert payload["preview_source_url"] == ""
    assert payload["previous_plot_preview"]["status"] == "updating"
    p.state.active_run_id = ""
    p.state.active_execution_node_ids.clear()
    assert p.resolve()["previous_plot_preview"] == {}


@pytest.mark.parametrize("outcome", ["failed", "empty", "unavailable"])
def test_publication_gap_fallback_ends_when_terminal_record_arrives(preview, outcome):
    p = preview
    p.state.running_node_ids = {p.node.node_id}
    p.facts[p.node.node_id] = replace(
        p.facts[p.node.node_id],
        freshness=SolutionFreshness.CURRENT,
        retained_record_id="not-arrived",
        expiration_reason_code="",
        expiration_root_node_ids=(),
    )
    assert p.resolve()["previous_plot_preview"]["status"] == "updating"
    p.records[p.node.node_id]["not-arrived"] = {
        "record_id": "not-arrived",
        "outputs_available": outcome != "unavailable",
        "outputs": {},
    }
    assert p.resolve()["previous_plot_preview"] == {}
