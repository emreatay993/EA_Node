"""Resolve a DPF operator node ``type_id`` to its Markdown spec page.

The spec pages live under ``docs/dpf_operator_docs/operator-specifications/`` and
an index keyed on the DPF internal ``operator.name`` (for example
``merge::fields_container``) is produced next to them at
``docs/dpf_operator_docs/doc_index.json``.

The catalog persists the same ``operator.name`` on every generated operator
``NodeTypeSpec`` as ``source_metadata.variants[0].operator_name``
(see [ansys_dpf_operator_catalog.py](../nodes/builtins/ansys_dpf_operator_catalog.py)).
Resolution is therefore a dict lookup — no DPF query at runtime.
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from ea_node_editor.help._qt_markdown import prepare_for_qt
from ea_node_editor.nodes.node_specs import DpfOperatorSourceSpec, NodeTypeSpec

_DOCS_ROOT_SEGMENTS = ("docs", "dpf_operator_docs")
_OPERATOR_SPECS_DIR = "operator-specifications"
_DOC_INDEX_FILENAME = "doc_index.json"
_DPF_OPERATOR_TYPE_ID_PREFIX = "dpf.op."


class _SpecLookup(Protocol):
    def spec_or_none(self, type_id: str) -> NodeTypeSpec | None: ...


def is_dpf_operator_type_id(type_id: str | None) -> bool:
    return bool(type_id) and str(type_id).startswith(_DPF_OPERATOR_TYPE_ID_PREFIX)


@lru_cache(maxsize=1)
def docs_root() -> Path:
    """Resolve ``docs/dpf_operator_docs/`` in dev and PyInstaller layouts."""
    for base in _candidate_root_bases():
        candidate = base.joinpath(*_DOCS_ROOT_SEGMENTS)
        if candidate.is_dir():
            return candidate
    # Fall back to the dev path even if missing so the caller sees a predictable
    # error rather than a random parent directory.
    return _repo_root().joinpath(*_DOCS_ROOT_SEGMENTS)


def _candidate_root_bases() -> tuple[Path, ...]:
    bases: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bases.append(Path(meipass))
    bases.append(_repo_root())
    return tuple(bases)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _doc_index() -> dict[str, str]:
    index_path = docs_root() / _DOC_INDEX_FILENAME
    if not index_path.is_file():
        return {}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if value}


def _operator_name_from_spec(spec: NodeTypeSpec | None) -> str:
    if spec is None:
        return ""
    source = getattr(spec, "source_metadata", None)
    if not isinstance(source, DpfOperatorSourceSpec):
        return ""
    if not source.variants:
        return ""
    return str(source.variants[0].operator_name or "").strip()


def markdown_path_for_type_id(type_id: str, lookup: _SpecLookup) -> Path | None:
    if not is_dpf_operator_type_id(type_id):
        return None
    spec = lookup.spec_or_none(type_id)
    operator_name = _operator_name_from_spec(spec)
    if not operator_name:
        return None
    relative = _doc_index().get(operator_name)
    if not relative:
        return None
    return docs_root() / _OPERATOR_SPECS_DIR / relative


def markdown_for_type_id(type_id: str, lookup: _SpecLookup) -> str | None:
    path = markdown_path_for_type_id(type_id, lookup)
    if path is None or not path.is_file():
        return None
    return _load_prepared_markdown(path)


@lru_cache(maxsize=256)
def _load_prepared_markdown(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return prepare_for_qt(raw)


def _host_lookup(host: Any) -> _SpecLookup | None:
    registry = getattr(host, "registry", None)
    if registry is None or not hasattr(registry, "spec_or_none"):
        return None
    return registry


def markdown_for_node(host: Any, node_id: str) -> tuple[str, str, str] | None:
    """Return ``(markdown, type_id, display_name)`` for a node if it has docs."""
    lookup = _host_lookup(host)
    if lookup is None or not node_id:
        return None
    spec_by_node = _spec_for_node(host, node_id)
    if spec_by_node is None:
        return None
    node, spec = spec_by_node
    if not is_dpf_operator_type_id(spec.type_id):
        return None
    markdown = markdown_for_type_id(spec.type_id, lookup)
    if markdown is None:
        return None
    display_name = str(getattr(spec, "display_name", "") or spec.type_id)
    return markdown, str(spec.type_id), display_name


def _spec_for_node(host: Any, node_id: str) -> tuple[Any, NodeTypeSpec] | None:
    workspace_id = str(
        getattr(host, "active_workspace_id", "")
        or (
            host.workspace_manager.active_workspace_id()
            if hasattr(host, "workspace_manager")
            else ""
        )
        or ""
    ).strip()
    if not workspace_id:
        return None
    project = getattr(getattr(host, "model", None), "project", None)
    workspace = project.workspaces.get(workspace_id) if project is not None else None
    node = workspace.nodes.get(node_id) if workspace is not None else None
    if node is None:
        return None
    lookup = _host_lookup(host)
    if lookup is None:
        return None
    spec = lookup.spec_or_none(node.type_id)
    if spec is None:
        return None
    return node, spec


__all__ = [
    "docs_root",
    "is_dpf_operator_type_id",
    "markdown_for_node",
    "markdown_for_type_id",
    "markdown_path_for_type_id",
]
