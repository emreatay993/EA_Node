from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote

from PyQt6.QtCore import QRectF, QSize, Qt, QUrl
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtQuick import QQuickImageProvider

LOCAL_PDF_PREVIEW_PROVIDER_ID = "local-pdf-preview"
_DEFAULT_PREVIEW_WIDTH = 268
_DEFAULT_PREVIEW_HEIGHT = 396
_DEFAULT_PAGE_NUMBER = 1


def _query_value(image_id: str, key: str) -> str:
    _path, _separator, query = str(image_id or "").partition("?")
    if not query:
        return ""
    parsed = parse_qs(query, keep_blank_values=False)
    values = parsed.get(key)
    if not values:
        return ""
    return unquote(values[-1])


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

    url = QUrl(normalized)
    if url.isValid() and url.scheme().lower() == "file" and url.isLocalFile():
        candidate = Path(url.toLocalFile())
    else:
        candidate = Path(normalized)

    if not candidate.is_absolute():
        return None
    return candidate


def _preview_url(source: str, page_number: int, file_stamp_token: str) -> str:
    normalized = str(source or "").strip()
    if not normalized:
        return ""
    params = [
        f"source={quote(normalized, safe='')}",
        f"page={int(page_number)}",
    ]
    if file_stamp_token:
        params.append(f"stamp={quote(file_stamp_token, safe='')}")
    return f"image://{LOCAL_PDF_PREVIEW_PROVIDER_ID}/preview?{'&'.join(params)}"


def _normalized_requested_size(requested_size: QSize) -> QSize:
    width = max(1, int(requested_size.width() or _DEFAULT_PREVIEW_WIDTH))
    height = max(1, int(requested_size.height() or _DEFAULT_PREVIEW_HEIGHT))
    return QSize(width, height)


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
def _cached_pdf_metadata(
    path_text: str,
    modified_ns: int,
    file_size: int,
) -> tuple[tuple[tuple[float, float], ...], int] | None:
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
        page_sizes: list[tuple[float, float]] = []
        for page_index in range(page_count):
            page_size = document.pagePointSize(page_index)
            page_sizes.append((float(page_size.width()), float(page_size.height())))
        return tuple(page_sizes), page_count
    finally:
        document.close()


def _source_stats(path: Path) -> tuple[int, int] | None:
    try:
        stats = path.stat()
    except OSError:
        return None
    return int(stats.st_mtime_ns), int(stats.st_size)


def _pdf_info(source: str, page_number: Any) -> dict[str, Any]:
    requested_page_number = _parse_page_number(page_number)
    raw_source = str(source or "").strip()
    if not raw_source:
        return {
            "state": "placeholder",
            "message": "Choose a local PDF file to preview it here.",
            "resolved_source_url": "",
            "preview_url": "",
            "page_count": 0,
            "requested_page_number": requested_page_number,
            "resolved_page_number": max(1, requested_page_number),
            "file_stamp_token": "",
            "page_point_width": 0.0,
            "page_point_height": 0.0,
        }

    path = _local_path_from_source(raw_source)
    if path is None:
        return {
            "state": "error",
            "message": "PDF previews support only absolute local file paths.",
            "resolved_source_url": "",
            "preview_url": _preview_url(raw_source, requested_page_number, ""),
            "page_count": 0,
            "requested_page_number": requested_page_number,
            "resolved_page_number": max(1, requested_page_number),
            "file_stamp_token": "",
            "page_point_width": 0.0,
            "page_point_height": 0.0,
        }
    if not path.exists() or not path.is_file():
        return {
            "state": "error",
            "message": "Unable to find the selected PDF file.",
            "resolved_source_url": "",
            "preview_url": _preview_url(raw_source, requested_page_number, ""),
            "page_count": 0,
            "requested_page_number": requested_page_number,
            "resolved_page_number": max(1, requested_page_number),
            "file_stamp_token": "",
            "page_point_width": 0.0,
            "page_point_height": 0.0,
        }

    stats = _source_stats(path)
    if stats is None:
        return {
            "state": "error",
            "message": "Unable to inspect the selected PDF file.",
            "resolved_source_url": "",
            "preview_url": _preview_url(raw_source, requested_page_number, ""),
            "page_count": 0,
            "requested_page_number": requested_page_number,
            "resolved_page_number": max(1, requested_page_number),
            "file_stamp_token": "",
            "page_point_width": 0.0,
            "page_point_height": 0.0,
        }

    modified_ns, file_size = stats
    metadata = _cached_pdf_metadata(str(path), modified_ns, file_size)
    resolved_source_url = QUrl.fromLocalFile(str(path)).toString()
    file_stamp_token = f"{modified_ns}-{file_size}"
    if metadata is None:
        return {
            "state": "error",
            "message": "Unable to load a local PDF preview.",
            "resolved_source_url": resolved_source_url,
            "preview_url": _preview_url(resolved_source_url, requested_page_number, file_stamp_token),
            "page_count": 0,
            "requested_page_number": requested_page_number,
            "resolved_page_number": max(1, requested_page_number),
            "file_stamp_token": file_stamp_token,
            "page_point_width": 0.0,
            "page_point_height": 0.0,
        }

    page_sizes, page_count = metadata
    resolved_page_number = min(max(requested_page_number, 1), page_count)
    page_point_width, page_point_height = page_sizes[resolved_page_number - 1]
    if requested_page_number != resolved_page_number:
        message = f"Requested page {requested_page_number}; showing page {resolved_page_number} of {page_count}."
    else:
        message = f"Page {resolved_page_number} of {page_count}."
    return {
        "state": "ready",
        "message": message,
        "resolved_source_url": resolved_source_url,
        "preview_url": _preview_url(resolved_source_url, resolved_page_number, file_stamp_token),
        "page_count": page_count,
        "requested_page_number": requested_page_number,
        "resolved_page_number": resolved_page_number,
        "file_stamp_token": file_stamp_token,
        "page_point_width": float(page_point_width),
        "page_point_height": float(page_point_height),
    }


def describe_pdf_preview(source: str, page_number: Any) -> dict[str, Any]:
    return dict(_pdf_info(source, page_number))


def clamp_pdf_page_number(source: str, page_number: Any) -> int | None:
    info = _pdf_info(source, page_number)
    if str(info.get("state", "")) != "ready":
        return None
    return int(info["resolved_page_number"])


def local_pdf_page_dimensions(source: str, page_number: Any) -> tuple[float, float] | None:
    info = _pdf_info(source, page_number)
    if str(info.get("state", "")) != "ready":
        return None
    width = float(info.get("page_point_width", 0.0))
    height = float(info.get("page_point_height", 0.0))
    if width <= 0.0 or height <= 0.0:
        return None
    return width, height


@lru_cache(maxsize=256)
def _cached_pdf_page_image(
    path_text: str,
    modified_ns: int,
    file_size: int,
    page_number: int,
    requested_width: int,
    requested_height: int,
) -> QImage:
    del modified_ns
    del file_size

    requested_size = QSize(max(1, requested_width), max(1, requested_height))
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
        return image
    finally:
        document.close()


class LocalPdfPreviewImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, image_id: str, requested_size: QSize) -> tuple[QImage, QSize]:  # type: ignore[override]
        source = _query_value(image_id, "source")
        page_number = _parse_page_number(_query_value(image_id, "page"))
        info = _pdf_info(source, page_number)
        state = str(info.get("state", "placeholder"))
        target_size = _normalized_requested_size(requested_size)

        if state == "placeholder":
            image = _placeholder_image(target_size)
            return image, image.size()
        if state != "ready":
            image = _error_image(target_size, str(info.get("message", "")))
            return image, image.size()

        path = _local_path_from_source(str(info.get("resolved_source_url", "")))
        file_stamp_token = str(info.get("file_stamp_token", ""))
        if path is None or not file_stamp_token:
            image = _error_image(target_size, "Unable to render the selected PDF page.")
            return image, image.size()
        try:
            modified_text, file_size_text = file_stamp_token.split("-", 1)
            modified_ns = int(modified_text)
            file_size = int(file_size_text)
        except (TypeError, ValueError):
            stats = _source_stats(path)
            if stats is None:
                image = _error_image(target_size, "Unable to render the selected PDF page.")
                return image, image.size()
            modified_ns, file_size = stats

        image = _cached_pdf_page_image(
            str(path),
            modified_ns,
            file_size,
            int(info["resolved_page_number"]),
            int(target_size.width()),
            int(target_size.height()),
        )
        return image, image.size()


__all__ = [
    "LOCAL_PDF_PREVIEW_PROVIDER_ID",
    "LocalPdfPreviewImageProvider",
    "clamp_pdf_page_number",
    "describe_pdf_preview",
    "local_pdf_page_dimensions",
]
