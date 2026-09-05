from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "node_catalog"
FROZEN_CATALOG_PATH = FIXTURE_DIR / "pre_cutover_non_dpf_catalog.json"
DOCUMENTATION_OVERLAY_PATH = FIXTURE_DIR / "t17_non_dpf_documentation_overlay.json"
STRUCTURAL_OVERLAY_PATH = FIXTURE_DIR / "unified_media_panel_structural_overlay.json"
CURRENT_CONTRACT_OVERLAY_PATH = (
    FIXTURE_DIR / "current_non_dpf_contract_overlay.json"
)
SOLUTION_REUSE_CLASSIFICATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "specs"
    / "perf"
    / "COREX_SOLUTION_REUSE_CLASSIFICATION.md"
)
FROZEN_CATALOG_SHA256 = (
    "3CF91390E9E4C606B571ED3C907D7BF35647165F5358328F8FE9C18BF15C618F"
)
SOLUTION_REUSE_CLASSIFICATION_SHA256 = (
    "0693C625B37118F46032DEF77BE4EB4C46D28774A984CB31684130DE62422551"
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate overlay patch or field: {key}")
        result[key] = value
    return result


def _exact_keys(value: object, expected: set[str], *, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{label} must contain only {sorted(expected)}")
    return value


def _catalog_by_type(catalog: object) -> dict[str, dict[str, Any]]:
    if type(catalog) is not list:
        raise ValueError("Non-DPF catalog must be a list")
    by_type: dict[str, dict[str, Any]] = {}
    for row in catalog:
        if type(row) is not dict or type(row.get("spec")) is not dict:
            raise ValueError("Non-DPF catalog row is invalid")
        type_id = row["spec"].get("type_id")
        if type(type_id) is not str or type_id in by_type:
            raise ValueError(f"Invalid or duplicate catalog type ID: {type_id!r}")
        by_type[type_id] = row
    return by_type


def _replace_catalog_rows(
    catalog: list[dict[str, Any]],
    *,
    remove_type_ids: object,
    add_rows: object,
    label: str,
) -> list[dict[str, Any]]:
    if (
        type(remove_type_ids) is not list
        or any(type(item) is not str or not item for item in remove_type_ids)
        or len(remove_type_ids) != len(set(remove_type_ids))
    ):
        raise ValueError(f"{label} remove_type_ids must be a unique string list")
    retained = _catalog_by_type(catalog)
    unknown_removals = set(remove_type_ids) - set(retained)
    if unknown_removals:
        raise ValueError(f"Unknown {label.lower()} removal: {sorted(unknown_removals)}")
    retained_rows = [
        row for row in catalog if row["spec"]["type_id"] not in set(remove_type_ids)
    ]
    additions = _catalog_by_type(add_rows)
    duplicates = set(additions) & set(_catalog_by_type(retained_rows))
    if duplicates:
        raise ValueError(f"Duplicate {label.lower()} addition: {sorted(duplicates)}")
    return [*retained_rows, *deepcopy(add_rows)]


def load_frozen_non_dpf_catalog(
    *, fixture_path: Path = FROZEN_CATALOG_PATH
) -> list[dict[str, Any]]:
    payload = fixture_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest().upper()
    if digest != FROZEN_CATALOG_SHA256:
        raise ValueError(
            f"Frozen non-DPF catalog SHA256 changed: {digest}; "
            f"expected {FROZEN_CATALOG_SHA256}"
        )
    catalog = json.loads(payload)
    _catalog_by_type(catalog)
    return catalog


def load_effective_non_dpf_catalog(
    *,
    fixture_path: Path = FROZEN_CATALOG_PATH,
    overlay_path: Path = DOCUMENTATION_OVERLAY_PATH,
    structural_overlay_path: Path = STRUCTURAL_OVERLAY_PATH,
    current_contract_overlay_path: Path = CURRENT_CONTRACT_OVERLAY_PATH,
    solution_reuse_classification_path: Path = SOLUTION_REUSE_CLASSIFICATION_PATH,
) -> list[dict[str, Any]]:
    catalog = deepcopy(load_frozen_non_dpf_catalog(fixture_path=fixture_path))
    by_type = _catalog_by_type(catalog)
    overlay = json.loads(
        overlay_path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    overlay = _exact_keys(
        overlay,
        {
            "schema_version",
            "frozen_sha256",
            "keyword_patches",
            "port_description_patches",
            "python_script_default_source",
        },
        label="Documentation overlay",
    )
    if overlay["schema_version"] != 1:
        raise ValueError("Documentation overlay schema_version must be 1")
    if overlay["frozen_sha256"] != FROZEN_CATALOG_SHA256:
        raise ValueError("Documentation overlay targets the wrong frozen catalog")

    keyword_patches = overlay["keyword_patches"]
    if type(keyword_patches) is not dict:
        raise ValueError("keyword_patches must be an object")
    for type_id, keywords in keyword_patches.items():
        if type_id not in by_type:
            raise ValueError(f"Unknown keyword patch target: {type_id}")
        if (
            type(keywords) is not list
            or not keywords
            or any(type(keyword) is not str or not keyword for keyword in keywords)
        ):
            raise ValueError(f"Invalid keyword patch for {type_id}")
        spec = by_type[type_id]["spec"]
        if spec["keywords"] != []:
            raise ValueError(f"Keyword patch target is not empty: {type_id}")
        spec["keywords"] = keywords

    port_patches = overlay["port_description_patches"]
    if type(port_patches) is not dict:
        raise ValueError("port_description_patches must be an object")
    for type_id, descriptions in port_patches.items():
        if type_id not in by_type:
            raise ValueError(f"Unknown port patch target: {type_id}")
        if type(descriptions) is not dict:
            raise ValueError(f"Port patches for {type_id} must be an object")
        row = by_type[type_id]
        for port_key, description in descriptions.items():
            if type(description) is not str or not description.strip():
                raise ValueError(f"Invalid port description patch: {type_id}.{port_key}")
            matched = False
            for ports in (row["spec"]["ports"], row["resolved_default_ports"]):
                for port in ports:
                    if port["key"] != port_key:
                        continue
                    if port["description"] != "":
                        raise ValueError(
                            f"Port description patch target is not empty: "
                            f"{type_id}.{port_key}"
                        )
                    port["description"] = description
                    matched = True
            if not matched:
                raise ValueError(f"Unknown port patch target: {type_id}.{port_key}")

    source_patch = _exact_keys(
        overlay["python_script_default_source"],
        {"type_id", "property_key", "value"},
        label="python_script_default_source",
    )
    type_id = source_patch["type_id"]
    property_key = source_patch["property_key"]
    if (type_id, property_key) != ("core.python_script", "script"):
        raise ValueError(
            "python_script_default_source may only target core.python_script.script"
        )
    if type_id not in by_type:
        raise ValueError(f"Unknown default-source patch target: {type_id}")
    properties = by_type[type_id]["spec"]["properties"]
    matching = [item for item in properties if item["key"] == property_key]
    if len(matching) != 1 or type(source_patch["value"]) is not str:
        raise ValueError(f"Unknown default-source patch target: {type_id}.{property_key}")
    matching[0]["default"] = source_patch["value"]

    structural = json.loads(
        structural_overlay_path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    structural = _exact_keys(
        structural,
        {"schema_version", "frozen_sha256", "remove_type_ids", "add_rows"},
        label="Structural overlay",
    )
    if structural["schema_version"] != 1:
        raise ValueError("Structural overlay schema_version must be 1")
    if structural["frozen_sha256"] != FROZEN_CATALOG_SHA256:
        raise ValueError("Structural overlay targets the wrong frozen catalog")
    catalog = _replace_catalog_rows(
        catalog,
        remove_type_ids=structural["remove_type_ids"],
        add_rows=structural["add_rows"],
        label="Structural overlay",
    )

    current_contract = json.loads(
        current_contract_overlay_path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    current_contract = _exact_keys(
        current_contract,
        {
            "schema_version",
            "frozen_sha256",
            "remove_type_ids",
            "add_rows",
            "model_viewer_patch",
            "dynamic_scene_ports",
            "property_default_patches",
            "port_contract_patches",
        },
        label="Current contract overlay",
    )
    if type(current_contract["schema_version"]) is not int or current_contract["schema_version"] != 1:
        raise ValueError("Current contract overlay schema_version must be 1")
    if current_contract["frozen_sha256"] != FROZEN_CATALOG_SHA256:
        raise ValueError("Current contract overlay targets the wrong frozen catalog")
    catalog = _replace_catalog_rows(
        catalog,
        remove_type_ids=current_contract["remove_type_ids"],
        add_rows=current_contract["add_rows"],
        label="Current contract overlay",
    )
    current_by_type = _catalog_by_type(catalog)
    port_contract_patches = current_contract["port_contract_patches"]
    if type(port_contract_patches) is not dict:
        raise ValueError("port_contract_patches must be an object")
    for type_id, port_patches in port_contract_patches.items():
        if type_id not in current_by_type or type(port_patches) is not dict:
            raise ValueError(f"Unknown or invalid port contract target: {type_id}")
        for port_key, raw_patch in port_patches.items():
            patch = _exact_keys(
                raw_patch,
                {
                    "expected_data_type",
                    "replacement_data_type",
                    "expected_accepted_data_types",
                    "replacement_accepted_data_types",
                },
                label=f"{type_id}.{port_key} port contract patch",
            )
            replacement_type = patch["replacement_data_type"]
            replacement_accepted = patch["replacement_accepted_data_types"]
            if (
                type(replacement_type) is not str
                or not replacement_type
                or replacement_type != replacement_type.strip()
                or type(replacement_accepted) is not list
                or any(type(item) is not str or not item for item in replacement_accepted)
                or len(replacement_accepted) != len(set(replacement_accepted))
                or replacement_type in replacement_accepted
            ):
                raise ValueError(f"Invalid port contract replacement: {type_id}.{port_key}")
            row = current_by_type[type_id]
            for ports in (row["spec"]["ports"], row["resolved_default_ports"]):
                matching_ports = [port for port in ports if port["key"] == port_key]
                if len(matching_ports) != 1:
                    raise ValueError(f"Unknown port contract target: {type_id}.{port_key}")
                port = matching_ports[0]
                if (
                    port["data_type"] != patch["expected_data_type"]
                    or port["accepted_data_types"] != patch["expected_accepted_data_types"]
                ):
                    raise ValueError(f"Port contract patch drifted: {type_id}.{port_key}")
                port["data_type"] = replacement_type
                port["accepted_data_types"] = list(replacement_accepted)
    viewer_patch = _exact_keys(
        current_contract["model_viewer_patch"],
        {
            "expected_description",
            "replacement_description",
            "expected_scene_description",
            "replacement_scene_description",
            "expected_scene_accepted_data_types",
            "replacement_scene_accepted_data_types",
        },
        label="model_viewer_patch",
    )
    viewer = current_by_type["model.viewer"]
    if viewer["spec"]["description"] != viewer_patch["expected_description"]:
        raise ValueError("Model Viewer description patch drifted")
    viewer["spec"]["description"] = viewer_patch["replacement_description"]
    for ports in (viewer["spec"]["ports"], viewer["resolved_default_ports"]):
        scene_ports = [port for port in ports if port["key"] == "scene"]
        if len(scene_ports) != 1:
            raise ValueError("Model Viewer scene port patch target is missing")
        scene = scene_ports[0]
        if (
            scene["description"] != viewer_patch["expected_scene_description"]
            or scene["accepted_data_types"]
            != viewer_patch["expected_scene_accepted_data_types"]
        ):
            raise ValueError("Model Viewer scene port patch drifted")
        scene["description"] = viewer_patch["replacement_scene_description"]
        scene["accepted_data_types"] = viewer_patch[
            "replacement_scene_accepted_data_types"
        ]
    dynamic_scene_ports = _exact_keys(
        current_contract["dynamic_scene_ports"],
        {"properties", "group", "input_port"},
        label="dynamic_scene_ports",
    )
    viewer["spec"]["ports"] = [port for port in viewer["spec"]["ports"] if port["direction"] == "out"]
    viewer["resolved_default_ports"] = [*deepcopy(viewer["spec"]["ports"]), deepcopy(dynamic_scene_ports["input_port"])]
    viewer["spec"]["dynamic_port_groups"] = [deepcopy(dynamic_scene_ports["group"])]
    viewer_properties = viewer["spec"]["properties"]
    style_index = next(index for index, prop in enumerate(viewer_properties) if prop["key"] == "primary_opacity")
    viewer_properties[style_index:style_index + 2] = deepcopy(dynamic_scene_ports["properties"])
    viewer["spec"]["properties"] = [prop for prop in viewer_properties if prop["key"] != "overlay_color"]
    patches = _exact_keys(
        current_contract["property_default_patches"],
        {"model.viewer"},
        label="property_default_patches",
    )
    properties = _exact_keys(
        patches["model.viewer"],
        {"representation"},
        label="model.viewer property patches",
    )
    patch = _exact_keys(
        properties["representation"],
        {"expected_default", "replacement_default"},
        label="model.viewer.representation patch",
    )
    try:
        property_rows = current_by_type["model.viewer"]["spec"]["properties"]
    except KeyError as exc:
        raise ValueError("Unknown current-contract patch target: model.viewer") from exc
    matching = [item for item in property_rows if item.get("key") == "representation"]
    if len(matching) != 1:
        raise ValueError("Unknown current-contract patch target: model.viewer.representation")
    property_row = matching[0]
    if property_row.get("default") != patch["expected_default"]:
        raise ValueError("Current-contract patch expected default drifted")
    replacement = patch["replacement_default"]
    enum_values = property_row.get("enum_values")
    if type(replacement) is not str or type(enum_values) is not list or replacement not in enum_values:
        raise ValueError("Current-contract patch replacement is outside the property enum")
    property_row["default"] = replacement

    reuse_scopes = load_solution_reuse_scopes(solution_reuse_classification_path)
    for type_id, row in _catalog_by_type(catalog).items():
        try:
            scope = reuse_scopes[type_id]
        except KeyError as exc:
            raise ValueError(
                f"Missing solution reuse classification for {type_id}"
            ) from exc
        spec = row["spec"]
        if "solution_reuse_scope" in spec:
            raise ValueError(
                f"Solution reuse classification already applied for {type_id}"
            )
        spec["solution_reuse_scope"] = scope
        if type_id == "tabular.input":
            # Source selection stays in the inspector and surface toolbar.
            next(prop for prop in spec["properties"] if prop["key"] == "path")["inline_editor"] = ""
        spec["solution_provenance_inputs"] = (
            [
                {
                    "property_key": "path",
                    "kind": "file",
                    "policy_revision": 1,
                }
            ]
            if type_id
            in {
                "engineering.cad_import",
                "engineering.fe_import",
                "io.file_read",
                "io.image_import",
                "io.excel_read",
                "tabular.input",
            }
            else []
        )
    return sorted(catalog, key=lambda row: row["spec"]["type_id"])


def load_solution_reuse_scopes(
    path: Path = SOLUTION_REUSE_CLASSIFICATION_PATH,
) -> dict[str, str]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest().upper()
    if digest != SOLUTION_REUSE_CLASSIFICATION_SHA256:
        raise ValueError(
            f"Solution reuse classification SHA256 changed: {digest}; "
            f"expected {SOLUTION_REUSE_CLASSIFICATION_SHA256}"
        )
    section = ""
    scopes: dict[str, str] = {}
    for line in payload.decode("utf-8").splitlines():
        if line == "## Executable Row Inventory":
            section = "executable"
            continue
        if line == "## Excluded Row Inventory":
            section = "excluded"
            continue
        if line.startswith("## "):
            section = ""
            continue
        if not section or not line.startswith("| `"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        expected_columns = 14 if section == "executable" else 7
        if len(cells) != expected_columns:
            raise ValueError("Solution reuse classification row is malformed")
        type_id = cells[0]
        scope = cells[6] if section == "executable" else "never"
        if type_id in scopes or scope not in {"never", "session", "durable"}:
            raise ValueError(
                f"Invalid solution reuse classification for {type_id}"
            )
        scopes[type_id] = scope
    return scopes


__all__ = [
    "CURRENT_CONTRACT_OVERLAY_PATH",
    "DOCUMENTATION_OVERLAY_PATH",
    "FROZEN_CATALOG_PATH",
    "FROZEN_CATALOG_SHA256",
    "STRUCTURAL_OVERLAY_PATH",
    "SOLUTION_REUSE_CLASSIFICATION_PATH",
    "SOLUTION_REUSE_CLASSIFICATION_SHA256",
    "load_effective_non_dpf_catalog",
    "load_frozen_non_dpf_catalog",
    "load_solution_reuse_scopes",
]
