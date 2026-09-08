# Purpose: Execute Mechanical Open, Search, table, camera, and image operations through the run-owned session.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_open_model.py, tests/mechanical_catalogue/test_search_tree.py, tests/mechanical_catalogue/test_result_tables.py, tests/mechanical_catalogue/test_image_export.py

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from ea_node_editor.addons.mechanical.contracts import (
    CAMERA_VIEW_TYPE_ID,
    OBJECT_TYPE_ID,
    PROPERTY_TYPE_ID,
    decode_selector,
    validate_camera_view,
    validate_object,
    validate_property,
)
from ea_node_editor.addons.mechanical.graphics import (
    IMAGE_CAPTURE_LIMIT,
    IMAGE_MAX_PIXELS,
    build_image_outputs,
    preflight_image_destinations,
    publish_image_batch,
    render_image_filenames,
)
from ea_node_editor.addons.mechanical.session import StaleMechanicalModelError
from ea_node_editor.nodes.execution_context import NodeInputNotReadyError
from ea_node_editor.runtime_contracts import ImageValue, RuntimeHandleRef, TableValue, TypedInlineValue


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


def _search_selector(query: str, metadata) -> dict[str, object] | None:
    try:
        decoded = json.loads(query)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict) or not {
        "schema_version", "kind", "document_id", "system_key", "object_path", "native_id"
    } & set(decoded):
        return None
    selector = decode_selector(query)
    if (
        selector["kind"] not in {"object", "property"}
        or selector["document_id"] != metadata["document_id"]
        or selector["system_key"] != metadata["system_key"]
    ):
        raise ValueError("mechanical.selector_missing: query selector belongs to another model or kind")
    return selector


def execute_search_tree(ctx, model=None, settings=None):
    if model is None:
        raise NodeInputNotReadyError("Model requires a live Mechanical model from this run")
    if not isinstance(model, RuntimeHandleRef):
        raise TypeError("Search Mechanical Tree requires a Mechanical Model")
    try:
        session = ctx.mechanical_sessions.admit_model(
            model, run_id=ctx.run_id, workspace_id=ctx.workspace_id
        )
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    filter_code = str(_setting(ctx, settings, "filter", "name"))
    if filter_code not in {
        "name", "tag", "type", "state", "coordinate_system", "model", "graphics",
        "environment", "scoping", "property_name", "property_value",
    }:
        raise ValueError(f"Unknown Mechanical search filter: {filter_code}")
    query = _setting(ctx, settings, "query", "")
    if type(query) is not str:
        raise TypeError("Mechanical search Query must be text")
    match_mode = str(_setting(ctx, settings, "match", "contains"))
    if match_mode not in {"contains", "exact"}:
        raise ValueError("Mechanical search Match must be contains or exact")
    flags = {}
    for key in ("case_sensitive", "include_hidden_properties", "invert"):
        value = _setting(ctx, settings, key, False)
        if type(value) is not bool:
            raise TypeError(f"Mechanical search {key} must be Boolean")
        flags[key] = value
    metadata = model.metadata
    selector = _search_selector(query, metadata)
    identity = {
        field: metadata[field]
        for field in (
            "run_id", "session_id", "document_id", "source_key", "system_key", "model_revision"
        )
    }
    try:
        result = ctx.mechanical_sessions.operate(
            session,
            expected_revision=metadata["model_revision"],
            operation="search",
            args={
                "filter": filter_code,
                "query": query,
                "match": match_mode,
                **flags,
                "identity": identity,
                "typed_selector": selector,
            },
        )["search"]
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    except Exception as exc:
        message = str(exc)
        if any(
            code in message
            for code in (
                "mechanical.search_incomplete:",
                "mechanical.capacity_exceeded:",
                "mechanical.selector_missing:",
            )
        ):
            raise ValueError(message[message.index("mechanical.") :]) from exc
        raise RuntimeError(f"mechanical.operation_failed: Search Mechanical Tree: {message}") from exc
    if (
        not isinstance(result, dict)
        or set(result) != {"objects", "properties", "details"}
        or type(result["objects"]) is not list
        or type(result["properties"]) is not list
        or type(result["details"]) is not TableValue
    ):
        raise RuntimeError("mechanical.operation_failed: Search returned an invalid result")
    for value in result["objects"]:
        validate_object(value)
        if any(value.payload[field] != identity[field] for field in identity):
            raise ValueError("mechanical.cross_session_reference: Search object belongs to another Model")
    for value in result["properties"]:
        validate_property(value)
        if any(value.payload[field] != identity[field] for field in identity):
            raise ValueError("mechanical.cross_session_reference: Search property belongs to another Model")
    return {
        **result,
        "found": bool(result["objects"] or result["properties"]),
    }


def _table_selector(value: str, metadata: Mapping[str, object]):
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict) or not {
        "schema_version", "kind", "document_id", "system_key", "object_path", "native_id"
    } & set(decoded):
        return None
    selector = decode_selector(value)
    if (
        selector["kind"] != "table"
        or selector["document_id"] != metadata["document_id"]
        or selector["system_key"] != metadata["system_key"]
        or type(selector["native_id"]) is not str
    ):
        raise ValueError(
            "mechanical.selector_missing: Table / property selector belongs to another model or kind"
        )
    return {
        "object_path": selector["object_path"],
        "native_id": selector["native_id"],
    }


def execute_fea_table(ctx, model=None, source=None, settings=None):
    if model is None:
        raise NodeInputNotReadyError("Model requires a live Mechanical model from this run")
    if not isinstance(model, RuntimeHandleRef):
        raise TypeError("FEA Table requires a Mechanical Model")
    try:
        session = ctx.mechanical_sessions.admit_model(
            model, run_id=ctx.run_id, workspace_id=ctx.workspace_id
        )
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    if source is None:
        raise NodeInputNotReadyError("Source requires a Mechanical Object or Property")
    if type(source) not in {list, tuple}:
        raise TypeError("FEA Table Source must be a list")
    if not source:
        raise ValueError("FEA Table Source must contain at least one Object or Property")
    metadata = model.metadata
    identity_fields = (
        "run_id", "session_id", "document_id", "source_key", "system_key", "model_revision"
    )
    sources = []
    for value in source:
        if type(value) is not TypedInlineValue or value.data_type_id not in {
            OBJECT_TYPE_ID, PROPERTY_TYPE_ID
        }:
            raise TypeError("FEA Table Source accepts only Mechanical Object or Property values")
        (validate_object if value.data_type_id == OBJECT_TYPE_ID else validate_property)(value)
        if any(value.payload[field] != metadata[field] for field in identity_fields):
            raise ValueError(
                "mechanical.cross_session_reference: FEA Table source belongs to another Model"
            )
        sources.append(
            {
                "kind": "object" if value.data_type_id == OBJECT_TYPE_ID else "property",
                "object_id": value.payload["object_id"],
                "object_path": value.payload["object_path"],
                "property_key": value.payload.get("property_key", ""),
            }
        )
    family = _setting(ctx, settings, "family", "auto")
    if family not in {
        "auto", "model_definition", "result_history_summary", "spatial_samples",
        "supported_worksheet",
    }:
        raise ValueError(f"Unknown Mechanical table family: {family}")
    if family not in {"auto", "model_definition"} and any(
        value.data_type_id == PROPERTY_TYPE_ID for value in source
    ):
        raise ValueError(
            f"mechanical.table_unsupported: family {family!r} requires a Mechanical Object source"
        )
    table = _setting(ctx, settings, "table", "")
    component = _setting(ctx, settings, "component", "all")
    units = _setting(ctx, settings, "units", "source")
    if type(table) is not str or type(component) is not str:
        raise TypeError("FEA Table Table / property and Component must be text")
    if not component:
        raise ValueError("FEA Table Component must be 'all' or an exact component")
    if units not in {"source", "si"}:
        raise ValueError("FEA Table Units must be source or si")
    selector = _table_selector(table, metadata) if table else None
    result_sources = [str(value.payload.get("api_type", "")) for value in source]
    sets_active = family in {"result_history_summary", "spatial_samples"} or (
        family == "auto"
        and any(".Results." in value or value.endswith(".Solution") for value in result_sources)
    )
    sets: list[int] = []
    if sets_active:
        raw_sets = _setting(ctx, settings, "sets", [])
        if type(raw_sets) not in {list, tuple}:
            raise TypeError("FEA Table Rows / sets must be an integer list")
        if any(type(value) is not int or value <= 0 for value in raw_sets) or len(set(raw_sets)) != len(raw_sets):
            raise ValueError("FEA Table Rows / sets must contain unique positive stored-set IDs")
        sets = list(raw_sets)
    try:
        args = {
            "sources": sources,
            "family": family,
            "table": "" if selector is not None else table,
            "table_selector": selector,
            "component": component,
            "units": units,
            "native_output_path": str(
                session.work_root / f"native-definitions-{uuid4().hex}.json"
            ),
        }
        if sets_active:
            args["sets"] = sets
        response = ctx.mechanical_sessions.operate(
            session,
            expected_revision=metadata["model_revision"],
            operation="definition_tables",
            args=args,
        )
        result = response["definition_tables"]
        warnings = response.get("warnings", [])
        if type(warnings) is not list or any(type(value) is not str for value in warnings):
            raise RuntimeError("Mechanical table diagnostics are invalid")
        warn = getattr(ctx, "warn", None)
        if callable(warn):
            for warning in warnings:
                warn(warning, code="mechanical.result_state_drift")
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    except Exception as exc:
        message = str(exc)
        if "Mechanical owner request exceeds encoded size limit" in message:
            raise ValueError(
                "mechanical.capacity_exceeded: source selection exceeds the owner request limit; "
                "narrow Source, Table / property, or Component"
            ) from exc
        for code in (
            "mechanical.table_unsupported:",
            "mechanical.capacity_exceeded:",
            "mechanical.selector_missing:",
            "mechanical.selector_ambiguous:",
            "mechanical.results_missing:",
            "mechanical.restore_failed:",
            "mechanical.capability_unproved:",
        ):
            if code in message:
                raise ValueError(message[message.index(code) :]) from exc
        raise RuntimeError(f"mechanical.operation_failed: FEA Table: {message}") from exc
    if (
        not isinstance(result, dict)
        or set(result) != {"tables", "definitions"}
        or type(result["tables"]) is not list
        or any(type(value) is not TableValue for value in result["tables"])
        or type(result["definitions"]) is not TableValue
    ):
        raise RuntimeError("mechanical.operation_failed: FEA Table returned invalid values")
    return result


def execute_camera_views(ctx, model=None, settings=None):
    if model is None:
        raise NodeInputNotReadyError(
            "Model requires a live Mechanical model from this run"
        )
    if not isinstance(model, RuntimeHandleRef):
        raise TypeError("Mechanical Camera Views requires a Mechanical Model")
    try:
        session = ctx.mechanical_sessions.admit_model(
            model, run_id=ctx.run_id, workspace_id=ctx.workspace_id
        )
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    include = _setting(ctx, settings, "include", "saved_and_current")
    if include not in {"saved_and_current", "saved", "current"}:
        raise ValueError("Mechanical Camera Views Include is invalid")
    metadata = model.metadata
    identity = {
        field: metadata[field]
        for field in (
            "run_id",
            "session_id",
            "document_id",
            "source_key",
            "system_key",
            "model_revision",
        )
    }
    try:
        result = ctx.mechanical_sessions.operate(
            session,
            expected_revision=metadata["model_revision"],
            operation="camera_views",
            args={
                "include": include,
                "identity": identity,
                "export_path": str(
                    session.work_root / f"camera-views-{uuid4().hex}.xml"
                ),
                "restore_name": f"COREX restore {uuid4().hex}",
            },
        )["camera_views"]
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    except Exception as exc:
        message = str(exc)
        for code in (
            "mechanical.camera_schema_invalid:",
            "mechanical.table_unsupported:",
            "mechanical.capacity_exceeded:",
            "mechanical.restore_failed:",
            "mechanical.capability_unproved:",
        ):
            if code in message:
                raise ValueError(message[message.index(code) :]) from exc
        raise RuntimeError(
            f"mechanical.operation_failed: Mechanical Camera Views: {message}"
        ) from exc
    if (
        not isinstance(result, dict)
        or set(result) != {"views", "names", "details"}
        or type(result["views"]) is not list
        or type(result["names"]) is not list
        or len(result["views"]) != len(result["names"])
        or type(result["details"]) is not TableValue
        or result["details"].row_count != len(result["views"])
    ):
        raise RuntimeError(
            "mechanical.operation_failed: Mechanical Camera Views returned invalid values"
        )
    for index, value in enumerate(result["views"]):
        if (
            type(value) is not TypedInlineValue
            or value.data_type_id != CAMERA_VIEW_TYPE_ID
        ):
            raise RuntimeError(
                "mechanical.operation_failed: Mechanical Camera Views returned an invalid camera"
            )
        validate_camera_view(value)
        if any(value.payload[field] != identity[field] for field in identity):
            raise ValueError(
                "mechanical.cross_session_reference: Camera view belongs to another Model"
            )
        if value.payload["name"] != result["names"][index]:
            raise RuntimeError(
                "mechanical.operation_failed: Camera names do not match their views"
            )
    return result


def _image_values(value: object, label: str) -> list[object]:
    if value is None:
        return []
    if type(value) not in {list, tuple}:
        raise TypeError(f"Export Mechanical Image {label} must be a list")
    return list(value)


def _image_selector(value: object, metadata: Mapping[str, Any], *, camera: bool) -> tuple[dict[str, Any], str]:
    identity_fields = (
        "run_id", "session_id", "document_id", "source_key", "system_key", "model_revision"
    )
    if type(value) is TypedInlineValue:
        expected = CAMERA_VIEW_TYPE_ID if camera else OBJECT_TYPE_ID
        validator = validate_camera_view if camera else validate_object
        if value.data_type_id != expected or not validator(value):
            raise TypeError(
                "Export Mechanical Image accepts only Mechanical CameraView or Text values"
                if camera
                else "Export Mechanical Image accepts only Mechanical Object or Text values"
            )
        if any(value.payload[field] != metadata[field] for field in identity_fields):
            raise ValueError(
                "mechanical.cross_session_reference: image selector belongs to another Model"
            )
        if camera:
            return (
                {
                    "kind": "current" if value.payload["kind"] == "current" else "typed",
                    "index": value.payload["index"],
                    "name": value.payload["name"],
                },
                str(value.payload["name"]),
            )
        return (
            {
                "kind": "typed",
                "object_id": value.payload["object_id"],
                "object_path": value.payload["object_path"],
            },
            str(value.payload["display_name"]),
        )
    if type(value) is not str or not value.strip():
        raise TypeError("Export Mechanical Image selectors must be non-empty Text or typed values")
    text = value.strip()
    try:
        decoded = decode_selector(text) if text.startswith("{") else None
    except (TypeError, ValueError) as exc:
        raise ValueError("mechanical.selector_missing: image selector code is invalid") from exc
    if decoded is not None:
        expected_kind = "view" if camera else "object"
        if (
            decoded["kind"] != expected_kind
            or decoded["document_id"] != metadata["document_id"]
            or decoded["system_key"] != metadata["system_key"]
        ):
            raise ValueError("mechanical.selector_missing: image selector belongs to another model or kind")
        if camera:
            if decoded["native_id"] == "current":
                return {"kind": "current"}, "Current view"
            if type(decoded["native_id"]) is not int:
                raise ValueError("mechanical.selector_missing: saved view selector has an invalid index")
            return {"kind": "typed", "index": decoded["native_id"], "name": None}, f"view_{decoded['native_id']}"
        if type(decoded["native_id"]) is not int or not decoded["object_path"]:
            raise ValueError("mechanical.selector_missing: object selector has an invalid identity")
        return {
            "kind": "typed",
            "object_id": decoded["native_id"],
            "object_path": decoded["object_path"],
        }, decoded["object_path"].rsplit("/", 1)[-1]
    if camera and text == "Current view":
        return {"kind": "current"}, text
    return {"kind": "text", "text": text}, text.rsplit("/", 1)[-1]


def execute_image_export(ctx, model=None, objects=None, views=None, settings=None):
    models = _image_values(model, "Model")
    if not models:
        raise NodeInputNotReadyError("Model requires a live Mechanical model from this run")
    if len(models) != 1:
        raise ValueError(
            "Export Mechanical Image requires exactly one Model per matched branch; apply Graft to multiple Model items"
        )
    model_value = models[0]
    if not isinstance(model_value, RuntimeHandleRef):
        raise TypeError("Export Mechanical Image requires a Mechanical Model")
    try:
        session = ctx.mechanical_sessions.admit_model(
            model_value, run_id=ctx.run_id, workspace_id=ctx.workspace_id
        )
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    metadata = model_value.metadata
    raw_objects = _image_values(objects, "Objects")
    raw_views = _image_values(views, "Views")
    object_selectors, object_labels = zip(
        *(_image_selector(value, metadata, camera=False) for value in raw_objects),
        strict=True,
    ) if raw_objects else (({"kind": "current"},), ("Current display",))
    view_selectors, view_labels = zip(
        *(_image_selector(value, metadata, camera=True) for value in raw_views),
        strict=True,
    ) if raw_views else (({"kind": "current"},), ("Current view",))
    capture_count = len(object_selectors) * len(view_selectors)
    if capture_count > IMAGE_CAPTURE_LIMIT:
        raise ValueError(
            f"mechanical.capacity_exceeded: requested {capture_count} image captures; maximum is {IMAGE_CAPTURE_LIMIT}"
        )
    width = _setting(ctx, settings, "width", 1600)
    height = _setting(ctx, settings, "height", 1000)
    if type(width) is not int or type(height) is not int or not 64 <= width <= 8192 or not 64 <= height <= 8192:
        raise ValueError("Mechanical image Width and Height must be integers from 64 to 8192")
    if width * height > IMAGE_MAX_PIXELS:
        raise ValueError(
            f"mechanical.capacity_exceeded: requested {width * height} pixels; maximum is {IMAGE_MAX_PIXELS}"
        )
    background = _setting(ctx, settings, "background", "white")
    if background not in {"white", "model"}:
        raise ValueError("Mechanical image Background must be white or model")
    fit_view = _setting(ctx, settings, "fit_view", False)
    if type(fit_view) is not bool:
        raise TypeError("Mechanical image Fit view must be Boolean")
    identity = {
        field: metadata[field]
        for field in (
            "run_id", "session_id", "document_id", "source_key", "system_key", "model_revision"
        )
    }
    args = {
        "objects": list(object_selectors),
        "views": list(view_selectors),
        "width": width,
        "height": height,
        "background": background,
        "fit_view": fit_view,
        "output_paths": [
            str(session.work_root / f"viewport-{uuid4().hex}.png")
            for _ in range(capture_count)
        ],
        "view_export_path": str(session.work_root / f"image-views-{uuid4().hex}.xml"),
        "restore_name": f"COREX restore {uuid4().hex}",
        "preflight_only": True,
    }
    try:
        preflight = ctx.mechanical_sessions.operate(
            session,
            expected_revision=metadata["model_revision"],
            operation="image_export",
            args=args,
        )["image_preflight"]
        preflight_records = preflight.get("images") if isinstance(preflight, dict) else None
        if type(preflight_records) is not list or len(preflight_records) != capture_count:
            raise RuntimeError("Mechanical image selector preflight returned an invalid result")
        record_fields = {
            "object_index", "object_name", "object_path", "object_id",
            "view_ordinal", "view_name", "view_kind", "view_index",
        }
        if any(
            not isinstance(record, Mapping)
            or set(record) != record_fields
            or record["object_index"] != ordinal // len(view_selectors)
            or record["view_ordinal"] != ordinal % len(view_selectors)
            or type(record["object_name"]) is not str
            or not record["object_name"]
            or type(record["view_name"]) is not str
            or not record["view_name"]
            for ordinal, record in enumerate(preflight_records)
        ):
            raise RuntimeError("Mechanical image selector preflight returned invalid records")
        labels = [
            (record["object_name"], record["view_name"])
            for record in preflight_records
        ]
        folder_value = _setting(ctx, settings, "folder", "")
        destinations: list[Path] = []
        if str(folder_value or "").strip():
            overwrite = _setting(ctx, settings, "overwrite", False)
            if type(overwrite) is not bool:
                raise TypeError("Mechanical image Overwrite must be Boolean")
            names = render_image_filenames(
                _setting(ctx, settings, "file_name", "{object}_{view}.png"),
                labels,
                view_count=len(view_selectors),
            )
            folder = ctx.resolve_path_value(folder_value)
            if folder is None:
                raise ValueError("Mechanical image Folder could not be resolved")
            destinations = preflight_image_destinations(folder, names, overwrite=overwrite)
        else:
            overwrite = False
        args["preflight_only"] = False
        response = ctx.mechanical_sessions.operate(
            session,
            expected_revision=metadata["model_revision"],
            operation="image_export",
            args=args,
        )
        result = response["image_export"]
        warnings = response.get("warnings", [])
        if type(warnings) is not list or any(type(value) is not str for value in warnings):
            raise RuntimeError("Mechanical image diagnostics are invalid")
        warn = getattr(ctx, "warn", None)
        if callable(warn):
            for warning in warnings:
                warn(warning, code="mechanical.result_state_drift")
    except StaleMechanicalModelError as exc:
        raise ValueError(f"mechanical.stale_reference: {exc}") from exc
    except Exception as exc:
        message = str(exc)
        for code in (
            "mechanical.selector_missing:",
            "mechanical.selector_ambiguous:",
            "mechanical.camera_schema_invalid:",
            "mechanical.table_unsupported:",
            "mechanical.capacity_exceeded:",
            "mechanical.restore_failed:",
            "mechanical.capability_unproved:",
        ):
            if code in message:
                raise ValueError(message[message.index(code):]) from exc
        raise RuntimeError(f"mechanical.operation_failed: Export Mechanical Image: {message}") from exc
    records = result.get("images") if isinstance(result, dict) else None
    if type(records) is not list or len(records) != capture_count:
        raise RuntimeError("mechanical.operation_failed: image capture returned an invalid result")
    images = []
    for ordinal, record in enumerate(records):
        if (
            not isinstance(record, Mapping)
            or set(record) != record_fields | {"image"}
            or {key: record[key] for key in record_fields} != dict(preflight_records[ordinal])
            or type(record["image"]) is not ImageValue
            or (record["image"].width, record["image"].height) != (width, height)
        ):
            raise RuntimeError("mechanical.operation_failed: image capture returned invalid records")
        images.append(record["image"])
    if len(images) != capture_count:
        raise RuntimeError("mechanical.operation_failed: image capture returned invalid records")
    if destinations:
        publish_image_batch(images, destinations, overwrite=overwrite)
    return build_image_outputs(
        records,
        identity=identity,
        target_path=tuple(ctx.target_path),
        target_iteration=int(ctx.target_iteration),
        file_paths=destinations,
    )


__all__ = [
    "discover_mechanical_releases",
    "execute_camera_views",
    "execute_fea_table",
    "execute_image_export",
    "execute_open_model",
    "execute_search_tree",
]
