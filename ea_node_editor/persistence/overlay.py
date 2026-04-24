from __future__ import annotations

import copy
import importlib
import re
import weakref
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID, registered_addon_registrations
from ea_node_editor.nodes.plugin_loader import discover_addon_records

PERSISTENCE_ENVELOPE_KEY = "_persistence_envelope"
LEGACY_RUNTIME_PERSISTENCE_KEY = "_runtime_unresolved_workspaces"
MISSING_ADDON_PLACEHOLDER_KEY = "_missing_addon_placeholder"
_WORKSPACE_PERSISTENCE_ENVELOPE_KEYS = frozenset(
    {
        "unresolved_nodes",
        "unresolved_edges",
        "authored_node_overrides",
    }
)
_LEGACY_WORKSPACE_PERSISTENCE_ENVELOPE_KEYS = frozenset(
    {
        "nodes",
        "edges",
        "node_overrides",
    }
)
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


def _copy_overlay_docs(value: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    copied: dict[str, dict[str, Any]] = {}
    for raw_key, raw_doc in value.items():
        key = str(raw_key).strip()
        if not key or not isinstance(raw_doc, Mapping):
            continue
        copied[key] = copy.deepcopy(dict(raw_doc))
    return copied


def _copy_unresolved_node_docs(value: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    copied: dict[str, dict[str, Any]] = {}
    for raw_key, raw_doc in value.items():
        key = str(raw_key).strip()
        if not key or not isinstance(raw_doc, Mapping):
            continue
        copied[key] = with_missing_addon_placeholder(raw_doc)
    return copied


def _copy_overlay_doc_sequence(value: Any, *, id_key: str, field_name: str) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a JSON array.")
    copied: dict[str, dict[str, Any]] = {}
    for raw_doc in value:
        if not isinstance(raw_doc, Mapping):
            raise ValueError(f"{field_name} entries must be JSON objects.")
        copied_doc = copy.deepcopy(dict(raw_doc))
        entry_id = str(copied_doc.get(id_key, "")).strip()
        if not entry_id:
            raise ValueError(f"{field_name} entries must include {id_key!r}.")
        if entry_id in copied:
            raise ValueError(f"{field_name} contains duplicate {id_key!r}: {entry_id}.")
        copied_doc[id_key] = entry_id
        copied[entry_id] = copied_doc
    return copied


@dataclass(slots=True)
class WorkspacePersistenceState:
    unresolved_node_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    unresolved_edge_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    authored_node_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    def clone(self) -> "WorkspacePersistenceState":
        return WorkspacePersistenceState(
            unresolved_node_docs=_copy_unresolved_node_docs(self.unresolved_node_docs),
            unresolved_edge_docs=_copy_overlay_docs(self.unresolved_edge_docs),
            authored_node_overrides=_copy_overlay_docs(self.authored_node_overrides),
        )

    @classmethod
    def capture(cls, owner: object) -> "WorkspacePersistenceState":
        return capture_workspace_persistence_state(owner)

    def restore(self, owner: object) -> None:
        restore_workspace_persistence_state(owner, self)

    def replace_unresolved_node_docs(self, value: Mapping[str, Any] | None) -> None:
        self.unresolved_node_docs = _copy_unresolved_node_docs(value)

    def replace_unresolved_edge_docs(self, value: Mapping[str, Any] | None) -> None:
        self.unresolved_edge_docs = _copy_overlay_docs(value)

    def replace_authored_node_overrides(self, value: Mapping[str, Any] | None) -> None:
        self.authored_node_overrides = _copy_overlay_docs(value)

    def remove_node_references(self, node_id: str) -> None:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return
        self.unresolved_node_docs.pop(normalized_node_id, None)
        self.authored_node_overrides.pop(normalized_node_id, None)
        for edge_id, edge_doc in list(self.unresolved_edge_docs.items()):
            if (
                str(edge_doc.get("source_node_id", "")).strip() == normalized_node_id
                or str(edge_doc.get("target_node_id", "")).strip() == normalized_node_id
            ):
                del self.unresolved_edge_docs[edge_id]
        for child_node_id, override in list(self.authored_node_overrides.items()):
            if str(override.get("parent_node_id", "")).strip() == normalized_node_id:
                del self.authored_node_overrides[child_node_id]


@dataclass(slots=True, frozen=True)
class WorkspacePersistenceEnvelope:
    unresolved_node_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    unresolved_edge_docs: dict[str, dict[str, Any]] = field(default_factory=dict)
    authored_node_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (
            self.unresolved_node_docs
            or self.unresolved_edge_docs
            or self.authored_node_overrides
        )

    @classmethod
    def from_state(cls, state: WorkspacePersistenceState) -> "WorkspacePersistenceEnvelope":
        return cls(
            unresolved_node_docs=_copy_unresolved_node_docs(state.unresolved_node_docs),
            unresolved_edge_docs=_copy_overlay_docs(state.unresolved_edge_docs),
            authored_node_overrides=_copy_overlay_docs(state.authored_node_overrides),
        )

    @classmethod
    def capture(cls, owner: object) -> "WorkspacePersistenceEnvelope":
        return cls.from_state(capture_workspace_persistence_state(owner))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "WorkspacePersistenceEnvelope":
        if not isinstance(value, Mapping):
            return cls()
        keys = {str(key) for key in value}
        legacy_keys = sorted(keys & _LEGACY_WORKSPACE_PERSISTENCE_ENVELOPE_KEYS)
        if legacy_keys:
            raise ValueError(
                "Workspace persistence envelope uses legacy keys: "
                f"{', '.join(legacy_keys)}. Use unresolved_nodes, "
                "unresolved_edges, and authored_node_overrides."
            )
        unsupported_keys = sorted(keys - _WORKSPACE_PERSISTENCE_ENVELOPE_KEYS)
        if unsupported_keys:
            raise ValueError(
                "Workspace persistence envelope contains unsupported keys: "
                f"{', '.join(unsupported_keys)}."
            )
        authored_node_overrides = value.get("authored_node_overrides")
        if authored_node_overrides is not None and not isinstance(authored_node_overrides, Mapping):
            raise ValueError("authored_node_overrides must be a JSON object.")
        return cls(
            unresolved_node_docs=_copy_unresolved_node_docs(
                _copy_overlay_doc_sequence(
                    value.get("unresolved_nodes"),
                    id_key="node_id",
                    field_name="unresolved_nodes",
                )
            ),
            unresolved_edge_docs=_copy_overlay_doc_sequence(
                value.get("unresolved_edges"),
                id_key="edge_id",
                field_name="unresolved_edges",
            ),
            authored_node_overrides=_copy_overlay_docs(authored_node_overrides),
        )

    def to_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.unresolved_node_docs:
            payload["unresolved_nodes"] = [
                copy.deepcopy(self.unresolved_node_docs[node_id])
                for node_id in sorted(self.unresolved_node_docs)
            ]
        if self.unresolved_edge_docs:
            payload["unresolved_edges"] = [
                copy.deepcopy(self.unresolved_edge_docs[edge_id])
                for edge_id in sorted(self.unresolved_edge_docs)
            ]
        if self.authored_node_overrides:
            payload["authored_node_overrides"] = {
                node_id: copy.deepcopy(self.authored_node_overrides[node_id])
                for node_id in sorted(self.authored_node_overrides)
                if self.authored_node_overrides[node_id]
            }
        return payload

    def to_state(self) -> WorkspacePersistenceState:
        state = WorkspacePersistenceState()
        self.apply_to(state)
        return state

    def apply_to(self, state: WorkspacePersistenceState) -> None:
        state.replace_unresolved_node_docs(self.unresolved_node_docs)
        state.replace_unresolved_edge_docs(self.unresolved_edge_docs)
        state.replace_authored_node_overrides(self.authored_node_overrides)


_PERSISTENCE_STATE_BY_OWNER: dict[int, tuple[weakref.ReferenceType[Any], WorkspacePersistenceState]] = {}


def _persistence_state_entry(owner: object) -> tuple[weakref.ReferenceType[Any], WorkspacePersistenceState] | None:
    owner_id = id(owner)
    entry = _PERSISTENCE_STATE_BY_OWNER.get(owner_id)
    if entry is None:
        return None
    owner_ref, state = entry
    if owner_ref() is owner:
        return owner_ref, state
    _PERSISTENCE_STATE_BY_OWNER.pop(owner_id, None)
    return None


def _owner_ref(owner: object) -> weakref.ReferenceType[Any]:
    owner_id = id(owner)

    def _cleanup(owner_ref: weakref.ReferenceType[Any]) -> None:
        entry = _PERSISTENCE_STATE_BY_OWNER.get(owner_id)
        if entry is not None and entry[0] is owner_ref:
            _PERSISTENCE_STATE_BY_OWNER.pop(owner_id, None)

    return weakref.ref(owner, _cleanup)


def workspace_has_persistence_overlay(owner: object) -> bool:
    return _persistence_state_entry(owner) is not None


def capture_workspace_persistence_state(owner: object) -> WorkspacePersistenceState:
    entry = _persistence_state_entry(owner)
    if entry is None:
        return WorkspacePersistenceState()
    return entry[1].clone()


def restore_workspace_persistence_state(
    owner: object,
    state: WorkspacePersistenceState,
) -> WorkspacePersistenceState:
    restored = state.clone()
    _PERSISTENCE_STATE_BY_OWNER[id(owner)] = (_owner_ref(owner), restored)
    return restored


def workspace_persistence_overlay(owner: object) -> WorkspacePersistenceState:
    entry = _persistence_state_entry(owner)
    if entry is not None:
        return entry[1]
    return restore_workspace_persistence_state(owner, WorkspacePersistenceState())


def copy_workspace_persistence_overlay(
    source: object,
    target: object,
) -> WorkspacePersistenceState:
    return restore_workspace_persistence_state(target, capture_workspace_persistence_state(source))


def set_workspace_unresolved_node_docs(owner: object, value: Mapping[str, Any] | None) -> None:
    workspace_persistence_overlay(owner).replace_unresolved_node_docs(value)


def set_workspace_unresolved_edge_docs(owner: object, value: Mapping[str, Any] | None) -> None:
    workspace_persistence_overlay(owner).replace_unresolved_edge_docs(value)


def set_workspace_authored_node_overrides(
    owner: object,
    value: Mapping[str, Any] | None,
) -> None:
    workspace_persistence_overlay(owner).replace_authored_node_overrides(value)
