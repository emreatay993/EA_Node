from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from weakref import WeakKeyDictionary

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QWidget

from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.execution.viewer_camera_state import apply_camera_state, extract_camera_state
from ea_node_editor.execution.viewer_pyvista_style import scalar_bar_args_for_viewport
from ea_node_editor.ui_qml.viewer_widget_binder import (
    ViewerWidgetBindRequest,
    ViewerWidgetNoBind,
    ViewerWidgetReleaseRequest,
)

_DPF_TRANSPORT_KIND = "dpf_transport_bundle"
_DPF_TRANSPORT_SCHEMA = "ea.dpf.viewer_transport_bundle.v1"
_VIEWER_METADATA_OVERLAY_NAME = "ea.dpf.viewer.metadata"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value).strip()


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
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
            return interactor
        interactor = self._interactor_factory(container)
        if not isinstance(interactor, QWidget):
            raise TypeError("DPF viewer interactor factory must return a QWidget instance.")
        if container is not None and interactor.parent() is not container:
            interactor.setParent(container)
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

        viewport_width, viewport_height = self._viewport_size(
            interactor,
            container=request.container,
        )
        scalar_bar_args = (
            scalar_bar_args_for_viewport(viewport_width, viewport_height)
            if loaded_transport.scalars_name
            else None
        )
        clear()
        add_mesh(
            loaded_transport.display_dataset,
            scalars=loaded_transport.scalars_name,
            scalar_bar_args=scalar_bar_args,
            reset_camera=False,
            render=False,
        )
        apply_camera_state(interactor, request.camera_state)
        self._add_live_metadata_overlay(
            interactor,
            summary=request.summary,
            playback_state=request.playback_state,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )
        self._set_widget_state(
            interactor,
            session_id=request.session_id,
            transport_revision=request.transport_revision,
            manifest_path=str(loaded_transport.manifest_path),
            entry_path=str(loaded_transport.entry_path),
            step_index=loaded_transport.resolved_step_index,
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
            color="#F4F6F8",
            shadow=True,
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
    ) -> None:
        self._widget_state[widget] = _DpfWidgetState(
            backend_id=self.backend_id,
            session_id=str(session_id),
            transport_revision=int(transport_revision),
            manifest_path=str(manifest_path),
            entry_path=str(entry_path),
            step_index=int(step_index),
        )

    @staticmethod
    def _create_interactor(container: QWidget | None) -> QWidget:
        from pyvistaqt import QtInteractor

        platform = os.environ.get("QT_QPA_PLATFORM", "").strip().lower()
        off_screen = platform in {"minimal", "offscreen"}
        return QtInteractor(parent=container, auto_update=False, off_screen=off_screen)

    @staticmethod
    def _load_dataset(entry_path: str) -> Any:
        import pyvista

        return pyvista.read(entry_path)


__all__ = ["DpfViewerWidgetBinder"]
