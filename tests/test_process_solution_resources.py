# Purpose: Prove process-owned solution handle transfer, cleanup and CAD CURRENT reads.
# Map: subsystems/execution.md
# Tests: this file
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import threading

import pytest

from ea_node_editor.execution.solution_resources import (
    ClientSolutionResources, SolutionResourceCommand, SolutionResourceOffer,
)
from ea_node_editor.execution.protocol_codec import command_to_dict, dict_to_command, dict_to_event, event_to_dict
from ea_node_editor.execution.run_messages import NodeSettledEvent
from ea_node_editor.execution.retained_resources import file_source_provenance_binding, validate_source_provenance_bindings
from ea_node_editor.execution.solution_identity import hash_file_provenance
from ea_node_editor.runtime_contracts import DataTree, ENGINEERING_SCENE_DATA_TYPE_ID
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.runtime_contracts.retained_resources import RetainedSourceBinding, RetainedResourceError
from tests.typed_handle_support import core_worker_services
from ea_node_editor.common.scene_protocol import COREX_SCENE_HANDLE_KIND


def _offer():
    services = core_worker_services()
    disposed = []
    ref = services.register_handle(object(), data_type_id=ENGINEERING_SCENE_DATA_TYPE_ID,
                                   kind=COREX_SCENE_HANDLE_KIND, run_id="run", dispose=lambda: disposed.append(True))
    outputs = {"scene": SettledPortResult(status="value", value=DataTree.from_list((ref, ref)))}
    offer = services.solution_resources.stage(outputs, run_id="run", workspace_id="ws", node_id="cad", generation=7)
    assert offer is not None
    return services, ref, outputs, offer, disposed


def test_offer_survives_run_cleanup_and_partial_claim_is_released_exactly_once():
    services, ref, _, offer, disposed = _offer()
    host = ClientSolutionResources(lambda command, generation: services.solution_resources.apply(command))
    services.cleanup_run("run")
    assert services.handle_registry.active_lease_count == 2
    with host.dispatch(offer, generation=7, run_id="run", workspace_id="ws", node_id="cad"):
        leased, token = host.claim("run", ref, 7)
        assert services.resolve_handle(leased) is not None
        assert host.claim("run", replace(ref, metadata={"forged": True}), 7) is None
        assert host.claim("run", ref, 6) is None
    services.solution_resources.retire_unclaimed("ws")
    assert services.handle_registry.active_lease_count == 1
    host.release(token)
    host.release(token)
    assert disposed == [True]
    assert services.handle_registry.active_handle_count == 0


@pytest.mark.parametrize("failure", [False, True])
def test_unclaimed_and_failed_callback_offers_are_cleaned(failure):
    services, ref, _, offer, disposed = _offer()
    host = ClientSolutionResources(lambda command, generation: services.solution_resources.apply(command))
    services.cleanup_run("run")
    try:
        with host.dispatch(offer, generation=7, run_id="run", workspace_id="ws", node_id="cad"):
            if failure:
                host.claim("run", ref, 7)
                raise RuntimeError("subscriber failed")
    except RuntimeError:
        pass
    assert disposed == [True]
    assert not services.solution_resources._offers


def test_replayed_offer_cannot_replace_live_claim_after_replay_window():
    services, ref, _, offer, _ = _offer()
    host = ClientSolutionResources(lambda command, generation: services.solution_resources.apply(command))
    with host.dispatch(offer, generation=7, run_id="run", workspace_id="ws", node_id="cad"):
        _, token = host.claim("run", ref, 7)
    host._sequence = 5000
    with host.dispatch(offer, generation=7, run_id="run", workspace_id="ws", node_id="cad"):
        assert host.claim("run", ref, 7) is None
    services.cleanup_run("run")
    host.release(token)
    with host.dispatch(offer, generation=7, run_id="run", workspace_id="ws", node_id="cad"):
        assert host.claim("run", ref, 7) is None
    assert not services.handle_registry.active_handle_count


def test_offer_protocol_roundtrip_and_strict_correlation():
    services, _, outputs, offer, _ = _offer()
    event = NodeSettledEvent(run_id="run", workspace_id="ws", node_id="cad", outputs=outputs, resource_offer=offer)
    assert dict_to_event(event_to_dict(event, catalog=services.data_types), catalog=services.data_types) == event
    command = SolutionResourceCommand.for_offer(offer, "settle", (0,))
    assert dict_to_command(command_to_dict(command)) == command
    for changed in (replace(command, generation=8), replace(command, workspace_id="other"),
                    replace(command, indices=(100,))):
        with pytest.raises(ValueError):
            services.solution_resources.apply(changed)
    bad = offer.to_payload(services.data_types)
    bad["handles"][0][1] = bad["handles"][0][0]
    with pytest.raises(ValueError):
        SolutionResourceOffer.from_payload(bad, services.data_types)
    services.reset()


def test_failed_delivery_notification_runs_outside_resource_lock():
    services, ref, _, offer, _ = _offer()
    notified = []
    host = None
    def fail_send(command, generation):
        raise OSError("closed queue")
    def notify(generation):
        thread = threading.Thread(target=host.reset)
        thread.start()
        thread.join(1)
        assert not thread.is_alive()
        notified.append(generation)
    host = ClientSolutionResources(fail_send, notify)
    with host.dispatch(offer, generation=7, run_id="run", workspace_id="ws", node_id="cad"):
        host.claim("run", ref, 7)
    assert notified == [7]
    services.reset()


@pytest.mark.parametrize("change", ["changed", "deleted"])
def test_file_provenance_binding_roundtrip_and_changes(tmp_path, change):
    path = tmp_path / "part.stl"
    path.write_bytes(b"original")
    binding = file_source_provenance_binding(path, hash_file_provenance(path))
    assert RetainedSourceBinding.from_payload(binding.to_payload()) == binding
    validate_source_provenance_bindings((binding,))
    with pytest.raises(ValueError):
        replace(binding, resolver_id="forged")
    if change == "changed":
        path.write_bytes(b"modified")
    else:
        path.unlink()
    with pytest.raises(RetainedResourceError):
        validate_source_provenance_bindings((binding,))


@pytest.mark.parametrize("connected", [False, True])
def test_real_process_cad_reuse_provenance_reset_and_restart(tmp_path, connected):
    import pyvista
    from ea_node_editor.execution.runtime import CorexRuntime
    from ea_node_editor.execution.runtime_requests import ExecutionRequest
    from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
    from ea_node_editor.graph.model import GraphModel
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from tests.test_runtime import _wait_for_backend_run_cleanup

    path = tmp_path / "part.stl"
    pyvista.Cube().triangulate().save(path)
    registry = build_default_registry(include_public_plugins=False)
    model = GraphModel()
    workspace = model.active_workspace
    wid = workspace.workspace_id
    source = model.add_node(wid, "data.panel", "Path", 0, 0,
                            properties={"value": str(path), "interpretation": "text"})
    cad = model.add_node(wid, "engineering.cad_import", "CAD", 200, 0,
                        properties={"length_unit": "mm", "path": "" if connected else str(path)})
    sink = model.add_node(wid, "data.panel", "Scene", 400, 0)
    if connected:
        model.add_edge(wid, source.node_id, "output", cad.node_id, "path")
    model.add_edge(wid, cad.node_id, "scene", sink.node_id, "input")
    runtime = CorexRuntime(registry=registry)
    events = []
    runtime.subscribe(events.append)
    def request(targets=(), *, force=False):
        from ea_node_editor.execution.prepared_execution import RecomputeMode
        return ExecutionRequest(runtime_snapshot=build_runtime_snapshot(model.project, workspace_id=wid, registry=registry),
                                workspace_id=wid, target_node_ids=targets,
                                recompute_mode=RecomputeMode.FORCE_RECOMPUTE if force else RecomputeMode.REUSE_VALID)
    def run(targets=(), *, force=False):
        start = len(events)
        runtime.run(request(targets, force=force), timeout=60)
        _wait_for_backend_run_cleanup(runtime)
        result = events[start:]
        assert not [item for item in result if item.get("type") in {"run_failed", "protocol_error"}], result
        return result
    try:
        first = run()
        cad_event = next(item for item in first if item.get("type") == "node_settled" and item.get("node_id") == cad.node_id)
        assert cad_event["accepted_solution_record"]
        if connected:
            assert cad_event["source_provenance_bindings"]
        assert runtime._client._process_client.solution_resources._offers, cad_event
        store = runtime.solution_store
        record = store.record(cad_event["record_id"])
        kwargs = dict(solution_key=record.solution_key, project_id=model.project.project_id,
                      workspace_id=wid, node_id=cad.node_id, runtime_generation=record.runtime_generation,
                      catalog=registry.data_types, port_keys=("scene",))
        entry = store._records[record.record_id]
        retained = entry.resource_leases
        entry.resource_leases = ()
        with pytest.raises(ValueError, match="no retained resource lease"):
            store.current_outputs(**kwargs)
        entry.resource_leases = retained
        with pytest.raises(ValueError, match="generation is stale"):
            store.current_outputs(**{**kwargs, "runtime_generation": record.runtime_generation + 1})
        assert store.current_outputs(**kwargs) is not None
        if not connected:
            general = run()
            reused = next(item for item in general if item.get("type") == "node_settled" and item.get("node_id") == cad.node_id)
            assert reused["disposition"] == "recomputed"
            assert reused["record_id"] != cad_event["record_id"]
            forced = run(force=True)
            assert not [item for item in forced if item.get("type") == "solution_nondeterminism"]
            assert next(item for item in forced if item.get("type") == "node_settled" and item.get("node_id") == cad.node_id)["accepted_solution_record"]
            assert retained[0].offer_id not in runtime._client._process_client.solution_resources._offers
        second = run((sink.node_id,))
        assert cad.node_id not in [item["node_id"] for item in second if item["type"] == "node_started"]
        assert not [item for item in second if item["type"] == "node_settled" and item.get("node_id") == cad.node_id]
        pyvista.Sphere().triangulate().save(path)
        changed = run((sink.node_id,))
        assert cad.node_id in [item["node_id"] for item in changed if item["type"] == "node_started"]
        client = runtime._client._process_client
        process = client._process
        old_generation = client._physical_generation_token
        process.terminate()
        process.join(5)
        client._check_worker_health(process, old_generation)
        restarted = run()
        assert client._physical_generation_token > old_generation
        restart_cad = next(item for item in restarted if item.get("type") == "node_settled" and item.get("node_id") == cad.node_id)
        assert restart_cad["accepted_solution_record"]
        after_restart = run((sink.node_id,))
        assert cad.node_id not in [item["node_id"] for item in after_restart if item["type"] == "node_started"]
        assert client.solution_resources._offers
        runtime.reset_project_session(model.project.project_id)
        runtime.retire_workspace(wid)  # ACK is a barrier after queued release commands.
        assert not client.solution_resources._offers
    finally:
        runtime.shutdown()


def _current_payload(services, ref):
    from ea_node_editor.execution.prepared_execution import AcceptedOutputPayload
    from ea_node_editor.runtime_contracts.settled_results import settled_outputs_to_payload
    from ea_node_editor.runtime_contracts.solution_records import SolutionResidency
    outputs = {"scene": SettledPortResult(status="value", value=DataTree.from_item(ref))}
    encoded = json.dumps(settled_outputs_to_payload(outputs, catalog=services.data_types),
                         sort_keys=True, separators=(",", ":")).encode()
    return AcceptedOutputPayload(node_id="cad", record_id="record", solution_key="a" * 64,
                                 settlement_status="completed", result_digest=hashlib.sha256(encoded).hexdigest(),
                                 residency=SolutionResidency.SESSION, runtime_generation=7,
                                 outputs=encoded, catalog=services.data_types)


def test_current_handle_requires_exact_accepted_worker_lease():
    from ea_node_editor.execution.prepared_execution import validate_current_output_payload
    services, ref, _, offer, _ = _offer()
    leased = offer.handles[0][1]
    validator = services.solution_resources.validate_retained
    def validate(value, *, owner=validator):
        validate_current_output_payload(_current_payload(services, value), catalog=services.data_types,
                                        port_keys=("scene",), handle_validator=owner)
    with pytest.raises(ValueError, match="session-only"):
        validate(leased, owner=None)
    with pytest.raises(ValueError, match="no accepted worker lease"):
        validate(leased)
    services.solution_resources.apply(SolutionResourceCommand.for_offer(offer, "settle", (0,)))
    services.cleanup_run("run")
    validate(leased)
    for forged in (replace(leased, worker_generation=2), replace(leased, metadata={"forged": True}),
                   replace(leased, owner_scope="other"), replace(leased, handle_id="missing")):
        with pytest.raises(ValueError, match="no accepted worker lease"):
            validate(forged)
    services.solution_resources.apply(SolutionResourceCommand.for_offer(offer, "release", (0,)))
    with pytest.raises(ValueError, match="no accepted worker lease"):
        validate(leased)


def test_stage_rollback_and_publication_failure_release_offers():
    from ea_node_editor.execution.worker_runner import RunEventPublisher
    services, ref, outputs, offer, disposed = _offer()
    services.solution_resources.apply(SolutionResourceCommand.for_offer(offer, "settle", ()))
    forged_outputs = {"scene": SettledPortResult(status="value", value=DataTree.from_list((ref, replace(ref, metadata={"bad": True}))))}
    assert services.solution_resources.stage(forged_outputs, run_id="run", workspace_id="ws", node_id="cad", generation=7) is None
    assert services.handle_registry.active_lease_count == 1
    class BrokenQueue:
        def put(self, payload):
            raise OSError("queue closed")
    services.solution_resource_offers_enabled = True
    publisher = RunEventPublisher(BrokenQueue(), run_id="run", workspace_id="ws",
                                   data_types=services.data_types, worker_services=services, dispatch_generation=7)
    with pytest.raises(OSError):
        publisher.emit_node_settled("cad", "completed", outputs)
    assert not services.solution_resources._offers
    services.cleanup_run("run")
    assert disposed == [True]


def test_aborting_transport_terminates_active_run_and_preserves_failure():
    from unittest.mock import Mock
    from ea_node_editor.execution.process_client import ProcessExecutionClient
    client = ProcessExecutionClient()
    process = Mock()
    events = []
    client.subscribe(events.append)
    try:
        client._process = process
        client._physical_generation_token = client._catalog_generation_token = client._accepted_physical_generation_token = 7
        client._active_run_id = "run"
        client._active_workspace_id = "ws"
        client._abort_solution_resource_transport(6)
        process.terminate.assert_not_called()
        assert client._active_run_id == "run"
        original = {"type": "run_failed", "run_id": "run", "workspace_id": "ws",
                    "error": "exact native error", "traceback": "original trace", "fatal": True}
        client._abort_solution_resource_transport(7, reason="worker_service_reset", failure_event=original)
        process.terminate.assert_called_once()
        assert client._active_run_id == ""
        assert client._accepted_physical_generation_token == -1
        assert original in events
        assert any(event.get("state") == "error" for event in events)
    finally:
        client._process = None
        client.shutdown()


def test_aborting_old_generation_does_not_retire_replacement_waiters():
    from unittest.mock import Mock
    from types import SimpleNamespace
    from ea_node_editor.execution.process_client import ProcessExecutionClient
    client = ProcessExecutionClient()
    process = Mock()
    replacement = threading.Event()
    old_waiter = threading.Event()
    client._workspace_retirement_waiters = {"old": (old_waiter, {})}
    try:
        client._process = process
        client._physical_generation_token = client._catalog_generation_token = client._accepted_physical_generation_token = 7
        def replace_process():
            with client._state_lock:
                client._physical_generation_token = client._catalog_generation_token = client._accepted_physical_generation_token = 8
                client._workspace_retirement_waiters["new"] = (replacement, {})
            with client._generation_readiness._lock:
                client._generation_readiness._current = SimpleNamespace(physical_generation=8)
                client._generation_readiness._phase = "ready"
        process.terminate.side_effect = replace_process
        client._abort_solution_resource_transport(7)
        assert old_waiter.is_set() and not replacement.is_set()
        assert client._generation_readiness._current.physical_generation == 8
        assert client._accepted_physical_generation_token == 8
    finally:
        client._process = None
        client.shutdown()


def test_unexpected_worker_reset_retires_process_loop(monkeypatch):
    import queue
    import ea_node_editor.execution.worker as worker
    from ea_node_editor.execution.run_messages import StartRunCommand
    services = core_worker_services()
    commands, events = queue.Queue(), queue.Queue()
    commands.put({"start": True})
    monkeypatch.setattr(worker, "decode_command_payload", lambda *args, **kwargs: StartRunCommand(run_id="run", workspace_id="ws"))
    def fail(*args, **kwargs):
        raise RuntimeError("native reset failure")
    monkeypatch.setattr(worker, "run_workflow", fail)
    worker.worker_main(commands, events, services)
    failure = events.get_nowait()
    assert failure["type"] == "run_failed" and failure["fatal"]
    assert failure["error"] == "native reset failure"
    assert services.worker_generation == 2


def test_property_file_change_between_preparation_and_execution_is_rejected(tmp_path):
    from types import SimpleNamespace
    from ea_node_editor.execution.worker_runner import NodeExecutor
    from ea_node_editor.execution.solution_identity import node_input_provenance_digest
    from ea_node_editor.nodes.bootstrap import build_default_registry
    path = tmp_path / "part.stl"
    path.write_bytes(b"old source")
    registry = build_default_registry(include_public_plugins=False)
    spec = registry.get_spec("engineering.cad_import")
    node = SimpleNamespace(type_id=spec.type_id, properties={"path": str(path)})
    plan = SimpleNamespace(nodes={"cad": node}, node_specs={"cad": spec}, incoming_edges_for=lambda *args: ())
    fingerprint = node_input_provenance_digest(plan=plan, node_id="cad",
                                               normalized_properties=registry.normalize_properties(spec.type_id, node.properties))
    executor = SimpleNamespace(_plan=plan, _registry=registry, _source_dependencies={},
                               _executing_source_provenance={}, source_provenance_by_node={"cad": fingerprint},
                               _artifact_service=SimpleNamespace(resolve_authored_path=lambda value: path))
    path.write_bytes(b"new source")
    with pytest.raises(RetainedResourceError, match="after execution preparation"):
        NodeExecutor._capture_declared_source_provenance(executor, "cad", None)


def test_installed_current_input_survives_accepted_owner_release_until_run_cleanup():
    from types import SimpleNamespace
    from ea_node_editor.execution.worker_runner import NodeExecutor
    services, _, _, offer, disposed = _offer()
    source = offer.handles[0][1]
    services.solution_resources.apply(SolutionResourceCommand.for_offer(offer, "settle", (0,)))
    services.cleanup_run("run")
    executor = NodeExecutor.__new__(NodeExecutor)
    executor._worker_services = services
    executor._data_types = services.data_types
    executor._control = SimpleNamespace(run_id="consume")
    executor._plan = SimpleNamespace(output_ports=lambda _: (
        SimpleNamespace(key="scene", kind="data", data_type=ENGINEERING_SCENE_DATA_TYPE_ID,
                        accepted_data_types=()),
    ))
    installed, original = executor.validate_reused_output(_current_payload(services, source), port_keys=("scene",))
    installed_ref = installed["scene"].value.branches[0][1][0]
    assert installed_ref.owner_scope == "run:consume"
    assert original["scene"].value.branches[0][1][0] == source
    services.solution_resources.apply(SolutionResourceCommand.for_offer(offer, "release", (0,)))
    with pytest.raises(LookupError):
        services.resolve_handle(source)
    assert services.resolve_handle(installed_ref) is not None
    assert not disposed
    services.cleanup_run("consume")
    assert disposed == [True]
    with pytest.raises(LookupError):
        services.resolve_handle(installed_ref)


def test_current_input_partial_install_failure_rolls_back_run_leases():
    from types import SimpleNamespace
    from ea_node_editor.execution.worker_runner import NodeExecutor
    services, _, _, offer, _ = _offer()
    source = offer.handles[0][1]
    services.solution_resources.apply(SolutionResourceCommand.for_offer(offer, "settle", (0,)))
    services.cleanup_run("run")
    executor = NodeExecutor.__new__(NodeExecutor)
    executor._worker_services = services
    executor._data_types = services.data_types
    executor._control = SimpleNamespace(run_id="consume")
    executor._plan = SimpleNamespace(output_ports=lambda _: (
        SimpleNamespace(key="scene", kind="data", data_type=ENGINEERING_SCENE_DATA_TYPE_ID,
                        accepted_data_types=()),
    ))
    payload = _current_payload(services, source)
    outputs = payload.decode_outputs(catalog=services.data_types)
    outputs["scene"] = replace(outputs["scene"], value=DataTree.from_list((source, replace(source, handle_id="missing"))))
    from ea_node_editor.runtime_contracts.settled_results import settled_outputs_to_payload
    encoded = json.dumps(settled_outputs_to_payload(outputs, catalog=services.data_types),
                         sort_keys=True, separators=(",", ":")).encode()
    payload = replace(payload, outputs=encoded, result_digest=hashlib.sha256(encoded).hexdigest(), catalog=services.data_types)
    with pytest.raises(LookupError):
        executor.validate_reused_output(payload, port_keys=("scene",))
    assert services.handle_registry.active_lease_count == 1
    services.reset()


@pytest.mark.parametrize("external", [False, True])
def test_managed_cad_current_consumption_and_external_execution(tmp_path, external):
    import shutil
    import sys
    from ea_node_editor.execution.runtime import CorexRuntime
    from ea_node_editor.execution.runtime_requests import ExecutionRequest
    from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.persistence.serializer import JsonProjectSerializer
    from tests.test_engineering_viewer_example_project import PROJECT_PATH, VIEWER_NODE_ID, CAD_REF
    from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
    from tests.test_runtime import _wait_for_backend_run_cleanup

    project_path = tmp_path / PROJECT_PATH.name
    shutil.copy2(PROJECT_PATH, project_path)
    shutil.copytree(PROJECT_PATH.with_suffix(".data"), project_path.with_suffix(".data"))
    registry = build_default_registry(include_public_plugins=False)
    project = JsonProjectSerializer(registry).load(str(project_path))
    workspace = project.workspaces[project.active_workspace_id]
    runtime = CorexRuntime(registry=registry)
    request = ExecutionRequest(
        project_path=project_path,
        runtime_snapshot=build_runtime_snapshot(project, workspace_id=workspace.workspace_id, registry=registry),
        workspace_id=workspace.workspace_id, target_node_ids=(VIEWER_NODE_ID,),
        execution_backend=({"requested_backend": "external_subprocess", "allow_external_subprocess": True,
                            "python_executable": sys.executable} if external else None),
    )
    try:
        first = runtime.run(request, timeout=60)
        _wait_for_backend_run_cleanup(runtime)
        assert first.status == "completed"
        assert not [event for event in first.events if event.get("type") == "node_settled" and event.get("status") in {"failed", "blocked"}]
        second = runtime.run(request, timeout=60)
        _wait_for_backend_run_cleanup(runtime)
        assert second.status == "completed"
        started = [event["node_id"] for event in second.events if event.get("type") == "node_started"]
        if external:
            assert all(event.get("resource_offer") is None for event in (*first.events, *second.events))
        else:
            assert "node_cad_import" not in started, started
            assert "node_fe_import" not in started, started
        store = ProjectArtifactStore.from_project_metadata(project_path=project_path, project_metadata=project.metadata)
        source = store.resolve_managed_path(CAD_REF)
        source.write_bytes(b"tampered managed CAD content")
        tampered = runtime.run(request, timeout=60)
        _wait_for_backend_run_cleanup(runtime)
        failure = next(event for event in tampered.events if event.get("type") == "node_settled" and event.get("node_id") == "node_cad_import")
        assert failure["status"] == "failed"
        assert "does not match" in failure["errors"][0]["error"]
    finally:
        runtime.shutdown()
