from __future__ import annotations

import copy
import importlib
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID, registered_addon_registrations
from ea_node_editor.nodes.plugin_loader import discover_addon_records
from ea_node_editor.persistence.envelope import (
    LEGACY_RUNTIME_PERSISTENCE_KEY,
    PERSISTENCE_ENVELOPE_KEY,
)

MISSING_ADDON_PLACEHOLDER_KEY = "_missing_addon_placeholder"
_LOCKED_PLACEHOLDER_LABEL = "Requires add-on"
_DPF_OPERATOR_TYPE_ID_PREFIX = "dpf.op"
_TYPE_ID_TOKEN_SANITIZE_RE = re.compile(r"[^0-9a-zA-Z_]+")


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _locked_reason_for_status(status: str) -> str:
    if status == "disabled":
        return "addon_disabled"
    if status == "pending_restart":
        return "addon_pending_restart"
    return "missing_addon"


def _default_unavailable_reason(
    *,
    display_name: str,
    status: str,
    dependencies: tuple[str, ...],
    summary: str,
    is_available: bool,
) -> str:
    if status == "disabled":
        return f"{display_name} is disabled."
    if status == "pending_restart":
        return f"{display_name} has pending restart changes."
    if is_available:
        return f"{display_name} is not loaded in this session."
    if summary:
        return summary
    if dependencies:
        return ", ".join(dependencies)
    return f"{display_name} is unavailable."


def _normalized_type_id_candidates(values: Sequence[Any]) -> tuple[str, ...]:
    ordered: list[str] = []
    for value in values:
        normalized = _normalized_text(value)
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return tuple(ordered)


def _type_ids_from_descriptor_sequence(values: Any) -> tuple[str, ...]:
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
        candidates = []
        for value in values:
            spec = getattr(value, "spec", None)
            type_id = _normalized_text(getattr(spec, "type_id", ""))
            if type_id:
                candidates.append(type_id)
        return _normalized_type_id_candidates(candidates)
    return ()


def _type_ids_from_loader(candidate: Any) -> tuple[str, ...]:
    if not callable(candidate):
        return ()
    try:
        return _type_ids_from_descriptor_sequence(candidate())
    except Exception:  # noqa: BLE001
        return ()


def _type_ids_from_module_constants(module: Any) -> tuple[str, ...]:
    candidates: list[str] = []
    for name in dir(module):
        if not name.endswith(("TYPE_ID", "TYPE_IDS", "_NODE_TYPE_ID", "_NODE_TYPE_IDS")):
            continue
        value = getattr(module, name, None)
        if isinstance(value, str):
            candidates.append(value)
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            candidates.extend(str(item) for item in value)
    return _normalized_type_id_candidates(candidates)


def _type_ids_from_backend_module(module: Any, *, backend_collection_attr: str) -> tuple[str, ...]:
    candidates: list[str] = []
    raw_backends = getattr(module, backend_collection_attr, ())
    if isinstance(raw_backends, Sequence) and not isinstance(raw_backends, (str, bytes, bytearray)):
        for backend in raw_backends:
            candidates.extend(_type_ids_from_loader(getattr(backend, "load_descriptors", None)))
    for name in dir(module):
        if not name.startswith("load_") or not name.endswith(("_descriptors", "_definitions")):
            continue
        candidates.extend(_type_ids_from_loader(getattr(module, name, None)))
    candidates.extend(_type_ids_from_module_constants(module))
    return _normalized_type_id_candidates(candidates)


def _sanitize_type_id_token(value: Any) -> str:
    token = _TYPE_ID_TOKEN_SANITIZE_RE.sub("_", str(value or "").strip().lower())
    token = re.sub(r"_+", "_", token).strip("_")
    return token


@lru_cache(maxsize=1)
def _dpf_doc_operator_type_ids() -> tuple[str, ...]:
    docs_root = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "dpf_operator_docs"
        / "operator-specifications"
    )
    if not docs_root.is_dir():
        return ()
    candidates: list[str] = []
    for markdown_path in sorted(docs_root.rglob("*.md")):
        if markdown_path.name == "operator-specifications.md" or markdown_path.stem.endswith("_category"):
            continue
        relative_path = markdown_path.relative_to(docs_root)
        if len(relative_path.parts) < 2:
            continue
        family = _sanitize_type_id_token(relative_path.parts[0])
        module_name = _sanitize_type_id_token(markdown_path.stem)
        if not family or not module_name:
            continue
        candidates.append(f"{_DPF_OPERATOR_TYPE_ID_PREFIX}.{family}.{module_name}")
    return _normalized_type_id_candidates(candidates)


@lru_cache(maxsize=1)
def _dpf_static_type_ids() -> tuple[str, ...]:
    try:
        from ea_node_editor.nodes.builtins import ansys_dpf_common
    except Exception:  # noqa: BLE001
        return ()
    return _type_ids_from_module_constants(ansys_dpf_common)


def _addon_specific_fallback_type_ids(addon_id: str) -> tuple[str, ...]:
    if addon_id == ANSYS_DPF_ADDON_ID:
        return _normalized_type_id_candidates(
            [*_dpf_static_type_ids(), *_dpf_doc_operator_type_ids()]
        )
    return ()


@lru_cache(maxsize=1)
def _registered_addon_registrations_by_id() -> dict[str, Any]:
    return {
        registration.manifest.addon_id: registration
        for registration in registered_addon_registrations()
    }


@lru_cache(maxsize=None)
def _fallback_type_ids_for_addon(addon_id: str) -> tuple[str, ...]:
    registration = _registered_addon_registrations_by_id().get(addon_id)
    if registration is None:
        return ()
    candidates: list[str] = []
    try:
        module = importlib.import_module(registration.backend_module)
    except Exception:  # noqa: BLE001
        module = None
    if module is not None:
        candidates.extend(
            _type_ids_from_backend_module(
                module,
                backend_collection_attr=str(
                    getattr(registration, "backend_collection_attr", "") or "PLUGIN_BACKENDS"
                ),
            )
        )
    candidates.extend(_addon_specific_fallback_type_ids(addon_id))
    return _normalized_type_id_candidates(candidates)


def _addon_record_type_ids(record: Any) -> tuple[str, ...]:
    direct_type_ids = _normalized_type_id_candidates(getattr(record, "provided_node_type_ids", ()))
    if direct_type_ids:
        return direct_type_ids
    addon_id = _normalized_text(getattr(record, "addon_id", ""))
    if not addon_id:
        return ()
    return _fallback_type_ids_for_addon(addon_id)


def _addon_record_by_type_id(type_id: Any) -> Any | None:
    normalized_type_id = _normalized_text(type_id)
    if not normalized_type_id:
        return None
    for record in discover_addon_records():
        if normalized_type_id in _addon_record_type_ids(record):
            return record
    return None


def normalize_missing_addon_placeholder(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    addon_id = _normalized_text(value.get("addon_id"))
    if not addon_id:
        return None
    display_name = _normalized_text(value.get("display_name")) or addon_id
    version = _normalized_text(value.get("version"))
    apply_policy = _normalized_text(value.get("apply_policy"))
    status = _normalized_text(value.get("status")) or "unavailable"
    unavailable_reason = _normalized_text(value.get("unavailable_reason"))
    raw_locked_state = value.get("locked_state")
    locked_state_mapping = raw_locked_state if isinstance(raw_locked_state, Mapping) else {}
    locked_reason = _normalized_text(locked_state_mapping.get("reason")) or _locked_reason_for_status(status)
    locked_label = _normalized_text(locked_state_mapping.get("label")) or _LOCKED_PLACEHOLDER_LABEL
    locked_summary = _normalized_text(locked_state_mapping.get("summary")) or unavailable_reason
    return {
        "addon_id": addon_id,
        "display_name": display_name,
        "version": version,
        "apply_policy": apply_policy,
        "status": status,
        "unavailable_reason": unavailable_reason,
        "locked_state": {
            "is_locked": bool(locked_state_mapping.get("is_locked", True)),
            "reason": locked_reason,
            "label": locked_label,
            "summary": locked_summary,
            "focus_addon_id": addon_id,
        },
    }


def missing_addon_placeholder_payload(node_doc: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(node_doc, Mapping):
        return None
    return normalize_missing_addon_placeholder(node_doc.get(MISSING_ADDON_PLACEHOLDER_KEY))


def with_missing_addon_placeholder(
    node_doc: Mapping[str, Any],
    *,
    addon_record: Any | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(node_doc))
    existing = missing_addon_placeholder_payload(copied)
    if existing is not None:
        copied[MISSING_ADDON_PLACEHOLDER_KEY] = existing
        return copied
    record = addon_record or _addon_record_by_type_id(copied.get("type_id"))
    if record is None:
        return copied
    manifest = record.manifest
    dependencies = tuple(
        dependency
        for dependency in (_normalized_text(item) for item in manifest.dependencies)
        if dependency
    )
    unavailable_reason = _default_unavailable_reason(
        display_name=record.display_name,
        status=record.status,
        dependencies=dependencies,
        summary=_normalized_text(record.availability.summary),
        is_available=bool(record.availability.is_available),
    )
    copied[MISSING_ADDON_PLACEHOLDER_KEY] = normalize_missing_addon_placeholder(
        {
            "addon_id": record.addon_id,
            "display_name": record.display_name,
            "version": manifest.version,
            "apply_policy": record.apply_policy,
            "status": record.status,
            "unavailable_reason": unavailable_reason,
            "locked_state": {
                "reason": _locked_reason_for_status(record.status),
            },
        }
    )
    return copied
