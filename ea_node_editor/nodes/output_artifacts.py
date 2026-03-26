from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ea_node_editor.nodes.types import ExecutionContext, RuntimeArtifactRef
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.settings import (
    PROJECT_ARTIFACT_SESSION_STAGING_DIRNAME,
    PROJECT_MANAGED_ARTIFACTS_DIRNAME,
    recent_session_path,
)

_INVALID_ARTIFACT_TOKEN_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class ManagedOutputWriteResult:
    path: Path
    artifact_ref: RuntimeArtifactRef


def _sanitize_artifact_token(value: Any, *, fallback: str) -> str:
    text = _INVALID_ARTIFACT_TOKEN_CHARS.sub("_", str(value).strip())
    text = text.strip("._-")
    return text or fallback


def _default_staging_workspace_root() -> Path:
    return recent_session_path().parent / PROJECT_ARTIFACT_SESSION_STAGING_DIRNAME


def _normalize_suffix(value: str) -> str:
    suffix = str(value or "").strip()
    if not suffix:
        return ""
    return suffix if suffix.startswith(".") else f".{suffix}"


def _normalize_managed_subdirectory(value: str) -> str:
    raw_path = PurePosixPath(str(value or "").replace("\\", "/"))
    parts = [part for part in raw_path.parts if part not in {"", ".", ".."}]
    return "/".join(parts) if parts else "generated"


def _managed_output_artifact_id(ctx: ExecutionContext, *, output_key: str) -> str:
    workspace_id = _sanitize_artifact_token(ctx.workspace_id, fallback="workspace")
    node_id = _sanitize_artifact_token(ctx.node_id, fallback="node")
    output_name = _sanitize_artifact_token(output_key, fallback="output")
    return f"generated.{workspace_id}.{node_id}.{output_name}"


def _managed_output_slot(ctx: ExecutionContext, *, output_key: str) -> str:
    return f"{ctx.workspace_id}:{ctx.node_id}:{output_key}"


def _managed_output_relative_path(
    artifact_id: str,
    *,
    suffix: str,
    managed_subdirectory: str,
) -> str:
    relative_path = PurePosixPath(
        PROJECT_MANAGED_ARTIFACTS_DIRNAME,
        _normalize_managed_subdirectory(managed_subdirectory),
        f"{artifact_id}{suffix}",
    )
    return relative_path.as_posix()


def _resolver_store_from_context(ctx: ExecutionContext) -> ProjectArtifactStore | None:
    owner = getattr(ctx.path_resolver, "__self__", None)
    if owner is None:
        return None
    if isinstance(owner, ProjectArtifactResolver):
        return owner.store

    direct_store = getattr(owner, "store", None)
    if isinstance(direct_store, ProjectArtifactStore):
        return direct_store
    return None


def _artifact_store_for_context(ctx: ExecutionContext) -> ProjectArtifactStore:
    live_store = _resolver_store_from_context(ctx)
    if live_store is not None:
        _persist_runtime_artifact_store(ctx, live_store)
        return live_store

    if ctx.artifact_store is not None:
        return ctx.artifact_store

    store = ProjectArtifactStore.from_project_metadata(
        project_path=ctx.project_path or None,
        project_metadata=ctx.runtime_project_metadata(),
    )
    _persist_runtime_artifact_store(ctx, store)
    return store


def _persist_runtime_artifact_store(ctx: ExecutionContext, store: ProjectArtifactStore) -> None:
    if ctx.runtime_snapshot_context is not None:
        ctx.runtime_snapshot_context.artifact_store = store
        return

    if ctx.runtime_snapshot is None and not ctx.project_path:
        return

    from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshotContext

    ctx.runtime_snapshot_context = RuntimeSnapshotContext.from_snapshot(
        ctx.runtime_snapshot,
        project_path=ctx.project_path,
        artifact_store=store,
    )


def write_managed_output(
    ctx: ExecutionContext,
    *,
    output_key: str,
    default_suffix: str,
    managed_subdirectory: str = "generated",
    write_payload: Callable[[Path], None],
) -> ManagedOutputWriteResult:
    store = _artifact_store_for_context(ctx)
    staging_root = store.ensure_staging_root(
        temporary_root_parent=_default_staging_workspace_root(),
    )

    artifact_id = _managed_output_artifact_id(ctx, output_key=output_key)
    relative_path = _managed_output_relative_path(
        artifact_id,
        suffix=_normalize_suffix(default_suffix),
        managed_subdirectory=managed_subdirectory,
    )
    output_path = staging_root.joinpath(*PurePosixPath(relative_path).parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_payload(output_path)

    store.register_staged_entry(
        artifact_id,
        relative_path=relative_path,
        slot=_managed_output_slot(ctx, output_key=output_key),
    )
    _persist_runtime_artifact_store(ctx, store)
    return ManagedOutputWriteResult(
        path=output_path,
        artifact_ref=RuntimeArtifactRef.staged(artifact_id),
    )


def default_staging_workspace_root() -> Path:
    return _default_staging_workspace_root()


def artifact_store_for_context(ctx: ExecutionContext) -> ProjectArtifactStore:
    return _artifact_store_for_context(ctx)


def persist_artifact_store(ctx: ExecutionContext, store: ProjectArtifactStore) -> None:
    _persist_runtime_artifact_store(ctx, store)


__all__ = [
    "ManagedOutputWriteResult",
    "artifact_store_for_context",
    "default_staging_workspace_root",
    "persist_artifact_store",
    "write_managed_output",
]
