from __future__ import annotations

import gc
from pathlib import Path

import pytest
from PyQt6.QtCore import QMarginsF, QRectF, QSize, QUrl
from PyQt6.QtGui import QColor, QImage, QPainter, QPageLayout, QPageSize, QPdfWriter
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtQuick import QQuickItem  # noqa: F401 - registers QtQuick types for the engine

from ea_node_editor.ui.media_panel_source import resolve_media_panel_source
from ea_node_editor.ui.media_preview_provider import (
    LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
    LocalMediaPreviewImageProvider,
)
from ea_node_editor.ui.pdf_preview_provider import (
    LOCAL_PDF_PREVIEW_PROVIDER_ID,
    LocalPdfPreviewImageProvider,
    describe_pdf_preview,
)
from ea_node_editor.ui.preview_image_ids import preview_image_params, preview_image_url

# Real Windows folder and file names that a second URL decode used to corrupt:
# "#" became a URL fragment and "%20" became a space.
_HOSTILE_DIRECTORY = "C# Projects #12"
_HOSTILE_STEM = "report 100%20 R&D+final=v2"


@pytest.mark.parametrize(
    "value",
    [
        "file:///C:/C%2523%20Projects/report%20100%2520.pdf",
        "C:\\Users\\me\\a+b & c=d #1 100%.pdf",
        "temp://preview_pdf",
        "Türkçe şğıİ.pdf",
    ],
)
def test_preview_image_ids_decode_each_value_exactly_once(value: str) -> None:
    url = preview_image_url("provider", {"source": value, "page": 3})
    image_id = url.removeprefix("image://provider/")

    assert preview_image_params(image_id) == {"source": value, "page": "3"}


def test_preview_image_ids_omit_blank_values_and_keep_last_duplicate() -> None:
    assert preview_image_url("provider", {"source": "x", "stamp": "", "page": None}) == (
        "image://provider/preview?source=x"
    )
    assert preview_image_params("preview?source=a&source=b&flag&=orphan") == {"source": "b"}
    assert preview_image_params("preview") == {}


def _write_pdf(path: Path) -> None:
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    painter.drawText(QRectF(80.0, 120.0, 420.0, 120.0), "PDF page 1")
    painter.end()
    del painter
    del writer
    gc.collect()


class _RecordingPdfProvider(LocalPdfPreviewImageProvider):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[QImage] = []

    def requestImage(self, image_id: str, requested_size: QSize) -> tuple[QImage, QSize]:  # type: ignore[override]
        image, size = super().requestImage(image_id, requested_size)
        self.images.append(image)
        return image, size


def _load_qml_image(engine: QQmlEngine, source_url: str, qapp) -> bool:  # noqa: ANN001
    component = QQmlComponent(engine)
    component.setData(
        b"import QtQuick\n"
        b"Image {\n"
        b"    asynchronous: false\n"
        b"    cache: false\n"
        b"    sourceSize.width: 120\n"
        b"    sourceSize.height: 120\n"
        b"    readonly property bool loaded: status === Image.Ready\n"
        b"}\n",
        QUrl(),
    )
    item = component.create()
    assert item is not None, component.errorString()
    try:
        item.setProperty("source", source_url)
        qapp.processEvents()
        return bool(item.property("loaded"))
    finally:
        item.deleteLater()
        qapp.processEvents()


def test_pdf_preview_url_renders_the_page_through_qml_for_hostile_paths(qapp, tmp_path: Path) -> None:  # noqa: ANN001
    pdf_dir = tmp_path / _HOSTILE_DIRECTORY
    pdf_dir.mkdir()
    pdf_path = pdf_dir / f"{_HOSTILE_STEM}.pdf"
    _write_pdf(pdf_path)
    info = describe_pdf_preview(str(pdf_path), 1)
    assert info["state"] == "ready"

    engine = QQmlEngine()
    provider = _RecordingPdfProvider()
    engine.addImageProvider(LOCAL_PDF_PREVIEW_PROVIDER_ID, provider)

    assert _load_qml_image(engine, str(info["preview_url"]), qapp)
    assert len(provider.images) == 1
    rendered = provider.images[0]
    # A4 fits a 120px square as a portrait page; the error card fills the whole square.
    assert rendered.width() < rendered.height() <= 120
    assert rendered.pixelColor(0, 0) == QColor("white")


def test_media_panel_image_preview_url_loads_through_qml_for_hostile_paths(qapp, tmp_path: Path) -> None:  # noqa: ANN001
    image_dir = tmp_path / _HOSTILE_DIRECTORY
    image_dir.mkdir()
    image_path = image_dir / f"{_HOSTILE_STEM}.png"
    image = QImage(16, 9, QImage.Format.Format_ARGB32)
    image.fill(QColor("#2c85bf"))
    assert image.save(str(image_path))

    class _Node:
        type_id = "media.panel"
        node_id = "media"
        exposed_ports = {"source": False}
        properties = {"source": str(image_path)}

    resolution = resolve_media_panel_source(
        node=_Node(),
        workspace=type("_Workspace", (), {"workspace_id": "ws", "edges": {}})(),
    )
    assert resolution.state == "ready"

    engine = QQmlEngine()
    provider = LocalMediaPreviewImageProvider()
    engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, provider)

    assert _load_qml_image(engine, resolution.preview_source_url, qapp)
