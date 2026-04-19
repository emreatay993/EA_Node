from __future__ import annotations

from dataclasses import dataclass

from ea_node_editor.nodes.plugin_contracts import AddOnManifest

ANSYS_DPF_ADDON_ID = "ea_node_editor.builtins.ansys_dpf"


@dataclass(slots=True, frozen=True)
class AddOnRegistration:
    manifest: AddOnManifest
    backend_module: str
    backend_id: str
    backend_collection_attr: str = "PLUGIN_BACKENDS"
    version_resolver_attr: str = ""


REGISTERED_ADDON_REGISTRATIONS = (
    AddOnRegistration(
        manifest=AddOnManifest(
            addon_id=ANSYS_DPF_ADDON_ID,
            display_name="ANSYS DPF",
            apply_policy="hot_apply",
            vendor="Ansys",
            summary="Enable ANSYS DPF helper, operator, and viewer nodes when ansys.dpf.core is installed.",
            details=(
                "Provides the ANSYS DPF node family used for local result-file inspection, "
                "operator execution, and viewer workflows."
            ),
            dependencies=("ansys.dpf.core",),
        ),
        backend_module="ea_node_editor.nodes.builtins.ansys_dpf_catalog",
        backend_id=ANSYS_DPF_ADDON_ID,
        version_resolver_attr="resolve_ansys_dpf_plugin_version",
    ),
)


def registered_addon_registrations() -> tuple[AddOnRegistration, ...]:
    return REGISTERED_ADDON_REGISTRATIONS


__all__ = [
    "ANSYS_DPF_ADDON_ID",
    "AddOnRegistration",
    "REGISTERED_ADDON_REGISTRATIONS",
    "registered_addon_registrations",
]
