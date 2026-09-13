# Purpose: Transport session-only plots through a strict bounded data-only schema.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_value.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, fields
from typing import Any

from ea_node_editor.common.payload_tools import validate_payload_fields
from ea_node_editor.runtime_contracts.image_value import ImageValue, IMAGE_VALUE_MAX_ENCODED_BYTES
from ea_node_editor.runtime_contracts.plot_value import PlotProvenance, PlotSettings, PlotSignal, PlotValue, plot_metadata_size
from ea_node_editor.runtime_contracts.scientific_codec import scientific_from_payload, scientific_payload_size, scientific_to_payload
from ea_node_editor.runtime_contracts import scientific_values

PLOT_MARKER = "plot_value"
_MARKER = "__ea_runtime_value__"


def _fields(value: object, names: set[str], label: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    validate_payload_fields(value, label=label, required=frozenset(names))


def plot_payload_size(payload: Mapping[str, Any]) -> int:
    """Validate layout and cumulative limits before allocating decoded arrays."""
    _fields(payload, {_MARKER, "version", "preview", "signals", "settings", "provenance"}, "Plot payload")
    if payload[_MARKER] != PLOT_MARKER or type(payload["version"]) is not int or payload["version"] != 1:
        raise ValueError("Unsupported Plot schema version")
    if type(payload["signals"]) is not list or not payload["signals"]:
        raise ValueError("Plot signals must be a nonempty list")
    _fields(payload["settings"], {f.name for f in fields(PlotSettings)}, "Plot settings")
    _fields(payload["provenance"], {f.name for f in fields(PlotProvenance)}, "Plot provenance")
    settings = _settings_from_payload(payload["settings"])
    provenance = PlotProvenance(**payload["provenance"])
    if not isinstance(payload["preview"], Mapping):
        raise ValueError("Plot preview requires an ImageValue payload")
    encoded = payload["preview"].get("encoded_base64")
    if type(encoded) is not str or len(encoded) % 4 or len(encoded) > IMAGE_VALUE_MAX_ENCODED_BYTES:
        raise ValueError("Plot preview has an invalid or oversized encoded image")
    size = len(encoded) // 4 * 3 - (2 if encoded.endswith("==") else 1 if encoded.endswith("=") else 0)
    metadata = []
    for signal in payload["signals"]:
        _fields(signal, {"signal_id", "x", "y", "label", "x_kind"}, "Plot signal")
        metadata.append((signal["signal_id"], signal["label"], signal["x_kind"]))
        for name in ("x", "y"):
            if not isinstance(signal[name], Mapping) or signal[name].get("kind") != "array":
                raise ValueError("Plot X/Y require scientific array payloads")
            size += scientific_payload_size(signal[name])
        if size > scientific_values.SCIENTIFIC_VALUE_MAX_BYTES:
            raise ValueError("Plot value exceeds the 256 MiB decoded-content limit")
    size += plot_metadata_size(settings, provenance, metadata)
    if size > scientific_values.SCIENTIFIC_VALUE_MAX_BYTES:
        raise ValueError("Plot value exceeds the 256 MiB decoded-content limit")
    # ImageValue's strict decoder independently preflights its encoded PNG limit.
    return size


def _settings_from_payload(payload: Mapping[str, Any]) -> PlotSettings:
    values = dict(payload)
    for key in ("labels", "colors", "line_styles", "line_widths", "marker_shapes", "marker_sizes", "x_bounds", "y_bounds"):
        if values[key] is None and key in {"x_bounds", "y_bounds"}:
            continue
        if type(values[key]) is not list:
            raise ValueError(f"Plot settings {key} must be a list")
        values[key] = tuple(values[key])
    return PlotSettings(**values)


def plot_to_payload(value: PlotValue, *, catalog=None) -> dict[str, Any]:
    if catalog is not None:
        catalog.validate_carrier(value.data_type_id, value)
    settings = asdict(value.settings)
    settings = {key: list(item) if type(item) is tuple else item for key, item in settings.items()}
    return {
        _MARKER: PLOT_MARKER, "version": 1,
        "preview": value.preview.to_payload(catalog=catalog),
        "signals": [{"signal_id": s.signal_id, "label": s.label, "x_kind": s.x_kind,
                     "x": scientific_to_payload(s.x), "y": scientific_to_payload(s.y)} for s in value.signals],
        "settings": settings, "provenance": asdict(value.provenance),
    }


def plot_from_payload(payload: Mapping[str, Any], *, catalog=None) -> PlotValue:
    plot_payload_size(payload)
    preview = ImageValue.from_payload(payload["preview"], catalog=catalog)
    if preview is None:
        raise ValueError("Plot preview requires an ImageValue payload")
    value = PlotValue(
        preview,
        tuple(PlotSignal(s["signal_id"], scientific_from_payload(s["x"]), scientific_from_payload(s["y"]), s["label"], s["x_kind"])
              for s in payload["signals"]),
        _settings_from_payload(payload["settings"]), PlotProvenance(**payload["provenance"]),
    )
    catalog.validate_carrier(value.data_type_id, value)
    return value
