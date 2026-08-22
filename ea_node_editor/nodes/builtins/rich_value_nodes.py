# Purpose: Declare COREX rich-value types and offline value nodes.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_rich_values.py

from __future__ import annotations

import math
import re
from types import MappingProxyType

from ea_node_editor.nodes.core_data_types import GRAPH_DATA_TYPE_ID
from ea_node_editor.nodes.decorators import node_type, plugin_descriptor
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import PortSpec, PropertySpec
from ea_node_editor.nodes.plugin_contracts import (
    PluginContractManifest,
)
from ea_node_editor.runtime_contracts import DataTypeSpec, TypedInlineValue

COREX_RICH_VALUE_OWNER_ID = "corex.rich_value_nodes"
COREX_RICH_VALUE_OWNER_VERSION = "1"

PLANE_DATA_TYPE_ID = "COREX.DataTypes.Plane"
COLOR_MAP_DATA_TYPE_ID = "COREX.DataTypes.ColorMap"
NODE_VISUAL_DATA_TYPE_ID = "COREX.DataTypes.NodeVisual"
AGENT_MODEL_DATA_TYPE_ID = "COREX.DataTypes.MultiAgentSystem.AgentModel"

PLANE_CONTAINER_NODE_TYPE_ID = "reference.plane_container"
LARGE_LANGUAGE_MODEL_NODE_TYPE_ID = "ai.large_language_model"

PLANE_FRAME_TOLERANCE = 1.0e-9


_COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{8}")
_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+\-]*")
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))


def _finite_number(value: object) -> float:
    if type(value) not in {int, float}:
        raise TypeError("coordinate must be a built-in number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError("coordinate must be finite") from exc
    if not math.isfinite(number):
        raise ValueError("coordinate must be finite")
    return number


def _vector3(value: object) -> tuple[float, float, float]:
    if type(value) is not list or len(value) != 3:
        raise TypeError("vector must be an exact three-item list")
    return tuple(_finite_number(item) for item in value)  # type: ignore[return-value]


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _cross(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _close(actual: float, expected: float) -> bool:
    return math.isclose(
        actual,
        expected,
        rel_tol=0.0,
        abs_tol=PLANE_FRAME_TOLERANCE,
    )


def _require_plane_payload(value: object) -> None:
    if type(value) is not dict or set(value) != {"origin", "axes", "normal"}:
        raise TypeError("Plane payload must contain only origin, axes, and normal")
    origin = _vector3(value["origin"])
    axes_value = value["axes"]
    if type(axes_value) is not list or len(axes_value) != 2:
        raise TypeError("Plane axes must be an exact two-item list")
    x_axis = _vector3(axes_value[0])
    y_axis = _vector3(axes_value[1])
    normal = _vector3(value["normal"])
    del origin

    if any(
        not _close(_dot(vector, vector), 1.0) for vector in (x_axis, y_axis, normal)
    ):
        raise ValueError("Plane frame vectors must be unit length")
    if any(
        not _close(dot, 0.0)
        for dot in (
            _dot(x_axis, y_axis),
            _dot(x_axis, normal),
            _dot(y_axis, normal),
        )
    ):
        raise ValueError("Plane frame vectors must be orthogonal")
    if any(
        not _close(actual, expected)
        for actual, expected in zip(
            _cross(x_axis, y_axis),
            normal,
            strict=True,
        )
    ):
        raise ValueError("Plane frame must be right-handed")


def is_plane_payload(value: object) -> bool:
    try:
        _require_plane_payload(value)
    except (TypeError, ValueError):
        return False
    return True


def is_color_map_payload(value: object) -> bool:
    return (
        type(value) is list
        and 1 <= len(value) <= 256
        and all(
            type(item) is str and _COLOR_PATTERN.fullmatch(item) is not None
            for item in value
        )
    )


def _is_opaque_ref(value: object) -> bool:
    return (
        type(value) is str
        and 0 < len(value) <= 128
        and value.strip() == value
        and value.isprintable()
    )


def is_node_visual_payload(value: object) -> bool:
    return (
        type(value) is dict
        and set(value) == {"node_refs"}
        and type(value["node_refs"]) is list
        and len(value["node_refs"]) <= 256
        and all(_is_opaque_ref(item) for item in value["node_refs"])
    )


def _is_identifier(value: object, *, maximum: int) -> bool:
    return (
        type(value) is str
        and 0 < len(value) <= maximum
        and value.strip() == value
        and value.isprintable()
        and _IDENTIFIER_PATTERN.fullmatch(value) is not None
    )


def is_agent_model_payload(value: object) -> bool:
    return (
        type(value) is dict
        and set(value) == {"provider_id", "model_id"}
        and _is_identifier(value["provider_id"], maximum=128)
        and _is_identifier(value["model_id"], maximum=256)
    )


COREX_RICH_VALUE_DATA_TYPES = (
    DataTypeSpec(
        PLANE_DATA_TYPE_ID,
        "Plane",
        "engineering",
        is_plane_payload,
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"inline"}),
        persistence="inline",
    ),
    DataTypeSpec(
        COLOR_MAP_DATA_TYPE_ID,
        "COREX Color Map",
        "viewer",
        is_color_map_payload,
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"inline"}),
        persistence="inline",
    ),
    DataTypeSpec(
        NODE_VISUAL_DATA_TYPE_ID,
        "Node Visual",
        "viewer",
        is_node_visual_payload,
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"inline"}),
    ),
    DataTypeSpec(
        AGENT_MODEL_DATA_TYPE_ID,
        "Agent Model",
        "graph",
        is_agent_model_payload,
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"inline"}),
        persistence="inline",
    ),
)


IDENTITY_PLANE = TypedInlineValue(
    PLANE_DATA_TYPE_ID,
    1,
    {
        "origin": [0.0, 0.0, 0.0],
        "axes": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        "normal": [0.0, 0.0, 1.0],
    },
)


def _plane_input(ctx: ExecutionContext) -> object:
    value = ctx.inputs.get("input")
    if value is None:
        value = ctx.properties.get("input")
    if not isinstance(value, TypedInlineValue):
        raise ValueError("Plane input must be a typed Plane value")
    if (
        value.data_type_id != PLANE_DATA_TYPE_ID
        or value.schema_version != 1
        or not is_plane_payload(value.payload)
    ):
        raise ValueError("Plane input is invalid")
    return value


@node_type(
    type_id=PLANE_CONTAINER_NODE_TYPE_ID,
    display_name="Plane",
    category_path=("Reference", "Container"),
    icon="3d_rotation",
    description="Stores or passes through one typed Plane value.",
    keywords=("Plane", "Reference", "Container", "Coordinate System"),
    ports=(
        PortSpec(
            "input",
            "in",
            "data",
            PLANE_DATA_TYPE_ID,
            label="Plane",
            required=False,
            description="Optional Plane value to store or pass through.",
        ),
        PortSpec(
            "output",
            "out",
            "data",
            PLANE_DATA_TYPE_ID,
            label="Plane",
            description="The stored or incoming Plane value.",
        ),
    ),
    properties=(
        PropertySpec(
            "input",
            "json",
            IDENTITY_PLANE,
            "Plane",
            description="Typed inline Plane stored by this container.",
            persistence_data_type_id=PLANE_DATA_TYPE_ID,
        ),
    ),
)
class PlaneContainerNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"output": _plane_input(ctx)})


@node_type(
    type_id=LARGE_LANGUAGE_MODEL_NODE_TYPE_ID,
    display_name="Large Language Model",
    category_path=("AI", "Agent"),
    icon="smart_toy",
    description="Builds offline provider and model configuration for an agent.",
    keywords=("AI", "Agent", "LLM", "Model", "Provider", "Configuration"),
    ports=(
        PortSpec(
            "model",
            "out",
            "data",
            AGENT_MODEL_DATA_TYPE_ID,
            label="Agent Model",
            description="Validated provider and model configuration.",
        ),
    ),
    properties=(
        PropertySpec(
            "provider_id",
            "str",
            "corex-server",
            "Provider ID",
            description="Offline provider identifier; no credentials or client are stored.",
        ),
        PropertySpec(
            "model_id",
            "str",
            "",
            "Model ID",
            description="Model identifier emitted as configuration only.",
        ),
    ),
)
class LargeLanguageModelNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        payload = {
            "provider_id": ctx.properties.get("provider_id"),
            "model_id": ctx.properties.get("model_id"),
        }
        if not is_agent_model_payload(payload):
            raise ValueError(
                "provider_id and model_id must be valid non-empty identifiers"
            )
        return NodeResult(
            outputs={
                "model": TypedInlineValue(
                    AGENT_MODEL_DATA_TYPE_ID,
                    1,
                    payload,
                )
            }
        )


COREX_RICH_VALUE_NODE_DESCRIPTORS = (
    plugin_descriptor(PlaneContainerNodePlugin),
    plugin_descriptor(LargeLanguageModelNodePlugin),
)














def _exact_proof_value(value: object, expected: object) -> bool:
    if type(value) is not type(expected):
        return False
    if type(expected) is tuple:
        return len(value) == len(expected) and all(
            _exact_proof_value(observed, wanted)
            for observed, wanted in zip(value, expected, strict=True)
        )
    return value == expected







COREX_RICH_VALUE_CONTRACT_MANIFEST = PluginContractManifest(
    data_types=COREX_RICH_VALUE_DATA_TYPES,
)

COREX_RICH_VALUE_LLM_CANDIDATE_CONTRACT_MANIFEST = PluginContractManifest(
    data_types=COREX_RICH_VALUE_DATA_TYPES,
)

__all__ = [
    "AGENT_MODEL_DATA_TYPE_ID",
    "COLOR_MAP_DATA_TYPE_ID",
    "IDENTITY_PLANE",
    "LARGE_LANGUAGE_MODEL_NODE_TYPE_ID",
    "NODE_VISUAL_DATA_TYPE_ID",
    "PLANE_CONTAINER_NODE_TYPE_ID",
    "PLANE_DATA_TYPE_ID",
    "PLANE_FRAME_TOLERANCE",
    "COREX_RICH_VALUE_CONTRACT_MANIFEST",
    "COREX_RICH_VALUE_DATA_TYPES",
    "COREX_RICH_VALUE_LLM_CANDIDATE_CONTRACT_MANIFEST",
    "COREX_RICH_VALUE_NODE_DESCRIPTORS",
    "COREX_RICH_VALUE_OWNER_ID",
    "COREX_RICH_VALUE_OWNER_VERSION",
    "LargeLanguageModelNodePlugin",
    "PlaneContainerNodePlugin",
    "is_agent_model_payload",
    "is_color_map_payload",
    "is_node_visual_payload",
    "is_plane_payload",
]
