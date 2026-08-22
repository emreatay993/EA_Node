from __future__ import annotations

import json
import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from weakref import WeakKeyDictionary

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QWidget

from ea_node_editor.common.coercions import coerce_int as _coerce_int
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.execution.viewer_camera_state import apply_camera_state, extract_camera_state
from ea_node_editor.execution.viewer_pyvista_style import (
    VIEWER_OVERLAY_FONT_FAMILY,
    scalar_bar_args_for_viewport,
    viewer_canvas_style,
)
from ea_node_editor.ui_qml.viewer_widget_binder import (
    ViewerWidgetBindRequest,
    ViewerWidgetNoBind,
    ViewerWidgetReleaseRequest,
)

_DPF_TRANSPORT_KIND = "dpf_transport_bundle"
_DPF_TRANSPORT_SCHEMA = "ea.dpf.viewer_transport_bundle.v1"
_VIEWER_METADATA_OVERLAY_NAME = "ea.dpf.viewer.metadata"
_NATIVE_WINDOW_OVERLAY_PROPERTY = "ea.nativeWindowOverlay"
_SHOW_MESH_EDGES_OPTION = "show_mesh_edges"
_COLORMAP_OPTION = "colormap"
_RESULT_COMPONENT_OPTION = "result_component"
_SCALAR_RANGE_MODE_OPTION = "scalar_range_mode"
_SCALAR_RANGE_MIN_OPTION = "scalar_range_min"
_SCALAR_RANGE_MAX_OPTION = "scalar_range_max"
_SHOW_SCALAR_BAR_OPTION = "show_scalar_bar"
_DEFORM_SCALE_OPTION = "deform_scale"
_HOVER_PROBE_OPTION = "hover_probe"
_SHOW_MINMAX_MARKERS_OPTION = "show_minmax_markers"
_VIEWER_BACKGROUND_OPTION = "viewer_background"
_VIEWER_PROBE_OVERLAY_NAME = "ea.dpf.viewer.probe"
_COMPONENT_INDEX_BY_NAME = {"x": 0, "y": 1, "z": 2}
_AUTO_DEFORM_BBOX_FRACTION = 0.1


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value).strip()


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = _string(value).casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return default


def _preferred_scalars_name(dataset: Any, metadata: Mapping[str, Any]) -> str | None:
    array_names = [str(name) for name in getattr(dataset, "array_names", ()) if str(name).strip()]
    result_name = _string(metadata.get("result_name"))
    if result_name and result_name in array_names:
        return result_name
    for name in array_names:
        if name.casefold() in {"node_id", "element_id"}:
            continue
        return name
    return array_names[0] if array_names else None


def _block_count(dataset: Any) -> int:
    try:
        return max(0, int(getattr(dataset, "n_blocks", 0)))
    except (TypeError, ValueError):
        return 0


def _active_array(dataset: Any, name: str | None) -> tuple[Any, str]:
    if not name:
        return None, ""
    for location in ("point_data", "cell_data"):
        data = getattr(dataset, location, None)
        if data is None:
            continue
        try:
            if name in data:
                return data[name], location
        except (TypeError, KeyError):
            continue
    return None, ""


def _array_component_count(array: Any) -> int:
    shape = getattr(array, "shape", None)
    if not isinstance(shape, (tuple, list)):
        return 0
    if len(shape) == 1:
        return 1
    if len(shape) == 2:
        try:
            return max(0, int(shape[1]))
        except (TypeError, ValueError):
            return 0
    return 0


def _parse_range_bound(value: Any) -> float | None:
    text = _string(value)
    if not text:
        return None
    try:
        parsed = float(text)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


@dataclass(slots=True, frozen=True)
class _RenderStyle:
    cmap: str
    clim: tuple[float, float] | None
    component: int | None
    component_label: str
    show_scalar_bar: bool


def _resolve_render_style(options: Mapping[str, Any], dataset: Any, scalars_name: str | None) -> _RenderStyle:
    cmap = _string(options.get(_COLORMAP_OPTION)).lower() or "jet"

    component: int | None = None
    component_label = ""
    array, _ = _active_array(dataset, scalars_name)
    component_count = _array_component_count(array)
    if component_count >= 2:
        requested = _string(options.get(_RESULT_COMPONENT_OPTION)).lower()
        index = _COMPONENT_INDEX_BY_NAME.get(requested)
        if index is not None and index < component_count:
            component = index
            component_label = requested.upper()
        else:
            component_label = "Magnitude"

    clim: tuple[float, float] | None = None
    if _string(options.get(_SCALAR_RANGE_MODE_OPTION)).lower() == "custom":
        minimum = _parse_range_bound(options.get(_SCALAR_RANGE_MIN_OPTION))
        maximum = _parse_range_bound(options.get(_SCALAR_RANGE_MAX_OPTION))
        if minimum is not None and maximum is not None:
            clim = (minimum, maximum) if minimum <= maximum else (maximum, minimum)

    show_scalar_bar = bool(scalars_name) and _coerce_bool(
        options.get(_SHOW_SCALAR_BAR_OPTION), default=True
    )
    return _RenderStyle(
        cmap=cmap,
        clim=clim,
        component=component,
        component_label=component_label,
        show_scalar_bar=show_scalar_bar,
    )


def _auto_deform_factor(dataset: Any, array: Any) -> float:
    bounds = getattr(dataset, "bounds", None)
    try:
        values = [float(v) for v in bounds]
    except (TypeError, ValueError):
        return 0.0
    if len(values) < 6:
        return 0.0
    diagonal = math.sqrt(
        (values[1] - values[0]) ** 2
        + (values[3] - values[2]) ** 2
        + (values[5] - values[4]) ** 2
    )
    if diagonal <= 0.0 or not math.isfinite(diagonal):
        return 0.0
    try:
        max_magnitude = float(((array * array).sum(axis=1)).max()) ** 0.5
    except Exception:  # noqa: BLE001
        return 0.0
    if max_magnitude <= 0.0 or not math.isfinite(max_magnitude):
        return 0.0
    return _AUTO_DEFORM_BBOX_FRACTION * diagonal / max_magnitude


def _apply_deform(dataset: Any, scalars_name: str | None, deform_option: Any) -> tuple[Any, float]:
    normalized = _string(deform_option).lower()
    if normalized in {"", "off"}:
        return dataset, 0.0
    array, location = _active_array(dataset, scalars_name)
    if array is None or location != "point_data" or _array_component_count(array) != 3:
        return dataset, 0.0
    warp = getattr(dataset, "warp_by_vector", None)
    if not callable(warp):
        return dataset, 0.0
    if normalized == "auto":
        factor = _auto_deform_factor(dataset, array)
    else:
        try:
            factor = float(normalized)
        except (TypeError, ValueError):
            factor = 0.0
    if factor <= 0.0 or not math.isfinite(factor):
        return dataset, 0.0
    try:
        warped = warp(scalars_name, factor=factor)
    except Exception:  # noqa: BLE001
        return dataset, 0.0
    if warped is None:
        return dataset, 0.0
    return warped, factor


def _display_stats(
    dataset: Any,
    scalars_name: str | None,
    style: _RenderStyle,
    *,
    summary: Mapping[str, Any],
    step_index: int,
) -> dict[str, Any]:
    if not scalars_name:
        return {}
    array, location = _active_array(dataset, scalars_name)
    if array is None:
        return {}
    try:
        component_count = _array_component_count(array)
        if component_count >= 2:
            if style.component is not None:
                values = array[:, style.component]
            else:
                values = ((array * array).sum(axis=1)) ** 0.5
        else:
            values = array.reshape(-1) if hasattr(array, "reshape") else array
        min_index = int(values.argmin())
        max_index = int(values.argmax())
        stats: dict[str, Any] = {
            "array": str(scalars_name),
            "component": style.component_label,
            "min": float(values[min_index]),
            "max": float(values[max_index]),
            "min_index": min_index,
            "max_index": max_index,
            "location": location,
            "unit": _string(summary.get("unit")),
            "step_index": int(step_index),
        }
    except Exception:  # noqa: BLE001
        return {}
    id_name = "node_id" if location == "point_data" else "element_id"
    ids, _ids_location = _active_array(dataset, id_name)
    if ids is not None:
        try:
            stats["min_entity_id"] = int(ids[min_index])
            stats["max_entity_id"] = int(ids[max_index])
            stats["entity_kind"] = "node" if id_name == "node_id" else "element"
        except Exception:  # noqa: BLE001
            pass
    return stats


def _format_probe_value(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    magnitude = abs(numeric)
    if magnitude >= 1e5 or (magnitude > 0 and magnitude < 1e-3):
        return f"{numeric:.4e}"
    return f"{numeric:.6g}"


class _ViewerProbeController:
    """Native hover readout: VTK point picking + a named text overlay.

    Lives entirely widget-side so it works identically under the embedded
    overlay and the fullscreen retarget (a QML readout would sit below the
    native window's airspace).
    """

    def __init__(self) -> None:
        self._picker: Any = None
        self._observer_id: Any = None
        self._observed_interactor: Any = None
        self._widget: Any = None
        self._scalars_name = ""
        self._component: int | None = None
        self._component_label = ""
        self._unit = ""
        self._canvas_background = ""
        self._last_text = ""
        self._last_point_id = -2

    def attach(
        self,
        widget: Any,
        *,
        scalars_name: str | None,
        style: _RenderStyle,
        unit: str,
        canvas_background: str = "",
    ) -> bool:
        interactor = getattr(widget, "iren", None)
        renderer = getattr(widget, "renderer", None)
        add_observer = getattr(interactor, "add_observer", None)
        if not callable(add_observer) or renderer is None or not scalars_name:
            self.detach()
            return False
        if self._picker is None:
            try:
                from vtkmodules.vtkRenderingCore import vtkPointPicker
            except Exception:  # noqa: BLE001
                return False
            self._picker = vtkPointPicker()
            self._picker.SetTolerance(0.01)
        self._widget = widget
        self._scalars_name = str(scalars_name)
        self._component = style.component
        self._component_label = style.component_label
        self._unit = _string(unit)
        self._canvas_background = _string(canvas_background)
        self._last_text = ""
        self._last_point_id = -2
        if self._observer_id is None or self._observed_interactor is not interactor:
            self.detach_observer()
            try:
                self._observer_id = add_observer(
                    "MouseMoveEvent",
                    self._on_mouse_move,
                    interactor_style_fallback=False,
                )
            except TypeError:
                self._observer_id = add_observer("MouseMoveEvent", self._on_mouse_move)
            self._observed_interactor = interactor
        return True

    def detach_observer(self) -> None:
        interactor = self._observed_interactor
        remove_observer = getattr(interactor, "remove_observer", None)
        if self._observer_id is not None and callable(remove_observer):
            try:
                remove_observer(self._observer_id)
            except Exception:  # noqa: BLE001
                pass
        self._observer_id = None
        self._observed_interactor = None

    def detach(self) -> None:
        self.detach_observer()
        self._widget = None
        self._last_text = ""
        self._last_point_id = -2

    def _set_probe_text(self, text: str) -> None:
        widget = self._widget
        add_text = getattr(widget, "add_text", None)
        if not callable(add_text):
            return
        if text == self._last_text:
            return
        self._last_text = text
        add_text(
            text,
            position="upper_right",
            font_size=9,
            color=str(viewer_canvas_style(self._canvas_background)["annotation_color"]),
            font=VIEWER_OVERLAY_FONT_FAMILY,
            shadow=False,
            name=_VIEWER_PROBE_OVERLAY_NAME,
        )

    def _on_mouse_move(self, *_args: Any) -> None:
        widget = self._widget
        interactor = getattr(widget, "iren", None)
        renderer = getattr(widget, "renderer", None)
        picker = self._picker
        if interactor is None or renderer is None or picker is None:
            return
        try:
            x, y = interactor.get_event_position()
            if not picker.Pick(x, y, 0, renderer):
                self._set_probe_text("")
                return
            picked = picker.GetDataSet()
            point_id = int(picker.GetPointId())
        except Exception:  # noqa: BLE001
            return
        if picked is None or point_id < 0:
            self._set_probe_text("")
            return
        if point_id == self._last_point_id:
            return
        self._last_point_id = point_id
        self._set_probe_text(self._probe_text(picked, point_id))

    def _probe_text(self, picked: Any, point_id: int) -> str:
        try:
            import pyvista

            dataset = pyvista.wrap(picked)
        except Exception:  # noqa: BLE001
            return ""
        lines: list[str] = []
        point_data = getattr(dataset, "point_data", None)
        entity_label = f"Point {point_id}"
        if point_data is not None:
            try:
                if "node_id" in point_data:
                    entity_label = f"Node {int(point_data['node_id'][point_id])}"
            except Exception:  # noqa: BLE001
                pass
        lines.append(entity_label)
        if point_data is not None and self._scalars_name:
            try:
                if self._scalars_name in point_data:
                    values = point_data[self._scalars_name]
                    if _array_component_count(values) >= 2:
                        row = values[point_id]
                        if self._component is not None:
                            display_value = _format_probe_value(row[self._component])
                        else:
                            display_value = _format_probe_value(
                                float((row * row).sum()) ** 0.5
                            )
                    else:
                        display_value = _format_probe_value(values[point_id])
                    label = self._scalars_name
                    if self._component_label:
                        label += f" ({self._component_label})"
                    value_text = f"{label}: {display_value}"
                    if self._unit:
                        value_text += f" {self._unit}"
                    lines.append(value_text)
            except Exception:  # noqa: BLE001
                pass
        try:
            point = dataset.points[point_id]
            lines.append(
                "({}, {}, {})".format(
                    _format_probe_value(point[0]),
                    _format_probe_value(point[1]),
                    _format_probe_value(point[2]),
                )
            )
        except Exception:  # noqa: BLE001
            pass
        return "\n".join(lines)


def _add_minmax_markers(
    interactor: Any,
    dataset: Any,
    stats: Mapping[str, Any],
    *,
    canvas_background: str = "",
) -> None:
    if stats.get("location") != "point_data":
        return
    add_point_labels = getattr(interactor, "add_point_labels", None)
    points = getattr(dataset, "points", None)
    if not callable(add_point_labels) or points is None:
        return
    try:
        min_point = points[int(stats["min_index"])]
        max_point = points[int(stats["max_index"])]
        labels = [
            f"Min {_format_probe_value(stats['min'])}",
            f"Max {_format_probe_value(stats['max'])}",
        ]
        style = viewer_canvas_style(canvas_background)
        add_point_labels(
            [min_point, max_point],
            labels,
            font_size=12,
            text_color=str(style["marker_text_color"]),
            shape_color=str(style["marker_chip_color"]),
            shape_opacity=0.7,
            always_visible=True,
        )
    except Exception:  # noqa: BLE001
        return


@dataclass(slots=True, frozen=True)
class _LoadedDpfTransport:
    manifest_path: Path
    entry_path: Path
    metadata: dict[str, Any]
    display_dataset: Any
    resolved_step_index: int
    block_count: int
    scalars_name: str | None


@dataclass(slots=True)
class _DpfWidgetState:
    backend_id: str
    session_id: str = ""
    transport_revision: int = 0
    manifest_path: str = ""
    entry_path: str = ""
    step_index: int = 0
    render_stats: dict[str, Any] | None = None


class DpfViewerWidgetBinder:
    backend_id = DPF_EXECUTION_VIEWER_BACKEND_ID

    def __init__(
        self,
        *,
        interactor_factory: Callable[[QWidget | None], QWidget] | None = None,
        dataset_loader: Callable[[str], Any] | None = None,
    ) -> None:
        self._interactor_factory = interactor_factory or self._create_interactor
        self._dataset_loader = dataset_loader or self._load_dataset
        self._widget_state: WeakKeyDictionary[QWidget, _DpfWidgetState] = WeakKeyDictionary()
        self._probe_controllers: WeakKeyDictionary[QWidget, _ViewerProbeController] = WeakKeyDictionary()

    def bind_widget(self, request: ViewerWidgetBindRequest) -> QWidget:
        loaded_transport = self._load_transport_bundle(request)
        interactor = self._resolve_interactor(
            container=request.container,
            current_widget=request.current_widget,
        )
        self._populate_interactor(interactor, request=request, loaded_transport=loaded_transport)
        return interactor

    def release_widget(self, request: ViewerWidgetReleaseRequest) -> None:
        widget = request.widget
        if not self._is_reusable_interactor(widget):
            return
        controller = self._probe_controllers.pop(widget, None)
        if controller is not None:
            controller.detach()
        clear = getattr(widget, "clear", None)
        if callable(clear):
            clear()
        render = getattr(widget, "render", None)
        if callable(render):
            render()
        self._set_widget_state(
            widget,
            session_id="",
            transport_revision=0,
            manifest_path="",
            entry_path="",
            step_index=0,
        )

    def capture_camera_state(self, widget: QWidget | None) -> dict[str, Any]:
        if not self._is_reusable_interactor(widget):
            return {}
        return extract_camera_state(widget)

    def capture_view_state(self, widget: QWidget | None) -> dict[str, Any]:
        return self.capture_camera_state(widget)

    def render_stats(self, widget: QWidget | None) -> dict[str, Any]:
        if not isinstance(widget, QWidget):
            return {}
        state = self._widget_state.get(widget)
        if state is None or not state.render_stats:
            return {}
        return dict(state.render_stats)

    def _sync_probe(
        self,
        interactor: QWidget,
        *,
        options: Mapping[str, Any],
        scalars_name: str | None,
        style: _RenderStyle,
        summary: Mapping[str, Any],
        canvas_background: str = "",
    ) -> None:
        controller = self._probe_controllers.get(interactor)
        if not _coerce_bool(options.get(_HOVER_PROBE_OPTION)):
            if controller is not None:
                controller.detach()
            return
        if controller is None:
            controller = _ViewerProbeController()
            self._probe_controllers[interactor] = controller
        controller.attach(
            interactor,
            scalars_name=scalars_name,
            style=style,
            unit=_string(summary.get("unit")),
            canvas_background=canvas_background,
        )

    def restore_view_state(self, widget: QWidget | None, state: Mapping[str, Any]) -> bool:
        if not self._is_reusable_interactor(widget):
            return False
        apply_camera_state(widget, _mapping(state))
        render = getattr(widget, "render", None)
        if callable(render):
            render()
        return True

    def capture_preview_image(self, widget: QWidget | None) -> QImage | None:
        if not self._is_reusable_interactor(widget):
            return QImage()
        render = getattr(widget, "render", None)
        if callable(render):
            try:
                render()
            except Exception:  # noqa: BLE001
                return QImage()
        screenshot = getattr(widget, "screenshot", None)
        if not callable(screenshot):
            return QImage()
        try:
            captured = screenshot(return_img=True)
        except Exception:  # noqa: BLE001
            return QImage()
        return self._qimage_from_screenshot(captured)

    def _resolve_interactor(
        self,
        *,
        container: QWidget | None,
        current_widget: QWidget | None,
    ) -> QWidget:
        if self._is_reusable_interactor(current_widget):
            interactor = current_widget
            if container is not None and interactor.parent() is not container:
                interactor.setParent(container)
            self._mark_native_window_overlay(interactor)
            return interactor
        interactor = self._interactor_factory(container)
        if not isinstance(interactor, QWidget):
            raise TypeError("DPF viewer interactor factory must return a QWidget instance.")
        if container is not None and interactor.parent() is not container:
            interactor.setParent(container)
        self._mark_native_window_overlay(interactor)
        self._apply_canvas_background(interactor)
        self._set_widget_state(
            interactor,
            session_id="",
            transport_revision=0,
            manifest_path="",
            entry_path="",
            step_index=0,
        )
        return interactor

    def _populate_interactor(
        self,
        interactor: QWidget,
        *,
        request: ViewerWidgetBindRequest,
        loaded_transport: _LoadedDpfTransport,
    ) -> None:
        clear = getattr(interactor, "clear", None)
        if not callable(clear):
            raise TypeError("DPF viewer interactor widget must expose clear().")
        add_mesh = getattr(interactor, "add_mesh", None)
        if not callable(add_mesh):
            raise TypeError("DPF viewer interactor widget must expose add_mesh().")

        display_dataset, _deform_factor = _apply_deform(
            loaded_transport.display_dataset,
            loaded_transport.scalars_name,
            request.options.get(_DEFORM_SCALE_OPTION),
        )
        style = _resolve_render_style(
            request.options,
            display_dataset,
            loaded_transport.scalars_name,
        )
        viewport_width, viewport_height = self._viewport_size(
            interactor,
            container=request.container,
        )
        canvas_background = _string(request.options.get(_VIEWER_BACKGROUND_OPTION))
        scalar_bar_args = None
        if loaded_transport.scalars_name and style.show_scalar_bar:
            scalar_bar_args = scalar_bar_args_for_viewport(
                viewport_width,
                viewport_height,
                themed=True,
                themed_background=canvas_background,
            )
            if style.component_label:
                scalar_bar_args["title"] = f"{loaded_transport.scalars_name} ({style.component_label})"
        camera_state = _mapping(request.camera_state)
        previous_state = self._widget_state.get(interactor)
        if previous_state is not None and previous_state.session_id:
            # A live view already exists on this widget: the user's current
            # camera wins over both empty payloads (which reset the camera)
            # and stale persisted payload state — view-option and step
            # changes must never move the camera.
            live_camera_state = extract_camera_state(interactor)
            if live_camera_state:
                camera_state = live_camera_state
        clear()
        self._apply_canvas_background(interactor, canvas_background)
        mesh_kwargs: dict[str, Any] = {
            "scalars": loaded_transport.scalars_name,
            "scalar_bar_args": scalar_bar_args,
            "show_edges": _coerce_bool(request.options.get(_SHOW_MESH_EDGES_OPTION)),
            "show_scalar_bar": style.show_scalar_bar,
            "reset_camera": False,
            "render": False,
        }
        if loaded_transport.scalars_name:
            mesh_kwargs["cmap"] = style.cmap
            mesh_kwargs["clim"] = style.clim
            mesh_kwargs["component"] = style.component
        try:
            add_mesh(display_dataset, **mesh_kwargs)
        except Exception:  # noqa: BLE001
            # Named colormaps need matplotlib; retry once with the default map.
            if "cmap" not in mesh_kwargs:
                raise
            mesh_kwargs.pop("cmap")
            add_mesh(display_dataset, **mesh_kwargs)
        apply_camera_state(interactor, camera_state)
        self._add_live_metadata_overlay(
            interactor,
            summary=request.summary,
            playback_state=request.playback_state,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            canvas_background=canvas_background,
        )
        stats = _display_stats(
            display_dataset,
            loaded_transport.scalars_name,
            style,
            summary=request.summary,
            step_index=loaded_transport.resolved_step_index,
        )
        if stats and _coerce_bool(request.options.get(_SHOW_MINMAX_MARKERS_OPTION)):
            _add_minmax_markers(interactor, display_dataset, stats, canvas_background=canvas_background)
        self._sync_probe(
            interactor,
            options=request.options,
            scalars_name=loaded_transport.scalars_name,
            style=style,
            summary=request.summary,
            canvas_background=canvas_background,
        )
        self._set_widget_state(
            interactor,
            session_id=request.session_id,
            transport_revision=request.transport_revision,
            manifest_path=str(loaded_transport.manifest_path),
            entry_path=str(loaded_transport.entry_path),
            step_index=loaded_transport.resolved_step_index,
            render_stats=stats,
        )
        render = getattr(interactor, "render", None)
        if callable(render):
            render()

    def _load_transport_bundle(self, request: ViewerWidgetBindRequest) -> _LoadedDpfTransport:
        if _string(request.live_open_status).lower() != "ready":
            raise ViewerWidgetNoBind("DPF viewer transport is not ready for live binding.")

        transport = _mapping(request.transport)
        if _string(transport.get("kind")) != _DPF_TRANSPORT_KIND:
            raise ViewerWidgetNoBind("DPF viewer transport bundle descriptor is unavailable.")
        if _string(transport.get("status")).lower() == "blocked":
            raise ViewerWidgetNoBind("DPF viewer transport bundle is blocked.")

        manifest_path = Path(_string(transport.get("manifest_path")))
        if not manifest_path.is_file():
            raise ViewerWidgetNoBind("DPF viewer transport manifest is missing.")

        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if _string(manifest_payload.get("schema")) != _DPF_TRANSPORT_SCHEMA:
            raise ValueError("DPF viewer transport manifest schema is not supported.")

        entry_path = self._resolve_entry_path(manifest_path, transport, manifest_payload)
        if not entry_path.is_file():
            raise ViewerWidgetNoBind("DPF viewer transport entry file is missing.")

        manifest_metadata = _mapping(manifest_payload.get("metadata"))
        metadata = {
            **manifest_metadata,
            **_mapping(transport.get("metadata")),
        }
        dataset = self._dataset_loader(str(entry_path))
        display_dataset, resolved_step_index, block_count = self._display_dataset_for_playback(
            dataset,
            playback_state=request.playback_state,
        )
        return _LoadedDpfTransport(
            manifest_path=manifest_path,
            entry_path=entry_path,
            metadata=metadata,
            display_dataset=display_dataset,
            resolved_step_index=resolved_step_index,
            block_count=block_count,
            scalars_name=_preferred_scalars_name(display_dataset, metadata),
        )

    @staticmethod
    def _resolve_entry_path(
        manifest_path: Path,
        transport: Mapping[str, Any],
        manifest_payload: Mapping[str, Any],
    ) -> Path:
        transport_entry_path = Path(_string(transport.get("entry_path")))
        manifest_entry_file = _string(manifest_payload.get("entry_file"))
        if manifest_entry_file:
            manifest_entry_path = manifest_path.parent.joinpath(*PurePosixPath(manifest_entry_file).parts)
            if manifest_entry_path.is_file():
                return manifest_entry_path
        return transport_entry_path

    @staticmethod
    def _display_dataset_for_playback(
        dataset: Any,
        *,
        playback_state: Mapping[str, Any],
    ) -> tuple[Any, int, int]:
        block_count = _block_count(dataset)
        if block_count <= 0:
            return dataset, 0, 0

        requested_step_index = max(0, _coerce_int(playback_state.get("step_index"), default=0))
        resolved_step_index = min(requested_step_index, block_count - 1)
        display_dataset = dataset[resolved_step_index]
        if display_dataset is None:
            for index in range(block_count):
                candidate = dataset[index]
                if candidate is not None:
                    return candidate, index, block_count
            raise ViewerWidgetNoBind("DPF viewer transport bundle does not contain a readable step.")
        return display_dataset, resolved_step_index, block_count

    @staticmethod
    def _viewport_size(
        interactor: QWidget,
        *,
        container: QWidget | None,
    ) -> tuple[int, int]:
        widths: list[int] = []
        heights: list[int] = []
        for widget in (interactor, container):
            if not isinstance(widget, QWidget):
                continue
            width = int(widget.width())
            height = int(widget.height())
            if width > 0:
                widths.append(width)
            if height > 0:
                heights.append(height)
        width = min(widths) if widths else 320
        height = min(heights) if heights else 240
        if width <= 0:
            width = 320
        if height <= 0:
            height = 240
        return width, height

    def _add_live_metadata_overlay(
        self,
        interactor: QWidget,
        *,
        summary: Mapping[str, Any],
        playback_state: Mapping[str, Any],
        viewport_width: int,
        viewport_height: int,
        canvas_background: str = "",
    ) -> None:
        overlay_text = self._live_metadata_overlay_text(summary, playback_state)
        if not overlay_text:
            return

        add_text = getattr(interactor, "add_text", None)
        if not callable(add_text):
            return

        add_text(
            overlay_text,
            position="upper_left",
            font_size=self._overlay_font_size(viewport_width, viewport_height),
            color=str(viewer_canvas_style(canvas_background)["annotation_color"]),
            font=VIEWER_OVERLAY_FONT_FAMILY,
            shadow=False,
            name=_VIEWER_METADATA_OVERLAY_NAME,
            render=False,
        )

    @staticmethod
    def _live_metadata_overlay_text(
        summary: Mapping[str, Any],
        playback_state: Mapping[str, Any],
    ) -> str:
        lines: list[str] = []

        result_name = _string(summary.get("result_name") or summary.get("result_label"))
        if result_name:
            lines.append(f"Result: {result_name}")

        set_label = _string(summary.get("set_label") or summary.get("time_label"))
        if set_label:
            lines.append(f"Set: {set_label}")

        step_value = playback_state.get("step_index")
        if step_value is not None and _string(step_value):
            lines.append(f"Step: {max(0, _coerce_int(step_value, default=0))}")

        return "\n".join(lines)

    @staticmethod
    def _overlay_font_size(viewport_width: int, viewport_height: int) -> int:
        shortest_side = min(max(1, int(viewport_width)), max(1, int(viewport_height)))
        if shortest_side < 180:
            return 8
        if shortest_side < 260:
            return 9
        return 10

    @staticmethod
    def _qimage_from_screenshot(value: Any) -> QImage:
        if isinstance(value, QImage):
            return value.copy()

        shape = getattr(value, "shape", None)
        if not isinstance(shape, (tuple, list)) or len(shape) < 2:
            return QImage()

        try:
            height = int(shape[0])
            width = int(shape[1])
            channels = int(shape[2]) if len(shape) >= 3 else 1
        except (TypeError, ValueError):
            return QImage()

        if width <= 0 or height <= 0:
            return QImage()

        tobytes = getattr(value, "tobytes", None)
        if not callable(tobytes):
            return QImage()
        try:
            payload = tobytes()
        except Exception:  # noqa: BLE001
            return QImage()

        if channels == 4:
            image_format = QImage.Format.Format_RGBA8888
            bytes_per_line = width * 4
        elif channels == 3:
            image_format = QImage.Format.Format_RGB888
            bytes_per_line = width * 3
        elif channels == 1:
            image_format = QImage.Format.Format_Grayscale8
            bytes_per_line = width
        else:
            return QImage()

        if len(payload) < bytes_per_line * height:
            return QImage()
        image = QImage(payload, width, height, bytes_per_line, image_format)
        if image.isNull():
            return QImage()
        return image.copy()

    def _is_reusable_interactor(self, widget: QWidget | None) -> bool:
        if not isinstance(widget, QWidget):
            return False
        state = self._widget_state.get(widget)
        if state is None or state.backend_id != self.backend_id:
            return False
        return callable(getattr(widget, "clear", None)) and callable(getattr(widget, "add_mesh", None))

    def _set_widget_state(
        self,
        widget: QWidget,
        *,
        session_id: str,
        transport_revision: int,
        manifest_path: str,
        entry_path: str,
        step_index: int,
        render_stats: dict[str, Any] | None = None,
    ) -> None:
        self._widget_state[widget] = _DpfWidgetState(
            backend_id=self.backend_id,
            session_id=str(session_id),
            transport_revision=int(transport_revision),
            manifest_path=str(manifest_path),
            entry_path=str(entry_path),
            step_index=int(step_index),
            render_stats=dict(render_stats) if render_stats else None,
        )

    @staticmethod
    def _apply_canvas_background(widget: QWidget, background: str = "") -> None:
        # Match the active shell theme (or the node's explicit background
        # override); report PNG exports keep their own default light
        # background (see execution/dpf_runtime materialization).
        set_background = getattr(widget, "set_background", None)
        if not callable(set_background):
            return
        style = viewer_canvas_style(background)
        try:
            set_background(str(style["background_bottom"]), top=str(style["background_top"]))
        except TypeError:
            set_background(str(style["background_bottom"]))

    def apply_canvas_theme(self, widget: QWidget | None, options: Mapping[str, Any] | None = None) -> bool:
        """Re-apply the themed canvas to a live widget (shell theme switches).

        Overlay text and scalar-bar colors refresh on the next populate; the
        background flips immediately so the viewport tracks the shell theme.
        Nodes with an explicit `viewer_background` override keep it.
        """
        if not isinstance(widget, QWidget):
            return False
        background = _string(_mapping(options).get(_VIEWER_BACKGROUND_OPTION))
        self._apply_canvas_background(widget, background)
        render = getattr(widget, "render", None)
        if callable(render):
            try:
                render()
            except Exception:  # noqa: BLE001
                return False
        return True

    @staticmethod
    def _create_interactor(container: QWidget | None) -> QWidget:
        from pyvistaqt import QtInteractor

        platform = os.environ.get("QT_QPA_PLATFORM", "").strip().lower()
        off_screen = platform in {"minimal", "offscreen"}
        return QtInteractor(parent=container, auto_update=False, off_screen=off_screen)

    @staticmethod
    def _mark_native_window_overlay(widget: QWidget) -> None:
        widget.setProperty(_NATIVE_WINDOW_OVERLAY_PROPERTY, True)

    @staticmethod
    def _load_dataset(entry_path: str) -> Any:
        import pyvista

        return pyvista.read(entry_path)


__all__ = ["DpfViewerWidgetBinder"]
