from __future__ import annotations

import json
import queue
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.common.optimization_links import (
    OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
    OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
    PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
    PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE,
)
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
    DpfMaterializationResult,
)
from ea_node_editor.execution.dpf_runtime.viewer_session_backend import (
    DpfViewerSessionMaterializationBackend,
    ViewerSessionMaterializationRequest,
)
from ea_node_editor.execution.backends import (
    TRUSTED_IN_PROCESS_BACKEND,
    ExecutionBackendSelection,
)
from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.execution.protocol import (
    CloseViewerSessionCommand,
    MaterializeViewerDataCommand,
    NodeSettledEvent,
    OpenViewerSessionCommand,
    QueryViewerSessionCommand,
    SettledPortResult,
    ShutdownCommand,
    StartRunCommand,
    UpdateViewerSessionCommand,
    ViewerSessionOpenedEvent,
    catalog_agreement,
    command_to_dict,
    coerce_start_run_command,
    dict_to_command,
    dict_to_event,
)
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    build_runtime_snapshot,
)
from ea_node_editor.execution.worker import run_workflow, worker_main
from ea_node_editor.execution.worker_runner import WorkflowRunner
from ea_node_editor.execution.worker_runtime import (
    ExecutionPlan,
    RuntimePreparationCache,
    prepare_runtime,
)
from ea_node_editor.execution.worker_protocol import dispatch_viewer_command
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.execution.viewer_backend import ViewerBackendQueryResult
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeLinkRecord
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_VIEWER_DATASET_DATA_TYPE,
)
from ea_node_editor.nodes.decorators import node_type
from ea_node_editor.nodes.output_artifacts import register_staged_artifact
from ea_node_editor.nodes.plugin_contracts import PluginContractManifest
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import (
    ExecutionContext,
    NodeResult,
    PortSpec,
    deserialize_runtime_value,
)
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.runtime_contracts import (
    ARRAY_DATA_REF_TYPE_ID,
    PATH_DATA_TYPE_ID,
    TABULAR_DATA_REF_TYPE_ID,
    ArrayDataRef,
    DataTypeCatalog,
    DataTypeFamilySpec,
    DataTypeSpec,
    DataTree,
    RuntimeArtifactRef,
    RuntimeHandleRef,
    TabularDataRef,
)
from tests.typed_handle_support import dpf_worker_services

_WAIT_NODE_ENTERED = threading.Event()
_WAIT_NODE_RELEASE = threading.Event()
_TEST_HANDLE_TYPE_ID = "tests.Runtime.Payload"
_TEST_HANDLE_KIND = "tests.payload"
_TEST_START_CATALOGS = {}
_OPTIMIZATION_CONTEXTS: list[ExecutionContext] = []
_OPTIMIZATION_EXECUTION_ORDER: list[tuple[str, str]] = []
_OPTIMIZATION_STATE_READS: dict[str, object] = {}


def _decorated_python_script(body: str) -> str:
    indented = "\n".join(f"    {line}" for line in body.splitlines())
    return (
        "@corex.node\n"
        "@corex.output(\"result\", value_type=corex.Any)\n"
        "def run(ctx):\n"
        f"{indented}\n"
    )


def _catalog_start_run_command(command, *, catalog=None):  # noqa: ANN001
    if catalog is None:
        from ea_node_editor.nodes import bootstrap as node_bootstrap

        provider = node_bootstrap.build_default_registry
        active_catalog = _TEST_START_CATALOGS.get(provider)
        if active_catalog is None:
            active_catalog = provider().data_types
            _TEST_START_CATALOGS[provider] = active_catalog
    else:
        active_catalog = catalog
    return coerce_start_run_command(command, catalog=active_catalog)


def _revision_catalog(implementation_version: str) -> DataTypeCatalog:
    catalog = DataTypeCatalog()
    catalog.register_many(
        families=(
            DataTypeFamilySpec("tests.catalog", "Catalog", "data.tests", "tests"),
        ),
        types=(
            DataTypeSpec(
                "tests.CatalogValue",
                "Catalog Value",
                "tests.catalog",
                lambda value: isinstance(value, str),
                implementation_version=implementation_version,
            ),
        ),
        owner_id="tests.catalog",
        owner_version=implementation_version,
    )
    catalog.freeze()
    return catalog


def _register_test_handle_type(registry) -> None:  # noqa: ANN001
    registry.register_plugin_bundle(
        PluginContractManifest(
            data_type_families=(
                DataTypeFamilySpec("tests", "Tests", "data.tests", "tests"),
            ),
            data_types=(
                DataTypeSpec(
                    _TEST_HANDLE_TYPE_ID,
                    "Test Payload",
                    "tests",
                    lambda value: (
                        isinstance(value, RuntimeHandleRef)
                        and value.kind == _TEST_HANDLE_KIND
                    ),
                    carriers=frozenset({"handle"}),
                ),
            ),
        ),
        (),
        owner_id="tests.execution_worker_handles",
    )


def _test_handle_worker_services() -> WorkerServices:
    registry = build_default_registry()
    _register_test_handle_type(registry)
    services = WorkerServices()
    services.bind_data_types(registry.data_types)
    return services


@node_type(
    type_id="tests.passive_note",
    display_name="Passive Note",
    category_path=("Tests",),
    icon="note",
    ports=(),
    properties=(),
    runtime_behavior="passive",
    surface_family="annotation",
)
class _PassiveNotePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id="tests.artifact_source",
    display_name="Artifact Source",
    category_path=("Tests",),
    icon="upload",
    ports=(
        PortSpec("artifact", "out", "data", "COREX.DataTypes.Path", exposed=True),
        PortSpec(
            "summary", "out", "data", "COREX.DataTypes.String", exposed=True
        ),
    ),
    properties=(),
)
class _ArtifactSourcePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(
            outputs={
                "artifact": RuntimeArtifactRef.staged(
                    "stored_stdout",
                    data_type_id=PATH_DATA_TYPE_ID,
                    schema_version=1,
                    format="txt",
                    size_bytes=98_303,
                    sha256="595d915dcae2d1d0d4f18dbb624f16d7c17223d9c849e37405c9c053f762a733",
                    provenance="corex.test.fixture",
                ),
                "summary": "stored output staged",
            }
        )


@node_type(
    type_id="tests.artifact_sink",
    display_name="Artifact Sink",
    category_path=("Tests",),
    icon="download",
    ports=(
        PortSpec("artifact", "in", "data", "COREX.DataTypes.Path", required=True),
        PortSpec("resolved_path", "out", "data", "COREX.DataTypes.Path", exposed=True),
        PortSpec(
            "artifact_size", "out", "data", "COREX.DataTypes.Int", exposed=True
        ),
    ),
    properties=(),
)
class _ArtifactSinkPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        path = ctx.resolve_input_path("artifact")
        if path is None:
            raise FileNotFoundError(
                "Artifact Sink could not resolve the runtime artifact input."
            )
        contents = path.read_text(encoding="utf-8")
        return NodeResult(
            outputs={
                "resolved_path": str(path),
                "artifact_size": len(contents),
            }
        )


@node_type(
    type_id="tests.tabular_runtime_source",
    display_name="Tabular Runtime Source",
    category_path=("Tests",),
    icon="table",
    ports=(
        PortSpec("table", "out", "data", TABULAR_DATA_REF_TYPE_ID, exposed=True),
        PortSpec("array", "out", "data", ARRAY_DATA_REF_TYPE_ID, exposed=True),
    ),
    properties=(),
)
class _TabularRuntimeSourcePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(
            outputs={
                "table": TabularDataRef(
                    ref_id="table_runtime_worker",
                    resolver_id="tabular.cache",
                    backend_id="duckdb",
                    row_count=128,
                    column_count=6,
                ),
                "array": ArrayDataRef(
                    ref_id="array_runtime_worker",
                    resolver_id="tabular.cache",
                    backend_id="npy_mmap",
                    shape=(64, 32),
                    dtype="float32",
                ),
            }
        )


_TABULAR_WARNING_TEXTS = (
    "Tabular large-data warning: source_larger_than_1_gib",
    "Tabular selector-required warning: selector_required",
    "Tabular backend-fallback warning: backend_fallback_to_python_text_stream",
    "Tabular NPZ-gated warning: large_npz_preview_requires_explicit_opt_in",
)


@node_type(
    type_id="tests.tabular_warning_source",
    display_name="Tabular Warning Source",
    category_path=("Tests",),
    icon="table",
    ports=(),
    properties=(),
)
class _TabularWarningSourcePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(warnings=_TABULAR_WARNING_TEXTS)


@node_type(
    type_id="tests.error_source",
    display_name="Error Source",
    category_path=("Tests",),
    icon="alert-triangle",
    ports=(
        PortSpec("error", "out", "data", "COREX.DataTypes.String", exposed=True),
    ),
    properties=(),
)
class _ErrorSourcePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"error": "explicit handler error"})


@node_type(
    type_id="tests.failure_error_sink",
    display_name="Failure Error Sink",
    category_path=("Tests",),
    icon="alert-circle",
    ports=(
        PortSpec("error", "in", "data", "COREX.DataTypes.String", required=True),
        PortSpec(
            "seen_error", "out", "data", "COREX.DataTypes.String", exposed=True
        ),
    ),
    properties=(),
)
class _FailureErrorSinkPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"seen_error": ctx.inputs.get("error", "")})


@node_type(
    type_id="tests.handle_source",
    display_name="Handle Source",
    category_path=("Tests",),
    icon="memory",
    ports=(PortSpec("handle", "out", "data", _TEST_HANDLE_TYPE_ID, exposed=True),),
    properties=(),
)
class _HandleSourcePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        handle_ref = ctx.register_handle(
            {"value": "from_handle"},
            data_type_id=_TEST_HANDLE_TYPE_ID,
            kind=_TEST_HANDLE_KIND,
        )
        return NodeResult(outputs={"handle": handle_ref})


def _raise_test_handle_disposal_error() -> None:
    raise RuntimeError("test handle disposal failed")


@node_type(
    type_id="tests.failing_dispose_handle_source",
    display_name="Failing Dispose Handle Source",
    category_path=("Tests",),
    icon="memory",
    ports=(PortSpec("handle", "out", "data", _TEST_HANDLE_TYPE_ID, exposed=True),),
    properties=(),
)
class _FailingDisposeHandleSourcePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        handle_ref = ctx.register_handle(
            object(),
            data_type_id=_TEST_HANDLE_TYPE_ID,
            kind=_TEST_HANDLE_KIND,
            dispose=_raise_test_handle_disposal_error,
        )
        return NodeResult(outputs={"handle": handle_ref})


@node_type(
    type_id="tests.persistent_handle_source",
    display_name="Persistent Handle Source",
    category_path=("Tests",),
    icon="database",
    ports=(PortSpec("handle", "out", "data", _TEST_HANDLE_TYPE_ID, exposed=True),),
    properties=(),
)
class _PersistentHandleSourcePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        handle_ref = ctx.register_handle(
            {"value": "cached_handle"},
            data_type_id=_TEST_HANDLE_TYPE_ID,
            kind=_TEST_HANDLE_KIND,
            owner_scope="cache:tests:persistent_handle",
        )
        return NodeResult(outputs={"handle": handle_ref})


@node_type(
    type_id="tests.viewer_source",
    display_name="Viewer Source",
    category_path=("Tests",),
    icon="image",
    ports=(
        PortSpec(
            "fields_container",
            "out",
            "data",
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            exposed=True,
        ),
        PortSpec("model", "out", "data", DPF_MODEL_DATA_TYPE, exposed=True),
    ),
    properties=(),
)
class _ViewerSourcePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        fields_ref = ctx.register_handle(
            {"viewer": "fields"},
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        )
        model_ref = ctx.register_handle(
            {"viewer": "model"},
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
        )
        return NodeResult(
            outputs={
                "fields_container": fields_ref,
                "model": model_ref,
            }
        )


@node_type(
    type_id="tests.viewer_wait",
    display_name="Viewer Wait",
    category_path=("Tests",),
    icon="hourglass",
    ports=(
        PortSpec(
            "dependency",
            "in",
            "data",
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            required=True,
        ),
    ),
    properties=(),
)
class _ViewerWaitPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        _WAIT_NODE_ENTERED.set()
        deadline = time.time() + 15.0
        while not _WAIT_NODE_RELEASE.is_set() and time.time() < deadline:
            ctx.should_stop()
            time.sleep(0.01)
        return NodeResult()


@node_type(
    type_id="tests.handle_sink",
    display_name="Handle Sink",
    category_path=("Tests",),
    icon="download",
    ports=(
        PortSpec("handle", "in", "data", _TEST_HANDLE_TYPE_ID, required=True),
        PortSpec(
            "resolved_value",
            "out",
            "data",
            "COREX.DataTypes.String",
            exposed=True,
        ),
    ),
    properties=(),
)
class _HandleSinkPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        payload = ctx.resolve_handle(
            ctx.inputs["handle"], expected_kind="tests.payload"
        )
        return NodeResult(outputs={"resolved_value": payload["value"]})


@node_type(
    type_id=OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
    display_name="Parameter Setup",
    category_path=("Tests",),
    icon="settings",
    ports=(
        PortSpec(
            "reverse",
            "in",
            "data",
            "COREX.DataTypes.String",
            required=False,
        ),
    ),
    properties=(),
)
class _OptimizationParameterSetupPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        _OPTIMIZATION_CONTEXTS.append(ctx)
        _OPTIMIZATION_EXECUTION_ORDER.append((ctx.run_id, ctx.node_id))
        if ctx.run_id == "run_semantic_links_first":
            target_node_id = str(ctx.semantic_links[0]["target_node_id"])
            ctx.publish_node_state(
                target_node_id,
                {"publisher": ctx.node_id},
            )
        return NodeResult()


@node_type(
    type_id=OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
    display_name="Parameter Pool",
    category_path=("Tests",),
    icon="list",
    ports=(
        PortSpec(
            "reverse",
            "out",
            "data",
            "COREX.DataTypes.String",
            exposed=True,
        ),
    ),
    properties=(),
)
class _OptimizationParameterPoolPlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        _OPTIMIZATION_CONTEXTS.append(ctx)
        _OPTIMIZATION_EXECUTION_ORDER.append((ctx.run_id, ctx.node_id))
        _OPTIMIZATION_STATE_READS[ctx.run_id] = ctx.read_node_state(ctx.node_id)
        return NodeResult(outputs={"reverse": "pool"})


def _build_optimization_worker_test_registry() -> NodeRegistry:
    default_registry = build_default_registry()
    replaced_type_ids = {
        OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
        OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
    }
    registry = NodeRegistry(data_types=default_registry.data_types)
    registry.register_descriptors(
        descriptor
        for descriptor in default_registry.all_descriptors()
        if descriptor.spec.type_id not in replaced_type_ids
    )
    registry.register(_OptimizationParameterSetupPlugin)
    registry.register(_OptimizationParameterPoolPlugin)
    return registry


class ExecutionWorkerTests(unittest.TestCase):
    @staticmethod
    def _drain_events(event_queue: queue.Queue) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        return events

    @staticmethod
    def _runtime_snapshot(model: GraphModel, *, registry=None):  # noqa: ANN001
        runtime_registry = registry or build_default_registry()
        return build_runtime_snapshot(
            model.project,
            workspace_id=model.active_workspace.workspace_id,
            registry=runtime_registry,
        )

    @staticmethod
    def _settled_output_tree(
        event: dict[str, object],
        port_key: str,
        *,
        catalog=None,  # noqa: ANN001
    ) -> DataTree:
        outputs = event.get("outputs", {})
        assert isinstance(outputs, dict)
        result = outputs[port_key]
        assert isinstance(result, dict)
        assert result.get("status") == "value"
        tree = deserialize_runtime_value(result["value"], catalog=catalog)
        assert isinstance(tree, DataTree)
        return tree

    @classmethod
    def _settled_output_value(
        cls,
        event: dict[str, object],
        port_key: str,
        *,
        catalog=None,  # noqa: ANN001
    ) -> object:
        tree = cls._settled_output_tree(event, port_key, catalog=catalog)
        return tree.branches[0][1][0]

    @staticmethod
    def _node_settled(
        events: list[dict[str, object]],
        node_id: str,
    ) -> dict[str, object]:
        return next(
            event
            for event in events
            if event.get("type") == "node_settled" and event.get("node_id") == node_id
        )

    @classmethod
    def _settled_error(
        cls,
        events: list[dict[str, object]],
        node_id: str,
    ) -> dict[str, object]:
        settled = cls._node_settled(events, node_id)
        errors = settled.get("errors", ())
        assert isinstance(errors, (list, tuple)) and errors
        error = errors[0]
        assert isinstance(error, dict)
        return error

    @staticmethod
    def _wait_for_event(
        event_queue: queue.Queue,
        predicate,  # noqa: ANN001
        *,
        timeout: float = 5.0,
        collected: list[dict[str, object]] | None = None,
    ) -> dict[str, object] | None:
        deadline = time.time() + timeout
        seen_events = collected if collected is not None else []
        while time.time() < deadline:
            try:
                event = event_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            seen_events.append(event)
            if predicate(event):
                return event
        return None

    def _fake_viewer_materialize(
        self,
        worker_services: WorkerServices,
        calls: list[dict[str, object]],
    ):
        def _materialize(
            value,  # noqa: ANN001
            *,
            model,  # noqa: ANN001
            mesh=None,  # noqa: ANN001
            output_profile: str,
            artifact_store=None,  # noqa: ANN001
            artifact_key: str = "",
            export_formats=(),  # noqa: ANN001
            camera_state=None,  # noqa: ANN001
            temporary_root_parent=None,  # noqa: ANN001
            run_id: str = "",
            owner_scope: str = "",
            **extra_kwargs,  # noqa: ANN003
        ) -> DpfMaterializationResult:
            worker_services.resolve_handle(
                value, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND
            )
            worker_services.resolve_handle(model, expected_kind=DPF_MODEL_HANDLE_KIND)
            calls.append(
                {
                    "fields_owner_scope": value.owner_scope,
                    "model_owner_scope": model.owner_scope,
                    "artifact_key": artifact_key,
                    "output_profile": output_profile,
                    "export_formats": tuple(export_formats),
                    "artifact_store_present": artifact_store is not None,
                    "camera_state": dict(camera_state or {})
                    if isinstance(camera_state, dict)
                    else camera_state,
                    "temporary_root_parent": temporary_root_parent,
                    "run_id": run_id,
                    "owner_scope": owner_scope,
                    "extra_kwargs": dict(extra_kwargs),
                }
            )

            dataset_ref = None
            if output_profile in {"memory", "both"}:
                dataset_ref = worker_services.register_handle(
                    {"dataset": "viewer"},
                    data_type_id=DPF_VIEWER_DATASET_DATA_TYPE,
                    kind=DPF_VIEWER_DATASET_HANDLE_KIND,
                    owner_scope=owner_scope or "cache:tests:viewer_dataset",
                    metadata={"dataset_type": "fake_dataset", "array_names": ["U"]},
                )
            artifacts = {}
            if output_profile in {"stored", "both"}:
                artifacts["png"] = RuntimeArtifactRef.staged(
                    "worker_viewer_png",
                    data_type_id=PATH_DATA_TYPE_ID,
                    schema_version=1,
                    format="png",
                    size_bytes=0,
                    sha256="0" * 64,
                    provenance="corex.test.fixture",
                )
            return DpfMaterializationResult(
                output_profile=output_profile,
                dataset_ref=dataset_ref,
                artifacts=artifacts,
                summary={"output_profile": output_profile, "field_count": 1},
            )

        return _materialize

    @staticmethod
    def _fake_viewer_transport_bundle(
        _value,  # noqa: ANN001
        *,
        model,  # noqa: ANN001
        bundle_root,
        mesh=None,  # noqa: ANN001
        workspace_id: str = "",
        session_id: str = "",
        transport_revision: int = 0,
    ) -> dict[str, object]:
        root_path = Path(bundle_root)
        dataset_dir = root_path / "dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        entry_file = "dataset/dataset.vtm"
        entry_path = root_path / entry_file
        entry_path.write_text("worker fake transport bundle", encoding="utf-8")
        manifest_path = root_path / "transport_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema": "ea.dpf.viewer_transport_bundle.v1",
                    "workspace_id": workspace_id,
                    "session_id": session_id,
                    "transport_revision": transport_revision,
                    "entry_file": entry_file,
                    "files": [entry_file],
                    "metadata": {
                        "model": repr(model),
                        "has_mesh": mesh is not None,
                    },
                },
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "kind": "dpf_transport_bundle",
            "version": 1,
            "schema": "ea.dpf.viewer_transport_bundle.v1",
            "manifest_path": str(manifest_path),
            "bundle_root": str(root_path),
            "entry_file": entry_file,
            "entry_path": str(entry_path),
            "files": [entry_file],
            "metadata": {
                "model": repr(model),
                "has_mesh": mesh is not None,
            },
        }

    def test_run_workflow_completes(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(
            ws.workspace_id,
            "core.logger",
            "Logger",
            100,
            0,
            properties={"message": "ok"},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_test",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )
        events = []
        while not event_queue.empty():
            events.append(event_queue.get())
        event_types = [event["type"] for event in events]
        self.assertIn("run_started", event_types)
        self.assertIn("node_started", event_types)
        self.assertIn("node_settled", event_types)
        self.assertIn("run_completed", event_types)

    def test_workflow_runner_binds_prepared_data_type_catalog_before_execution(
        self,
    ) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        command = _catalog_start_run_command(
            {
                "run_id": "run_catalog_binding",
                "workspace_id": workspace.workspace_id,
                "runtime_snapshot": self._runtime_snapshot(model),
            }
        )
        prepared = prepare_runtime(command)
        services = WorkerServices()

        with mock.patch(
            "ea_node_editor.execution.worker_runner.prepare_runtime",
            return_value=prepared,
        ):
            runner = WorkflowRunner(
                command,
                queue.Queue(),
                worker_services=services,
            )

        self.assertIs(services.data_types, prepared.registry.data_types)
        self.assertIsNone(runner._preflight_error)

    def test_workflow_runner_catalog_mismatch_precedes_executor_and_node_events(
        self,
    ) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        model.add_node(
            workspace.workspace_id,
            "core.logger",
            "Logger",
            0,
            0,
            properties={"message": "never runs"},
        )
        desktop_catalog = _revision_catalog("desktop-v2")
        fingerprint, revisions = catalog_agreement(desktop_catalog)
        command = StartRunCommand(
            run_id="run_catalog_mismatch",
            workspace_id=workspace.workspace_id,
            runtime_snapshot=self._runtime_snapshot(model),
            catalog_fingerprint=fingerprint,
            catalog_revisions=revisions,
        )
        event_queue: queue.Queue = queue.Queue()
        services = WorkerServices()

        with (
            mock.patch(
                "ea_node_editor.execution.worker_runner.prepare_runtime",
            ) as prepare,
            mock.patch(
                "ea_node_editor.execution.worker_runner.NodeExecutor",
                side_effect=AssertionError("NodeExecutor must not be constructed"),
            ) as executor,
        ):
            runner = WorkflowRunner(
                command,
                event_queue,
                worker_services=services,
            )
            runner.run()

        prepare.assert_not_called()
        executor.assert_not_called()
        with self.assertRaisesRegex(ValueError, "active data-type catalog"):
            _ = services.data_types
        events = self._drain_events(event_queue)
        self.assertTrue(
            any(event.get("type") == "run_failed" for event in events)
        )
        self.assertFalse(
            any(event.get("type") == "node_started" for event in events)
        )
        failure = next(
            event for event in events if event.get("type") == "run_failed"
        )
        self.assertIn("desktop=", str(failure.get("error", "")))
        self.assertIn("worker=", str(failure.get("error", "")))
        self.assertNotIn("source_label", str(failure.get("error", "")))
        self.assertEqual(failure.get("traceback"), "")
        run_state = next(
            event
            for event in events
            if event.get("type") == "run_state"
            and event.get("reason") == "catalog_mismatch"
        )
        self.assertEqual(run_state.get("reason"), "catalog_mismatch")

    def test_dpf_viewer_alias_requires_semantic_type_and_handle_kind(self) -> None:
        registry = build_default_registry()
        services = WorkerServices()
        services.bind_data_types(registry.data_types)
        fields_ref = RuntimeHandleRef(
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            schema_version=1,
            handle_id="fields_valid",
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="run:viewer_alias",
            worker_generation=1,
        )
        spoofed_ref = RuntimeHandleRef(
            data_type_id=DPF_MODEL_DATA_TYPE,
            schema_version=1,
            handle_id="fields_spoofed",
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="run:viewer_alias",
            worker_generation=1,
        )
        wrong_kind_ref = RuntimeHandleRef(
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            schema_version=1,
            handle_id="fields_wrong_kind",
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="run:viewer_alias",
            worker_generation=1,
        )
        command = OpenViewerSessionCommand(
            request_id="viewer_alias",
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id="session_alias",
            data_refs={
                "fields": spoofed_ref,
                "field_data": fields_ref,
                "result": wrong_kind_ref,
            },
        )
        event_queue: queue.Queue = queue.Queue()

        with mock.patch.object(
            services.viewer_session_service,
            "handle_command",
            return_value=ViewerSessionOpenedEvent(
                request_id="viewer_alias",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_alias",
            ),
        ) as handle_command:
            dispatch_viewer_command(
                command,
                event_queue=event_queue,
                worker_services=services,
            )

        normalized = handle_command.call_args.args[0]
        self.assertEqual(normalized.data_refs["fields"], spoofed_ref)
        self.assertEqual(normalized.data_refs["fields_container"], fields_ref)
        self.assertEqual(normalized.data_refs["result"], wrong_kind_ref)

    def test_run_workflow_emits_tabular_warning_logs_and_node_settled_warning_state(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        tabular = model.add_node(
            ws.workspace_id,
            "tests.tabular_warning_source",
            "Tabular Warning Source",
            100,
            0,
        )

        registry = build_default_registry()
        registry.register(_TabularWarningSourcePlugin)
        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_tabular_warnings",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

        events = self._drain_events(event_queue)
        completed_event = next(
            event
            for event in events
            if event.get("type") == "node_settled"
            and event.get("node_id") == tabular.node_id
        )
        self.assertEqual(
            tuple(completed_event.get("warnings", ())), _TABULAR_WARNING_TEXTS
        )
        round_tripped = dict_to_event(completed_event)
        self.assertIsInstance(round_tripped, NodeSettledEvent)
        self.assertEqual(round_tripped.warnings, _TABULAR_WARNING_TEXTS)

        warning_messages = [
            str(event.get("message", ""))
            for event in events
            if event.get("type") == "log" and event.get("level") == "warning"
        ]
        for expected in _TABULAR_WARNING_TEXTS:
            self.assertTrue(
                any(expected in message for message in warning_messages), expected
            )
        self.assertNotIn("run_failed", [event.get("type") for event in events])
        self.assertIn("run_completed", [event.get("type") for event in events])

    def test_start_run_command_round_trips_execution_backend_selection(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        runtime_snapshot = self._runtime_snapshot(model)
        selection = ExecutionBackendSelection(
            backend_id=TRUSTED_IN_PROCESS_BACKEND,
            isolation="in_process",
            reason="unit_test",
            trusted_in_process=True,
        )

        command = StartRunCommand(
            run_id="run_backend_roundtrip",
            workspace_id=ws.workspace_id,
            runtime_snapshot=runtime_snapshot,
            execution_backend=selection,
        )
        catalog = build_default_registry().data_types
        round_tripped = _catalog_start_run_command(
            command_to_dict(command, catalog=catalog),
            catalog=catalog,
        )

        self.assertEqual(
            round_tripped.execution_backend.backend_id, TRUSTED_IN_PROCESS_BACKEND
        )
        self.assertEqual(round_tripped.execution_backend.isolation, "in_process")
        self.assertEqual(round_tripped.execution_backend.reason, "unit_test")
        self.assertTrue(round_tripped.execution_backend.trusted_in_process)

    def test_prepare_runtime_cache_reuses_safe_registry_and_compiled_workspace(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0)
        runtime_snapshot = self._runtime_snapshot(model)
        command = StartRunCommand(
            run_id="run_cache",
            workspace_id=ws.workspace_id,
            runtime_snapshot=runtime_snapshot,
        )
        cache = RuntimePreparationCache()

        import ea_node_editor.execution.worker_runtime as worker_runtime_module

        with mock.patch.object(
            worker_runtime_module,
            "compile_runtime_snapshot",
            wraps=worker_runtime_module.compile_runtime_snapshot,
        ) as compile_mock:
            first = prepare_runtime(command, cache=cache)
            second = prepare_runtime(command, cache=cache)

        self.assertIs(first.registry, second.registry)
        self.assertIs(first.workspace, second.workspace)
        self.assertIsNot(first.plan, second.plan)
        self.assertEqual(compile_mock.call_count, 1)

    def test_prepare_runtime_uses_one_full_cached_catalog_for_all_node_types(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0)
        runtime_snapshot = self._runtime_snapshot(model)
        command = StartRunCommand(
            run_id="run_builtin_registry",
            workspace_id=ws.workspace_id,
            runtime_snapshot=runtime_snapshot,
        )

        cache = RuntimePreparationCache()
        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            wraps=build_default_registry,
        ) as build_default_registry_mock:
            prepared = prepare_runtime(command, cache=cache)
            builtin_payload = runtime_snapshot.to_document(
                catalog=prepared.registry.data_types
            )
            addon_payload = json.loads(json.dumps(builtin_payload))
            addon_payload["workspaces"][0]["nodes"][0]["type_id"] = (
                "dpf.workflow.result_fields"
            )
            builtin_registry = cache.default_registry()
            addon_registry = cache.default_registry()
            addon_snapshot = RuntimeSnapshot.from_mapping(
                addon_payload,
                catalog=addon_registry.data_types,
            )
            addon_prepared = prepare_runtime(
                StartRunCommand(
                    run_id="run_addon_registry",
                    workspace_id=ws.workspace_id,
                    runtime_snapshot=addon_snapshot,
                ),
                cache=cache,
            )

        self.assertEqual(build_default_registry_mock.call_count, 1)
        self.assertIs(prepared.registry, builtin_registry)
        self.assertIs(builtin_registry, addon_registry)
        self.assertIs(addon_prepared.registry, addon_registry)
        self.assertIsNotNone(
            addon_registry.spec_or_none("dpf.workflow.result_fields")
        )
        self.assertEqual(
            builtin_registry.data_types.fingerprint(),
            addon_registry.data_types.fingerprint(),
        )

    def test_persistent_node_elapsed_time_protocol_run_workflow_emits_timing_metadata(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(
            ws.workspace_id,
            "core.logger",
            "Logger",
            100,
            0,
            properties={"message": "ok"},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        with mock.patch(
            "ea_node_editor.execution.worker_runner.time.time",
            side_effect=[200.0, 200.25],
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_timing_protocol",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

        events = self._drain_events(event_queue)
        started = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_started"
            and str(event.get("node_id", "")) == logger.node_id
        )
        completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("node_id", "")) == logger.node_id
        )

        self.assertEqual(float(started.get("started_at_epoch_ms", -1.0)), 200000.0)
        self.assertEqual(float(completed.get("elapsed_ms", -1.0)), 250.0)
        self.assertIn("outputs", completed)

    def test_persistent_node_elapsed_time_protocol_failed_nodes_emit_settled_timing(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": _decorated_python_script("raise RuntimeError('timing boom')")},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        with mock.patch(
            "ea_node_editor.execution.worker_runner.time.time",
            side_effect=[200.0, 200.25],
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_timing_failure",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

        events = self._drain_events(event_queue)
        started = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_started"
            and str(event.get("node_id", "")) == script.node_id
        )
        settled = self._node_settled(events, script.node_id)

        self.assertEqual(float(started.get("started_at_epoch_ms", -1.0)), 200000.0)
        self.assertEqual(settled.get("status"), "failed")
        self.assertGreaterEqual(float(settled.get("elapsed_ms", -1.0)), 0.0)

    def test_run_workflow_emits_failure(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": _decorated_python_script("raise RuntimeError('boom')")},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_error",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )
        events = []
        while not event_queue.empty():
            events.append(event_queue.get())
        error = self._settled_error(events, script.node_id)
        self.assertEqual(error["node_id"], script.node_id)
        self.assertIn("RuntimeError: boom", str(error["traceback"]))
        self.assertIn("run_completed", [event["type"] for event in events])
        self.assertNotIn("run_failed", [event["type"] for event in events])

    def test_python_script_failure_traceback_is_sanitized_by_default(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": _decorated_python_script("value = 1 / 0")},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_sanitized",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        traceback_text = self._settled_error(events, script.node_id)["traceback"]
        self.assertIn("ZeroDivisionError", traceback_text)
        self.assertIn("<script>", traceback_text)
        self.assertNotIn("ea_node_editor", traceback_text)
        self.assertNotIn("worker_runner", traceback_text)
        self.assertNotIn("core.py", traceback_text)
        leaking_logs = [
            event
            for event in events
            if event["type"] == "log"
            and "ea_node_editor" in str(event.get("message", ""))
        ]
        self.assertEqual(leaking_logs, [])

    def test_tampered_python_script_declaration_fails_at_the_node_with_sanitized_traceback(
        self,
    ) -> None:
        registry = build_default_registry()
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
        )
        snapshot = self._runtime_snapshot(model, registry=registry)
        document = snapshot.to_document(catalog=registry.data_types)
        node_document = next(
            node
            for node in document["workspaces"][0]["nodes"]
            if node["node_id"] == script.node_id
        )
        node_document["properties"]["script"] = "@corex.node\ndef run("
        tampered = RuntimeSnapshot.from_mapping(document, catalog=registry.data_types)

        event_queue: queue.Queue = queue.Queue()
        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_tampered_script",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": tampered,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

        events = self._drain_events(event_queue)
        error = self._settled_error(events, script.node_id)
        traceback_text = str(error["traceback"])
        self.assertEqual(error["node_id"], script.node_id)
        self.assertIn("<script>", traceback_text)
        self.assertIn("PythonScriptDeclarationError", traceback_text)
        self.assertNotIn("ea_node_editor", traceback_text)
        self.assertNotIn("worker_runtime", traceback_text)
        self.assertNotIn("worker_runner", traceback_text)
        self.assertIn("run_completed", [event["type"] for event in events])
        self.assertNotIn("run_failed", [event["type"] for event in events])

    def test_tampered_python_script_unknown_type_fails_at_the_node_without_host_traceback(
        self,
    ) -> None:
        registry = build_default_registry()
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
        )
        snapshot = self._runtime_snapshot(model, registry=registry)
        document = snapshot.to_document(catalog=registry.data_types)
        node_document = next(
            node
            for node in document["workspaces"][0]["nodes"]
            if node["node_id"] == script.node_id
        )
        node_document["properties"]["script"] = '''@corex.node
@corex.output("value", value_type="Missing.Type")
def run(ctx):
    return {}
'''
        tampered = RuntimeSnapshot.from_mapping(document, catalog=registry.data_types)

        event_queue: queue.Queue = queue.Queue()
        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_tampered_script_type",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": tampered,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

        events = self._drain_events(event_queue)
        error = self._settled_error(events, script.node_id)
        traceback_text = str(error["traceback"])
        self.assertEqual(error["node_id"], script.node_id)
        self.assertIn("unknown data-type ID", str(error["error"]))
        self.assertIn("Missing.Type", str(error["error"]))
        self.assertIn("<script>", traceback_text)
        self.assertIn("PythonScriptDeclarationError", traceback_text)
        self.assertNotIn("ea_node_editor", traceback_text)
        self.assertNotIn("worker_runtime", traceback_text)
        self.assertNotIn("worker_runner", traceback_text)
        self.assertIn("run_completed", [event["type"] for event in events])
        self.assertNotIn("run_failed", [event["type"] for event in events])

    def test_python_script_failure_traceback_is_full_in_developer_mode(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": _decorated_python_script("value = 1 / 0")},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_developer_mode",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                    "developer_mode": True,
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        traceback_text = self._settled_error(events, script.node_id)["traceback"]
        self.assertIn("ZeroDivisionError", traceback_text)
        self.assertIn("ea_node_editor", traceback_text)

    def test_run_workflow_emits_failure_for_system_exit(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": _decorated_python_script("raise SystemExit('bye')")},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_system_exit",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        error = self._settled_error(events, script.node_id)
        self.assertEqual(error["node_id"], script.node_id)
        self.assertEqual(error["error"], "bye")
        self.assertIn("SystemExit: bye", str(error["traceback"]))

    def test_run_workflow_emits_failure_for_keyboard_interrupt(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            100,
            0,
            properties={"script": _decorated_python_script("raise KeyboardInterrupt('ctrl c')")},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_keyboard_interrupt",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        error = self._settled_error(events, script.node_id)
        self.assertEqual(error["node_id"], script.node_id)
        self.assertEqual(error["error"], "ctrl c")
        self.assertIn("KeyboardInterrupt: ctrl c", str(error["traceback"]))

    def test_run_workflow_exec_node_pulls_pure_data_dependencies(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        constant = model.add_node(
            ws.workspace_id,
            "core.constant",
            "Constant",
            100,
            -80,
            properties={"value": "from_constant"},
        )
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 200, 0)
        model.add_edge(
            ws.workspace_id, constant.node_id, "value", logger.node_id, "message"
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_dependency_pull",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        started_indexes = {
            str(event.get("node_id", "")): index
            for index, event in enumerate(events)
            if str(event.get("type", "")) == "node_started"
        }
        self.assertIn(constant.node_id, started_indexes)
        self.assertIn(logger.node_id, started_indexes)
        self.assertLess(
            started_indexes[constant.node_id], started_indexes[logger.node_id]
        )

        logger_logs = [
            str(event.get("message", ""))
            for event in events
            if str(event.get("type", "")) == "log"
            and str(event.get("node_id", "")) == logger.node_id
        ]
        self.assertTrue(any("from_constant" in message for message in logger_logs))

    def test_start_run_command_roundtrips_selected_target_fields(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 100, 0)
        runtime_snapshot = self._runtime_snapshot(model)

        command = _catalog_start_run_command(
            {
                "run_id": "run_selected_roundtrip",
                "workspace_id": ws.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "target_node_ids": [logger.node_id, logger.node_id, ""],
                "trigger_publications": {
                    "trigger": {
                        "status": "value",
                        "value": DataTree.from_item("cached"),
                    }
                },
                "trigger_captures": {
                    "trigger": {
                        "status": "empty",
                    }
                },
                "clicked_trigger_node_id": "trigger",
            }
        )
        payload = command_to_dict(command)
        restored = _catalog_start_run_command(payload)

        self.assertEqual(restored.target_node_ids, (logger.node_id,))
        self.assertEqual(
            restored.trigger_publications["trigger"],
            SettledPortResult(status="value", value=DataTree.from_item("cached")),
        )
        self.assertEqual(
            restored.trigger_captures["trigger"],
            SettledPortResult(status="empty"),
        )
        self.assertEqual(restored.clicked_trigger_node_id, "trigger")

    def test_selected_run_pulls_enabled_upstream_without_running_siblings(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            80,
            0,
            properties={"script": _decorated_python_script("return {'result': 'fresh'}")},
        )
        logger = model.add_node(ws.workspace_id, "core.logger", "Logger", 220, 0)
        sibling = model.add_node(
            ws.workspace_id,
            "core.constant",
            "Sibling",
            220,
            120,
        )
        model.add_edge(
            ws.workspace_id, script.node_id, "result", logger.node_id, "message"
        )

        event_queue: queue.Queue = queue.Queue()
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_selected_upstream",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": self._runtime_snapshot(model),
                    "target_node_ids": [logger.node_id],
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        started = [
            str(event.get("node_id", ""))
            for event in events
            if str(event.get("type", "")) == "node_started"
        ]
        self.assertEqual(started, [script.node_id, logger.node_id])
        self.assertNotIn(sibling.node_id, started)
        logger_logs = [
            str(event.get("message", ""))
            for event in events
            if str(event.get("type", "")) == "log"
            and str(event.get("node_id", "")) == logger.node_id
        ]
        self.assertTrue(any("fresh" in message for message in logger_logs))

    def test_parameter_setup_hidden_ordering_context_and_run_state(self) -> None:
        _OPTIMIZATION_CONTEXTS.clear()
        _OPTIMIZATION_EXECUTION_ORDER.clear()
        _OPTIMIZATION_STATE_READS.clear()

        model = GraphModel()
        workspace = model.active_workspace
        pool = model.add_node(
            workspace.workspace_id,
            OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
            "Parameter Pool",
            20,
            20,
        )
        unrelated = model.add_node(
            workspace.workspace_id,
            "core.constant",
            "Unrelated",
            200,
            20,
        )
        setup = model.add_node(
            workspace.workspace_id,
            OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
            "Parameter Setup",
            20,
            160,
        )
        setup.links.append(
            NodeLinkRecord(
                link_id=PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
                kind="node",
                title=PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE,
                target=pool.node_id,
                subtitle="",
                target_workspace_id=workspace.workspace_id,
                target_node_id=pool.node_id,
            )
        )

        registry = _build_optimization_worker_test_registry()
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        first_command = _catalog_start_run_command(
            {
                "run_id": "run_semantic_links_first",
                "workspace_id": workspace.workspace_id,
                "runtime_snapshot": runtime_snapshot,
                "target_node_ids": [pool.node_id],
                "trigger": {},
            },
            catalog=registry.data_types,
        )
        worker_services = WorkerServices()

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            prepared = prepare_runtime(first_command)
            self.assertEqual(
                prepared.plan.scheduled_node_ids,
                {setup.node_id, pool.node_id},
            )
            self.assertEqual(
                prepared.plan.execution_order,
                (setup.node_id, pool.node_id),
            )
            self.assertEqual(prepared.plan.dependency_edges(), ())
            self.assertEqual(prepared.plan.incoming_edges_for(pool.node_id), ())

            first_events: queue.Queue = queue.Queue()
            run_workflow(
                first_command,
                first_events,
                worker_services=worker_services,
            )

            second_command = _catalog_start_run_command(
                {
                    "run_id": "run_semantic_links_second",
                    "workspace_id": workspace.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "target_node_ids": [pool.node_id],
                    "clicked_trigger_node_id": pool.node_id,
                    "trigger": {},
                },
                catalog=registry.data_types,
            )
            clicked_plan = prepare_runtime(second_command).plan
            self.assertEqual(
                clicked_plan.execution_order,
                (setup.node_id, pool.node_id),
            )
            second_events: queue.Queue = queue.Queue()
            run_workflow(
                second_command,
                second_events,
                worker_services=worker_services,
            )

        self.assertEqual(
            [
                node_id
                for run_id, node_id in _OPTIMIZATION_EXECUTION_ORDER
                if run_id == "run_semantic_links_first"
            ],
            [setup.node_id, pool.node_id],
        )
        self.assertNotIn(
            unrelated.node_id,
            {
                node_id
                for _run_id, node_id in _OPTIMIZATION_EXECUTION_ORDER
            },
        )
        self.assertEqual(
            _OPTIMIZATION_STATE_READS["run_semantic_links_first"],
            {"publisher": setup.node_id},
        )
        self.assertIsNone(_OPTIMIZATION_STATE_READS["run_semantic_links_second"])

        setup_context = next(
            context
            for context in _OPTIMIZATION_CONTEXTS
            if context.run_id == "run_semantic_links_first"
            and context.node_id == setup.node_id
        )
        pool_context = next(
            context
            for context in _OPTIMIZATION_CONTEXTS
            if context.run_id == "run_semantic_links_first"
            and context.node_id == pool.node_id
        )
        self.assertEqual(
            tuple(dict(link) for link in setup_context.semantic_links),
            (
                {
                    "id": PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
                    "kind": "node",
                    "title": PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE,
                    "target": pool.node_id,
                    "subtitle": "",
                    "target_workspace_id": workspace.workspace_id,
                    "target_node_id": pool.node_id,
                },
            ),
        )
        self.assertEqual(pool_context.semantic_links, ())
        self.assertEqual(
            dict(setup_context.workspace_node_types),
            {
                pool.node_id: OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
                unrelated.node_id: "core.constant",
                setup.node_id: OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
            },
        )
        self.assertEqual(pool_context.inputs, {})
        self.assertIsNone(setup_context.read_node_state(pool.node_id))
        with self.assertRaises(TypeError):
            setup_context.semantic_links[0]["title"] = "Changed"
        with self.assertRaises(TypeError):
            setup_context.workspace_node_types["unknown"] = "tests.unknown"

    def test_parameter_setup_hidden_ordering_rejects_cycles_and_invalid_links(
        self,
    ) -> None:
        registry = _build_optimization_worker_test_registry()

        cycle_model = GraphModel()
        cycle_workspace = cycle_model.active_workspace
        cycle_pool = cycle_model.add_node(
            cycle_workspace.workspace_id,
            OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
            "Cycle Pool",
            20,
            20,
        )
        cycle_setup = cycle_model.add_node(
            cycle_workspace.workspace_id,
            OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
            "Cycle Setup",
            20,
            160,
        )
        cycle_setup.links.append(
            NodeLinkRecord(
                link_id=PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
                kind="node",
                title=PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE,
                target=cycle_pool.node_id,
                target_workspace_id=cycle_workspace.workspace_id,
                target_node_id=cycle_pool.node_id,
            )
        )
        cycle_model.add_edge(
            cycle_workspace.workspace_id,
            cycle_pool.node_id,
            "reverse",
            cycle_setup.node_id,
            "reverse",
        )
        cycle_runtime_workspace = self._runtime_snapshot(
            cycle_model,
            registry=registry,
        ).workspace(cycle_workspace.workspace_id)
        with self.assertRaisesRegex(ValueError, "Cycle detected"):
            ExecutionPlan(
                cycle_runtime_workspace,
                registry,
                target_node_ids=(cycle_pool.node_id,),
            )

        conflict_model = GraphModel()
        conflict_workspace = conflict_model.active_workspace
        conflict_pool = conflict_model.add_node(
            conflict_workspace.workspace_id,
            OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
            "Conflict Pool",
            20,
            20,
        )
        for index in range(2):
            conflict_setup = conflict_model.add_node(
                conflict_workspace.workspace_id,
                OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
                f"Conflict Setup {index + 1}",
                20,
                160 + index * 120,
            )
            conflict_setup.links.append(
                NodeLinkRecord(
                    link_id=PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
                    kind="node",
                    title=PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE,
                    target=conflict_pool.node_id,
                    target_workspace_id=conflict_workspace.workspace_id,
                    target_node_id=conflict_pool.node_id,
                )
            )
        conflict_runtime_workspace = self._runtime_snapshot(
            conflict_model,
            registry=registry,
        ).workspace(conflict_workspace.workspace_id)
        with self.assertRaises(ValueError) as raised:
            ExecutionPlan(
                conflict_runtime_workspace,
                registry,
                target_node_ids=(conflict_pool.node_id,),
            )
        self.assertEqual(
            str(raised.exception),
            "Conflicting Parameter Setup links target pool node "
            f"{conflict_pool.node_id!r}.",
        )

        for variant in (
            "malformed",
            "duplicate",
            "wrong_type",
            "wrong_workspace",
            "stale",
        ):
            with self.subTest(variant=variant):
                model = GraphModel()
                workspace = model.active_workspace
                target_type_id = (
                    "core.constant"
                    if variant == "wrong_type"
                    else OPTIMIZATION_PARAMETER_POOL_TYPE_ID
                )
                target = model.add_node(
                    workspace.workspace_id,
                    target_type_id,
                    "Target",
                    20,
                    20,
                )
                setup = model.add_node(
                    workspace.workspace_id,
                    OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
                    "Setup",
                    20,
                    160,
                )
                linked_target_id = "missing-node" if variant == "stale" else target.node_id
                record = NodeLinkRecord(
                    link_id=PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
                    kind="node",
                    title=(
                        "Forged title"
                        if variant == "malformed"
                        else PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE
                    ),
                    target=linked_target_id,
                    target_workspace_id=(
                        "other-workspace"
                        if variant == "wrong_workspace"
                        else workspace.workspace_id
                    ),
                    target_node_id=linked_target_id,
                )
                setup.links.append(record)
                if variant == "duplicate":
                    setup.links.append(record.clone())

                runtime_workspace = self._runtime_snapshot(
                    model,
                    registry=registry,
                ).workspace(workspace.workspace_id)
                plan = ExecutionPlan(
                    runtime_workspace,
                    registry,
                    target_node_ids=(target.node_id,),
                )
                self.assertEqual(plan.scheduled_node_ids, {target.node_id})
                self.assertEqual(plan.execution_order, (target.node_id,))
                self.assertEqual(plan.dependency_edges(), ())

    def test_run_workflow_executes_pure_only_workspace_explicitly(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        constant = model.add_node(
            ws.workspace_id,
            "core.constant",
            "Constant",
            80,
            0,
            properties={"value": 42},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_pure_only",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_completed", event_types)
        self.assertTrue(
            any(
                str(event.get("type", "")) == "node_started"
                and str(event.get("node_id", "")) == constant.node_id
                for event in events
            )
        )
        completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("node_id", "")) == constant.node_id
        )
        self.assertEqual(self._settled_output_value(completed, "value"), 42)

    def test_run_workflow_emits_runtime_artifact_ref_payloads_and_resolves_downstream_inputs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_store = ProjectArtifactStore(project_path=None, metadata=None)
            staging_root = artifact_store.ensure_staging_root(
                temporary_root_parent=temp_dir,
            )
            artifact_paths = artifact_store.node_artifact_paths(
                artifact_id="stored_stdout",
                workspace_id="ws_main",
                node_id="artifact_source",
                io_dir="out",
                filename="stored_stdout.txt",
            )
            artifact_path = staging_root.joinpath(
                *Path(artifact_paths.staged_relative_path).parts
            )
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            large_payload = ("stored artifact payload\n" * 4096).strip()
            artifact_path.write_bytes(large_payload.encode("utf-8"))
            register_staged_artifact(
                store=artifact_store,
                artifact_id="stored_stdout",
                payload_path=artifact_path,
                relative_path=artifact_paths.staged_relative_path,
                slot="ws_main:artifact_source:artifact",
                data_type_id=PATH_DATA_TYPE_ID,
                schema_version=1,
                format="txt",
                provenance="corex.test.fixture",
            )

            model = GraphModel()
            ws = model.active_workspace
            source = model.add_node(
                ws.workspace_id, "tests.artifact_source", "Source", 120, 0
            )
            sink = model.add_node(
                ws.workspace_id, "tests.artifact_sink", "Sink", 260, 0
            )
            model.add_edge(
                ws.workspace_id, source.node_id, "artifact", sink.node_id, "artifact"
            )
            model.project.metadata["artifact_store"] = artifact_store.metadata

            registry = build_default_registry()
            registry.register(_ArtifactSourcePlugin)
            registry.register(_ArtifactSinkPlugin)
            runtime_snapshot = self._runtime_snapshot(model, registry=registry)
            event_queue: queue.Queue = queue.Queue()

            with mock.patch(
                "ea_node_editor.nodes.bootstrap.build_default_registry",
                return_value=registry,
            ):
                run_workflow(
                    _catalog_start_run_command(
                        {
                            "run_id": "run_artifact_refs",
                            "workspace_id": ws.workspace_id,
                            "runtime_snapshot": runtime_snapshot,
                            "trigger": {},
                        }
                    ),
                    event_queue,
                )

            events = self._drain_events(event_queue)
            source_completed = next(
                event
                for event in events
                if str(event.get("type", "")) == "node_settled"
                and str(event.get("node_id", "")) == source.node_id
            )
            self.assertEqual(
                self._settled_output_value(source_completed, "summary"),
                "stored output staged",
            )
            self.assertEqual(
                self._settled_output_value(
                    source_completed,
                    "artifact",
                    catalog=registry.data_types,
                ),
                RuntimeArtifactRef.staged(
                    "stored_stdout",
                    data_type_id=PATH_DATA_TYPE_ID,
                    schema_version=1,
                    format="txt",
                    size_bytes=98_303,
                    sha256="595d915dcae2d1d0d4f18dbb624f16d7c17223d9c849e37405c9c053f762a733",
                    provenance="corex.test.fixture",
                ),
            )
            self.assertNotIn(large_payload[:128], json.dumps(source_completed))

            sink_completed = next(
                event
                for event in events
                if str(event.get("type", "")) == "node_settled"
                and str(event.get("node_id", "")) == sink.node_id
            )
            self.assertEqual(
                self._settled_output_value(sink_completed, "resolved_path"),
                str(artifact_path),
            )
            self.assertEqual(
                self._settled_output_value(sink_completed, "artifact_size"),
                len(large_payload),
            )

    def test_run_workflow_emits_tabular_runtime_ref_payloads(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        source = model.add_node(
            ws.workspace_id, "tests.tabular_runtime_source", "Source", 120, 0
        )

        registry = build_default_registry()
        registry.register(_TabularRuntimeSourcePlugin)
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        event_queue: queue.Queue = queue.Queue()

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_tabular_refs",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

        events = self._drain_events(event_queue)
        source_completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("node_id", "")) == source.node_id
        )
        self.assertEqual(
            self._settled_output_value(source_completed, "table"),
            TabularDataRef(
                ref_id="table_runtime_worker",
                resolver_id="tabular.cache",
                backend_id="duckdb",
                row_count=128,
                column_count=6,
            ),
        )
        self.assertEqual(
            self._settled_output_value(source_completed, "array"),
            ArrayDataRef(
                ref_id="array_runtime_worker",
                resolver_id="tabular.cache",
                backend_id="npy_mmap",
                shape=(64, 32),
                dtype="float32",
            ),
        )

    def test_run_workflow_resolves_runtime_handle_refs_and_cleans_run_scope_handles(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        source = model.add_node(
            ws.workspace_id, "tests.handle_source", "Handle Source", 120, 0
        )
        sink = model.add_node(
            ws.workspace_id, "tests.handle_sink", "Handle Sink", 260, 0
        )
        model.add_edge(
            ws.workspace_id, source.node_id, "handle", sink.node_id, "handle"
        )

        registry = build_default_registry()
        _register_test_handle_type(registry)
        registry.register(_HandleSourcePlugin)
        registry.register(_HandleSinkPlugin)
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        event_queue: queue.Queue = queue.Queue()
        worker_services = WorkerServices()

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_handle_refs",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
                worker_services=worker_services,
            )

        events = self._drain_events(event_queue)
        source_completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("node_id", "")) == source.node_id
        )
        handle_ref = self._settled_output_value(
            source_completed,
            "handle",
            catalog=registry.data_types,
        )
        sink_completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("node_id", "")) == sink.node_id
        )
        self.assertEqual(
            self._settled_output_value(sink_completed, "resolved_value"),
            "from_handle",
        )
        self.assertEqual(worker_services.handle_registry.active_handle_count, 0)

        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            worker_services.resolve_handle(handle_ref)

    def test_run_cleanup_warns_without_masking_completed_run(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        model.add_node(
            ws.workspace_id,
            "tests.failing_dispose_handle_source",
            "Failing Dispose Handle Source",
            120,
            0,
        )

        registry = build_default_registry()
        _register_test_handle_type(registry)
        registry.register(_FailingDisposeHandleSourcePlugin)
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        event_queue: queue.Queue = queue.Queue()
        worker_services = WorkerServices()

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_failing_handle_cleanup",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
                worker_services=worker_services,
            )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        warnings = [
            str(event.get("message", ""))
            for event in events
            if event.get("type") == "log" and event.get("level") == "warning"
        ]
        self.assertIn("run_completed", event_types)
        self.assertNotIn("run_failed", event_types)
        self.assertIn(
            "Runtime handle automatic disposal failed.",
            warnings,
        )
        self.assertEqual(worker_services.handle_registry.active_handle_count, 0)

    def test_run_workflow_retains_non_run_scope_handles_when_allowed(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        source = model.add_node(
            ws.workspace_id,
            "tests.persistent_handle_source",
            "Persistent Handle Source",
            120,
            0,
        )

        registry = build_default_registry()
        _register_test_handle_type(registry)
        registry.register(_PersistentHandleSourcePlugin)
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        event_queue: queue.Queue = queue.Queue()
        worker_services = WorkerServices()

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_persistent_handles",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
                worker_services=worker_services,
            )

        events = self._drain_events(event_queue)
        source_completed = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("node_id", "")) == source.node_id
        )
        handle_ref = self._settled_output_value(
            source_completed,
            "handle",
            catalog=registry.data_types,
        )
        self.assertEqual(handle_ref.owner_scope, "cache:tests:persistent_handle")
        self.assertEqual(
            worker_services.resolve_handle(handle_ref, expected_kind="tests.payload"),
            {"value": "cached_handle"},
        )
        self.assertEqual(worker_services.handle_registry.active_handle_count, 1)
        self.assertTrue(worker_services.release_handle(handle_ref))
        self.assertEqual(worker_services.handle_registry.active_handle_count, 0)

    def test_worker_main_resets_services_after_worker_exception(self) -> None:
        registry = build_default_registry()
        _register_test_handle_type(registry)
        worker_services = WorkerServices()
        worker_services.bind_data_types(registry.data_types)
        model = GraphModel()
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        persistent_ref = worker_services.register_handle(
            {"value": "preloaded"},
            data_type_id=_TEST_HANDLE_TYPE_ID,
            kind=_TEST_HANDLE_KIND,
            owner_scope="cache:tests:preloaded",
        )
        command_queue: queue.Queue = queue.Queue()
        event_queue: queue.Queue = queue.Queue()
        command_queue.put(
            command_to_dict(
                StartRunCommand(
                    run_id="run_crash",
                    workspace_id=model.active_workspace.workspace_id,
                    runtime_snapshot=runtime_snapshot,
                ),
                catalog=registry.data_types,
            )
        )
        command_queue.put(command_to_dict(ShutdownCommand()))

        with (
            mock.patch(
                "ea_node_editor.nodes.bootstrap.build_default_registry",
                return_value=registry,
            ),
            mock.patch(
                "ea_node_editor.execution.worker.run_workflow",
                side_effect=RuntimeError("worker boom"),
            ),
        ):
            worker_main(command_queue, event_queue, worker_services=worker_services)

        events = self._drain_events(event_queue)
        failed = [
            event for event in events if str(event.get("type", "")) == "run_failed"
        ]

        self.assertTrue(failed)
        self.assertEqual(failed[0]["run_id"], "run_crash")
        self.assertIn("worker boom", str(failed[0]["error"]))
        self.assertEqual(
            worker_services.worker_generation, persistent_ref.worker_generation + 1
        )

        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            worker_services.resolve_handle(persistent_ref)

    def test_worker_main_resets_services_once_on_normal_shutdown(self) -> None:
        registry = build_default_registry()
        _register_test_handle_type(registry)
        worker_services = WorkerServices()
        worker_services.bind_data_types(registry.data_types)
        disposed: list[str] = []
        persistent_ref = worker_services.register_handle(
            {"value": "preloaded"},
            data_type_id=_TEST_HANDLE_TYPE_ID,
            kind=_TEST_HANDLE_KIND,
            owner_scope="cache:tests:preloaded",
            dispose=lambda: disposed.append("disposed"),
        )
        previous_generation = worker_services.worker_generation
        command_queue: queue.Queue = queue.Queue()
        event_queue: queue.Queue = queue.Queue()
        command_queue.put(command_to_dict(ShutdownCommand()))

        worker_main(command_queue, event_queue, worker_services=worker_services)

        self.assertEqual(disposed, ["disposed"])
        self.assertEqual(
            worker_services.worker_generation,
            previous_generation + 1,
        )
        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            worker_services.resolve_handle(persistent_ref)

    def test_worker_main_routes_viewer_commands_during_run_and_after_completion(
        self,
    ) -> None:
        _WAIT_NODE_ENTERED.clear()
        _WAIT_NODE_RELEASE.clear()
        command_queue: queue.Queue = queue.Queue()
        event_queue: queue.Queue = queue.Queue()
        worker_services = dpf_worker_services()
        registry = build_default_registry()
        materialize_calls: list[dict[str, object]] = []
        thread: threading.Thread | None = None

        model = GraphModel()
        ws = model.active_workspace
        source = model.add_node(
            ws.workspace_id, "tests.viewer_source", "Viewer Source", 120, 0
        )
        wait_node = model.add_node(
            ws.workspace_id, "tests.viewer_wait", "Viewer Wait", 260, 0
        )
        model.add_edge(
            ws.workspace_id,
            source.node_id,
            "fields_container",
            wait_node.node_id,
            "dependency",
        )

        registry = build_default_registry()
        registry.register(_ViewerSourcePlugin)
        registry.register(_ViewerWaitPlugin)
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            with (
                mock.patch.object(
                    worker_services.dpf_runtime_service,
                    "materialize_viewer_dataset",
                    side_effect=self._fake_viewer_materialize(
                        worker_services, materialize_calls
                    ),
                ),
                mock.patch.object(
                    worker_services.dpf_runtime_service,
                    "export_viewer_transport_bundle",
                    side_effect=self._fake_viewer_transport_bundle,
                ),
            ):
                thread = threading.Thread(
                    target=worker_main,
                    args=(command_queue, event_queue),
                    kwargs={"worker_services": worker_services},
                    daemon=True,
                )
                thread.start()
                collected_events: list[dict[str, object]] = []
                try:
                    command_queue.put(
                        command_to_dict(
                            StartRunCommand(
                                run_id="run_viewer_worker",
                                workspace_id=ws.workspace_id,
                                runtime_snapshot=runtime_snapshot,
                            ),
                            catalog=registry.data_types,
                        )
                    )

                    source_completed = self._wait_for_event(
                        event_queue,
                        lambda event: (
                            str(event.get("type", "")) == "node_settled"
                            and str(event.get("node_id", "")) == source.node_id
                        ),
                        timeout=6.0,
                        collected=collected_events,
                    )
                    self.assertIsNotNone(source_completed)
                    self.assertTrue(_WAIT_NODE_ENTERED.wait(timeout=6.0))
                    if source_completed is None:
                        self.fail(
                            "Expected viewer source outputs before sending session commands"
                        )

                    fields_ref = self._settled_output_value(
                        source_completed,
                        "fields_container",
                        catalog=registry.data_types,
                    )
                    model_ref = self._settled_output_value(
                        source_completed,
                        "model",
                        catalog=registry.data_types,
                    )

                    open_command = OpenViewerSessionCommand(
                        request_id="viewer_req_open",
                        workspace_id=ws.workspace_id,
                        node_id="node_viewer",
                        session_id="session_worker",
                        backend_id="dpf_embedded",
                        data_refs={"fields_container": fields_ref, "model": model_ref},
                        summary={"result_name": "displacement"},
                        options={"live_mode": "full"},
                    )
                    transported = dict_to_command(
                        command_to_dict(open_command, catalog=registry.data_types),
                        catalog=registry.data_types,
                    )
                    self.assertEqual(
                        worker_services.resolve_handle(
                            transported.data_refs["fields_container"],
                            expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                        ),
                        {"viewer": "fields"},
                    )
                    command_queue.put(
                        command_to_dict(open_command, catalog=registry.data_types)
                    )
                    opened = self._wait_for_event(
                        event_queue,
                        lambda event: (
                            str(event.get("type", "")) == "viewer_session_opened"
                        ),
                        timeout=6.0,
                        collected=collected_events,
                    )
                    self.assertIsNotNone(opened)
                    if opened is None:
                        self.fail("Expected viewer_session_opened event")
                    self.assertEqual(opened["backend_id"], "dpf_embedded")
                    self.assertEqual(opened["live_open_status"], "blocked")
                    self.assertEqual(opened["summary"]["cache_state"], "proxy_ready")
                    self.assertEqual(opened["options"]["session_state"], "open")
                    self.assertEqual(opened["options"]["live_mode"], "proxy")
                    viewer_owner_scope = worker_services.viewer_session_service._sessions[  # noqa: SLF001
                        (ws.workspace_id, "session_worker")
                    ].owner_scope

                    command_queue.put(
                        command_to_dict(
                            UpdateViewerSessionCommand(
                                request_id="viewer_req_update",
                                workspace_id=ws.workspace_id,
                                node_id="node_viewer",
                                session_id="session_worker",
                                summary={"camera": {"zoom": 1.1}},
                                options={"selection": {"set_ids": [3]}},
                            ),
                            catalog=registry.data_types,
                        )
                    )
                    updated = self._wait_for_event(
                        event_queue,
                        lambda event: (
                            str(event.get("type", "")) == "viewer_session_updated"
                        ),
                        timeout=6.0,
                        collected=collected_events,
                    )
                    self.assertIsNotNone(updated)

                    _WAIT_NODE_RELEASE.set()
                    completed = self._wait_for_event(
                        event_queue,
                        lambda event: (
                            str(event.get("type", "")) == "run_completed"
                            and str(event.get("run_id", "")) == "run_viewer_worker"
                        ),
                        timeout=6.0,
                        collected=collected_events,
                    )
                    self.assertIsNotNone(completed)
                    if completed is None:
                        self.fail("Expected run completion after releasing wait node")

                    with self.assertRaisesRegex(
                        StaleHandleError,
                        "owner_scope is stale",
                    ):
                        worker_services.resolve_handle(fields_ref)
                    with self.assertRaisesRegex(
                        StaleHandleError,
                        "owner_scope is stale",
                    ):
                        worker_services.resolve_handle(model_ref)

                    command_queue.put(
                        command_to_dict(
                            MaterializeViewerDataCommand(
                                request_id="viewer_req_materialize",
                                workspace_id=ws.workspace_id,
                                node_id="node_viewer",
                                session_id="session_worker",
                                options={
                                    "output_profile": "both",
                                    "export_formats": ["png"],
                                },
                            ),
                            catalog=registry.data_types,
                        )
                    )
                    materialized = self._wait_for_event(
                        event_queue,
                        lambda event: (
                            str(event.get("type", "")) == "viewer_data_materialized"
                        ),
                        timeout=6.0,
                        collected=collected_events,
                    )
                    self.assertIsNotNone(materialized)
                    if materialized is None:
                        self.fail("Expected viewer_data_materialized event")
                    self.assertEqual(len(materialize_calls), 1)
                    self.assertEqual(materialize_calls[0]["output_profile"], "both")
                    self.assertEqual(
                        materialize_calls[0]["artifact_key"],
                        "node_viewer_session_worker",
                    )
                    self.assertEqual(
                        materialize_calls[0]["camera_state"], {"zoom": 1.1}
                    )
                    self.assertEqual(
                        materialize_calls[0]["fields_owner_scope"],
                        viewer_owner_scope,
                    )
                    self.assertEqual(
                        materialize_calls[0]["model_owner_scope"],
                        viewer_owner_scope,
                    )
                    self.assertIn("dataset", materialized["data_refs"])
                    self.assertIn("png", materialized["data_refs"])
                    self.assertEqual(materialized["backend_id"], "dpf_embedded")
                    self.assertEqual(
                        materialized["transport"]["kind"], "dpf_transport_bundle"
                    )
                    self.assertTrue(
                        Path(materialized["transport"]["manifest_path"]).is_file()
                    )
                    self.assertTrue(
                        Path(materialized["transport"]["entry_path"]).is_file()
                    )
                    self.assertGreaterEqual(int(materialized["transport_revision"]), 1)
                    self.assertEqual(materialized["live_open_status"], "ready")
                    self.assertEqual(
                        materialized["summary"]["cache_state"], "live_ready"
                    )
                    self.assertEqual(
                        materialized["summary"]["transport_revision"],
                        materialized["transport_revision"],
                    )
                    self.assertEqual(
                        materialized["options"]["transport_revision"],
                        materialized["transport_revision"],
                    )

                    opened_index = next(
                        index
                        for index, event in enumerate(collected_events)
                        if str(event.get("type", "")) == "viewer_session_opened"
                    )
                    updated_index = next(
                        index
                        for index, event in enumerate(collected_events)
                        if str(event.get("type", "")) == "viewer_session_updated"
                    )
                    completed_index = next(
                        index
                        for index, event in enumerate(collected_events)
                        if str(event.get("type", "")) == "run_completed"
                        and str(event.get("run_id", "")) == "run_viewer_worker"
                    )
                    self.assertLess(opened_index, completed_index)
                    self.assertLess(updated_index, completed_index)

                    command_queue.put(
                        command_to_dict(
                            CloseViewerSessionCommand(
                                request_id="viewer_req_close",
                                workspace_id=ws.workspace_id,
                                node_id="node_viewer",
                                session_id="session_worker",
                                options={
                                    "reason": "node_hidden",
                                    "release_handles": True,
                                },
                            ),
                            catalog=registry.data_types,
                        )
                    )
                    closed = self._wait_for_event(
                        event_queue,
                        lambda event: (
                            str(event.get("type", "")) == "viewer_session_closed"
                        ),
                        timeout=6.0,
                        collected=collected_events,
                    )
                    self.assertIsNotNone(closed)
                finally:
                    _WAIT_NODE_RELEASE.set()
                    command_queue.put(command_to_dict(ShutdownCommand()))
                    if thread is not None:
                        thread.join(timeout=6.0)
                        self.assertFalse(thread.is_alive())

    def test_worker_main_routes_serializable_viewer_query_command_and_result(
        self,
    ) -> None:
        command_queue: queue.Queue = queue.Queue()
        event_queue: queue.Queue = queue.Queue()
        worker_services = WorkerServices()
        worker_services.bind_data_types(build_default_registry().data_types)
        backend = worker_services.viewer_backend_registry.resolve("corex_scene")

        with mock.patch.object(
            backend,
            "query",
            return_value=ViewerBackendQueryResult(
                supported=True,
                value={"distance": 5.0, "length_unit": "mm"},
            ),
        ):
            thread = threading.Thread(
                target=worker_main,
                args=(command_queue, event_queue),
                kwargs={"worker_services": worker_services},
                daemon=True,
            )
            thread.start()
            try:
                command_queue.put(
                    command_to_dict(
                        OpenViewerSessionCommand(
                            request_id="viewer_query_open",
                            workspace_id="ws_query",
                            node_id="node_viewer",
                            session_id="session_query",
                            backend_id="corex_scene",
                        )
                    )
                )
                opened = self._wait_for_event(
                    event_queue,
                    lambda event: event.get("type") == "viewer_session_opened",
                    timeout=6.0,
                )
                self.assertIsNotNone(opened)

                command_queue.put(
                    command_to_dict(
                        QueryViewerSessionCommand(
                            request_id="viewer_query_distance",
                            workspace_id="ws_query",
                            node_id="node_viewer",
                            session_id="session_query",
                            backend_id="corex_scene",
                            query_type="distance",
                            payload={"point_a": [0, 0, 0], "point_b": [3, 4, 0]},
                        )
                    )
                )
                queried = self._wait_for_event(
                    event_queue,
                    lambda event: event.get("type") == "viewer_query_result",
                    timeout=6.0,
                )
                self.assertIsNotNone(queried)
                if queried is None:
                    self.fail("Expected viewer_query_result event")
                self.assertEqual(queried["request_id"], "viewer_query_distance")
                self.assertTrue(queried["supported"])
                self.assertEqual(queried["value"]["distance"], 5.0)
            finally:
                command_queue.put(command_to_dict(ShutdownCommand()))
                thread.join(timeout=6.0)
                self.assertFalse(thread.is_alive())

    def test_worker_main_invalidates_cached_viewer_sessions_on_rerun(self) -> None:
        command_queue: queue.Queue = queue.Queue()
        event_queue: queue.Queue = queue.Queue()
        worker_services = dpf_worker_services()
        registry = build_default_registry()

        model = GraphModel()
        ws = model.active_workspace
        runtime_snapshot = self._runtime_snapshot(model)

        fields_ref = worker_services.register_handle(
            {"viewer": "fields"},
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:viewer_fields",
        )
        model_ref = worker_services.register_handle(
            {"viewer": "model"},
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="cache:tests:viewer_model",
        )

        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            thread = threading.Thread(
                target=worker_main,
                args=(command_queue, event_queue),
                kwargs={"worker_services": worker_services},
                daemon=True,
            )
            thread.start()
            collected_events: list[dict[str, object]] = []
            try:
                command_queue.put(
                    command_to_dict(
                        StartRunCommand(
                            run_id="run_viewer_cache_a",
                            workspace_id=ws.workspace_id,
                            runtime_snapshot=runtime_snapshot,
                        ),
                        catalog=registry.data_types,
                    )
                )
                completed_a = self._wait_for_event(
                    event_queue,
                    lambda event: (
                        str(event.get("type", "")) == "run_completed"
                        and str(event.get("run_id", "")) == "run_viewer_cache_a"
                    ),
                    timeout=6.0,
                    collected=collected_events,
                )
                self.assertIsNotNone(completed_a)

                command_queue.put(
                    command_to_dict(
                        OpenViewerSessionCommand(
                            request_id="viewer_req_open",
                            workspace_id=ws.workspace_id,
                            node_id="node_viewer",
                            session_id="session_rerun",
                            data_refs={
                                "fields_container": fields_ref,
                                "model": model_ref,
                            },
                        ),
                        catalog=registry.data_types,
                    )
                )
                opened = self._wait_for_event(
                    event_queue,
                    lambda event: str(event.get("type", "")) == "viewer_session_opened",
                    timeout=6.0,
                    collected=collected_events,
                )
                self.assertIsNotNone(opened)

                command_queue.put(
                    command_to_dict(
                        StartRunCommand(
                            run_id="run_viewer_cache_b",
                            workspace_id=ws.workspace_id,
                            runtime_snapshot=runtime_snapshot,
                        ),
                        catalog=registry.data_types,
                    )
                )
                completed_b = self._wait_for_event(
                    event_queue,
                    lambda event: (
                        str(event.get("type", "")) == "run_completed"
                        and str(event.get("run_id", "")) == "run_viewer_cache_b"
                    ),
                    timeout=6.0,
                    collected=collected_events,
                )
                self.assertIsNotNone(completed_b)

                command_queue.put(
                    command_to_dict(
                        MaterializeViewerDataCommand(
                            request_id="viewer_req_materialize",
                            workspace_id=ws.workspace_id,
                            node_id="node_viewer",
                            session_id="session_rerun",
                            options={"output_profile": "memory"},
                        ),
                        catalog=registry.data_types,
                    )
                )
                failed = self._wait_for_event(
                    event_queue,
                    lambda event: str(event.get("type", "")) == "viewer_session_failed",
                    timeout=6.0,
                    collected=collected_events,
                )
                self.assertIsNotNone(failed)
                self.assertIn("invalidated", str(failed.get("error", "")))
            finally:
                command_queue.put(command_to_dict(ShutdownCommand()))
                thread.join(timeout=6.0)
                self.assertFalse(thread.is_alive())

    def test_worker_protocol_normalizes_legacy_dpf_fields_alias_before_viewer_session(
        self,
    ) -> None:
        event_queue: queue.Queue = queue.Queue()
        worker_services = dpf_worker_services()
        fields_ref = worker_services.register_handle(
            {"viewer": "fields"},
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="run:viewer_alias",
        )
        model_ref = worker_services.register_handle(
            {"viewer": "model"},
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="run:viewer_alias",
        )

        dispatch_viewer_command(
            OpenViewerSessionCommand(
                request_id="viewer_alias_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_alias",
                data_refs={"fields": fields_ref, "model": model_ref},
            ),
            event_queue=event_queue,
            worker_services=worker_services,
        )

        opened = event_queue.get_nowait()
        self.assertEqual(opened["type"], "viewer_session_opened")
        record = worker_services.viewer_session_service._sessions[
            ("ws_main", "session_alias")
        ]  # noqa: SLF001
        self.assertIn("fields_container", record.source_refs)
        self.assertNotIn("fields", record.source_refs)

    def test_worker_protocol_reports_viewer_close_cleanup_failure_then_allows_retry(
        self,
    ) -> None:
        event_queue: queue.Queue = queue.Queue()
        worker_services = dpf_worker_services()
        disposed: list[str] = []

        def fail_disposal() -> None:
            disposed.append("failed")
            raise RuntimeError("private disposal detail")

        fields_ref = worker_services.register_handle(
            {"viewer": "fields"},
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_close_failure",
            dispose=fail_disposal,
        )
        model_ref = worker_services.register_handle(
            {"viewer": "model"},
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            run_id="run_close_failure",
            dispose=lambda: disposed.append("successful"),
        )
        worker_services.viewer_session_service.open_session(
            OpenViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_close_failure",
                data_refs={
                    "fields_container": fields_ref,
                    "model": model_ref,
                },
            )
        )
        worker_services.cleanup_run("run_close_failure")
        close_command = CloseViewerSessionCommand(
            request_id="viewer_close_failure",
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id="session_close_failure",
        )

        dispatch_viewer_command(
            close_command,
            event_queue=event_queue,
            worker_services=worker_services,
        )

        failed = event_queue.get_nowait()
        self.assertEqual(failed["type"], "viewer_session_failed")
        self.assertEqual(failed["error"], "Viewer session cleanup failed.")
        self.assertNotIn("private disposal detail", failed["error"])
        record = worker_services.viewer_session_service._sessions[  # noqa: SLF001
            ("ws_main", "session_close_failure")
        ]
        self.assertEqual(record.session_state, "closed")
        self.assertCountEqual(disposed, ["failed", "successful"])

        dispatch_viewer_command(
            close_command,
            event_queue=event_queue,
            worker_services=worker_services,
        )

        closed = event_queue.get_nowait()
        self.assertEqual(closed["type"], "viewer_session_closed")
        self.assertEqual(closed["options"]["session_state"], "closed")
        self.assertCountEqual(disposed, ["failed", "successful"])

    def test_dpf_viewer_backend_requires_canonical_fields_container_source_key(
        self,
    ) -> None:
        worker_services = dpf_worker_services()
        backend = DpfViewerSessionMaterializationBackend(worker_services)
        fields_ref = worker_services.register_handle(
            {"viewer": "fields"},
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:viewer_session:ws_main:session_alias",
        )
        model_ref = worker_services.register_handle(
            {"viewer": "model"},
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="cache:viewer_session:ws_main:session_alias",
        )

        with self.assertRaisesRegex(ValueError, "missing cached fields/model refs"):
            backend.materialize(
                ViewerSessionMaterializationRequest(
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_alias",
                    owner_scope="cache:viewer_session:ws_main:session_alias",
                    source_refs={"fields": fields_ref, "model": model_ref},
                    session_options={},
                    request_options={},
                    output_profile="memory",
                )
            )

    def test_run_workflow_runs_ready_isolated_active_nodes(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(
            ws.workspace_id,
            "core.logger",
            "Logger",
            120,
            0,
            properties={"message": "should_run"},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_no_exec_trigger",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_completed", event_types)
        self.assertTrue(
            any(
                str(event.get("type", "")) == "node_started"
                and str(event.get("node_id", "")) == logger.node_id
                for event in events
            )
        )
        self.assertTrue(
            any(
                str(event.get("type", "")) == "log"
                and str(event.get("node_id", "")) == logger.node_id
                for event in events
            )
        )

    def test_run_workflow_manual_ui_trigger_preserves_current_trigger_payload(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        script = model.add_node(
            ws.workspace_id,
            "core.python_script",
            "Script",
            160,
            0,
            properties={"script": _decorated_python_script("return {'result': ctx.trigger}")},
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_manual_trigger",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {
                        "kind": "manual",
                        "workflow_settings": {"general": {"project_name": "Demo"}},
                    },
                }
            ),
            event_queue,
        )

        events = self._drain_events(event_queue)
        settled = self._node_settled(events, script.node_id)
        self.assertEqual(
            self._settled_output_value(settled, "result"),
            {
                "kind": "manual",
                "workflow_settings": {"general": {"project_name": "Demo"}},
            },
        )

    def test_run_workflow_requires_runtime_snapshot_payload(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(
            ws.workspace_id,
            "core.logger",
            "Logger",
            100,
            0,
            properties={"message": "legacy project doc"},
        )

        event_queue: queue.Queue = queue.Queue()
        with self.assertRaisesRegex(ValueError, "requires runtime_snapshot"):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_missing_snapshot",
                        "workspace_id": ws.workspace_id,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

    def test_run_workflow_emits_pause_resume_and_stop_transitions(self) -> None:
        model = GraphModel()
        ws = model.active_workspace
        logger = model.add_node(
            ws.workspace_id,
            "core.logger",
            "Logger",
            100,
            0,
            properties={"message": "ok"},
        )

        runtime_snapshot = self._runtime_snapshot(model)

        pause_event_queue: queue.Queue = queue.Queue()
        pause_command_queue: queue.Queue = queue.Queue()
        pause_command_queue.put({"type": "pause_run", "run_id": "run_pause"})
        pause_command_queue.put({"type": "resume_run", "run_id": "run_pause"})
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_pause",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            pause_event_queue,
            command_queue=pause_command_queue,
        )
        pause_events = []
        while not pause_event_queue.empty():
            pause_events.append(pause_event_queue.get())
        pause_states = [
            (event.get("state"), event.get("transition"))
            for event in pause_events
            if event.get("type") == "run_state"
        ]
        self.assertIn(("paused", "pause"), pause_states)
        self.assertIn(("running", "resume"), pause_states)
        self.assertTrue(
            any(event.get("type") == "run_completed" for event in pause_events)
        )

        stop_event_queue: queue.Queue = queue.Queue()
        stop_command_queue: queue.Queue = queue.Queue()
        stop_command_queue.put({"type": "stop_run", "run_id": "run_stop"})
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_stop",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            stop_event_queue,
            command_queue=stop_command_queue,
        )
        stop_events = []
        while not stop_event_queue.empty():
            stop_events.append(stop_event_queue.get())
        self.assertTrue(
            any(event.get("type") == "run_stopped" for event in stop_events)
        )
        self.assertFalse(
            any(event.get("type") == "node_started" for event in stop_events)
        )

    def test_run_workflow_streams_process_run_output_before_node_completion(
        self,
    ) -> None:
        model = GraphModel()
        ws = model.active_workspace
        process_node = model.add_node(
            ws.workspace_id,
            "io.process_run",
            "Process",
            100,
            0,
            properties={
                "command": sys.executable,
                "args": [
                    "-c",
                    (
                        "import sys, time\n"
                        "print('tick_worker_0', flush=True)\n"
                        "time.sleep(0.15)\n"
                        "print('tick_worker_1', flush=True)\n"
                        "print('warn_worker_0', file=sys.stderr, flush=True)\n"
                    ),
                ],
                "timeout_sec": 5.0,
                "shell": False,
                "fail_on_nonzero": True,
                "env": {},
                "encoding": "utf-8",
                "cwd": "",
            },
        )

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model)
        run_workflow(
            _catalog_start_run_command(
                {
                    "run_id": "run_stream_worker",
                    "workspace_id": ws.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                }
            ),
            event_queue,
        )

        events = []
        while not event_queue.empty():
            events.append(event_queue.get())

        streamed_logs = [
            event
            for event in events
            if event.get("type") == "log"
            and event.get("node_id") == process_node.node_id
        ]
        self.assertTrue(
            any(
                "tick_worker_0" in str(event.get("message", ""))
                for event in streamed_logs
            )
        )
        self.assertTrue(
            any(
                "tick_worker_1" in str(event.get("message", ""))
                for event in streamed_logs
            )
        )
        self.assertTrue(
            any(
                "warn_worker_0" in str(event.get("message", ""))
                for event in streamed_logs
            )
        )

        log_indexes = [
            index
            for index, event in enumerate(events)
            if event.get("type") == "log"
            and event.get("node_id") == process_node.node_id
        ]
        completed_indexes = [
            index
            for index, event in enumerate(events)
            if event.get("type") == "node_settled"
            and event.get("node_id") == process_node.node_id
        ]
        self.assertTrue(log_indexes, "Expected streamed log events for process node")
        self.assertTrue(completed_indexes, "Expected process node completion event")
        self.assertLess(min(log_indexes), min(completed_indexes))

    def test_run_workflow_treats_passive_only_workspace_as_successful_no_op(
        self,
    ) -> None:
        registry = build_default_registry()
        registry.register(_PassiveNotePlugin)

        model = GraphModel()
        ws = model.active_workspace
        model.add_node(ws.workspace_id, "tests.passive_note", "Note A", 0, 0)
        model.add_node(ws.workspace_id, "tests.passive_note", "Note B", 240, 0)

        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = self._runtime_snapshot(model, registry=registry)
        with mock.patch(
            "ea_node_editor.nodes.bootstrap.build_default_registry",
            return_value=registry,
        ):
            run_workflow(
                _catalog_start_run_command(
                    {
                        "run_id": "run_passive_only",
                        "workspace_id": ws.workspace_id,
                        "runtime_snapshot": runtime_snapshot,
                        "trigger": {},
                    }
                ),
                event_queue,
            )

        events = self._drain_events(event_queue)
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_started", event_types)
        self.assertIn("run_completed", event_types)
        self.assertNotIn("run_failed", event_types)
        self.assertFalse(
            any(str(event.get("type", "")) == "node_started" for event in events)
        )


if __name__ == "__main__":
    unittest.main()
