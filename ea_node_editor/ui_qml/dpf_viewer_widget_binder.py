from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from PyQt6.QtWidgets import QWidget

from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.ui_qml.viewer_widget_binder import (
    ViewerWidgetBindRequest,
    ViewerWidgetNoBind,
    ViewerWidgetReleaseRequest,
)

_DPF_TRANSPORT_KIND = "dpf_transport_bundle"
_DPF_TRANSPORT_SCHEMA = "ea.dpf.viewer_transport_bundle.v1"
_BACKEND_PROPERTY = "ea.viewer.backend_id"
_ENTRY_PATH_PROPERTY = "ea.viewer.entry_path"
_MANIFEST_PATH_PROPERTY = "ea.viewer.manifest_path"
_SESSION_PROPERTY = "ea.viewer.session_id"
_STEP_INDEX_PROPERTY = "ea.viewer.step_index"
_TRANSPORT_REVISION_PROPERTY = "ea.viewer.transport_revision"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value).strip()


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _vector3(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    components = [_coerce_float(item) for item in value]
    if any(component is None for component in components):
        return None
    return (float(components[0]), float(components[1]), float(components[2]))


def _camera_position_payload(camera_state: Mapping[str, Any]) -> Any:
    explicit = camera_state.get("camera_position")
    if explicit is not None:
        return explicit
    position = _vector3(camera_state.get("position"))
    focal_point = _vector3(camera_state.get("focal_point"))
    view_up = _vector3(camera_state.get("viewup", camera_state.get("view_up")))
    if position is not None and focal_point is not None and view_up is not None:
        return [position, focal_point, view_up]
    if position is not None:
        return position
    return None


def _assign_camera_vector(camera: Any, *, attribute: str, setter: str, value: tuple[float, float, float]) -> bool:
    if hasattr(camera, attribute):
        setattr(camera, attribute, value)
        return True
    method = getattr(camera, setter, None)
    if callable(method):
        method(*value)
        return True
    return False


def _assign_camera_scalar(camera: Any, *, attribute: str, setter: str, value: float) -> bool:
    if hasattr(camera, attribute):
        setattr(camera, attribute, value)
        return True
    method = getattr(camera, setter, None)
    if callable(method):
        method(value)
        return True
    return False


def _assign_camera_bool(camera: Any, *, attribute: str, setter: str, value: bool) -> bool:
    if hasattr(camera, attribute):
        setattr(camera, attribute, value)
        return True
    method = getattr(camera, setter, None)
    if callable(method):
        method(value)
        return True
    return False


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
        self._set_widget_properties(
            widget,
            session_id="",
            transport_revision=0,
            manifest_path="",
            entry_path="",
            step_index=0,
        )

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
        self._mark_backend(interactor)
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

        clear()
        add_mesh(
            loaded_transport.display_dataset,
            scalars=loaded_transport.scalars_name,
            reset_camera=False,
            render=False,
        )
        self._apply_camera_state(interactor, request.camera_state)
        self._set_widget_properties(
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
    def _mark_backend(widget: QWidget) -> None:
        widget.setProperty(_BACKEND_PROPERTY, DpfViewerWidgetBinder.backend_id)

    @staticmethod
    def _is_reusable_interactor(widget: QWidget | None) -> bool:
        if not isinstance(widget, QWidget):
            return False
        if _string(widget.property(_BACKEND_PROPERTY)) != DpfViewerWidgetBinder.backend_id:
            return False
        return callable(getattr(widget, "clear", None)) and callable(getattr(widget, "add_mesh", None))

    @staticmethod
    def _set_widget_properties(
        widget: QWidget,
        *,
        session_id: str,
        transport_revision: int,
        manifest_path: str,
        entry_path: str,
        step_index: int,
    ) -> None:
        widget.setProperty(_BACKEND_PROPERTY, DpfViewerWidgetBinder.backend_id)
        widget.setProperty(_SESSION_PROPERTY, session_id)
        widget.setProperty(_TRANSPORT_REVISION_PROPERTY, int(transport_revision))
        widget.setProperty(_MANIFEST_PATH_PROPERTY, manifest_path)
        widget.setProperty(_ENTRY_PATH_PROPERTY, entry_path)
        widget.setProperty(_STEP_INDEX_PROPERTY, int(step_index))

    @staticmethod
    def _apply_camera_state(interactor: QWidget, camera_state: Mapping[str, Any]) -> None:
        camera_payload = _mapping(camera_state)
        if not camera_payload:
            reset_camera = getattr(interactor, "reset_camera", None)
            if callable(reset_camera):
                reset_camera()
            return

        camera_applied = False
        camera_position = _camera_position_payload(camera_payload)
        if camera_position is not None and hasattr(interactor, "camera_position"):
            setattr(interactor, "camera_position", camera_position)
            camera_applied = True

        camera = getattr(interactor, "camera", None)
        if camera is not None:
            position = _vector3(camera_payload.get("position"))
            if position is not None and camera_position is None:
                camera_applied = _assign_camera_vector(
                    camera,
                    attribute="position",
                    setter="SetPosition",
                    value=position,
                ) or camera_applied
            focal_point = _vector3(camera_payload.get("focal_point"))
            if focal_point is not None:
                camera_applied = _assign_camera_vector(
                    camera,
                    attribute="focal_point",
                    setter="SetFocalPoint",
                    value=focal_point,
                ) or camera_applied
            view_up = _vector3(camera_payload.get("viewup", camera_payload.get("view_up")))
            if view_up is not None:
                camera_applied = _assign_camera_vector(
                    camera,
                    attribute="up",
                    setter="SetViewUp",
                    value=view_up,
                ) or camera_applied

            zoom_value = _coerce_float(camera_payload.get("zoom"))
            zoom = getattr(camera, "zoom", None)
            if zoom_value is not None and callable(zoom):
                zoom(zoom_value)
                camera_applied = True

            if "parallel_projection" in camera_payload:
                camera_applied = _assign_camera_bool(
                    camera,
                    attribute="parallel_projection",
                    setter="SetParallelProjection",
                    value=bool(camera_payload.get("parallel_projection")),
                ) or camera_applied
            parallel_scale = _coerce_float(camera_payload.get("parallel_scale"))
            if parallel_scale is not None:
                camera_applied = _assign_camera_scalar(
                    camera,
                    attribute="parallel_scale",
                    setter="SetParallelScale",
                    value=parallel_scale,
                ) or camera_applied

        if camera_applied:
            return
        reset_camera = getattr(interactor, "reset_camera", None)
        if callable(reset_camera):
            reset_camera()

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
