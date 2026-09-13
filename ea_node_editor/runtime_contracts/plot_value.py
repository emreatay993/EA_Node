# Purpose: Own immutable session-only XY plot data, validated settings and producer identity.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_value.py
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field

from ea_node_editor.runtime_contracts.image_value import ImageValue
from ea_node_editor.runtime_contracts.scientific_values import ArrayValue
from ea_node_editor.runtime_contracts import scientific_values

PLOT_DATA_TYPE_ID = "COREX.DataTypes.Plot"


def _text(value: object, name: str, *, required: bool = False) -> None:
    if type(value) is not str or len(value.encode("utf-8")) > 65536 or (required and not value.strip()):
        raise ValueError(f"Plot {name} must be bounded text" + (" and nonempty" if required else ""))


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PlotProvenance:
    workspace_id: str
    node_id: str
    run_id: str

    def __post_init__(self) -> None:
        for key, value in asdict(self).items():
            _text(value, key, required=True)


@dataclass(frozen=True, slots=True)
class PlotSignal:
    signal_id: str
    x: ArrayValue
    y: ArrayValue
    label: str = ""
    x_kind: str = "numeric"

    def __post_init__(self) -> None:
        import numpy as np

        _text(self.signal_id, "signal identity", required=True)
        _text(self.label, "signal label")
        if type(self.x) is not ArrayValue or type(self.y) is not ArrayValue:
            raise ValueError("Plot signals require owned scientific ArrayValue buffers")
        if len(self.x.shape) != 1 or not self.x.shape[0] or self.x.shape != self.y.shape:
            raise ValueError("Plot X/Y buffers must be nonempty, aligned one-dimensional arrays")
        if self.x_kind not in {"numeric", "datetime"}:
            raise ValueError("Plot X kind must be numeric or datetime")
        x = self.x.to_numpy()
        y = self.y.to_numpy()
        if y.dtype.kind not in "iuf" or x.dtype.kind not in ("M" if self.x_kind == "datetime" else "iuf"):
            raise ValueError("Plot signal dtype does not match its axis kind")
        if not np.any(np.isfinite(x) & np.isfinite(y)):
            raise ValueError("Plot signal requires at least one finite aligned sample")


@dataclass(frozen=True, slots=True)
class PlotSettings:
    width: int = 600
    height: int = 400
    font_size: int = 12
    max_points: int = 4000
    legend_alignment: int = 8
    title: str = ""
    x_axis_label: str = ""
    y_axis_label: str = ""
    logarithmic_y_axis: bool = False
    show_legend: bool = False
    labels: tuple[str, ...] = ()
    colors: tuple[str, ...] = ("#1f77b4",)
    line_styles: tuple[int, ...] = (1,)
    line_widths: tuple[int, ...] = (1,)
    marker_shapes: tuple[int, ...] = (1,)
    marker_sizes: tuple[int, ...] = (10,)
    image_background_color: str = "#ffffff"
    data_background_color: str = "#ffffff"
    x_bounds: tuple[float, float] | None = None
    y_bounds: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        for key, low, high in (("width", 1, 16384), ("height", 1, 16384), ("font_size", 1, 72),
                               ("max_points", 0, 2**31 - 1), ("legend_alignment", 0, 8)):
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Plot {key} must be an integer from {low} to {high}")
        if self.width * self.height > 64_000_000:
            raise ValueError("Signal Plot dimensions must not exceed 64 megapixels")
        for key in ("title", "x_axis_label", "y_axis_label"):
            _text(getattr(self, key), key)
        for key in ("show_legend", "logarithmic_y_axis"):
            if type(getattr(self, key)) is not bool:
                raise ValueError(f"Plot {key} must be Boolean")
        if type(self.labels) is not tuple:
            raise ValueError("Plot labels must be an immutable tuple")
        for label in self.labels:
            _text(label, "label")
        if type(self.colors) is not tuple or not self.colors:
            raise ValueError("Plot colors must be a nonempty immutable tuple")
        for color in (*self.colors, self.image_background_color, self.data_background_color):
            if type(color) is not str or re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", color) is None:
                raise ValueError("Plot colors must use #RRGGBB or #RRGGBBAA")
        for key, low, high in (("line_styles", 0, 5), ("line_widths", 0, 5),
                               ("marker_shapes", 0, 17), ("marker_sizes", 1, 72)):
            value = getattr(self, key)
            if type(value) is not tuple or not value or any(type(n) is not int or not low <= n <= high for n in value):
                raise ValueError(f"Plot {key} must be a nonempty immutable tuple of integers from {low} to {high}")
        for key in ("x_bounds", "y_bounds"):
            value = getattr(self, key)
            if value is not None and (type(value) is not tuple or len(value) != 2 or
                    any(type(n) not in {int, float} or not math.isfinite(n) for n in value) or value[0] >= value[1]):
                raise ValueError(f"Plot {key} requires finite increasing endpoints")
        if self.logarithmic_y_axis and self.y_bounds and self.y_bounds[0] <= 0:
            raise ValueError("Plot logarithmic Y bounds must be positive")
        if len(json.dumps(asdict(self), allow_nan=False).encode()) > 1024 * 1024:
            raise ValueError("Plot settings exceed the 1 MiB metadata limit")


def plot_metadata_size(
    settings: PlotSettings,
    provenance: PlotProvenance,
    signals: Iterable[tuple[str, str, str]],
) -> int:
    """Account for the same validated UTF-8 metadata before and after decoding."""
    size = len(json.dumps([asdict(settings), asdict(provenance)], ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8"))
    for signal_id, label, x_kind in signals:
        _text(signal_id, "signal identity", required=True)
        _text(label, "signal label")
        if type(x_kind) is not str or x_kind not in {"numeric", "datetime"}:
            raise ValueError("Plot X kind must be numeric or datetime")
        size += len(json.dumps([signal_id, label, x_kind], ensure_ascii=False,
                               separators=(",", ":")).encode("utf-8"))
    return size


@dataclass(frozen=True, slots=True)
class PlotValue:
    """Data-only inspection output. Never persisted or reused across projects."""

    preview: ImageValue
    signals: tuple[PlotSignal, ...]
    settings: PlotSettings
    provenance: PlotProvenance
    data_signature: str = field(init=False)
    settings_signature: str = field(init=False)
    render_signature: str = field(init=False)
    value_signature: str = field(init=False)

    def __post_init__(self) -> None:
        import numpy as np

        if type(self.preview) is not ImageValue or type(self.settings) is not PlotSettings or type(self.provenance) is not PlotProvenance:
            raise ValueError("Plot requires a valid ImageValue preview, PlotSettings and PlotProvenance")
        if type(self.signals) is not tuple or not self.signals or any(type(s) is not PlotSignal for s in self.signals):
            raise ValueError("Plot signals must be a nonempty immutable tuple")
        if len({s.signal_id for s in self.signals}) != len(self.signals) or len({s.x_kind for s in self.signals}) != 1:
            raise ValueError("Plot signals require unique identities and one common X axis kind")
        if self.settings.labels and len(self.settings.labels) != len(self.signals):
            raise ValueError("Plot labels must match the number of logical signals")
        if self.nbytes > scientific_values.SCIENTIFIC_VALUE_MAX_BYTES:
            raise ValueError("Plot value exceeds the 256 MiB decoded-content limit")
        digest = hashlib.sha256()
        for signal in self.signals:
            if self.settings.logarithmic_y_axis and not np.any(np.isfinite(signal.x.to_numpy()) & np.isfinite(signal.y.to_numpy()) & (signal.y.to_numpy() > 0)):
                raise ValueError("Plot signal has no positive finite samples for logarithmic Y")
            digest.update(_digest([signal.signal_id, signal.label, signal.x_kind,
                                   signal.x.dtype, signal.x.shape, signal.y.dtype, signal.y.shape]).encode())
            digest.update(signal.x.buffer)
            digest.update(signal.y.buffer)
        settings = asdict(self.settings)
        data_signature = digest.hexdigest()
        settings_signature = _digest(settings)
        render_signature = _digest({key: value for key, value in settings.items() if key not in {"x_bounds", "y_bounds"}})
        for key, value in (("data_signature", data_signature), ("settings_signature", settings_signature),
                           ("render_signature", render_signature), ("value_signature", _digest([
                               data_signature, settings_signature, self.preview.sha256, asdict(self.provenance)]))):
            object.__setattr__(self, key, value)

    @property
    def nbytes(self) -> int:
        return (
            sum(s.x.nbytes + s.y.nbytes for s in self.signals)
            + len(self.preview.encoded_bytes)
            + plot_metadata_size(self.settings, self.provenance,
                                 ((s.signal_id, s.label, s.x_kind) for s in self.signals))
        )

    @property
    def data_type_id(self) -> str:
        return PLOT_DATA_TYPE_ID

    @property
    def schema_version(self) -> int:
        return 1
