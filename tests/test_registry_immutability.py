# Purpose: Prove registry generations and declaration values have no mutable aliases.
# Map: subsystems/nodes_registry_builtins.md
# Tests: this file
from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

import pytest

from ea_node_editor.nodes.node_specs import NodeTypeSpec, PropertySpec
from ea_node_editor.nodes.plugin_contracts import ArtifactDescriptor
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import Interval1D, TypedInlineValue


def spec(name="tests.immutable", properties=()):
    return NodeTypeSpec(name, "Immutable", ("Tests",), "", (), properties)


def factory():
    raise AssertionError("Registry operations must not construct plugins")


def test_default_capture_detaches_nested_values_and_preserves_container_kinds():
    original = {"list": [1, {"pair": (2, [3])}], "range": Interval1D(0, 4)}
    prop = PropertySpec("value", "json", original, "Value")
    original["list"][1]["pair"][1].append(99)
    first = prop.make_default()
    second = prop.make_default()
    assert (
        first == second == {"list": [1, {"pair": (2, [3])}], "range": Interval1D(0, 4)}
    )
    first["list"][1]["pair"][1].append(7)
    assert prop.make_default() == second
    changed = prop.with_changes(label="Other")
    assert changed.label == "Other" and changed.make_default() == second
    with pytest.raises(FrozenInstanceError):
        prop.label = "Changed"


def test_typed_default_payload_has_independent_ownership():
    original = TypedInlineValue("Example.Point", 1, {"coordinates": [1, 2, 3]})
    prop = PropertySpec("point", "json", original, "Point")
    original.payload["coordinates"][0] = 100
    first = prop.make_default()
    first.payload["coordinates"][1] = 200
    assert prop.make_default().payload == {"coordinates": [1, 2, 3]}


def test_mapping_default_equality_preserves_mapping_semantics():
    a = PropertySpec("value", "json", {"a": 1, "b": 2}, "Value")
    b = PropertySpec("value", "json", {"b": 2, "a": 1}, "Value")
    assert a == b
    assert list(a.make_default()) == ["a", "b"]
    assert list(b.make_default()) == ["b", "a"]


def test_default_cycles_and_opaque_objects_are_rejected_at_capture():
    value = []
    value.append(value)
    with pytest.raises(ValueError, match="cycles"):
        PropertySpec("value", "json", value, "Value")
    with pytest.raises(TypeError, match="Unsupported"):
        PropertySpec("value", "json", {"opaque": object()}, "Value")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda registry: registry.register(factory),
        lambda registry: registry.register_descriptor(spec(), factory),
        lambda registry: registry.register_descriptors(()),
        lambda registry: registry.register_plugin_bundle(
            None, (), owner_id="tests.owner"
        ),
        lambda registry: registry.register_python_function(None, None),
        lambda registry: registry._register_trusted_python_function(None, None),
        lambda registry: registry.set_python_plugin_catalog(
            (), plugin_fingerprint="0" * 64
        ),
        lambda registry: registry.set_addon_runtime_config(()),
    ],
)
def test_published_registry_rejects_every_mutation_before_work(mutate):
    registry = NodeRegistry()
    registry.freeze()
    before = registry.contract_fingerprint()
    with pytest.raises(ValueError, match="frozen"):
        mutate(registry)
    assert registry.contract_fingerprint() == before
    assert registry.all_specs() == []


def test_fork_stages_independently_and_freeze_is_idempotent():
    registry = NodeRegistry()
    registry.register_descriptor(spec(), factory)
    registry.freeze()
    before = registry.contract_fingerprint()
    child = registry.fork()
    assert registry.is_frozen and not child.is_frozen and not child.data_types.is_frozen
    child.register_descriptor(spec("tests.child"), factory)
    child.freeze()
    child.freeze()
    assert child.is_frozen and child.contract_fingerprint() != before
    assert registry.contract_fingerprint() == before
    assert registry.spec_or_none("tests.child") is None
    assert len(registry.trusted_runtime_copy().all_specs()) == 1


def test_frozen_catalog_facts_do_not_rebuild_or_expose_mutable_records():
    registry = NodeRegistry()
    catalog = registry.data_types
    expected = catalog.fingerprint()
    catalog.freeze()
    with patch.object(
        catalog, "_snapshot_records", Mock(side_effect=AssertionError("rebuilt"))
    ):
        assert catalog.fingerprint() == expected
        snapshot = catalog.snapshot()
        assert snapshot is catalog.snapshot()
        with pytest.raises(TypeError):
            snapshot[0]["owner_id"] = "attacker"
        catalog.freeze()
    child = catalog.fork()
    assert not child.is_frozen and child.fingerprint() == expected


def test_artifact_metadata_is_sealed():
    metadata = {"purpose": "input"}
    artifact = ArtifactDescriptor("tests.asset", "python_module", metadata=metadata)
    metadata["purpose"] = "changed"
    assert artifact.metadata["purpose"] == "input"
    with pytest.raises(TypeError):
        artifact.metadata["purpose"] = "changed"
