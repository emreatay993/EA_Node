from __future__ import annotations

import copy
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from uuid import uuid4

from ea_node_editor.settings import (
    PROJECT_ARTIFACT_RECOVERY_DIRNAME,
    PROJECT_ARTIFACT_STAGING_DIRNAME,
    PROJECT_ARTIFACT_STORE_METADATA_KEY,
    PROJECT_DATA_DIR_SUFFIX,
    PROJECT_MANAGED_ARTIFACTS_DIRNAME,
    PROJECT_MANAGED_ASSETS_DIRNAME,
)

from .artifact_refs import (
    coerce_managed_artifact_id,
    coerce_staged_artifact_id,
    format_managed_artifact_ref,
    format_staged_artifact_ref,
)

_MANAGED_ROOT_NAMES = frozenset(
    {
        PROJECT_MANAGED_ASSETS_DIRNAME,
        PROJECT_MANAGED_ARTIFACTS_DIRNAME,
    }
)
_STAGING_ROOT_HINT_KIND_SESSION = "session_temp"


def _coerce_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _copy_mapping_excluding(payload: Mapping[str, Any], *excluded_keys: str) -> dict[str, Any]:
    excluded = set(excluded_keys)
    return {
        str(key): copy.deepcopy(value)
        for key, value in payload.items()
        if str(key) not in excluded
    }


def _normalize_relative_path(value: Any, *, allowed_roots: set[str] | frozenset[str] | None = None) -> str:
    text = _coerce_str(value).replace("\\", "/")
    if not text:
        return ""
    normalized_path = PurePosixPath(text)
    if normalized_path.is_absolute():
        return ""
    parts: list[str] = []
    for part in normalized_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return ""
        parts.append(part)
    if not parts:
        return ""
    if allowed_roots is not None and parts[0] not in allowed_roots:
        return ""
    return "/".join(parts)


def _normalize_absolute_path(value: Any) -> str | None:
    text = _coerce_str(value)
    if not text:
        return None
    path = Path(text)
    if path.is_absolute() or PureWindowsPath(text).is_absolute():
        return text
    return None


def _metadata_entry_relative_path(
    payload: Mapping[str, Any],
    *,
    allowed_roots: set[str] | frozenset[str] | None = None,
) -> str:
    root = _normalize_relative_path(payload.get("root"))
    raw_relative = payload.get("relative_path")
    if raw_relative is None:
        raw_relative = payload.get("path")
    if raw_relative is None:
        return ""
    raw_text = _coerce_str(raw_relative)
    if root and raw_text and raw_text != root and not raw_text.startswith(f"{root}/"):
        raw_text = f"{root}/{raw_text}"
    return _normalize_relative_path(raw_text, allowed_roots=allowed_roots)


def _path_from_relative(relative_path: str) -> Path:
    return Path(*PurePosixPath(relative_path).parts)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _delete_path(path: Path) -> bool:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
            return True
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _prune_empty_ancestors(path: Path, *, stop_roots: tuple[Path, ...]) -> None:
    current = path
    while current not in stop_roots:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


@dataclass(frozen=True, slots=True)
class ProjectArtifactLayout:
    project_file: Path
    sidecar_root: Path
    assets_root: Path
    artifacts_root: Path
    staging_root: Path
    staging_recovery_root: Path

    @classmethod
    def from_project_path(cls, project_path: str | Path) -> "ProjectArtifactLayout":
        project_file = Path(project_path)
        sidecar_root = project_file.with_name(f"{project_file.stem}{PROJECT_DATA_DIR_SUFFIX}")
        staging_root = sidecar_root / PROJECT_ARTIFACT_STAGING_DIRNAME
        return cls(
            project_file=project_file,
            sidecar_root=sidecar_root,
            assets_root=sidecar_root / PROJECT_MANAGED_ASSETS_DIRNAME,
            artifacts_root=sidecar_root / PROJECT_MANAGED_ARTIFACTS_DIRNAME,
            staging_root=staging_root,
            staging_recovery_root=staging_root / PROJECT_ARTIFACT_RECOVERY_DIRNAME,
        )

    def absolute_path_for_relative(self, relative_path: str) -> Path:
        return self.sidecar_root.joinpath(_path_from_relative(relative_path))


@dataclass(frozen=True, slots=True)
class ManagedArtifactEntry:
    artifact_id: str
    relative_path: str
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def root_name(self) -> str:
        return PurePosixPath(self.relative_path).parts[0]

    def to_metadata_entry(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra)
        payload["relative_path"] = self.relative_path
        return payload

    def absolute_path(self, layout: ProjectArtifactLayout) -> Path:
        return layout.absolute_path_for_relative(self.relative_path)

    @classmethod
    def from_metadata(cls, artifact_id: str, payload: Any) -> "ManagedArtifactEntry" | None:
        normalized_id = coerce_managed_artifact_id(artifact_id)
        if not normalized_id or not isinstance(payload, Mapping):
            return None
        relative_path = _metadata_entry_relative_path(payload, allowed_roots=_MANAGED_ROOT_NAMES)
        if not relative_path:
            return None
        return cls(
            artifact_id=normalized_id,
            relative_path=relative_path,
            extra=_copy_mapping_excluding(payload, "relative_path", "path", "root"),
        )


@dataclass(frozen=True, slots=True)
class StagingRootHint:
    kind: str
    absolute_path: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_metadata_entry(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra)
        payload["kind"] = self.kind
        payload["absolute_path"] = self.absolute_path
        return payload

    def as_path(self) -> Path:
        return Path(self.absolute_path)

    @classmethod
    def from_metadata(cls, payload: Any) -> "StagingRootHint" | None:
        if isinstance(payload, str):
            absolute_path = _normalize_absolute_path(payload)
            if absolute_path is None:
                return None
            return cls(kind=_STAGING_ROOT_HINT_KIND_SESSION, absolute_path=absolute_path)
        if not isinstance(payload, Mapping):
            return None
        absolute_path = _normalize_absolute_path(payload.get("absolute_path"))
        if absolute_path is None:
            absolute_path = _normalize_absolute_path(payload.get("path"))
        if absolute_path is None:
            return None
        kind = _coerce_str(payload.get("kind")) or _STAGING_ROOT_HINT_KIND_SESSION
        return cls(
            kind=kind,
            absolute_path=absolute_path,
            extra=_copy_mapping_excluding(payload, "kind", "absolute_path", "path"),
        )


@dataclass(frozen=True, slots=True)
class StagedArtifactEntry:
    artifact_id: str
    relative_path: str | None = None
    absolute_path_hint: str | None = None
    slot: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_metadata_entry(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra)
        if self.relative_path:
            payload["relative_path"] = self.relative_path
        if self.absolute_path_hint:
            payload["absolute_path"] = self.absolute_path_hint
        if self.slot:
            payload["slot"] = self.slot
        return payload

    def absolute_path(
        self,
        layout: ProjectArtifactLayout | None,
        staging_root_hint: StagingRootHint | None = None,
    ) -> Path | None:
        if self.absolute_path_hint:
            return Path(self.absolute_path_hint)
        if self.relative_path:
            if self.relative_path == PROJECT_ARTIFACT_STAGING_DIRNAME or self.relative_path.startswith(
                f"{PROJECT_ARTIFACT_STAGING_DIRNAME}/"
            ):
                if layout is not None:
                    return layout.absolute_path_for_relative(self.relative_path)
            elif staging_root_hint is not None:
                return staging_root_hint.as_path().joinpath(_path_from_relative(self.relative_path))
        return None

    @classmethod
    def from_metadata(cls, artifact_id: str, payload: Any) -> "StagedArtifactEntry" | None:
        normalized_id = coerce_staged_artifact_id(artifact_id)
        if not normalized_id or not isinstance(payload, Mapping):
            return None
        relative_path = _metadata_entry_relative_path(payload)
        absolute_path_hint = _normalize_absolute_path(payload.get("absolute_path"))
        slot = _coerce_str(payload.get("slot")) or None
        extra = _copy_mapping_excluding(payload, "absolute_path", "relative_path", "path", "root", "slot")
        if not relative_path and not absolute_path_hint and not slot and not extra:
            return None
        return cls(
            artifact_id=normalized_id,
            relative_path=relative_path or None,
            absolute_path_hint=absolute_path_hint,
            slot=slot,
            extra=extra,
        )


@dataclass(frozen=True, slots=True)
class ArtifactStoreState:
    artifacts: dict[str, ManagedArtifactEntry] = field(default_factory=dict)
    staged: dict[str, StagedArtifactEntry] = field(default_factory=dict)
    staging_root: StagingRootHint | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_metadata(cls, payload: Any) -> "ArtifactStoreState":
        metadata = payload if isinstance(payload, Mapping) else {}
        raw_artifacts = metadata.get("artifacts")
        raw_staged = metadata.get("staged")
        artifacts: dict[str, ManagedArtifactEntry] = {}
        artifact_items = raw_artifacts.items() if isinstance(raw_artifacts, Mapping) else ()
        for artifact_id, entry_payload in sorted(artifact_items):
            entry = ManagedArtifactEntry.from_metadata(str(artifact_id), entry_payload)
            if entry is not None:
                artifacts[entry.artifact_id] = entry
        staged: dict[str, StagedArtifactEntry] = {}
        staged_items = raw_staged.items() if isinstance(raw_staged, Mapping) else ()
        for artifact_id, entry_payload in sorted(staged_items):
            entry = StagedArtifactEntry.from_metadata(str(artifact_id), entry_payload)
            if entry is not None:
                staged[entry.artifact_id] = entry
        return cls(
            artifacts=artifacts,
            staged=staged,
            staging_root=StagingRootHint.from_metadata(metadata.get("staging_root")),
            extra=_copy_mapping_excluding(metadata, "artifacts", "staged", "staging_root"),
        )

    def to_metadata(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra)
        payload["artifacts"] = {
            artifact_id: entry.to_metadata_entry()
            for artifact_id, entry in sorted(self.artifacts.items())
        }
        payload["staged"] = {
            artifact_id: entry.to_metadata_entry()
            for artifact_id, entry in sorted(self.staged.items())
        }
        if self.staging_root is not None:
            payload["staging_root"] = self.staging_root.to_metadata_entry()
        return payload


def normalize_artifact_store_metadata(payload: Any) -> dict[str, Any]:
    return ArtifactStoreState.from_metadata(payload).to_metadata()


def artifact_store_metadata_from_project_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        return normalize_artifact_store_metadata(None)
    return normalize_artifact_store_metadata(metadata.get(PROJECT_ARTIFACT_STORE_METADATA_KEY))


class ProjectArtifactStore:
    def __init__(
        self,
        *,
        project_path: str | Path | None,
        metadata: Mapping[str, Any] | ArtifactStoreState | None = None,
    ) -> None:
        self._project_path = Path(project_path) if project_path else None
        self._state = metadata if isinstance(metadata, ArtifactStoreState) else ArtifactStoreState.from_metadata(metadata)

    @classmethod
    def from_project_metadata(
        cls,
        *,
        project_path: str | Path | None,
        project_metadata: Mapping[str, Any] | None,
    ) -> "ProjectArtifactStore":
        return cls(
            project_path=project_path,
            metadata=artifact_store_metadata_from_project_metadata(project_metadata),
        )

    @property
    def project_path(self) -> Path | None:
        return self._project_path

    @property
    def layout(self) -> ProjectArtifactLayout | None:
        if self._project_path is None:
            return None
        return ProjectArtifactLayout.from_project_path(self._project_path)

    @property
    def state(self) -> ArtifactStoreState:
        return self._state

    @property
    def metadata(self) -> dict[str, Any]:
        return self._state.to_metadata()

    @property
    def staging_root_hint(self) -> StagingRootHint | None:
        return self._state.staging_root

    def managed_ref(self, artifact_id: str) -> str:
        return format_managed_artifact_ref(artifact_id)

    def staged_ref(self, artifact_id: str) -> str:
        return format_staged_artifact_ref(artifact_id)

    def managed_entry(self, artifact_id_or_ref: object) -> ManagedArtifactEntry | None:
        artifact_id = coerce_managed_artifact_id(artifact_id_or_ref)
        if not artifact_id:
            return None
        return self._state.artifacts.get(artifact_id)

    def staged_entry(self, artifact_id_or_ref: object) -> StagedArtifactEntry | None:
        artifact_id = coerce_staged_artifact_id(artifact_id_or_ref)
        if not artifact_id:
            return None
        return self._state.staged.get(artifact_id)

    def resolve_managed_path(self, artifact_id_or_ref: object) -> Path | None:
        entry = self.managed_entry(artifact_id_or_ref)
        layout = self.layout
        if entry is None or layout is None:
            return None
        return entry.absolute_path(layout)

    def resolve_staged_path(self, artifact_id_or_ref: object) -> Path | None:
        entry = self.staged_entry(artifact_id_or_ref)
        if entry is None:
            return None
        return entry.absolute_path(self.layout, self._state.staging_root)

    def ensure_staging_root(self, *, temporary_root_parent: str | Path | None = None) -> Path:
        layout = self.layout
        if layout is not None:
            layout.staging_root.mkdir(parents=True, exist_ok=True)
            return layout.staging_root

        if self._state.staging_root is not None:
            root = self._state.staging_root.as_path()
            root.mkdir(parents=True, exist_ok=True)
            return root

        if temporary_root_parent is None:
            raise ValueError("temporary_root_parent is required for unsaved project staging")

        parent = Path(temporary_root_parent)
        parent.mkdir(parents=True, exist_ok=True)
        root = parent / f"project-{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        self._state = replace(
            self._state,
            staging_root=StagingRootHint(
                kind=_STAGING_ROOT_HINT_KIND_SESSION,
                absolute_path=str(root),
            ),
        )
        return root

    def clear_staging_root_hint(self) -> None:
        if self._state.staging_root is None:
            return
        self._state = replace(self._state, staging_root=None)

    def register_staged_entry(
        self,
        artifact_id: str,
        *,
        relative_path: str | None = None,
        absolute_path_hint: str | Path | None = None,
        slot: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> StagedArtifactEntry:
        normalized_id = coerce_staged_artifact_id(artifact_id)
        if not normalized_id:
            raise ValueError(f"Invalid staged artifact id: {artifact_id!r}")

        normalized_relative = _normalize_relative_path(relative_path) or None
        if normalized_relative and self.layout is not None and not normalized_relative.startswith(
            f"{PROJECT_ARTIFACT_STAGING_DIRNAME}/"
        ):
            normalized_relative = _normalize_relative_path(
                f"{PROJECT_ARTIFACT_STAGING_DIRNAME}/{normalized_relative}"
            ) or None
        normalized_absolute = _normalize_absolute_path(absolute_path_hint)
        normalized_slot = _coerce_str(slot) or None
        payload_extra = copy.deepcopy(dict(extra)) if isinstance(extra, Mapping) else {}

        if not normalized_relative and not normalized_absolute:
            raise ValueError("A staged entry requires a relative path or an absolute path hint")

        entry = StagedArtifactEntry(
            artifact_id=normalized_id,
            relative_path=normalized_relative,
            absolute_path_hint=normalized_absolute,
            slot=normalized_slot,
            extra=payload_extra,
        )

        staged = dict(self._state.staged)
        removed_entries: list[StagedArtifactEntry] = []
        current_entry = staged.get(normalized_id)
        if current_entry is not None:
            removed_entries.append(current_entry)
        for existing_id, existing_entry in list(staged.items()):
            if existing_id == normalized_id or not normalized_slot:
                continue
            if existing_entry.slot == normalized_slot:
                removed_entries.append(existing_entry)
                staged.pop(existing_id, None)
        staged[normalized_id] = entry
        self._state = replace(self._state, staged=staged)

        new_path = self.resolve_staged_path(normalized_id)
        stop_roots = self._cleanup_stop_roots()
        for removed_entry in removed_entries:
            removed_path = removed_entry.absolute_path(self.layout, self._state.staging_root)
            if removed_path is None or removed_path == new_path:
                continue
            if _delete_path(removed_path):
                _prune_empty_ancestors(removed_path.parent, stop_roots=stop_roots)
        return entry

    def discard_staged_payloads(self) -> bool:
        removed_any = False
        roots_to_remove: list[Path] = []
        if self.layout is not None:
            roots_to_remove.append(self.layout.staging_root)
        if self._state.staging_root is not None:
            roots_to_remove.append(self._state.staging_root.as_path())

        deduped_roots: list[Path] = []
        seen_roots: set[str] = set()
        for root in roots_to_remove:
            key = str(root)
            if key in seen_roots:
                continue
            seen_roots.add(key)
            deduped_roots.append(root)

        for root in sorted(deduped_roots, key=lambda item: len(item.parts), reverse=True):
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)
                removed_any = True

        stop_roots = self._cleanup_stop_roots()
        for entry in self._state.staged.values():
            path = entry.absolute_path(self.layout, self._state.staging_root)
            if path is None:
                continue
            if any(path == root or _is_relative_to(path, root) for root in deduped_roots):
                continue
            if _delete_path(path):
                removed_any = True
                _prune_empty_ancestors(path.parent, stop_roots=stop_roots)

        if self._state.staging_root is not None:
            self._state = replace(self._state, staging_root=None)
        return removed_any

    def _cleanup_stop_roots(self) -> tuple[Path, ...]:
        roots: list[Path] = []
        if self.layout is not None:
            roots.extend([self.layout.sidecar_root, self.layout.staging_root])
        if self._state.staging_root is not None:
            roots.append(self._state.staging_root.as_path())
        return tuple(roots)
