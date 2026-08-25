# Purpose: Compose built-in, add-on, and external plugin data types before node descriptors.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_plugin_loader.py, tests/test_corex_contract_catalog.py

from __future__ import annotations

from pathlib import Path
from typing import Any

from ea_node_editor.nodes.builtins.core import CORE_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.data_control import DATA_CONTROL_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.engineering_imports import (
    ENGINEERING_IMPORT_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.engineering_viewer import (
    ENGINEERING_VIEWER_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.excalidraw import EXCALIDRAW_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.integrations import INTEGRATION_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.integrations_ssh_sftp import (
    SSH_SFTP_DATA_TYPE_FAMILIES,
    SSH_SFTP_DATA_TYPE_OWNER_ID,
    SSH_SFTP_DATA_TYPES,
    SSH_SFTP_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.jupyter_notebook import (
    JUPYTER_NOTEBOOK_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.math_interval import MATH_INTERVAL_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_annotation import (
    PASSIVE_ANNOTATION_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.passive_flowchart import (
    PASSIVE_FLOWCHART_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.passive_media import PASSIVE_MEDIA_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.passive_planning import (
    PASSIVE_PLANNING_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.plot import PLOT_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.subnode import SUBNODE_NODE_DESCRIPTORS
from ea_node_editor.nodes.builtins.ai_ml_contracts import (
    COREX_AI_ML_CONTRACTS_OWNER_ID,
    COREX_AI_ML_CONTRACTS_OWNER_VERSION,
    COREX_AI_ML_VECTOR_DATABASE_CANDIDATE_CONTRACT_MANIFEST,
    COREX_AI_ML_VECTOR_DATABASE_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.core_values import (
    COREX_CORE_VALUE_CONTRACT_MANIFEST,
    COREX_CORE_VALUE_OWNER_ID,
    COREX_CORE_VALUE_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.core_media import (
    COREX_CORE_MEDIA_CONTRACT_MANIFEST,
    COREX_CORE_MEDIA_OWNER_ID,
    COREX_CORE_MEDIA_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.core_unit_nodes import (
    COREX_CORE_UNIT_NODE_CONTRACT_MANIFEST,
    COREX_CORE_UNIT_NODE_DESCRIPTORS,
    COREX_CORE_UNIT_NODE_OWNER_ID,
    COREX_CORE_UNIT_NODE_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.fem_contracts import (
    COREX_FEM_CONTRACT_MANIFEST,
    COREX_FEM_CONTRACTS_OWNER_ID,
    COREX_FEM_CONTRACTS_OWNER_VERSION,
    COREX_FEM_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.geometry_contracts import (
    COREX_GEOMETRY_COORDINATE_SYSTEM_VALUE_CANDIDATE_CONTRACT_MANIFEST,
    COREX_GEOMETRY_CONTRACTS_OWNER_ID,
    COREX_GEOMETRY_CONTRACTS_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.geometry_primitives import (
    COREX_GEOMETRY_PRIMITIVES_CONTRACT_MANIFEST,
    COREX_GEOMETRY_PRIMITIVES_OWNER_ID,
    COREX_GEOMETRY_PRIMITIVES_OWNER_VERSION,
    COREX_GEOMETRY_PRIMITIVE_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.mesh_contracts import (
    COREX_DECONSTRUCT_MESH_FACE_CANDIDATE_NODE_DESCRIPTORS,
    COREX_MESH_CONTRACTS_OWNER_ID,
    COREX_MESH_CONTRACTS_OWNER_VERSION,
    COREX_MESH_PARAMETER_CANDIDATE_CONTRACT_MANIFEST,
)
from ea_node_editor.nodes.builtins.voxel_contracts import (
    COREX_VOXEL_CONTRACT_MANIFEST,
    COREX_VOXEL_CONTRACTS_OWNER_ID,
    COREX_VOXEL_CONTRACTS_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.rich_value_nodes import (
    COREX_RICH_VALUE_LLM_CANDIDATE_CONTRACT_MANIFEST,
    COREX_RICH_VALUE_NODE_DESCRIPTORS,
    COREX_RICH_VALUE_OWNER_ID,
    COREX_RICH_VALUE_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.reporting import (
    COREX_REPORTING_CONTRACT_MANIFEST,
    COREX_REPORTING_NODE_DESCRIPTORS,
    COREX_REPORTING_OWNER_ID,
    COREX_REPORTING_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.security_contracts import (
    COREX_SECURITY_CONTRACT_MANIFEST,
    COREX_SECURITY_OWNER_ID,
    COREX_SECURITY_OWNER_VERSION,
    COREX_WINDOWS_AUTHENTICATION_NODE_CONTRACT_MANIFEST,
    COREX_WINDOWS_AUTHENTICATION_NODE_DESCRIPTORS,
    COREX_WINDOWS_AUTHENTICATION_NODE_OWNER_ID,
    COREX_WINDOWS_AUTHENTICATION_NODE_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.spatial_values import (
    COREX_SPATIAL_VALUES_CONSTRUCTION_NODE_DESCRIPTORS,
    COREX_SPATIAL_VALUES_OWNER_ID,
    COREX_SPATIAL_VALUES_OWNER_VERSION,
    COREX_SPATIAL_VALUES_COORDINATE_SYSTEM_CANDIDATE_CONTRACT_MANIFEST,
)
from ea_node_editor.nodes.builtins.core_value_nodes import (
    COREX_CORE_VALUE_NODE_BUNDLE_DESCRIPTORS,
    COREX_CORE_VALUE_NODE_CONTRACT_MANIFEST,
    COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS,
    COREX_CORE_VALUE_NODE_OWNER_ID,
    COREX_CORE_VALUE_NODE_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.tree_path import (
    COREX_TREE_PATH_CONTRACT_MANIFEST,
    COREX_TREE_PATH_OWNER_ID,
    COREX_TREE_PATH_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.units import (
    COREX_UNITS_CONTRACT_MANIFEST,
    COREX_UNITS_OWNER_ID,
    COREX_UNITS_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.viewer_viewport import (
    COREX_VIEWER_VIEWPORT_CONTRACT_MANIFEST,
    COREX_VIEWER_VIEWPORT_NODE_DESCRIPTORS,
    COREX_VIEWER_VIEWPORT_OWNER_ID,
    COREX_VIEWER_VIEWPORT_OWNER_VERSION,
)
from ea_node_editor.nodes.builtins.web_viewer import WEB_PAGE_VIEWER_NODE_DESCRIPTORS
from ea_node_editor.nodes.core_data_types import (
    CORE_DATA_CONVERSIONS,
    CORE_DATA_TYPE_FAMILIES,
    CORE_DATA_TYPE_OWNER_ID,
    CORE_DATA_TYPE_OWNER_VERSION,
    CORE_DATA_TYPES,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.plugin_contracts import PluginContractManifest


BUILTIN_NODE_DESCRIPTORS = (
    *CORE_NODE_DESCRIPTORS,
    *DATA_CONTROL_NODE_DESCRIPTORS,
    *INTEGRATION_NODE_DESCRIPTORS,
    *ENGINEERING_IMPORT_NODE_DESCRIPTORS,
    *ENGINEERING_VIEWER_NODE_DESCRIPTORS,
    *COREX_AI_ML_VECTOR_DATABASE_NODE_DESCRIPTORS,
    *COREX_RICH_VALUE_NODE_DESCRIPTORS,
    *COREX_GEOMETRY_PRIMITIVE_NODE_DESCRIPTORS,
    *SSH_SFTP_NODE_DESCRIPTORS,
    *MATH_INTERVAL_NODE_DESCRIPTORS,
    *COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS,
    *COREX_CORE_UNIT_NODE_DESCRIPTORS,
    *COREX_SPATIAL_VALUES_CONSTRUCTION_NODE_DESCRIPTORS,
    *COREX_DECONSTRUCT_MESH_FACE_CANDIDATE_NODE_DESCRIPTORS,
    *COREX_VIEWER_VIEWPORT_NODE_DESCRIPTORS,
    *COREX_REPORTING_NODE_DESCRIPTORS,
    *COREX_WINDOWS_AUTHENTICATION_NODE_DESCRIPTORS,
    *PLOT_NODE_DESCRIPTORS,
    *SUBNODE_NODE_DESCRIPTORS,
    *PASSIVE_FLOWCHART_NODE_DESCRIPTORS,
    *PASSIVE_PLANNING_NODE_DESCRIPTORS,
    *PASSIVE_ANNOTATION_NODE_DESCRIPTORS,
    *PASSIVE_MEDIA_NODE_DESCRIPTORS,
    *WEB_PAGE_VIEWER_NODE_DESCRIPTORS,
    *JUPYTER_NOTEBOOK_NODE_DESCRIPTORS,
    *EXCALIDRAW_NODE_DESCRIPTORS,
)


def build_builtin_registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register_plugin_bundle(
        PluginContractManifest(
            data_type_families=CORE_DATA_TYPE_FAMILIES,
            data_types=CORE_DATA_TYPES,
            data_conversions=CORE_DATA_CONVERSIONS,
        ),
        (),
        owner_id=CORE_DATA_TYPE_OWNER_ID,
        owner_version=CORE_DATA_TYPE_OWNER_VERSION,
        source_label="ea_node_editor.nodes.core_data_types",
        replace_owner=True,
    )
    registry.register_plugin_bundle(
        COREX_GEOMETRY_COORDINATE_SYSTEM_VALUE_CANDIDATE_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_GEOMETRY_CONTRACTS_OWNER_ID,
        owner_version=COREX_GEOMETRY_CONTRACTS_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.geometry_contracts",
    )
    registry.register_plugin_bundle(
        COREX_VOXEL_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_VOXEL_CONTRACTS_OWNER_ID,
        owner_version=COREX_VOXEL_CONTRACTS_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.voxel_contracts",
    )
    registry.register_plugin_bundle(
        COREX_MESH_PARAMETER_CANDIDATE_CONTRACT_MANIFEST,
        COREX_DECONSTRUCT_MESH_FACE_CANDIDATE_NODE_DESCRIPTORS,
        owner_id=COREX_MESH_CONTRACTS_OWNER_ID,
        owner_version=COREX_MESH_CONTRACTS_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.mesh_contracts",
    )
    registry.register_plugin_bundle(
        COREX_FEM_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_FEM_CONTRACTS_OWNER_ID,
        owner_version=COREX_FEM_CONTRACTS_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.fem_contracts",
    )
    registry.register_plugin_bundle(
        COREX_AI_ML_VECTOR_DATABASE_CANDIDATE_CONTRACT_MANIFEST,
        COREX_AI_ML_VECTOR_DATABASE_NODE_DESCRIPTORS,
        owner_id=COREX_AI_ML_CONTRACTS_OWNER_ID,
        owner_version=COREX_AI_ML_CONTRACTS_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.ai_ml_contracts",
    )
    registry.register_plugin_bundle(
        COREX_RICH_VALUE_LLM_CANDIDATE_CONTRACT_MANIFEST,
        COREX_RICH_VALUE_NODE_DESCRIPTORS,
        owner_id=COREX_RICH_VALUE_OWNER_ID,
        owner_version=COREX_RICH_VALUE_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.rich_value_nodes",
    )
    registry.register_plugin_bundle(
        COREX_GEOMETRY_PRIMITIVES_CONTRACT_MANIFEST,
        COREX_GEOMETRY_PRIMITIVE_NODE_DESCRIPTORS,
        owner_id=COREX_GEOMETRY_PRIMITIVES_OWNER_ID,
        owner_version=COREX_GEOMETRY_PRIMITIVES_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.geometry_primitives",
        replace_owner=True,
    )
    registry.register_plugin_bundle(
        COREX_CORE_VALUE_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_CORE_VALUE_OWNER_ID,
        owner_version=COREX_CORE_VALUE_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.core_values",
    )
    registry.register_plugin_bundle(
        COREX_TREE_PATH_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_TREE_PATH_OWNER_ID,
        owner_version=COREX_TREE_PATH_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.tree_path",
    )
    registry.register_plugin_bundle(
        COREX_CORE_MEDIA_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_CORE_MEDIA_OWNER_ID,
        owner_version=COREX_CORE_MEDIA_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.core_media",
    )
    registry.register_plugin_bundle(
        COREX_UNITS_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_UNITS_OWNER_ID,
        owner_version=COREX_UNITS_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.units",
    )
    registry.register_plugin_bundle(
        COREX_SPATIAL_VALUES_COORDINATE_SYSTEM_CANDIDATE_CONTRACT_MANIFEST,
        COREX_SPATIAL_VALUES_CONSTRUCTION_NODE_DESCRIPTORS,
        owner_id=COREX_SPATIAL_VALUES_OWNER_ID,
        owner_version=COREX_SPATIAL_VALUES_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.spatial_values",
    )
    registry.register_descriptors(
        COREX_FEM_NODE_DESCRIPTORS,
        owner_id=COREX_FEM_CONTRACTS_OWNER_ID,
    )
    registry.register_plugin_bundle(
        COREX_VIEWER_VIEWPORT_CONTRACT_MANIFEST,
        COREX_VIEWER_VIEWPORT_NODE_DESCRIPTORS,
        owner_id=COREX_VIEWER_VIEWPORT_OWNER_ID,
        owner_version=COREX_VIEWER_VIEWPORT_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.viewer_viewport",
    )
    registry.register_plugin_bundle(
        COREX_REPORTING_CONTRACT_MANIFEST,
        COREX_REPORTING_NODE_DESCRIPTORS,
        owner_id=COREX_REPORTING_OWNER_ID,
        owner_version=COREX_REPORTING_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.reporting",
    )
    registry.register_plugin_bundle(
        COREX_SECURITY_CONTRACT_MANIFEST,
        (),
        owner_id=COREX_SECURITY_OWNER_ID,
        owner_version=COREX_SECURITY_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.security_contracts",
    )
    registry.register_plugin_bundle(
        COREX_WINDOWS_AUTHENTICATION_NODE_CONTRACT_MANIFEST,
        COREX_WINDOWS_AUTHENTICATION_NODE_DESCRIPTORS,
        owner_id=COREX_WINDOWS_AUTHENTICATION_NODE_OWNER_ID,
        owner_version=COREX_WINDOWS_AUTHENTICATION_NODE_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.security_contracts",
    )
    registry.register_plugin_bundle(
        COREX_CORE_VALUE_NODE_CONTRACT_MANIFEST,
        COREX_CORE_VALUE_NODE_BUNDLE_DESCRIPTORS,
        owner_id=COREX_CORE_VALUE_NODE_OWNER_ID,
        owner_version=COREX_CORE_VALUE_NODE_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.core_value_nodes",
    )
    registry.register_plugin_bundle(
        COREX_CORE_UNIT_NODE_CONTRACT_MANIFEST,
        COREX_CORE_UNIT_NODE_DESCRIPTORS,
        owner_id=COREX_CORE_UNIT_NODE_OWNER_ID,
        owner_version=COREX_CORE_UNIT_NODE_OWNER_VERSION,
        source_label="ea_node_editor.nodes.builtins.core_unit_nodes",
    )
    registry.register_plugin_bundle(
        PluginContractManifest(
            data_type_families=SSH_SFTP_DATA_TYPE_FAMILIES,
            data_types=SSH_SFTP_DATA_TYPES,
        ),
        SSH_SFTP_NODE_DESCRIPTORS,
        owner_id=SSH_SFTP_DATA_TYPE_OWNER_ID,
        source_label="ea_node_editor.nodes.builtins.integrations_ssh_sftp",
    )
    registry.register_descriptors(
        descriptor
        for descriptor in BUILTIN_NODE_DESCRIPTORS
        if descriptor
        not in (
            *COREX_AI_ML_VECTOR_DATABASE_NODE_DESCRIPTORS,
            *COREX_RICH_VALUE_NODE_DESCRIPTORS,
            *COREX_GEOMETRY_PRIMITIVE_NODE_DESCRIPTORS,
            *COREX_CORE_VALUE_NODE_BUNDLE_DESCRIPTORS,
            *COREX_CORE_UNIT_NODE_DESCRIPTORS,
            *COREX_SPATIAL_VALUES_CONSTRUCTION_NODE_DESCRIPTORS,
            *COREX_DECONSTRUCT_MESH_FACE_CANDIDATE_NODE_DESCRIPTORS,
            *COREX_VIEWER_VIEWPORT_NODE_DESCRIPTORS,
            *COREX_REPORTING_NODE_DESCRIPTORS,
            *COREX_WINDOWS_AUTHENTICATION_NODE_DESCRIPTORS,
            *SSH_SFTP_NODE_DESCRIPTORS,
        )
    )
    registry.freeze()
    return registry


def build_default_registry(
    extra_plugin_dirs: list[Path] | None = None,
    *,
    app_preferences_store: Any = None,
    preferences_document: Any = None,
    include_public_plugins: bool = True,
) -> NodeRegistry:
    registry = build_builtin_registry()

    from ea_node_editor.addons.catalog import live_addon_backend_collections
    from ea_node_editor.nodes.plugin_loader import (
        discover_and_load_plugins,
        register_plugin_backends,
    )

    for addon_backends in live_addon_backend_collections(
        preferences_document=preferences_document,
        store=app_preferences_store,
    ):
        register_plugin_backends(
            addon_backends.backends,
            registry,
            addon_backends.source,
        )
    if include_public_plugins:
        discover_and_load_plugins(registry, extra_dirs=extra_plugin_dirs)
    registry.freeze()
    return registry
