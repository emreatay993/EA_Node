from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, unquote

from PyQt6.QtCore import QSize, QUrl
from PyQt6.QtGui import QImage, QImageReader
from PyQt6.QtQuick import QQuickImageProvider

LOCAL_MEDIA_PREVIEW_PROVIDER_ID = "local-media-preview"


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


def _requested_source(image_id: str) -> str:
    _path, _separator, query = str(image_id or "").partition("?")
    if not query:
        return ""
    parsed = parse_qs(query, keep_blank_values=False)
    values = parsed.get("source")
    if not values:
        return ""
    return unquote(values[-1])


class LocalMediaPreviewImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, image_id: str, requested_size: QSize) -> tuple[QImage, QSize]:  # type: ignore[override]
        source = _requested_source(image_id)
        path = _local_path_from_source(source)
        if path is None or not path.exists() or not path.is_file():
            return QImage(), QSize()

        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        reader.setDecideFormatFromContent(True)
        image = reader.read()
        if image.isNull():
            return QImage(), QSize()

        return image, image.size()
