from __future__ import annotations

import hashlib
import json
import os
import threading
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.common.payload_tools import (
    artifact_content_integrity,
    copy_json_safe,
)
from ea_node_editor.common.optimization_links import (
    OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
    OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
    OPTIMIZATION_RESPONSE_POOL_TYPE_ID,
    optimization_pool_role,
    parameter_setup_pool_link_facts,
)
from ea_node_editor.execution.compiler import compile_runtime_snapshot
from ea_node_editor.execution.protocol import StartRunCommand
from ea_node_editor.execution.runtime_dto import RuntimeEdge, RuntimeWorkspace
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    RuntimeSnapshotContext,
)
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.persistence.artifact_refs import (
    ARTIFACT_REF_SCHEME,
    STAGED_ARTIFACT_REF_SCHEME,
    normalize_artifact_id,
)
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    ArraySlice2DRef,
    DataTree,
    DataTypeCatalog,
    Interval1D,
    RuntimeArtifactRef,
    RuntimeHandleRef,
    TabularDataRef,
    TabularWindowRef,
    TypedInlineValue,
    coerce_runtime_artifact_ref,
)

_TRIGGER_TYPE_ID = "core.trigger"
_UNTYPED_ARTIFACT_PREFIXES = (
    f"{ARTIFACT_REF_SCHEME}://",
    f"{STAGED_ARTIFACT_REF_SCHEME}://",
)


def load_runtime_snapshot(
    command: StartRunCommand,
) -> RuntimeSnapshot:
    if command.runtime_snapshot is None:
        raise ValueError("start_run requires runtime_snapshot.")
    return command.runtime_snapshot


class ExecutionPlan:
    def __init__(
        self,
        workspace: RuntimeWorkspace,
        registry: Any,
        *,
        target_node_ids: tuple[str, ...] = (),
        clicked_trigger_node_id: str = "",
        trigger_capture_node_ids: tuple[str, ...] = (),
    ) -> None:
        self.workspace = workspace
        self.nodes = workspace.nodes_by_id
        self.clicked_trigger_node_id = str(clicked_trigger_node_id or "").strip()
        self.trigger_capture_node_ids = frozenset(
            str(node_id or "").strip()
            for node_id in trigger_capture_node_ids
            if str(node_id or "").strip()
        )
        self.target_nodes = tuple(
            node_id
            for node_id in dict.fromkeys(
                str(node_id or "").strip() for node_id in target_node_ids
            )
            if node_id and node_id in self.nodes
        )
        self.node_specs = {
            node_id: registry.get_spec(node.type_id)
            for node_id, node in self.nodes.items()
        }
        self.node_instances = self._materialize_nodes()
        self.node_ports = self._resolve_effective_ports()
        self.ports_by_key = {
            node_id: {port.key: port for port in ports}
            for node_id, ports in self.node_ports.items()
        }
        self.data_incoming: dict[str, list[RuntimeEdge]] = defaultdict(list)
        self.data_outgoing: dict[str, list[RuntimeEdge]] = defaultdict(list)
        for edge in sorted(
            (edge for edge in workspace.edges if edge.enabled),
            key=lambda item: (
                item.target_node_id,
                item.target_port_key,
                item.input_order,
            ),
        ):
            self.data_incoming[edge.target_node_id].append(edge)
            self.data_outgoing[edge.source_node_id].append(edge)
        self._hidden_ordering_pairs = self._decode_hidden_ordering_pairs()
        self.scheduled_node_ids = self._build_scheduled_nodes()
        self.execution_order = self._topological_order()

    def _materialize_nodes(self) -> dict[str, Any]:
        from ea_node_editor.graph.record_payloads import node_instance_from_mapping

        result: dict[str, Any] = {}
        for node_id, node in self.nodes.items():
            materialized = node_instance_from_mapping(node.to_document())
            if materialized is None:
                raise ValueError(f"Unable to materialize runtime node: {node_id}")
            result[node_id] = materialized
        return result

    def _resolve_effective_ports(self) -> dict[str, tuple[Any, ...]]:
        from ea_node_editor.graph.effective_ports import effective_ports

        return {
            node_id: effective_ports(
                node=node,
                spec=self.node_specs[node_id],
                workspace_nodes=self.node_instances,
            )
            for node_id, node in self.node_instances.items()
        }

    def _decode_hidden_ordering_pairs(self) -> tuple[tuple[str, str], ...]:
        expected_pool_types = (
            OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
            OPTIMIZATION_RESPONSE_POOL_TYPE_ID,
        )
        candidates: list[tuple[str, str]] = []
        target_counts: dict[str, int] = defaultdict(int)
        workspace_id = self.workspace.workspace_id
        for setup_node in self.workspace.nodes:
            if setup_node.type_id != OPTIMIZATION_PARAMETER_SETUP_TYPE_ID:
                continue
            raw_links = setup_node.extra_fields.get("links", ())
            if not isinstance(raw_links, Sequence) or isinstance(
                raw_links, (str, bytes)
            ):
                continue
            link_mappings = tuple(
                link for link in raw_links if isinstance(link, Mapping)
            )
            for expected_pool_type in expected_pool_types:
                link_facts = parameter_setup_pool_link_facts(
                    optimization_pool_role(expected_pool_type)
                )
                if link_facts is None:
                    continue
                link_id, link_title = link_facts
                matching = tuple(
                    link
                    for link in link_mappings
                    if link.get("id") == link_id
                )
                if len(matching) != 1:
                    continue
                link = matching[0]
                target_node_id = link.get("target_node_id")
                target_node = (
                    self.nodes.get(target_node_id)
                    if isinstance(target_node_id, str)
                    else None
                )
                if (
                    target_node is None
                    or target_node.type_id != expected_pool_type
                    or link.get("kind") != "node"
                    or link.get("title") != link_title
                    or link.get("target") != target_node_id
                    or link.get("subtitle") != ""
                    or link.get("target_workspace_id") != workspace_id
                ):
                    continue
                pair = (setup_node.node_id, target_node_id)
                candidates.append(pair)
                target_counts[target_node_id] += 1
        conflicting_target_id = next(
            (
                target_node_id
                for target_node_id, count in target_counts.items()
                if count > 1
            ),
            "",
        )
        if conflicting_target_id:
            raise ValueError(
                "Conflicting Parameter Setup links target pool node "
                f"{conflicting_target_id!r}."
            )
        return tuple(candidates)

    def includes_node(self, node_id: str) -> bool:
        return node_id in self.scheduled_node_ids

    def is_trigger(self, node_id: str) -> bool:
        node = self.nodes.get(node_id)
        return node is not None and node.type_id == _TRIGGER_TYPE_ID

    def _build_scheduled_nodes(self) -> set[str]:
        if not self.target_nodes:
            return set(self.nodes)
        targets = set(self.target_nodes)
        explicit_targets = set(targets)
        if self.clicked_trigger_node_id in self.nodes:
            targets.add(self.clicked_trigger_node_id)
        pending = list(targets)
        while pending:
            current = pending.pop()
            if self.is_trigger(current):
                if (
                    current == self.clicked_trigger_node_id
                    and current in self.trigger_capture_node_ids
                ):
                    continue
                if (
                    current != self.clicked_trigger_node_id
                    and current not in explicit_targets
                ):
                    continue
            for edge in self.data_incoming.get(current, ()):
                source_node_id = edge.source_node_id
                if source_node_id not in self.nodes or source_node_id in targets:
                    continue
                targets.add(source_node_id)
                pending.append(source_node_id)
            for source_node_id, target_node_id in self._hidden_ordering_pairs:
                if target_node_id != current or source_node_id in targets:
                    continue
                targets.add(source_node_id)
                pending.append(source_node_id)
        if self.clicked_trigger_node_id in targets:
            pending = [self.clicked_trigger_node_id]
            while pending:
                current = pending.pop()
                for edge in self.data_outgoing.get(current, ()):
                    downstream = edge.target_node_id
                    if self.is_trigger(downstream) or downstream in targets:
                        continue
                    targets.add(downstream)
                    pending.append(downstream)
        return targets

    def dependency_edges(self) -> tuple[RuntimeEdge, ...]:
        return tuple(
            edge
            for node_id in self.scheduled_node_ids
            for edge in self.data_incoming.get(node_id, ())
            if edge.source_node_id in self.scheduled_node_ids
            and not self.is_trigger(node_id)
        )

    def _topological_order(self) -> tuple[str, ...]:
        validated_order = self._topological_subset(self.scheduled_node_ids)
        if self.clicked_trigger_node_id not in self.scheduled_node_ids:
            return validated_order
        upstream = self._clicked_upstream_nodes()
        downstream = self.scheduled_node_ids.difference(
            upstream, {self.clicked_trigger_node_id}
        )
        return (
            *self._topological_subset(upstream),
            self.clicked_trigger_node_id,
            *self._topological_subset(downstream),
        )

    def _clicked_upstream_nodes(self) -> set[str]:
        upstream: set[str] = set()
        pending = [self.clicked_trigger_node_id]
        while pending:
            current = pending.pop()
            for edge in self.data_incoming.get(current, ()):
                source = edge.source_node_id
                if source == self.clicked_trigger_node_id or source in upstream:
                    continue
                if source not in self.scheduled_node_ids:
                    continue
                upstream.add(source)
                if not self.is_trigger(source):
                    pending.append(source)
            for source, target in self._hidden_ordering_pairs:
                if target != current:
                    continue
                if source == self.clicked_trigger_node_id or source in upstream:
                    continue
                if source not in self.scheduled_node_ids:
                    continue
                upstream.add(source)
                if not self.is_trigger(source):
                    pending.append(source)
        return upstream

    def _topological_subset(self, node_ids: set[str]) -> tuple[str, ...]:
        incoming_count = {node_id: 0 for node_id in node_ids}
        outgoing: dict[str, list[str]] = defaultdict(list)
        for edge in self.dependency_edges():
            if (
                edge.source_node_id not in node_ids
                or edge.target_node_id not in node_ids
            ):
                continue
            incoming_count[edge.target_node_id] += 1
            outgoing[edge.source_node_id].append(edge.target_node_id)
        for source_node_id, target_node_id in self._hidden_ordering_pairs:
            if source_node_id not in node_ids or target_node_id not in node_ids:
                continue
            incoming_count[target_node_id] += 1
            outgoing[source_node_id].append(target_node_id)
        declaration_order = {
            node.node_id: ordinal for ordinal, node in enumerate(self.workspace.nodes)
        }
        ready = sorted(
            (node_id for node_id, count in incoming_count.items() if count == 0),
            key=lambda node_id: declaration_order.get(node_id, 0),
        )
        ordered: list[str] = []
        while ready:
            node_id = ready.pop(0)
            ordered.append(node_id)
            for downstream in outgoing.get(node_id, ()):
                incoming_count[downstream] -= 1
                if incoming_count[downstream] == 0:
                    ready.append(downstream)
            ready.sort(key=lambda item: declaration_order.get(item, 0))
        if len(ordered) != len(node_ids):
            cyclic = sorted(
                node_id for node_id, count in incoming_count.items() if count > 0
            )
            raise ValueError(f"Cycle detected among nodes: {', '.join(cyclic)}")
        return tuple(ordered)

    def input_ports(self, node_id: str) -> tuple[Any, ...]:
        return tuple(
            port for port in self.node_ports.get(node_id, ()) if port.direction == "in"
        )

    def output_ports(self, node_id: str) -> tuple[Any, ...]:
        return tuple(
            port for port in self.node_ports.get(node_id, ()) if port.direction == "out"
        )

    def incoming_edges_for(
        self, node_id: str, port_key: str = ""
    ) -> tuple[RuntimeEdge, ...]:
        return tuple(
            edge
            for edge in self.data_incoming.get(node_id, ())
            if not port_key or edge.target_port_key == port_key
        )


@dataclass(slots=True)
class PreparedRuntime:
    registry: Any
    runtime_snapshot: RuntimeSnapshot
    runtime_context: RuntimeSnapshotContext
    workspace: RuntimeWorkspace
    plan: ExecutionPlan


class RuntimeArtifactService:
    def __init__(
        self,
        *,
        runtime_context: RuntimeSnapshotContext,
        data_types: DataTypeCatalog,
    ) -> None:
        self._runtime_context = runtime_context
        self._data_types = data_types
        self._project_path = str(runtime_context.project_path).strip()
        self._resolver = ProjectArtifactResolver(
            project_path=self._project_path or None,
            artifact_store=runtime_context.artifact_store,
        )

    @property
    def project_path(self) -> str:
        return self._project_path

    @property
    def runtime_context(self) -> RuntimeSnapshotContext:
        return self._runtime_context

    @property
    def store(self):
        return self._resolver.store

    def normalize_outputs(self, payload: dict[str, Any]) -> dict[str, Any]:
        from ea_node_editor.nodes.runtime_refs import (
            deserialize_runtime_value,
            serialize_runtime_value,
        )

        normalized = deserialize_runtime_value(
            serialize_runtime_value(payload, catalog=self._data_types),
            catalog=self._data_types,
        )
        normalized_outputs = (
            dict(normalized) if isinstance(normalized, dict) else {}
        )
        self._verify_runtime_artifacts(normalized_outputs)
        return normalized_outputs

    def materialize_persisted_value(
        self,
        value: Any,
    ) -> Any:
        return self._materialize_persisted_value(
            value,
            _runtime_markers_decoded=False,
        )

    def _materialize_persisted_value(
        self,
        value: Any,
        *,
        _runtime_markers_decoded: bool,
    ) -> Any:
        if isinstance(value, RuntimeArtifactRef):
            self._verify_runtime_artifact(value)
            return value
        if isinstance(
            value,
            (
                ArrayDataRef,
                ArraySlice2DRef,
                RuntimeHandleRef,
                TabularDataRef,
                TabularWindowRef,
                TypedInlineValue,
            ),
        ):
            self._data_types.validate_carrier(value.data_type_id, value)
            return value
        if isinstance(value, Interval1D):
            return value
        if isinstance(value, DataTree):
            return DataTree(
                (
                    path,
                    tuple(
                        self._materialize_persisted_value(
                            item,
                            _runtime_markers_decoded=_runtime_markers_decoded,
                        )
                        for item in items
                    ),
                )
                for path, items in value.branches
            )
        if isinstance(value, Mapping):
            if (
                not _runtime_markers_decoded
                and "__ea_runtime_value__" in value
            ):
                from ea_node_editor.nodes.runtime_refs import (
                    deserialize_runtime_value,
                )

                decoded = deserialize_runtime_value(
                    value,
                    catalog=self._data_types,
                )
                if isinstance(decoded, DataTree) or not isinstance(
                    decoded, Mapping
                ):
                    return self._materialize_persisted_value(
                        decoded,
                        _runtime_markers_decoded=True,
                    )
                value = decoded
                _runtime_markers_decoded = True
            copied: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError(
                        "persisted runtime property mapping keys must be strings"
                    )
                copied[key] = self._materialize_persisted_value(
                    item,
                    _runtime_markers_decoded=_runtime_markers_decoded,
                )
            return copied
        if isinstance(value, list):
            return [
                self._materialize_persisted_value(
                    item,
                    _runtime_markers_decoded=_runtime_markers_decoded,
                )
                for item in value
            ]
        if isinstance(value, tuple):
            return tuple(
                self._materialize_persisted_value(
                    item,
                    _runtime_markers_decoded=_runtime_markers_decoded,
                )
                for item in value
            )
        if not _is_untyped_artifact_reference(value):
            return copy_json_safe(
                value,
                field_name="persisted runtime property",
            )

        text = value.strip()
        saved_prefix = f"{ARTIFACT_REF_SCHEME}://"
        staged_prefix = f"{STAGED_ARTIFACT_REF_SCHEME}://"
        if text.casefold().startswith(staged_prefix):
            raise TypeError(
                "artifact references must use RuntimeArtifactRef"
            )
        if not text.startswith(saved_prefix):
            raise ValueError("persisted artifact reference is malformed")
        artifact_id = normalize_artifact_id(text[len(saved_prefix) :])
        if not artifact_id or text != f"{saved_prefix}{artifact_id}":
            raise ValueError("persisted artifact reference is malformed")

        entry = self.store.managed_entry(artifact_id)
        if entry is None:
            raise FileNotFoundError(
                f"artifact {artifact_id!r} is not registered in the active store"
            )
        if "runtime_artifact" not in entry.extra:
            raise ValueError(
                f"artifact {artifact_id!r} descriptor is missing"
            )
        descriptor = entry.extra["runtime_artifact"]
        if not isinstance(descriptor, Mapping):
            raise ValueError(
                f"artifact {artifact_id!r} descriptor is invalid"
            )
        try:
            runtime_ref = RuntimeArtifactRef.managed(
                artifact_id,
                data_type_id=descriptor["data_type_id"],
                schema_version=descriptor["schema_version"],
                format=descriptor["format"],
                size_bytes=descriptor["size_bytes"],
                sha256=descriptor["sha256"],
                provenance=descriptor["provenance"],
            )
            self._data_types.validate_carrier(
                runtime_ref.data_type_id,
                runtime_ref,
            )
            if set(descriptor) != set(runtime_ref.to_descriptor()):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise ValueError(
                f"artifact {artifact_id!r} descriptor is invalid"
            ) from None
        if (
            runtime_ref.scope != "managed"
            or runtime_ref.artifact_id != artifact_id
        ):
            raise ValueError(
                f"artifact {artifact_id!r} descriptor does not match"
            )
        self._verify_runtime_artifact(runtime_ref)
        return runtime_ref

    def resolve_path(self, value: Any) -> Any:
        if _is_untyped_artifact_reference(value):
            raise TypeError(
                "artifact references must use RuntimeArtifactRef"
            )
        runtime_ref = coerce_runtime_artifact_ref(
            value,
            catalog=self._data_types,
        )
        if runtime_ref is not None:
            return self._verify_runtime_artifact(runtime_ref)
        return self._resolver.resolve_to_path(value)

    def _verify_runtime_artifacts(self, value: Any) -> None:
        if _is_untyped_artifact_reference(value):
            raise TypeError(
                "artifact references must use RuntimeArtifactRef"
            )
        if isinstance(value, RuntimeArtifactRef):
            self._verify_runtime_artifact(value)
            return
        if isinstance(value, DataTree):
            for _path, items in value.branches:
                for item in items:
                    self._verify_runtime_artifacts(item)
            return
        if isinstance(value, Mapping):
            for item in value.values():
                self._verify_runtime_artifacts(item)
            return
        if isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        ):
            for item in value:
                self._verify_runtime_artifacts(item)

    def _verify_runtime_artifact(
        self,
        runtime_ref: RuntimeArtifactRef,
    ) -> Path:
        artifact_id = runtime_ref.artifact_id
        self._data_types.validate_carrier(
            runtime_ref.data_type_id,
            runtime_ref,
        )
        if runtime_ref.scope == "staged":
            entry = self.store.staged_entry(artifact_id)
            resolved_path = self.store.resolve_staged_path(artifact_id)
            trusted_root = self.store.active_staging_root()
            relative_path = entry.relative_path if entry is not None else None
            try:
                trusted_target = (
                    self.store.staged_target_path(relative_path)
                    if relative_path
                    else None
                )
            except ValueError:
                trusted_target = None
        else:
            entry = self.store.managed_entry(artifact_id)
            resolved_path = self.store.resolve_managed_path(artifact_id)
            layout = self.store.layout
            trusted_root = layout.sidecar_root if layout is not None else None
            relative_path = entry.relative_path if entry is not None else None
            trusted_target = (
                layout.absolute_path_for_relative(relative_path)
                if layout is not None and relative_path
                else None
            )
        if (
            entry is None
            or resolved_path is None
            or trusted_root is None
            or trusted_target is None
            or not relative_path
        ):
            raise FileNotFoundError(
                f"artifact {artifact_id!r} is not registered in the active store"
            )
        if _normalized_absolute_path(resolved_path) != _normalized_absolute_path(
            trusted_target
        ):
            raise ValueError(
                f"artifact {artifact_id!r} store target does not match"
            )

        descriptor = entry.extra.get("runtime_artifact")
        expected_descriptor = runtime_ref.to_descriptor()
        if not isinstance(descriptor, Mapping):
            raise ValueError(
                f"artifact {artifact_id!r} descriptor is missing"
            )
        if set(descriptor) != set(expected_descriptor):
            raise ValueError(
                f"artifact {artifact_id!r} descriptor fields do not match"
            )
        for field_name, expected_value in expected_descriptor.items():
            actual_value = descriptor.get(field_name)
            if (
                type(actual_value) is not type(expected_value)
                or actual_value != expected_value
            ):
                raise ValueError(
                    f"artifact {artifact_id!r} descriptor field "
                    f"{field_name!r} does not match"
                )

        try:
            size_bytes, sha256 = artifact_content_integrity(
                trusted_root,
                relative_path,
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"artifact {artifact_id!r} payload is missing"
            ) from None
        except (OSError, ValueError):
            raise ValueError(
                f"artifact {artifact_id!r} payload could not be verified"
            ) from None
        if size_bytes != runtime_ref.size_bytes:
            raise ValueError(
                f"artifact {artifact_id!r} size_bytes does not match"
            )
        if sha256 != runtime_ref.sha256:
            raise ValueError(
                f"artifact {artifact_id!r} sha256 does not match"
            )
        return resolved_path


def _normalized_absolute_path(value: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(value)))


def _is_untyped_artifact_reference(value: object) -> bool:
    return isinstance(value, str) and value.strip().casefold().startswith(
        _UNTYPED_ARTIFACT_PREFIXES
    )


def resolve_runtime_artifact_store(
    *,
    project_path: str = "",
    runtime_snapshot: RuntimeSnapshot | None = None,
    runtime_context: RuntimeSnapshotContext | None = None,
) -> ProjectArtifactStore:
    if runtime_context is not None:
        return runtime_context.artifact_store
    project_metadata = (
        runtime_snapshot.metadata if runtime_snapshot is not None else None
    )
    return ProjectArtifactStore.from_project_metadata(
        project_path=str(project_path).strip() or None,
        project_metadata=project_metadata
        if isinstance(project_metadata, Mapping)
        else None,
    )


class RuntimePreparationCache:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._registry: Any | None = None
        self._registry_provider_id: Any = 0
        self._compiled_workspaces: dict[tuple[int, str, str], RuntimeWorkspace] = {}

    def default_registry(self) -> Any:
        from ea_node_editor.nodes.bootstrap import build_default_registry

        provider_id = id(build_default_registry)
        with self._lock:
            if self._registry is None or self._registry_provider_id != provider_id:
                self._registry = build_default_registry()
                self._registry_provider_id = provider_id
                self._compiled_workspaces.clear()
            return self._registry

    def compiled_workspace(
        self,
        runtime_snapshot: RuntimeSnapshot,
        *,
        workspace_id: str,
        registry: Any,
    ) -> RuntimeWorkspace:
        cache_key = self._workspace_cache_key(
            runtime_snapshot,
            workspace_id=workspace_id,
            registry=registry,
        )
        with self._lock:
            cached = self._compiled_workspaces.get(cache_key)
            if cached is not None:
                return cached
        compiled = compile_runtime_snapshot(
            runtime_snapshot,
            workspace_id=workspace_id,
            registry=registry,
        )
        with self._lock:
            return self._compiled_workspaces.setdefault(cache_key, compiled)

    @staticmethod
    def _workspace_cache_key(
        runtime_snapshot: RuntimeSnapshot,
        *,
        workspace_id: str,
        registry: Any,
    ) -> tuple[int, str, str]:
        snapshot_payload = runtime_snapshot.to_document(catalog=registry.data_types)
        digest = hashlib.sha256(
            json.dumps(
                snapshot_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        return (id(registry), str(workspace_id).strip(), digest)

    def clear(self) -> None:
        with self._lock:
            self._compiled_workspaces.clear()
            self._registry = None
            self._registry_provider_id = 0


DEFAULT_RUNTIME_PREPARATION_CACHE = RuntimePreparationCache()


def prepare_runtime(
    command: StartRunCommand,
    *,
    cache: RuntimePreparationCache | None = None,
) -> PreparedRuntime:
    runtime_cache = cache or DEFAULT_RUNTIME_PREPARATION_CACHE
    runtime_snapshot = load_runtime_snapshot(command)
    registry = runtime_cache.default_registry()
    artifact_context_project_path = command.project_path
    runtime_context = RuntimeSnapshotContext.from_snapshot(
        runtime_snapshot,
        project_path=artifact_context_project_path,
    )
    workspace = runtime_cache.compiled_workspace(
        runtime_snapshot,
        workspace_id=command.workspace_id,
        registry=registry,
    )
    return PreparedRuntime(
        registry=registry,
        runtime_snapshot=runtime_snapshot,
        runtime_context=runtime_context,
        workspace=workspace,
        plan=ExecutionPlan(
            workspace,
            registry,
            target_node_ids=tuple(command.target_node_ids),
            clicked_trigger_node_id=command.clicked_trigger_node_id,
            trigger_capture_node_ids=tuple(command.trigger_captures),
        ),
    )


__all__ = [
    "ExecutionPlan",
    "DEFAULT_RUNTIME_PREPARATION_CACHE",
    "PreparedRuntime",
    "RuntimePreparationCache",
    "RuntimeArtifactService",
    "load_runtime_snapshot",
    "prepare_runtime",
    "resolve_runtime_artifact_store",
]
