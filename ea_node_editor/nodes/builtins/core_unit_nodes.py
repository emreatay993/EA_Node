# Purpose: Provide COREX core, media, and unit utility nodes.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_core_unit_nodes.py

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType

from ea_node_editor.nodes.builtins.core_media import (
    CELL_DATA_TYPE_ID,
    DATETIME_DATA_TYPE_ID,
    INTERVAL_2D_DATA_TYPE_ID,
    TENSOR_DATA_TYPE_ID,
    is_cell_payload,
    is_datetime_payload,
    is_interval_2d_payload,
    is_tensor_payload,
)
from ea_node_editor.nodes.builtins.tree_path import (
    COREX_PATH_DATA_TYPE_ID,
    make_tree_path_value,
    tree_path_indices,
)
from ea_node_editor.nodes.builtins.units import (
    IQUANTITY_DATA_TYPE_ID,
    LENGTH_DATA_TYPE_ID,
    PLANE_ANGLE_DATA_TYPE_ID,
    TIME_DATA_TYPE_ID,
    UNIT_SYSTEM_DATA_TYPE_ID,
    is_length_payload,
    is_plane_angle_payload,
    is_time_payload,
    is_unit_system_payload,
)
from ea_node_editor.nodes.core_data_types import (
    DOUBLE_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
)
from ea_node_editor.nodes.decorators import node_type, plugin_descriptor
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import PortSpec
from ea_node_editor.nodes.plugin_contracts import (
    PluginContractManifest,
)
from ea_node_editor.runtime_contracts import Interval1D, TypedInlineValue


COREX_CORE_UNIT_NODE_OWNER_ID = "corex.core_unit_nodes"
COREX_CORE_UNIT_NODE_OWNER_VERSION = "1"

CONSTRUCT_PATH_TYPE_ID = "data.construct_path"
DECONSTRUCT_PATH_TYPE_ID = "data.deconstruct_path"
DECONSTRUCT_DATE_TIME_TYPE_ID = "utilities.deconstruct_date_time"
DECONSTRUCT_TENSOR_TYPE_ID = "math.deconstruct_tensor"
EXCEL_CELL_TYPE_ID = "data.excel_cell"
DECONSTRUCT_INTERVAL_2D_TYPE_ID = "math.deconstruct_interval_2d"
PHYSICAL_QUANTITY_CONTAINER_TYPE_ID = "math.physical_quantity_container"
UNIT_SYSTEM_CONTAINER_TYPE_ID = "math.unit_system_container"




_INT32_MAX = 2_147_483_647
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))


def _typed_payload(
    value: object,
    data_type_id: str,
    validator: Callable[[object], bool],
) -> dict[str, object]:
    if (
        type(value) is not TypedInlineValue
        or type(value.data_type_id) is not str
        or value.data_type_id != data_type_id
        or type(value.schema_version) is not int
        or value.schema_version != 1
        or not validator(value.payload)
    ):
        raise ValueError(f"{data_type_id} input is invalid")
    return value.payload


def _normalize_excel_column(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("column must be an ASCII column name or positive Int32")
    if all(("A" <= char <= "Z") or ("a" <= char <= "z") for char in value):
        return value.upper()
    if not all("0" <= char <= "9" for char in value):
        raise ValueError("column must be an ASCII column name or positive Int32")
    digits = value.lstrip("0")
    if (
        not digits
        or len(digits) > 10
        or (len(digits) == 10 and digits > str(_INT32_MAX))
    ):
        raise ValueError("column number must be a positive Int32")
    index = int(digits)
    letters: list[str] = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


@node_type(
    type_id=CONSTRUCT_PATH_TYPE_ID,
    display_name="Construct Path",
    category_path=("Data Structure", "Tree"),
    icon="account_tree",
    description="Construct a path of a data tree branch using a list of indices.",
    keywords=("data", "tree", "path", "construct"),
    ports=(
        PortSpec(
            "indices",
            "in",
            "data",
            INTEGER_DATA_TYPE_ID,
            data_access="list",
            label="Indices",
            required=True,
            description="Path indices.",
        ),
        PortSpec(
            "path",
            "out",
            "data",
            COREX_PATH_DATA_TYPE_ID,
            label="Path",
            description="Path defined by the given indices.",
        ),
    ),
    properties=(),
)
class ConstructPathNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"path": make_tree_path_value(ctx.inputs["indices"])})


@node_type(
    type_id=DECONSTRUCT_PATH_TYPE_ID,
    display_name="Deconstruct Path",
    category_path=("Data Structure", "Tree"),
    icon="account_tree",
    description="Deconstruct a path of a data tree into a list of integers.",
    keywords=("data", "tree", "path", "deconstruct"),
    ports=(
        PortSpec(
            "path",
            "in",
            "data",
            COREX_PATH_DATA_TYPE_ID,
            label="Path",
            required=True,
            description="Path to deconstruct into its indices.",
        ),
        PortSpec(
            "indices",
            "out",
            "data",
            INTEGER_DATA_TYPE_ID,
            data_access="list",
            label="Indices",
            description="Indices of the path.",
        ),
    ),
    properties=(),
)
class DeconstructPathNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"indices": tree_path_indices(ctx.inputs["path"])})


@node_type(
    type_id=DECONSTRUCT_DATE_TIME_TYPE_ID,
    display_name="Deconstruct Date and Time",
    category_path=("Utilities", "Time"),
    icon="schedule",
    description="Extracts the integer components of a typed COREX date and time.",
    keywords=("date", "time", "deconstruct"),
    ports=(
        PortSpec(
            "date_and_time",
            "in",
            "data",
            DATETIME_DATA_TYPE_ID,
            label="Date and time",
            required=True,
            description="The date and time to deconstruct.",
        ),
        *(
            PortSpec(key, "out", "data", INTEGER_DATA_TYPE_ID, label=label)
            for key, label in (
                ("year", "Year"),
                ("month", "Month"),
                ("day", "Day"),
                ("hour", "Hour"),
                ("minute", "Minute"),
                ("second", "Second"),
                ("millisecond", "Millisecond"),
            )
        ),
    ),
    properties=(),
)
class DeconstructDateTimeNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        payload = _typed_payload(
            ctx.inputs["date_and_time"],
            DATETIME_DATA_TYPE_ID,
            is_datetime_payload,
        )
        return NodeResult(
            outputs={
                key: payload[key]
                for key in (
                    "year",
                    "month",
                    "day",
                    "hour",
                    "minute",
                    "second",
                    "millisecond",
                )
            }
        )


@node_type(
    type_id=DECONSTRUCT_TENSOR_TYPE_ID,
    display_name="Deconstruct Tensor",
    category_path=("Math", "Tensor"),
    icon="view_in_ar",
    description="Deconstruct a Tensor to retrieve data and shape.",
    keywords=("tensor", "deconstruct", "dimensions"),
    ports=(
        PortSpec(
            "tensor",
            "in",
            "data",
            TENSOR_DATA_TYPE_ID,
            label="Tensor",
            required=True,
            description="A Tensor representation of data.",
        ),
        PortSpec(
            "data",
            "out",
            "data",
            DOUBLE_DATA_TYPE_ID,
            data_access="list",
            label="Values",
            description="The values in the tensor.",
        ),
        PortSpec(
            "dimensions",
            "out",
            "data",
            INTEGER_DATA_TYPE_ID,
            data_access="list",
            label="Shape",
            description="The shape of the tensor.",
        ),
    ),
    properties=(),
)
class DeconstructTensorNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        payload = _typed_payload(
            ctx.inputs["tensor"],
            TENSOR_DATA_TYPE_ID,
            is_tensor_payload,
        )
        return NodeResult(
            outputs={
                "data": list(payload["data"]),
                "dimensions": list(payload["dimensions"]),
            }
        )


@node_type(
    type_id=EXCEL_CELL_TYPE_ID,
    display_name="Excel Cell",
    category_path=("Data", "Excel"),
    icon="grid_on",
    description="Define an Excel cell by its column and row.",
    keywords=("excel", "cell", "column", "row"),
    ports=(
        PortSpec(
            "column",
            "in",
            "data",
            STRING_DATA_TYPE_ID,
            label="Column",
            required=True,
            description="Column of the Excel cell starting at A or 1.",
        ),
        PortSpec(
            "row",
            "in",
            "data",
            INTEGER_DATA_TYPE_ID,
            label="Row",
            required=True,
            description="Row of the Excel cell starting at 1.",
        ),
        PortSpec(
            "cell",
            "out",
            "data",
            CELL_DATA_TYPE_ID,
            label="Cell",
            description="Excel cell defined by column and row.",
        ),
    ),
    properties=(),
)
class ExcelCellNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        row = ctx.inputs["row"]
        if type(row) is not int or not 1 <= row <= _INT32_MAX:
            raise ValueError("row must be a positive Int32")
        payload = {
            "Column": _normalize_excel_column(ctx.inputs["column"]),
            "Row": row,
        }
        if not is_cell_payload(payload):
            raise ValueError("cell payload is invalid")
        return NodeResult(
            outputs={"cell": TypedInlineValue(CELL_DATA_TYPE_ID, 1, payload)}
        )


@node_type(
    type_id=DECONSTRUCT_INTERVAL_2D_TYPE_ID,
    display_name="Deconstruct Interval 2D",
    category_path=("Math", "Interval"),
    icon="aspect_ratio",
    description="Deconstruct a 2D numeric interval into its u- and v-intervals.",
    keywords=("interval", "2d", "deconstruct"),
    ports=(
        PortSpec(
            "interval",
            "in",
            "data",
            INTERVAL_2D_DATA_TYPE_ID,
            label="Interval 2D",
            required=True,
            description="Interval to deconstruct into its u- and v-interval.",
        ),
        PortSpec(
            "u",
            "out",
            "data",
            INTERVAL_1D_GRAPH_DATA_TYPE_ID,
            label="U-interval",
            description="Interval in the u-direction of the 2D-interval.",
        ),
        PortSpec(
            "v",
            "out",
            "data",
            INTERVAL_1D_GRAPH_DATA_TYPE_ID,
            label="V-interval",
            description="Interval in the v-direction of the 2D-interval.",
        ),
    ),
    properties=(),
)
class DeconstructInterval2DNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        payload = _typed_payload(
            ctx.inputs["interval"],
            INTERVAL_2D_DATA_TYPE_ID,
            is_interval_2d_payload,
        )
        return NodeResult(
            outputs={
                axis: Interval1D(
                    payload[axis]["start"],
                    payload[axis]["end"],
                )
                for axis in ("u", "v")
            }
        )


_QUANTITY_VALIDATORS = (
    (LENGTH_DATA_TYPE_ID, is_length_payload),
    (PLANE_ANGLE_DATA_TYPE_ID, is_plane_angle_payload),
    (TIME_DATA_TYPE_ID, is_time_payload),
)


def _validated_quantity(value: object) -> object:
    if value is None:
        return None
    if type(value) is not TypedInlineValue or type(value.data_type_id) is not str:
        raise ValueError("physical quantity input is invalid")
    for data_type_id, validator in _QUANTITY_VALIDATORS:
        if value.data_type_id == data_type_id:
            _typed_payload(value, data_type_id, validator)
            return value
    raise ValueError("physical quantity input is invalid")


@node_type(
    type_id=PHYSICAL_QUANTITY_CONTAINER_TYPE_ID,
    display_name="Physical Quantity",
    category_path=("Math", "Container"),
    icon="straighten",
    description="Passes through an optional typed physical quantity.",
    keywords=("physical", "quantity", "container", "units"),
    ports=(
        PortSpec(
            "input",
            "in",
            "data",
            IQUANTITY_DATA_TYPE_ID,
            label="Input",
            required=False,
        ),
        PortSpec(
            "output",
            "out",
            "data",
            IQUANTITY_DATA_TYPE_ID,
            label="Output",
        ),
    ),
    properties=(),
)
class PhysicalQuantityContainerNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        if "input" not in ctx.inputs:
            return NodeResult()
        return NodeResult(outputs={"output": _validated_quantity(ctx.inputs["input"])})


@node_type(
    type_id=UNIT_SYSTEM_CONTAINER_TYPE_ID,
    display_name="Unit System",
    category_path=("Math", "Container"),
    icon="square_foot",
    description="Passes through an optional typed Unit System.",
    keywords=("unit", "system", "container"),
    ports=(
        PortSpec(
            "input",
            "in",
            "data",
            UNIT_SYSTEM_DATA_TYPE_ID,
            label="Input",
            required=False,
        ),
        PortSpec(
            "output",
            "out",
            "data",
            UNIT_SYSTEM_DATA_TYPE_ID,
            label="Output",
        ),
    ),
    properties=(),
)
class UnitSystemContainerNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        if "input" not in ctx.inputs:
            return NodeResult()
        value = ctx.inputs["input"]
        if value is not None:
            _typed_payload(value, UNIT_SYSTEM_DATA_TYPE_ID, is_unit_system_payload)
        return NodeResult(outputs={"output": value})


COREX_CORE_UNIT_NODE_DESCRIPTORS = tuple(
    plugin_descriptor(node)
    for node in (
        ConstructPathNodePlugin,
        DeconstructPathNodePlugin,
        DeconstructDateTimeNodePlugin,
        DeconstructTensorNodePlugin,
        ExcelCellNodePlugin,
        DeconstructInterval2DNodePlugin,
        PhysicalQuantityContainerNodePlugin,
        UnitSystemContainerNodePlugin,
    )
)


























COREX_CORE_UNIT_NODE_CONTRACT_MANIFEST = PluginContractManifest(
)


__all__ = [
    "CONSTRUCT_PATH_TYPE_ID",
    "DECONSTRUCT_DATE_TIME_TYPE_ID",
    "DECONSTRUCT_INTERVAL_2D_TYPE_ID",
    "DECONSTRUCT_PATH_TYPE_ID",
    "DECONSTRUCT_TENSOR_TYPE_ID",
    "EXCEL_CELL_TYPE_ID",
    "ConstructPathNodePlugin",
    "DeconstructDateTimeNodePlugin",
    "DeconstructInterval2DNodePlugin",
    "DeconstructPathNodePlugin",
    "DeconstructTensorNodePlugin",
    "ExcelCellNodePlugin",
    "PHYSICAL_QUANTITY_CONTAINER_TYPE_ID",
    "PhysicalQuantityContainerNodePlugin",
    "COREX_CORE_UNIT_NODE_CONTRACT_MANIFEST",
    "COREX_CORE_UNIT_NODE_DESCRIPTORS",
    "COREX_CORE_UNIT_NODE_OWNER_ID",
    "COREX_CORE_UNIT_NODE_OWNER_VERSION",
    "UNIT_SYSTEM_CONTAINER_TYPE_ID",
    "UnitSystemContainerNodePlugin",
]
