from __future__ import annotations

from ea_node_editor.nodes.category_paths import CategoryPath

DPF_NODE_CATEGORY = "Ansys DPF"
DPF_NODE_CATEGORY_PATH: CategoryPath = (DPF_NODE_CATEGORY,)

DPF_INPUTS_FAMILY_PATH = ("Inputs",)
DPF_HELPERS_FAMILY_PATH = ("Helpers",)
DPF_OPERATORS_FAMILY_PATH = ("Operators",)
DPF_WORKFLOW_FAMILY_PATH = ("Workflow",)
DPF_VIEWER_FAMILY_PATH = ("Viewer",)
DPF_ADVANCED_FAMILY_PATH = ("Advanced",)
DPF_RAW_API_MIRROR_FAMILY_PATH = (*DPF_ADVANCED_FAMILY_PATH, "Raw API Mirror")

DPF_HELPERS_MODELS_FAMILY_PATH = (*DPF_HELPERS_FAMILY_PATH, "Models")
DPF_HELPERS_SCOPING_FAMILY_PATH = (*DPF_HELPERS_FAMILY_PATH, "Scoping")
DPF_HELPERS_FACTORIES_FAMILY_PATH = (*DPF_HELPERS_FAMILY_PATH, "Factories")
DPF_HELPERS_CONTAINERS_FAMILY_PATH = (*DPF_HELPERS_FAMILY_PATH, "Containers")
DPF_HELPERS_SUPPORT_FAMILY_PATH = (*DPF_HELPERS_FAMILY_PATH, "Support")


def dpf_category_path(*family_path: str) -> CategoryPath:
    return DPF_NODE_CATEGORY_PATH + tuple(segment for segment in family_path if segment)


DPF_INPUTS_CATEGORY_PATH = dpf_category_path(*DPF_INPUTS_FAMILY_PATH)
DPF_HELPERS_CATEGORY_PATH = dpf_category_path(*DPF_HELPERS_FAMILY_PATH)
DPF_OPERATORS_CATEGORY_PATH = dpf_category_path(*DPF_OPERATORS_FAMILY_PATH)
DPF_WORKFLOW_CATEGORY_PATH = dpf_category_path(*DPF_WORKFLOW_FAMILY_PATH)
DPF_VIEWER_CATEGORY_PATH = dpf_category_path(*DPF_VIEWER_FAMILY_PATH)
DPF_ADVANCED_CATEGORY_PATH = dpf_category_path(*DPF_ADVANCED_FAMILY_PATH)
DPF_RAW_API_MIRROR_CATEGORY_PATH = dpf_category_path(*DPF_RAW_API_MIRROR_FAMILY_PATH)

DPF_HELPERS_MODELS_CATEGORY_PATH = dpf_category_path(*DPF_HELPERS_MODELS_FAMILY_PATH)
DPF_HELPERS_SCOPING_CATEGORY_PATH = dpf_category_path(*DPF_HELPERS_SCOPING_FAMILY_PATH)
DPF_HELPERS_FACTORIES_CATEGORY_PATH = dpf_category_path(*DPF_HELPERS_FACTORIES_FAMILY_PATH)
DPF_HELPERS_CONTAINERS_CATEGORY_PATH = dpf_category_path(*DPF_HELPERS_CONTAINERS_FAMILY_PATH)
DPF_HELPERS_SUPPORT_CATEGORY_PATH = dpf_category_path(*DPF_HELPERS_SUPPORT_FAMILY_PATH)

DPF_OPERATOR_FAMILY_ORDER = (
    "result",
    "math",
    "utility",
    "mesh",
    "averaging",
    "logic",
    "filter",
    "metadata",
    "scoping",
    "geo",
    "min_max",
    "invariant",
    "mapping",
    "compression",
    "serialization",
    "server",
)

_ADVANCED_OPERATOR_FAMILIES = frozenset({"compression", "serialization", "server", "info"})
_OPERATOR_FAMILY_DISPLAY_NAMES = {
    "averaging": "Averaging",
    "compression": "Compression",
    "filter": "Filter",
    "geo": "Geo",
    "info": "Info",
    "invariant": "Invariant",
    "logic": "Logic",
    "mapping": "Mapping",
    "math": "Math",
    "mesh": "Mesh",
    "metadata": "Metadata",
    "min_max": "Min Max",
    "result": "Result",
    "scoping": "Scoping",
    "serialization": "Serialization",
    "server": "Server",
    "utility": "Utility",
}
_HELPER_ROLE_PATHS = {
    "models": DPF_HELPERS_MODELS_FAMILY_PATH,
    "scoping": DPF_HELPERS_SCOPING_FAMILY_PATH,
    "factories": DPF_HELPERS_FACTORIES_FAMILY_PATH,
    "containers": DPF_HELPERS_CONTAINERS_FAMILY_PATH,
    "support": DPF_HELPERS_SUPPORT_FAMILY_PATH,
}


def _normalized_token(value: str) -> str:
    return str(value or "").strip().replace("-", "_").replace(" ", "_").lower()


def operator_family_display_name(family: str) -> str:
    normalized_family = _normalized_token(family)
    if normalized_family in _OPERATOR_FAMILY_DISPLAY_NAMES:
        return _OPERATOR_FAMILY_DISPLAY_NAMES[normalized_family]
    return normalized_family.replace("_", " ").title()


def operator_source_path(family: str) -> str:
    normalized_family = _normalized_token(family)
    if not normalized_family:
        return "ansys.dpf.core.operators"
    return f"ansys.dpf.core.operators.{normalized_family}"


def operator_family_from_source_path(source_path: str) -> str:
    normalized_path = str(source_path or "").strip()
    prefix = "ansys.dpf.core.operators."
    if not normalized_path.startswith(prefix):
        return ""
    remainder = normalized_path[len(prefix) :]
    return _normalized_token(remainder.split(".", 1)[0])


def operator_family_path(family: str, *, stability: str = "core") -> tuple[str, ...]:
    normalized_family = _normalized_token(family)
    normalized_stability = _normalized_token(stability)
    display_name = operator_family_display_name(normalized_family)
    if normalized_stability in {"advanced", "raw"} or normalized_family in _ADVANCED_OPERATOR_FAMILIES:
        return (*DPF_RAW_API_MIRROR_FAMILY_PATH, display_name)
    return (*DPF_OPERATORS_FAMILY_PATH, display_name)


def operator_family_category_path(family: str, *, stability: str = "core") -> CategoryPath:
    return dpf_category_path(*operator_family_path(family, stability=stability))


def helper_role_path(role: str) -> tuple[str, ...]:
    normalized_role = _normalized_token(role)
    try:
        return _HELPER_ROLE_PATHS[normalized_role]
    except KeyError as exc:
        raise ValueError(f"Unsupported DPF helper role: {role}") from exc


def helper_role_category_path(role: str) -> CategoryPath:
    return dpf_category_path(*helper_role_path(role))


__all__ = [
    "DPF_ADVANCED_CATEGORY_PATH",
    "DPF_ADVANCED_FAMILY_PATH",
    "DPF_HELPERS_CATEGORY_PATH",
    "DPF_HELPERS_CONTAINERS_CATEGORY_PATH",
    "DPF_HELPERS_CONTAINERS_FAMILY_PATH",
    "DPF_HELPERS_FACTORIES_CATEGORY_PATH",
    "DPF_HELPERS_FACTORIES_FAMILY_PATH",
    "DPF_HELPERS_FAMILY_PATH",
    "DPF_HELPERS_MODELS_CATEGORY_PATH",
    "DPF_HELPERS_MODELS_FAMILY_PATH",
    "DPF_HELPERS_SCOPING_CATEGORY_PATH",
    "DPF_HELPERS_SCOPING_FAMILY_PATH",
    "DPF_HELPERS_SUPPORT_CATEGORY_PATH",
    "DPF_HELPERS_SUPPORT_FAMILY_PATH",
    "DPF_INPUTS_CATEGORY_PATH",
    "DPF_INPUTS_FAMILY_PATH",
    "DPF_NODE_CATEGORY",
    "DPF_NODE_CATEGORY_PATH",
    "DPF_OPERATOR_FAMILY_ORDER",
    "DPF_OPERATORS_CATEGORY_PATH",
    "DPF_OPERATORS_FAMILY_PATH",
    "DPF_RAW_API_MIRROR_CATEGORY_PATH",
    "DPF_RAW_API_MIRROR_FAMILY_PATH",
    "DPF_VIEWER_CATEGORY_PATH",
    "DPF_VIEWER_FAMILY_PATH",
    "DPF_WORKFLOW_CATEGORY_PATH",
    "DPF_WORKFLOW_FAMILY_PATH",
    "dpf_category_path",
    "helper_role_category_path",
    "helper_role_path",
    "operator_family_category_path",
    "operator_family_display_name",
    "operator_family_from_source_path",
    "operator_family_path",
    "operator_source_path",
]
