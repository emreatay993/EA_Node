# Purpose: Define worker-owned exact CAD and surface-mesh import handles.
# Map: feature_routes/neutral_cad_fe_engineering_viewer.md
# Tests: tests/test_engineering_import_nodes.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ea_node_editor.nodes.plugin_contracts import PluginContractManifest
from ea_node_editor.runtime_contracts import DataTypeSpec, RuntimeHandleRef

CAD_MODEL_DATA_TYPE_ID = "COREX.Geometry.CADModel"
CAD_MODEL_HANDLE_KIND = "corex.geometry.cad_model"
SURFACE_MODEL_DATA_TYPE_ID = "COREX.Mesh.SurfaceModel"
SURFACE_MODEL_HANDLE_KIND = "corex.mesh.surface_model"


def is_cad_model_handle(value: object) -> bool:
    return (
        type(value) is RuntimeHandleRef
        and value.data_type_id == CAD_MODEL_DATA_TYPE_ID
        and value.schema_version == 1
        and value.kind == CAD_MODEL_HANDLE_KIND
        and value.metadata == {}
    )


def is_surface_model_handle(value: object) -> bool:
    return (
        type(value) is RuntimeHandleRef
        and value.data_type_id == SURFACE_MODEL_DATA_TYPE_ID
        and value.schema_version == 1
        and value.kind == SURFACE_MODEL_HANDLE_KIND
        and value.metadata == {}
    )


CAD_MODEL_DATA_TYPE = DataTypeSpec(
    CAD_MODEL_DATA_TYPE_ID,
    "CAD Model",
    "engineering",
    is_cad_model_handle,
    carriers=frozenset({"handle"}),
    persistence="never",
    sensitivity="normal",
    payload_schema_version=1,
    implementation_version="1",
)

SURFACE_MODEL_DATA_TYPE = DataTypeSpec(
    SURFACE_MODEL_DATA_TYPE_ID,
    "Surface Mesh Model",
    "engineering",
    is_surface_model_handle,
    carriers=frozenset({"handle"}),
    persistence="never",
    sensitivity="normal",
    payload_schema_version=1,
    implementation_version="1",
)

IMPORTED_MODEL_CONTRACT_MANIFEST = PluginContractManifest(
    data_types=(CAD_MODEL_DATA_TYPE, SURFACE_MODEL_DATA_TYPE),
)
IMPORTED_MODEL_OWNER_ID = "corex.imported_models"
IMPORTED_MODEL_OWNER_VERSION = "1"


@dataclass(slots=True)
class CADModelRecord:
    shape: Any | None
    cad_metadata: Any | None
    source_name: str
    source_format: str
    source_sha256: str
    source_unit: str
    interpreted_unit: str
    length_unit: str = "mm"

    def close(self) -> None:
        self.shape = None
        self.cad_metadata = None

    dispose = close


@dataclass(slots=True)
class SurfaceModelRecord:
    dataset: Any | None
    source_name: str
    source_sha256: str
    source_unit: str
    length_unit: str = "mm"

    def close(self) -> None:
        self.dataset = None

    dispose = close


def resolve_cad_model(services: Any, value: object) -> CADModelRecord:
    if not is_cad_model_handle(value):
        raise TypeError("CAD Model input must be an exact COREX CADModel handle")
    record = services.resolve_handle(
        value,
        expected_data_type=CAD_MODEL_DATA_TYPE_ID,
        expected_kind=CAD_MODEL_HANDLE_KIND,
    )
    if type(record) is not CADModelRecord or record.shape is None or record.cad_metadata is None:
        raise RuntimeError("CAD Model handle no longer owns a live model")
    return record


def resolve_surface_model(services: Any, value: object) -> SurfaceModelRecord:
    if not is_surface_model_handle(value):
        raise TypeError("Surface Model input must be an exact COREX SurfaceModel handle")
    record = services.resolve_handle(
        value,
        expected_data_type=SURFACE_MODEL_DATA_TYPE_ID,
        expected_kind=SURFACE_MODEL_HANDLE_KIND,
    )
    if type(record) is not SurfaceModelRecord or record.dataset is None:
        raise RuntimeError("Surface Model handle no longer owns a live mesh")
    return record
