from __future__ import annotations

import copy
import io
import json
import queue
import threading
import time
import unittest
from dataclasses import dataclass, replace
from unittest.mock import patch

from ea_node_editor.execution.client import (
    ExternalPythonExecutionClient,
    ProcessExecutionClient,
    TrustedInProcessExecutionClient,
)
from ea_node_editor.execution.protocol import (
    CancelRunPreflightCommand,
    CatalogRevisionRecord,
    CommitRunPreflightCommand,
    NodeSettledEvent,
    OpenViewerSessionCommand,
    ProtocolErrorEvent,
    QueryViewerSessionCommand,
    RunCompletedEvent,
    RunFailedEvent,
    RunPreflightAcceptedEvent,
    RunStateEvent,
    RunStoppedEvent,
    ShutdownCommand,
    StartRunCommand,
    catalog_agreement,
    catalog_mismatch_message,
    command_to_dict,
    dict_to_command,
    dict_to_event,
    event_to_dict,
    normalize_catalog_revisions,
    viewer_epoch_snapshot_digest,
)
from ea_node_editor.execution.prepared_execution import (
    AcceptedOutputPayload,
    PreparedAction,
    PreparedNodeDecision,
)
from ea_node_editor.runtime_contracts.settled_results import (
    RootExecutionError,
    SettledPortResult,
)
from ea_node_editor.execution.runtime_dto import (
    RuntimeEdge,
    RuntimeNode,
    RuntimeWorkspace,
)
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot
from ea_node_editor.execution.stdio_worker import main as stdio_worker_main
from ea_node_editor.execution.worker_protocol import decode_command_payload, emit
from ea_node_editor.execution.worker_runner import RunControl
from ea_node_editor.execution.worker_runtime import (
    DEFAULT_RUNTIME_PREPARATION_CACHE,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    DataConversionSpec,
    DataTypeCatalog,
    DataTypeFamilySpec,
    DataTypeSpec,
    DataTree,
    Interval1D,
    PATH_DATA_TYPE_ID,
    RuntimeArtifactRef,
    TabularDataRef,
)
from ea_node_editor.runtime_contracts.data_types import MAX_PAYLOAD_SCHEMA_VERSION
from ea_node_editor.runtime_contracts.solution_records import SolutionResidency


@dataclass
class _UnsupportedDataclass:
    value: int


class _RecordingQueue:
    def __init__(self) -> None:
        self.items: list[object] = []

    def put(self, value: object) -> None:
        self.items.append(value)


class _RecordingStdin:
    def __init__(self) -> None:
        self.writes: list[str] = []
        self.flush_count = 0

    def write(self, value: str) -> None:
        self.writes.append(value)

    def flush(self) -> None:
        self.flush_count += 1


class _RunningExternalProcess:
    def __init__(self) -> None:
        self.stdin = _RecordingStdin()

    @staticmethod
    def poll() -> None:
        return None


class _TrackingWorkerServices(WorkerServices):
    def __init__(self) -> None:
        super().__init__()
        self.bound_catalogs = []

    def bind_data_types(self, data_types) -> None:  # noqa: ANN001
        self.bound_catalogs.append(data_types)
        super().bind_data_types(data_types)


def _catalog():
    return build_default_registry().data_types


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


def _semantic_catalog(
    *,
    family_display_name: str = "Catalog",
    capabilities: frozenset[str] = frozenset(),
    source_label: str = "",
) -> DataTypeCatalog:
    catalog = DataTypeCatalog()
    catalog.register_many(
        families=(
            DataTypeFamilySpec(
                "tests.catalog",
                family_display_name,
                "data.tests",
                "tests",
            ),
        ),
        types=(
            DataTypeSpec(
                "tests.CatalogValue",
                "Catalog Value",
                "tests.catalog",
                lambda value: isinstance(value, str),
                capabilities=capabilities,
                implementation_version="1",
            ),
            DataTypeSpec(
                "tests.CatalogText",
                "Catalog Text",
                "tests.catalog",
                lambda value: isinstance(value, str),
                implementation_version="1",
            ),
        ),
        conversions=(
            DataConversionSpec(
                "tests.CatalogValue",
                "tests.CatalogText",
                str,
                implementation_version="1",
            ),
        ),
        owner_id="tests.catalog",
        owner_version="1",
        source_label=source_label,
    )
    catalog.freeze()
    return catalog


def _typed_snapshot() -> RuntimeSnapshot:
    artifact = RuntimeArtifactRef.staged(
        "protocol_artifact",
        data_type_id=PATH_DATA_TYPE_ID,
        schema_version=1,
        format="txt",
        size_bytes=0,
        sha256="0" * 64,
        provenance="corex.test.fixture",
    )
    return RuntimeSnapshot(
        schema_version=1,
        active_workspace_id="ws_protocol",
        workspace_order=("ws_protocol",),
        workspaces=(
            RuntimeWorkspace(
                document_fields={"workspace_id": "ws_protocol"},
                nodes=(
                    RuntimeNode(
                        node_id="node_protocol",
                        type_id="core.constant",
                        title="Protocol",
                        x=0.0,
                        y=0.0,
                        properties={"value": artifact},
                    ),
                ),
            ),
        ),
    )


class ExecutionProtocolTests(unittest.TestCase):
    def test_prepared_start_roundtrip_and_legacy_prepared_field_rejection(self) -> None:
        catalog = _catalog()
        decision = PreparedNodeDecision(
            node_id="node_protocol",
            action=PreparedAction.REUSE,
            reason_code="reusable_record_accepted",
            solution_key="a" * 64,
            dependency_solution_keys=(),
            accepted_record_id="record_protocol",
        )
        accepted = AcceptedOutputPayload(
            node_id=decision.node_id,
            record_id="record_protocol",
            solution_key=decision.solution_key,
            settlement_status="completed",
            result_digest="b" * 64,
            residency=SolutionResidency.SESSION,
            runtime_generation=7,
            outputs={
                "value": SettledPortResult(
                    status="value",
                    value=DataTree.from_item("cached"),
                )
            },
            catalog=catalog,
        )
        command = StartRunCommand(
            run_id="run_prepared",
            workspace_id="ws_protocol",
            runtime_snapshot=_typed_snapshot(),
            preparation_id="preparation_protocol",
            solution_namespace_id="namespace_protocol",
            execution_affecting_workspace_revision=3,
            dispatch_runtime_generation=7,
            runtime_snapshot_fingerprint="c" * 64,
            execution_plan_fingerprint="d" * 64,
            workflow_interface_revision=1,
            workflow_interface_digest="e" * 64,
            execution_environment_digest="f" * 64,
            trigger_publication_generations=(("trigger", 2),),
            node_decisions=(decision,),
            accepted_output_payloads=(accepted,),
            viewer_invalidation_node_ids=(),
            viewer_invalidation_reservation_id="viewer_inv_protocol",
            viewer_epoch_snapshot_digest=viewer_epoch_snapshot_digest(
                workspace_id="ws_protocol",
                node_ids=(),
                workspace_epoch=0,
                node_epochs=(),
            ),
        )
        payload = command_to_dict(command, catalog=catalog)
        restored = dict_to_command(json.loads(json.dumps(payload)), catalog=catalog)
        self.assertEqual(command_to_dict(restored, catalog=catalog), payload)
        self.assertEqual(restored.preparation_id, command.preparation_id)
        self.assertEqual(restored.viewer_invalidation_node_ids, ())
        self.assertEqual(
            restored.viewer_epoch_snapshot_digest,
            command.viewer_epoch_snapshot_digest,
        )
        self.assertEqual(restored.node_decisions, command.node_decisions)
        self.assertEqual(
            restored.accepted_output_payloads[0].to_payload(catalog=catalog),
            accepted.to_payload(catalog=catalog),
        )
        clients = (
            ProcessExecutionClient(),
            ExternalPythonExecutionClient(),
            TrustedInProcessExecutionClient(),
        )
        try:
            for client in clients:
                client._data_types = catalog  # noqa: SLF001
                transported = client._decode_command(  # noqa: SLF001
                    client._encode_command(command)  # noqa: SLF001
                )
                self.assertEqual(transported.preparation_id, command.preparation_id)
                self.assertEqual(transported.node_decisions, command.node_decisions)
                self.assertEqual(
                    transported.accepted_output_payloads[0].to_payload(
                        catalog=catalog
                    ),
                    accepted.to_payload(catalog=catalog),
                )
        finally:
            for client in clients:
                client.shutdown()

        for mutate in (
            lambda value: value.pop("solution_namespace_id"),
            lambda value: value.__setitem__("dispatch_runtime_generation", 8),
            lambda value: value.__setitem__("preparation_id", ""),
            lambda value: value.__setitem__(
                "viewer_epoch_snapshot_digest", "0" * 64
            ),
        ):
            malformed = copy.deepcopy(payload)
            mutate(malformed)
            with self.assertRaises(ValueError):
                dict_to_command(malformed, catalog=catalog)

    def test_run_preflight_acknowledgments_round_trip_exact_identity(self) -> None:
        digest = "a" * 64
        for command in (
            CommitRunPreflightCommand(
                run_id="run_preflight",
                viewer_invalidation_reservation_id="viewer_inv_preflight",
                viewer_epoch_snapshot_digest=digest,
            ),
            CancelRunPreflightCommand(
                run_id="run_preflight",
                viewer_invalidation_reservation_id="viewer_inv_preflight",
                viewer_epoch_snapshot_digest=digest,
            ),
        ):
            self.assertEqual(dict_to_command(command_to_dict(command)), command)
        event = RunPreflightAcceptedEvent(
            run_id="run_preflight",
            workspace_id="ws_preflight",
            preparation_id="prepared_preflight",
            viewer_invalidation_reservation_id="viewer_inv_preflight",
            viewer_epoch_snapshot_digest=digest,
        )
        self.assertEqual(dict_to_event(event_to_dict(event)), event)

    def test_solution_settlement_identity_combinations_are_strict(self) -> None:
        reused = NodeSettledEvent(
            run_id="run",
            workspace_id="ws",
            node_id="node",
            status="empty",
            disposition="reused",
            decision_reason="reusable_record_accepted",
            solution_key="a" * 64,
            record_id="record",
            residency="session",
        )
        self.assertEqual(
            dict_to_event(event_to_dict(reused)),
            reused,
        )
        invalid = (
            replace(reused, status="failed"),
            replace(reused, record_id=""),
            replace(reused, disposition="recomputed"),
            replace(
                reused,
                disposition="skipped",
                status="completed",
                record_id="",
                residency="",
            ),
            replace(
                reused,
                disposition="blocked",
                status="empty",
                record_id="",
                residency="",
            ),
        )
        for event in invalid:
            with self.assertRaises(ValueError):
                event_to_dict(event)

    def test_legacy_start_requires_exact_prepared_field_default_types(self) -> None:
        catalog = _catalog()
        payload = command_to_dict(
            StartRunCommand(
                run_id="legacy",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )
        self.assertIsInstance(dict_to_command(payload, catalog=catalog), StartRunCommand)
        text_fields = (
            "preparation_id",
            "solution_namespace_id",
            "runtime_snapshot_fingerprint",
            "execution_plan_fingerprint",
            "workflow_interface_digest",
            "execution_environment_digest",
        )
        sequence_fields = (
            "trigger_publication_generations",
            "node_decisions",
            "accepted_output_payloads",
        )
        integer_fields = (
            "execution_affecting_workspace_revision",
            "dispatch_runtime_generation",
            "workflow_interface_revision",
        )
        for field_name in text_fields:
            for invalid in (None, False, 0):
                malformed = copy.deepcopy(payload)
                malformed[field_name] = invalid
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_command(malformed, catalog=catalog)
        for field_name in sequence_fields:
            for invalid in (None, False, 0):
                malformed = copy.deepcopy(payload)
                malformed[field_name] = invalid
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_command(malformed, catalog=catalog)
        for field_name in integer_fields:
            for invalid in (None, False, "0"):
                malformed = copy.deepcopy(payload)
                malformed[field_name] = invalid
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_command(malformed, catalog=catalog)

    def test_start_run_semantic_carrier_round_trips_through_json(self) -> None:
        catalog = _catalog()
        command = StartRunCommand(
            run_id="run_protocol",
            workspace_id="ws_protocol",
            runtime_snapshot=_typed_snapshot(),
        )

        payload = command_to_dict(command, catalog=catalog)
        restored = dict_to_command(
            json.loads(json.dumps(payload)),
            catalog=catalog,
        )

        self.assertEqual(payload["catalog_fingerprint"], catalog.fingerprint())
        self.assertTrue(payload["catalog_revisions"])
        self.assertNotIn("catalog", payload["runtime_snapshot"])
        self.assertNotIn("catalog_revisions", payload["runtime_snapshot"])
        self.assertIsInstance(restored, StartRunCommand)
        self.assertEqual(restored.catalog_fingerprint, catalog.fingerprint())
        artifact = (
            restored.runtime_snapshot.workspace("ws_protocol")
            .nodes[0]
            .properties["value"]
        )
        self.assertIsInstance(artifact, RuntimeArtifactRef)
        self.assertEqual(artifact.data_type_id, PATH_DATA_TYPE_ID)

    def test_semantic_carrier_requires_catalog_in_both_directions(self) -> None:
        catalog = _catalog()
        fingerprint, revisions = catalog_agreement(catalog)
        command = StartRunCommand(
            workspace_id="ws_protocol",
            runtime_snapshot=_typed_snapshot(),
            catalog_fingerprint=fingerprint,
            catalog_revisions=revisions,
        )
        catalog_payload = command_to_dict(command, catalog=catalog)

        with self.assertRaisesRegex(ValueError, "active data-type catalog"):
            command_to_dict(command)
        with self.assertRaisesRegex(ValueError, "active data-type catalog"):
            dict_to_command(catalog_payload)

    def test_catalog_revisions_cover_semantic_family_type_and_conversion_changes(
        self,
    ) -> None:
        baseline = _semantic_catalog(source_label=r"C:\plugins\catalog.py")
        source_moved = _semantic_catalog(source_label="/opt/plugins/catalog.py")
        family_changed = _semantic_catalog(family_display_name="Renamed Catalog")
        type_changed = _semantic_catalog(
            capabilities=frozenset({"viewer.render"})
        )

        baseline_fingerprint, baseline_records = catalog_agreement(baseline)
        moved_fingerprint, moved_records = catalog_agreement(source_moved)
        self.assertEqual(baseline_fingerprint, moved_fingerprint)
        self.assertEqual(baseline_records, moved_records)
        self.assertNotEqual(baseline.snapshot(), source_moved.snapshot())
        self.assertEqual(
            {record.kind for record in baseline_records},
            {"family", "type", "conversion"},
        )
        self.assertTrue(
            all(
                len(record.semantic_digest) == 64
                and record.semantic_digest.islower()
                for record in baseline_records
            )
        )

        family_fingerprint, family_records = catalog_agreement(family_changed)
        family_message = catalog_mismatch_message(
            family_fingerprint,
            family_records,
            baseline,
        )
        self.assertIn("family tests.catalog", family_message)
        self.assertIn("desktop digest=", family_message)
        type_fingerprint, type_records = catalog_agreement(type_changed)
        type_message = catalog_mismatch_message(
            type_fingerprint,
            type_records,
            baseline,
        )
        self.assertIn("type tests.CatalogValue", type_message)
        self.assertIn("desktop digest=", type_message)

    def test_catalog_mismatch_uses_identities_without_rendering_versions(
        self,
    ) -> None:
        desktop = _revision_catalog("desktop-private-version")
        worker = _revision_catalog("worker-private-version")
        fingerprint, records = catalog_agreement(desktop)

        version_message = catalog_mismatch_message(
            fingerprint,
            records,
            worker,
        )

        self.assertIn("type tests.CatalogValue", version_message)
        self.assertNotIn("desktop-private-version", version_message)
        self.assertNotIn("worker-private-version", version_message)

        desktop_with_extra_records = _semantic_catalog()
        fingerprint, records = catalog_agreement(desktop_with_extra_records)
        desktop_only_message = catalog_mismatch_message(
            fingerprint,
            records,
            _revision_catalog("1"),
        )

        self.assertIn("type tests.CatalogText", desktop_only_message)
        self.assertIn(
            "conversion tests.CatalogValue -> tests.CatalogText",
            desktop_only_message,
        )
        self.assertIn("desktop-only", desktop_only_message)

    def test_catalog_mismatch_preserves_long_canonical_identity_context(
        self,
    ) -> None:
        long_identity = "Tests." + ".".join(
            f"RecognizableSegment{index:02d}" for index in range(40)
        )
        record = CatalogRevisionRecord(
            kind="type",
            identity=long_identity,
            payload_schema_version=1,
            implementation_version="private-implementation-v1",
            owner_id="tests.catalog",
            owner_version="private-owner-v1",
            semantic_digest="a" * 64,
        )
        worker_catalog = DataTypeCatalog()
        worker_catalog.freeze()

        message = catalog_mismatch_message(
            "b" * 64,
            (record,),
            worker_catalog,
        )

        self.assertIn(f"type {long_identity[:64]}", message)
        self.assertIn(long_identity[-32:], message)
        self.assertIn("#" + ("a" * 12), message)
        self.assertIn("desktop-only", message)
        self.assertNotIn("private-implementation-v1", message)
        self.assertNotIn("private-owner-v1", message)
        self.assertLess(len(message), 1024)

    def test_catalog_mismatch_preserves_short_identity_exactly(
        self,
    ) -> None:
        record = CatalogRevisionRecord(
            kind="type",
            identity="Tests.ShortIdentity",
            payload_schema_version=1,
            implementation_version="private-implementation-v1",
            owner_id="tests.catalog",
            owner_version="private-owner-v1",
            semantic_digest="c" * 64,
        )
        worker_catalog = DataTypeCatalog()
        worker_catalog.freeze()
        expected_fingerprint = "b" * 64
        prefix = (
            "Data-type catalog mismatch before execution: "
            f"desktop={expected_fingerprint}, "
            f"worker={worker_catalog.fingerprint()}. "
        )

        message = catalog_mismatch_message(
            expected_fingerprint,
            (record,),
            worker_catalog,
        )

        self.assertTrue(message.startswith(prefix))
        detail = message[len(prefix) :]
        self.assertEqual(
            detail,
            "type Tests.ShortIdentity "
            "(schema=1, owner=tests.catalog): desktop-only",
        )
        self.assertNotIn("...", detail)
        self.assertNotIn("#" + ("c" * 12), detail)

    def test_catalog_mismatch_caps_eight_maximum_sized_differences(
        self,
    ) -> None:
        records = []
        implementation_version = "private-implementation-" + ("v" * 105)
        owner_version = "private-owner-" + ("v" * 114)
        owner_id = "owner." + ("o" * 250)
        for index in range(8):
            prefix = f"Tests.Relevant{index:02d}."
            suffix = f".RecognizableTail{index:02d}"
            identity = (
                prefix
                + ("A" * (1024 - len(prefix) - len(suffix)))
                + suffix
            )
            records.append(
                CatalogRevisionRecord(
                    kind="type",
                    identity=identity,
                    payload_schema_version=MAX_PAYLOAD_SCHEMA_VERSION,
                    implementation_version=implementation_version,
                    owner_id=owner_id,
                    owner_version=owner_version,
                    semantic_digest=f"{index:064x}",
                )
            )
        worker_catalog = DataTypeCatalog()
        worker_catalog.freeze()

        first = catalog_mismatch_message(
            "f" * 64,
            tuple(records),
            worker_catalog,
        )
        second = catalog_mismatch_message(
            "f" * 64,
            tuple(records),
            worker_catalog,
        )

        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 2048)
        self.assertIn(
            "[catalog mismatch details truncated: showing 3 of 8 differences]",
            first,
        )
        for retained_index in range(3):
            self.assertIn(f"Tests.Relevant{retained_index:02d}.", first)
            self.assertIn(f".RecognizableTail{retained_index:02d}", first)
        self.assertNotIn("Tests.Relevant03.", first)
        self.assertNotIn(".RecognizableTail03", first)
        self.assertIn("#000000000000", first)
        self.assertNotIn(implementation_version, first)
        self.assertNotIn(owner_version, first)
        self.assertNotIn(r"C:\private", first)

    def test_catalog_revision_payload_schema_version_boundary_matrix(
        self,
    ) -> None:
        cases = (
            (
                "type",
                "Tests.BoundaryType",
                "1",
                (MAX_PAYLOAD_SCHEMA_VERSION,),
                (True, 0, MAX_PAYLOAD_SCHEMA_VERSION + 1),
            ),
            (
                "family",
                "tests.boundary",
                "",
                (0,),
                (True, -1, 1, MAX_PAYLOAD_SCHEMA_VERSION),
            ),
            (
                "conversion",
                "Tests.Source -> Tests.Target",
                "1",
                (0,),
                (True, -1, 1, MAX_PAYLOAD_SCHEMA_VERSION),
            ),
        )
        for kind, identity, implementation_version, accepted, rejected in cases:
            for schema_version in accepted:
                with self.subTest(
                    kind=kind,
                    schema_version=schema_version,
                    expected="accepted",
                ):
                    normalized = normalize_catalog_revisions(
                        (
                            CatalogRevisionRecord(
                                kind=kind,  # type: ignore[arg-type]
                                identity=identity,
                                payload_schema_version=schema_version,
                                implementation_version=implementation_version,
                                owner_id="tests.catalog",
                                owner_version="1",
                                semantic_digest="d" * 64,
                            ),
                        )
                    )
                    self.assertEqual(
                        normalized[0].payload_schema_version,
                        schema_version,
                    )
            for schema_version in rejected:
                with self.subTest(
                    kind=kind,
                    schema_version=schema_version,
                    expected="rejected",
                ):
                    with self.assertRaises(ValueError):
                        normalize_catalog_revisions(
                            (
                                CatalogRevisionRecord(
                                    kind=kind,  # type: ignore[arg-type]
                                    identity=identity,
                                    payload_schema_version=schema_version,
                                    implementation_version=implementation_version,
                                    owner_id="tests.catalog",
                                    owner_version="1",
                                    semantic_digest="d" * 64,
                                ),
                            )
                        )

    def test_malformed_catalog_revision_rejects_before_diagnostic_rendering(
        self,
    ) -> None:
        malformed = CatalogRevisionRecord(
            kind="type",
            identity="Tests.InvalidSchema",
            payload_schema_version=MAX_PAYLOAD_SCHEMA_VERSION + 1,
            implementation_version="1",
            owner_id="tests.catalog",
            owner_version="1",
            semantic_digest="e" * 64,
        )
        worker_catalog = DataTypeCatalog()
        worker_catalog.freeze()

        with patch(
            "ea_node_editor.execution.protocol._trusted_catalog_revision_label"
        ) as formatter:
            with self.assertRaises(ValueError):
                catalog_mismatch_message(
                    "f" * 64,
                    (malformed,),
                    worker_catalog,
                )

        formatter.assert_not_called()

    def test_matching_fingerprint_treats_valid_revisions_as_diagnostics_only(
        self,
    ) -> None:
        catalog = _semantic_catalog()
        fingerprint, records = catalog_agreement(catalog)
        diagnostic_records = list(records)
        diagnostic_records[0] = replace(
            diagnostic_records[0],
            semantic_digest="0" * 64,
        )

        self.assertEqual(
            catalog_mismatch_message(
                fingerprint,
                tuple(diagnostic_records),
                catalog,
            ),
            "",
        )
        with self.assertRaises(ValueError):
            catalog_mismatch_message(
                fingerprint,
                ({"kind": "type"},),
                catalog,
            )

    def test_catalog_revision_identity_accepts_canonical_generic_clr_ids(
        self,
    ) -> None:
        generic_type_id = "Example.Generic`1[[Example.Outer+Inner[]]]"
        catalog = DataTypeCatalog()
        catalog.register_many(
            families=(
                DataTypeFamilySpec(
                    "tests.generic",
                    "Generic",
                    "data.tests",
                    "tests",
                ),
            ),
            types=(
                DataTypeSpec(
                    generic_type_id,
                    "Generic Value",
                    "tests.generic",
                    lambda _value: True,
                ),
            ),
            owner_id="tests.generic",
        )
        catalog.freeze()

        payload = command_to_dict(
            StartRunCommand(
                run_id="run_generic_catalog",
                workspace_id="ws_protocol",
                runtime_snapshot=RuntimeSnapshot(
                    schema_version=1,
                    active_workspace_id="ws_protocol",
                    workspace_order=("ws_protocol",),
                    workspaces=(
                        RuntimeWorkspace(
                            document_fields={"workspace_id": "ws_protocol"},
                        ),
                    ),
                ),
            ),
            catalog=catalog,
        )
        restored = dict_to_command(payload, catalog=catalog)

        self.assertEqual(restored.catalog_fingerprint, catalog.fingerprint())
        self.assertTrue(
            any(
                record.identity == generic_type_id
                for record in restored.catalog_revisions
            )
        )

    def test_start_run_catalog_agreement_rejects_missing_malformed_and_unbounded(
        self,
    ) -> None:
        catalog = _catalog()
        payload = command_to_dict(
            StartRunCommand(
                run_id="run_catalog_validation",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )
        first_revision = copy.deepcopy(payload["catalog_revisions"][0])
        malformed_payloads: list[dict[str, object]] = []

        missing = copy.deepcopy(payload)
        missing.pop("catalog_fingerprint")
        malformed_payloads.append(missing)

        uppercase = copy.deepcopy(payload)
        uppercase["catalog_fingerprint"] = str(
            uppercase["catalog_fingerprint"]
        ).upper()
        malformed_payloads.append(uppercase)

        wrong_container = copy.deepcopy(payload)
        wrong_container["catalog_revisions"] = {}
        malformed_payloads.append(wrong_container)

        extra_field = copy.deepcopy(payload)
        extra_field["catalog_revisions"][0]["source_label"] = "hidden"
        malformed_payloads.append(extra_field)

        boolean_schema = copy.deepcopy(payload)
        boolean_schema["catalog_revisions"][0]["payload_schema_version"] = True
        malformed_payloads.append(boolean_schema)

        oversized_schema = copy.deepcopy(payload)
        type_revision = next(
            revision
            for revision in oversized_schema["catalog_revisions"]
            if revision["kind"] == "type"
        )
        type_revision["payload_schema_version"] = (
            MAX_PAYLOAD_SCHEMA_VERSION + 1
        )
        malformed_payloads.append(oversized_schema)

        missing_digest = copy.deepcopy(payload)
        missing_digest["catalog_revisions"][0].pop("semantic_digest")
        malformed_payloads.append(missing_digest)

        bad_digest = copy.deepcopy(payload)
        bad_digest["catalog_revisions"][0]["semantic_digest"] = "A" * 64
        malformed_payloads.append(bad_digest)

        for field_name, malicious_value in (
            ("owner_version", "/opt/private/catalog.py"),
            ("owner_version", "C:private"),
            ("owner_version", "1\nsecret"),
            ("owner_version", "x" * 129),
            ("implementation_version", r"C:\private\validator.py"),
            ("implementation_version", "C:private"),
            ("implementation_version", "1\nsecret"),
            ("implementation_version", "x" * 129),
        ):
            malicious_revision = copy.deepcopy(payload)
            malicious_revision["catalog_revisions"][0][
                field_name
            ] = malicious_value
            malformed_payloads.append(malicious_revision)

        long_identity = copy.deepcopy(payload)
        long_identity["catalog_revisions"][0]["identity"] = "x" * 1025
        malformed_payloads.append(long_identity)

        path_identity = copy.deepcopy(payload)
        type_revision = next(
            revision
            for revision in path_identity["catalog_revisions"]
            if revision["kind"] == "type"
        )
        type_revision["identity"] = r"C:\private\plugins\CatalogValue"
        malformed_payloads.append(path_identity)

        too_many = copy.deepcopy(payload)
        too_many["catalog_revisions"] = [
            copy.deepcopy(first_revision) for _ in range(4097)
        ]
        malformed_payloads.append(too_many)

        for malformed in malformed_payloads:
            with self.subTest(keys=tuple(malformed)):
                with self.assertRaises(ValueError):
                    dict_to_command(malformed, catalog=catalog)

    def test_semantic_viewer_command_before_worker_catalog_fails_closed(self) -> None:
        catalog = _catalog()
        payload = command_to_dict(
            OpenViewerSessionCommand(
                request_id="viewer_pre_catalog",
                workspace_id="ws_protocol",
                node_id="node_viewer",
                data_refs={
                    "preview": RuntimeArtifactRef.staged(
                        "viewer_pre_catalog",
                        data_type_id=PATH_DATA_TYPE_ID,
                        schema_version=1,
                        format="png",
                        size_bytes=0,
                        sha256="0" * 64,
                        provenance="corex.test.fixture",
                    )
                },
            ),
            catalog=catalog,
        )
        event_queue: queue.Queue = queue.Queue()

        command = decode_command_payload(
            payload,
            event_queue=event_queue,
        )

        self.assertIsNone(command)
        error_event = event_queue.get_nowait()
        self.assertEqual(error_event["type"], "protocol_error")
        self.assertIn("active data-type catalog", error_event["error"])

    def test_raw_start_catalog_mismatch_is_terminal_before_bind_and_decode(
        self,
    ) -> None:
        desktop_catalog = _catalog()
        worker_catalog = _revision_catalog("worker-v1")
        payload = command_to_dict(
            StartRunCommand(
                run_id="run_catalog_mismatch",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=desktop_catalog,
        )
        registry = type("_Registry", (), {"data_types": worker_catalog})()
        runtime_cache = type(
            "_RuntimeCache",
            (),
            {"default_registry": lambda *_args, **_kwargs: registry},
        )()
        services = _TrackingWorkerServices()
        event_queue: queue.Queue = queue.Queue()

        with patch(
            "ea_node_editor.execution.worker_protocol.dict_to_command"
        ) as decode:
            command = decode_command_payload(
                payload,
                event_queue=event_queue,
                runtime_cache=runtime_cache,
                worker_services=services,
            )

        self.assertIsNone(command)
        decode.assert_not_called()
        self.assertEqual(services.bound_catalogs, [])
        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())
        self.assertEqual(
            [event["type"] for event in events],
            ["run_failed", "run_state"],
        )
        self.assertEqual(events[1]["transition"], "fail")
        self.assertEqual(events[1]["reason"], "catalog_mismatch")
        self.assertIn("desktop=", events[0]["error"])
        self.assertIn("worker=", events[0]["error"])
        self.assertNotIn("source_label", events[0]["error"])

    def test_malformed_start_catalog_agreement_is_terminal_before_bind_and_decode(
        self,
    ) -> None:
        catalog = _catalog()
        payload = command_to_dict(
            StartRunCommand(
                run_id="r" * 300,
                workspace_id="workspace\nsecret",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )
        malicious_value = r"C:\private\plugins\credential-value"
        payload["catalog_revisions"][0]["owner_id"] = malicious_value
        registry = type("_Registry", (), {"data_types": catalog})()
        runtime_cache = type(
            "_RuntimeCache",
            (),
            {"default_registry": lambda *_args, **_kwargs: registry},
        )()
        services = _TrackingWorkerServices()
        event_queue: queue.Queue = queue.Queue()

        with patch(
            "ea_node_editor.execution.worker_protocol.dict_to_command"
        ) as decode:
            command = decode_command_payload(
                payload,
                event_queue=event_queue,
                runtime_cache=runtime_cache,
                worker_services=services,
            )

        self.assertIsNone(command)
        decode.assert_not_called()
        self.assertEqual(services.bound_catalogs, [])
        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())
        self.assertEqual(
            [event["type"] for event in events],
            ["protocol_error", "run_failed", "run_state"],
        )
        self.assertTrue(all(event["run_id"] == "r" * 256 for event in events))
        self.assertTrue(all(event["workspace_id"] == "" for event in events))
        self.assertEqual(events[2]["state"], "error")
        self.assertEqual(events[2]["transition"], "fail")
        self.assertEqual(events[2]["reason"], "invalid_start_run")
        self.assertNotIn(
            malicious_value,
            "\n".join(str(event.get("error", "")) for event in events),
        )

    def test_malformed_non_start_command_remains_protocol_error_only(self) -> None:
        event_queue: queue.Queue = queue.Queue()

        command = decode_command_payload(
            {
                "type": "open_viewer_session",
                "request_id": "viewer_bad",
                "data_refs": [],
            },
            event_queue=event_queue,
        )

        self.assertIsNone(command)
        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())
        self.assertEqual([event["type"] for event in events], ["protocol_error"])
        self.assertEqual(events[0]["request_id"], "viewer_bad")

    def test_peer_catalog_fields_never_leak_paths_controls_or_credentials(
        self,
    ) -> None:
        catalog = _catalog()
        registry = type("_Registry", (), {"data_types": catalog})()
        runtime_cache = type(
            "_RuntimeCache",
            (),
            {"default_registry": lambda *_args, **_kwargs: registry},
        )()
        base_payload = command_to_dict(
            StartRunCommand(
                run_id="run_catalog_redaction",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )
        cases = (
            ("owner_id", r"C:\Users\alice\private\plugin.py"),
            ("owner_id", "/opt/private/plugin.py"),
            ("owner_version", r"C:\Users\alice\private\plugin.py"),
            ("implementation_version", "/opt/private/plugin.py"),
            ("identity", "tests.catalog\ninjected-secret"),
        )

        for field_name, peer_value in cases:
            with self.subTest(field_name=field_name):
                payload = copy.deepcopy(base_payload)
                payload["catalog_revisions"][0][field_name] = peer_value
                services = _TrackingWorkerServices()
                event_queue: queue.Queue = queue.Queue()

                command = decode_command_payload(
                    payload,
                    event_queue=event_queue,
                    runtime_cache=runtime_cache,
                    worker_services=services,
                )

                self.assertIsNone(command)
                self.assertEqual(services.bound_catalogs, [])
                events = []
                while not event_queue.empty():
                    events.append(event_queue.get_nowait())
                self.assertTrue(events)
                diagnostic = "\n".join(
                    str(event.get("error", "")) for event in events
                )
                self.assertNotIn(peer_value, diagnostic)
                self.assertNotIn("alice", diagnostic)
                self.assertNotIn("/opt/private", diagnostic)
                self.assertNotIn("credential-value", diagnostic)
                self.assertNotIn("SECRET_TOKEN", diagnostic)
                self.assertNotIn("injected-secret", diagnostic)
                self.assertNotIn("source_label", diagnostic)

    def test_valid_peer_revision_metadata_is_advisory_when_fingerprint_matches(
        self,
    ) -> None:
        catalog = _catalog()
        registry = type("_Registry", (), {"data_types": catalog})()
        runtime_cache = type(
            "_RuntimeCache",
            (),
            {"default_registry": lambda *_args, **_kwargs: registry},
        )()
        base_payload = command_to_dict(
            StartRunCommand(
                run_id="run_catalog_advisory",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )

        for field_name, peer_value in (
            ("owner_version", "peer-version"),
            ("implementation_version", "peer-implementation"),
        ):
            with self.subTest(field_name=field_name):
                payload = copy.deepcopy(base_payload)
                payload["catalog_revisions"][0][field_name] = peer_value
                services = _TrackingWorkerServices()
                event_queue: queue.Queue = queue.Queue()

                command = decode_command_payload(
                    payload,
                    event_queue=event_queue,
                    runtime_cache=runtime_cache,
                    worker_services=services,
                )

                self.assertIsNotNone(command)
                self.assertEqual(services.bound_catalogs, [catalog])
                self.assertTrue(event_queue.empty())

    def test_stdio_catalog_mismatch_is_terminal_before_workflow_launch(self) -> None:
        desktop_catalog = _catalog()
        worker_catalog = _revision_catalog("worker-v1")
        payload = command_to_dict(
            StartRunCommand(
                run_id="run_stdio_catalog_mismatch",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=desktop_catalog,
        )
        registry = type("_Registry", (), {"data_types": worker_catalog})()
        input_stream = io.StringIO(json.dumps(payload) + "\n")
        output_stream = io.StringIO()
        services = _TrackingWorkerServices()

        with (
            patch(
                "ea_node_editor.execution.stdio_worker.WorkerServices",
                return_value=services,
            ),
            patch.object(
                DEFAULT_RUNTIME_PREPARATION_CACHE,
                "default_registry",
                return_value=registry,
            ),
            patch(
                "ea_node_editor.execution.stdio_worker._run_workflow_thread"
            ) as launch,
        ):
            self.assertEqual(stdio_worker_main(input_stream, output_stream), 0)

        launch.assert_not_called()
        self.assertEqual(services.bound_catalogs, [])
        events = [
            json.loads(line)
            for line in output_stream.getvalue().splitlines()
            if line.strip()
        ]
        self.assertEqual(
            [event["type"] for event in events],
            ["run_failed", "run_state"],
        )
        self.assertEqual(events[1]["reason"], "catalog_mismatch")

    def test_protocol_rejects_arbitrary_python_values(self) -> None:
        catalog = _catalog()
        for value in (_UnsupportedDataclass(1), object(), b"bytes", {"set"}):
            with self.subTest(value_type=type(value).__name__):
                command = StartRunCommand(
                    workspace_id="ws_protocol",
                    trigger={"unsafe": value},
                    runtime_snapshot=_typed_snapshot(),
                )
                with self.assertRaises(TypeError):
                    command_to_dict(command, catalog=catalog)

    def test_settlement_and_root_error_use_explicit_adapters(self) -> None:
        catalog = _catalog()
        value_event = NodeSettledEvent(
            run_id="run_protocol",
            workspace_id="ws_protocol",
            node_id="node_protocol",
            outputs={
                "artifact": SettledPortResult(
                    status="value",
                    value=DataTree.from_item(
                        RuntimeArtifactRef.staged(
                            "settled_artifact",
                            data_type_id=PATH_DATA_TYPE_ID,
                            schema_version=1,
                            format="txt",
                            size_bytes=0,
                            sha256="0" * 64,
                            provenance="corex.test.fixture",
                        )
                    ),
                )
            },
        )
        restored_value = dict_to_event(
            event_to_dict(value_event, catalog=catalog),
            catalog=catalog,
        )
        self.assertIsInstance(restored_value, NodeSettledEvent)
        self.assertIsInstance(
            restored_value.outputs["artifact"].value[(0,)][0],
            RuntimeArtifactRef,
        )

        failed_event = NodeSettledEvent(
            node_id="node_protocol",
            status="failed",
            errors=(
                RootExecutionError(
                    node_id="root_node",
                    error="failed",
                    traceback="trace",
                ),
            ),
        )
        restored_failed = dict_to_event(event_to_dict(failed_event))
        self.assertEqual(restored_failed.errors, failed_event.errors)

    def test_protocol_round_trips_composite_runtime_tree_with_active_catalog(
        self,
    ) -> None:
        catalog = _catalog()
        secret = {
            "__ea_runtime_value__": "secret_data",
            "revision": 1,
            "provider": "windows_dpapi",
            "scope": "CurrentUser",
            "ciphertext_b64": "opaque",
        }
        host = {
            "__ea_runtime_value__": "ssh_sftp_host_data",
            "revision": 1,
            "address": "example.invalid",
            "port": 22,
            "username": "tester",
            "password": secret,
            "private_key_path": "",
            "private_key_passphrase": None,
            "use_openssh_agent": False,
            "use_pageant": False,
        }
        event = NodeSettledEvent(
            outputs={
                "result": SettledPortResult(
                    status="value",
                    value=DataTree.from_item(
                        {
                            "interval": Interval1D(5, 1),
                            "table": TabularDataRef(
                                ref_id="table-protocol",
                                resolver_id="tabular.cache",
                            ),
                            "array": ArrayDataRef(
                                ref_id="array-protocol",
                                resolver_id="array.cache",
                            ),
                            "secret": secret,
                            "host": host,
                        }
                    ),
                )
            }
        )

        restored = dict_to_event(
            json.loads(json.dumps(event_to_dict(event, catalog=catalog))),
            catalog=catalog,
        )
        item = restored.outputs["result"].value[(0,)][0]

        self.assertEqual(item["interval"], Interval1D(5, 1))
        self.assertIsInstance(item["table"], TabularDataRef)
        self.assertIsInstance(item["array"], ArrayDataRef)
        self.assertEqual(item["secret"], secret)
        self.assertEqual(item["host"], host)

    def test_query_options_and_strict_composite_fields_round_trip(self) -> None:
        command = QueryViewerSessionCommand(
            request_id="query_protocol",
            workspace_id="ws_protocol",
            node_id="node_protocol",
            session_id="session_protocol",
            query_type="distance",
            payload={"points": [[0, 0, 0], [1, 0, 0]]},
            options={"precision": 4},
        )
        payload = command_to_dict(command)
        restored = dict_to_command(payload)
        self.assertEqual(restored.options, {"precision": 4})

        payload["options"] = "malformed"
        with self.assertRaisesRegex(ValueError, "options must be a dictionary"):
            dict_to_command(payload)

    def test_scalar_protocol_traffic_remains_catalog_free(self) -> None:
        self.assertIsInstance(
            dict_to_command(command_to_dict(ShutdownCommand())),
            ShutdownCommand,
        )
        event = ProtocolErrorEvent(command="shutdown", error="bad command")
        self.assertEqual(dict_to_event(event_to_dict(event)), event)

    def test_process_client_fails_before_queue_put(self) -> None:
        client = object.__new__(ProcessExecutionClient)
        client._data_types = _catalog()  # noqa: SLF001
        client._command_queue = _RecordingQueue()  # noqa: SLF001
        client._callbacks = []  # noqa: SLF001
        client._state_lock = threading.Lock()  # noqa: SLF001
        client._active_workspace_id = ""  # noqa: SLF001
        command = StartRunCommand(
            workspace_id="ws_protocol",
            trigger={"unsafe": object()},
            runtime_snapshot=_typed_snapshot(),
        )

        success, _message = client._try_post_command(command)  # noqa: SLF001

        self.assertFalse(success)
        self.assertEqual(client._command_queue.items, [])  # noqa: SLF001

    def test_malformed_outbound_runtime_documents_fail_before_queue_put(
        self,
    ) -> None:
        base = _typed_snapshot()
        workspace = base.workspaces[0]
        node = workspace.nodes[0]
        malformed_snapshots = {
            "schema_version": replace(
                base,
                schema_version="bad",  # type: ignore[arg-type]
            ),
            "node_x": replace(
                base,
                workspaces=(
                    replace(
                        workspace,
                        nodes=(
                            replace(
                                node,
                                x="bad",  # type: ignore[arg-type]
                            ),
                        ),
                    ),
                ),
            ),
            "node_properties": replace(
                base,
                workspaces=(
                    replace(
                        workspace,
                        nodes=(
                            replace(
                                node,
                                properties="bad",  # type: ignore[arg-type]
                            ),
                        ),
                    ),
                ),
            ),
            "edge_input_order": replace(
                base,
                workspaces=(
                    replace(
                        workspace,
                        edges=(
                            RuntimeEdge(
                                source_node_id=node.node_id,
                                source_port_key="value",
                                target_node_id=node.node_id,
                                target_port_key="value",
                                input_order="bad",  # type: ignore[arg-type]
                            ),
                        ),
                    ),
                ),
            ),
            "nested_view_zoom": replace(
                base,
                workspaces=(
                    replace(
                        workspace,
                        document_fields={
                            "workspace_id": "ws_protocol",
                            "views": [
                                {
                                    "view_id": "view",
                                    "zoom": "bad",
                                }
                            ],
                        },
                    ),
                ),
            ),
        }
        client = object.__new__(ProcessExecutionClient)
        client._data_types = _catalog()  # noqa: SLF001
        client._command_queue = _RecordingQueue()  # noqa: SLF001
        client._callbacks = []  # noqa: SLF001
        client._state_lock = threading.Lock()  # noqa: SLF001
        client._active_workspace_id = ""  # noqa: SLF001

        for field_name, snapshot in malformed_snapshots.items():
            command = StartRunCommand(
                run_id=f"run_{field_name}",
                workspace_id="ws_protocol",
                runtime_snapshot=snapshot,
            )
            with self.subTest(field_name=field_name):
                with self.assertRaises((TypeError, ValueError)):
                    command_to_dict(command, catalog=client._data_types)  # noqa: SLF001
                success, _message = client._try_post_command(command)  # noqa: SLF001
                self.assertFalse(success)
                self.assertEqual(client._command_queue.items, [])  # noqa: SLF001

    def test_external_client_fails_before_stdin_write(self) -> None:
        client = object.__new__(ExternalPythonExecutionClient)
        process = _RunningExternalProcess()
        client._data_types = _catalog()  # noqa: SLF001
        client._process = process  # noqa: SLF001
        client._stdin_lock = threading.Lock()  # noqa: SLF001
        client._callbacks = []  # noqa: SLF001
        client._state_lock = threading.Lock()  # noqa: SLF001
        client._active_workspace_id = ""  # noqa: SLF001
        command = StartRunCommand(
            workspace_id="ws_protocol",
            trigger={"unsafe": object()},
            runtime_snapshot=_typed_snapshot(),
        )

        success, _message = client._try_post_command(command)  # noqa: SLF001

        self.assertFalse(success)
        self.assertEqual(process.stdin.writes, [])
        self.assertEqual(process.stdin.flush_count, 0)

    def test_trusted_client_fails_before_run_thread_start(self) -> None:
        client = TrustedInProcessExecutionClient()
        try:
            run_id = client.start_run(
                "",
                "ws_protocol",
                {
                    "runtime_snapshot": _typed_snapshot(),
                    "unsafe": object(),
                },
                data_types=_catalog(),
            )

            self.assertEqual(run_id, "")
            self.assertIsNone(client._run_thread)  # noqa: SLF001
        finally:
            client.shutdown()

    def test_worker_event_fails_before_queue_put(self) -> None:
        event_queue = _RecordingQueue()
        event = NodeSettledEvent(
            outputs={
                "artifact": SettledPortResult(
                    status="value",
                    value=DataTree.from_item(
                        RuntimeArtifactRef.staged(
                            "event_artifact",
                            data_type_id=PATH_DATA_TYPE_ID,
                            schema_version=1,
                            format="txt",
                            size_bytes=0,
                            sha256="0" * 64,
                            provenance="corex.test.fixture",
                        )
                    ),
                )
            }
        )

        with self.assertRaisesRegex(ValueError, "active data-type catalog"):
            emit(event_queue, event)
        self.assertEqual(event_queue.items, [])

    def test_runtime_snapshot_rejects_present_malformed_full_schema_fields(
        self,
    ) -> None:
        catalog = _catalog()
        payload = command_to_dict(
            StartRunCommand(
                run_id="run_schema",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )
        workspace = payload["runtime_snapshot"]["workspaces"][0]
        workspace["document_fields"].update(
            {
                "name": "Workspace",
                "dirty": False,
                "active_view_id": "view",
                "views": [
                    {
                        "view_id": "view",
                        "name": "View",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                        "scope_path": [],
                    }
                ],
            }
        )
        workspace["edges"] = [
            {
                "edge_id": "edge",
                "source_node_id": "node_protocol",
                "source_port_key": "value",
                "target_node_id": "node_protocol",
                "target_port_key": "value",
                "enabled": True,
                "input_order": 0,
                "label": "",
                "visual_style": {},
            }
        ]

        malformed_paths = (
            (("runtime_snapshot", "schema_version"), "bad"),
            (("runtime_snapshot", "metadata"), "bad"),
            (("runtime_snapshot", "workspace_order"), "bad"),
            (("runtime_snapshot", "workspace_order", 0), 42),
            (("runtime_snapshot", "workspaces", 0, "document_fields"), "bad"),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "document_fields",
                    "dirty",
                ),
                "bad",
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "document_fields",
                    "views",
                ),
                "bad",
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "document_fields",
                    "views",
                    0,
                    "zoom",
                ),
                "bad",
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "document_fields",
                    "views",
                    0,
                    "scope_path",
                ),
                "bad",
            ),
            (
                ("runtime_snapshot", "workspaces", 0, "nodes", 0, "properties"),
                "bad",
            ),
            (
                ("runtime_snapshot", "workspaces", 0, "nodes", 0, "x"),
                "bad",
            ),
            (
                ("runtime_snapshot", "workspaces", 0, "nodes", 0, "collapsed"),
                1,
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "nodes",
                    0,
                    "exposed_ports",
                ),
                "bad",
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "nodes",
                    0,
                    "port_labels",
                ),
                "bad",
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "nodes",
                    0,
                    "port_modifiers",
                ),
                {"value": "bad"},
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "nodes",
                    0,
                    "visual_style",
                ),
                "bad",
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "nodes",
                    0,
                    "custom_width",
                ),
                "bad",
            ),
            (
                ("runtime_snapshot", "workspaces", 0, "edges", 0, "enabled"),
                "bad",
            ),
            (
                ("runtime_snapshot", "workspaces", 0, "edges", 0, "input_order"),
                "bad",
            ),
            (
                (
                    "runtime_snapshot",
                    "workspaces",
                    0,
                    "edges",
                    0,
                    "visual_style",
                ),
                "bad",
            ),
        )

        for path, malformed_value in malformed_paths:
            with self.subTest(path=path):
                malformed = copy.deepcopy(payload)
                target = malformed
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = malformed_value
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_command(malformed, catalog=catalog)

    def test_protocol_rejects_present_malformed_dto_fields(self) -> None:
        catalog = _catalog()
        start_payload = command_to_dict(
            StartRunCommand(
                run_id="run_schema",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )
        start_cases = {
            "trigger": "bad",
            "execution_backend": "bad",
            "target_node_ids": 42,
            "trigger_publications": [],
            "trigger_captures": [],
            "clicked_trigger_node_id": 42,
            "developer_mode": "bad",
        }
        for field_name, malformed_value in start_cases.items():
            with self.subTest(command_field=field_name):
                malformed = copy.deepcopy(start_payload)
                malformed[field_name] = malformed_value
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_command(malformed, catalog=catalog)

        command_payload = command_to_dict(
            OpenViewerSessionCommand(
                request_id="viewer",
                workspace_id="ws_protocol",
                node_id="node_protocol",
            )
        )
        for field_name, malformed_value in {
            "request_id": 42,
            "transport_revision": "bad",
            "live_open_status": 42,
            "data_refs": [],
        }.items():
            with self.subTest(viewer_command_field=field_name):
                malformed = copy.deepcopy(command_payload)
                malformed[field_name] = malformed_value
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_command(malformed)

        event_cases = (
            (
                {
                    "type": "node_started",
                    "started_at_epoch_ms": "bad",
                },
                "started_at_epoch_ms",
            ),
            (
                {
                    "type": "node_settled",
                    "elapsed_ms": "bad",
                    "outputs": {},
                    "errors": [],
                    "warnings": [],
                },
                "elapsed_ms",
            ),
            (
                {
                    "type": "node_settled",
                    "outputs": {},
                    "errors": [],
                    "warnings": 42,
                },
                "warnings",
            ),
            (
                {
                    "type": "node_settled",
                    "outputs": {},
                    "errors": 42,
                    "warnings": [],
                },
                "errors",
            ),
            (
                {
                    "type": "run_failed",
                    "fatal": "bad",
                },
                "fatal",
            ),
            (
                {
                    "type": "viewer_query_result",
                    "supported": "bad",
                    "value": {},
                },
                "supported",
            ),
        )
        for malformed, field_name in event_cases:
            with self.subTest(event_field=field_name):
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_event(malformed)

        with self.assertRaises((TypeError, ValueError)):
            command_to_dict(
                OpenViewerSessionCommand(
                    transport_revision="bad",  # type: ignore[arg-type]
                )
            )
        with self.assertRaises((TypeError, ValueError)):
            event_to_dict(
                NodeSettledEvent(
                    elapsed_ms="bad",  # type: ignore[arg-type]
                )
            )
        with self.assertRaises((TypeError, ValueError)):
            event_to_dict(
                NodeSettledEvent(
                    warnings=42,  # type: ignore[arg-type]
                )
            )

    def test_protocol_missing_optional_fields_keep_defaults(self) -> None:
        catalog = _catalog()
        payload = command_to_dict(
            StartRunCommand(
                run_id="run_defaults",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
            ),
            catalog=catalog,
        )
        for field_name in (
            "trigger",
            "execution_backend",
            "target_node_ids",
            "trigger_publications",
            "trigger_captures",
            "clicked_trigger_node_id",
            "developer_mode",
        ):
            payload.pop(field_name)
        restored = dict_to_command(payload, catalog=catalog)
        self.assertEqual(restored.trigger, {})
        self.assertEqual(restored.target_node_ids, ())
        self.assertEqual(restored.trigger_publications, {})
        self.assertEqual(restored.trigger_captures, {})
        self.assertFalse(restored.developer_mode)

        settled = dict_to_event({"type": "node_settled"})
        self.assertEqual(settled.elapsed_ms, 0.0)
        self.assertEqual(settled.outputs, {})
        self.assertEqual(settled.errors, ())
        self.assertEqual(settled.warnings, ())

    def test_runtime_node_optional_dimensions_preserve_none_and_require_numbers(
        self,
    ) -> None:
        required_fields = {
            "node_id": "node_dimensions",
            "type_id": "core.constant",
        }
        node = RuntimeNode.from_mapping(required_fields)
        self.assertIsNotNone(node)
        assert node is not None
        self.assertIsNone(node.custom_width)
        self.assertIsNone(node.custom_height)

        for field_name in ("custom_width", "custom_height"):
            for numeric_value in (0, 24, 24.5):
                with self.subTest(field_name=field_name, value=numeric_value):
                    numeric_node = RuntimeNode.from_mapping(
                        {
                            **required_fields,
                            field_name: numeric_value,
                        }
                    )
                    self.assertIsNotNone(numeric_node)
                    assert numeric_node is not None
                    self.assertEqual(
                        getattr(numeric_node, field_name),
                        float(numeric_value),
                    )
            for malformed_value in (True, "24", float("nan"), float("inf")):
                with self.subTest(field_name=field_name, value=malformed_value):
                    with self.assertRaises(ValueError):
                        RuntimeNode.from_mapping(
                            {
                                **required_fields,
                                field_name: malformed_value,
                            }
                        )

    def test_run_lifecycle_states_are_literal_validated_in_both_directions(
        self,
    ) -> None:
        for state in ("ready", "running", "paused", "error"):
            with self.subTest(run_state=state):
                restored = dict_to_event({"type": "run_state", "state": state})
                self.assertEqual(restored.state, state)
                self.assertEqual(
                    dict_to_event(event_to_dict(RunStateEvent(state=state))).state,
                    state,
                )

        for transition in ("", "start", "pause", "resume", "stop", "complete", "fail"):
            with self.subTest(run_transition=transition):
                restored = dict_to_event(
                    {
                        "type": "run_state",
                        "transition": transition,
                    }
                )
                self.assertEqual(restored.transition, transition)

        for field_name, malformed_value in (
            ("state", 42),
            ("state", []),
            ("state", "bogus"),
            ("transition", 42),
            ("transition", []),
            ("transition", "bogus"),
        ):
            with self.subTest(field_name=field_name, value=malformed_value):
                with self.assertRaises((TypeError, ValueError)):
                    dict_to_event(
                        {
                            "type": "run_state",
                            field_name: malformed_value,
                        }
                    )

        fixed_events = (
            ("run_completed", "ready", RunCompletedEvent),
            ("run_failed", "error", RunFailedEvent),
            ("run_stopped", "ready", RunStoppedEvent),
        )
        for event_type, expected_state, event_class in fixed_events:
            with self.subTest(event_type=event_type, state="missing"):
                self.assertEqual(
                    dict_to_event({"type": event_type}).state,
                    expected_state,
                )
            with self.subTest(event_type=event_type, state="expected"):
                self.assertEqual(
                    dict_to_event(
                        {
                            "type": event_type,
                            "state": expected_state,
                        }
                    ).state,
                    expected_state,
                )
                self.assertEqual(
                    dict_to_event(event_to_dict(event_class())).state,
                    expected_state,
                )
            for malformed_value in (42, [], "bad", "bogus"):
                with self.subTest(
                    event_type=event_type,
                    malformed_state=malformed_value,
                ):
                    with self.assertRaises((TypeError, ValueError)):
                        dict_to_event(
                            {
                                "type": event_type,
                                "state": malformed_value,
                            }
                        )

        malformed_outbound_events = (
            RunStateEvent(state=42),  # type: ignore[arg-type]
            RunStateEvent(state="bogus"),  # type: ignore[arg-type]
            RunStateEvent(transition=[]),  # type: ignore[arg-type]
            RunStateEvent(transition="bogus"),
            RunCompletedEvent(state=42),  # type: ignore[arg-type]
            RunCompletedEvent(state="bad"),  # type: ignore[arg-type]
            RunFailedEvent(state=[]),  # type: ignore[arg-type]
            RunFailedEvent(state="bad"),  # type: ignore[arg-type]
            RunStoppedEvent(state=42),  # type: ignore[arg-type]
            RunStoppedEvent(state="bad"),  # type: ignore[arg-type]
        )
        for event in malformed_outbound_events:
            with self.subTest(event=event):
                with self.assertRaises((TypeError, ValueError)):
                    event_to_dict(event)

    def test_active_stdio_rejects_duplicate_start_before_registry_rebind(self) -> None:
        registry = build_default_registry()
        catalog = registry.data_types
        DEFAULT_RUNTIME_PREPARATION_CACHE.clear()
        first = command_to_dict(
            StartRunCommand(
                run_id="run_a",
                workspace_id="ws_protocol",
                runtime_snapshot=_typed_snapshot(),
                registry_contract_fingerprint=registry.contract_fingerprint(),
                addon_runtime_config=registry.addon_runtime_config(),
            ),
            catalog=catalog,
        )
        second = copy.deepcopy(first)
        second["run_id"] = "run_b"
        second["runtime_snapshot"]["workspaces"][0]["nodes"][0]["type_id"] = "math.add"
        input_stream = io.StringIO(json.dumps(first) + "\n" + json.dumps(second) + "\n")
        output_stream = io.StringIO()
        services = _TrackingWorkerServices()

        def hold_active_run(*args, **kwargs) -> None:  # noqa: ANN002, ANN003
            time.sleep(0.2)

        with (
            patch(
                "ea_node_editor.execution.stdio_worker.WorkerServices",
                return_value=services,
            ),
            patch(
                "ea_node_editor.execution.stdio_worker._run_workflow_thread",
                side_effect=hold_active_run,
            ),
        ):
            self.assertEqual(stdio_worker_main(input_stream, output_stream), 0)

        self.assertEqual(len(services.bound_catalogs), 1)
        events = [
            json.loads(line)
            for line in output_stream.getvalue().splitlines()
            if line.strip()
        ]
        self.assertTrue(
            any(
                event.get("type") == "protocol_error"
                and "active run" in str(event.get("error", ""))
                for event in events
            )
        )

    def test_active_run_control_rejects_raw_start_before_decode(self) -> None:
        command_queue: queue.Queue = queue.Queue()
        event_queue: queue.Queue = queue.Queue()
        command_queue.put(
            {
                "type": "start_run",
                "run_id": "run_b",
                "workspace_id": "ws_b",
                "runtime_snapshot": {"properties": "bad"},
            }
        )
        control = RunControl(
            command_queue,
            event_queue,
            run_id="run_a",
            workspace_id="ws_a",
            data_types=_catalog(),
        )

        with patch(
            "ea_node_editor.execution.worker_runner.decode_command_payload"
        ) as decode:
            control.poll_commands()

        decode.assert_not_called()
        event = event_queue.get_nowait()
        self.assertEqual(event["type"], "protocol_error")
        self.assertIn("active run", event["error"])


if __name__ == "__main__":
    unittest.main()
