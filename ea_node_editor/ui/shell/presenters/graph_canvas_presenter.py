# Purpose: Shell presenter for graph-canvas view capture/export — PNG export and
#          project-review canvas capture viewport/spec.
# Map: subsystems/ui_shell
# Landmarks: CanvasViewPngExport, ProjectReviewCanvasCaptureSpec, ProjectReviewCanvasCaptureViewport
from __future__ import annotations

import copy
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from PyQt6.QtCore import Q_ARG, QEventLoop, QMetaObject, QObject, QThread, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_TEXT_TYPE_ID
from ea_node_editor.nodes.builtins.media_panel import MEDIA_PANEL_TYPE_ID
from ea_node_editor.ui.canvas_view_export import (
    DEFAULT_CANVAS_EXPORT_CROP_PADDING_PX,
    CanvasExportCropRect,
    CanvasViewExportError,
    canvas_export_crop_rect_for_scene_bounds,
    canvas_export_crop_rect_with_overlay_snapshots,
    canvas_view_png_output_paths,
    collision_safe_path,
    final_export_pixel_size,
    validate_export_pixel_size,
)
from ea_node_editor.ui.canvas_view_export_compositor import (
    CanvasViewExportCompositeError,
    composite_canvas_view_png,
)
from ea_node_editor.ui.dialogs.canvas_view_export_dialog import CanvasViewExportDialog
from ea_node_editor.ui.image_crop import ImageCropError, crop_image_file_to_png_bytes, crop_rect_is_effective
from ea_node_editor.ui.media_panel_source import (
    MediaPanelSourceResolution,
    resolve_media_panel_source,
)
from ea_node_editor.ui.pptx_export import (
    CanvasViewPptxExportError,
    CanvasViewPptxSlide,
    create_canvas_views_pptx,
    default_canvas_views_deck_path,
)
from ea_node_editor.ui.video_trim import VideoTrimResult, VideoTrimWorker
from ea_node_editor.ui_qml.native_overlay_owners import (
    PLOT_HOST_OVERLAY_OWNER,
    VIEWER_SESSION_OVERLAY_OWNER,
)

from .contracts import _GraphCanvasPresenterHostProtocol, _presenter_parent

if TYPE_CHECKING:
    from .inspector_presenter import ShellInspectorPresenter
    from .library_presenter import ShellLibraryPresenter
    from .workspace_presenter import ShellWorkspacePresenter


@dataclass(frozen=True, slots=True)
class _VideoTrimContext:
    action: str
    node_id: str
    start_ms: int
    end_ms: int
    scene_x: float
    scene_y: float
    properties: dict[str, Any]
    resolved_source_url: str


@dataclass(frozen=True, slots=True)
class _CanvasBaseCaptureResult:
    request_id: str
    path: Path
    canvas_logical_size: tuple[float, float]
    device_pixel_ratio: float
    output_pixel_size: tuple[int, int]


@dataclass(frozen=True, slots=True)
class _CanvasExportViewState:
    zoom: float
    center_x: float
    center_y: float


@dataclass(frozen=True, slots=True)
class ProjectReviewCanvasCaptureViewport:
    zoom: float
    center_x: float
    center_y: float


@dataclass(frozen=True, slots=True)
class ProjectReviewCanvasCaptureSpec:
    slide_id: str
    display_name: str
    capture_mode: str
    view_id: str = ""
    viewport: ProjectReviewCanvasCaptureViewport | None = None
    crop_to_content: bool = True


@dataclass(frozen=True, slots=True)
class _CanvasViewExportFailure:
    view_name: str
    message: str


@dataclass(frozen=True, slots=True)
class _ActiveCanvasPngCapture:
    path: Path
    output_pixel_size: tuple[int, int]
    device_pixel_ratio: float


@dataclass(frozen=True, slots=True)
class CanvasViewPngExport:
    view_id: str
    view_name: str
    path: Path
    output_pixel_size: tuple[int, int]
    device_pixel_ratio: float


@dataclass(frozen=True, slots=True)
class CanvasViewPngExportResult:
    exports: tuple[CanvasViewPngExport, ...]
    failures: tuple[_CanvasViewExportFailure, ...]


@dataclass(frozen=True, slots=True)
class ProjectReviewCanvasPngExport:
    slide_id: str
    view_id: str
    view_name: str
    path: Path
    output_pixel_size: tuple[int, int]
    device_pixel_ratio: float


@dataclass(frozen=True, slots=True)
class ProjectReviewCanvasPngExportResult:
    exports: tuple[ProjectReviewCanvasPngExport, ...]
    failures: tuple[_CanvasViewExportFailure, ...]


_CANVAS_BASE_CAPTURE_TIMEOUT_MS = 15000


def _mapping(value: Any) -> dict[str, Any]:
    normalized = value.toVariant() if hasattr(value, "toVariant") else value
    if isinstance(normalized, Mapping):
        return dict(normalized)
    if hasattr(normalized, "items"):
        try:
            return dict(normalized.items())
        except Exception:  # noqa: BLE001
            return {}
    return {}


class GraphCanvasPresenter(QObject):
    snap_to_grid_changed = pyqtSignal()

    def __init__(
        self,
        host: _GraphCanvasPresenterHostProtocol,
        *,
        parent: QObject | None = None,
        workspace_presenter: "ShellWorkspacePresenter",
        library_presenter: "ShellLibraryPresenter",
        inspector_presenter: "ShellInspectorPresenter",
    ) -> None:
        super().__init__(_presenter_parent(host, parent))
        self._host = host
        self._workspace_presenter = workspace_presenter
        self._library_presenter = library_presenter
        self._inspector_presenter = inspector_presenter
        self._video_trim_jobs: dict[str, tuple[QThread, VideoTrimWorker, _VideoTrimContext]] = {}
        host.snap_to_grid_changed.connect(self.snap_to_grid_changed.emit)

    def trigger_node(self, node_id: str) -> bool:
        normalized_node_id = str(node_id or "").strip()
        callback = getattr(self._host.run_controller, "trigger_node", None)
        if not normalized_node_id or not callable(callback):
            return False
        return callback(normalized_node_id) is not False

    @property
    def graphics_minimap_expanded(self) -> bool: return bool(self._host.search_scope_state.graphics_minimap_expanded)

    @property
    def selected_run_preview_before_run(self) -> bool:
        return bool(self._host.app_preferences_controller.selected_run_preview_before_run())

    @property
    def snap_to_grid_enabled(self) -> bool: return bool(self._host.search_scope_state.snap_to_grid_enabled)

    @property
    def snap_grid_size(self) -> float: return float(self._host._SNAP_GRID_SIZE)

    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        self._host.search_scope_controller.set_snap_to_grid_enabled(enabled)

    def request_toggle_snap_to_grid(self) -> bool:
        self.set_snap_to_grid_enabled(not self._host.search_scope_state.snap_to_grid_enabled)
        return bool(self._host.search_scope_state.snap_to_grid_enabled)

    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self._host.search_scope_controller.set_graphics_minimap_expanded(expanded)

    def set_selected_run_preview_before_run(self, enabled: bool) -> None:
        previous = self.selected_run_preview_before_run
        current = self._host.app_preferences_controller.set_selected_run_preview_before_run(enabled)
        if current != previous:
            self._host.graphics_preferences_changed.emit()

    def request_open_subnode_scope(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        return bool(
            self._host.search_scope_controller.navigate_scope(
                lambda: self._host.scene.open_subnode_scope(normalized_node_id)
            )
        )

    def browse_node_property_path(self, node_id: str, key: str, current_path: str, source_mode: str = "") -> str:
        return self._inspector_presenter.browse_node_property_path(node_id, key, current_path, source_mode)

    def internalize_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return self._inspector_presenter.internalize_node_property_path(node_id, key, current_path)

    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str:
        return self._inspector_presenter.pick_node_property_color(node_id, key, current_value)

    def request_save_image_crop_replace(
        self,
        image_node_id: str,
        crop_rect: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        normalized_image_node_id = str(image_node_id or "").strip()
        node, source_resolution = self._active_media_source(
            normalized_image_node_id,
            expected_kind="image",
        )
        if node is None or source_resolution is None:
            return self._image_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="missing_image_node",
                message="The source Media Panel is not showing a ready image.",
            )
        if source_resolution.input_exposed:
            return self._image_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="input_authority",
                message="Hide the Source input before replacing the Media Panel source.",
            )
        normalized_crop = dict(crop_rect or {})
        try:
            if not crop_rect_is_effective(normalized_crop):
                return self._image_command_result(
                    success=False,
                    created_type_id=MEDIA_PANEL_TYPE_ID,
                    code="no_effective_crop",
                    message="Set a crop before saving the cropped image.",
                )
        except ImageCropError as exc:
            return self._image_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="invalid_crop",
                message=str(exc) or "The selected crop is invalid.",
            )

        source_path = self._local_media_source_path(source_resolution)
        if source_path is None or not source_path.exists() or not source_path.is_file():
            return self._image_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="source_unavailable",
                message="The source image file could not be found.",
            )
        try:
            crop_result = crop_image_file_to_png_bytes(source_path, normalized_crop)
        except ImageCropError as exc:
            return self._image_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="crop_failed",
                message=str(exc) or "The cropped image could not be saved.",
            )

        staged_ref = self._stage_image_crop(crop_result.data, node)
        if not staged_ref:
            return self._image_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="stage_failed",
                message="The cropped image could not be staged into the project.",
            )

        _current_node, current_resolution = self._active_media_source(
            normalized_image_node_id,
            expected_kind="image",
        )
        if (
            current_resolution is None
            or current_resolution.input_exposed
            or current_resolution.resolved_source_url
            != source_resolution.resolved_source_url
        ):
            return self._image_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="source_changed",
                message="The Media Panel source changed before the crop could be saved.",
            )
        self._host.scene.set_node_properties(
            normalized_image_node_id,
            {
                "source": staged_ref,
                "crop_x": 0.0,
                "crop_y": 0.0,
                "crop_w": 1.0,
                "crop_h": 1.0,
            },
        )
        self._append_console_log("info", "Cropped Media Panel source saved internally.")
        self.show_graph_hint("Cropped image saved internally.", 2800)
        return self._image_command_result(
            success=True,
            created_node_id=normalized_image_node_id,
            created_type_id=MEDIA_PANEL_TYPE_ID,
            source_ref=staged_ref,
        )

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
        append_requested: bool = False,
    ) -> bool:
        result = self._host.workspace_library_controller.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
            append_requested,
        )
        return bool(result.payload)

    def request_drop_node_from_library_with_properties(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        properties: dict[str, Any],
    ) -> bool:
        return bool(
            self._host.workspace_library_controller.insert_library_node_with_properties(
                type_id,
                dict(properties or {}),
                float(scene_x),
                float(scene_y),
            )
        )

    def video_frame_capture_path(self, video_node_id: str, position_ms: int) -> str:
        safe_node_id = "".join(
            character if character.isalnum() or character in {"-", "_"} else "-"
            for character in str(video_node_id or "").strip()
        )[:48] or "video"
        position = max(0, int(position_ms or 0))
        return str(
            Path(tempfile.gettempdir())
            / f"corex-video-frame-{safe_node_id}-{position}-{uuid4().hex}.png"
        )

    def request_create_video_frame_image_node(
        self,
        video_node_id: str,
        frame_path: str,
        position_ms: int,
        scene_x: float,
        scene_y: float,
        capture_width: float,
        capture_height: float,
    ) -> dict[str, object]:
        normalized_video_node_id = str(video_node_id or "").strip()
        _source_node, source_resolution = self._active_media_source(
            normalized_video_node_id,
            expected_kind="video",
        )
        if source_resolution is None:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="missing_video_node",
                message="The source Media Panel is not showing a ready video.",
            )

        path = Path(str(frame_path or "").strip())
        try:
            frame_data = path.read_bytes()
        except OSError:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="missing_frame",
                message="The captured video frame could not be read.",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

        if not frame_data:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="empty_frame",
                message="The captured video frame was empty.",
            )

        source_ref: dict[str, str] = {"value": ""}
        initial_width = self._positive_capture_dimension(capture_width)
        initial_height = self._positive_capture_dimension(capture_height)

        def _after_create(node, mutations) -> bool:  # noqa: ANN001
            staged_ref = self._stage_video_frame_capture(frame_data, node, max(0, int(position_ms or 0)))
            if not staged_ref:
                return False
            source_ref["value"] = staged_ref
            mutations.set_node_properties(node.node_id, {"source": staged_ref})
            return True

        _current_node, current_resolution = self._active_media_source(
            normalized_video_node_id,
            expected_kind="video",
        )
        if (
            current_resolution is None
            or current_resolution.resolved_source_url
            != source_resolution.resolved_source_url
        ):
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="source_changed",
                message="The Media Panel source changed before the frame could be saved.",
            )

        try:
            node_id = str(
                self._host.scene.create_node_from_type(
                    type_id=MEDIA_PANEL_TYPE_ID,
                    x=float(scene_x),
                    y=float(scene_y),
                    parent_node_id=None,
                    select_node=True,
                    property_overrides={},
                    exposed_port_overrides={"source": False},
                    custom_width=initial_width,
                    custom_height=initial_height,
                    after_create=_after_create,
                )
                or ""
            )
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="create_failed",
                message=str(exc) or "Media Panel creation failed.",
            )

        if not node_id or not source_ref["value"]:
            return self._video_command_result(
                success=False,
                created_node_id=node_id,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="stage_failed",
                message="The captured frame could not be staged into the project.",
            )
        return self._video_command_result(
            success=True,
            created_node_id=node_id,
            created_type_id=MEDIA_PANEL_TYPE_ID,
            source_ref=source_ref["value"],
        )

    def request_create_video_timestamp_annotation(
        self,
        video_node_id: str,
        position_ms: int,
        scene_x: float,
        scene_y: float,
    ) -> dict[str, object]:
        normalized_video_node_id = str(video_node_id or "").strip()
        _source_node, source_resolution = self._active_media_source(
            normalized_video_node_id,
            expected_kind="video",
        )
        if source_resolution is None:
            return self._video_command_result(
                success=False,
                created_type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
                code="missing_video_node",
                message="The source Media Panel is not showing a ready video.",
            )

        position = max(0, int(position_ms or 0))
        time_label = _format_video_timestamp(position)
        try:
            node_id = str(
                self._host.scene.create_node_from_type(
                    type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
                    x=float(scene_x),
                    y=float(scene_y),
                    parent_node_id=None,
                    select_node=True,
                    property_overrides={
                        "text": "Video note",
                        "format": "markdown",
                    },
                )
                or ""
            )
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            return self._video_command_result(
                success=False,
                created_type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
                code="create_failed",
                message=str(exc) or "Text annotation creation failed.",
            )
        if not node_id:
            return self._video_command_result(
                success=False,
                created_type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
                code="create_failed",
                message="Text annotation creation failed.",
            )

        link_id = str(
            self._host.scene.upsert_node_link(
                node_id,
                "",
                "node",
                f"Video {time_label}",
                normalized_video_node_id,
                f"video_position_ms={position}",
            )
            or ""
        )
        if link_id:
            self._host.scene.set_node_properties(
                node_id,
                {
                    "text": f"[Video {time_label}](corex-link:{link_id})\n\nVideo note",
                    "format": "markdown",
                },
            )
        return self._video_command_result(
            success=True,
            created_node_id=node_id,
            created_type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
            link_id=link_id,
        )

    def request_trim_video_clip_replace(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        state: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        return self._request_trim_video_clip(
            action="replace",
            video_node_id=video_node_id,
            start_ms=start_ms,
            end_ms=end_ms,
            scene_x=0.0,
            scene_y=0.0,
            state=state,
        )

    def request_trim_video_clip_copy(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        scene_x: float,
        scene_y: float,
        state: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        return self._request_trim_video_clip(
            action="copy",
            video_node_id=video_node_id,
            start_ms=start_ms,
            end_ms=end_ms,
            scene_x=float(scene_x),
            scene_y=float(scene_y),
            state=state,
        )

    @staticmethod
    def _positive_capture_dimension(value: object) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(number) or number <= 0:
            return None
        return number

    @staticmethod
    def _positive_capture_integer(value: object) -> int | None:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def request_connect_ports(
        self,
        node_a_id: str,
        port_a: str,
        node_b_id: str,
        port_b: str,
        append_requested: bool = False,
    ) -> bool:
        result = self._host.workspace_library_controller.request_connect_ports(
            node_a_id,
            port_a,
            node_b_id,
            port_b,
            append_requested,
        )
        if not result.payload and str(result.message or "").strip():
            self.show_graph_hint(str(result.message), 2400)
        return bool(result.payload)

    def request_rewire_edges(
        self,
        edge_ids: list[Any],
        endpoint: str,
        node_id: str,
        port_key: str,
        copy_requested: bool = False,
        append_requested: bool = False,
    ) -> bool:
        result = self._host.workspace_library_controller.request_rewire_edges(
            edge_ids,
            endpoint,
            node_id,
            port_key,
            copy_requested,
            append_requested,
        )
        if not result.payload and str(result.message or "").strip():
            self.show_graph_hint(str(result.message), 2400)
        return bool(result.payload)

    def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
        self._host.show_graph_hint(message, timeout_ms)

    def clear_graph_hint(self) -> None:
        self._host.clear_graph_hint()

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
        append_requested: bool = False,
    ) -> bool:
        return bool(
            self._library_presenter.request_open_connection_quick_insert(
                node_id,
                port_key,
                scene_x,
                scene_y,
                overlay_x,
                overlay_y,
                append_requested,
            )
        )

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        self._library_presenter.request_open_canvas_quick_insert(scene_x, scene_y, overlay_x, overlay_y)

    def _active_media_source(
        self,
        node_id: str,
        *,
        expected_kind: str,
    ) -> tuple[object | None, MediaPanelSourceResolution | None]:
        workspace_id = str(self._host.workspace_manager.active_workspace_id() or "").strip()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return None, None
        node = workspace.nodes.get(str(node_id or "").strip())
        if node is None or str(node.type_id) != MEDIA_PANEL_TYPE_ID:
            return None, None
        project = self._host.model.project
        try:
            resolution = resolve_media_panel_source(
                node=node,
                workspace=workspace,
                run_state=getattr(self._host, "run_state", None),
                project_path=(
                    str(getattr(self._host, "project_path", "") or "").strip()
                    or None
                ),
                project_metadata=(
                    dict(project.metadata)
                    if isinstance(project.metadata, Mapping)
                    else None
                ),
            )
        except (OSError, TypeError, ValueError):
            return node, None
        if resolution.state != "ready" or resolution.media_kind != expected_kind:
            return node, None
        return node, resolution

    @staticmethod
    def _local_media_source_path(
        resolution: MediaPanelSourceResolution,
    ) -> Path | None:
        url = QUrl(str(resolution.resolved_source_url or "").strip())
        if not url.isLocalFile():
            return None
        path = str(url.toLocalFile() or "").strip()
        return Path(path) if path else None

    def _request_trim_video_clip(
        self,
        *,
        action: str,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        scene_x: float,
        scene_y: float,
        state: dict[str, Any] | None,
    ) -> dict[str, object]:
        normalized_node_id = str(video_node_id or "").strip()
        node, source_resolution = self._active_media_source(
            normalized_node_id,
            expected_kind="video",
        )
        if node is None or source_resolution is None:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="missing_video_node",
                message="The source Media Panel is not showing a ready video.",
            )
        if action == "replace" and source_resolution.input_exposed:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="input_authority",
                message="Hide the Source input before replacing the Media Panel source.",
            )
        start = max(0, int(start_ms or 0))
        end = max(0, int(end_ms or 0))
        if end <= start:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="invalid_clip_range",
                message="Set a clip out point after the clip in point.",
            )
        source_path = self._local_media_source_path(source_resolution)
        if source_path is None or not source_path.exists() or not source_path.is_file():
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="source_unavailable",
                message="Video trim is available only for ready local Media Panel sources.",
            )

        request_id = f"video_trim_{uuid4().hex}"
        properties = dict(getattr(node, "properties", {}) or {})
        properties.update(dict(state or {}))
        context = _VideoTrimContext(
            action=str(action or "replace"),
            node_id=normalized_node_id,
            start_ms=start,
            end_ms=end,
            scene_x=float(scene_x),
            scene_y=float(scene_y),
            properties=properties,
            resolved_source_url=source_resolution.resolved_source_url,
        )
        thread = QThread(self)
        worker = VideoTrimWorker(
            request_id=request_id,
            source_path=source_path,
            start_ms=start,
            end_ms=end,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._finish_video_trim_job)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda request_id=request_id: self._video_trim_thread_finished(request_id))
        self._video_trim_jobs[request_id] = (thread, worker, context)
        self._append_console_log(
            "info",
            f"Trimming Media Panel clip ({_format_video_timestamp(start)}-{_format_video_timestamp(end)}).",
        )
        self.show_graph_hint("Trimming video clip...", 2400)
        thread.start()
        return self._video_command_result(
            success=True,
            created_type_id=MEDIA_PANEL_TYPE_ID,
            request_id=request_id,
        )

    def _finish_video_trim_job(self, request_id: str, result: object) -> None:
        record = self._video_trim_jobs.get(str(request_id or ""))
        if record is None:
            return
        _thread, _worker, context = record
        if not isinstance(result, VideoTrimResult) or not result.success:
            error_result = result if isinstance(result, VideoTrimResult) else None
            message = error_result.message if error_result is not None else "Video trim failed."
            diagnostics = error_result.diagnostics if error_result is not None else ""
            self._append_console_log("error", f"Video trim failed: {message}")
            if diagnostics:
                self._append_console_log("error", diagnostics)
            self._update_notification_counters()
            self.show_graph_hint(message, 4200)
            return

        if context.action == "copy":
            command_result = self._complete_video_trim_copy(context, result)
        else:
            command_result = self._complete_video_trim_replace(context, result)

        if bool(command_result.get("success")):
            mode = str(result.mode_used or "ffmpeg")
            self._append_console_log("info", f"Video trim saved internally ({mode}).")
            self.show_graph_hint("Trimmed video saved internally.", 2800)
        else:
            error = command_result.get("error") if isinstance(command_result.get("error"), dict) else {}
            message = str(error.get("message") or "Video trim could not be saved.")
            self._append_console_log("error", message)
            self._update_notification_counters()
            self.show_graph_hint(message, 4200)

    def _complete_video_trim_replace(
        self,
        context: _VideoTrimContext,
        result: VideoTrimResult,
    ) -> dict[str, object]:
        node, source_resolution = self._active_media_source(
            context.node_id,
            expected_kind="video",
        )
        if (
            node is None
            or source_resolution is None
            or source_resolution.input_exposed
            or source_resolution.resolved_source_url != context.resolved_source_url
        ):
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="source_changed",
                message="The Media Panel source or authority changed before trim replacement completed.",
            )
        staged_ref = self._stage_video_clip(
            result.data,
            node,
            context.start_ms,
            context.end_ms,
        )
        if not staged_ref:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="stage_failed",
                message="The trimmed video could not be staged into the project.",
            )
        self._host.scene.set_node_properties(
            context.node_id,
            self._trimmed_video_properties(context, staged_ref),
        )
        return self._video_command_result(
            success=True,
            created_node_id=context.node_id,
            created_type_id=MEDIA_PANEL_TYPE_ID,
            source_ref=staged_ref,
        )

    def _complete_video_trim_copy(
        self,
        context: _VideoTrimContext,
        result: VideoTrimResult,
    ) -> dict[str, object]:
        source_node, source_resolution = self._active_media_source(
            context.node_id,
            expected_kind="video",
        )
        if (
            source_node is None
            or source_resolution is None
            or source_resolution.resolved_source_url != context.resolved_source_url
        ):
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="source_changed",
                message="The Media Panel source changed before trim copy completed.",
            )
        source_ref: dict[str, str] = {"value": ""}
        copy_properties = self._trimmed_video_properties(context, "")
        for key in ("fit_mode", "show_title", "show_frame", "auto_play", "muted", "loop", "volume", "playback_rate"):
            if key in context.properties:
                copy_properties[key] = context.properties[key]
        x = context.scene_x if isfinite(context.scene_x) and context.scene_x else float(getattr(source_node, "x", 0.0)) + 48.0
        y = context.scene_y if isfinite(context.scene_y) and context.scene_y else float(getattr(source_node, "y", 0.0)) + 48.0

        def _after_create(node, mutations) -> bool:  # noqa: ANN001
            staged_ref = self._stage_video_clip(
                result.data,
                node,
                context.start_ms,
                context.end_ms,
            )
            if not staged_ref:
                return False
            source_ref["value"] = staged_ref
            properties = dict(copy_properties)
            properties["source"] = staged_ref
            mutations.set_node_properties(node.node_id, properties)
            return True

        try:
            node_id = str(
                self._host.scene.create_node_from_type(
                    type_id=MEDIA_PANEL_TYPE_ID,
                    x=x,
                    y=y,
                    parent_node_id=None,
                    select_node=True,
                    property_overrides={},
                    exposed_port_overrides={"source": False},
                    after_create=_after_create,
                )
                or ""
            )
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            return self._video_command_result(
                success=False,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="create_failed",
                message=str(exc) or "Media Panel creation failed.",
            )
        if not node_id or not source_ref["value"]:
            return self._video_command_result(
                success=False,
                created_node_id=node_id,
                created_type_id=MEDIA_PANEL_TYPE_ID,
                code="stage_failed",
                message="The trimmed video could not be staged into the project.",
            )
        return self._video_command_result(
            success=True,
            created_node_id=node_id,
            created_type_id=MEDIA_PANEL_TYPE_ID,
            source_ref=source_ref["value"],
        )

    def _video_trim_thread_finished(self, request_id: str) -> None:
        self._video_trim_jobs.pop(str(request_id or ""), None)

    def _trimmed_video_properties(self, context: _VideoTrimContext, staged_ref: str) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "position_ms": 0,
            "clip_enabled": False,
            "clip_start_ms": 0,
            "clip_end_ms": 0,
            "timeline_bookmarks": _remap_timeline_bookmarks(
                context.properties.get("timeline_bookmarks"),
                context.start_ms,
                context.end_ms,
            ),
        }
        if staged_ref:
            properties["source"] = staged_ref
        return properties

    def _stage_image_crop(self, image_data: bytes, node) -> str:  # noqa: ANN001
        controller = getattr(self._host, "project_session_controller", None)
        stage = getattr(controller, "stage_node_artifact_bytes", None)
        if not callable(stage):
            return ""
        try:
            return str(
                stage(
                    data=bytes(image_data or b""),
                    filename=f"image-crop-{uuid4().hex[:8]}.png",
                    mime_type="image/png",
                    artifact_prefix="image_crop",
                    subdirectory="media",
                    artifact_kind="image_crop_source",
                    node_id=node.node_id,
                )
                or ""
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return ""

    def _stage_video_frame_capture(self, frame_data: bytes, node, position_ms: int) -> str:  # noqa: ANN001
        controller = getattr(self._host, "project_session_controller", None)
        stage = getattr(controller, "stage_node_artifact_bytes", None)
        if not callable(stage):
            return ""
        try:
            return str(
                stage(
                    data=bytes(frame_data or b""),
                    filename=f"video-frame-{max(0, int(position_ms or 0))}-{uuid4().hex[:8]}.png",
                    mime_type="image/png",
                    artifact_prefix="video_frame",
                    subdirectory="media",
                    artifact_kind="video_frame_capture",
                    node_id=node.node_id,
                )
                or ""
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return ""

    def _stage_video_clip(self, video_data: bytes, node, start_ms: int, end_ms: int) -> str:  # noqa: ANN001
        controller = getattr(self._host, "project_session_controller", None)
        stage = getattr(controller, "stage_node_artifact_bytes", None)
        if not callable(stage):
            return ""
        try:
            return str(
                stage(
                    data=bytes(video_data or b""),
                    filename=f"video-clip-{max(0, int(start_ms or 0))}-{max(0, int(end_ms or 0))}-{uuid4().hex[:8]}.mp4",
                    mime_type="video/mp4",
                    artifact_prefix="video_clip",
                    subdirectory="media",
                    artifact_kind="video_clip_source",
                    node_id=node.node_id,
                )
                or ""
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return ""

    def export_canvas_views(self, view_ids: Sequence[str] | None = None) -> bool:
        try:
            context = self._canvas_export_context(view_ids)
            graph_canvas_item = self._graph_canvas_item()
            canvas_logical_size = self._canvas_logical_size(graph_canvas_item)
            device_pixel_ratio = self._canvas_device_pixel_ratio()
            dialog = CanvasViewExportDialog(
                view_items=context["view_items"],
                initial_view_ids=context["initial_view_ids"],
                output_folder=self._default_canvas_export_folder(),
                canvas_logical_size=canvas_logical_size,
                device_pixel_ratio=device_pixel_ratio,
                browse_folder_callback=self._choose_canvas_export_folder,
                parent=self._dialog_parent(),
            )
            if dialog.exec() != CanvasViewExportDialog.DialogCode.Accepted:
                return False
            values = dialog.values()
            self._export_canvas_views_to_paths(
                view_ids=values.view_ids,
                output_dir=values.output_folder,
                scale=values.scale,
                create_pptx=values.create_pptx,
                slide_size=values.slide_size,
                crop_to_content=values.crop_to_content,
            )
            return True
        except (
            CanvasViewExportError,
            CanvasViewExportCompositeError,
            CanvasViewPptxExportError,
            OSError,
            RuntimeError,
            ValueError,
        ) as exc:
            self._show_canvas_export_error(str(exc))
            return False

    def _canvas_export_context(self, view_ids: Sequence[str] | None) -> dict[str, Any]:
        workspace_id = str(self._host.workspace_manager.active_workspace_id() or "").strip()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            raise CanvasViewExportError("No active workspace is available for export.")
        workspace.ensure_default_view()
        view_items = [
            {
                "view_id": view.view_id,
                "label": view.name,
            }
            for view in workspace.views.values()
        ]
        requested_ids = [str(view_id or "").strip() for view_id in view_ids or []]
        initial_view_ids = [view_id for view_id in requested_ids if view_id in workspace.views]
        if requested_ids and not initial_view_ids:
            raise CanvasViewExportError("The requested view is no longer available.")
        return {
            "view_items": view_items,
            "initial_view_ids": initial_view_ids,
        }

    def _export_canvas_views_to_paths(
        self,
        *,
        view_ids: Sequence[str],
        output_dir: Path,
        scale: int,
        create_pptx: bool,
        slide_size: str,
        crop_to_content: bool = True,
    ) -> None:
        result = self.capture_canvas_view_pngs(
            view_ids=view_ids,
            output_dir=output_dir,
            scale=scale,
            crop_to_content=crop_to_content,
        )
        exports = list(result.exports)
        failures = list(result.failures)
        output_dir = Path(output_dir).expanduser()
        workspace_id = str(self._host.workspace_manager.active_workspace_id() or "").strip()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            raise CanvasViewExportError("No active workspace is available for export.")

        deck_path: Path | None = None
        if create_pptx and exports:
            exported_slides = [
                CanvasViewPptxSlide(title=export.view_name, image_path=export.path)
                for export in exports
            ]
            default_deck_path = default_canvas_views_deck_path(output_dir, workspace.name)
            deck_path = collision_safe_path(output_dir, default_deck_path.stem, ".pptx")
            create_canvas_views_pptx(
                slides=exported_slides,
                output_path=deck_path,
                slide_size=slide_size,
            )

        self._append_console_log(
            "info",
            f"Exported {len(exports)} canvas view PNG"
            f"{'' if len(exports) == 1 else 's'} to {output_dir}.",
        )
        if deck_path is not None:
            self._append_console_log("info", f"Canvas view PowerPoint deck saved to {deck_path}.")
        if failures:
            self._append_console_log(
                "warning",
                self._format_canvas_export_failures(failures, all_failed=False),
            )
        self.show_graph_hint(
            "Canvas view export complete." if not failures else "Canvas view export completed with failures.",
            3000,
        )
        self._show_canvas_export_complete(len(exports), output_dir, deck_path, failures)

    def capture_canvas_view_pngs(
        self,
        *,
        view_ids: Sequence[str],
        output_dir: Path | str,
        scale: int,
        crop_to_content: bool = True,
        crop_padding_px: float = DEFAULT_CANVAS_EXPORT_CROP_PADDING_PX,
    ) -> CanvasViewPngExportResult:
        workspace_id = str(self._host.workspace_manager.active_workspace_id() or "").strip()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            raise CanvasViewExportError("No active workspace is available for export.")
        workspace.ensure_default_view()
        selected_view_ids = [str(view_id or "").strip() for view_id in view_ids if str(view_id or "").strip()]
        selected_view_ids = [view_id for view_id in selected_view_ids if view_id in workspace.views]
        if not selected_view_ids:
            raise CanvasViewExportError("Select at least one view to export.")

        output_dir = Path(output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        selected_names_by_id = {
            view_id: workspace.views[view_id].name
            for view_id in selected_view_ids
        }
        output_paths_by_id = canvas_view_png_output_paths(
            output_dir=output_dir,
            workspace_name=workspace.name,
            view_names_by_id=selected_names_by_id,
        )
        original_view_id = str(workspace.active_view_id or "").strip()
        exports: list[CanvasViewPngExport] = []
        failures: list[_CanvasViewExportFailure] = []

        try:
            with tempfile.TemporaryDirectory(prefix="canvas-view-export-") as temp_dir:
                temp_root = Path(temp_dir)
                for index, view_id in enumerate(selected_view_ids, start=1):
                    workspace = self._host.model.project.workspaces.get(workspace_id)
                    if workspace is None or view_id not in workspace.views:
                        failures.append(_CanvasViewExportFailure(view_id, "A selected view is no longer available."))
                        continue
                    view_name = str(workspace.views[view_id].name or view_id)
                    try:
                        if workspace.active_view_id != view_id:
                            self._workspace_presenter.request_switch_view(view_id)
                        capture = self._capture_active_canvas_png(
                            output_path=output_paths_by_id[view_id],
                            base_path=temp_root / f"canvas-view-{index}.base.png",
                            scale=scale,
                            crop_to_content=crop_to_content,
                            crop_padding_px=crop_padding_px,
                        )
                    except (
                        CanvasViewExportError,
                        CanvasViewExportCompositeError,
                        OSError,
                        RuntimeError,
                        ValueError,
                    ) as exc:
                        message = str(exc or "View export failed.")
                        failures.append(_CanvasViewExportFailure(view_name, message))
                        self._append_console_log(
                            "error",
                            f"Canvas view export failed for {view_name}: {message}",
                        )
                        continue
                    exports.append(
                        CanvasViewPngExport(
                            view_id=view_id,
                            view_name=view_name,
                            path=capture.path,
                            output_pixel_size=capture.output_pixel_size,
                            device_pixel_ratio=capture.device_pixel_ratio,
                        )
                    )
                    self._append_console_log(
                        "info",
                        "Canvas view exported: "
                            f"{view_name} -> {capture.path} "
                            f"({capture.output_pixel_size[0]} x {capture.output_pixel_size[1]} px, "
                            f"DPR {capture.device_pixel_ratio:g}).",
                    )
        finally:
            self._restore_canvas_export_view(workspace_id, original_view_id)

        if failures and not exports:
            raise CanvasViewExportError(self._format_canvas_export_failures(failures, all_failed=True))

        return CanvasViewPngExportResult(exports=tuple(exports), failures=tuple(failures))

    def capture_project_review_canvas_pngs(
        self,
        *,
        capture_specs: Sequence[ProjectReviewCanvasCaptureSpec],
        output_dir: Path | str,
        scale: int,
        crop_padding_px: float = DEFAULT_CANVAS_EXPORT_CROP_PADDING_PX,
    ) -> ProjectReviewCanvasPngExportResult:
        workspace_id = str(self._host.workspace_manager.active_workspace_id() or "").strip()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            raise CanvasViewExportError("No active workspace is available for export.")
        workspace.ensure_default_view()
        specs = [spec for spec in capture_specs if str(spec.slide_id or "").strip()]
        if not specs:
            raise CanvasViewExportError("Select at least one canvas slide to export.")

        output_dir = Path(output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths_by_slide_id = self._project_review_canvas_png_output_paths(
            output_dir=output_dir,
            workspace_name=workspace.name,
            capture_specs=specs,
        )
        original_view_id = str(workspace.active_view_id or "").strip()
        original_views = copy.deepcopy(workspace.views)
        original_live_view_state = self._canvas_export_view_state()
        exports: list[ProjectReviewCanvasPngExport] = []
        failures: list[_CanvasViewExportFailure] = []

        try:
            with tempfile.TemporaryDirectory(prefix="project-review-canvas-export-") as temp_dir:
                temp_root = Path(temp_dir)
                for index, spec in enumerate(specs, start=1):
                    display_name = str(spec.display_name or spec.view_id or spec.slide_id)
                    capture_mode = str(spec.capture_mode or "").strip().lower()
                    live_view_state = self._canvas_export_view_state()
                    try:
                        if capture_mode == "view":
                            viewport = self._project_review_canvas_viewport_state(spec.viewport)
                            if viewport is None:
                                raise CanvasViewExportError("Saved workspace view state is not available.")
                            if not self._set_canvas_export_live_view_state(viewport):
                                raise CanvasViewExportError("Saved workspace view could not be applied.")
                            effective_crop_to_content = False
                        elif capture_mode == "snapshot":
                            effective_crop_to_content = bool(spec.crop_to_content)
                        else:
                            raise CanvasViewExportError("Unsupported review deck canvas capture mode.")
                        capture = self._capture_active_canvas_png(
                            output_path=output_paths_by_slide_id[spec.slide_id],
                            base_path=temp_root / f"project-review-canvas-{index}.base.png",
                            scale=scale,
                            crop_to_content=effective_crop_to_content,
                            crop_padding_px=crop_padding_px,
                        )
                    except (
                        CanvasViewExportError,
                        CanvasViewExportCompositeError,
                        OSError,
                        RuntimeError,
                        ValueError,
                    ) as exc:
                        message = str(exc or "Canvas capture failed.")
                        failures.append(_CanvasViewExportFailure(display_name, message))
                        self._append_console_log(
                            "error",
                            f"Project review canvas export failed for {display_name}: {message}",
                        )
                        continue
                    finally:
                        self._restore_canvas_export_live_view_state(live_view_state)
                    exports.append(
                        ProjectReviewCanvasPngExport(
                            slide_id=spec.slide_id,
                            view_id=spec.view_id,
                            view_name=display_name,
                            path=capture.path,
                            output_pixel_size=capture.output_pixel_size,
                            device_pixel_ratio=capture.device_pixel_ratio,
                        )
                    )
        finally:
            workspace = self._host.model.project.workspaces.get(workspace_id)
            if workspace is not None:
                workspace.views = copy.deepcopy(original_views)
                workspace.active_view_id = original_view_id
                workspace.ensure_default_view()
            self._restore_canvas_export_live_view_state(original_live_view_state)

        if failures and not exports:
            raise CanvasViewExportError(self._format_canvas_export_failures(failures, all_failed=True))

        return ProjectReviewCanvasPngExportResult(exports=tuple(exports), failures=tuple(failures))

    def _capture_active_canvas_png(
        self,
        *,
        output_path: Path,
        base_path: Path,
        scale: int,
        crop_to_content: bool,
        crop_padding_px: float,
    ) -> _ActiveCanvasPngCapture:
        live_view_state = self._canvas_export_view_state() if crop_to_content else None
        try:
            scene_bounds = self._canvas_export_scene_bounds() if crop_to_content else None
            framed_for_crop = (
                self._frame_canvas_export_scene_bounds(scene_bounds, padding_px=crop_padding_px)
                if live_view_state is not None and scene_bounds is not None
                else False
            )
            self._settle_canvas_export_frame()
            graph_canvas_item = self._graph_canvas_item()
            canvas_logical_size = self._canvas_logical_size(graph_canvas_item)
            device_pixel_ratio = self._canvas_device_pixel_ratio()
            expected_pixel_size = final_export_pixel_size(
                canvas_logical_width=canvas_logical_size[0],
                canvas_logical_height=canvas_logical_size[1],
                device_pixel_ratio=device_pixel_ratio,
                scale=scale,
            )
            self._sync_canvas_export_overlays()
            overlay_snapshots = self._canvas_export_overlay_snapshots()
            base_capture = self._capture_canvas_base_png(
                graph_canvas_item=graph_canvas_item,
                output_path=base_path,
                scale=scale,
                device_pixel_ratio=device_pixel_ratio,
                expected_pixel_size=expected_pixel_size,
            )
            content_crop_rect_px = (
                self._canvas_export_content_crop_rect(
                    scene_bounds=scene_bounds,
                    canvas_logical_size=base_capture.canvas_logical_size,
                    output_pixel_size=base_capture.output_pixel_size,
                    padding_px=crop_padding_px,
                )
                if crop_to_content and framed_for_crop
                else None
            )
            crop_rect_px = canvas_export_crop_rect_with_overlay_snapshots(
                base_crop_rect=content_crop_rect_px,
                overlay_snapshots=overlay_snapshots,
                canvas_logical_width=base_capture.canvas_logical_size[0],
                canvas_logical_height=base_capture.canvas_logical_size[1],
                output_pixel_width=base_capture.output_pixel_size[0],
                output_pixel_height=base_capture.output_pixel_size[1],
            )
            composite_canvas_view_png(
                base_png_path=base_capture.path,
                output_png_path=output_path,
                canvas_logical_width=base_capture.canvas_logical_size[0],
                canvas_logical_height=base_capture.canvas_logical_size[1],
                overlay_snapshots=overlay_snapshots,
                capture_overlay_image=self._capture_canvas_export_overlay_image,
                crop_rect_px=crop_rect_px,
            )
            final_pixel_size = (
                (crop_rect_px.width, crop_rect_px.height)
                if crop_rect_px is not None
                else base_capture.output_pixel_size
            )
            return _ActiveCanvasPngCapture(
                path=output_path,
                output_pixel_size=final_pixel_size,
                device_pixel_ratio=base_capture.device_pixel_ratio,
            )
        finally:
            self._restore_canvas_export_live_view_state(live_view_state)

    def _project_review_canvas_png_output_paths(
        self,
        *,
        output_dir: Path,
        workspace_name: object,
        capture_specs: Sequence[ProjectReviewCanvasCaptureSpec],
    ) -> dict[str, Path]:
        reserved: set[Path] = set()
        paths: dict[str, Path] = {}
        for spec in capture_specs:
            paths[str(spec.slide_id)] = collision_safe_path(
                output_dir,
                f"{workspace_name}-{spec.display_name}",
                ".png",
                reserved=reserved,
            )
        return paths

    def _project_review_canvas_viewport_state(
        self,
        viewport: ProjectReviewCanvasCaptureViewport | None,
    ) -> _CanvasExportViewState | None:
        if viewport is None:
            return None
        zoom = self._numeric_export_value(getattr(viewport, "zoom", None))
        center_x = self._numeric_export_value(getattr(viewport, "center_x", None))
        center_y = self._numeric_export_value(getattr(viewport, "center_y", None))
        if zoom is None or center_x is None or center_y is None or zoom <= 0.0:
            return None
        return _CanvasExportViewState(zoom=zoom, center_x=center_x, center_y=center_y)

    def _canvas_export_content_crop_rect(
        self,
        *,
        scene_bounds: object,
        canvas_logical_size: tuple[float, float],
        output_pixel_size: tuple[int, int],
        padding_px: float,
    ) -> CanvasExportCropRect | None:
        if scene_bounds is None:
            return None
        view = getattr(self._host, "view", None)
        if view is None:
            return None
        return canvas_export_crop_rect_for_scene_bounds(
            scene_bounds=scene_bounds,
            center_x=getattr(view, "center_x", None),
            center_y=getattr(view, "center_y", None),
            zoom=getattr(view, "zoom_value", getattr(view, "zoom", None)),
            canvas_logical_width=canvas_logical_size[0],
            canvas_logical_height=canvas_logical_size[1],
            output_pixel_width=output_pixel_size[0],
            output_pixel_height=output_pixel_size[1],
            padding_px=padding_px,
        )

    def _canvas_export_scene_bounds(self) -> object | None:
        scene = getattr(self._host, "scene", None)
        bounds = getattr(scene, "workspace_scene_bounds", None)
        if not callable(bounds):
            return None
        try:
            scene_bounds = bounds()
        except (RuntimeError, TypeError, ValueError):
            return None
        if scene_bounds is None:
            return None
        width = self._numeric_export_value(getattr(scene_bounds, "width", None))
        height = self._numeric_export_value(getattr(scene_bounds, "height", None))
        if width is None or height is None or width <= 0.0 or height <= 0.0:
            return None
        return scene_bounds

    def _frame_canvas_export_scene_bounds(self, scene_bounds: object, *, padding_px: float) -> bool:
        view = getattr(self._host, "view", None)
        if view is None:
            return False
        frame_scene_rect = getattr(view, "frame_scene_rect", None)
        if callable(frame_scene_rect):
            try:
                frame_scene_rect(scene_bounds, padding_px=float(padding_px))
                return True
            except TypeError:
                try:
                    frame_scene_rect(scene_bounds, float(padding_px))
                    return True
                except (RuntimeError, TypeError, ValueError):
                    return False
            except (RuntimeError, ValueError):
                return False

        fit_zoom_for_scene_rect = getattr(view, "fit_zoom_for_scene_rect", None)
        center = getattr(scene_bounds, "center", None)
        set_view_state = getattr(view, "set_view_state", None)
        if not callable(fit_zoom_for_scene_rect) or not callable(center) or not callable(set_view_state):
            return False
        try:
            fitted_zoom = fit_zoom_for_scene_rect(scene_bounds, padding_px=float(padding_px))
            scene_center = center()
            center_x = self._numeric_export_value(getattr(scene_center, "x", None))
            center_y = self._numeric_export_value(getattr(scene_center, "y", None))
            if center_x is None or center_y is None:
                return False
            set_view_state(float(fitted_zoom), center_x, center_y)
            return True
        except (RuntimeError, TypeError, ValueError):
            return False

    def _canvas_export_view_state(self) -> _CanvasExportViewState | None:
        view = getattr(self._host, "view", None)
        if view is None:
            return None
        zoom = self._numeric_export_value(getattr(view, "zoom_value", getattr(view, "zoom", None)))
        center_x = self._numeric_export_value(getattr(view, "center_x", None))
        center_y = self._numeric_export_value(getattr(view, "center_y", None))
        if zoom is None or center_x is None or center_y is None or zoom <= 0.0:
            return None
        return _CanvasExportViewState(zoom=zoom, center_x=center_x, center_y=center_y)

    def _restore_canvas_export_live_view_state(self, state: _CanvasExportViewState | None) -> None:
        if state is None:
            return
        self._set_canvas_export_live_view_state(state)

    def _set_canvas_export_live_view_state(self, state: _CanvasExportViewState | None) -> bool:
        if state is None:
            return False
        view = getattr(self._host, "view", None)
        if view is None:
            return False
        try:
            set_view_state = getattr(view, "set_view_state", None)
            if callable(set_view_state):
                set_view_state(state.zoom, state.center_x, state.center_y)
            else:
                set_zoom = getattr(view, "set_zoom", None)
                center_on = getattr(view, "centerOn", None)
                if not callable(set_zoom) or not callable(center_on):
                    return False
                if callable(set_zoom):
                    set_zoom(state.zoom)
                center_on(state.center_x, state.center_y)
        except (RuntimeError, TypeError, ValueError):
            return False
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        return True

    @staticmethod
    def _numeric_export_value(value: object) -> float | None:
        raw = value() if callable(value) else value
        try:
            resolved = float(raw)
        except (TypeError, ValueError):
            return None
        return resolved if isfinite(resolved) else None

    def _graph_canvas_item(self) -> QObject:
        quick_widget = getattr(self._host, "quick_widget", None)
        root_object = quick_widget.rootObject() if quick_widget is not None else None
        graph_canvas_item = root_object.findChild(QObject, "graphCanvas") if root_object is not None else None
        if graph_canvas_item is None:
            raise CanvasViewExportError("Graph canvas is not ready for export.")
        return graph_canvas_item

    def _canvas_logical_size(self, graph_canvas_item: QObject) -> tuple[float, float]:
        width = self._positive_capture_dimension(self._numeric_qobject_value(graph_canvas_item, "width"))
        height = self._positive_capture_dimension(self._numeric_qobject_value(graph_canvas_item, "height"))
        if width is None or height is None:
            raise CanvasViewExportError("Graph canvas size is not ready for export.")
        return width, height

    @staticmethod
    def _numeric_qobject_value(obj: QObject, name: str) -> object:
        attr = getattr(obj, name, None)
        if callable(attr):
            return attr()
        value = obj.property(name)
        return value if value is not None else attr

    def _canvas_device_pixel_ratio(self) -> float:
        quick_widget = getattr(self._host, "quick_widget", None)
        candidates = [
            getattr(quick_widget, "devicePixelRatioF", lambda: 0.0)(),
        ]
        quick_window = quick_widget.quickWindow() if quick_widget is not None else None
        if quick_window is not None:
            candidates.append(getattr(quick_window, "effectiveDevicePixelRatio", lambda: 0.0)())
        for candidate in candidates:
            try:
                value = float(candidate)
            except (TypeError, ValueError):
                continue
            if isfinite(value) and value > 0.0:
                return value
        return 1.0

    def _default_canvas_export_folder(self) -> Path:
        project_path = str(getattr(self._host, "project_path", "") or "").strip()
        if project_path:
            parent = Path(project_path).expanduser().parent
            if str(parent):
                return parent
        return Path.cwd()

    def _choose_canvas_export_folder(self, suggested_path: str) -> str:
        presenter = getattr(self._host, "shell_host_presenter", None)
        choose = getattr(presenter, "choose_output_folder_dialog", None)
        if not callable(choose):
            return ""
        return str(
            choose(
                title="Choose Canvas Export Folder",
                suggested_path=str(suggested_path or ""),
            )
            or ""
        ).strip()

    def _capture_canvas_base_png(
        self,
        *,
        graph_canvas_item: QObject,
        output_path: Path,
        scale: int,
        device_pixel_ratio: float,
        expected_pixel_size: tuple[int, int],
    ) -> _CanvasBaseCaptureResult:
        result_box: dict[str, Any] = {}
        timed_out = {"value": False}
        loop = QEventLoop()
        request_id = f"canvas_export_{uuid4().hex}"

        def _finished(result: Any) -> None:
            result_box["result"] = _mapping(result)
            if loop.isRunning():
                loop.quit()

        signal = getattr(graph_canvas_item, "canvasBasePngExportFinished", None)
        if signal is None or not hasattr(signal, "connect"):
            raise CanvasViewExportError("Canvas base capture signal is not available.")
        signal.connect(_finished)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._mark_canvas_capture_timeout(loop, timed_out))
        try:
            timer.start(_CANVAS_BASE_CAPTURE_TIMEOUT_MS)
            request = {
                "request_id": request_id,
                "path": str(output_path),
                "scale": int(scale),
                "device_pixel_ratio": float(device_pixel_ratio),
                "width": int(expected_pixel_size[0]),
                "height": int(expected_pixel_size[1]),
            }
            try:
                invoked = QMetaObject.invokeMethod(
                    graph_canvas_item,
                    "exportCanvasBasePng",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG("QVariant", request),
                )
            except (RuntimeError, TypeError) as exc:
                raise CanvasViewExportError("Canvas base capture could not be started.") from exc
            if invoked is False:
                raise CanvasViewExportError("Canvas base capture could not be started.")
            loop.exec()
        finally:
            timer.stop()
            try:
                signal.disconnect(_finished)
            except (TypeError, RuntimeError):
                pass
        if timed_out["value"]:
            raise CanvasViewExportError("Canvas base capture timed out.")
        result = result_box.get("result", {})
        if not bool(result.get("success")):
            message = str(result.get("error") or result.get("message") or "Canvas base capture failed.")
            raise CanvasViewExportError(message)
        result_request_id = str(result.get("request_id") or "").strip()
        if result_request_id != request_id:
            raise CanvasViewExportError("Canvas base capture returned an unexpected request id.")
        result_path = Path(str(result.get("path") or "")).expanduser()
        if result_path != output_path:
            raise CanvasViewExportError("Canvas base capture returned an unexpected output path.")
        if not output_path.exists():
            raise CanvasViewExportError("Canvas base PNG was not written.")
        canvas_logical_width = self._positive_capture_dimension(result.get("base_logical_width"))
        canvas_logical_height = self._positive_capture_dimension(result.get("base_logical_height"))
        if canvas_logical_width is None or canvas_logical_height is None:
            raise CanvasViewExportError("Canvas base capture returned an invalid logical size.")
        output_width = self._positive_capture_integer(
            result.get("output_pixel_width", result.get("width"))
        )
        output_height = self._positive_capture_integer(
            result.get("output_pixel_height", result.get("height"))
        )
        if output_width is None or output_height is None:
            raise CanvasViewExportError("Canvas base capture returned an invalid pixel size.")
        validate_export_pixel_size(output_width, output_height)
        result_dpr = self._positive_capture_dimension(result.get("device_pixel_ratio"))
        if result_dpr is None:
            raise CanvasViewExportError("Canvas base capture returned an invalid device pixel ratio.")
        return _CanvasBaseCaptureResult(
            request_id=request_id,
            path=output_path,
            canvas_logical_size=(canvas_logical_width, canvas_logical_height),
            device_pixel_ratio=result_dpr,
            output_pixel_size=(output_width, output_height),
        )

    @staticmethod
    def _mark_canvas_capture_timeout(loop: QEventLoop, timed_out: dict[str, bool]) -> None:
        timed_out["value"] = True
        if loop.isRunning():
            loop.quit()

    def _settle_canvas_export_frame(self) -> None:
        graph_canvas_item = self._graph_canvas_item()
        try:
            QMetaObject.invokeMethod(
                graph_canvas_item,
                "forceExactVisibleSceneModels",
                Qt.ConnectionType.DirectConnection,
            )
            QMetaObject.invokeMethod(
                graph_canvas_item,
                "flushViewStateRedraw",
                Qt.ConnectionType.DirectConnection,
            )
        except RuntimeError:
            pass
        for _index in range(3):
            QApplication.processEvents()

    def _sync_canvas_export_overlays(self) -> None:
        for service_name in ("viewer_host_service", "plot_host_service"):
            service = getattr(self._host, service_name, None)
            sync = getattr(service, "sync", None)
            if callable(sync):
                sync()
        overlay_manager = getattr(self._host, "embedded_viewer_overlay_manager", None)
        sync = getattr(overlay_manager, "sync", None)
        if callable(sync):
            sync()
        QApplication.processEvents()

    def _canvas_export_overlay_snapshots(self) -> tuple[Any, ...]:
        overlay_manager = getattr(self._host, "embedded_viewer_overlay_manager", None)
        snapshots = getattr(overlay_manager, "export_overlay_snapshots", None)
        if not callable(snapshots):
            return ()
        return tuple(snapshots())

    def _capture_canvas_export_overlay_image(self, snapshot: Any) -> QImage:
        owner = str(getattr(snapshot, "owner", "") or "").strip()
        if owner == VIEWER_SESSION_OVERLAY_OWNER:
            service = getattr(self._host, "viewer_host_service", None)
        elif owner == PLOT_HOST_OVERLAY_OWNER:
            service = getattr(self._host, "plot_host_service", None)
        else:
            return QImage()
        capture = getattr(service, "capture_overlay_preview_image", None)
        if not callable(capture):
            return QImage()
        return capture(
            str(getattr(snapshot, "node_id", "") or ""),
            workspace_id=str(getattr(snapshot, "workspace_id", "") or ""),
        )

    def _restore_canvas_export_view(self, workspace_id: str, view_id: str) -> None:
        if not view_id:
            return
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None or view_id not in workspace.views or workspace.active_view_id == view_id:
            return
        try:
            self._workspace_presenter.request_switch_view(view_id)
            self._settle_canvas_export_frame()
        except (RuntimeError, ValueError, CanvasViewExportError):
            pass

    @staticmethod
    def _format_canvas_export_failures(
        failures: Sequence[_CanvasViewExportFailure],
        *,
        all_failed: bool,
    ) -> str:
        prefix = "Canvas view export failed for all selected views." if all_failed else (
            f"{len(failures)} canvas view export"
            f"{'' if len(failures) == 1 else 's'} failed."
        )
        details = [f"{failure.view_name}: {failure.message}" for failure in failures[:5]]
        if len(failures) > len(details):
            details.append(f"{len(failures) - len(details)} more failure(s) omitted.")
        return "\n".join([prefix, *details])

    def _dialog_parent(self) -> QWidget | None:
        return self._host if isinstance(self._host, QWidget) else None

    def _show_canvas_export_error(self, message: str) -> None:
        normalized = str(message or "Canvas view export failed.").strip()
        self._append_console_log("error", f"Canvas view export failed: {normalized}")
        self.show_graph_hint(normalized, 4200)
        QMessageBox.warning(self._dialog_parent(), "Export Canvas Views", normalized)

    def _show_canvas_export_complete(
        self,
        png_count: int,
        output_dir: Path,
        deck_path: Path | None,
        failures: Sequence[_CanvasViewExportFailure] = (),
    ) -> None:
        deck_text = f"\nPowerPoint deck: {deck_path}" if deck_path is not None else ""
        failure_text = (
            "\n\n" + self._format_canvas_export_failures(failures, all_failed=False)
            if failures
            else ""
        )
        QMessageBox.information(
            self._dialog_parent(),
            "Export Canvas Views",
            f"Exported {png_count} PNG file{'' if png_count == 1 else 's'} to:\n"
            f"{output_dir}{deck_text}{failure_text}",
        )

    def _append_console_log(self, level: str, message: str) -> None:
        console = getattr(self._host, "console_panel", None)
        append = getattr(console, "append_log", None)
        if callable(append):
            append(level, message)

    def _update_notification_counters(self) -> None:
        console = getattr(self._host, "console_panel", None)
        updater = getattr(self._host, "update_notification_counters", None)
        if callable(updater) and console is not None:
            updater(getattr(console, "warning_count", 0), getattr(console, "error_count", 0))

    def _image_command_result(
        self,
        *,
        success: bool,
        created_node_id: str = "",
        created_type_id: str = "",
        source_ref: str = "",
        link_id: str = "",
        request_id: str = "",
        code: str = "",
        message: str = "",
    ) -> dict[str, object]:
        return self._media_command_result(
            success=success,
            created_node_id=created_node_id,
            created_type_id=created_type_id,
            source_ref=source_ref,
            link_id=link_id,
            request_id=request_id,
            code=code,
            message=message,
            default_message="Image action failed.",
        )

    def _video_command_result(
        self,
        *,
        success: bool,
        created_node_id: str = "",
        created_type_id: str = "",
        source_ref: str = "",
        link_id: str = "",
        request_id: str = "",
        code: str = "",
        message: str = "",
    ) -> dict[str, object]:
        return self._media_command_result(
            success=success,
            created_node_id=created_node_id,
            created_type_id=created_type_id,
            source_ref=source_ref,
            link_id=link_id,
            request_id=request_id,
            code=code,
            message=message,
            default_message="Video action failed.",
        )

    @staticmethod
    def _media_command_result(
        *,
        success: bool,
        created_node_id: str = "",
        created_type_id: str = "",
        source_ref: str = "",
        link_id: str = "",
        request_id: str = "",
        code: str = "",
        message: str = "",
        default_message: str,
    ) -> dict[str, object]:
        return {
            "success": bool(success),
            "created_node_id": str(created_node_id or ""),
            "created_type_id": str(created_type_id or ""),
            "source_ref": str(source_ref or ""),
            "link_id": str(link_id or ""),
            "request_id": str(request_id or ""),
            "error": {} if success else {"code": str(code or "failed"), "message": str(message or default_message)},
        }


__all__ = ["GraphCanvasPresenter"]


def _format_video_timestamp(position_ms: int) -> str:
    total_seconds = max(0, int(position_ms) // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _remap_timeline_bookmarks(value: object, start_ms: int, end_ms: int) -> list[dict[str, object]]:
    raw_items = value
    if isinstance(value, str):
        try:
            import json

            raw_items = json.loads(value)
        except (TypeError, ValueError):
            raw_items = []
    if not isinstance(raw_items, list):
        return []
    start = max(0, int(start_ms or 0))
    end = max(start + 1, int(end_ms or 0))
    remapped: list[dict[str, object]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        try:
            position = max(0, int(round(float(item.get("position_ms", 0)))))
        except (TypeError, ValueError):
            continue
        if position < start or position > end:
            continue
        label = str(item.get("label", "") or "").strip() or _format_video_timestamp(position - start)
        bookmark_id = str(item.get("id", "") or "").strip() or f"bookmark-{index}-{position}"
        remapped.append(
            {
                "id": bookmark_id,
                "label": label,
                "position_ms": position - start,
            }
        )
    return remapped
