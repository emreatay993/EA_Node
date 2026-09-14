# Purpose: Prove detached requests, bounded compilation and cancellable preparation.
# Map: subsystems/execution.md
# Tests: this file
from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from ea_node_editor.execution.compiled_snapshot_cache import CompiledSnapshotCache
from ea_node_editor.execution.request_capture import CapturedExecutionRequest
from ea_node_editor.execution.runtime import CorexRuntime
from ea_node_editor.execution.runtime_requests import ExecutionRequest
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.execution.submission_service import SubmissionCancelled
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from tests.test_runtime import _PreparedClient


@pytest.fixture
def graph():
    registry = build_default_registry(include_public_plugins=False)
    model = GraphModel()
    wid = model.active_workspace.workspace_id
    node = model.validated_mutations(wid, registry).add_node(
        type_id="data.number_slider", title="Value", x=0, y=0, properties={"value": 1.0}
    )
    return registry, model, wid, node.node_id


def snapshot(registry, model, wid):
    return build_runtime_snapshot(model.project, workspace_id=wid, registry=registry)


def test_request_capture_has_no_mutable_aliases(graph):
    registry, model, wid, _node = graph
    original = snapshot(registry, model, wid)
    original.metadata["probe"] = {"items": [1]}
    trigger = {"probe": {"items": [2]}}
    captured = CapturedExecutionRequest(
        ExecutionRequest(runtime_snapshot=original, workspace_id=wid, trigger=trigger),
        catalog=registry.data_types,
    )
    original.metadata["probe"]["items"].append(3)
    trigger["probe"]["items"].append(4)
    first = captured.materialize(registry.data_types)
    assert first.runtime_snapshot.metadata["probe"] == {"items": [1]}
    assert first.trigger["probe"] == {"items": [2]}
    first.runtime_snapshot.metadata["probe"]["items"].append(5)
    first.trigger["probe"]["items"].append(6)
    assert captured.materialize(registry.data_types).trigger["probe"] == {"items": [2]}
    assert captured.materialize(registry.data_types).runtime_snapshot.metadata[
        "probe"
    ] == {"items": [1]}


def test_snapshot_projection_validates_its_owners_without_reparsing_children(graph):
    from ea_node_editor.execution.runtime_dto import RuntimeWorkspace
    from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot

    registry, model, wid, _node = graph
    original = snapshot(registry, model, wid)
    expected = original.to_document(catalog=registry.data_types)
    with patch.object(RuntimeSnapshot, "from_mapping", side_effect=AssertionError("snapshot reparse")), patch.object(
        RuntimeWorkspace, "from_mapping", side_effect=AssertionError("workspace reparse")
    ):
        assert original.to_document(catalog=registry.data_types) == expected
        original.workspaces[0].nodes[0].exposed_ports["value"] = "invalid"
        with pytest.raises(ValueError, match="boolean"):
            original.to_document(catalog=registry.data_types)
        original.workspaces[0].nodes[0].exposed_ports.clear()
        original.workspaces[0].document_fields["views"][0]["zoom"] = "invalid"
        with pytest.raises(ValueError):
            original.to_document(catalog=registry.data_types)
    invalid_raw = expected
    invalid_raw["workspaces"][0]["nodes"][0]["exposed_ports"] = {"value": "invalid"}
    with pytest.raises(ValueError, match="boolean"):
        RuntimeSnapshot.from_mapping(invalid_raw, catalog=registry.data_types)


def test_snapshot_projection_preserves_authored_numeric_representation(graph):
    registry, model, wid, _node = graph
    original = snapshot(registry, model, wid)
    original.workspaces[0].document_fields["views"][0]["zoom"] = 2
    projected = original.to_document(catalog=registry.data_types)
    zoom = projected["workspaces"][0]["document_fields"]["views"][0]["zoom"]
    assert type(zoom) is int
    assert zoom == 2


def test_compiled_cache_is_bounded_and_does_not_expose_its_workspace(graph):
    registry, model, wid, node = graph
    cache = CompiledSnapshotCache()
    original = snapshot(registry, model, wid)
    first = cache.get(original, workspace_id=wid, registry=registry)
    first.workspace.nodes[0].properties["value"] = 999
    with patch(
        "ea_node_editor.execution.compiled_snapshot_cache.compile_runtime_snapshot",
        side_effect=AssertionError("recompiled"),
    ):
        repeated = cache.get(original, workspace_id=wid, registry=registry)
        assert repeated.workspace.nodes[0].properties["value"] == 1.0
    for value in (2, 3, 4):
        model.validated_mutations(wid, registry).set_node_properties(
            node, {"value": value}
        )
        cache.get(snapshot(registry, model, wid), workspace_id=wid, registry=registry)
    assert cache.entry_count == 2
    assert cache.encoded_bytes <= 64 * 1024 * 1024
    cache.retire_workspace(wid)
    assert cache.entry_count == 0
    oversized = CompiledSnapshotCache(max_bytes=1)
    assert oversized.get(original, workspace_id=wid, registry=registry).workspace.nodes
    assert oversized.entry_count == 0


def test_compiled_cache_keys_full_authored_snapshot_and_registry_identity(graph):
    from ea_node_editor.execution import compiled_snapshot_cache as cache_module

    registry, model, wid, _node = graph
    cache = CompiledSnapshotCache()
    original = snapshot(registry, model, wid)
    with patch.object(
        cache_module,
        "compile_runtime_snapshot",
        wraps=cache_module.compile_runtime_snapshot,
    ) as compile_call:
        first = cache.get(original, workspace_id=wid, registry=registry)
        original.metadata["presentation_note"] = "changed"
        second = cache.get(original, workspace_id=wid, registry=registry)
        generation = registry.fork()
        generation.freeze()
        assert generation.contract_fingerprint() == registry.contract_fingerprint()
        third = cache.get(original, workspace_id=wid, registry=generation)
    assert compile_call.call_count == 3
    assert first.snapshot_fingerprint != second.snapshot_fingerprint
    assert second.snapshot_fingerprint == third.snapshot_fingerprint
    assert cache.entry_count == 2


def test_compiled_identity_is_deferred_shared_and_preserves_canonical_wire_bytes(graph):
    from ea_node_editor.execution import compiled_snapshot_cache as cache_module
    from ea_node_editor.execution.solution_identity import canonical_digest
    from ea_node_editor.runtime_contracts import Interval1D

    registry, model, wid, _node = graph
    original = snapshot(registry, model, wid)
    original.metadata["value_shapes"] = {"tuple": (1, 2.5), "range": Interval1D(2, 5)}
    expected = canonical_digest(original.to_document(catalog=registry.data_types))
    cache = CompiledSnapshotCache()
    with patch.object(cache_module, "canonical_digest", wraps=canonical_digest) as digest:
        first = cache.get(original, workspace_id=wid, registry=registry)
        second = cache.get(original, workspace_id=wid, registry=registry)
        digest.assert_not_called()
        assert first.snapshot_fingerprint == expected
        assert second.snapshot_fingerprint == expected
        digest.assert_called_once()


def test_retired_cache_does_not_accept_a_late_compilation(graph):
    from ea_node_editor.execution import compiled_snapshot_cache as cache_module

    registry, model, wid, _node = graph
    cache = CompiledSnapshotCache()
    original = snapshot(registry, model, wid)
    entered, release = threading.Event(), threading.Event()
    results = []
    compile_snapshot = cache_module.compile_runtime_snapshot

    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return compile_snapshot(*args, **kwargs)

    with patch.object(cache_module, "compile_runtime_snapshot", side_effect=blocked):
        worker = threading.Thread(
            target=lambda: results.append(
                cache.get(original, workspace_id=wid, registry=registry)
            )
        )
        worker.start()
        try:
            assert entered.wait(10)
            cache.retire_workspace(wid)
        finally:
            release.set()
            worker.join(10)
        assert not worker.is_alive()
    assert len(results) == 1 and results[0].workspace.nodes
    assert cache.entry_count == 0


def test_edit_invalidation_does_not_wait_for_background_preparation(graph):
    registry, model, wid, node = graph
    runtime = CorexRuntime(registry=registry, client=_PreparedClient())
    entered = threading.Event()
    release = threading.Event()
    invalidated = threading.Event()
    errors = []
    original_get = runtime._compiled_snapshots.get

    def blocked(*args, **kwargs):
        if threading.current_thread() is worker:
            entered.set()
            assert release.wait(10)
        return original_get(*args, **kwargs)

    def prepare():
        try:
            runtime.prepare_execution(
                ExecutionRequest(
                    runtime_snapshot=snapshot(registry, model, wid), workspace_id=wid
                )
            )
        except Exception as exc:
            errors.append(exc)

    with patch.object(runtime._compiled_snapshots, "get", side_effect=blocked):
        worker = threading.Thread(target=prepare)
        worker.start()
        assert entered.wait(10)
        model.validated_mutations(wid, registry).set_node_properties(node, {"value": 2})
        changed = snapshot(registry, model, wid)

        def invalidate():
            runtime.invalidate_solution(
                model.project.project_id, wid, changed, (node,), "property_changed"
            )
            invalidated.set()

        edit = threading.Thread(target=invalidate)
        edit.start()
        try:
            assert invalidated.wait(5), (
                "invalidation waited for preparation's lifecycle lock"
            )
        finally:
            release.set()
            worker.join(10)
            edit.join(10)
    assert len(errors) == 1 and "revision_changed" in str(errors[0])
    assert not runtime._solution_store._preparations
    runtime.shutdown()


def test_submission_admission_precedes_immediate_worker_events(graph):
    registry, model, wid, _node = graph
    client = _PreparedClient()
    runtime = CorexRuntime(registry=registry, client=client)
    events = []
    runtime.subscribe(events.append)
    try:
        handle = runtime.submit_execution(
            ExecutionRequest(
                runtime_snapshot=snapshot(registry, model, wid), workspace_id=wid
            )
        )
        run_id = handle.result(10)
        scoped = [event for event in events if event.get("run_id") == run_id]
        assert scoped[0]["type"] == "submission_admitted"
        assert scoped[0]["submission_id"] == handle.submission_id
        assert any(event["type"] == "run_preflight_accepted" for event in scoped[1:])
        assert handle.state == "dispatched"
    finally:
        runtime.shutdown()


def test_queued_submission_preserves_revision_at_handoff(graph):
    registry, model, wid, node = graph
    client = _PreparedClient()
    runtime = CorexRuntime(registry=registry, client=client)
    entered, release = threading.Event(), threading.Event()
    original_get = runtime._compiled_snapshots.get

    def blocked(*args, **kwargs):
        if threading.current_thread().name.startswith("corex-preparation"):
            entered.set()
            assert release.wait(10)
        return original_get(*args, **kwargs)

    try:
        with patch.object(runtime._compiled_snapshots, "get", side_effect=blocked):
            request = ExecutionRequest(
                runtime_snapshot=snapshot(registry, model, wid), workspace_id=wid
            )
            first = runtime.submit_execution(request)
            assert entered.wait(10)
            second = runtime.submit_execution(request)
            model.validated_mutations(wid, registry).set_node_properties(
                node, {"value": 2}
            )
            runtime.invalidate_solution(
                model.project.project_id,
                wid,
                snapshot(registry, model, wid),
                (node,),
                "property_changed",
            )
            first.cancel("superseded")
            release.set()
            for handle in (first, second):
                with pytest.raises(SubmissionCancelled):
                    handle.result(10)
            assert not client.commands
            assert runtime.solution_store.stats()["preparations"] == 0
    finally:
        release.set()
        runtime.shutdown()


@pytest.mark.parametrize("action", ["stop", "reset", "edit", "shutdown"])
def test_blocked_reservation_does_not_block_state_changes_or_start_late(graph, action):
    registry, model, wid, node = graph
    client = _PreparedClient()
    runtime = CorexRuntime(registry=registry, client=client)
    entered, release, changed = threading.Event(), threading.Event(), threading.Event()
    original_reserve = client.reserve_run

    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original_reserve(*args, **kwargs)

    try:
        with patch.object(client, "reserve_run", side_effect=blocked):
            handle = runtime.submit_execution(
                ExecutionRequest(
                    runtime_snapshot=snapshot(registry, model, wid), workspace_id=wid
                )
            )
            assert entered.wait(10)

            def change():
                if action == "stop":
                    handle.cancel()
                elif action == "reset":
                    runtime.reset_project_session("replacement")
                elif action == "shutdown":
                    runtime.shutdown(wait=False)
                else:
                    runtime.invalidate_solution(
                        model.project.project_id,
                        wid,
                        snapshot(registry, model, wid),
                        (node,),
                        "property_changed",
                    )
                changed.set()

            changer = threading.Thread(target=change)
            changer.start()
            try:
                assert changed.wait(5), "state change waited for worker reservation"
            finally:
                release.set()
                changer.join(10)
            with pytest.raises(SubmissionCancelled):
                handle.result(10)
            assert not client.commands
    finally:
        release.set()
        runtime.shutdown()
    assert not client.viewer_reservations
    assert runtime.solution_store.stats()["preparations"] == 0


def test_duplicate_dispatch_cannot_discard_claimed_preparation(graph):
    registry, model, wid, _node = graph
    client = _PreparedClient()
    runtime = CorexRuntime(registry=registry, client=client)
    prepared = runtime.prepare_execution(
        ExecutionRequest(
            runtime_snapshot=snapshot(registry, model, wid), workspace_id=wid
        )
    )
    entered, release = threading.Event(), threading.Event()
    results, errors = [], []
    original_reserve = client.reserve_run

    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original_reserve(*args, **kwargs)

    def dispatch():
        try:
            results.append(runtime.dispatch_prepared(prepared))
        except Exception as exc:
            errors.append(exc)

    try:
        with patch.object(client, "reserve_run", side_effect=blocked):
            worker = threading.Thread(target=dispatch)
            worker.start()
            assert entered.wait(10)
            with pytest.raises(ValueError, match="preparation_dispatching"):
                runtime.dispatch_prepared(prepared)
            runtime.discard_prepared(prepared)
            assert runtime.solution_store.stats()["preparations"] == 1
            release.set()
            worker.join(10)
            assert not worker.is_alive()
        assert not errors
        assert results == ["run_1"]
        assert len(client.commands) == 1
    finally:
        release.set()
        runtime.shutdown()


def test_stop_after_admission_is_sent_after_start_write(graph):
    registry, model, wid, _node = graph
    client = _PreparedClient()
    client.stop_run = lambda run_id: client.operations.append(f"stop:{run_id}")
    runtime = CorexRuntime(registry=registry, client=client)
    entered, release = threading.Event(), threading.Event()
    original_start = client.start_reserved_run

    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original_start(*args, **kwargs)

    try:
        with patch.object(client, "start_reserved_run", side_effect=blocked):
            handle = runtime.submit_execution(
                ExecutionRequest(
                    runtime_snapshot=snapshot(registry, model, wid), workspace_id=wid
                )
            )
            assert entered.wait(10)
            assert handle.state == "admitted"
            handle.cancel()
            assert "stop:run_1" not in client.operations
            release.set()
            assert handle.result(10) == "run_1"
        assert client.operations.index("start_reserved_run") < client.operations.index(
            "stop:run_1"
        )
    finally:
        release.set()
        runtime.shutdown()
