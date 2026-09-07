# Purpose: Execute Open Mechanical Model through the run-owned native session.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_open_model.py

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from ea_node_editor.addons.mechanical.contracts import decode_selector
from ea_node_editor.nodes.execution_context import NodeInputNotReadyError


def discover_mechanical_releases() -> tuple[int, ...]:
    try:
        from ansys.tools.common.path import get_available_ansys_installations
        found = get_available_ansys_installations()
    except (ImportError, OSError) as exc:
        raise RuntimeError("Mechanical installation discovery is unavailable") from exc
    releases = tuple(sorted((int(code) for code in found if int(code) >= 261), reverse=True))
    return releases


def _release(requested: object) -> int:
    if isinstance(requested, bool) or not isinstance(requested, (int, float)) or int(requested) != requested:
        raise ValueError("Version must be an integer release code")
    code = int(requested)
    if code and code < 261:
        raise ValueError("mechanical.release_unsupported: releases earlier than 261 are unsupported")
    available = discover_mechanical_releases()
    if not available:
        raise RuntimeError("mechanical.release_unsupported: no supported Mechanical release (261 or newer) is installed")
    if code and code not in available:
        raise RuntimeError(f"mechanical.release_unsupported: release {code} is not installed; available releases: {list(available)}")
    return code or available[0]


def _source_key(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _setting(ctx, settings, key: str, default):
    if key in ctx.inputs:
        return ctx.inputs[key]
    if settings is not None and hasattr(settings, key):
        return getattr(settings, key)
    return ctx.properties.get(key, default)


def execute_open_model(ctx, settings=None):
    raw_source = _setting(ctx, settings, "file", "")
    if not str(raw_source or "").strip():
        raise NodeInputNotReadyError("File requires an existing Mechanical model or archive")
    source = ctx.resolve_path_value(raw_source)
    if source is None or not source.is_file():
        raise ValueError(f"mechanical.open_failed: File must resolve to an existing regular file: {raw_source}")
    suffix = source.suffix.casefold()
    if suffix not in {".mechdat", ".mechdb", ".mechpz", ".wbpj", ".wbpz"}:
        raise ValueError("File must be .mechdat, .mechdb, .mechpz, .wbpj, or .wbpz")
    mode = str(_setting(ctx, settings, "mode", "background")).strip()
    if mode not in {"background", "interactive"}:
        raise ValueError("Mode must be background or interactive")
    timeout = float(_setting(ctx, settings, "timeout_s", 600.0))
    if not 1 <= timeout <= 86400:
        raise ValueError("Timeout must be between 1 and 86400 seconds")
    release = _release(_setting(ctx, settings, "version", 0))
    working_value = _setting(ctx, settings, "working_folder", "")
    working = ctx.resolve_path_value(working_value) if str(working_value or "").strip() else None
    system = str(_setting(ctx, settings, "system", "") or "").strip()
    catalogue_id = str(uuid4())
    source_key = _source_key(source)
    document_id = str(
        uuid5(
            NAMESPACE_URL,
            f"corex-mechanical:{os.path.normcase(str(source.resolve()))}:{source_key}",
        )
    )
    if system.startswith("{"):
        selector = decode_selector(system)
        if (
            selector["kind"] != "system"
            or selector["document_id"] != document_id
            or selector["object_path"]
            or type(selector["native_id"]) is not str
            or selector["system_key"] != selector["native_id"]
        ):
            raise ValueError("mechanical.open_failed: system selector belongs to another source or kind")
        system = selector["native_id"]
    session = ctx.mechanical_sessions.open_session(
        run_id=ctx.run_id, workspace_id=ctx.workspace_id, open_node_id=ctx.node_id,
        source_path=source, target_path=ctx.target_path,
        target_iteration=ctx.target_iteration, backend_mode=mode,
        working_folder=working, register_cancel=ctx.register_cancel,
    )
    identity = {
        "schema_version": 1, "model_revision": 0,
        "producer_iteration": ctx.target_iteration, "catalogue_id": catalogue_id,
        "producer_node_id": ctx.node_id, "producer_port": "info",
        "producer_path": json.dumps(list(ctx.target_path), separators=(",", ":")),
        "run_id": ctx.run_id, "session_id": session.session_id,
        "document_id": document_id, "source_key": source_key,
        "system_key": system,
    }
    try:
        result = ctx.mechanical_sessions.operate(
            session, expected_revision=0, operation="open", timeout_sec=timeout,
            args={
                "source_path": str(source), "work_path": str(session.work_path),
                "mode": mode, "release_code": release, "system": system,
                "timeout_sec": timeout,
                "catalogue_identity": identity,
                "view_export_path": str(session.work_root / "catalogue-views.xml"),
            },
        )
    except TimeoutError as exc:
        raise TimeoutError(
            f"mechanical.operation_timeout: source={source}; release={release}; {exc}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"mechanical.open_failed: source={source}; release={release}; {exc}"
        ) from exc
    outputs = {"info": result["catalogue"]}
    if result["status"] == "system_required":
        ctx.warn("Select a Mechanical Model/system and run again.", code="mechanical.system_required")
        return outputs
    selected = str(result["system_key"])
    outputs["model"] = ctx.mechanical_sessions.register_model(
        session, document_id=document_id, source_key=source_key,
        system_key=selected, release_code=release, catalogue_id=catalogue_id,
    )
    return outputs


__all__ = ["discover_mechanical_releases", "execute_open_model"]
