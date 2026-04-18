from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlencode

from PyQt6.QtCore import QObject, QRectF, QSize, Qt, pyqtSlot
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtQuick import QQuickImageProvider
from PyQt6.QtSvg import QSvgRenderer

UI_ICON_PROVIDER_ID = "ui-icons"
DEFAULT_ICON_COLOR = "#D8DEEA"
DEFAULT_ICON_SIZE = 16


@dataclass(frozen=True, slots=True)
class IconSpec:
    name: str
    label: str
    relative_path: str
    default_size: int = DEFAULT_ICON_SIZE


_ICON_ROOT = Path(__file__).resolve().parents[1] / "ui_qml" / "components" / "shell" / "icons"
_ICON_SPECS: dict[str, IconSpec] = {
    "comment": IconSpec(name="comment", label="Comment", relative_path="comment.svg"),
    "crop": IconSpec(name="crop", label="Crop", relative_path="crop.svg"),
    "delete": IconSpec(name="delete", label="Delete", relative_path="delete.svg"),
    "duplicate": IconSpec(name="duplicate", label="Duplicate", relative_path="duplicate.svg"),
    "edit": IconSpec(name="edit", label="Edit", relative_path="edit.svg"),
    "filter": IconSpec(name="filter", label="Filter", relative_path="filter.svg"),
    "fullscreen": IconSpec(name="fullscreen", label="Fullscreen", relative_path="fullscreen.svg"),
    "open-session": IconSpec(name="open-session", label="Open Session", relative_path="open-session.svg"),
    "run": IconSpec(name="run", label="Run", relative_path="player-play.svg"),
    "pause": IconSpec(name="pause", label="Pause", relative_path="player-pause.svg"),
    "resume": IconSpec(name="resume", label="Resume", relative_path="player-play.svg"),
    "stop": IconSpec(name="stop", label="Stop", relative_path="player-stop.svg"),
    "step": IconSpec(name="step", label="Step", relative_path="step.svg"),
    "focus": IconSpec(name="focus", label="Focus", relative_path="focus.svg"),
    "keep-live": IconSpec(name="keep-live", label="Keep Live", relative_path="keep-live.svg"),
    "pin": IconSpec(name="pin", label="Pin", relative_path="pin.svg"),
    "search": IconSpec(name="search", label="Search", relative_path="search.svg"),
    "more": IconSpec(name="more", label="More", relative_path="more.svg"),
    "chevrons-left": IconSpec(name="chevrons-left", label="Collapse", relative_path="chevrons-left.svg"),
    "chevrons-right": IconSpec(name="chevrons-right", label="Collapse", relative_path="chevrons-right.svg"),
    "chevron-up": IconSpec(name="chevron-up", label="Expand", relative_path="chevron-up.svg"),
    "chevron-down": IconSpec(name="chevron-down", label="Collapse", relative_path="chevron-down.svg"),
}


def _normalize_name(name: str) -> str:
    return str(name or "").strip().lower()


def has_icon(name: str) -> bool:
    return _normalize_name(name) in _ICON_SPECS


def icon_names() -> tuple[str, ...]:
    return tuple(sorted(_ICON_SPECS))


def icon_spec(name: str) -> IconSpec:
    normalized = _normalize_name(name)
    if normalized not in _ICON_SPECS:
        raise KeyError(f"Unknown icon: {name}")
    return _ICON_SPECS[normalized]


def icon_path(name: str) -> Path:
    return _ICON_ROOT / icon_spec(name).relative_path


def icon_source_url(name: str, size: int = DEFAULT_ICON_SIZE, color: str = DEFAULT_ICON_COLOR) -> str:
    spec = icon_spec(name)
    params = urlencode({"size": max(1, int(size)), "color": color or DEFAULT_ICON_COLOR})
    return f"image://{UI_ICON_PROVIDER_ID}/{spec.name}?{params}"


def _normalize_color(color: str) -> QColor:
    qcolor = QColor(color or DEFAULT_ICON_COLOR)
    if not qcolor.isValid():
        qcolor = QColor(DEFAULT_ICON_COLOR)
    return qcolor


@lru_cache(maxsize=256)
def _render_icon_image(name: str, size: int, color: str) -> QImage:
    renderer = QSvgRenderer(str(icon_path(name)))
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    if not renderer.isValid():
        return image

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(image.rect(), _normalize_color(color))
    painter.end()
    return image


def icon_pixmap(name: str, size: int = DEFAULT_ICON_SIZE, color: str = DEFAULT_ICON_COLOR) -> QPixmap:
    normalized_size = max(1, int(size))
    return QPixmap.fromImage(_render_icon_image(name, normalized_size, color))


def qicon(name: str, size: int = DEFAULT_ICON_SIZE, color: str = DEFAULT_ICON_COLOR) -> QIcon:
    return QIcon(icon_pixmap(name, size=size, color=color))


class UiIconRegistryBridge(QObject):
    @pyqtSlot(str, result=bool)
    def has(self, name: str) -> bool:
        return has_icon(name)

    @pyqtSlot(str, result=str)
    def label(self, name: str) -> str:
        try:
            return icon_spec(name).label
        except KeyError:
            return str(name or "")

    @pyqtSlot(str, result=int)
    def defaultSize(self, name: str) -> int:
        try:
            return icon_spec(name).default_size
        except KeyError:
            return DEFAULT_ICON_SIZE

    @pyqtSlot(str, result=str)
    def source(self, name: str) -> str:
        return self.sourceSized(name, DEFAULT_ICON_SIZE, DEFAULT_ICON_COLOR)

    @pyqtSlot(str, int, str, result=str)
    def sourceSized(self, name: str, size: int, color: str) -> str:
        try:
            return icon_source_url(name, size=size, color=color)
        except KeyError:
            return ""


class UiIconImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Pixmap)

    def requestPixmap(self, icon_id: str, requested_size: QSize) -> tuple[QPixmap, QSize]:  # type: ignore[override]
        icon_name, _, query = icon_id.partition("?")
        parsed_params = parse_qs(query, keep_blank_values=False)
        params = {key: values[-1] for key, values in parsed_params.items() if values}

        requested = max(requested_size.width(), requested_size.height(), 0)
        resolved_size = max(1, requested or int(params.get("size", DEFAULT_ICON_SIZE)))
        color = params.get("color", DEFAULT_ICON_COLOR)

        try:
            pixmap = icon_pixmap(icon_name, size=resolved_size, color=color)
        except KeyError:
            pixmap = QPixmap(resolved_size, resolved_size)
            pixmap.fill(Qt.GlobalColor.transparent)

        return pixmap, pixmap.size()
