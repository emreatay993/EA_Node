# Purpose: Build bounded data-only Mechanical discovery rows on the native owner thread.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_open_model.py

from __future__ import annotations

import json
from typing import Any

from ea_node_editor.addons.mechanical.contracts import CATALOGUE_COLUMNS, encode_selector


def _blank(identity: dict[str, Any], kind: str) -> dict[str, Any]:
    row = {name: None for name in CATALOGUE_COLUMNS}
    row.update({name: "" for name in CATALOGUE_COLUMNS if name not in {
        "schema_version", "model_revision", "producer_iteration", "object_id",
        "parent_id", "analysis_id", "scalar_value", "has_tabular_data",
        "row_count", "column_count", "view_index", "omitted_rows",
        "catalogue_complete", "related_object_id", "scope_count", "body_hidden",
    }})
    row.update(identity)
    row["record_kind"] = kind
    return row


def _safe(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name)
    except Exception:  # native metadata getters are independently fallible
        return default


def _type_name(obj: Any) -> str:
    try:
        return str(obj.GetType().FullName)
    except Exception:
        return type(obj).__name__


def _path(obj: Any) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    while obj is not None and id(obj) not in seen:
        seen.add(id(obj))
        name = str(_safe(obj, "Name", "")).strip()
        if name:
            parts.append(name)
        obj = _safe(obj, "Parent")
    return "/".join(reversed(parts))


def collect_catalogue_rows(
    *, tree: Any, graphics: Any, identity: dict[str, Any], systems: list[dict[str, str]],
    status: str = "opened", message: str = "",
) -> list[dict[str, Any]]:
    """Read descriptors only; never inspect table cells or execute authored scripts."""
    rows: list[dict[str, Any]] = []
    metadata_errors: list[str] = []
    summary = _blank(identity, "session")
    summary.update(status=status, message=message, catalogue_complete=True, omitted_rows=0)
    rows.append(summary)
    for system in systems:
        row = _blank(identity, "system")
        key, label = str(system["key"]), str(system["label"])
        row.update(system_key=key, system_label=label)
        row["selector_code"] = encode_selector(
            "system", document_id=identity["document_id"], system_key=key,
            object_path="", native_id=key,
        )
        rows.append(row)
    if tree is None:
        for row in rows:
            row.pop("view_export_path", None)
        return rows
    objects = list(tree.AllObjects)
    analysis_ids = {
        int(_safe(item, "ObjectId")): int(_safe(item, "ObjectId"))
        for item in objects if ".Analysis" in _type_name(item)
    }
    for obj in objects:
        object_id = int(_safe(obj, "ObjectId", -1))
        if object_id < 0:
            continue
        parent = _safe(obj, "Parent")
        parent_id = _safe(parent, "ObjectId") if parent is not None else None
        parent_id = int(parent_id) if parent_id is not None else None
        object_path = _path(obj) or str(object_id)
        analysis_id = object_id if object_id in analysis_ids else None
        cursor = parent
        while analysis_id is None and cursor is not None:
            candidate = _safe(cursor, "ObjectId")
            if candidate is not None and int(candidate) in analysis_ids:
                analysis_id = int(candidate)
            cursor = _safe(cursor, "Parent")
        row = _blank(identity, "object")
        row.update(
            object_id=object_id, parent_id=parent_id, analysis_id=analysis_id,
            object_path=object_path, display_name=str(_safe(obj, "Name", "")),
            api_type=_type_name(obj),
        )
        row["selector_code"] = encode_selector(
            "object", document_id=identity["document_id"],
            system_key=identity["system_key"], object_path=object_path,
            native_id=object_id,
        )
        rows.append(row)
        table = _safe(obj, "TabularData")
        if table is not None:
            try:
                keys = [str(key) for key in table.Keys]
            except Exception:
                keys = []
            table_key = f"{object_id}:tabular_data"
            trow = _blank(identity, "table")
            trow.update(
                object_id=object_id, analysis_id=analysis_id,
                object_path=object_path, display_name=str(_safe(obj, "Name", "")),
                api_type=_type_name(obj), table_key=table_key,
                table_family="api_native", definition_kind="ITable",
                row_count=None, column_count=len(keys),
            )
            trow["selector_code"] = encode_selector(
                "table", document_id=identity["document_id"],
                system_key=identity["system_key"], object_path=object_path,
                native_id=table_key,
            )
            rows.append(trow)
        try:
            properties = list(obj.VisibleProperties)
        except Exception as exc:
            properties = []
            metadata_errors.append(f"{object_path}: VisibleProperties: {type(exc).__name__}")
        for prop in properties:
            key = str(_safe(prop, "APIName", "")).strip()
            if not key:
                continue
            prow = _blank(identity, "property")
            try:
                display = str(prop.StringValue)
                value_status = "available"
            except Exception as exc:
                display, value_status = "", f"unreadable: {type(exc).__name__}"
            internal = _safe(prop, "InternalValue")
            has_definition = internal is not None and hasattr(internal, "Inputs") and hasattr(internal, "Output")
            prow.update(
                object_id=object_id, analysis_id=analysis_id, object_path=object_path,
                display_name=str(_safe(obj, "Name", "")), api_type=_type_name(obj),
                property_key=key, property_caption=str(_safe(prop, "Caption", key)),
                display_value=display,
                definition_kind="scalar" if value_status == "available" else value_status,
                has_tabular_data=has_definition,
            )
            if has_definition:
                inputs = _safe(internal, "Inputs", []) or []
                prow.update(
                    table_key=f"{object_id}:{key}:field",
                    table_family="field_definition",
                    row_count=None,
                    column_count=len(list(inputs)) + 1,
                )
            prow["selector_code"] = encode_selector(
                "property", document_id=identity["document_id"],
                system_key=identity["system_key"], object_path=object_path,
                native_id=key,
            )
            rows.append(prow)
            if has_definition:
                table_key = f"{object_id}:{key}:field"
                trow = _blank(identity, "table")
                inputs = _safe(internal, "Inputs", []) or []
                trow.update(
                    object_id=object_id, analysis_id=analysis_id,
                    object_path=object_path, display_name=str(_safe(obj, "Name", "")),
                    api_type=_type_name(obj), property_key=key,
                    property_caption=str(_safe(prop, "Caption", key)),
                    table_key=table_key, table_family="field_definition",
                    definition_kind="Field", row_count=None,
                    column_count=len(list(inputs)) + 1,
                )
                trow["selector_code"] = encode_selector(
                    "table", document_id=identity["document_id"],
                    system_key=identity["system_key"], object_path=object_path,
                    native_id=table_key,
                )
                rows.append(trow)
        relations = []
        coordinate = _safe(obj, "CoordinateSystem")
        if coordinate is not None:
            relations.append(("coordinate_system", "assignment", coordinate, "", "", None, None))
        source_id = _safe(obj, "ImportableObjectSourceId")
        if source_id not in {None, ""}:
            relations.append(("source_model", "source", None, str(source_id), "", None, None))
        hidden = _safe(obj, "Hidden")
        if type(hidden) is bool:
            relations.append(("body_visibility", "body", None, "", "", hidden, None))
        if analysis_id is not None:
            analysis = next((item for item in objects if int(_safe(item, "ObjectId", -1)) == analysis_id), None)
            relations.append(("environment", "owner", analysis, "", "", None, None))
        for attribute, role in (("Location", "primary"), ("SourceLocation", "source"), ("TargetLocation", "target")):
            if not hasattr(obj, attribute):
                continue
            try:
                scope = getattr(obj, attribute)
                count = _safe(scope, "ScopeCount")
                if count is None:
                    count = len(list(_safe(scope, "Ids", []) or []))
                kind = "empty_explicit_scope" if not count else "explicit_scope"
                relations.append(("scope", role, scope if hasattr(scope, "ObjectId") else None, "", kind, None, count))
            except Exception:
                relations.append(("scope", role, None, "", "", None, None))
        for relation_kind, role, related, raw_source, scope_kind, body_hidden, scope_count in relations:
            rrow = _blank(identity, "relation")
            related_id = _safe(related, "ObjectId") if related is not None else None
            related_id = int(related_id) if related_id is not None else None
            rrow.update(
                object_id=object_id, analysis_id=analysis_id,
                object_path=object_path, display_name=str(_safe(obj, "Name", "")),
                api_type=_type_name(obj), relation_kind=relation_kind,
                relation_role=role, related_label=str(_safe(related, "Name", "")),
                raw_source_id=raw_source, scope_kind=scope_kind,
                relation_status="available" if related is not None or raw_source or body_hidden is not None or scope_kind else "unavailable",
                related_object_id=related_id,
                scope_count=scope_count,
                body_hidden=body_hidden,
            )
            rows.append(rrow)
        existing_relation_kinds = {item[0] for item in relations}
        for relation_kind in ("coordinate_system", "source_model", "body_visibility", "environment", "scope"):
            if relation_kind in existing_relation_kinds:
                continue
            rrow = _blank(identity, "relation")
            status = "available" if relation_kind == "source_model" else "not_applicable"
            rrow.update(
                object_id=object_id, analysis_id=analysis_id,
                object_path=object_path, display_name=str(_safe(obj, "Name", "")),
                api_type=_type_name(obj), relation_kind=relation_kind,
                relation_role="current_document" if relation_kind == "source_model" else "",
                related_label=(identity["system_key"] or identity["source_key"] if relation_kind == "source_model" else ""),
                relation_status=status,
            )
            rows.append(rrow)
    current = _blank(identity, "view")
    current.update(view_key="current", view_name="Current")
    current["selector_code"] = encode_selector(
        "view", document_id=identity["document_id"],
        system_key=identity["system_key"], object_path="", native_id="current",
    )
    rows.append(current)
    try:
        manager = graphics.ModelViewManager
        count = int(manager.NumberOfViews)
        # Names are exported by the documented API; numeric XML fields are ignored.
        export_path = identity["view_export_path"]
        manager.ExportModelViews(export_path)
        import xml.etree.ElementTree as ET
        views = [child.attrib.get("Name") for child in ET.parse(export_path).getroot()
                 if child.tag.split("}")[-1] == "ModelView"]
        if len(views) != count or any(name is None for name in views):
            raise ValueError("saved-view export schema/count is invalid")
        for index, name in enumerate(views):
            row = _blank(identity, "view")
            key = f"saved:{index}"
            row.update(view_index=index, view_key=key, view_name=str(name))
            row["selector_code"] = encode_selector(
                "view", document_id=identity["document_id"],
                system_key=identity["system_key"], object_path="", native_id=index,
            )
            rows.append(row)
    except Exception as exc:
        metadata_errors.append(f"saved views: {type(exc).__name__}: {exc}")
        summary["message"] = (
            summary["message"] + "; " if summary["message"] else ""
        ) + f"view metadata unreadable: {type(exc).__name__}: {exc}"
    unique: list[dict[str, Any]] = []
    selectors: set[str] = set()
    for row in rows:
        row.pop("view_export_path", None)
        selector = row["selector_code"]
        if selector and selector in selectors:
            continue
        if selector:
            selectors.add(selector)
        unique.append(row)
    omitted = max(0, len(unique) - 100_000)
    unique = unique[:100_000]
    while len(rows_json(unique).encode("utf-8")) > 64 * 1024 * 1024 and len(unique) > 1:
        unique.pop()
        omitted += 1
    remote_errors = list(getattr(tree, "metadata_errors", ())) if tree is not None else []
    metadata_errors.extend(remote_errors)
    unique[0]["catalogue_complete"] = omitted == 0 and not metadata_errors
    unique[0]["omitted_rows"] = omitted if not metadata_errors else None
    if metadata_errors:
        unique[0]["message"] = "; ".join(metadata_errors[:20])
    return unique


def rows_json(rows: list[dict[str, Any]]) -> str:
    return json.dumps(rows, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


__all__ = ["collect_catalogue_rows", "rows_json"]
