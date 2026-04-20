from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.nodes.plugin_contracts import PluginProvenance

NODE_TITLE_ICON_ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets" / "node_title_icons"
SUPPORTED_NODE_TITLE_ICON_SUFFIXES = frozenset({".svg", ".png", ".jpg", ".jpeg"})
TITLE_ICON_RUNTIME_BEHAVIORS = frozenset({"active", "compile_only"})

_WINDOWS_ABSOLUTE_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def resolve_node_title_icon_source(
    icon: object,
    *,
    provenance: PluginProvenance | None = None,
    asset_root: Path | None = None,
) -> str:
    """Resolve authored node icon metadata to a local QML source URL."""
    authored_icon = str(icon or "").strip()
    if not authored_icon or _has_url_scheme(authored_icon):
        return ""

    authored_path = Path(authored_icon)
    if authored_path.is_absolute():
        return _local_icon_source_url(authored_path)

    root = _relative_icon_root(provenance=provenance, asset_root=asset_root)
    if root is None:
        return ""
    root = root.resolve(strict=False)
    candidate = (root / authored_path).resolve(strict=False)
    if not _is_relative_to(candidate, root):
        return ""
    return _local_icon_source_url(candidate, required_root=root)


def title_icon_source_for_node_payload(
    spec: NodeTypeSpec,
    *,
    provenance: PluginProvenance | None = None,
) -> str:
    # Passive nodes suppress the title icon by default (flowchart, planning,
    # annotation, and media families draw their own body art). Data-source-
    # style passive nodes can opt back in via ``NodeTypeSpec.show_title_icon``.
    if (
        spec.runtime_behavior not in TITLE_ICON_RUNTIME_BEHAVIORS
        and not getattr(spec, "show_title_icon", False)
    ):
        return ""
    return resolve_node_title_icon_source(spec.icon, provenance=provenance)


def _relative_icon_root(
    *,
    provenance: PluginProvenance | None,
    asset_root: Path | None,
) -> Path | None:
    if provenance is None:
        return asset_root or NODE_TITLE_ICON_ASSET_ROOT

    if provenance.kind == "file" and provenance.source_path is not None:
        return provenance.source_path.resolve(strict=False).parent
    if provenance.kind in {"package", "entry_point"} and provenance.package_root is not None:
        return provenance.package_root
    return None


def _local_icon_source_url(path: Path, *, required_root: Path | None = None) -> str:
    if path.suffix.casefold() not in SUPPORTED_NODE_TITLE_ICON_SUFFIXES:
        return ""
    try:
        resolved_path = path.resolve(strict=True)
    except OSError:
        return ""
    if required_root is not None and not _is_relative_to(
        resolved_path,
        required_root.resolve(strict=False),
    ):
        return ""
    if not resolved_path.is_file() or not _is_readable_file(resolved_path):
        return ""
    try:
        return resolved_path.as_uri()
    except ValueError:
        return ""


def _is_readable_file(path: Path) -> bool:
    try:
        with path.open("rb"):
            return True
    except OSError:
        return False


def _has_url_scheme(value: str) -> bool:
    if _WINDOWS_ABSOLUTE_DRIVE_RE.match(value):
        return False
    return bool(urlsplit(value).scheme)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


__all__ = [
    "NODE_TITLE_ICON_ASSET_ROOT",
    "SUPPORTED_NODE_TITLE_ICON_SUFFIXES",
    "TITLE_ICON_RUNTIME_BEHAVIORS",
    "resolve_node_title_icon_source",
    "title_icon_source_for_node_payload",
]
