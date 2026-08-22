from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from ea_node_editor.nodes.runtime_refs import RuntimeArtifactRef, RuntimeHandleRef

DPF_RESULT_FILE_HANDLE_KIND = "dpf.result_file"
DPF_MODEL_HANDLE_KIND = "dpf.model"
DPF_MESH_SCOPING_HANDLE_KIND = "dpf.mesh_scoping"
DPF_TIME_SCOPING_HANDLE_KIND = "dpf.time_scoping"
DPF_FIELDS_CONTAINER_HANDLE_KIND = "dpf.fields_container"
DPF_FIELD_HANDLE_KIND = "dpf.field"
DPF_MESH_HANDLE_KIND = "dpf.mesh"
DPF_VIEWER_DATASET_HANDLE_KIND = "dpf.viewer_dataset"
DPF_OBJECT_HANDLE_KIND = "dpf_object_handle"

SUPPORTED_RESULT_EXTENSIONS = frozenset({".rst", ".rth"})
DEFAULT_TIME_SCOPING_LOCATION = "TimeFreq"
DEFAULT_EXPORT_SUBDIRECTORY = PurePosixPath("dpf")
DEFAULT_VTU_BASENAME = "dataset"
DEFAULT_VTM_FILENAME = "dataset.vtm"
MESH_LOCATION_ALIASES = {
    "nodal": "Nodal",
    "node": "Nodal",
    "nodes": "Nodal",
    "elemental": "Elemental",
    "element": "Elemental",
    "elements": "Elemental",
}
FIELD_LOCATION_ALIASES = {
    **MESH_LOCATION_ALIASES,
    "elemental_nodal": "ElementalNodal",
    "elementalnodal": "ElementalNodal",
}
SUPPORTED_OUTPUT_PROFILES = frozenset({"memory", "stored", "both"})
SUPPORTED_EXPORT_FORMATS = frozenset({"csv", "png", "vtu", "vtm"})
SUPPORTED_INVARIANTS = frozenset(
    {"von_mises", "principal_1", "principal_2", "principal_3", "intensity", "max_shear"}
)
SUPPORTED_FIELD_MATH_OPERATIONS = frozenset({"add", "subtract", "multiply", "divide", "scale"})
INVALID_ARTIFACT_TOKEN_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class DpfRuntimeUnavailableError(RuntimeError):
    """Raised when optional ansys.dpf.core dependencies are not available."""


class DpfOperatorInvocationError(RuntimeError):
    """Raised when descriptor-driven DPF operator execution cannot complete."""


class UnsupportedDpfResultFileError(ValueError):
    """Raised when a requested result file is not a supported Mechanical result."""


@dataclass(slots=True, frozen=True)
class DpfResultFile:
    path: Path
    extension: str
    cache_key: str


@dataclass(slots=True, frozen=True)
class DpfFieldRange:
    minimum: RuntimeHandleRef
    maximum: RuntimeHandleRef


@dataclass(slots=True, frozen=True)
class DpfOperatorBinding:
    value_key: str
    pin_name: str
    value_origin: str
    omission_semantics: str
    exclusive_group: str = ""
    omitted: bool = False


@dataclass(slots=True, frozen=True)
class DpfOperatorInvocationResult:
    node_type_id: str
    variant_key: str
    operator_name: str
    outputs: dict[str, Any] = field(default_factory=dict)
    bound_inputs: tuple[DpfOperatorBinding, ...] = ()


@dataclass(slots=True, frozen=True)
class DpfMaterializationResult:
    output_profile: str
    dataset_ref: RuntimeHandleRef | None = None
    artifacts: dict[str, RuntimeArtifactRef] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DpfMinMaxEnvelope:
    envelope_min: RuntimeHandleRef
    envelope_max: RuntimeHandleRef
    per_set_rows: tuple[dict[str, Any], ...]
    overall: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DpfTimeHistorySeries:
    series: RuntimeHandleRef
    rows: tuple[dict[str, Any], ...]
    time_values: tuple[float, ...]
    entity_ids: tuple[int, ...]


@dataclass(slots=True, frozen=True)
class DpfTableExportResult:
    rows: tuple[dict[str, Any], ...]
    columns: tuple[str, ...]
    csv_artifact: RuntimeArtifactRef | None = None


__all__ = [
    "DPF_FIELDS_CONTAINER_HANDLE_KIND",
    "DPF_FIELD_HANDLE_KIND",
    "DPF_MESH_SCOPING_HANDLE_KIND",
    "DPF_MESH_HANDLE_KIND",
    "DPF_MODEL_HANDLE_KIND",
    "DPF_OBJECT_HANDLE_KIND",
    "DPF_RESULT_FILE_HANDLE_KIND",
    "DPF_TIME_SCOPING_HANDLE_KIND",
    "DPF_VIEWER_DATASET_HANDLE_KIND",
    "SUPPORTED_FIELD_MATH_OPERATIONS",
    "SUPPORTED_INVARIANTS",
    "DpfFieldRange",
    "DpfMaterializationResult",
    "DpfMinMaxEnvelope",
    "DpfOperatorBinding",
    "DpfOperatorInvocationError",
    "DpfOperatorInvocationResult",
    "DpfResultFile",
    "DpfRuntimeUnavailableError",
    "DpfTableExportResult",
    "DpfTimeHistorySeries",
    "UnsupportedDpfResultFileError",
]
