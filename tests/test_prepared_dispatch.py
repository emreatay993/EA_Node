# Purpose: Prove sealed projections, raw admission and immutable generation metadata.
# Map: subsystems/execution.md
# Tests: this file
from __future__ import annotations

from dataclasses import replace
import queue
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ea_node_editor.execution import registry_agreement
from ea_node_editor.execution.prepared_dispatch import PreparedRunDispatch
from ea_node_editor.execution.prepared_execution import (
    AcceptedOutputPayload,
    PreparedAction,
    PreparedExecution,
    PreparedNodeDecision,
    validate_current_output_payload,
)
from ea_node_editor.execution.protocol_codec import command_to_dict, dict_to_command
from ea_node_editor.execution.registry_agreement import RegistryAgreement
from ea_node_editor.execution.viewer_messages import viewer_epoch_snapshot_digest
from ea_node_editor.execution.worker_protocol import decode_command_payload
from ea_node_editor.runtime_contracts import (
    DataTree,
    DataTypeCatalog,
    DataTypeFamilySpec,
    DataTypeSpec,
    STRING_DATA_TYPE_ID,
    TypedInlineValue,
)
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.runtime_contracts.solution_records import SolutionResidency
from tests.test_solution_records import _dispatch_envelope


@pytest.fixture
def dispatch():
    envelope, registry, _snapshot = _dispatch_envelope()
    node_id = envelope.target_node_ids[0]
    decision = PreparedNodeDecision(
        node_id, PreparedAction.EXECUTE, "new", "a" * 64, ()
    )
    prepared = PreparedExecution(
        preparation_id="preparation-test",
        dispatch_envelope=envelope,
        solution_namespace_id="session-test",
        execution_affecting_workspace_revision=0,
        runtime_snapshot_fingerprint="b" * 64,
        execution_plan_fingerprint="c" * 64,
        registry_contract_fingerprint=registry.contract_fingerprint(),
        workflow_interface_revision=1,
        workflow_interface_digest="d" * 64,
        execution_environment_digest="e" * 64,
        trigger_publication_generations=(),
        node_decisions=(decision,),
        accepted_output_payloads=(),
        recompute_node_ids=(node_id,),
        reused_node_ids=(),
    )
    value = PreparedRunDispatch(
        prepared,
        "run-test",
        7,
        (),
        0,
        (),
        "viewer-reservation",
        viewer_epoch_snapshot_digest(
            workspace_id=envelope.workspace_id,
            node_ids=(),
            workspace_epoch=0,
            node_epochs=(),
        ),
    )
    return value, registry


def test_prepared_wire_projection_matches_the_existing_complete_wire_contract(dispatch):
    value, registry = dispatch
    payload = value.to_payload()
    assert payload == command_to_dict(
        value.materialize(registry.data_types), catalog=registry.data_types
    )
    decoded = dict_to_command(payload, catalog=registry.data_types)
    assert decoded.preparation_id == value.prepared.preparation_id
    assert decoded.viewer_epoch_snapshot_digest == value.viewer_epoch_snapshot_digest


def test_projections_do_not_reenter_admission_and_return_detached_values(dispatch):
    value, registry = dispatch
    with (
        patch.object(
            PreparedExecution, "from_payload", side_effect=AssertionError("re-admitted")
        ),
        patch(
            "ea_node_editor.execution.protocol_codec.coerce_start_run_command",
            side_effect=AssertionError("re-admitted"),
        ),
    ):
        first = value.prepared.to_payload(catalog=registry.data_types)
        first["dispatch_envelope"]["trigger"]["alias_probe"]["items"].append(2)
        first = value.to_payload()
        first["runtime_snapshot"]["metadata"]["alias_probe"]["items"].append(3)
        command = value.materialize(registry.data_types)
        command.trigger["alias_probe"]["items"].append(4)
        assert value.to_payload()["trigger"]["alias_probe"]["items"] == [1]
        assert value.to_payload()["runtime_snapshot"]["metadata"]["alias_probe"][
            "items"
        ] == [1]


def test_raw_worker_admits_each_catalog_record_once(dispatch):
    value, registry = dispatch
    events = queue.Queue()
    cache = SimpleNamespace(default_registry=lambda _configuration: registry)
    with patch.object(
        registry_agreement,
        "_catalog_revision_values",
        wraps=registry_agreement._catalog_revision_values,
    ) as validate:
        command = decode_command_payload(
            value.to_payload(), event_queue=events, runtime_cache=cache
        )
    assert command is not None
    assert validate.call_count == len(
        value.prepared.dispatch_envelope.catalog_revisions
    )


def test_matching_fingerprint_cannot_hide_malformed_raw_metadata(dispatch):
    value, registry = dispatch
    payload = value.to_payload()
    payload["catalog_revisions"][0]["owner_id"] = "invalid\nowner"
    events = queue.Queue()
    with patch(
        "ea_node_editor.execution.runtime_snapshot.RuntimeSnapshot.from_mapping",
        side_effect=AssertionError("decoded before admission"),
    ):
        assert (
            decode_command_payload(
                payload,
                event_queue=events,
                runtime_cache=SimpleNamespace(
                    default_registry=lambda _configuration: registry
                ),
            )
            is None
        )
    assert any(event["type"] == "protocol_error" for event in events.queue)


def test_registry_agreement_does_not_retain_mutable_payloads(dispatch):
    value, registry = dispatch
    agreement = RegistryAgreement.from_registry(registry)
    raw = agreement.to_payload()
    captured = RegistryAgreement.from_payload(raw)
    raw["catalog_revisions"][0]["identity"] = "changed"
    raw["plugin_bundles"].clear()
    assert captured == agreement
    assert captured.to_payload() == agreement.to_payload()


def test_aggregate_payload_limit_is_enforced_during_construction(dispatch):
    value, registry = dispatch
    prepared = value.prepared
    node = prepared.node_decisions[0].node_id
    output = AcceptedOutputPayload(
        node_id=node,
        record_id="record",
        solution_key="a" * 64,
        settlement_status="completed",
        result_digest="b" * 64,
        residency=SolutionResidency.SESSION,
        runtime_generation=7,
        outputs={
            "result": SettledPortResult(
                status="value", value=DataTree.from_item("value")
            )
        },
        catalog=registry.data_types,
    )
    decision = PreparedNodeDecision(
        node,
        PreparedAction.REUSE,
        "current",
        "a" * 64,
        (),
        accepted_record_id=output.record_id,
        accepted_payload_digest=output.commitment_digest(),
    )
    with patch(
        "ea_node_editor.execution.prepared_execution.MAX_ACCEPTED_OUTPUT_PAYLOAD_BYTES",
        output.encoded_size,
    ):
        with pytest.raises(ValueError, match="maximum encoded size"):
            replace(
                prepared,
                node_decisions=(decision,),
                accepted_output_payloads=(output,),
                recompute_node_ids=(),
                reused_node_ids=(node,),
            )


def reuse_preparation(value, output):
    node = value.prepared.node_decisions[0].node_id
    decision = PreparedNodeDecision(
        node,
        PreparedAction.READ_CURRENT,
        "current",
        "a" * 64,
        (),
        accepted_record_id=output.record_id,
        accepted_payload_digest=output.commitment_digest(),
    )
    return replace(
        value.prepared,
        node_decisions=(decision,),
        accepted_output_payloads=(output,),
        recompute_node_ids=(),
        reused_node_ids=(node,),
    )


def test_session_output_generation_is_bound_before_dispatch(dispatch):
    value, registry = dispatch
    output = AcceptedOutputPayload(
        node_id=value.prepared.node_decisions[0].node_id,
        record_id="record",
        solution_key="a" * 64,
        settlement_status="completed",
        result_digest="b" * 64,
        residency=SolutionResidency.SESSION,
        runtime_generation=8,
        outputs={
            "result": SettledPortResult(
                status="value", value=DataTree.from_item("value")
            )
        },
        catalog=registry.data_types,
    )
    with pytest.raises(ValueError, match="generation must match"):
        replace(value, prepared=reuse_preparation(value, output))


@pytest.mark.parametrize("name", ["preparation_id", "solution_namespace_id"])
def test_prepared_identity_rejects_embedded_control_characters(dispatch, name):
    value, _registry = dispatch
    with pytest.raises(ValueError):
        replace(value.prepared, **{name: "first\nsecond"})


def test_output_consumption_revalidates_the_active_catalog(dispatch):
    value, registry = dispatch
    alternate = DataTypeCatalog()
    alternate.register_many(
        families=(DataTypeFamilySpec("tests.family", "Tests", "data", ""),),
        types=(
            DataTypeSpec(
                STRING_DATA_TYPE_ID,
                "String",
                "tests.family",
                lambda _value: True,
                carriers=frozenset({"inline"}),
                persistence="inline",
            ),
        ),
        owner_id="tests.alternate",
    )
    alternate.freeze()
    output = AcceptedOutputPayload(
        node_id=value.prepared.node_decisions[0].node_id,
        record_id="record",
        solution_key="a" * 64,
        settlement_status="completed",
        result_digest="b" * 64,
        residency=SolutionResidency.SESSION,
        runtime_generation=7,
        outputs={
            "result": SettledPortResult(
                status="value",
                value=DataTree.from_item(
                    TypedInlineValue(STRING_DATA_TYPE_ID, 1, {"value": "inline"})
                ),
            )
        },
        catalog=alternate,
    )
    other = replace(value, prepared=reuse_preparation(value, output))
    with pytest.raises(ValueError):
        other.materialize(registry.data_types)
    with pytest.raises(ValueError):
        validate_current_output_payload(
            output, catalog=registry.data_types, port_keys=("result",)
        )


def test_matching_unfrozen_catalog_is_rejected(dispatch):
    value, registry = dispatch
    unfrozen = registry.data_types.fork()
    assert unfrozen.fingerprint() == registry.data_types.fingerprint()
    with pytest.raises(ValueError):
        value.materialize(unfrozen)
    with pytest.raises(ValueError, match="frozen"):
        registry_agreement.catalog_mismatch_message(
            value.prepared.dispatch_envelope.catalog_fingerprint,
            value.prepared.dispatch_envelope.catalog_revisions,
            unfrozen,
        )


def test_backend_and_function_sequences_do_not_retain_subclass_aliases(dispatch):
    from ea_node_editor.execution.backends import ExecutionBackendSelection

    value, registry = dispatch

    class Backend(ExecutionBackendSelection):
        pass

    envelope = replace(
        value.prepared.dispatch_envelope,
        execution_backend=Backend(),
        catalog=registry.data_types,
    )
    assert type(envelope.execution_backend) is ExecutionBackendSelection
    original = registry.plugin_bundle_refs()[0]
    functions = list(original.functions)

    class FunctionSequence(tuple):
        def __iter__(self):
            return iter(functions)

    bundle = replace(original, functions=FunctionSequence(original.functions))
    functions.clear()
    assert type(bundle.functions) is tuple
    assert bundle.functions == original.functions
