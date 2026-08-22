# Purpose: Project curated DPF workflow outputs into bounded QML-safe summaries.
# Map: feature_routes/ansys_dpf_operator_viewer_transport
# Tests: tests/test_dpf_ui_summary.py
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ea_node_editor.runtime_contracts import (
    coerce_runtime_artifact_ref,
    coerce_runtime_handle_ref,
)

_MAX_TEXT_LENGTH = 180
_MAX_FACTS = 6

_RESULT_SOURCE = "dpf.workflow.result_source"
_RESULT_FIELDS = "dpf.workflow.result_fields"
_MIN_MAX_ENVELOPE = "dpf.workflow.min_max_envelope"
_TIME_HISTORY_PROBE = "dpf.workflow.time_history_probe"
_STRESS_INVARIANTS = "dpf.workflow.stress_invariants"
_FIELD_MATH = "dpf.workflow.field_math"
_TABLE_EXPORT = "dpf.workflow.table_export"

Summary = dict[str, Any]
Projector = Callable[[Mapping[str, Any], Mapping[str, Any]], Summary]


def _text(value: object, *, fallback: str = "") -> str:
    normalized = str(value if value is not None else "").strip() or fallback
    if len(normalized) <= _MAX_TEXT_LENGTH:
        return normalized
    return normalized[: _MAX_TEXT_LENGTH - 1].rstrip() + "…"


def _label(value: object, *, fallback: str = "Result") -> str:
    normalized = _text(value, fallback=fallback).replace("_", " ")
    return " ".join(part.capitalize() for part in normalized.split())


def _count(value: object) -> int:
    if isinstance(value, (Mapping, Sequence)) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


def _int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _metadata_sequence_count(metadata: Mapping[str, Any], key: str) -> int:
    explicit_count = _int(metadata.get(f"{key}_count"))
    if explicit_count > 0:
        return explicit_count
    return _count(metadata.get(key))


def _number(value: object) -> str:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(normalized):
        return ""
    return f"{normalized:.6g}"


def _handle_metadata(value: object) -> dict[str, Any]:
    runtime_ref = coerce_runtime_handle_ref(value)
    return dict(runtime_ref.metadata) if runtime_ref is not None else {}


def _artifact_text(value: object) -> str:
    runtime_ref = coerce_runtime_artifact_ref(value)
    if runtime_ref is None:
        return _text(value)
    return _text(runtime_ref.metadata.get("absolute_path") or runtime_ref.ref)


def _fact(label: str, value: object) -> dict[str, str] | None:
    normalized = _text(value)
    if not normalized:
        return None
    return {"label": _text(label), "value": normalized}


def _summary(headline: object, detail: object = "", *facts: dict[str, str] | None) -> Summary:
    return {
        "state": "ready",
        "headline": _text(headline, fallback="Completed"),
        "detail": _text(detail),
        "facts": [fact for fact in facts if fact is not None][:_MAX_FACTS],
    }


def _field_facts(
    metadata: Mapping[str, Any],
    properties: Mapping[str, Any],
    *,
    result_fallback: str = "Result",
) -> tuple[str, str, str, int]:
    result_name = _label(
        metadata.get("result_name") or properties.get("result_name"),
        fallback=result_fallback,
    )
    location = _text(metadata.get("location"), fallback="Native")
    unit = _text(metadata.get("unit"))
    field_count = max(0, _int(metadata.get("field_count")))
    return result_name, location, unit, field_count


def _project_result_source(outputs: Mapping[str, Any], _properties: Mapping[str, Any]) -> Summary:
    model_metadata = _handle_metadata(outputs.get("model"))
    result_metadata = _handle_metadata(outputs.get("result_file"))
    raw_path = outputs.get("normalized_path") or model_metadata.get("path") or result_metadata.get("path")
    path_text = _text(raw_path)
    filename = _text(Path(path_text).name if path_text else "", fallback="Result file loaded")
    set_count = _metadata_sequence_count(model_metadata, "set_ids")
    if not set_count:
        set_count = _metadata_sequence_count(result_metadata, "set_ids")
    return _summary(
        filename,
        f"{set_count} available sets" if set_count else "DPF model ready",
        _fact("File", path_text),
        _fact("Sets", set_count if set_count else ""),
    )


def _project_result_fields(outputs: Mapping[str, Any], properties: Mapping[str, Any]) -> Summary:
    metadata = _handle_metadata(outputs.get("fields"))
    result_name, location, unit, field_count = _field_facts(metadata, properties)
    detail = " · ".join(value for value in (location, unit) if value)
    return _summary(
        f"{result_name} · {field_count} field{'s' if field_count != 1 else ''}",
        detail,
        _fact("Result", result_name),
        _fact("Location", location),
        _fact("Unit", unit),
        _fact("Fields", field_count),
    )


def _project_envelope(outputs: Mapping[str, Any], properties: Mapping[str, Any]) -> Summary:
    overall = outputs.get("summary")
    overall = overall if isinstance(overall, Mapping) else {}
    peak = overall.get("max")
    peak = peak if isinstance(peak, Mapping) else {}
    result_name = _label(overall.get("result_name") or properties.get("result_name"))
    location = _text(overall.get("location"), fallback="Native")
    unit = _text(overall.get("unit"))
    value = _number(peak.get("value"))
    entity_id = _text(peak.get("entity_id"))
    set_id = _text(peak.get("set_id"))
    headline = " ".join(item for item in ("Max", value, unit) if item)
    detail = " · ".join(
        item for item in (f"Entity {entity_id}" if entity_id else "", f"Set {set_id}" if set_id else "") if item
    )
    return _summary(
        headline,
        detail,
        _fact("Result", result_name),
        _fact("Location", location),
        _fact("Entity", entity_id),
        _fact("Set", set_id),
    )


def _project_time_history(outputs: Mapping[str, Any], properties: Mapping[str, Any]) -> Summary:
    metadata = _handle_metadata(outputs.get("series"))
    result_name, _location, unit, field_count = _field_facts(metadata, properties)
    entity_count = _metadata_sequence_count(metadata, "entity_ids") or field_count
    set_count = _count(outputs.get("time_values")) or _metadata_sequence_count(
        metadata,
        "time_values",
    )
    row_count = _count(outputs.get("table"))
    curve_count = field_count or entity_count
    return _summary(
        f"{curve_count} curve{'s' if curve_count != 1 else ''} · {row_count} rows",
        " · ".join(value for value in (result_name, unit) if value),
        _fact("Entities", entity_count),
        _fact("Sets", set_count),
        _fact("Curves", curve_count),
        _fact("Rows", row_count),
    )


def _project_stress(outputs: Mapping[str, Any], properties: Mapping[str, Any]) -> Summary:
    metadata = _handle_metadata(outputs.get("fields"))
    operation = _label(metadata.get("operation") or properties.get("invariant"), fallback="Stress")
    _result_name, location, unit, field_count = _field_facts(
        metadata,
        properties,
        result_fallback="Stress",
    )
    return _summary(
        " · ".join(value for value in (operation, location, unit) if value),
        f"{field_count} field{'s' if field_count != 1 else ''}",
        _fact("Invariant", operation),
        _fact("Location", location),
        _fact("Unit", unit),
        _fact("Fields", field_count),
    )


def _project_field_math(outputs: Mapping[str, Any], properties: Mapping[str, Any]) -> Summary:
    metadata = _handle_metadata(outputs.get("fields"))
    operation = _label(metadata.get("operation") or properties.get("operation"), fallback="Field Math")
    _result_name, location, unit, field_count = _field_facts(metadata, properties)
    return _summary(
        " · ".join(value for value in (operation, location, unit) if value),
        f"{field_count} field{'s' if field_count != 1 else ''}",
        _fact("Operation", operation),
        _fact("Location", location),
        _fact("Unit", unit),
        _fact("Fields", field_count),
    )


def _project_table_export(outputs: Mapping[str, Any], _properties: Mapping[str, Any]) -> Summary:
    row_count = _count(outputs.get("table"))
    csv_path = _artifact_text(outputs.get("csv"))
    return _summary(
        f"{row_count} row{'s' if row_count != 1 else ''} exported",
        Path(csv_path).name if csv_path else "Memory output",
        _fact("Rows", row_count),
        _fact("CSV", csv_path),
    )


_PROJECTORS: dict[str, Projector] = {
    _RESULT_SOURCE: _project_result_source,
    _RESULT_FIELDS: _project_result_fields,
    _MIN_MAX_ENVELOPE: _project_envelope,
    _TIME_HISTORY_PROBE: _project_time_history,
    _STRESS_INVARIANTS: _project_stress,
    _FIELD_MATH: _project_field_math,
    _TABLE_EXPORT: _project_table_export,
}


def project_dpf_workflow_summary(
    node_type_id: object,
    outputs: Mapping[str, Any],
    properties: Mapping[str, Any] | None = None,
) -> Summary | None:
    """Return a compact summary for curated non-viewer DPF workflow nodes."""

    projector = _PROJECTORS.get(str(node_type_id or "").strip())
    if projector is None or not isinstance(outputs, Mapping):
        return None
    return projector(outputs, properties if isinstance(properties, Mapping) else {})


__all__ = ["project_dpf_workflow_summary"]
