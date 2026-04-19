from __future__ import annotations

from ea_node_editor.nodes.plugin_contracts import AddOnManifest

ANSYS_DPF_ADDON_ID = "ea_node_editor.builtins.ansys_dpf"
ANSYS_DPF_DEPENDENCY = "ansys.dpf.core"
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
)

__all__ = [
    "ANSYS_DPF_ADDON_ID",
    "ANSYS_DPF_ADDON_MANIFEST",
    "ANSYS_DPF_DEPENDENCY",
]
