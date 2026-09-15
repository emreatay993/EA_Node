# Purpose: Describe local PDF pages and render them through the local-pdf-preview image provider.
# Map: feature_routes/media_image_video_pdf_refocus.md
# Tests: tests/test_pdf_preview_provider.py, tests/test_preview_image_ids.py
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QRectF, QSize, Qt, QUrl
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtQuick import QQuickImageProvider

from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.ui.preview_image_ids import preview_image_params, preview_image_url

LOCAL_PDF_PREVIEW_PROVIDER_ID = "local-pdf-preview"
_DEFAULT_PREVIEW_WIDTH = 268
_DEFAULT_PREVIEW_HEIGHT = 396
_DEFAULT_PAGE_NUMBER = 1
_PreviewProjectContext = tuple[str | Path | None, dict[str, Any] | None]
_PreviewProjectContextProvider = Callable[[], _PreviewProjectContext | None]
_project_context_provider: _PreviewProjectContextProvider | None = None


def set_pdf_preview_project_context_provider(
    provider: _PreviewProjectContextProvider | None,
) -> None:
    global _project_context_provider
    _project_context_provider = provider


def _preview_resolver() -> ProjectArtifactResolver:
    context = _project_context_provider() if callable(_project_context_provider) else None
    project_path: str | Path | None = None
    project_metadata: dict[str, Any] | None = None
    if isinstance(context, tuple) and len(context) >= 2:
        project_path = context[0]
        metadata = context[1]
        if isinstance(metadata, dict):
            project_metadata = metadata
    return ProjectArtifactResolver(
        project_path=project_path,
        project_metadata=project_metadata,
    )


def _parse_page_number(value: Any) -> int:
    if isinstance(value, bool):
        return _DEFAULT_PAGE_NUMBER
    try:
        return int(value)
    except (TypeError, ValueError):
        return _DEFAULT_PAGE_NUMBER


def _local_path_from_source(source: str) -> Path | None:
    normalized = str(source or "").strip()
    if not normalized:
        return None
    return _preview_resolver().resolve_to_path(normalized)


def _preview_url(source: str, page_number: int, file_stamp_token: str) -> str:
    normalized = str(source or "").strip()
    if not normalized:
        return ""
    return preview_image_url(
        LOCAL_PDF_PREVIEW_PROVIDER_ID,
        {"source": normalized, "page": int(page_number), "stamp": file_stamp_token},
    )


def _normalized_requested_size(requested_size: QSize) -> QSize:
    width = int(requested_size.width())
    height = int(requested_size.height())
    return QSize(
        width if width > 0 else _DEFAULT_PREVIEW_WIDTH,
        height if height > 0 else _DEFAULT_PREVIEW_HEIGHT,
    )


def _aspect_fit_render_size(page_width: float, page_height: float, requested_size: QSize) -> QSize:
    target_size = _normalized_requested_size(requested_size)
    if page_width <= 0.0 or page_height <= 0.0:
        return target_size

    scale = min(target_size.width() / float(page_width), target_size.height() / float(page_height))
    scale = max(scale, 0.01)
    return QSize(
        max(1, int(round(float(page_width) * scale))),
        max(1, int(round(float(page_height) * scale))),
    )


def _panel_image(size: QSize, *, accent: QColor, label: str, message: str) -> QImage:
    image = QImage(_normalized_requested_size(size), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#151a1f"))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    outer_rect = QRectF(8.0, 8.0, image.width() - 16.0, image.height() - 16.0)
    card_rect = QRectF(22.0, 18.0, image.width() - 44.0, image.height() - 36.0)

    painter.fillRect(outer_rect, QColor("#1b2026"))

    fold_size = min(card_rect.width(), card_rect.height()) * 0.16
    page_path = QPainterPath()
    page_path.moveTo(card_rect.left(), card_rect.top())
    page_path.lineTo(card_rect.right() - fold_size, card_rect.top())
    page_path.lineTo(card_rect.right(), card_rect.top() + fold_size)
    page_path.lineTo(card_rect.right(), card_rect.bottom())
    page_path.lineTo(card_rect.left(), card_rect.bottom())
    page_path.closeSubpath()

    painter.setPen(QPen(QColor("#D8DEE9"), 1.2))
    painter.fillPath(page_path, QColor("#FAFBFD"))
    painter.drawPath(page_path)

    fold_path = QPainterPath()
    fold_path.moveTo(card_rect.right() - fold_size, card_rect.top())
    fold_path.lineTo(card_rect.right() - fold_size, card_rect.top() + fold_size)
    fold_path.lineTo(card_rect.right(), card_rect.top() + fold_size)
    fold_path.closeSubpath()
    painter.fillPath(fold_path, QColor("#E8EDF3"))

    header_rect = QRectF(card_rect.left() + 18.0, card_rect.top() + 18.0, card_rect.width() - 36.0, 30.0)
    painter.fillRect(header_rect, accent)

    painter.setPen(QColor("#FAFBFD"))
    header_font = painter.font()
    header_font.setPixelSize(14)
    header_font.setBold(True)
    painter.setFont(header_font)
    painter.drawText(header_rect, int(Qt.AlignmentFlag.AlignCenter), label)

    body_font = painter.font()
    body_font.setPixelSize(11)
    body_font.setBold(False)
    painter.setFont(body_font)
    painter.setPen(QColor("#31414F"))
    text_rect = QRectF(card_rect.left() + 20.0, header_rect.bottom() + 14.0, card_rect.width() - 40.0, card_rect.height() - 80.0)
    painter.drawText(
        text_rect,
        int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap),
        str(message or ""),
    )

    painter.end()
    return image


def _placeholder_image(requested_size: QSize) -> QImage:
    return _panel_image(
        requested_size,
        accent=QColor("#3A7CA5"),
        label="PDF",
        message="Choose a local PDF file to preview it here.",
    )


def _error_image(requested_size: QSize, message: str) -> QImage:
    return _panel_image(
        requested_size,
        accent=QColor("#B55454"),
        label="PDF",
        message=message or "Unable to load a local PDF preview.",
    )


@lru_cache(maxsize=128)
def _cached_pdf_page_count(
    path_text: str,
    modified_ns: int,
    file_size: int,
) -> int | None:
    del modified_ns
    del file_size

    document = QPdfDocument(None)
    try:
        error = document.load(path_text)
        if error != QPdfDocument.Error.None_:
            return None
        page_count = int(document.pageCount())
        if page_count <= 0:
            return None
        return page_count
    finally:
        document.close()


@lru_cache(maxsize=512)
def _cached_pdf_page_point_size(
    path_text: str,
    modified_ns: int,
    file_size: int,
    page_number: int,
) -> tuple[float, float] | None:
    del modified_ns
    del file_size

    document = QPdfDocument(None)
    try:
        error = document.load(path_text)
        if error != QPdfDocument.Error.None_:
            return None
        page_count = int(document.pageCount())
        if page_count <= 0:
            return None
        resolved_page_number = min(max(int(page_number), 1), page_count)
        page_size = document.pagePointSize(resolved_page_number - 1)
        return float(page_size.width()), float(page_size.height())
    finally:
        document.close()


@dataclass(frozen=True, slots=True)
class _LocalPdfFile:
    path: Path
    modified_ns: int
    file_size: int

    @property
    def stamp_token(self) -> str:
        return f"{self.modified_ns}-{self.file_size}"


def _stat_local_pdf(path: Path) -> _LocalPdfFile | None:
    try:
        stats = path.stat()
    except OSError:
        return None
    return _LocalPdfFile(path, int(stats.st_mtime_ns), int(stats.st_size))


def _preview_info(
    state: str,
    message: str,
    requested_page_number: int,
    *,
    resolved_source_url: str = "",
    preview_url: str = "",
    page_count: int = 0,
    resolved_page_number: int | None = None,
    file_stamp_token: str = "",
    page_point_size: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    return {
        "state": state,
        "message": message,
        "resolved_source_url": resolved_source_url,
        "preview_url": preview_url,
        "page_count": page_count,
        "requested_page_number": requested_page_number,
        "resolved_page_number": (
            max(1, requested_page_number) if resolved_page_number is None else resolved_page_number
        ),
        "file_stamp_token": file_stamp_token,
        "page_point_width": float(page_point_size[0]),
        "page_point_height": float(page_point_size[1]),
    }


def _inspect_pdf(source: str, page_number: Any) -> tuple[dict[str, Any], _LocalPdfFile | None]:
    """Return the QML preview description and, when ready, the inspected local file."""
    requested_page_number = _parse_page_number(page_number)
    raw_source = str(source or "").strip()
    if not raw_source:
        return _preview_info("placeholder", "Choose a local PDF file to preview it here.", requested_page_number), None

    unresolved_preview_url = _preview_url(raw_source, requested_page_number, "")
    path = _local_path_from_source(raw_source)
    if path is None:
        message = "PDF previews support only absolute local file paths."
        return _preview_info("error", message, requested_page_number, preview_url=unresolved_preview_url), None
    if not path.exists() or not path.is_file():
        message = "Unable to find the selected PDF file."
        return _preview_info("error", message, requested_page_number, preview_url=unresolved_preview_url), None
    pdf_file = _stat_local_pdf(path)
    if pdf_file is None:
        message = "Unable to inspect the selected PDF file."
        return _preview_info("error", message, requested_page_number, preview_url=unresolved_preview_url), None

    path_text = str(pdf_file.path)
    resolved_source_url = QUrl.fromLocalFile(path_text).toString()
    stamp_token = pdf_file.stamp_token
    page_count = _cached_pdf_page_count(path_text, pdf_file.modified_ns, pdf_file.file_size)
    if page_count is None:
        return _preview_info(
            "error",
            "Unable to load a local PDF preview.",
            requested_page_number,
            resolved_source_url=resolved_source_url,
            preview_url=_preview_url(resolved_source_url, requested_page_number, stamp_token),
            file_stamp_token=stamp_token,
        ), None

    resolved_page_number = min(max(requested_page_number, 1), page_count)
    page_point_size = _cached_pdf_page_point_size(
        path_text, pdf_file.modified_ns, pdf_file.file_size, resolved_page_number
    )
    if requested_page_number != resolved_page_number:
        message = f"Requested page {requested_page_number}; showing page {resolved_page_number} of {page_count}."
    else:
        message = f"Page {resolved_page_number} of {page_count}."
    return _preview_info(
        "ready",
        message,
        requested_page_number,
        resolved_source_url=resolved_source_url,
        preview_url=_preview_url(resolved_source_url, resolved_page_number, stamp_token),
        page_count=page_count,
        resolved_page_number=resolved_page_number,
        file_stamp_token=stamp_token,
        page_point_size=page_point_size or (0.0, 0.0),
    ), pdf_file


def describe_pdf_preview(source: str, page_number: Any) -> dict[str, Any]:
    info, _pdf_file = _inspect_pdf(source, page_number)
    return info


def clamp_pdf_page_number(source: str, page_number: Any) -> int | None:
    info = describe_pdf_preview(source, page_number)
    if str(info.get("state", "")) != "ready":
        return None
    return int(info["resolved_page_number"])


def local_pdf_page_dimensions(source: str, page_number: Any) -> tuple[float, float] | None:
    info = describe_pdf_preview(source, page_number)
    if str(info.get("state", "")) != "ready":
        return None
    width = float(info.get("page_point_width", 0.0))
    height = float(info.get("page_point_height", 0.0))
    if width <= 0.0 or height <= 0.0:
        return None
    return width, height


def _flatten_pdf_page_to_paper(image: QImage) -> QImage:
    if not image.hasAlphaChannel():
        return image
    page = QImage(image.size(), QImage.Format.Format_RGB32)
    page.fill(Qt.GlobalColor.white)
    painter = QPainter(page)
    try:
        painter.drawImage(0, 0, image)
    finally:
        painter.end()
    return page


def _render_pdf_page_image_for_path(path_text: str, page_number: int, requested_size: QSize) -> QImage:
    document = QPdfDocument(None)
    try:
        error = document.load(path_text)
        if error != QPdfDocument.Error.None_:
            return _error_image(requested_size, "Unable to load a local PDF preview.")
        page_count = int(document.pageCount())
        if page_count <= 0:
            return _error_image(requested_size, "Unable to load a local PDF preview.")
        resolved_page_number = min(max(int(page_number), 1), page_count)
        page_size = document.pagePointSize(resolved_page_number - 1)
        render_size = _aspect_fit_render_size(float(page_size.width()), float(page_size.height()), requested_size)
        image = document.render(resolved_page_number - 1, render_size)
        if image.isNull():
            return _error_image(requested_size, "Unable to render the selected PDF page.")
        return _flatten_pdf_page_to_paper(image)
    finally:
        document.close()


def render_pdf_page_image(
    source: str,
    page_number: Any,
    requested_size: QSize | tuple[int, int] | None = None,
) -> tuple[QImage, dict[str, Any]]:
    if isinstance(requested_size, QSize):
        target_size = _normalized_requested_size(requested_size)
    elif isinstance(requested_size, tuple) and len(requested_size) >= 2:
        target_size = _normalized_requested_size(QSize(int(requested_size[0]), int(requested_size[1])))
    else:
        target_size = _normalized_requested_size(QSize(_DEFAULT_PREVIEW_WIDTH, _DEFAULT_PREVIEW_HEIGHT))

    info, pdf_file = _inspect_pdf(source, page_number)
    if info["state"] == "placeholder":
        return _placeholder_image(target_size), info
    if pdf_file is None:
        return _error_image(target_size, str(info["message"])), info
    image = _render_pdf_page_image_for_path(
        str(pdf_file.path),
        int(info["resolved_page_number"]),
        target_size,
    )
    return image, info


class LocalPdfPreviewImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, image_id: str, requested_size: QSize) -> tuple[QImage, QSize]:  # type: ignore[override]
        params = preview_image_params(image_id)
        image, _info = render_pdf_page_image(
            params.get("source", ""),
            params.get("page", ""),
            requested_size,
        )
        return image, image.size()


__all__ = [
    "LOCAL_PDF_PREVIEW_PROVIDER_ID",
    "LocalPdfPreviewImageProvider",
    "clamp_pdf_page_number",
    "describe_pdf_preview",
    "local_pdf_page_dimensions",
    "render_pdf_page_image",
    "set_pdf_preview_project_context_provider",
]
