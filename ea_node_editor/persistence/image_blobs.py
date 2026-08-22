# Purpose: Externalize immutable ImageValue bytes into content-addressed project sidecar blobs.
# Map: subsystems/persistence
# Tests: tests/test_image_value.py
from __future__ import annotations

import copy
import hashlib
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.persistence.artifact_store import (
    ProjectArtifactLayout,
    ensure_owned_artifact_directory,
    validate_owned_artifact_path,
)
from ea_node_editor.runtime_contracts import (
    IMAGE_VALUE_MAX_ENCODED_BYTES,
    DataTypeCatalog,
    ImageValue,
)

PROJECT_IMAGE_MARKER_KEY = "__ea_project_image__"
PROJECT_IMAGE_MARKER_VALUE = "image_blob"
PROJECT_IMAGE_METADATA_KEY = "image_blobs"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_MAX_RAW_BYTES = (IMAGE_VALUE_MAX_ENCODED_BYTES // 4) * 3


def _image_root(project_path: str | Path) -> Path:
    return ProjectArtifactLayout.from_project_path(project_path).sidecar_root / "images"


def _write_blob(root: Path, image: ImageValue) -> None:
    root = ensure_owned_artifact_directory(root)
    try:
        target = validate_owned_artifact_path(root, f"{image.sha256}.png")
    except FileNotFoundError:
        target = validate_owned_artifact_path(root, f"{image.sha256}.png", allow_missing=True)
    else:
        existing = target.read_bytes()
        if len(existing) == len(image.encoded_bytes) and hashlib.sha256(existing).hexdigest() == image.sha256:
            return
    fd, temporary = tempfile.mkstemp(prefix=f".{image.sha256}.", suffix=".tmp", dir=root)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(image.encoded_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def _project_marker(image: ImageValue) -> dict[str, Any]:
    return {
        PROJECT_IMAGE_MARKER_KEY: PROJECT_IMAGE_MARKER_VALUE,
        "schema_version": image.schema_version,
        "format": image.format,
        "width": image.width,
        "height": image.height,
        "sha256": image.sha256,
    }


def externalize_project_images(
    document: Mapping[str, Any],
    *,
    project_path: str | Path,
    catalog: DataTypeCatalog,
) -> dict[str, Any]:
    root = _image_root(project_path)
    referenced: set[str] = set()

    def visit(value: Any) -> Any:
        if isinstance(value, Mapping):
            if value.get("__ea_runtime_value__") == "image_value":
                image = ImageValue.from_payload(value, catalog=catalog)
                if image is None:
                    raise ValueError("persistent ImageValue payload is incomplete")
                _write_blob(root, image)
                referenced.add(image.sha256)
                return _project_marker(image)
            return {str(key): visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return copy.deepcopy(value)

    prepared = visit(document)
    if not isinstance(prepared, dict):
        raise TypeError("project document must be a mapping")
    metadata = dict(prepared.get("metadata", {})) if isinstance(prepared.get("metadata"), Mapping) else {}
    if referenced:
        metadata[PROJECT_IMAGE_METADATA_KEY] = sorted(referenced)
    else:
        metadata.pop(PROJECT_IMAGE_METADATA_KEY, None)
    prepared["metadata"] = metadata

    return prepared


def tracked_project_image_digests(document: Mapping[str, Any]) -> frozenset[str]:
    metadata = document.get("metadata")
    if not isinstance(metadata, Mapping):
        return frozenset()
    values = metadata.get(PROJECT_IMAGE_METADATA_KEY)
    if not isinstance(values, list):
        return frozenset()
    return frozenset(
        value
        for value in values
        if isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None
    )


def prune_project_images(
    *,
    project_path: str | Path,
    tracked_digests: frozenset[str] | set[str],
    retained_digests: frozenset[str] | set[str],
) -> None:
    root = _image_root(project_path)
    for digest in sorted(set(tracked_digests) - set(retained_digests)):
        if _SHA256_PATTERN.fullmatch(digest) is None:
            continue
        try:
            validate_owned_artifact_path(root, f"{digest}.png").unlink()
        except (FileNotFoundError, OSError, ValueError):
            continue
    try:
        validate_owned_artifact_path(
            root.parent,
            root.name,
            leaf_kind="directory",
        ).rmdir()
    except (FileNotFoundError, OSError, ValueError):
        pass


def hydrate_project_images(
    document: Mapping[str, Any],
    *,
    project_path: str | Path,
    catalog: DataTypeCatalog,
) -> dict[str, Any]:
    root = _image_root(project_path)

    def visit(value: Any) -> Any:
        if isinstance(value, Mapping):
            if PROJECT_IMAGE_MARKER_KEY in value:
                expected = {
                    PROJECT_IMAGE_MARKER_KEY,
                    "schema_version",
                    "format",
                    "width",
                    "height",
                    "sha256",
                }
                if set(value) != expected or value[PROJECT_IMAGE_MARKER_KEY] != PROJECT_IMAGE_MARKER_VALUE:
                    raise ValueError("persistent image blob marker is invalid")
                digest = value["sha256"]
                if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
                    raise ValueError("persistent image blob sha256 is invalid")
                try:
                    path = validate_owned_artifact_path(root, f"{digest}.png")
                except FileNotFoundError:
                    raise ValueError(f"persistent image blob is missing or too large: {digest}") from None
                if os.lstat(path).st_size > _MAX_RAW_BYTES:
                    raise ValueError(f"persistent image blob is missing or too large: {digest}")
                image = ImageValue.from_png(path.read_bytes())
                if (
                    image.sha256 != digest
                    or image.schema_version != value["schema_version"]
                    or image.format != value["format"]
                    or image.width != value["width"]
                    or image.height != value["height"]
                ):
                    raise ValueError(f"persistent image blob metadata does not match: {digest}")
                return image.to_payload(catalog=catalog)
            return {str(key): visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return copy.deepcopy(value)

    hydrated = visit(document)
    if not isinstance(hydrated, dict):
        raise TypeError("project document must be a mapping")
    return hydrated


__all__ = [
    "PROJECT_IMAGE_MARKER_KEY",
    "PROJECT_IMAGE_MARKER_VALUE",
    "PROJECT_IMAGE_METADATA_KEY",
    "externalize_project_images",
    "hydrate_project_images",
    "prune_project_images",
    "tracked_project_image_digests",
]
