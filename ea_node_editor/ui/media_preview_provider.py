from __future__ import annotations

from functools import lru_cache
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


def _read_local_image(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    reader.setDecideFormatFromContent(True)
    return reader.read()


@lru_cache(maxsize=256)
def _cached_local_image_dimensions(
    path_text: str,
    modified_ns: int,
    file_size: int,
) -> tuple[int, int] | None:
    del modified_ns
    del file_size
    image = _read_local_image(Path(path_text))
    if image.isNull():
        return None
    return image.width(), image.height()


def local_image_dimensions(source: str) -> tuple[int, int] | None:
    path = _local_path_from_source(source)
    if path is None or not path.exists() or not path.is_file():
        return None
    try:
        stats = path.stat()
    except OSError:
        return None
    return _cached_local_image_dimensions(str(path), int(stats.st_mtime_ns), int(stats.st_size))


class LocalMediaPreviewImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, image_id: str, requested_size: QSize) -> tuple[QImage, QSize]:  # type: ignore[override]
        source = _requested_source(image_id)
        path = _local_path_from_source(source)
        if path is None or not path.exists() or not path.is_file():
            return QImage(), QSize()

        image = _read_local_image(path)
        if image.isNull():
            return QImage(), QSize()

        return image, image.size()
