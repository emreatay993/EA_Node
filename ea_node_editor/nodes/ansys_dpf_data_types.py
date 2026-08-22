# Purpose: Declare canonical Ansys DPF semantic data types and their add-on contribution.
# Map: feature_routes/ansys_dpf_operator_viewer_transport.md
# Tests: tests/test_dpf_generated_operator_catalog.py

from __future__ import annotations

from ea_node_editor.nodes.core_data_types import (
    GRAPH_DATA_TYPE_ID,
    VIEWER_SESSION_DATA_TYPE_ID,
)
from ea_node_editor.nodes.dpf_runtime_contracts import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_OBJECT_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
)
from ea_node_editor.runtime_contracts import (
    DataTypeFamilySpec,
    DataTypeSpec,
    RuntimeHandleRef,
)

DPF_RESULT_FILE_DATA_TYPE = "COREX.Ansys.DPF.ResultFile"
DPF_MODEL_DATA_TYPE = "COREX.Ansys.DPF.Model"
DPF_MESH_DATA_TYPE = "COREX.Ansys.DPF.Mesh"
DPF_FIELD_DATA_TYPE = "COREX.Ansys.DPF.Field"
DPF_SCOPING_DATA_TYPE = "COREX.Ansys.DPF.Scoping"
DPF_FIELDS_CONTAINER_DATA_TYPE = "COREX.Ansys.DPF.FieldsContainer"
DPF_DATA_SOURCES_DATA_TYPE = "COREX.Ansys.DPF.DataSources"
DPF_STREAMS_CONTAINER_DATA_TYPE = "COREX.Ansys.DPF.StreamsContainer"
DPF_WORKFLOW_DATA_TYPE = "COREX.Ansys.DPF.Workflow"
DPF_OBJECT_HANDLE_DATA_TYPE = "COREX.Ansys.DPF.ObjectHandle"
DPF_VIEWER_DATASET_DATA_TYPE = "COREX.Viewer.Dataset"
COREX_MESH_INTERFACE_DATA_TYPE = "COREX.Mesh.IMesh"
COREX_MODEL_INTERFACE_DATA_TYPE = "COREX.Fem.Model.IModel"

DPF_DATA_TYPE_OWNER_ID = "corex.addon.ansys_dpf"


DPF_PUBLIC_DATA_TYPES = (
    DPF_MODEL_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_FIELD_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    VIEWER_SESSION_DATA_TYPE_ID,
)
DPF_SPECIALIZED_DATA_TYPES = (
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_FIELD_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_STREAMS_CONTAINER_DATA_TYPE,
    DPF_WORKFLOW_DATA_TYPE,
    DPF_VIEWER_DATASET_DATA_TYPE,
)

_SOURCE_TYPE_IDS = {
    "result_file": DPF_RESULT_FILE_DATA_TYPE,
    "resultfile": DPF_RESULT_FILE_DATA_TYPE,
    "model": DPF_MODEL_DATA_TYPE,
    "mesh": DPF_MESH_DATA_TYPE,
    "meshed_region": DPF_MESH_DATA_TYPE,
    "meshedregion": DPF_MESH_DATA_TYPE,
    "field": DPF_FIELD_DATA_TYPE,
    "scoping": DPF_SCOPING_DATA_TYPE,
    "fields_container": DPF_FIELDS_CONTAINER_DATA_TYPE,
    "fieldscontainer": DPF_FIELDS_CONTAINER_DATA_TYPE,
    "data_sources": DPF_DATA_SOURCES_DATA_TYPE,
    "datasources": DPF_DATA_SOURCES_DATA_TYPE,
    "streams_container": DPF_STREAMS_CONTAINER_DATA_TYPE,
    "streamscontainer": DPF_STREAMS_CONTAINER_DATA_TYPE,
    "workflow": DPF_WORKFLOW_DATA_TYPE,
    "object_handle": DPF_OBJECT_HANDLE_DATA_TYPE,
    "objecthandle": DPF_OBJECT_HANDLE_DATA_TYPE,
    "viewer_dataset": DPF_VIEWER_DATASET_DATA_TYPE,
    "viewerdataset": DPF_VIEWER_DATASET_DATA_TYPE,
}
_CANONICAL_DPF_TYPE_IDS = frozenset(
    (*DPF_SPECIALIZED_DATA_TYPES, DPF_OBJECT_HANDLE_DATA_TYPE)
)


def _normalize_source_type_name(value: str) -> str:
    characters: list[str] = []
    previous_was_separator = False
    for char in value:
        if char.isupper() and characters and characters[-1] != "_":
            characters.append("_")
        if char.isalnum():
            characters.append(char.lower())
            previous_was_separator = False
            continue
        if not previous_was_separator:
            characters.append("_")
            previous_was_separator = True
    normalized = "".join(characters).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def normalize_dpf_type_id(value: object) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("dpf type_id must be a non-empty trimmed string")
    if normalized in _CANONICAL_DPF_TYPE_IDS:
        return normalized
    source_names = (
        _normalize_source_type_name(normalized),
        _normalize_source_type_name(normalized.rsplit(".", 1)[-1]),
    )
    for source_name in source_names:
        canonical = _SOURCE_TYPE_IDS.get(source_name)
        if canonical is not None:
            return canonical
    return DPF_OBJECT_HANDLE_DATA_TYPE


def _has_handle_identity(data_type_id: str, *kinds: str):
    expected = frozenset(kinds)

    def validate(value: object) -> bool:
        return (
            isinstance(value, RuntimeHandleRef)
            and value.data_type_id == data_type_id
            and value.kind in expected
        )

    return validate


def _is_abstract_handle_interface(_value: object) -> bool:
    return False


DPF_DATA_TYPE_FAMILIES = (
    DataTypeFamilySpec("dpf", "Ansys DPF", "data.dpf", "dpf/ansys.svg"),
    DataTypeFamilySpec("mesh", "Mesh", "data.mesh", "mesh"),
    DataTypeFamilySpec("fem", "FEM", "data.fem", "model"),
)

DPF_DATA_TYPES = (
    DataTypeSpec(
        COREX_MESH_INTERFACE_DATA_TYPE,
        "Mesh",
        "mesh",
        _is_abstract_handle_interface,
        parents=(GRAPH_DATA_TYPE_ID,),
        abstract=True,
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        COREX_MODEL_INTERFACE_DATA_TYPE,
        "FEM Model",
        "fem",
        _is_abstract_handle_interface,
        parents=(GRAPH_DATA_TYPE_ID,),
        abstract=True,
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_RESULT_FILE_DATA_TYPE,
        "DPF Result File",
        "dpf",
        _has_handle_identity(
            DPF_RESULT_FILE_DATA_TYPE,
            DPF_RESULT_FILE_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_MODEL_DATA_TYPE,
        "DPF Model",
        "dpf",
        _has_handle_identity(DPF_MODEL_DATA_TYPE, DPF_MODEL_HANDLE_KIND),
        parents=(COREX_MODEL_INTERFACE_DATA_TYPE,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_MESH_DATA_TYPE,
        "DPF Mesh",
        "dpf",
        _has_handle_identity(DPF_MESH_DATA_TYPE, DPF_MESH_HANDLE_KIND),
        parents=(COREX_MESH_INTERFACE_DATA_TYPE,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_FIELD_DATA_TYPE,
        "DPF Field",
        "dpf",
        _has_handle_identity(DPF_FIELD_DATA_TYPE, DPF_FIELD_HANDLE_KIND),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_SCOPING_DATA_TYPE,
        "DPF Scoping",
        "dpf",
        _has_handle_identity(
            DPF_SCOPING_DATA_TYPE,
            DPF_MESH_SCOPING_HANDLE_KIND,
            DPF_TIME_SCOPING_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_FIELDS_CONTAINER_DATA_TYPE,
        "DPF Fields Container",
        "dpf",
        _has_handle_identity(
            DPF_FIELDS_CONTAINER_DATA_TYPE,
            DPF_FIELDS_CONTAINER_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_DATA_SOURCES_DATA_TYPE,
        "DPF Data Sources",
        "dpf",
        _has_handle_identity(
            DPF_DATA_SOURCES_DATA_TYPE,
            DPF_OBJECT_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_STREAMS_CONTAINER_DATA_TYPE,
        "DPF Streams Container",
        "dpf",
        _has_handle_identity(
            DPF_STREAMS_CONTAINER_DATA_TYPE,
            DPF_OBJECT_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_WORKFLOW_DATA_TYPE,
        "DPF Workflow",
        "dpf",
        _has_handle_identity(
            DPF_WORKFLOW_DATA_TYPE,
            DPF_OBJECT_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_OBJECT_HANDLE_DATA_TYPE,
        "DPF Object",
        "dpf",
        _has_handle_identity(
            DPF_OBJECT_HANDLE_DATA_TYPE,
            DPF_OBJECT_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
    DataTypeSpec(
        DPF_VIEWER_DATASET_DATA_TYPE,
        "Viewer Dataset",
        "viewer",
        _has_handle_identity(
            DPF_VIEWER_DATASET_DATA_TYPE,
            DPF_VIEWER_DATASET_HANDLE_KIND,
        ),
        parents=(GRAPH_DATA_TYPE_ID,),
        carriers=frozenset({"handle"}),
    ),
)

DPF_DATA_CONVERSIONS = ()

__all__ = [
    "DPF_DATA_CONVERSIONS",
    "DPF_DATA_SOURCES_DATA_TYPE",
    "DPF_DATA_TYPE_FAMILIES",
    "DPF_DATA_TYPE_OWNER_ID",
    "DPF_DATA_TYPES",
    "DPF_FIELD_DATA_TYPE",
    "DPF_FIELDS_CONTAINER_DATA_TYPE",
    "DPF_MESH_DATA_TYPE",
    "DPF_MODEL_DATA_TYPE",
    "DPF_OBJECT_HANDLE_DATA_TYPE",
    "DPF_PUBLIC_DATA_TYPES",
    "DPF_RESULT_FILE_DATA_TYPE",
    "DPF_SCOPING_DATA_TYPE",
    "DPF_SPECIALIZED_DATA_TYPES",
    "DPF_STREAMS_CONTAINER_DATA_TYPE",
    "DPF_WORKFLOW_DATA_TYPE",
    "DPF_VIEWER_DATASET_DATA_TYPE",
    "COREX_MESH_INTERFACE_DATA_TYPE",
    "COREX_MODEL_INTERFACE_DATA_TYPE",
    "normalize_dpf_type_id",
]
