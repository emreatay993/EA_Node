# Purpose: Bind sealed preparations to run reservations without re-admitting internal payloads.
# Map: subsystems/execution.md
# Tests: tests/test_prepared_dispatch.py, tests/test_runtime.py, tests/test_backend_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ea_node_editor.execution.prepared_execution import (
    PreparedExecution,
    _digest,
    _integer,
    _text,
)
from ea_node_editor.execution.run_messages import StartRunCommand
from ea_node_editor.execution.viewer_messages import (
    normalize_viewer_invalidation_fields,
)
from ea_node_editor.runtime_contracts import DataTypeCatalog
from ea_node_editor.runtime_contracts.solution_records import SolutionResidency


@dataclass(frozen=True, slots=True)
class PreparedRunDispatch:
    """An immutable preparation plus the independently checked admission identity.

    Runtime/backend reservation checks still authorize dispatch. This object
    supplies a pure wire projection and detached worker DTOs; it never admits
    raw start requests or grants authority based on a fingerprint alone.
    """

    prepared: PreparedExecution
    run_id: str
    runtime_generation: int
    viewer_invalidation_node_ids: tuple[str, ...] | None
    viewer_workspace_invalidation_epoch: int
    viewer_node_invalidation_epochs: tuple[tuple[str, int], ...]
    viewer_invalidation_reservation_id: str
    viewer_epoch_snapshot_digest: str

    def __post_init__(self) -> None:
        if type(self.prepared) is not PreparedExecution:
            raise TypeError("prepared must be a sealed PreparedExecution")
        object.__setattr__(self, "run_id", _text(self.run_id, field_name="run_id"))
        _integer(
            self.runtime_generation, field_name="runtime_generation", positive=True
        )
        if any(
            payload.residency is SolutionResidency.SESSION
            and payload.runtime_generation != self.runtime_generation
            for payload in self.prepared.accepted_output_payloads
        ):
            raise ValueError(
                "session accepted output generation must match command generation"
            )
        envelope = self.prepared.dispatch_envelope
        values = normalize_viewer_invalidation_fields(
            preparation_id=self.prepared.preparation_id,
            workspace_id=envelope.workspace_id,
            node_ids=self.viewer_invalidation_node_ids,
            workspace_epoch=self.viewer_workspace_invalidation_epoch,
            node_epochs=self.viewer_node_invalidation_epochs,
            reservation_id=self.viewer_invalidation_reservation_id,
            snapshot_digest=self.viewer_epoch_snapshot_digest,
        )
        for name, value in values.items():
            object.__setattr__(self, name, value)

    def _admission_fields(self) -> dict[str, Any]:
        prepared = self.prepared
        return {
            "preparation_id": prepared.preparation_id,
            "solution_namespace_id": prepared.solution_namespace_id,
            "execution_affecting_workspace_revision": prepared.execution_affecting_workspace_revision,
            "dispatch_runtime_generation": self.runtime_generation,
            "runtime_snapshot_fingerprint": prepared.runtime_snapshot_fingerprint,
            "execution_plan_fingerprint": prepared.execution_plan_fingerprint,
            "workflow_interface_revision": prepared.workflow_interface_revision,
            "workflow_interface_digest": prepared.workflow_interface_digest,
            "execution_environment_digest": prepared.execution_environment_digest,
            "trigger_publication_generations": prepared.trigger_publication_generations,
            "node_decisions": prepared.node_decisions,
            "accepted_output_payloads": prepared.accepted_output_payloads,
            "viewer_invalidation_node_ids": self.viewer_invalidation_node_ids,
            "viewer_workspace_invalidation_epoch": self.viewer_workspace_invalidation_epoch,
            "viewer_node_invalidation_epochs": self.viewer_node_invalidation_epochs,
            "viewer_invalidation_reservation_id": self.viewer_invalidation_reservation_id,
            "viewer_epoch_snapshot_digest": self.viewer_epoch_snapshot_digest,
        }

    def to_payload(self) -> dict[str, Any]:
        envelope = self.prepared.dispatch_envelope
        payload = envelope.to_payload()
        payload.pop("project_id")
        payload.pop("trigger_capture_node_ids")
        payload.update(self._admission_fields())
        payload.update(type="start_run", run_id=self.run_id)
        payload["node_decisions"] = [
            item.to_payload() for item in self.prepared.node_decisions
        ]
        payload["accepted_output_payloads"] = [
            item.to_payload() for item in self.prepared.accepted_output_payloads
        ]
        for name in (
            "trigger_publication_generations",
            "viewer_node_invalidation_epochs",
        ):
            payload[name] = [list(item) for item in payload[name]]
        if self.viewer_invalidation_node_ids is not None:
            payload["viewer_invalidation_node_ids"] = list(
                self.viewer_invalidation_node_ids
            )
        return payload

    def materialize(self, catalog: DataTypeCatalog) -> StartRunCommand:
        """Return a private DTO, with no mutable aliases to this preparation."""
        envelope = self.prepared.dispatch_envelope
        if (
            not isinstance(catalog, DataTypeCatalog)
            or not catalog.is_frozen
            or catalog.fingerprint() != envelope.catalog_fingerprint
        ):
            raise ValueError("prepared dispatch catalog changed")
        # Admission of the immutable bytes to a different/active catalog is a
        # consumption check. Pure projection must never stand in for it.
        for payload in self.prepared.accepted_output_payloads:
            payload.validate_for_catalog(catalog)
        _digest(
            envelope.registry_contract_fingerprint,
            field_name="registry_contract_fingerprint",
        )
        return StartRunCommand(
            run_id=self.run_id,
            project_path=envelope.project_path,
            workspace_id=envelope.workspace_id,
            trigger=envelope.decode_trigger(catalog=catalog),
            runtime_snapshot=envelope.decode_runtime_snapshot(catalog=catalog),
            execution_backend=envelope.execution_backend,
            target_node_ids=envelope.target_node_ids,
            recompute_mode=envelope.recompute_mode.value,
            trigger_publications=envelope.decode_trigger_publications(catalog=catalog),
            trigger_captures=envelope.decode_trigger_captures(catalog=catalog),
            clicked_trigger_node_id=envelope.clicked_trigger_node_id,
            developer_mode=envelope.developer_mode,
            catalog_fingerprint=envelope.catalog_fingerprint,
            catalog_revisions=envelope.catalog_revisions,
            plugin_bundles=envelope.plugin_bundles,
            plugin_fingerprint=envelope.plugin_fingerprint,
            runtime_registry_fingerprint=envelope.runtime_registry_fingerprint,
            registry_contract_fingerprint=envelope.registry_contract_fingerprint,
            addon_runtime_config=envelope.addon_runtime_config,
            **self._admission_fields(),
        )
