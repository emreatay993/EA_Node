from __future__ import annotations

import copy
import base64
import json
from pathlib import Path

import pytest

from ea_node_editor.execution.run_messages import (
    NodeSettledEvent,
)
from ea_node_editor.execution.protocol_codec import (
    dict_to_event,
    event_to_dict,
)
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.builtins.core_values import (
    COLOR_DATA_TYPE_ID,
    COMPLEX_DATA_TYPE_ID,
    IMAGE_DATA_TYPE_ID,
    COREX_CORE_VALUE_CONTRACT_MANIFEST,
    COREX_CORE_VALUE_OWNER_ID,
    COREX_CORE_VALUE_OWNER_VERSION,
    is_color_payload,
    is_complex_payload,
    is_image_value,
)
from ea_node_editor.nodes.core_data_types import GRAPH_DATA_TYPE_ID
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import (
    DataTree,
    ImageValue,
    RuntimeArtifactRef,
    TypedInlineValue,
    deserialize_runtime_value,
    serialize_runtime_value,
)

_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg=="
)














def _registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register_plugin_bundle(
        COREX_CORE_VALUE_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_CORE_VALUE_OWNER_ID,
        owner_version=COREX_CORE_VALUE_OWNER_VERSION,
    )
    return registry
















def test_semantic_payloads_are_exact_finite_and_color_has_no_invented_range() -> None:
    assert is_complex_payload({"real": -2.0, "imag": 4.5})
    assert is_color_payload(
        {
            "R": -0.25,
            "G": 1.5,
            "B": 0.0,
            "A": 2.0,
            "IsValid": False,
        }
    )
    assert not is_complex_payload({"real": 1, "imag": 2.0})
    assert not is_complex_payload({"real": float("inf"), "imag": 2.0})
    assert not is_complex_payload({"real": 1.0, "imag": 2.0, "extra": 0.0})
    assert not is_color_payload({"R": 0.0, "G": 0.0, "B": 0.0, "A": 1, "IsValid": True})
    assert not is_color_payload(
        {"R": 0.0, "G": 0.0, "B": float("nan"), "A": 1.0, "IsValid": True}
    )
    assert not is_color_payload({"R": 0.0, "G": 0.0, "B": 0.0, "A": 1.0, "IsValid": 1})


def test_complex_and_color_round_trip_through_runtime_and_stdio_event_json() -> None:
    registry = _registry()
    tree = DataTree(
        (
            (
                (0,),
                (
                    TypedInlineValue(
                        COMPLEX_DATA_TYPE_ID,
                        1,
                        {"real": 1.5, "imag": -2.5},
                    ),
                    TypedInlineValue(
                        COLOR_DATA_TYPE_ID,
                        1,
                        {
                            "R": 0.1,
                            "G": 0.2,
                            "B": 0.3,
                            "A": 0.4,
                            "IsValid": True,
                        },
                    ),
                ),
            ),
        )
    )
    wire = serialize_runtime_value(tree, catalog=registry.data_types)
    assert (
        deserialize_runtime_value(
            json.loads(json.dumps(wire)),
            catalog=registry.data_types,
        )
        == tree
    )

    event = NodeSettledEvent(
        outputs={"value": SettledPortResult(status="value", value=tree)}
    )
    restored = dict_to_event(
        json.loads(json.dumps(event_to_dict(event, catalog=registry.data_types))),
        catalog=registry.data_types,
    )
    assert restored.outputs["value"].value == tree


def test_image_value_round_trips_and_invalid_carriers_are_rejected() -> None:
    registry = _registry()
    image = ImageValue.from_png(_PNG_BYTES)
    registry.data_types.validate_carrier(IMAGE_DATA_TYPE_ID, image)
    wire = serialize_runtime_value(image, catalog=registry.data_types)
    assert (
        deserialize_runtime_value(
            json.loads(json.dumps(wire)),
            catalog=registry.data_types,
        )
        == image
    )
    assert is_image_value(image)

    invalid = (
        RuntimeArtifactRef.staged(
            "wrong_format",
            data_type_id=IMAGE_DATA_TYPE_ID,
            schema_version=1,
            format="bin",
            size_bytes=0,
            sha256="0" * 64,
            provenance="corex.test.fixture",
        ),
        RuntimeArtifactRef.staged(
            "wrong_schema",
            data_type_id=IMAGE_DATA_TYPE_ID,
            schema_version=2,
            format="png",
            size_bytes=0,
            sha256="0" * 64,
            provenance="corex.test.fixture",
        ),
        RuntimeArtifactRef.staged(
            "wrong_type",
            data_type_id=GRAPH_DATA_TYPE_ID,
            schema_version=1,
            format="png",
            size_bytes=0,
            sha256="0" * 64,
            provenance="corex.test.fixture",
        ),
        "image.png",
        b"\x89PNG\r\n\x1a\n",
        {"format": "png"},
        object(),
    )
    for value in invalid:
        with pytest.raises((TypeError, ValueError)):
            registry.data_types.validate_carrier(IMAGE_DATA_TYPE_ID, value)


def _persistence_registry() -> tuple[NodeRegistry, NodeTypeSpec]:
    registry = _registry()
    node_spec = NodeTypeSpec(
        "tests.core_values",
        "COREX Core Values",
        ("Tests",),
        "",
        (PortSpec("result", "out", "data", GRAPH_DATA_TYPE_ID),),
        (
            PropertySpec(
                "complex",
                "json",
                {"real": 0.0, "imag": 0.0},
                "Complex",
                persistence_data_type_id=COMPLEX_DATA_TYPE_ID,
            ),
            PropertySpec(
                "color",
                "json",
                {
                    "R": 0.0,
                    "G": 0.0,
                    "B": 0.0,
                    "A": 1.0,
                    "IsValid": True,
                },
                "Color",
                persistence_data_type_id=COLOR_DATA_TYPE_ID,
            ),
            PropertySpec(
                "image",
                "json",
                ImageValue.from_png(_PNG_BYTES),
                "Image",
                persistence_data_type_id=IMAGE_DATA_TYPE_ID,
            ),
        ),
    )
    registry.register_descriptor(
        node_spec,
        lambda: object(),
        owner_id="tests.core_values",
    )
    return registry, node_spec


def _project_with_values(
    spec: NodeTypeSpec,
    *,
    image: object | None = None,
) -> GraphModel:
    if image is None:
        image = next(prop.default for prop in spec.properties if prop.key == "image")
    model = GraphModel()
    model.add_node(
        model.active_workspace.workspace_id,
        spec.type_id,
        spec.display_name,
        0.0,
        0.0,
        properties={
            "complex": TypedInlineValue(
                COMPLEX_DATA_TYPE_ID,
                1,
                {"real": 1.0, "imag": -1.0},
            ),
            "color": TypedInlineValue(
                COLOR_DATA_TYPE_ID,
                1,
                {
                    "R": 0.0,
                    "G": 0.51,
                    "B": 0.515,
                    "A": 1.0,
                    "IsValid": True,
                },
            ),
            "image": image,
        },
    )
    return model


def test_complex_and_color_are_allowed_inline_project_properties() -> None:
    registry, spec = _persistence_registry()
    serializer = JsonProjectSerializer(registry)
    model = _project_with_values(spec)
    document = serializer.to_persistent_document(model.project)
    loaded = serializer.from_document(copy.deepcopy(document))
    properties = next(
        iter(next(iter(loaded.workspaces.values())).nodes.values())
    ).properties
    assert (
        properties["complex"]
        == next(iter(model.active_workspace.nodes.values())).properties["complex"]
    )
    assert (
        properties["color"]
        == next(iter(model.active_workspace.nodes.values())).properties["color"]
    )


def test_image_value_externalizes_and_hydrates_during_project_save_load(
    tmp_path: Path,
) -> None:
    registry, spec = _persistence_registry()
    serializer = JsonProjectSerializer(registry)
    image = ImageValue.from_png(_PNG_BYTES)
    model = _project_with_values(spec, image=image)
    project_path = tmp_path / "image_value.cxproj"
    serializer.save(str(project_path), model.project)
    document = json.loads(project_path.read_text(encoding="utf-8"))
    persisted = document["workspaces"][0]["nodes"][0]["properties"]["image"]
    assert persisted["__ea_project_image__"] == "image_blob"
    assert persisted["sha256"] == image.sha256
    loaded = serializer.load(str(project_path))
    assert (
        next(iter(next(iter(loaded.workspaces.values())).nodes.values())).properties[
            "image"
        ]
        == image
    )
