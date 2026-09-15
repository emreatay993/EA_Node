# Purpose: Prove source-backed current outputs cross real workers without rerunning producers.
# Map: subsystems/execution.md
# Tests: this file
from __future__ import annotations

from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import threading
from types import SimpleNamespace

import pytest

from ea_node_editor.execution.prepared_execution import (
    AcceptedOutputPayload,
    PreparedAction,
    RecomputeMode,
    validate_current_output_payload,
)
from ea_node_editor.execution.retained_resources import collect_retained_source_bindings
from ea_node_editor.execution.runtime import CorexRuntime
from ea_node_editor.execution.runtime_requests import ExecutionRequest
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.execution.worker_runner import NodeExecutor
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.runtime_contracts import ArrayDataRef, DataTree, TabularWindowRef
from ea_node_editor.runtime_contracts.settled_results import (
    SettledPortResult,
    settled_outputs_to_payload,
)
from ea_node_editor.runtime_contracts.solution_records import SolutionResidency
from tests.test_runtime import _PreparedClient, _wait_for_backend_run_cleanup
from tests.test_retained_resources import _table, _change_content
from tests.test_runtime_current_results import _settlement, _run_worker
from ea_node_editor.addons.tabular_data.loader_cache_service import (
    TabularLoaderCacheService,
    TabularLoadOptions,
)
from ea_node_editor.execution.worker_runtime import DEFAULT_RUNTIME_PREPARATION_CACHE


@pytest.mark.parametrize("action", ["invalidate", "reset"])
def test_source_validation_releases_lifecycle_lock_and_rejects_stale_settlement(
    tmp_path, monkeypatch, action
):
    import ea_node_editor.execution.runtime as runtime_module

    scene = _scene(tmp_path, client=_PreparedClient())
    entered = threading.Event()
    release = threading.Event()
    events = []
    scene.runtime.subscribe(events.append)
    original = runtime_module.validate_retained_source_bindings

    def blocked_validation(value, bindings, **kwargs):
        entered.set()
        assert release.wait(5), "test did not release source validation"
        return original(value, bindings, **kwargs)

    try:
        run_id = scene.runtime.dispatch_prepared(
            scene.runtime.prepare_execution(scene.request(scene.table.node_id))
        )
        decision = scene.client.commands[-1].node_decisions[0]
        loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
        ref = loader.open_source(
            scene.source, TabularLoadOptions(cache_policy="source_direct")
        )
        event = {
            **_settlement(scene.table.node_id, table_data=ref),
            "run_id": run_id,
            "workspace_id": scene.workspace.workspace_id,
            "solution_key": decision.solution_key,
            "decision_reason": decision.reason_code,
            "disposition": "recomputed",
            "retained_source_bindings": collect_retained_source_bindings(ref),
        }
        event["outputs"]["array_data"] = SettledPortResult(status="empty")
        monkeypatch.setattr(
            runtime_module, "validate_retained_source_bindings", blocked_validation
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            settlement = pool.submit(
                scene.runtime._handle_generation_event, event, scene.client.snapshot
            )
            try:
                assert entered.wait(5)
                operation = (
                    pool.submit(scene.invalidate, scene.table.node_id)
                    if action == "invalidate"
                    else pool.submit(
                        scene.runtime.reset_project_session,
                        scene.model.project.project_id,
                    )
                )
                operation.result(timeout=2)
            finally:
                release.set()
            settlement.result(timeout=5)
        settled = [item for item in events if item["type"] == "node_settled"]
        assert len(settled) == 1 and not settled[0]["accepted_solution_record"]
        assert not settled[0]["record_id"]
    finally:
        release.set()
        scene.runtime.shutdown()


def _scene(tmp_path, *, client=None):
    source = tmp_path / "signals.csv"
    source.write_text("time,value\n0,21\n1,22\n", encoding="utf-8")
    registry = build_default_registry(include_public_plugins=False)
    model = GraphModel()
    workspace = model.active_workspace
    table = model.add_node(
        workspace.workspace_id,
        "tabular.input",
        "Table",
        0,
        0,
        properties={"path": str(source), "cache_policy": "source_direct"},
    )
    title = model.add_node(
        workspace.workspace_id,
        "data.panel",
        "Title",
        0,
        200,
        properties={"value": "Original title", "interpretation": "text"},
    )
    plot = model.add_node(workspace.workspace_id, "plot.signal", "Plot", 300, 0)
    media = model.add_node(workspace.workspace_id, "media.panel", "Media", 600, 0)
    model.add_edge(
        workspace.workspace_id, table.node_id, "table_data", plot.node_id, "values"
    )
    title_edge = model.add_edge(
        workspace.workspace_id, title.node_id, "output", plot.node_id, "title"
    )
    model.add_edge(
        workspace.workspace_id, plot.node_id, "image", media.node_id, "source"
    )
    runtime = CorexRuntime(
        registry=registry, **({"client": client} if client is not None else {})
    )

    def request(*targets, force=False):
        return ExecutionRequest(
            runtime_snapshot=build_runtime_snapshot(
                model.project, workspace_id=workspace.workspace_id, registry=registry
            ),
            workspace_id=workspace.workspace_id,
            target_node_ids=targets,
            recompute_mode=RecomputeMode.FORCE_RECOMPUTE
            if force
            else RecomputeMode.REUSE_VALID,
        )

    def invalidate(*roots):
        return runtime.invalidate_solution(
            model.project.project_id,
            workspace.workspace_id,
            request().runtime_snapshot,
            roots,
            "graph_changed",
        )

    return SimpleNamespace(**locals())


def _facts(scene):
    return {
        fact.node_id: fact
        for fact in scene.runtime.solution_facts(
            scene.model.project.project_id, scene.workspace.workspace_id
        )
    }


def _materialized_scene(tmp_path, *, client=None):
    scene = _scene(tmp_path, client=client)
    wid = scene.workspace.workspace_id
    scene.path = scene.model.add_node(
        wid,
        "data.panel",
        "Path",
        -300,
        0,
        properties={"value": str(scene.source), "interpretation": "text"},
    )
    scene.filtered = scene.model.add_node(
        wid, "tabular.table_filter", "Filter", 200, 400
    )
    scene.materialized = scene.model.add_node(
        wid, "tabular.materialize_table_filter", "Rows", 400, 400
    )
    scene.consumer = scene.model.add_node(wid, "data.panel", "Consumer", 600, 400)
    scene.model.add_edge(wid, scene.path.node_id, "output", scene.table.node_id, "path")
    scene.model.add_edge(
        wid, scene.table.node_id, "table_data", scene.filtered.node_id, "table_data"
    )
    scene.model.add_edge(
        wid, scene.filtered.node_id, "window", scene.materialized.node_id, "window"
    )
    scene.model.add_edge(
        wid, scene.materialized.node_id, "rows", scene.consumer.node_id, "input"
    )
    return scene


def test_real_process_detached_current_result_keeps_source_provenance(tmp_path):
    scene = _materialized_scene(tmp_path)
    try:
        _assert_executed(
            scene.runtime.run(scene.request(scene.consumer.node_id), timeout=40),
            (
                scene.path,
                scene.table,
                scene.filtered,
                scene.materialized,
                scene.consumer,
            ),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        original = _facts(scene)[scene.materialized.node_id]
        prepared = scene.runtime.prepare_execution(
            scene.request(scene.consumer.node_id)
        )
        boundary = next(
            item
            for item in prepared.accepted_output_payloads
            if item.node_id == scene.materialized.node_id
        )
        assert not boundary.retained_source_bindings
        assert len(boundary.source_provenance_bindings) == 1
        assert boundary.source_provenance_complete
        _assert_executed(
            scene.runtime.run(scene.request(scene.consumer.node_id), timeout=40),
            (scene.consumer,),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        _change_content(scene.source)
        result = scene.runtime.run(scene.request(scene.consumer.node_id), timeout=40)
        _assert_executed(
            result, (scene.table, scene.filtered, scene.materialized, scene.consumer)
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        assert (
            _facts(scene)[scene.materialized.node_id].retained_record_id
            != original.retained_record_id
        )
        output = next(
            event
            for event in result.events
            if event["type"] == "node_settled"
            and event["node_id"] == scene.consumer.node_id
        )
        assert [
            item["value"]
            for _path, items in output["outputs"]["output"].value.branches
            for item in items
        ] == ["91", "92"]
    finally:
        scene.runtime.shutdown()


def test_cold_connected_source_and_descendants_remain_non_reusable(tmp_path):
    scene = _materialized_scene(tmp_path, client=_PreparedClient(cold=True))
    try:
        prepared = scene.runtime.prepare_execution(
            scene.request(scene.consumer.node_id)
        )
        scene.runtime.dispatch_prepared(prepared)
        entry = scene.runtime.solution_store._runs[
            scene.client.commands[-1].run_id
        ].preparation
        for node in (scene.table, scene.filtered, scene.materialized, scene.consumer):
            assert not entry.captured_nodes[node.node_id].identity_reuse_eligible
        assert entry.captured_nodes[scene.path.node_id].identity_reuse_eligible
    finally:
        scene.runtime.shutdown()


def test_durable_detached_source_result_uses_captured_keys_without_session_metadata(
    tmp_path, monkeypatch
):
    from ea_node_editor.addons.tabular_data import function_nodes
    from ea_node_editor.addons.tabular_data import extraction_nodes
    from ea_node_editor.execution.solution_backend import DurableBackendOpenResult
    from ea_node_editor.persistence.solution_repository import SolutionRepository

    original = (
        'id="tabular.materialize_table_filter",\n    _solution_reuse_scope="session"'
    )
    assert original in function_nodes.SOURCE
    source = function_nodes.SOURCE.replace(
        original, original.replace('"session"', '"durable"')
    )
    source = source.replace(
        'value_type="COREX.DataTypes.GraphDictionary"',
        'value_type="COREX.DataTypes.Bool"',
    )
    monkeypatch.setattr(function_nodes, "SOURCE", source)
    materialize = extraction_nodes.execute_materialize_table_filter

    def detached_boolean(ctx):
        result = materialize(ctx)
        return SimpleNamespace(
            outputs={"rows": [bool(result.outputs["rows"])]}, warnings=()
        )

    monkeypatch.setattr(
        extraction_nodes, "execute_materialize_table_filter", detached_boolean
    )
    scene = _materialized_scene(tmp_path, client=_PreparedClient())
    for edge in tuple(scene.workspace.edges.values()):
        if (
            edge.target_node_id == scene.table.node_id
            and edge.target_port_key == "path"
        ):
            scene.model.remove_edge(scene.workspace.workspace_id, edge.edge_id)
    project_id = scene.model.project.project_id
    project_path = tmp_path / "project.cxproj"
    scene.runtime.reset_project_session(project_id, str(project_path))
    repository = SolutionRepository.create_empty(
        project_id=project_id,
        project_path=project_path,
        solution_namespace_id=project_id,
        catalog=scene.registry.data_types,
    )
    scene.runtime.solution_store.install_durable_backend(
        project_id,
        DurableBackendOpenResult(
            repository,
            project_id,
            "durable_bound_active",
            active_generation_id="a" * 32,
            active_manifest_set_digest="b" * 64,
        ),
    )
    DEFAULT_RUNTIME_PREPARATION_CACHE.clear()
    monkeypatch.setattr(
        "ea_node_editor.nodes.bootstrap.build_default_registry",
        lambda **_kwargs: scene.registry,
    )
    observed = []
    scene.runtime.subscribe(observed.append)
    try:
        for force in (False, True):
            scene.runtime.dispatch_prepared(
                scene.runtime.prepare_execution(
                    scene.request(scene.consumer.node_id, force=force)
                )
            )
            events = _run_worker(scene, scene.client.commands[-1])
            for event in events:
                if event["type"] in {"node_settled", "run_completed"}:
                    scene.client.emit(event, snapshot=scene.client.snapshot)
            assert not any(
                event["type"] == "solution_nondeterminism" for event in observed
            )
            fact = _facts(scene)[scene.materialized.node_id]
            assert fact.residency is SolutionResidency.DURABLE, (
                scene.runtime.solution_store.last_durable_reason_code,
                [
                    (item.node_id, item.reason_code)
                    for item in scene.client.commands[-1].node_decisions
                ],
                scene.registry.get_spec(
                    "tabular.materialize_table_filter"
                ).solution_reuse_scope,
            )
            current = scene.runtime.prepare_execution(
                scene.request(scene.consumer.node_id)
            )
            payload = next(
                item
                for item in current.accepted_output_payloads
                if item.node_id == scene.materialized.node_id
            )
            assert payload.residency is SolutionResidency.DURABLE
            assert (
                not payload.source_provenance_bindings
                and not payload.retained_source_bindings
            )
        _change_content(scene.source)
        changed = scene.runtime.prepare_execution(scene.request(scene.consumer.node_id))
        assert (
            next(
                item
                for item in changed.node_decisions
                if item.node_id == scene.materialized.node_id
            ).action
            is PreparedAction.EXECUTE
        )
    finally:
        scene.runtime.shutdown()
        DEFAULT_RUNTIME_PREPARATION_CACHE.clear()


def test_unknown_source_provenance_is_inherited_by_detached_descendant(
    tmp_path, monkeypatch
):
    scene = _materialized_scene(tmp_path, client=_PreparedClient())
    try:
        scene.runtime.dispatch_prepared(
            scene.runtime.prepare_execution(scene.request(scene.consumer.node_id))
        )
        DEFAULT_RUNTIME_PREPARATION_CACHE.clear()
        monkeypatch.setattr(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            lambda **_kwargs: scene.registry,
        )
        original = TabularLoaderCacheService.open_source

        def unsupported(loader, path, options=None):
            return replace(original(loader, path, options), resolver_id="unknown")

        monkeypatch.setattr(TabularLoaderCacheService, "open_source", unsupported)
        # Model an ordinary detached computation over an unsupported source. Its
        # lack of a retained resolver must remain visible after the ref disappears.
        monkeypatch.setattr(
            "ea_node_editor.addons.tabular_data.extraction_nodes.execute_materialize_table_filter",
            lambda ctx: SimpleNamespace(
                outputs={"rows": [{"value": "21"}]}, warnings=()
            ),
        )
        events = _run_worker(scene, scene.client.commands[-1])
        detached = next(
            event
            for event in events
            if event["type"] == "node_settled"
            and event["node_id"] == scene.materialized.node_id
        )
        assert detached["status"] == "completed", events
        assert not detached["source_provenance_complete"]
        assert not detached["retained_source_bindings"]
        for event in events:
            if event["type"] == "node_settled":
                scene.client.emit(event, snapshot=scene.client.snapshot)
        next_prepared = scene.runtime.prepare_execution(
            scene.request(scene.consumer.node_id)
        )
        assert (
            next(
                item
                for item in next_prepared.node_decisions
                if item.node_id == scene.materialized.node_id
            ).action
            is PreparedAction.EXECUTE
        )
    finally:
        scene.runtime.shutdown()
        DEFAULT_RUNTIME_PREPARATION_CACHE.clear()


def _assert_executed(result, nodes):
    assert result.status == "completed", result.events
    expected = {node.node_id for node in nodes}
    for event_type in ("node_started", "node_settled"):
        actual = [
            event["node_id"] for event in result.events if event["type"] == event_type
        ]
        assert set(actual) == expected and len(actual) == len(expected), result.events
    assert all(
        event.get("accepted_solution_record")
        for event in result.events
        if event["type"] == "node_settled"
    ), [
        {
            key: event.get(key)
            for key in (
                "type",
                "node_id",
                "reason",
                "disposition",
                "accepted_solution_record",
            )
        }
        for event in result.events
        if event["type"] in {"node_settled", "solution_nondeterminism"}
    ]


def test_real_process_title_edit_disconnect_reconnect_keep_source_record(tmp_path):
    scene = _scene(tmp_path)
    try:
        _assert_executed(
            scene.runtime.run(scene.request(), timeout=40),
            (scene.table, scene.title, scene.plot, scene.media),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        original = _facts(scene)[scene.table.node_id]
        scene.model.validated_mutations(
            scene.workspace.workspace_id, scene.registry
        ).set_node_property(scene.title.node_id, "value", "Edited title")
        invalidation = scene.invalidate(scene.title.node_id)
        prepared = scene.runtime.prepare_execution(
            scene.request(*invalidation.expired_node_ids)
        )
        table_decision = next(
            item
            for item in prepared.node_decisions
            if item.node_id == scene.table.node_id
        )
        assert table_decision.action is PreparedAction.READ_CURRENT
        payload = next(
            item
            for item in prepared.accepted_output_payloads
            if item.node_id == scene.table.node_id
        )
        assert payload.record_id == original.retained_record_id
        assert len(payload.retained_source_bindings) == 1
        result = scene.runtime.run(
            scene.request(*invalidation.expired_node_ids), timeout=40
        )
        _assert_executed(result, (scene.title, scene.plot, scene.media))
        _wait_for_backend_run_cleanup(scene.runtime)
        assert _facts(scene)[scene.table.node_id] == original
        scene.model.remove_edge(scene.workspace.workspace_id, scene.title_edge.edge_id)
        invalidation = scene.invalidate(scene.plot.node_id)
        _assert_executed(
            scene.runtime.run(
                scene.request(*invalidation.expired_node_ids), timeout=40
            ),
            (scene.plot, scene.media),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        assert _facts(scene)[scene.table.node_id] == original
        scene.model.add_edge(
            scene.workspace.workspace_id,
            scene.title.node_id,
            "output",
            scene.plot.node_id,
            "title",
        )
        invalidation = scene.invalidate(scene.plot.node_id)
        _assert_executed(
            scene.runtime.run(
                scene.request(*invalidation.expired_node_ids), timeout=40
            ),
            (scene.plot, scene.media),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        assert _facts(scene)[scene.table.node_id] == original
        _assert_executed(
            scene.runtime.run(scene.request(force=True), timeout=40),
            (scene.table, scene.title, scene.plot, scene.media),
        )
    finally:
        scene.runtime.shutdown()


def _bound_payload(registry, value, bindings):
    outputs = {
        "data": SettledPortResult(status="value", value=DataTree.from_item(value))
    }
    encoded = json.dumps(
        settled_outputs_to_payload(outputs, catalog=registry.data_types),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return AcceptedOutputPayload(
        node_id="node",
        record_id="record",
        solution_key="a" * 64,
        settlement_status="completed",
        result_digest=hashlib.sha256(encoded).hexdigest(),
        residency=SolutionResidency.SESSION,
        runtime_generation=1,
        outputs=encoded,
        retained_source_bindings=bindings,
        catalog=registry.data_types,
    )


def test_current_source_binding_roundtrip_subset_and_durable_rejection(tmp_path):
    source, loader, ref = _table(tmp_path)
    registry = build_default_registry(include_public_plugins=False)
    bindings = collect_retained_source_bindings(ref)
    payload = _bound_payload(
        registry, {"nested": [TabularWindowRef("window", ref, row_limit=1)]}, bindings
    )
    roundtrip = AcceptedOutputPayload.from_payload(
        payload.to_payload(), catalog=registry.data_types
    )
    assert roundtrip == payload
    assert roundtrip.commitment_digest() == payload.commitment_digest()
    validate_current_output_payload(
        roundtrip, catalog=registry.data_types, port_keys=("data",)
    )
    for changed in ((), (replace(bindings[0], sha256="a" * 64),)):
        forged = replace(
            payload, retained_source_bindings=changed, catalog=registry.data_types
        )
        assert forged.commitment_digest() != payload.commitment_digest()
        with pytest.raises(ValueError):
            validate_current_output_payload(
                forged, catalog=registry.data_types, port_keys=("data",)
            )
    with pytest.raises(ValueError, match="duplicate"):
        replace(
            payload,
            retained_source_bindings=bindings + bindings,
            catalog=registry.data_types,
        )
    with pytest.raises(ValueError):
        replace(
            payload,
            residency=SolutionResidency.DURABLE,
            runtime_generation=None,
            catalog=registry.data_types,
        )
    _change_content(source)
    with pytest.raises(ValueError, match="differs"):
        validate_current_output_payload(
            roundtrip, catalog=registry.data_types, port_keys=("data",)
        )


def test_real_process_connected_path_retains_current_source_but_not_computation(
    tmp_path,
):
    scene = _scene(tmp_path)
    path = scene.model.add_node(
        scene.workspace.workspace_id,
        "data.panel",
        "Source path",
        -300,
        0,
        properties={"value": str(scene.source), "interpretation": "text"},
    )
    scene.model.add_edge(
        scene.workspace.workspace_id,
        path.node_id,
        "output",
        scene.table.node_id,
        "path",
    )
    try:
        _assert_executed(
            scene.runtime.run(scene.request(), timeout=40),
            (path, scene.table, scene.title, scene.plot, scene.media),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        original = _facts(scene)[scene.table.node_id]
        assert not scene.runtime.solution_record(
            original.retained_record_id
        ).reuse_eligible
        scene.model.validated_mutations(
            scene.workspace.workspace_id, scene.registry
        ).set_node_property(scene.title.node_id, "value", "Connected title")
        invalidation = scene.invalidate(scene.title.node_id)
        prepared = scene.runtime.prepare_execution(
            scene.request(*invalidation.expired_node_ids)
        )
        decisions = {item.node_id: item.action for item in prepared.node_decisions}
        assert decisions[scene.table.node_id] is PreparedAction.READ_CURRENT
        assert decisions[path.node_id] is PreparedAction.PRUNE
        _assert_executed(
            scene.runtime.run(
                scene.request(*invalidation.expired_node_ids), timeout=40
            ),
            (scene.title, scene.plot, scene.media),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        assert _facts(scene)[scene.table.node_id] == original
        _change_content(scene.source)
        invalidation = scene.invalidate(scene.plot.node_id)
        _assert_executed(
            scene.runtime.run(
                scene.request(*invalidation.expired_node_ids), timeout=40
            ),
            (scene.table, scene.plot, scene.media),
        )
        _wait_for_backend_run_cleanup(scene.runtime)
        assert (
            _facts(scene)[scene.table.node_id].retained_record_id
            != original.retained_record_id
        )
    finally:
        scene.runtime.shutdown()


def test_real_process_path_ports_receive_unquoted_windows_copy_as_path_text(tmp_path):
    """Path ports canonicalize wired text before provenance capture or any node sees it."""
    pyvista = pytest.importorskip("pyvista")
    part = tmp_path / "part.stl"
    pyvista.Cube().triangulate().save(part)
    registry = build_default_registry(include_public_plugins=False)
    model = GraphModel()
    wid = model.active_workspace.workspace_id
    panel = model.add_node(
        wid,
        "data.panel",
        "Path",
        0,
        0,
        properties={"value": f'"{part}"', "interpretation": "text"},
    )
    cad = model.add_node(
        wid,
        "engineering.cad_import",
        "CAD",
        300,
        0,
        properties={"length_unit": "mm"},
    )
    deconstruct = model.add_node(wid, "io.deconstruct_file_path", "Parts", 300, 200)
    model.add_edge(wid, panel.node_id, "output", cad.node_id, "path")
    model.add_edge(wid, panel.node_id, "output", deconstruct.node_id, "file_path")
    runtime = CorexRuntime(registry=registry)
    try:
        result = runtime.run(
            ExecutionRequest(
                runtime_snapshot=build_runtime_snapshot(
                    model.project, workspace_id=wid, registry=registry
                ),
                workspace_id=wid,
                target_node_ids=(cad.node_id, deconstruct.node_id),
                recompute_mode=RecomputeMode.FORCE_RECOMPUTE,
            ),
            timeout=120,
        )
        settled = {
            event["node_id"]: event
            for event in result.events
            if event["type"] == "node_settled"
        }
        assert result.status == "completed", result.events
        assert settled[cad.node_id]["status"] == "completed", settled[cad.node_id]
        assert settled[cad.node_id]["outputs"]["scene"]["status"] == "value"
        parts = settled[deconstruct.node_id]["outputs"]
        assert [
            [item for _path, items in parts[key].value.branches for item in items]
            for key in ("directory", "file_extension")
        ] == [[str(tmp_path)], [".stl"]], parts
    finally:
        runtime.shutdown()


@pytest.fixture
def retained_scene(tmp_path, monkeypatch, request):
    scene = _scene(tmp_path, client=_PreparedClient())
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(
        scene.source, TabularLoadOptions(cache_policy="source_direct")
    )
    bindings = collect_retained_source_bindings(ref)
    scene.client.events_on_start = [
        {
            **_settlement(scene.table.node_id, table_data=ref, array_data=None),
            "retained_source_bindings": bindings,
        },
        _settlement(scene.title.node_id, output="Original title"),
        {"type": "run_completed"},
    ]
    scene.client.events_on_start[0]["outputs"]["array_data"] = SettledPortResult(
        status="empty"
    )
    if getattr(request, "param", "") == "unbound_unused":
        scene.client.events_on_start[0]["outputs"]["array_data"] = SettledPortResult(
            status="value",
            value=DataTree.from_item(
                ArrayDataRef(ref_id="unbound", resolver_id="unknown")
            ),
        )
    scene.runtime.dispatch_prepared(scene.runtime.prepare_execution(scene.request()))
    scene.client.events_on_start = []
    scene.ref = ref
    scene.bindings = bindings
    DEFAULT_RUNTIME_PREPARATION_CACHE.clear()
    monkeypatch.setattr(
        "ea_node_editor.nodes.bootstrap.build_default_registry",
        lambda **_kwargs: scene.registry,
    )
    try:
        yield scene
    finally:
        scene.runtime.shutdown()
        DEFAULT_RUNTIME_PREPARATION_CACHE.clear()


@pytest.mark.parametrize("retained_scene", ["unbound_unused"], indirect=True)
def test_current_table_ignores_unconsumed_unbound_array_port(retained_scene):
    scene = retained_scene
    fact = _facts(scene)[scene.table.node_id]
    assert not scene.runtime.solution_record(fact.retained_record_id).reuse_eligible
    prepared = scene.runtime.prepare_execution(scene.request(scene.plot.node_id))
    payload = next(
        item
        for item in prepared.accepted_output_payloads
        if item.node_id == scene.table.node_id
    )
    assert set(payload.to_payload()["outputs"]) == {"table_data"}
    assert payload.retained_source_bindings == scene.bindings
    scene.runtime.dispatch_prepared(prepared)
    events = _run_worker(scene, scene.client.commands[-1])
    settled = [event for event in events if event["type"] == "node_settled"]
    assert len(settled) == 1 and settled[0]["node_id"] == scene.plot.node_id
    assert settled[0]["status"] == "completed", events


def test_plot_computational_identity_excludes_only_run_occurrence(monkeypatch):
    from ea_node_editor.execution.settled_output_identity import (
        computational_output_digest,
    )
    from tests.test_plot_value import plot_value

    registry = build_default_registry(include_public_plugins=False)
    original = plot_value()

    def digest(value):
        outputs = {
            "output": SettledPortResult(
                status="value", value=DataTree.from_item({"nested": [value]})
            )
        }
        return computational_output_digest(
            outputs, catalog=registry.data_types, result_digest="f" * 64
        )

    changed_run = replace(
        original, provenance=replace(original.provenance, run_id="new-run")
    )
    assert digest(original) == digest(changed_run)
    assert original.value_signature != changed_run.value_signature
    assert digest(original) != digest(
        replace(original, settings=replace(original.settings, title="different"))
    )
    assert digest(original) != digest(
        replace(original, provenance=replace(original.provenance, node_id="other"))
    )
    assert digest(original) != digest(
        replace(original, signals=(replace(original.signals[0], label="different"),))
    )
    # Mixed user dictionaries preserve run_id as ordinary data.
    assert digest([original, {"run_id": "first"}]) != digest(
        [original, {"run_id": "second"}]
    )
    monkeypatch.setattr(
        "ea_node_editor.execution.settled_output_identity.serialize_runtime_value",
        lambda *_args, **_kwargs: pytest.fail(
            "ordinary values must use the existing digest"
        ),
    )
    assert digest({"run_id": "ordinary"}) == "f" * 64


def test_retained_binding_bytes_count_toward_session_record_capacity(tmp_path):
    from ea_node_editor.execution.solution_store import (
        SolutionStore,
        SolutionStoreLimits,
    )

    scene = _scene(tmp_path, client=_PreparedClient())
    loader = TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    ref = loader.open_source(
        scene.source, TabularLoadOptions(cache_policy="source_direct")
    )
    event = _settlement(scene.table.node_id, table_data=ref)
    event["outputs"]["array_data"] = SettledPortResult(status="empty")
    bindings = collect_retained_source_bindings(ref)
    encoded = json.dumps(
        settled_outputs_to_payload(event["outputs"], catalog=scene.registry.data_types),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    scene.runtime.shutdown()
    scene.runtime = CorexRuntime(
        client=scene.client,
        registry=scene.registry,
        solution_store=SolutionStore(
            limits=SolutionStoreLimits(payload_bytes_per_runtime=len(encoded))
        ),
    )
    # request() only closes over the graph; dispatch directly on the capacity-limited runtime.
    scene.client.events_on_start = [
        {**event, "retained_source_bindings": bindings},
        {"type": "run_completed"},
    ]
    try:
        scene.runtime.dispatch_prepared(
            scene.runtime.prepare_execution(scene.request(scene.table.node_id))
        )
        fact = _facts(scene)[scene.table.node_id]
        assert fact.expiration_reason_code == "session_store_capacity_exceeded"
        assert scene.runtime.solution_store.stats()["records"] == 0
    finally:
        scene.runtime.shutdown()


@pytest.mark.parametrize("mutation", ["changed", "missing", "generation"])
def test_invalid_source_before_preparation_recomputes_required_ancestry(
    retained_scene, mutation
):
    scene = retained_scene
    if mutation == "changed":
        _change_content(scene.source)
    elif mutation == "missing":
        scene.source.unlink()
    else:
        scene.client.snapshot = replace(
            scene.client.snapshot, runtime_generation=2, backend_generation=2
        )
    prepared = scene.runtime.prepare_execution(scene.request(scene.plot.node_id))
    assert (
        next(
            item
            for item in prepared.node_decisions
            if item.node_id == scene.table.node_id
        ).action
        is PreparedAction.EXECUTE
    )
    assert (
        next(
            item
            for item in prepared.node_decisions
            if item.node_id == scene.plot.node_id
        ).action
        is PreparedAction.EXECUTE
    )


@pytest.mark.parametrize("mutation", ["source", "binding", "unbound"])
def test_worker_rejects_source_changes_and_forged_bindings_before_node_events(
    retained_scene, mutation
):
    scene = retained_scene
    prepared = scene.runtime.prepare_execution(scene.request(scene.plot.node_id))
    scene.runtime.dispatch_prepared(prepared)
    command = scene.client.commands[-1]
    if mutation == "source":
        _change_content(scene.source)
    else:
        original = next(
            item
            for item in command.accepted_output_payloads
            if item.node_id == scene.table.node_id
        )
        bindings = (
            ()
            if mutation == "unbound"
            else (replace(original.retained_source_bindings[0], sha256="a" * 64),)
        )
        forged = replace(
            original,
            retained_source_bindings=bindings,
            catalog=scene.registry.data_types,
        )
        command = replace(
            command,
            accepted_output_payloads=tuple(
                forged if item.node_id == forged.node_id else item
                for item in command.accepted_output_payloads
            ),
            node_decisions=tuple(
                replace(item, accepted_payload_digest=forged.commitment_digest())
                if item.node_id == forged.node_id
                else item
                for item in command.node_decisions
            ),
        )
    events = _run_worker(scene, command)
    assert any(event["type"] == "run_failed" for event in events), events
    assert not any(
        event["type"] in {"node_started", "node_settled"} for event in events
    ), events


def test_actual_consumer_read_rejects_source_changed_after_worker_admission(
    retained_scene, monkeypatch
):
    scene = retained_scene
    prepared = scene.runtime.prepare_execution(scene.request(scene.plot.node_id))
    scene.runtime.dispatch_prepared(prepared)
    original = NodeExecutor._execute_node

    def change_then_read(executor, node_id):
        if node_id == scene.plot.node_id:
            _change_content(scene.source)
        return original(executor, node_id)

    monkeypatch.setattr(NodeExecutor, "_execute_node", change_then_read)
    events = _run_worker(scene, scene.client.commands[-1])
    settled = [event for event in events if event["type"] == "node_settled"]
    assert len(settled) == 1 and settled[0]["node_id"] == scene.plot.node_id
    assert settled[0]["status"] == "failed", events
    assert "accepted output" in settled[0]["errors"][0]["error"]


def test_new_source_cannot_bind_changed_bytes_to_original_capture(
    tmp_path, monkeypatch
):
    scene = _scene(tmp_path, client=_PreparedClient())
    try:
        scene.runtime.dispatch_prepared(
            scene.runtime.prepare_execution(scene.request(scene.table.node_id))
        )
        DEFAULT_RUNTIME_PREPARATION_CACHE.clear()
        monkeypatch.setattr(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            lambda **_kwargs: scene.registry,
        )
        original = TabularLoaderCacheService.open_source

        def change_after_open(loader, path, options=None):
            ref = original(loader, path, options)
            _change_content(scene.source)
            return ref

        monkeypatch.setattr(TabularLoaderCacheService, "open_source", change_after_open)
        events = _run_worker(scene, scene.client.commands[-1])
        settled = [event for event in events if event["type"] == "node_settled"]
        assert len(settled) == 1 and settled[0]["status"] == "failed", events
        assert "after execution preparation" in settled[0]["errors"][0]["error"]
        assert not settled[0]["retained_source_bindings"]
    finally:
        scene.runtime.shutdown()
        DEFAULT_RUNTIME_PREPARATION_CACHE.clear()
