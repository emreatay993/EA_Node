from __future__ import annotations

from ea_node_editor.nodes.plugin_contracts import (
    AddOnManifest,
    ArtifactDescriptor,
    RuntimeBackendSpec,
    SurfaceCapabilitySpec,
    ToolchainRequirementSpec,
    ToolchainSpec,
)
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_DATA_CONVERSIONS,
    DPF_DATA_TYPE_FAMILIES,
    DPF_DATA_TYPES,
)

ANSYS_DPF_ADDON_ID = "ea_node_editor.builtins.ansys_dpf"
ANSYS_DPF_DEPENDENCY = "ansys.dpf.core"
ANSYS_DPF_RUNTIME_TOOLCHAIN_ID = "ansys_dpf.python_runtime"
ANSYS_DPF_VIEWER_TOOLCHAIN_ID = "ansys_dpf.viewer_runtime"
ANSYS_DPF_COMPUTE_BACKEND_ID = "ansys_dpf.python"
ANSYS_DPF_VIEWER_BACKEND_ID = "dpf_embedded"
ANSYS_DPF_VIEWER_SURFACE_CAPABILITY_ID = "ansys_dpf.viewer_surface"
ANSYS_DPF_FIELD_ARTIFACT_ID = "ansys_dpf.field_exports"

ANSYS_DPF_TOOLCHAINS = (
    ToolchainSpec(
        toolchain_id=ANSYS_DPF_RUNTIME_TOOLCHAIN_ID,
        display_name="ANSYS DPF Python Runtime",
        kind="python",
        language="python",
        requirements=(
            ToolchainRequirementSpec(
                requirement_id=ANSYS_DPF_DEPENDENCY,
                kind="python_module",
                display_name="ansys-dpf-core",
                import_name=ANSYS_DPF_DEPENDENCY,
            ),
        ),
    ),
    ToolchainSpec(
        toolchain_id=ANSYS_DPF_VIEWER_TOOLCHAIN_ID,
        display_name="ANSYS DPF Viewer Extras",
        kind="python",
        language="python",
        requirements=(
            ToolchainRequirementSpec(
                requirement_id="pyvista",
                kind="python_module",
                display_name="PyVista",
                import_name="pyvista",
                optional=True,
            ),
            ToolchainRequirementSpec(
                requirement_id="pyvistaqt",
                kind="python_module",
                display_name="PyVistaQt",
                import_name="pyvistaqt",
                optional=True,
            ),
            ToolchainRequirementSpec(
                requirement_id="vtk",
                kind="python_module",
                display_name="VTK",
                import_name="vtk",
                optional=True,
            ),
        ),
    ),
)
ANSYS_DPF_SURFACE_CAPABILITIES = (
    SurfaceCapabilitySpec(
        capability_id=ANSYS_DPF_VIEWER_SURFACE_CAPABILITY_ID,
        surface_family="viewer",
        runtime_backend_id=ANSYS_DPF_VIEWER_BACKEND_ID,
        qml_component="viewer/GraphViewerSurface.qml",
        fullscreen=True,
        input_modes=("pointer", "keyboard", "wheel", "touch", "stylus"),
        render_quality={
            "supported_quality_tiers": ("full", "proxy"),
        },
    ),
)
ANSYS_DPF_ARTIFACTS = (
    ArtifactDescriptor(
        artifact_id=ANSYS_DPF_FIELD_ARTIFACT_ID,
        kind="data_bundle",
        runtime_backend_id=ANSYS_DPF_VIEWER_BACKEND_ID,
        toolchain_id=ANSYS_DPF_RUNTIME_TOOLCHAIN_ID,
        formats=("csv", "png", "vtu", "vtm"),
        metadata={"artifact_key_property": "artifact_key", "formats_property": "export_formats"},
    ),
)
ANSYS_DPF_RUNTIME_BACKENDS = (
    RuntimeBackendSpec(
        backend_id=ANSYS_DPF_COMPUTE_BACKEND_ID,
        display_name="ANSYS DPF Python Runtime",
        kind="python",
        adapter_module="ea_node_editor.execution.dpf_runtime_service",
        adapter_factory="DpfRuntimeService",
        runtime_behaviors=("active",),
        toolchain_ids=(ANSYS_DPF_RUNTIME_TOOLCHAIN_ID,),
        artifact_ids=(ANSYS_DPF_FIELD_ARTIFACT_ID,),
    ),
    RuntimeBackendSpec(
        backend_id=ANSYS_DPF_VIEWER_BACKEND_ID,
        display_name="ANSYS DPF Embedded Viewer",
        kind="external_process",
        adapter_module="ea_node_editor.execution.viewer_backend_dpf",
        adapter_factory="DpfExecutionViewerBackend",
        transport="viewer_transport_bundle",
        transport_revision=1,
        runtime_behaviors=("active",),
        toolchain_ids=(ANSYS_DPF_RUNTIME_TOOLCHAIN_ID, ANSYS_DPF_VIEWER_TOOLCHAIN_ID),
        artifact_ids=(ANSYS_DPF_FIELD_ARTIFACT_ID,),
        surface_capability_ids=(ANSYS_DPF_VIEWER_SURFACE_CAPABILITY_ID,),
    ),
)
ANSYS_DPF_ADDON_MANIFEST = AddOnManifest(
    addon_id=ANSYS_DPF_ADDON_ID,
    display_name="ANSYS DPF",
    apply_policy="hot_apply",
    vendor="Ansys",
    summary="Enable ANSYS DPF helper, operator, and viewer nodes when ansys.dpf.core is installed.",
    details=(
        "Provides the ANSYS DPF node family used for local result-file inspection, "
        "operator execution, and viewer workflows."
    ),
    dependencies=(ANSYS_DPF_DEPENDENCY,),
    runtime_backends=ANSYS_DPF_RUNTIME_BACKENDS,
    toolchains=ANSYS_DPF_TOOLCHAINS,
    artifacts=ANSYS_DPF_ARTIFACTS,
    surface_capabilities=ANSYS_DPF_SURFACE_CAPABILITIES,
    data_type_families=DPF_DATA_TYPE_FAMILIES,
    data_types=DPF_DATA_TYPES,
    data_conversions=DPF_DATA_CONVERSIONS,
)

__all__ = [
    "ANSYS_DPF_ADDON_ID",
    "ANSYS_DPF_ARTIFACTS",
    "ANSYS_DPF_ADDON_MANIFEST",
    "ANSYS_DPF_COMPUTE_BACKEND_ID",
    "ANSYS_DPF_DEPENDENCY",
    "ANSYS_DPF_FIELD_ARTIFACT_ID",
    "ANSYS_DPF_RUNTIME_BACKENDS",
    "ANSYS_DPF_RUNTIME_TOOLCHAIN_ID",
    "ANSYS_DPF_SURFACE_CAPABILITIES",
    "ANSYS_DPF_TOOLCHAINS",
    "ANSYS_DPF_VIEWER_BACKEND_ID",
    "ANSYS_DPF_VIEWER_SURFACE_CAPABILITY_ID",
    "ANSYS_DPF_VIEWER_TOOLCHAIN_ID",
    "DPF_DATA_CONVERSIONS",
    "DPF_DATA_TYPE_FAMILIES",
    "DPF_DATA_TYPES",
]
