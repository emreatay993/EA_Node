from __future__ import annotations

import copy
import json
import threading

import pytest

from ea_node_editor.execution import protocol
from ea_node_editor.execution.client import (
    ExecutionBackendClient,
    _ExecutionClientCommon,
)
from ea_node_editor.execution.headless_runtime import CorexRuntime, ExecutionRequest
from ea_node_editor.execution.protocol import (
    StartRunCommand,
    command_to_dict,
    dict_to_command,
    runtime_registry_fingerprint,
)
from ea_node_editor.execution.runtime_dto import RuntimeWorkspace
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.validated_mutation import ValidatedGraphMutation
from ea_node_editor.nodes.function_plugin import (
    EMPTY_PLUGIN_FINGERPRINT,
    PluginBundleRef,
    PythonFunctionRef,
)
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import DataTypeCatalog

_BUNDLE_DIGEST = "a" * 64
_SOURCE_DIGEST = "b" * 64
_PLUGIN_FINGERPRINT = "c" * 64


def _snapshot() -> RuntimeSnapshot:
    return RuntimeSnapshot(
        schema_version=1,
        active_workspace_id="ws",
        workspace_order=("ws",),
        workspaces=(RuntimeWorkspace(document_fields={"workspace_id": "ws"}),),
    )


def _bundle(generation_root) -> PluginBundleRef:  # noqa: ANN001
    generation = generation_root / _BUNDLE_DIGEST
    generation.mkdir(parents=True, exist_ok=True)
    function_ref = PythonFunctionRef(
        bundle_id="plugin:file:scale",
        bundle_digest=_BUNDLE_DIGEST,
        module_relative_path="scale.py",
        function_name="scale",
        source_digest=_SOURCE_DIGEST,
    )
    return PluginBundleRef(
        owner_id="plugin:file:scale",
        version="0.0.0",
        generation_id=_BUNDLE_DIGEST,
        bundle_digest=_BUNDLE_DIGEST,
        approved_generation_root=str(generation.resolve()),
        functions=(function_ref,),
    )


def _frozen_catalog() -> DataTypeCatalog:
    registry = NodeRegistry()
    registry.freeze()
    return registry.data_types


def test_start_run_plugin_bundle_round_trips_with_combined_fingerprint(
    tmp_path,
    monkeypatch,
) -> None:
    generation_root = tmp_path / "plugin_generations"
    monkeypatch.setattr(protocol, "plugin_generations_dir", lambda: generation_root)
    bundle = _bundle(generation_root)
    catalog = _frozen_catalog()
    expected_runtime = runtime_registry_fingerprint(
        catalog.fingerprint(),
        _PLUGIN_FINGERPRINT,
    )
    command = StartRunCommand(
        run_id="run-plugin",
        workspace_id="ws",
        runtime_snapshot=_snapshot(),
        plugin_bundles=(bundle,),
        plugin_fingerprint=_PLUGIN_FINGERPRINT,
        runtime_registry_fingerprint=expected_runtime,
    )

    payload = command_to_dict(command, catalog=catalog)
    restored = dict_to_command(json.loads(json.dumps(payload)), catalog=catalog)

    assert restored.plugin_bundles == (bundle,)
    assert restored.plugin_fingerprint == _PLUGIN_FINGERPRINT
    assert restored.runtime_registry_fingerprint == expected_runtime
    assert payload["plugin_bundles"][0]["functions"][0] == {
        "bundle_id": "plugin:file:scale",
        "bundle_digest": _BUNDLE_DIGEST,
        "module_relative_path": "scale.py",
        "function_name": "scale",
        "source_digest": _SOURCE_DIGEST,
        "is_async": False,
    }
    assert "source" not in payload["plugin_bundles"][0]
    assert "source_code" not in json.dumps(payload)


def test_plugin_protocol_rejects_path_escape_bounds_and_fingerprint_mismatch(
    tmp_path,
    monkeypatch,
) -> None:
    generation_root = tmp_path / "plugin_generations"
    monkeypatch.setattr(protocol, "plugin_generations_dir", lambda: generation_root)
    catalog = _frozen_catalog()
    payload = command_to_dict(
        StartRunCommand(
            run_id="run-plugin",
            workspace_id="ws",
            runtime_snapshot=_snapshot(),
            plugin_bundles=(_bundle(generation_root),),
            plugin_fingerprint=_PLUGIN_FINGERPRINT,
        ),
        catalog=catalog,
    )

    escaped = copy.deepcopy(payload)
    outside = tmp_path / "outside" / _BUNDLE_DIGEST
    outside.mkdir(parents=True)
    escaped["plugin_bundles"][0]["approved_generation_root"] = str(outside)
    with pytest.raises(ValueError, match="direct immutable generation child"):
        dict_to_command(escaped, catalog=catalog)

    mismatched = copy.deepcopy(payload)
    mismatched["runtime_registry_fingerprint"] = "d" * 64
    with pytest.raises(ValueError, match="does not match"):
        dict_to_command(mismatched, catalog=catalog)

    oversized = copy.deepcopy(payload)
    oversized["plugin_bundles"] *= 129
    with pytest.raises(ValueError, match="too many bundles"):
        dict_to_command(oversized, catalog=catalog)

    too_many_functions = copy.deepcopy(payload)
    too_many_functions["plugin_bundles"][0]["functions"] = [{}] * 4097
    with pytest.raises(ValueError, match="too many functions"):
        dict_to_command(too_many_functions, catalog=catalog)

    missing_agreement = copy.deepcopy(payload)
    missing_agreement.pop("plugin_fingerprint")
    with pytest.raises(ValueError, match="requires plugin agreement fields"):
        dict_to_command(missing_agreement, catalog=catalog)

    for field_name, invalid_value in (
        ("plugin_bundles", None),
        ("plugin_fingerprint", ""),
        ("runtime_registry_fingerprint", ""),
    ):
        invalid_agreement = copy.deepcopy(payload)
        invalid_agreement[field_name] = invalid_value
        with pytest.raises(ValueError):
            dict_to_command(invalid_agreement, catalog=catalog)

    long_reason = copy.deepcopy(payload)
    long_reason["plugin_bundles"][0]["unavailable_reason"] = "x" * 2049
    with pytest.raises(ValueError, match="too long"):
        dict_to_command(long_reason, catalog=catalog)


class _RecordingGenerationClient(_ExecutionClientCommon):
    def __init__(self) -> None:
        self._data_types = None
        self._catalog_generation_fingerprint = ""
        self._plugin_bundles = ()
        self._plugin_fingerprint = EMPTY_PLUGIN_FINGERPRINT
        self._runtime_registry_generation_fingerprint = ""
        self._catalog_generation_token = 0
        self._physical_generation_token = 0
        self._accepted_physical_generation_token = 0
        self._run_generation_tokens = {}
        self._start_lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._viewer_request_lock = threading.Lock()
        self._pending_viewer_requests = {}
        self._viewer_session_ids = set()
        self._viewer_session_generations = {}
        self._active_run_id = ""
        self._active_workspace_id = ""
        self._start_run_pending_id = ""
        self._run_thread = None
        self.recycled = 0

    def _viewer_generation_is_live(self) -> bool:
        return False

    def _recycle_catalog_generation(self) -> None:
        self.recycled += 1


def test_plugin_fingerprint_change_recycles_client_generation() -> None:
    catalog = _frozen_catalog()
    client = _RecordingGenerationClient()

    assert client._prepare_start_run(  # noqa: SLF001
        "run-1",
        "ws",
        catalog,
        (),
        _PLUGIN_FINGERPRINT,
    )
    first_token = client._catalog_generation_token_value()  # noqa: SLF001
    client._release_start_run("run-1")  # noqa: SLF001

    assert client._prepare_start_run(  # noqa: SLF001
        "run-2",
        "ws",
        catalog,
        (),
        _PLUGIN_FINGERPRINT,
    )
    assert client.recycled == 0
    assert client._catalog_generation_token_value() == first_token  # noqa: SLF001
    client._release_start_run("run-2")  # noqa: SLF001

    assert client._prepare_start_run(  # noqa: SLF001
        "run-3",
        "ws",
        catalog,
        (),
        "d" * 64,
    )
    assert client.recycled == 1
    assert client._catalog_generation_token_value() > first_token  # noqa: SLF001
    assert client._runtime_registry_fingerprint_value() == (  # noqa: SLF001
        runtime_registry_fingerprint(catalog.fingerprint(), "d" * 64)
    )
    client._release_start_run("run-3")  # noqa: SLF001


def _registry_with_fingerprint(fingerprint: str) -> NodeRegistry:
    registry = NodeRegistry()
    registry.set_python_plugin_catalog((), plugin_fingerprint=fingerprint)
    registry.freeze()
    return registry


def test_corex_runtime_replace_registry_retires_client_and_forwards_agreement() -> None:
    class RecordingBackend:
        def __init__(self) -> None:
            self.replacements = []
            self.starts = []

        def subscribe(self, _callback):  # noqa: ANN001
            return None

        def replace_registry(self, registry):  # noqa: ANN001
            self.replacements.append(registry)
            return True

        def start_run(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self.starts.append((args, kwargs))
            return "run-1"

    original = _registry_with_fingerprint(EMPTY_PLUGIN_FINGERPRINT)
    replacement = _registry_with_fingerprint(_PLUGIN_FINGERPRINT)
    backend = RecordingBackend()
    runtime = CorexRuntime(client=backend, registry=original)

    assert runtime.replace_registry(replacement)
    assert backend.replacements == [replacement]
    assert runtime.start(
        ExecutionRequest(workspace_id="ws", runtime_snapshot=_snapshot())
    ) == "run-1"
    _args, kwargs = backend.starts[0]
    assert kwargs["data_types"] is replacement.data_types
    assert kwargs["plugin_bundles"] == ()
    assert kwargs["plugin_fingerprint"] == _PLUGIN_FINGERPRINT


def test_execution_backend_registry_replacement_visits_every_client(monkeypatch) -> None:
    backend = ExecutionBackendClient()
    registry = _registry_with_fingerprint(_PLUGIN_FINGERPRINT)
    calls = []
    try:
        backend._workspace_clients["completed-ws"] = backend._process_client  # noqa: SLF001
        backend._workspace_client_generations["completed-ws"] = 0  # noqa: SLF001
        for index, client in enumerate(
            (
                backend._process_client,  # noqa: SLF001
                backend._external_python_client,  # noqa: SLF001
                backend._trusted_client,  # noqa: SLF001
            )
        ):
            monkeypatch.setattr(
                client,
                "replace_registry",
                lambda value, index=index: calls.append((index, value)) or index == 0,
            )

        assert backend.replace_registry(registry)
        assert calls == [(0, registry), (1, registry), (2, registry)]
        assert backend._workspace_clients == {}  # noqa: SLF001
    finally:
        backend.shutdown()


def test_plugin_refs_never_enter_project_persistence(tmp_path) -> None:
    generation_root = tmp_path / "plugin_generations"
    bundle = _bundle(generation_root)
    spec = NodeTypeSpec(
        type_id="custom.persist.1234abcd",
        display_name="Persist",
        category_path=("Tests",),
        icon="",
        ports=(),
        properties=(),
    )
    registry = NodeRegistry()
    registry.register_python_function(spec, bundle.functions[0])
    registry.set_python_plugin_catalog(
        (bundle,),
        plugin_fingerprint=_PLUGIN_FINGERPRINT,
    )
    model = GraphModel()
    ValidatedGraphMutation(
        model,
        model.active_workspace.workspace_id,
        registry,
    ).add_node(type_id=spec.type_id, title="Persist", x=0.0, y=0.0)

    document = JsonProjectSerializer(registry).to_persistent_document(model.project)
    serialized = json.dumps(document, sort_keys=True)

    assert spec.type_id in serialized
    assert bundle.approved_generation_root not in serialized
    assert _BUNDLE_DIGEST not in serialized
    assert _SOURCE_DIGEST not in serialized
    assert "plugin_bundles" not in serialized
    assert "function_name" not in serialized
