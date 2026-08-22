from __future__ import annotations

from dataclasses import dataclass

import pytest

from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.core_data_types import (
    GRAPH_ARRAY_DATA_TYPE_ID,
    GRAPH_DICTIONARY_DATA_TYPE_ID,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    ArraySlice2DRef,
    COREX_VIEWER_SESSION_HANDLE_KIND,
    DataTree,
    DataTypeCatalog,
    DataTypeCatalogError,
    DataTypeFamilySpec,
    DataTypeSpec,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    Interval1D,
    RuntimeArtifactRef,
    RuntimeHandleRef,
    TABULAR_DATA_REF_TYPE_ID,
    TabularDataRef,
    TabularWindowRef,
    TypedInlineValue,
    VIEWER_SESSION_DATA_TYPE_ID,
    deserialize_runtime_value,
    serialize_runtime_value,
)

ROOT_TYPE = "Test.Runtime.Root"
INLINE_TYPE = "Test.Runtime.Inline"
HANDLE_TYPE = "Test.Runtime.Handle"
ARTIFACT_TYPE = "Test.Runtime.Artifact"
NATIVE_TYPE = "Test.Runtime.Native"
SECRET_TYPE = "Test.Runtime.Secret"
ARTIFACT_SIZE_BYTES = 12
ARTIFACT_SHA256 = "a" * 64
ARTIFACT_PROVENANCE = "corex.test.fixture"


def _catalog() -> DataTypeCatalog:
    catalog = DataTypeCatalog()
    catalog.register_many(
        families=(
            DataTypeFamilySpec(
                "test_runtime",
                "Test Runtime",
                "type.test",
                "test",
            ),
        ),
        types=(
            DataTypeSpec(
                ROOT_TYPE,
                "Root",
                "test_runtime",
                lambda _value: True,
                abstract=True,
                carriers=frozenset({"native", "inline", "handle", "artifact"}),
            ),
            DataTypeSpec(
                INLINE_TYPE,
                "Inline",
                "test_runtime",
                lambda value: isinstance(value, dict) and value.get("kind") == "inline",
                parents=(ROOT_TYPE,),
                carriers=frozenset({"inline"}),
                payload_schema_version=2,
            ),
            DataTypeSpec(
                HANDLE_TYPE,
                "Handle",
                "test_runtime",
                lambda value: (
                    isinstance(value, RuntimeHandleRef) and value.kind == "test.handle"
                ),
                parents=(ROOT_TYPE,),
                carriers=frozenset({"handle"}),
            ),
            DataTypeSpec(
                ARTIFACT_TYPE,
                "Artifact",
                "test_runtime",
                lambda value: isinstance(value, RuntimeArtifactRef),
                parents=(ROOT_TYPE,),
                carriers=frozenset({"artifact"}),
            ),
            DataTypeSpec(
                NATIVE_TYPE,
                "Native",
                "test_runtime",
                lambda value: isinstance(value, str),
                parents=(ROOT_TYPE,),
            ),
            DataTypeSpec(
                SECRET_TYPE,
                "Secret",
                "test_runtime",
                lambda value: isinstance(value, dict),
                parents=(ROOT_TYPE,),
                sensitivity="secret",
            ),
            DataTypeSpec(
                TABULAR_DATA_REF_TYPE_ID,
                "Tabular",
                "test_runtime",
                lambda value: isinstance(value, TabularDataRef),
                parents=(ROOT_TYPE,),
                carriers=frozenset({"handle"}),
            ),
        ),
        owner_id="tests.runtime-carriers",
    )
    return catalog


def _inline() -> TypedInlineValue:
    return TypedInlineValue(
        INLINE_TYPE,
        2,
        {"kind": "inline", "nested": (1, {"items": (2, 3)})},
    )


def _handle() -> RuntimeHandleRef:
    return RuntimeHandleRef(
        data_type_id=HANDLE_TYPE,
        schema_version=1,
        handle_id="handle-1",
        kind="test.handle",
        owner_scope="run:1",
        worker_generation=7,
        metadata={"labels": ("a", "b")},
    )


def _artifact() -> RuntimeArtifactRef:
    return RuntimeArtifactRef.staged(
        "artifact-1",
        data_type_id=ARTIFACT_TYPE,
        schema_version=1,
        format="png",
        size_bytes=ARTIFACT_SIZE_BYTES,
        sha256=ARTIFACT_SHA256,
        provenance=ARTIFACT_PROVENANCE,
        metadata={"dimensions": (10, 20)},
    )


@pytest.mark.parametrize(
    "artifact_format",
    ("png", "file", "mars_results", "x-y", "tar.gz"),
)
def test_artifact_format_round_trips_exact_canonical_token(
    artifact_format: str,
) -> None:
    catalog = _catalog()
    artifact = RuntimeArtifactRef.staged(
        "artifact-format",
        data_type_id=ARTIFACT_TYPE,
        schema_version=1,
        format=artifact_format,
        size_bytes=ARTIFACT_SIZE_BYTES,
        sha256=ARTIFACT_SHA256,
        provenance=ARTIFACT_PROVENANCE,
    )

    payload = serialize_runtime_value(artifact, catalog=catalog)

    assert payload["format"] == artifact_format
    assert deserialize_runtime_value(payload, catalog=catalog) == artifact


@pytest.mark.parametrize(
    "artifact_format",
    (
        "",
        " png",
        "png ",
        "PNG",
        ".png",
        "png.",
        "../PNG",
        r"image\png",
        "image/png",
        "a" * 65,
    ),
)
def test_artifact_format_rejects_noncanonical_direct_and_wire_values(
    artifact_format: str,
) -> None:
    with pytest.raises(ValueError, match="format"):
        RuntimeArtifactRef.staged(
            "artifact-format",
            data_type_id=ARTIFACT_TYPE,
            schema_version=1,
            format=artifact_format,
            size_bytes=ARTIFACT_SIZE_BYTES,
            sha256=ARTIFACT_SHA256,
            provenance=ARTIFACT_PROVENANCE,
        )

    payload = _artifact().to_payload(catalog=_catalog())
    payload["format"] = artifact_format
    with pytest.raises(ValueError, match="format"):
        deserialize_runtime_value(payload, catalog=_catalog())


def test_artifact_format_rejects_non_string_values() -> None:
    with pytest.raises(TypeError, match="format must be a string"):
        RuntimeArtifactRef.staged(
            "artifact-format",
            data_type_id=ARTIFACT_TYPE,
            schema_version=1,
            format=None,  # type: ignore[arg-type]
            size_bytes=ARTIFACT_SIZE_BYTES,
            sha256=ARTIFACT_SHA256,
            provenance=ARTIFACT_PROVENANCE,
        )

    payload = _artifact().to_payload(catalog=_catalog())
    payload["format"] = None
    with pytest.raises(TypeError, match="format must be a string"):
        deserialize_runtime_value(payload, catalog=_catalog())


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "error_type"),
    (
        ("size_bytes", True, TypeError),
        ("size_bytes", -1, ValueError),
        ("sha256", "A" * 64, ValueError),
        ("sha256", "a" * 63, ValueError),
        ("sha256", "z" * 64, ValueError),
        ("provenance", "", ValueError),
        ("provenance", " corex.test", ValueError),
        ("provenance", r"C:\private\artifact", ValueError),
    ),
)
def test_artifact_integrity_fields_reject_malformed_direct_and_wire_values(
    field_name: str,
    invalid_value: object,
    error_type: type[Exception],
) -> None:
    values = {
        "data_type_id": ARTIFACT_TYPE,
        "schema_version": 1,
        "format": "bin",
        "size_bytes": ARTIFACT_SIZE_BYTES,
        "sha256": ARTIFACT_SHA256,
        "provenance": ARTIFACT_PROVENANCE,
    }
    values[field_name] = invalid_value
    with pytest.raises(error_type) as direct_error:
        RuntimeArtifactRef.staged("artifact", **values)  # type: ignore[arg-type]
    if str(invalid_value):
        assert str(invalid_value) not in str(direct_error.value)

    payload = _artifact().to_payload(catalog=_catalog())
    payload[field_name] = invalid_value
    with pytest.raises(error_type) as wire_error:
        deserialize_runtime_value(payload, catalog=_catalog())
    if str(invalid_value):
        assert str(invalid_value) not in str(wire_error.value)


@pytest.mark.parametrize(
    ("missing_field",), (("size_bytes",), ("sha256",), ("provenance",))
)
def test_artifact_integrity_fields_are_required_on_wire(
    missing_field: str,
) -> None:
    payload = _artifact().to_payload(catalog=_catalog())
    payload.pop(missing_field)

    with pytest.raises(ValueError, match=missing_field):
        deserialize_runtime_value(payload, catalog=_catalog())


def test_secret_semantic_type_cannot_use_an_artifact_carrier() -> None:
    artifact = RuntimeArtifactRef.staged(
        "secret-artifact",
        data_type_id=SECRET_TYPE,
        schema_version=1,
        format="bin",
        size_bytes=ARTIFACT_SIZE_BYTES,
        sha256=ARTIFACT_SHA256,
        provenance=ARTIFACT_PROVENANCE,
    )

    with pytest.raises(DataTypeCatalogError, match="does not allow 'artifact'"):
        serialize_runtime_value(artifact, catalog=_catalog())


def test_secret_runtime_handle_metadata_must_be_empty() -> None:
    catalog = DataTypeCatalog()
    catalog.register_many(
        families=(
            DataTypeFamilySpec(
                "secret_handle",
                "Secret Handle",
                "type.secret",
                "secret",
            ),
        ),
        types=(
            DataTypeSpec(
                "Test.Runtime.SecretHandle",
                "Secret Handle",
                "secret_handle",
                lambda value: isinstance(value, RuntimeHandleRef),
                carriers=frozenset({"handle"}),
                sensitivity="secret",
            ),
        ),
        owner_id="tests.secret-handle",
    )
    handle = RuntimeHandleRef(
        data_type_id="Test.Runtime.SecretHandle",
        schema_version=1,
        handle_id="secret-handle",
        kind="test.secret",
        owner_scope="run:1",
        worker_generation=1,
        metadata={"label": "innocuous"},
    )

    with pytest.raises(DataTypeCatalogError, match="metadata must be empty"):
        catalog.validate_carrier("Test.Runtime.SecretHandle", handle)


def test_secret_type_registration_rejects_artifact_carrier_explicitly() -> None:
    catalog = DataTypeCatalog()

    with pytest.raises(
        DataTypeCatalogError,
        match="secret.*must not allow artifact carriers",
    ):
        catalog.register_many(
            families=(
                DataTypeFamilySpec(
                    "secret_runtime",
                    "Secret Runtime",
                    "type.secret",
                    "secret",
                ),
            ),
            types=(
                DataTypeSpec(
                    "Test.Runtime.ArtifactEnabledSecret",
                    "Artifact-enabled Secret",
                    "secret_runtime",
                    lambda value: isinstance(value, RuntimeArtifactRef),
                    carriers=frozenset({"artifact"}),
                    persistence="never",
                    sensitivity="secret",
                ),
            ),
            owner_id="tests.secret-artifact-registration",
        )


def test_artifact_validation_errors_do_not_echo_ref_values() -> None:
    unsafe_value = r"C:\private\never-echo-this"
    with pytest.raises(ValueError) as caught:
        RuntimeArtifactRef.staged(
            unsafe_value,
            data_type_id=ARTIFACT_TYPE,
            schema_version=1,
            format="bin",
            size_bytes=ARTIFACT_SIZE_BYTES,
            sha256=ARTIFACT_SHA256,
            provenance=ARTIFACT_PROVENANCE,
        )

    assert unsafe_value not in str(caught.value)
    assert "never-echo-this" not in str(caught.value)


def test_typed_carriers_round_trip_nested_data_tree_with_canonical_lists() -> None:
    catalog = _catalog()
    value = DataTree.from_item(
        {
            "inline": _inline(),
            "handle": _handle(),
            "artifact": _artifact(),
            "table": TabularDataRef(
                ref_id="table-1",
                resolver_id="tabular.cache",
                metadata={"labels": ("x", "y")},
            ),
        }
    )

    payload = serialize_runtime_value(value, catalog=catalog)
    restored = deserialize_runtime_value(payload, catalog=catalog)

    assert payload["branches"][0]["items"][0]["inline"] == {
        "__ea_runtime_value__": "typed_inline",
        "data_type_id": INLINE_TYPE,
        "schema_version": 2,
        "payload": {
            "kind": "inline",
            "nested": [1, {"items": [2, 3]}],
        },
    }
    assert payload["branches"][0]["items"][0]["handle"] == {
        "__ea_runtime_value__": "handle_ref",
        "data_type_id": HANDLE_TYPE,
        "schema_version": 1,
        "handle_id": "handle-1",
        "kind": "test.handle",
        "owner_scope": "run:1",
        "worker_generation": 7,
        "metadata": {"labels": ["a", "b"]},
    }
    assert payload["branches"][0]["items"][0]["artifact"] == {
        "__ea_runtime_value__": "artifact_ref",
        "data_type_id": ARTIFACT_TYPE,
        "schema_version": 1,
        "ref": "temp://artifact-1",
        "artifact_id": "artifact-1",
        "scope": "staged",
        "format": "png",
        "size_bytes": ARTIFACT_SIZE_BYTES,
        "sha256": ARTIFACT_SHA256,
        "provenance": ARTIFACT_PROVENANCE,
        "metadata": {"dimensions": [10, 20]},
    }
    assert payload["branches"][0]["items"][0]["table"]["data_type_id"] == (
        "COREX.Runtime.TabularDataRef"
    )
    assert payload["branches"][0]["items"][0]["table"]["schema_version"] == 1
    assert restored == value


def _canonical_runtime_wire_payloads() -> tuple[
    tuple[str, dict[str, object], DataTypeCatalog | None],
    ...,
]:
    catalog = _catalog()
    values = (
        (
            "data-tree",
            serialize_runtime_value(DataTree.from_item([1, 2])),
            None,
        ),
        ("interval", serialize_runtime_value(Interval1D(3, 1)), None),
        (
            "typed-inline",
            serialize_runtime_value(_inline(), catalog=catalog),
            catalog,
        ),
        ("artifact", serialize_runtime_value(_artifact(), catalog=catalog), catalog),
        ("handle", serialize_runtime_value(_handle(), catalog=catalog), catalog),
    )
    assert all(isinstance(payload, dict) for _name, payload, _catalog in values)
    return values  # type: ignore[return-value]


@pytest.mark.parametrize(
    "declared_type_id",
    (GRAPH_ARRAY_DATA_TYPE_ID, GRAPH_DICTIONARY_DATA_TYPE_ID),
)
def test_declared_collections_reject_already_encoded_runtime_markers(
    declared_type_id: str,
) -> None:
    catalog = build_builtin_registry().data_types

    for _name, payload, _payload_catalog in _canonical_runtime_wire_payloads():
        with pytest.raises(DataTypeCatalogError, match="invalid for declared"):
            serialize_runtime_value(
                payload,
                catalog=catalog,
                declared_type_id=declared_type_id,
            )


def _data_tree_wire(*items: object) -> dict[str, object]:
    branches: list[dict[str, object]] = []
    if items:
        branches.append({"path": [0], "items": list(items)})
    return {
        "__ea_runtime_value__": "data_tree",
        "branches": branches,
    }


@pytest.mark.parametrize(
    "declared_type_id",
    (GRAPH_ARRAY_DATA_TYPE_ID, GRAPH_DICTIONARY_DATA_TYPE_ID),
)
def test_empty_root_data_tree_wire_is_valid_for_declared_collections(
    declared_type_id: str,
) -> None:
    catalog = build_builtin_registry().data_types
    payload = _data_tree_wire()

    assert (
        deserialize_runtime_value(
            payload,
            catalog=catalog,
            declared_type_id=declared_type_id,
        )
        == DataTree()
    )


@pytest.mark.parametrize(
    ("declared_type_id", "leaf"),
    (
        (GRAPH_ARRAY_DATA_TYPE_ID, [1, {"nested": [None, 2.5]}]),
        (GRAPH_DICTIONARY_DATA_TYPE_ID, {"nested": [None, 2.5]}),
    ),
)
def test_root_data_tree_wire_validates_matching_collection_leaves(
    declared_type_id: str,
    leaf: object,
) -> None:
    catalog = build_builtin_registry().data_types
    payload = _data_tree_wire(leaf)

    assert deserialize_runtime_value(
        payload,
        catalog=catalog,
        declared_type_id=declared_type_id,
    ) == DataTree.from_item(leaf)


@pytest.mark.parametrize(
    ("declared_type_id", "wrong_leaf"),
    (
        (GRAPH_ARRAY_DATA_TYPE_ID, {"wrong": "dictionary"}),
        (GRAPH_DICTIONARY_DATA_TYPE_ID, ["wrong", "array"]),
    ),
)
def test_root_data_tree_wire_rejects_wrong_collection_leaf_shapes(
    declared_type_id: str,
    wrong_leaf: object,
) -> None:
    with pytest.raises(DataTypeCatalogError, match="invalid for declared"):
        deserialize_runtime_value(
            _data_tree_wire(wrong_leaf),
            catalog=build_builtin_registry().data_types,
            declared_type_id=declared_type_id,
        )


def test_already_encoded_runtime_markers_stay_idempotent_without_declared_type() -> (
    None
):
    for _name, payload, catalog in _canonical_runtime_wire_payloads():
        assert serialize_runtime_value(payload, catalog=catalog) == payload


@pytest.mark.parametrize("value", [_inline(), _handle(), _artifact()])
def test_semantic_carriers_require_an_active_catalog(value: object) -> None:
    with pytest.raises(DataTypeCatalogError, match="active data-type catalog"):
        serialize_runtime_value(value)
    with pytest.raises(DataTypeCatalogError, match="active data-type catalog"):
        value.to_payload()  # type: ignore[union-attr]

    payload = value.to_payload(catalog=_catalog())  # type: ignore[union-attr]
    with pytest.raises(DataTypeCatalogError, match="active data-type catalog"):
        deserialize_runtime_value(payload)


def test_catalog_validates_identity_schema_carrier_abstract_relation_and_value() -> (
    None
):
    catalog = _catalog()

    catalog.validate_carrier(ROOT_TYPE, _inline())
    catalog.validate_carrier(ROOT_TYPE, _handle())
    catalog.validate_carrier(ROOT_TYPE, _artifact())
    catalog.validate_carrier(NATIVE_TYPE, "native")
    catalog.validate_carrier(ROOT_TYPE, "native")
    assert (
        deserialize_runtime_value(
            serialize_runtime_value(
                _inline(),
                catalog=catalog,
                declared_type_id=ROOT_TYPE,
            ),
            catalog=catalog,
            declared_type_id=ROOT_TYPE,
        )
        == _inline()
    )

    with pytest.raises(DataTypeCatalogError, match="unknown data-type ID"):
        serialize_runtime_value(
            TypedInlineValue("Test.Runtime.Unknown", 1, {}),
            catalog=catalog,
        )
    with pytest.raises(DataTypeCatalogError, match="unknown data-type ID"):
        serialize_runtime_value(
            {"nested": [TypedInlineValue("Test.Runtime.Unknown", 1, {})]},
            catalog=catalog,
        )
    with pytest.raises(DataTypeCatalogError, match="schema version 1"):
        catalog.validate_carrier(
            INLINE_TYPE,
            TypedInlineValue(INLINE_TYPE, 1, {"kind": "inline"}),
        )
    with pytest.raises(DataTypeCatalogError, match="schema version 1"):
        deserialize_runtime_value(
            {
                "__ea_runtime_value__": "typed_inline",
                "data_type_id": INLINE_TYPE,
                "schema_version": 1,
                "payload": {"kind": "inline"},
            },
            catalog=catalog,
        )
    with pytest.raises(DataTypeCatalogError, match="does not allow 'inline'"):
        catalog.validate_carrier(
            NATIVE_TYPE,
            TypedInlineValue(NATIVE_TYPE, 1, "native"),
        )
    with pytest.raises(DataTypeCatalogError, match="not assignable"):
        catalog.validate_carrier(HANDLE_TYPE, _inline())
    with pytest.raises(DataTypeCatalogError, match="invalid for declared"):
        catalog.validate_carrier(
            INLINE_TYPE,
            TypedInlineValue(INLINE_TYPE, 2, {"kind": "wrong"}),
        )
    with pytest.raises(DataTypeCatalogError, match="must be concrete"):
        catalog.validate_carrier(
            ROOT_TYPE,
            TypedInlineValue(ROOT_TYPE, 1, {}),
        )


def test_required_semantic_fields_and_fixed_ref_schema_fail_closed() -> None:
    with pytest.raises(TypeError, match="data_type_id"):
        RuntimeHandleRef(  # type: ignore[call-arg]
            handle_id="missing",
            kind="test.handle",
            owner_scope="run:1",
            worker_generation=1,
        )
    with pytest.raises(TypeError, match="data_type_id"):
        RuntimeArtifactRef.staged("missing")  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="missing.*data_type_id"):
        deserialize_runtime_value(
            {
                "__ea_runtime_value__": "handle_ref",
                "schema_version": 1,
                "handle_id": "missing",
                "kind": "test.handle",
                "owner_scope": "run:1",
                "worker_generation": 1,
            },
            catalog=_catalog(),
        )
    with pytest.raises(ValueError, match="schema_version must be 1"):
        deserialize_runtime_value(
            {
                "__ea_runtime_value__": "tabular_data_ref",
                "data_type_id": "COREX.Runtime.TabularDataRef",
                "schema_version": 2,
                "ref_id": "table",
                "resolver_id": "resolver",
            }
        )


@pytest.mark.parametrize(
    "unsafe",
    [
        {1: "integer key", "1": "collision"},
        {"bad": float("nan")},
        {"bad": float("inf")},
        {"bad": bytes([1])},
        {"bad": {1, 2}},
        {"bad": frozenset({1, 2})},
    ],
)
def test_inline_payload_rejects_non_json_values(unsafe: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        TypedInlineValue(INLINE_TYPE, 2, unsafe)


def test_inline_payload_rejects_dataclasses_objects_depth_and_size() -> None:
    @dataclass
    class Unsupported:
        value: int

    for value in (Unsupported(1), object()):
        with pytest.raises(TypeError, match="strict JSON values"):
            TypedInlineValue(INLINE_TYPE, 2, value)

    too_deep: object = "leaf"
    for _index in range(33):
        too_deep = [too_deep]
    with pytest.raises(ValueError, match="maximum JSON depth 32"):
        TypedInlineValue(INLINE_TYPE, 2, too_deep)

    with pytest.raises(ValueError, match="1048576 bytes"):
        TypedInlineValue(INLINE_TYPE, 2, "x" * 1024 * 1024)


def test_complete_runtime_depth_includes_outer_containers_and_carrier_payload() -> None:
    nested_payload: object = "leaf"
    for _index in range(20):
        nested_payload = [nested_payload]
    carrier = TypedInlineValue(
        INLINE_TYPE,
        2,
        {"kind": "inline", "nested": nested_payload},
    )
    catalog = _catalog()

    nested_value: object = carrier
    for _index in range(20):
        nested_value = [nested_value]
    with pytest.raises(ValueError, match="maximum JSON depth 32"):
        serialize_runtime_value(nested_value, catalog=catalog)

    nested_wire: object = carrier.to_payload(catalog=catalog)
    for _index in range(20):
        nested_wire = [nested_wire]
    with pytest.raises(ValueError, match="maximum JSON depth 32"):
        deserialize_runtime_value(nested_wire, catalog=catalog)


@pytest.mark.parametrize(
    "metadata",
    [
        {"password": "value"},
        {"api_key": "value"},
        {"ApiKey": "value"},
        {"api-token": "value"},
        {"clientCredential": "value"},
        {"Authorization": "value"},
        {"session_cookie": "value"},
        {"private_key_pem": "value"},
        {"path": "C:\\private\\value.bin"},
        {"path": "/private/value.bin"},
    ],
)
def test_ref_metadata_rejects_secrets_and_absolute_paths(
    metadata: dict[str, str],
) -> None:
    with pytest.raises(ValueError) as exc_info:
        RuntimeHandleRef(
            data_type_id=HANDLE_TYPE,
            schema_version=1,
            handle_id="handle",
            kind="test.handle",
            owner_scope="run:1",
            worker_generation=1,
            metadata=metadata,
        )
    if "path" not in metadata:
        assert not any(
            secret.casefold() in str(exc_info.value).casefold()
            for secret in (*metadata.keys(), *metadata.values())
        )


def test_ref_metadata_rejects_nested_opaque_secret_marker() -> None:
    with pytest.raises(ValueError, match="sensitive runtime data"):
        RuntimeHandleRef(
            data_type_id=HANDLE_TYPE,
            schema_version=1,
            handle_id="handle",
            kind="test.handle",
            owner_scope="run:1",
            worker_generation=1,
            metadata={
                "nested": {
                    "__ea_runtime_value__": "secret_data",
                    "password": "never-echo-this",
                }
            },
        )


def test_ref_metadata_rejects_nested_api_key_without_echoing_it() -> None:
    with pytest.raises(ValueError) as exc_info:
        RuntimeArtifactRef.staged(
            "artifact",
            data_type_id=ARTIFACT_TYPE,
            schema_version=1,
            format="bin",
            size_bytes=ARTIFACT_SIZE_BYTES,
            sha256=ARTIFACT_SHA256,
            provenance=ARTIFACT_PROVENANCE,
            metadata={"nested": {"api-key": "never-echo-this"}},
        )

    message = str(exc_info.value).casefold()
    assert "api-key" not in message
    assert "never-echo-this" not in message


def test_ref_metadata_has_a_bounded_wire_size() -> None:
    assert "metadata" not in repr(_handle())
    assert "metadata" not in repr(_artifact())
    assert "metadata" not in repr(
        TabularDataRef(
            ref_id="repr",
            resolver_id="resolver",
            metadata={"description": "hidden"},
        )
    )
    with pytest.raises(ValueError, match="65536 bytes"):
        RuntimeHandleRef(
            data_type_id=HANDLE_TYPE,
            schema_version=1,
            handle_id="large",
            kind="test.handle",
            owner_scope="run:1",
            worker_generation=1,
            metadata={"description": "x" * 65536},
        )


def test_unknown_markers_and_arbitrary_runtime_objects_fail_before_json() -> None:
    unknown = {"__ea_runtime_value__": "unknown", "payload": {}}
    for operation in (serialize_runtime_value, deserialize_runtime_value):
        with pytest.raises(ValueError, match="Unsupported runtime value marker"):
            operation(unknown)
    for value in (bytes([1]), {1, 2}, object()):
        with pytest.raises(TypeError):
            serialize_runtime_value(value)


def test_top_level_opaque_secret_marker_remains_strict_and_catalog_free() -> None:
    value = {
        "__ea_runtime_value__": "secret_data",
        "password": "opaque",
        "options": ("one", "two"),
    }

    payload = serialize_runtime_value(value)

    assert payload["options"] == ["one", "two"]
    assert deserialize_runtime_value(payload) == payload
    with pytest.raises(TypeError):
        serialize_runtime_value(
            {
                "__ea_runtime_value__": "secret_data",
                "password": bytes([1]),
            }
        )
    too_deep: object = "opaque"
    for _index in range(33):
        too_deep = [too_deep]
    with pytest.raises(ValueError, match="maximum JSON depth 32"):
        serialize_runtime_value(
            {
                "__ea_runtime_value__": "secret_data",
                "password": too_deep,
            }
        )


def test_artifact_decode_requires_exact_nonblank_redundant_identity() -> None:
    catalog = _catalog()
    payload = _artifact().to_payload(catalog=catalog)
    for field_name in ("artifact_id", "scope"):
        malformed = dict(payload)
        malformed[field_name] = ""
        with pytest.raises(ValueError, match=f"{field_name}.*non-empty"):
            deserialize_runtime_value(malformed, catalog=catalog)

    mismatched = dict(payload)
    mismatched["artifact_id"] = "other"
    with pytest.raises(ValueError, match="does not match"):
        deserialize_runtime_value(mismatched, catalog=catalog)


def test_data_tree_and_fixed_ref_markers_reject_unexpected_fields() -> None:
    table = TabularDataRef(ref_id="table", resolver_id="resolver")
    array = ArrayDataRef(ref_id="array", resolver_id="resolver")
    values = (
        {
            "__ea_runtime_value__": "data_tree",
            "branches": [{"path": [0], "items": [1], "extra": True}],
        },
        {**table.to_payload(), "extra": True},
        {**array.to_payload(), "extra": True},
        {
            **TabularWindowRef(ref_id="window", table_data=table).to_payload(),
            "extra": True,
        },
        {
            **ArraySlice2DRef(ref_id="slice", array_data=array).to_payload(),
            "extra": True,
        },
    )

    for payload in values:
        with pytest.raises(ValueError, match="unexpected fields"):
            deserialize_runtime_value(payload)

    with pytest.raises(ValueError, match="unexpected fields"):
        deserialize_runtime_value(
            {
                "__ea_runtime_value__": "data_tree",
                "branches": [],
                "extra": True,
            }
        )


def test_interval_is_the_only_legacy_typed_adapter() -> None:
    interval = Interval1D(3, 1)
    payload = serialize_runtime_value(interval)

    assert payload == {
        "__ea_runtime_value__": "interval_1d",
        "start": 3.0,
        "end": 1.0,
    }
    assert deserialize_runtime_value(payload) == interval

    catalog = NodeRegistry().data_types
    catalog.validate_carrier(
        INTERVAL_1D_GRAPH_DATA_TYPE_ID,
        interval,
    )
    assert (
        deserialize_runtime_value(
            serialize_runtime_value(
                interval,
                catalog=catalog,
                declared_type_id=INTERVAL_1D_GRAPH_DATA_TYPE_ID,
            ),
            catalog=catalog,
            declared_type_id=INTERVAL_1D_GRAPH_DATA_TYPE_ID,
        )
        == interval
    )


def test_core_viewer_session_type_accepts_only_typed_handle_refs() -> None:
    catalog = NodeRegistry().data_types
    session = RuntimeHandleRef(
        data_type_id=VIEWER_SESSION_DATA_TYPE_ID,
        schema_version=1,
        handle_id="viewer",
        kind=COREX_VIEWER_SESSION_HANDLE_KIND,
        owner_scope="run:viewer",
        worker_generation=1,
    )

    catalog.validate_carrier(VIEWER_SESSION_DATA_TYPE_ID, session)
    catalog.validate_output(VIEWER_SESSION_DATA_TYPE_ID, session)
    wrong_type = RuntimeHandleRef(
        data_type_id="COREX.Engineering.Scene",
        schema_version=1,
        handle_id="scene",
        kind=COREX_VIEWER_SESSION_HANDLE_KIND,
        owner_scope="run:viewer",
        worker_generation=1,
    )
    with pytest.raises(DataTypeCatalogError, match="invalid for declared"):
        catalog.validate_output(VIEWER_SESSION_DATA_TYPE_ID, wrong_type)
    wrong_kind = RuntimeHandleRef(
        data_type_id=VIEWER_SESSION_DATA_TYPE_ID,
        schema_version=1,
        handle_id="viewer-wrong-kind",
        kind="viewer.session",
        owner_scope="run:viewer",
        worker_generation=1,
    )
    with pytest.raises(DataTypeCatalogError, match="invalid for declared"):
        catalog.validate_output(VIEWER_SESSION_DATA_TYPE_ID, wrong_kind)
    with pytest.raises(DataTypeCatalogError, match="does not allow 'native'"):
        catalog.validate_carrier(
            VIEWER_SESSION_DATA_TYPE_ID,
            {"session_id": "legacy-mapping"},
        )
