from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from ea_node_editor.nodes.types import RuntimeArtifactRef, RuntimeHandleRef

DPF_RESULT_FILE_HANDLE_KIND = "dpf.result_file"
DPF_MODEL_HANDLE_KIND = "dpf.model"
DPF_MESH_SCOPING_HANDLE_KIND = "dpf.mesh_scoping"
DPF_TIME_SCOPING_HANDLE_KIND = "dpf.time_scoping"
DPF_FIELDS_CONTAINER_HANDLE_KIND = "dpf.fields_container"
DPF_FIELD_HANDLE_KIND = "dpf.field"
DPF_MESH_HANDLE_KIND = "dpf.mesh"
DPF_VIEWER_DATASET_HANDLE_KIND = "dpf.viewer_dataset"

SUPPORTED_RESULT_EXTENSIONS = frozenset({".rst", ".rth"})
DEFAULT_TIME_SCOPING_LOCATION = "TimeFreq"
DEFAULT_EXPORT_SUBDIRECTORY = PurePosixPath("artifacts") / "dpf"
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


__all__ = [
    "DPF_FIELDS_CONTAINER_HANDLE_KIND",
    "DPF_FIELD_HANDLE_KIND",
    "DPF_MESH_SCOPING_HANDLE_KIND",
    "DPF_MESH_HANDLE_KIND",
    "DPF_MODEL_HANDLE_KIND",
    "DPF_RESULT_FILE_HANDLE_KIND",
    "DPF_TIME_SCOPING_HANDLE_KIND",
    "DPF_VIEWER_DATASET_HANDLE_KIND",
    "DpfFieldRange",
    "DpfMaterializationResult",
    "DpfOperatorBinding",
    "DpfOperatorInvocationError",
    "DpfOperatorInvocationResult",
    "DpfResultFile",
    "DpfRuntimeUnavailableError",
    "UnsupportedDpfResultFileError",
]
