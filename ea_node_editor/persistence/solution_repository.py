# Purpose: Persist immutable solution records and result blobs in project sidecars.
# Map: subsystems/persistence.md
# Tests: tests/test_solution_repository.py
# Landmarks: SolutionRepositoryFactory; SolutionRepository; build_candidate_generation

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any
import unicodedata
from uuid import uuid4

from ea_node_editor.execution.solution_store import (
    DurableBackendOpenResult,
    DurableLookupResult,
    DurablePayloadResult,
    DurableStageResult,
)
from ea_node_editor.persistence.artifact_store import (
    ProjectArtifactLayout,
    ensure_owned_artifact_directory,
    validate_owned_artifact_path,
)
from ea_node_editor.runtime_contracts.data_types import DataTypeCatalog
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.runtime_contracts.solution_records import (
    MAX_DURABLE_LOGICAL_ID_UTF8_BYTES,
    SolutionPayloadLocator,
    SolutionRecord,
    SolutionResidency,
)
from ea_node_editor.runtime_contracts.runtime_values import (
    RuntimeArtifactRef,
    durable_settled_outputs_from_payload,
    validate_durable_settled_outputs,
)

SCHEMA_VERSION = 1
MAX_DURABLE_JSON_DEPTH = 32
MAX_DURABLE_DIAGNOSTIC_UTF8_BYTES = 512
MAX_DURABLE_MANIFEST_SET_BYTES = 67_108_864
MAX_DURABLE_NODE_MANIFEST_BYTES = 1_048_576
MAX_DURABLE_RECORD_JSON_BYTES = 8_388_608
MAX_DURABLE_RESULT_BLOB_BYTES = 67_108_864
MAX_DURABLE_NODE_MANIFESTS_PER_GENERATION = 100_000
MAX_DURABLE_RECORDS_PER_NODE = 256
MAX_DURABLE_RECORDS_PER_GENERATION = 1_000_000
MAX_DURABLE_NODE_MANIFEST_BYTES_PER_GENERATION = 268_435_456
MAX_DURABLE_REFERENCED_BYTES_PER_GENERATION = 4_294_967_296

_HEX_32 = re.compile(r"[0-9a-f]{32}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_WORKSPACE_KEY_PREFIX = b"corex-solution-workspace-key-v1\0"
_NODE_KEY_PREFIX = b"corex-solution-node-key-v1\0"
_SOLUTION_ROOT = PurePosixPath("solutions", "v1")
_MANIFEST_FIELDS = frozenset(
    {"schema_version", "generation_id", "solution_namespace_id", "node_manifests"}
)
_MANIFEST_ENTRY_FIELDS = frozenset(
    {"workspace_key", "node_key", "relative_path", "node_manifest_digest"}
)
_NODE_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "solution_namespace_id",
        "workspace_id",
        "node_id",
        "workspace_key",
        "node_key",
        "records",
    }
)
_NODE_RECORD_FIELDS = frozenset({"solution_key", "record_digest"})
_RESULT_BLOB_FIELDS = frozenset(
    {"schema_version", "record_id", "solution_key", "result_digest", "settlement_status", "outputs"}
)
_METADATA_FIELDS = frozenset(
    {"schema_version", "solution_namespace_id", "active_generation_id", "active_manifest_set_digest"}
)
_GENERATION_REASONS = frozenset(
    {
        "durable_generation_built",
        "durable_generation_valid",
        "durable_generation_capacity_exceeded",
        "durable_generation_invalid",
        "durable_generation_digest_mismatch",
        "durable_generation_write_failed",
    }
)
_PRUNABLE_PATH_PATTERNS = (
    re.compile(r"generations/[0-9a-f]{32}/manifest-set\.json"),
    re.compile(
        r"generations/[0-9a-f]{32}/nodes/[0-9a-f]{64}/[0-9a-f]{64}\.json"
    ),
    re.compile(r"records/sha256/[0-9a-f]{2}/[0-9a-f]{64}\.json"),
    re.compile(r"blobs/sha256/[0-9a-f]{2}/[0-9a-f]{64}"),
)


class _RepositoryError(Exception):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True, slots=True)
class DurableGenerationResult:
    generation_id: str
    manifest_set_digest: str
    reason_code: str
    solution_namespace_id: str = ""

    def __post_init__(self) -> None:
        if self.reason_code not in _GENERATION_REASONS:
            raise ValueError("durable generation reason_code is invalid")
        succeeded = self.reason_code in {
            "durable_generation_built",
            "durable_generation_valid",
        }
        if succeeded:
            if (
                _HEX_32.fullmatch(self.generation_id or "") is None
                or _SHA256.fullmatch(self.manifest_set_digest or "") is None
            ):
                raise ValueError("successful durable generations require IDs")
            _logical_id(self.solution_namespace_id, "solution_namespace_id")
        elif self.generation_id or self.manifest_set_digest or self.solution_namespace_id:
            raise ValueError("failed durable generations cannot carry IDs")

    @property
    def metadata_solution_store(self) -> dict[str, Any]:
        if self.reason_code not in {"durable_generation_built", "durable_generation_valid"}:
            return {}
        return {
            "schema_version": SCHEMA_VERSION,
            "solution_namespace_id": self.solution_namespace_id,
            "active_generation_id": self.generation_id,
            "active_manifest_set_digest": self.manifest_set_digest,
        }


@dataclass(frozen=True, slots=True)
class _GenerationInspection:
    paths: frozenset[Path]
    manifest_set_digest: str


def workspace_path_key(workspace_id: str) -> str:
    return hashlib.sha256(
        _WORKSPACE_KEY_PREFIX + _logical_id(workspace_id, "workspace_id").encode("utf-8")
    ).hexdigest()


def node_path_key(node_id: str) -> str:
    return hashlib.sha256(
        _NODE_KEY_PREFIX + _logical_id(node_id, "node_id").encode("utf-8")
    ).hexdigest()


def _logical_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    normalized = value.strip()
    if len(normalized.encode("utf-8")) > MAX_DURABLE_LOGICAL_ID_UTF8_BYTES:
        raise ValueError(f"{field_name} exceeds the durable logical ID limit")
    if any(unicodedata.category(char) == "Cc" for char in normalized):
        raise ValueError(f"{field_name} contains control characters")
    return normalized


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _strict_json_bytes(raw: bytes, *, maximum: int) -> Mapping[str, Any]:
    if type(raw) is not bytes or len(raw) > maximum:
        raise ValueError("durable JSON exceeds its byte limit")

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError("durable JSON contains duplicate keys")
            result[key] = value
        return result

    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("durable JSON contains a non-finite number")
            ),
        )
        if not isinstance(payload, Mapping):
            raise ValueError("durable JSON root must be an object")
        _validate_json_depth(payload, 0)
        if _canonical_json_bytes(payload) != raw:
            raise ValueError("durable JSON bytes are not canonical")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        OverflowError,
        RecursionError,
        TypeError,
    ) as exc:
        raise ValueError("durable JSON is invalid") from exc
    return payload


def _validate_json_depth(value: Any, depth: int) -> None:
    if depth > MAX_DURABLE_JSON_DEPTH:
        raise ValueError("durable JSON exceeds the depth limit")
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("durable JSON object keys must be strings")
            _validate_json_depth(item, depth + 1)
    elif type(value) is list:
        for item in value:
            _validate_json_depth(item, depth + 1)
    elif value is not None and type(value) not in {str, bool, int, float}:
        raise ValueError("durable JSON contains an unsupported value")


def _exact_fields(payload: Mapping[str, Any], fields: frozenset[str]) -> None:
    if set(payload) != fields:
        raise ValueError("durable JSON fields are invalid")


def _identity(file_stat: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(file_stat.st_dev),
        int(file_stat.st_ino),
        int(file_stat.st_size),
        int(file_stat.st_mtime_ns),
        int(getattr(file_stat, "st_file_attributes", 0)),
    )


def _contains_reparse_component(root: Path, relative_path: str) -> bool:
    target = Path(os.path.abspath(os.path.join(root, *PurePosixPath(relative_path).parts)))
    current = Path(target.anchor)
    for part in target.parts[1:]:
        current /= part
        try:
            current_stat = os.lstat(current)
        except FileNotFoundError:
            return False
        if stat.S_ISLNK(current_stat.st_mode) or bool(
            getattr(current_stat, "st_file_attributes", 0) & 0x400
        ):
            return True
    return False


def _read_file(
    root: Path,
    relative_path: str,
    *,
    maximum: int,
    missing_reason: str,
    oversized_reason: str,
) -> bytes:
    try:
        path = validate_owned_artifact_path(root, relative_path)
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError
        if before.st_size > maximum:
            raise _RepositoryError(oversized_reason)
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if _identity(opened) != _identity(before):
                raise OSError
            raw = stream.read(maximum + 1)
            after_open = os.fstat(stream.fileno())
        after = os.lstat(path)
        validate_owned_artifact_path(root, relative_path)
        if len(raw) > maximum:
            raise _RepositoryError(oversized_reason)
        if _identity(before) != _identity(after_open) or _identity(before) != _identity(after):
            raise OSError
        return raw
    except FileNotFoundError:
        raise _RepositoryError(missing_reason) from None
    except _RepositoryError:
        raise
    except ValueError:
        reason = (
            "durable_reparse_rejected"
            if _contains_reparse_component(root, relative_path)
            else "durable_path_unsafe"
        )
        raise _RepositoryError(reason) from None
    except OSError:
        raise _RepositoryError("durable_io_error") from None


def _ensure_relative_parent(root: Path, relative_path: PurePosixPath) -> Path:
    current = root
    for part in relative_path.parent.parts:
        current = ensure_owned_artifact_directory(current / part)
    return current


def _publish_immutable(root: Path, relative_path: str, raw: bytes) -> bool:
    relative = PurePosixPath(relative_path)
    parent = _ensure_relative_parent(root, relative)
    target_relative = relative.as_posix()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        existing = _read_file(
            root,
            target_relative,
            maximum=max(len(raw), 1),
            missing_reason="missing",
            oversized_reason="oversized",
        )
    except _RepositoryError as exc:
        if exc.reason_code == "oversized":
            raise _RepositoryError("durable_nondeterminism_conflict") from None
        if exc.reason_code != "missing":
            raise
    else:
        if existing != raw or hashlib.sha256(existing).hexdigest() != digest:
            raise _RepositoryError("durable_nondeterminism_conflict")
        return False

    fd, temporary = tempfile.mkstemp(prefix=f".{relative.name}.", suffix=".tmp", dir=parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        validate_owned_artifact_path(parent, temporary_path.name)
        try:
            os.link(temporary_path, parent / relative.name)
        except FileExistsError:
            winner = _read_file(
                root,
                target_relative,
                maximum=max(len(raw), 1),
                missing_reason="durable_stage_write_failed",
                oversized_reason="durable_stage_write_failed",
            )
            if winner != raw or hashlib.sha256(winner).hexdigest() != digest:
                raise _RepositoryError("durable_nondeterminism_conflict")
            return False
        validate_owned_artifact_path(root, target_relative)
        installed = _read_file(
            root,
            target_relative,
            maximum=max(len(raw), 1),
            missing_reason="durable_stage_write_failed",
            oversized_reason="durable_stage_write_failed",
        )
        if installed != raw:
            raise _RepositoryError("durable_stage_write_failed")
        return True
    except _RepositoryError:
        raise
    except ValueError:
        reason = (
            "durable_reparse_rejected"
            if _contains_reparse_component(root, target_relative)
            else "durable_path_unsafe"
        )
        raise _RepositoryError(reason) from None
    except OSError:
        raise _RepositoryError("durable_stage_write_failed") from None
    finally:
        temporary_path.unlink(missing_ok=True)


def _result_blob_payload(record: SolutionRecord, outputs_payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record.record_id,
        "solution_key": record.solution_key,
        "result_digest": record.result_digest,
        "settlement_status": record.settlement_status,
        "outputs": dict(outputs_payload),
    }


class _TrustedStagedArtifactContext:
    """Accept structurally valid managed refs already verified by the execution gate."""

    @staticmethod
    def inspect_durable_artifact(value: object) -> str:
        if type(value) is not RuntimeArtifactRef or value.scope != "managed":
            raise ValueError("durable artifact is not managed")
        return "managed"


_TRUSTED_STAGED_ARTIFACT_CONTEXT = _TrustedStagedArtifactContext()


class SolutionRepositoryFactory:
    def open_backend(
        self,
        project_id: str,
        project_path: str,
        metadata_solution_store: object,
        catalog: DataTypeCatalog,
    ) -> DurableBackendOpenResult:
        normalized_project_id = _logical_id(project_id, "project_id")
        fallback_namespace = normalized_project_id
        if not str(project_path).strip():
            return DurableBackendOpenResult(
                None,
                fallback_namespace,
                "durable_session_only_metadata_absent",
                "Unsaved projects use session-only solution reuse.",
            )
        if metadata_solution_store is None:
            return DurableBackendOpenResult(
                None,
                fallback_namespace,
                "durable_session_only_metadata_absent",
                "No durable solution pointer is committed; results will be recomputed.",
            )
        try:
            metadata = self._metadata(metadata_solution_store)
        except _RepositoryError as exc:
            return DurableBackendOpenResult(
                None,
                fallback_namespace,
                exc.reason_code,
                "The durable solution pointer is invalid; results will be recomputed.",
            )
        namespace_id = metadata["solution_namespace_id"]
        try:
            repository = SolutionRepository(
                project_id=normalized_project_id,
                project_path=project_path,
                solution_namespace_id=namespace_id,
                active_generation_id=metadata["active_generation_id"],
                active_manifest_set_digest=metadata["active_manifest_set_digest"],
                catalog=catalog,
            )
        except _RepositoryError as exc:
            status_code = {
                "durable_path_unsafe": "durable_session_only_path_unsafe",
                "durable_reparse_rejected": "durable_session_only_reparse_rejected",
                "durable_io_error": "durable_session_only_io_error",
            }.get(exc.reason_code, exc.reason_code)
            return DurableBackendOpenResult(
                None,
                namespace_id,
                status_code,
                "Durable solution data is unavailable; results will be recomputed.",
            )
        except (OverflowError, RecursionError, TypeError, ValueError):
            return DurableBackendOpenResult(
                None,
                namespace_id,
                "durable_session_only_manifest_invalid",
                "Durable solution data is unavailable; results will be recomputed.",
            )
        return DurableBackendOpenResult(
            repository,
            namespace_id,
            "durable_bound_active",
        )

    @staticmethod
    def _metadata(value: object) -> dict[str, Any]:
        if not isinstance(value, Mapping) or set(value) != _METADATA_FIELDS:
            raise _RepositoryError("durable_session_only_metadata_invalid")
        schema = value.get("schema_version")
        if type(schema) is not int:
            raise _RepositoryError("durable_session_only_metadata_invalid")
        if schema != SCHEMA_VERSION:
            raise _RepositoryError("durable_session_only_schema_unsupported")
        try:
            namespace_id = _logical_id(value.get("solution_namespace_id"), "solution_namespace_id")
        except ValueError:
            raise _RepositoryError("durable_session_only_metadata_invalid") from None
        generation_id = value.get("active_generation_id")
        digest = value.get("active_manifest_set_digest")
        if not isinstance(generation_id, str) or _HEX_32.fullmatch(generation_id) is None:
            raise _RepositoryError("durable_session_only_pointer_invalid")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise _RepositoryError("durable_session_only_pointer_invalid")
        return {
            "schema_version": SCHEMA_VERSION,
            "solution_namespace_id": namespace_id,
            "active_generation_id": generation_id,
            "active_manifest_set_digest": digest,
        }


class SolutionRepository:
    def __init__(
        self,
        *,
        project_id: str,
        project_path: str | Path,
        solution_namespace_id: str,
        active_generation_id: str,
        active_manifest_set_digest: str,
        catalog: DataTypeCatalog,
    ) -> None:
        self.project_id = _logical_id(project_id, "project_id")
        self.solution_namespace_id = _logical_id(
            solution_namespace_id,
            "solution_namespace_id",
        )
        self._catalog = catalog
        self._layout = ProjectArtifactLayout.from_project_path(project_path)
        self._root = self._layout.sidecar_root / _SOLUTION_ROOT
        self._closed = False
        if _HEX_32.fullmatch(active_generation_id or "") is None:
            raise _RepositoryError("durable_session_only_pointer_invalid")
        if _SHA256.fullmatch(active_manifest_set_digest or "") is None:
            raise _RepositoryError("durable_session_only_pointer_invalid")
        self._active_generation_id = active_generation_id
        self._active_manifest_set_digest = active_manifest_set_digest
        self._staged_records: dict[tuple[str, str, str], SolutionRecord] = {}
        self._record_digests: dict[str, str] = {}
        raw = _read_file(
            self._root,
            f"generations/{active_generation_id}/manifest-set.json",
            maximum=MAX_DURABLE_MANIFEST_SET_BYTES,
            missing_reason="durable_session_only_manifest_missing",
            oversized_reason="durable_session_only_manifest_oversized",
        )
        if hashlib.sha256(raw).hexdigest() != active_manifest_set_digest:
            raise _RepositoryError("durable_session_only_manifest_digest_mismatch")
        try:
            manifest = self._manifest_set(raw)
        except ValueError:
            raise _RepositoryError("durable_session_only_manifest_invalid") from None
        if (
            manifest["generation_id"] != active_generation_id
            or manifest["solution_namespace_id"] != self.solution_namespace_id
        ):
            raise _RepositoryError("durable_session_only_manifest_invalid")
        self._manifest = manifest
        self._manifest_entries = {
            (entry["workspace_key"], entry["node_key"]): entry
            for entry in manifest["node_manifests"]
        }

    @classmethod
    def create_empty(
        cls,
        *,
        project_id: str,
        project_path: str | Path,
        solution_namespace_id: str,
        catalog: DataTypeCatalog,
    ) -> SolutionRepository:
        self = object.__new__(cls)
        self.project_id = _logical_id(project_id, "project_id")
        self.solution_namespace_id = _logical_id(solution_namespace_id, "solution_namespace_id")
        self._catalog = catalog
        self._layout = ProjectArtifactLayout.from_project_path(project_path)
        self._root = self._layout.sidecar_root / _SOLUTION_ROOT
        self._closed = False
        self._active_generation_id = ""
        self._active_manifest_set_digest = ""
        self._staged_records = {}
        self._record_digests = {}
        self._manifest = {
            "schema_version": SCHEMA_VERSION,
            "generation_id": "",
            "solution_namespace_id": self.solution_namespace_id,
            "node_manifests": [],
        }
        self._manifest_entries = {}
        return self

    def close(self) -> None:
        self._closed = True

    def _require_open(self) -> None:
        if self._closed:
            raise _RepositoryError("durable_not_bound")

    @staticmethod
    def _manifest_set(raw: bytes) -> dict[str, Any]:
        payload = dict(_strict_json_bytes(raw, maximum=MAX_DURABLE_MANIFEST_SET_BYTES))
        _exact_fields(payload, _MANIFEST_FIELDS)
        if type(payload["schema_version"]) is not int or payload["schema_version"] != SCHEMA_VERSION:
            raise ValueError
        if not isinstance(payload["generation_id"], str) or _HEX_32.fullmatch(payload["generation_id"]) is None:
            raise ValueError
        _logical_id(payload["solution_namespace_id"], "solution_namespace_id")
        entries = payload["node_manifests"]
        if type(entries) is not list or len(entries) > MAX_DURABLE_NODE_MANIFESTS_PER_GENERATION:
            raise ValueError
        normalized: list[dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError
            _exact_fields(entry, _MANIFEST_ENTRY_FIELDS)
            workspace_key = entry["workspace_key"]
            node_key = entry["node_key"]
            digest = entry["node_manifest_digest"]
            if any(not isinstance(item, str) or _SHA256.fullmatch(item) is None for item in (workspace_key, node_key, digest)):
                raise ValueError
            relative = f"nodes/{workspace_key}/{node_key}.json"
            if entry["relative_path"] != relative:
                raise ValueError
            normalized.append(dict(entry))
        if normalized != sorted(normalized, key=lambda item: (item["workspace_key"], item["node_key"])):
            raise ValueError
        if len({(item["workspace_key"], item["node_key"]) for item in normalized}) != len(normalized):
            raise ValueError
        payload["node_manifests"] = normalized
        return payload

    def _node_manifest(self, raw: bytes, workspace_id: str, node_id: str) -> dict[str, Any]:
        payload = dict(_strict_json_bytes(raw, maximum=MAX_DURABLE_NODE_MANIFEST_BYTES))
        _exact_fields(payload, _NODE_MANIFEST_FIELDS)
        if type(payload["schema_version"]) is not int or payload["schema_version"] != SCHEMA_VERSION:
            raise ValueError
        if payload["solution_namespace_id"] != self.solution_namespace_id:
            raise ValueError
        if payload["workspace_id"] != workspace_id or payload["node_id"] != node_id:
            raise ValueError
        if payload["workspace_key"] != workspace_path_key(workspace_id) or payload["node_key"] != node_path_key(node_id):
            raise ValueError
        records = payload["records"]
        if type(records) is not list or len(records) > MAX_DURABLE_RECORDS_PER_NODE:
            raise ValueError
        normalized: list[dict[str, str]] = []
        for item in records:
            if not isinstance(item, Mapping):
                raise ValueError
            _exact_fields(item, _NODE_RECORD_FIELDS)
            if any(not isinstance(item[key], str) or _SHA256.fullmatch(item[key]) is None for key in _NODE_RECORD_FIELDS):
                raise ValueError
            normalized.append(dict(item))
        if normalized != sorted(normalized, key=lambda item: item["solution_key"]):
            raise ValueError
        if len({item["solution_key"] for item in normalized}) != len(normalized):
            raise ValueError
        payload["records"] = normalized
        return payload

    def lookup_record(
        self,
        workspace_id: str,
        node_id: str,
        solution_key: str,
        catalog: DataTypeCatalog,
    ) -> DurableLookupResult:
        try:
            self._require_open()
            workspace_id = _logical_id(workspace_id, "workspace_id")
            node_id = _logical_id(node_id, "node_id")
            if not isinstance(solution_key, str) or _SHA256.fullmatch(solution_key) is None:
                raise _RepositoryError("durable_record_binding_mismatch")
            staged = self._staged_records.get((workspace_id, node_id, solution_key))
            if staged is not None:
                return DurableLookupResult(staged, "durable_hit")
            entry = self._manifest_entries.get((workspace_path_key(workspace_id), node_path_key(node_id)))
            if entry is None:
                return DurableLookupResult(None, "durable_key_absent")
            raw_manifest = _read_file(
                self._root / "generations" / self._active_generation_id,
                entry["relative_path"],
                maximum=MAX_DURABLE_NODE_MANIFEST_BYTES,
                missing_reason="durable_node_manifest_missing",
                oversized_reason="durable_node_manifest_oversized",
            )
            if hashlib.sha256(raw_manifest).hexdigest() != entry["node_manifest_digest"]:
                return DurableLookupResult(None, "durable_node_manifest_digest_mismatch")
            try:
                node_manifest = self._node_manifest(raw_manifest, workspace_id, node_id)
            except (OverflowError, RecursionError, ValueError):
                return DurableLookupResult(None, "durable_node_manifest_invalid")
            record_ref = next((item for item in node_manifest["records"] if item["solution_key"] == solution_key), None)
            if record_ref is None:
                return DurableLookupResult(None, "durable_key_absent")
            record_digest = record_ref["record_digest"]
            raw_record = _read_file(
                self._root,
                f"records/sha256/{record_digest[:2]}/{record_digest}.json",
                maximum=MAX_DURABLE_RECORD_JSON_BYTES,
                missing_reason="durable_record_missing",
                oversized_reason="durable_record_oversized",
            )
            if hashlib.sha256(raw_record).hexdigest() != record_digest:
                return DurableLookupResult(None, "durable_record_digest_mismatch")
            try:
                payload = _strict_json_bytes(raw_record, maximum=MAX_DURABLE_RECORD_JSON_BYTES)
                record = SolutionRecord.from_payload(payload, catalog=catalog)
                if _canonical_json_bytes(record.to_payload(catalog=catalog)) != raw_record:
                    raise ValueError
            except (OverflowError, RecursionError, TypeError, ValueError):
                return DurableLookupResult(None, "durable_record_invalid")
            if (
                record.project_id != self.project_id
                or record.workspace_id != workspace_id
                or record.node_id != node_id
                or record.solution_key != solution_key
                or record.residency is not SolutionResidency.DURABLE
                or not record.reuse_eligible
            ):
                return DurableLookupResult(None, "durable_record_binding_mismatch")
            self._record_digests[record.record_id] = record_digest
            return DurableLookupResult(record, "durable_hit")
        except _RepositoryError as exc:
            reason = exc.reason_code
            if reason == "durable_path_unsafe":
                reason = "durable_path_unsafe"
            return DurableLookupResult(None, reason)
        except (AttributeError, OverflowError, RecursionError, TypeError, ValueError):
            return DurableLookupResult(None, "durable_record_binding_mismatch")

    def load_payload(
        self,
        record: SolutionRecord,
        catalog: DataTypeCatalog,
    ) -> DurablePayloadResult:
        try:
            self._require_open()
            if record.residency is not SolutionResidency.DURABLE:
                return DurablePayloadResult(None, "durable_payload_binding_mismatch")
            if record.payload_locator is None:
                return DurablePayloadResult(
                    tuple(
                        (descriptor.port_key, SettledPortResult(status="empty"))
                        for descriptor in record.output_descriptors
                    ),
                    "durable_hit",
                )
            digest = record.payload_locator.reference_id
            raw = _read_file(
                self._root,
                f"blobs/sha256/{digest[:2]}/{digest}",
                maximum=MAX_DURABLE_RESULT_BLOB_BYTES,
                missing_reason="durable_payload_missing",
                oversized_reason="durable_payload_oversized",
            )
            if hashlib.sha256(raw).hexdigest() != digest:
                return DurablePayloadResult(None, "durable_payload_digest_mismatch")
            try:
                payload = dict(_strict_json_bytes(raw, maximum=MAX_DURABLE_RESULT_BLOB_BYTES))
                _exact_fields(payload, _RESULT_BLOB_FIELDS)
                if type(payload["schema_version"]) is not int or payload["schema_version"] != SCHEMA_VERSION:
                    raise ValueError
                if (
                    payload["record_id"] != record.record_id
                    or payload["solution_key"] != record.solution_key
                    or payload["result_digest"] != record.result_digest
                    or payload["settlement_status"] != record.settlement_status
                ):
                    return DurablePayloadResult(None, "durable_payload_binding_mismatch")
                outputs = durable_settled_outputs_from_payload(payload["outputs"])
                canonical_outputs = _canonical_json_bytes(payload["outputs"])
            except (KeyError, OverflowError, RecursionError, TypeError, ValueError):
                return DurablePayloadResult(None, "durable_payload_invalid")
            if hashlib.sha256(canonical_outputs).hexdigest() != record.result_digest:
                return DurablePayloadResult(None, "durable_payload_binding_mismatch")
            return DurablePayloadResult(tuple(sorted(outputs.items())), "durable_hit")
        except _RepositoryError as exc:
            return DurablePayloadResult(None, exc.reason_code)
        except (AttributeError, OverflowError, RecursionError, TypeError, ValueError):
            return DurablePayloadResult(None, "durable_payload_binding_mismatch")

    def stage_record(
        self,
        record: SolutionRecord,
        canonical_payload: bytes,
        catalog: DataTypeCatalog,
    ) -> DurableStageResult:
        try:
            self._require_open()
            if (
                not isinstance(record, SolutionRecord)
                or record.project_id != self.project_id
                or not record.reuse_eligible
            ):
                return DurableStageResult(None, "durable_stage_ineligible")
            if type(canonical_payload) is not bytes or len(canonical_payload) > MAX_DURABLE_RESULT_BLOB_BYTES:
                return DurableStageResult(None, "durable_stage_capacity_exceeded")
            try:
                outputs_payload = _strict_json_bytes(
                    canonical_payload,
                    maximum=MAX_DURABLE_RESULT_BLOB_BYTES,
                )
                outputs = durable_settled_outputs_from_payload(outputs_payload)
                canonical_payload = _canonical_json_bytes(outputs_payload)
            except (OverflowError, RecursionError, TypeError, ValueError):
                return DurableStageResult(None, "durable_stage_ineligible")
            durable_validation = validate_durable_settled_outputs(
                outputs,
                record.output_descriptors,
                catalog,
                _TRUSTED_STAGED_ARTIFACT_CONTEXT,
            )
            if not durable_validation.eligible:
                return DurableStageResult(None, "durable_stage_ineligible")
            if hashlib.sha256(canonical_payload).hexdigest() != record.result_digest:
                return DurableStageResult(None, "durable_stage_ineligible")
            existing = self.lookup_record(
                record.workspace_id,
                record.node_id,
                record.solution_key,
                catalog,
            )
            if existing.reason_code == "durable_hit" and existing.record is not None:
                if existing.record.result_digest == record.result_digest:
                    return DurableStageResult(existing.record, "durable_stage_existing_identical")
                return DurableStageResult(None, "durable_nondeterminism_conflict")
            if existing.reason_code not in {"durable_key_absent"}:
                return DurableStageResult(None, "durable_stage_write_failed")
            has_value = any(item.status == "value" for item in record.output_descriptors)
            if has_value:
                blob_without_locator = _canonical_json_bytes(_result_blob_payload(record, outputs_payload))
                blob_digest = hashlib.sha256(blob_without_locator).hexdigest()
                durable_record = replace(
                    record,
                    residency=SolutionResidency.DURABLE,
                    runtime_generation=None,
                    payload_locator=SolutionPayloadLocator(
                        kind=SolutionResidency.DURABLE,
                        reference_id=blob_digest,
                        blob_digests=(blob_digest,),
                    ),
                    reuse_eligible=True,
                    catalog=catalog,
                )
                blob_raw = _canonical_json_bytes(_result_blob_payload(durable_record, outputs_payload))
                if hashlib.sha256(blob_raw).hexdigest() != blob_digest:
                    return DurableStageResult(None, "durable_stage_ineligible")
                if len(blob_raw) > MAX_DURABLE_RESULT_BLOB_BYTES:
                    return DurableStageResult(None, "durable_stage_capacity_exceeded")
                _publish_immutable(
                    self._root,
                    f"blobs/sha256/{blob_digest[:2]}/{blob_digest}",
                    blob_raw,
                )
            else:
                durable_record = replace(
                    record,
                    residency=SolutionResidency.DURABLE,
                    runtime_generation=None,
                    payload_locator=None,
                    reuse_eligible=True,
                    catalog=catalog,
                )
            record_raw = _canonical_json_bytes(durable_record.to_payload(catalog=catalog))
            if len(record_raw) > MAX_DURABLE_RECORD_JSON_BYTES:
                return DurableStageResult(None, "durable_stage_capacity_exceeded")
            record_digest = hashlib.sha256(record_raw).hexdigest()
            published = _publish_immutable(
                self._root,
                f"records/sha256/{record_digest[:2]}/{record_digest}.json",
                record_raw,
            )
            self._record_digests[durable_record.record_id] = record_digest
            self._staged_records[
                (durable_record.workspace_id, durable_record.node_id, durable_record.solution_key)
            ] = durable_record
            return DurableStageResult(
                durable_record,
                "durable_stage_published" if published else "durable_stage_existing_identical",
            )
        except _RepositoryError as exc:
            if exc.reason_code == "durable_nondeterminism_conflict":
                return DurableStageResult(None, exc.reason_code)
            if exc.reason_code == "durable_path_unsafe":
                return DurableStageResult(None, "durable_stage_path_unsafe")
            if exc.reason_code == "durable_reparse_rejected":
                return DurableStageResult(None, "durable_stage_reparse_rejected")
            return DurableStageResult(None, "durable_stage_write_failed")
        except (OSError, OverflowError, RecursionError, TypeError, ValueError):
            return DurableStageResult(None, "durable_stage_ineligible")

    def build_candidate_generation(
        self,
        records: Sequence[SolutionRecord] | None = None,
        *,
        generation_id: str | None = None,
    ) -> DurableGenerationResult:
        try:
            self._require_open()
            selected = tuple(records) if records is not None else tuple(self._staged_records.values())
            if len(selected) > MAX_DURABLE_RECORDS_PER_GENERATION:
                return DurableGenerationResult("", "", "durable_generation_capacity_exceeded")
            generation = generation_id or uuid4().hex
            if _HEX_32.fullmatch(generation) is None:
                return DurableGenerationResult("", "", "durable_generation_invalid")
            grouped: dict[tuple[str, str], list[SolutionRecord]] = {}
            record_ids: set[str] = set()
            for record in selected:
                if (
                    not isinstance(record, SolutionRecord)
                    or record.residency is not SolutionResidency.DURABLE
                    or record.project_id != self.project_id
                ):
                    return DurableGenerationResult("", "", "durable_generation_invalid")
                if record.record_id in record_ids:
                    return DurableGenerationResult("", "", "durable_generation_invalid")
                record_ids.add(record.record_id)
                grouped.setdefault((record.workspace_id, record.node_id), []).append(record)
            if len(grouped) > MAX_DURABLE_NODE_MANIFESTS_PER_GENERATION:
                return DurableGenerationResult("", "", "durable_generation_capacity_exceeded")
            entries: list[dict[str, str]] = []
            node_publications: list[tuple[str, bytes]] = []
            path_bindings: set[tuple[str, str]] = set()
            manifest_bytes_total = 0
            referenced_bytes = 0
            for (workspace_id, node_id), node_records in sorted(grouped.items()):
                if len(node_records) > MAX_DURABLE_RECORDS_PER_NODE:
                    return DurableGenerationResult("", "", "durable_generation_capacity_exceeded")
                if len({record.solution_key for record in node_records}) != len(node_records):
                    return DurableGenerationResult("", "", "durable_generation_invalid")
                record_refs: list[dict[str, str]] = []
                for record in sorted(node_records, key=lambda item: item.solution_key):
                    digest = self._record_digests.get(record.record_id)
                    if digest is None:
                        return DurableGenerationResult("", "", "durable_generation_invalid")
                    record_refs.append({"solution_key": record.solution_key, "record_digest": digest})
                    raw_record = _read_file(
                        self._root,
                        f"records/sha256/{digest[:2]}/{digest}.json",
                        maximum=MAX_DURABLE_RECORD_JSON_BYTES,
                        missing_reason="durable_generation_invalid",
                        oversized_reason="durable_generation_capacity_exceeded",
                    )
                    if hashlib.sha256(raw_record).hexdigest() != digest:
                        return DurableGenerationResult("", "", "durable_generation_digest_mismatch")
                    try:
                        persisted = SolutionRecord.from_payload(
                            _strict_json_bytes(
                                raw_record,
                                maximum=MAX_DURABLE_RECORD_JSON_BYTES,
                            ),
                            catalog=self._catalog,
                        )
                    except (TypeError, ValueError):
                        return DurableGenerationResult("", "", "durable_generation_invalid")
                    if persisted != record:
                        return DurableGenerationResult("", "", "durable_generation_invalid")
                    referenced_bytes += len(raw_record)
                    if record.payload_locator is not None:
                        blob_digest = record.payload_locator.reference_id
                        blob_raw = _read_file(
                                self._root,
                                f"blobs/sha256/{blob_digest[:2]}/{blob_digest}",
                                maximum=MAX_DURABLE_RESULT_BLOB_BYTES,
                                missing_reason="durable_generation_invalid",
                                oversized_reason="durable_generation_capacity_exceeded",
                            )
                        if hashlib.sha256(blob_raw).hexdigest() != blob_digest:
                            return DurableGenerationResult("", "", "durable_generation_digest_mismatch")
                        loaded = self.load_payload(record, self._catalog)
                        if loaded.reason_code != "durable_hit":
                            return DurableGenerationResult("", "", "durable_generation_invalid")
                        referenced_bytes += len(blob_raw)
                workspace_key = workspace_path_key(workspace_id)
                node_key = node_path_key(node_id)
                if (workspace_key, node_key) in path_bindings:
                    return DurableGenerationResult("", "", "durable_generation_invalid")
                path_bindings.add((workspace_key, node_key))
                node_payload = {
                    "schema_version": SCHEMA_VERSION,
                    "solution_namespace_id": self.solution_namespace_id,
                    "workspace_id": workspace_id,
                    "node_id": node_id,
                    "workspace_key": workspace_key,
                    "node_key": node_key,
                    "records": record_refs,
                }
                node_raw = _canonical_json_bytes(node_payload)
                manifest_bytes_total += len(node_raw)
                if len(node_raw) > MAX_DURABLE_NODE_MANIFEST_BYTES:
                    return DurableGenerationResult("", "", "durable_generation_capacity_exceeded")
                node_digest = hashlib.sha256(node_raw).hexdigest()
                relative = f"nodes/{workspace_key}/{node_key}.json"
                node_publications.append((relative, node_raw))
                entries.append(
                    {
                        "workspace_key": workspace_key,
                        "node_key": node_key,
                        "relative_path": relative,
                        "node_manifest_digest": node_digest,
                    }
                )
            if (
                manifest_bytes_total > MAX_DURABLE_NODE_MANIFEST_BYTES_PER_GENERATION
                or referenced_bytes > MAX_DURABLE_REFERENCED_BYTES_PER_GENERATION
            ):
                return DurableGenerationResult("", "", "durable_generation_capacity_exceeded")
            entries.sort(key=lambda item: (item["workspace_key"], item["node_key"]))
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "generation_id": generation,
                "solution_namespace_id": self.solution_namespace_id,
                "node_manifests": entries,
            }
            raw = _canonical_json_bytes(manifest)
            if len(raw) > MAX_DURABLE_MANIFEST_SET_BYTES:
                return DurableGenerationResult("", "", "durable_generation_capacity_exceeded")
            digest = hashlib.sha256(raw).hexdigest()
            for relative, node_raw in sorted(node_publications):
                _publish_immutable(
                    self._root / "generations" / generation,
                    relative,
                    node_raw,
                )
            _publish_immutable(
                self._root,
                f"generations/{generation}/manifest-set.json",
                raw,
            )
            inspection = self._inspect_generation(
                generation,
                expected_manifest_set_digest=digest,
            )
            if inspection.manifest_set_digest != digest:
                return DurableGenerationResult(
                    "",
                    "",
                    "durable_generation_digest_mismatch",
                )
            return DurableGenerationResult(
                generation,
                digest,
                "durable_generation_built",
                self.solution_namespace_id,
            )
        except _RepositoryError as exc:
            reason = (
                exc.reason_code
                if exc.reason_code
                in {
                    "durable_generation_capacity_exceeded",
                    "durable_generation_digest_mismatch",
                    "durable_generation_invalid",
                }
                else "durable_generation_write_failed"
            )
            return DurableGenerationResult("", "", reason)
        except (AttributeError, OverflowError, RecursionError, TypeError, ValueError):
            return DurableGenerationResult("", "", "durable_generation_invalid")

    def _inspect_generation(
        self,
        generation_id: str,
        *,
        expected_manifest_set_digest: str | None = None,
    ) -> _GenerationInspection:
        try:
            self._require_open()
            if _HEX_32.fullmatch(generation_id or "") is None:
                raise _RepositoryError("durable_generation_invalid")
            if (
                expected_manifest_set_digest is not None
                and _SHA256.fullmatch(expected_manifest_set_digest) is None
            ):
                raise _RepositoryError("durable_generation_invalid")
            manifest_relative = f"generations/{generation_id}/manifest-set.json"
            manifest_raw = _read_file(
                self._root,
                manifest_relative,
                maximum=MAX_DURABLE_MANIFEST_SET_BYTES,
                missing_reason="durable_generation_invalid",
                oversized_reason="durable_generation_capacity_exceeded",
            )
            manifest_digest = hashlib.sha256(manifest_raw).hexdigest()
            if (
                expected_manifest_set_digest is not None
                and manifest_digest != expected_manifest_set_digest
            ):
                raise _RepositoryError("durable_generation_digest_mismatch")
            manifest = self._manifest_set(manifest_raw)
            if (
                manifest["generation_id"] != generation_id
                or manifest["solution_namespace_id"] != self.solution_namespace_id
            ):
                raise _RepositoryError("durable_generation_invalid")

            paths: set[Path] = {self._root / manifest_relative}
            record_count = 0
            node_manifest_bytes = 0
            referenced_bytes = 0
            for entry in manifest["node_manifests"]:
                node_relative = (
                    f"generations/{generation_id}/{entry['relative_path']}"
                )
                node_raw = _read_file(
                    self._root,
                    node_relative,
                    maximum=MAX_DURABLE_NODE_MANIFEST_BYTES,
                    missing_reason="durable_generation_invalid",
                    oversized_reason="durable_generation_capacity_exceeded",
                )
                if hashlib.sha256(node_raw).hexdigest() != entry["node_manifest_digest"]:
                    raise _RepositoryError("durable_generation_digest_mismatch")
                node_manifest_bytes += len(node_raw)
                if (
                    node_manifest_bytes
                    > MAX_DURABLE_NODE_MANIFEST_BYTES_PER_GENERATION
                ):
                    raise _RepositoryError(
                        "durable_generation_capacity_exceeded"
                    )
                generic_node = _strict_json_bytes(
                    node_raw,
                    maximum=MAX_DURABLE_NODE_MANIFEST_BYTES,
                )
                node_manifest = self._node_manifest(
                    node_raw,
                    generic_node.get("workspace_id", ""),
                    generic_node.get("node_id", ""),
                )
                record_count += len(node_manifest["records"])
                if record_count > MAX_DURABLE_RECORDS_PER_GENERATION:
                    raise _RepositoryError(
                        "durable_generation_capacity_exceeded"
                    )
                paths.add(self._root / node_relative)
                for record_ref in node_manifest["records"]:
                    record_digest = record_ref["record_digest"]
                    record_relative = (
                        f"records/sha256/{record_digest[:2]}/{record_digest}.json"
                    )
                    record_raw = _read_file(
                        self._root,
                        record_relative,
                        maximum=MAX_DURABLE_RECORD_JSON_BYTES,
                        missing_reason="durable_generation_invalid",
                        oversized_reason="durable_generation_capacity_exceeded",
                    )
                    if hashlib.sha256(record_raw).hexdigest() != record_digest:
                        raise _RepositoryError(
                            "durable_generation_digest_mismatch"
                        )
                    referenced_bytes += len(record_raw)
                    if referenced_bytes > MAX_DURABLE_REFERENCED_BYTES_PER_GENERATION:
                        raise _RepositoryError(
                            "durable_generation_capacity_exceeded"
                        )
                    record = SolutionRecord.from_payload(
                        _strict_json_bytes(
                            record_raw,
                            maximum=MAX_DURABLE_RECORD_JSON_BYTES,
                        ),
                        catalog=self._catalog,
                    )
                    if (
                        _canonical_json_bytes(
                            record.to_payload(catalog=self._catalog)
                        )
                        != record_raw
                        or record.project_id != self.project_id
                        or record.workspace_id != node_manifest["workspace_id"]
                        or record.node_id != node_manifest["node_id"]
                        or record.solution_key != record_ref["solution_key"]
                        or record.residency is not SolutionResidency.DURABLE
                        or not record.reuse_eligible
                    ):
                        raise _RepositoryError("durable_generation_invalid")
                    paths.add(self._root / record_relative)
                    if record.payload_locator is None:
                        continue
                    blob_digest = record.payload_locator.reference_id
                    blob_relative = f"blobs/sha256/{blob_digest[:2]}/{blob_digest}"
                    blob_raw = _read_file(
                        self._root,
                        blob_relative,
                        maximum=MAX_DURABLE_RESULT_BLOB_BYTES,
                        missing_reason="durable_generation_invalid",
                        oversized_reason="durable_generation_capacity_exceeded",
                    )
                    if hashlib.sha256(blob_raw).hexdigest() != blob_digest:
                        raise _RepositoryError(
                            "durable_generation_digest_mismatch"
                        )
                    referenced_bytes += len(blob_raw)
                    if referenced_bytes > MAX_DURABLE_REFERENCED_BYTES_PER_GENERATION:
                        raise _RepositoryError(
                            "durable_generation_capacity_exceeded"
                        )
                    loaded = self.load_payload(record, self._catalog)
                    if loaded.reason_code != "durable_hit":
                        reason = (
                            "durable_generation_capacity_exceeded"
                            if loaded.reason_code == "durable_payload_oversized"
                            else "durable_generation_invalid"
                        )
                        raise _RepositoryError(reason)
                    paths.add(self._root / blob_relative)
            return _GenerationInspection(
                paths=frozenset(paths),
                manifest_set_digest=manifest_digest,
            )
        except _RepositoryError:
            raise
        except (
            AttributeError,
            OverflowError,
            RecursionError,
            TypeError,
            ValueError,
        ) as exc:
            raise _RepositoryError("durable_generation_invalid") from exc

    def validate_generation(
        self,
        generation_id: str,
        manifest_set_digest: str,
    ) -> DurableGenerationResult:
        try:
            inspection = self._inspect_generation(
                generation_id,
                expected_manifest_set_digest=manifest_set_digest,
            )
        except _RepositoryError as exc:
            reason = (
                exc.reason_code
                if exc.reason_code
                in {
                    "durable_generation_capacity_exceeded",
                    "durable_generation_digest_mismatch",
                    "durable_generation_invalid",
                }
                else "durable_generation_invalid"
            )
            return DurableGenerationResult("", "", reason)
        return DurableGenerationResult(
            generation_id,
            inspection.manifest_set_digest,
            "durable_generation_valid",
            self.solution_namespace_id,
        )

    def enumerate_reachable_paths(
        self,
        generation_ids: Iterable[str],
    ) -> frozenset[Path]:
        if isinstance(generation_ids, (str, bytes)):
            raise TypeError("generation_ids must be an iterable of IDs")
        reachable: set[Path] = set()
        try:
            for generation_id in tuple(generation_ids):
                expected_digest = (
                    self._active_manifest_set_digest
                    if generation_id == self._active_generation_id
                    else None
                )
                inspection = self._inspect_generation(
                    generation_id,
                    expected_manifest_set_digest=expected_digest,
                )
                reachable.update(inspection.paths)
        except _RepositoryError as exc:
            raise ValueError("durable generation reachability is invalid") from exc
        return frozenset(reachable)

    def prune_unreachable_paths(
        self,
        candidate_relative_paths: Iterable[str],
        *,
        reachable_paths: Iterable[Path],
    ) -> tuple[str, ...]:
        self._require_open()
        if isinstance(candidate_relative_paths, (str, bytes)):
            raise TypeError("candidate_relative_paths must be an iterable")
        if isinstance(reachable_paths, (str, bytes)):
            raise TypeError("reachable_paths must be an iterable")
        protected = {Path(path) for path in reachable_paths}
        if self._active_generation_id:
            protected.update(
                self.enumerate_reachable_paths((self._active_generation_id,))
            )
        protected_keys = {
            os.path.normcase(os.path.abspath(os.fspath(path)))
            for path in protected
        }
        candidates: list[tuple[str, Path, tuple[int, int, int, int, int]]] = []
        for relative in sorted(set(candidate_relative_paths)):
            if (
                not isinstance(relative, str)
                or not any(pattern.fullmatch(relative) for pattern in _PRUNABLE_PATH_PATTERNS)
            ):
                raise ValueError("prune candidate path is invalid")
            try:
                target = validate_owned_artifact_path(self._root, relative)
            except FileNotFoundError:
                continue
            except ValueError as exc:
                raise ValueError("prune candidate path is unsafe") from exc
            if os.path.normcase(os.path.abspath(os.fspath(target))) in protected_keys:
                continue
            target_stat = os.lstat(target)
            if not stat.S_ISREG(target_stat.st_mode):
                raise ValueError("prune candidate is not a regular file")
            candidates.append((relative, target, _identity(target_stat)))

        for _relative, target, expected_identity in candidates:
            validate_owned_artifact_path(
                self._root,
                target.relative_to(self._root).as_posix(),
            )
            if _identity(os.lstat(target)) != expected_identity:
                raise ValueError("prune candidate changed during validation")

        removed: list[str] = []
        for relative, target, expected_identity in candidates:
            try:
                validate_owned_artifact_path(self._root, relative)
                if _identity(os.lstat(target)) != expected_identity:
                    raise ValueError("prune candidate changed before deletion")
                target.unlink()
                if target.exists():
                    continue
            except FileNotFoundError:
                continue
            except OSError:
                continue
            removed.append(relative)
        return tuple(removed)


__all__ = [
    "DurableGenerationResult",
    "MAX_DURABLE_DIAGNOSTIC_UTF8_BYTES",
    "MAX_DURABLE_JSON_DEPTH",
    "MAX_DURABLE_MANIFEST_SET_BYTES",
    "MAX_DURABLE_NODE_MANIFESTS_PER_GENERATION",
    "MAX_DURABLE_NODE_MANIFEST_BYTES",
    "MAX_DURABLE_NODE_MANIFEST_BYTES_PER_GENERATION",
    "MAX_DURABLE_RECORDS_PER_GENERATION",
    "MAX_DURABLE_RECORDS_PER_NODE",
    "MAX_DURABLE_RECORD_JSON_BYTES",
    "MAX_DURABLE_REFERENCED_BYTES_PER_GENERATION",
    "MAX_DURABLE_RESULT_BLOB_BYTES",
    "SCHEMA_VERSION",
    "SolutionRepository",
    "SolutionRepositoryFactory",
    "node_path_key",
    "workspace_path_key",
]
