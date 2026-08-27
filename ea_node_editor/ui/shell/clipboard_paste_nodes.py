from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QMimeData, QUrl
from PyQt6.QtGui import QImage

from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_TEXT_TYPE_ID
from ea_node_editor.nodes.builtins.media_panel import MEDIA_PANEL_TYPE_ID
from ea_node_editor.nodes.builtins.passive_mail import (
    PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID,
)
from ea_node_editor.nodes.file_dialog_filters import (
    MAIL_FILE_SUFFIXES,
    media_kind_from_source,
)
from ea_node_editor.nodes.builtins.web_viewer import (
    WEB_PAGE_VIEWER_START_LOCATION_PROPERTY,
    WEB_PAGE_VIEWER_TYPE_ID,
)
from ea_node_editor.ui.shell.runtime_clipboard import parse_graph_fragment_payload

_MEDIA_SOURCE_PROPERTY = "source"
_SOURCE_PATH_PROPERTY = "source_path"
_TEXT_PROPERTY = "text"
_TEXT_FORMAT_PROPERTY = "format"
_TABULAR_INPUT_NODE_TYPE_ID = "tabular.input"
_TABULAR_INPUT_PATH_PROPERTY = "path"

_MAIL_SUFFIXES = frozenset(MAIL_FILE_SUFFIXES)
_HTML_SUFFIXES = frozenset({".html", ".htm", ".xhtml"})

_IMAGE_MIME_SUFFIXES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/bmp": ".bmp",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/tiff": ".tiff",
}
_VIDEO_MIME_SUFFIXES = {
    "video/mp4": ".mp4",
    "video/x-m4v": ".m4v",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-matroska": ".mkv",
    "video/webm": ".webm",
    "video/x-ms-wmv": ".wmv",
}


@dataclass(frozen=True, slots=True)
class ClipboardBytePayload:
    property_key: str
    data: bytes
    filename: str
    mime_type: str
    artifact_prefix: str
    subdirectory: str
    artifact_kind: str

    def signature_payload(self) -> dict[str, Any]:
        return {
            "property_key": self.property_key,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "artifact_prefix": self.artifact_prefix,
            "subdirectory": self.subdirectory,
            "artifact_kind": self.artifact_kind,
            "size": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(),
        }


@dataclass(frozen=True, slots=True)
class ClipboardPasteItem:
    type_id: str
    properties: dict[str, Any]
    artifact: ClipboardBytePayload | None = None

    def signature_payload(self) -> dict[str, Any]:
        return {
            "type_id": self.type_id,
            "properties": self.properties,
            "artifact": None if self.artifact is None else self.artifact.signature_payload(),
        }


@dataclass(frozen=True, slots=True)
class ClipboardTablePasteItems:
    tabular: ClipboardPasteItem
    markdown: ClipboardPasteItem


def classify_clipboard_paste_items(mime_data: QMimeData | None) -> tuple[ClipboardPasteItem, ...]:
    if mime_data is None:
        return ()

    url_items = _items_from_urls(mime_data.urls()) if mime_data.hasUrls() else ()
    if url_items and (_has_local_file_url(mime_data.urls()) or not _has_html_fragment(mime_data)):
        return url_items

    image_item = _image_item_from_qimage(mime_data)
    if image_item is not None:
        return (image_item,)

    byte_item = _byte_item_from_mime_data(mime_data)
    if byte_item is not None:
        return (byte_item,)

    text = ""
    if mime_data.hasText():
        text = str(mime_data.text() or "")
        if parse_graph_fragment_payload(text) is not None:
            return ()
        url_item = _item_from_plain_text_url(text)
        if url_item is not None:
            return (url_item,)

    if _has_html_fragment(mime_data):
        html_url_item = _single_remote_href_item_from_html(mime_data.html())
        if html_url_item is not None:
            return (html_url_item,)
        markdown_text = html_to_markdownish(mime_data.html())
        if markdown_text:
            return (
                ClipboardPasteItem(
                    type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
                    properties={
                        _TEXT_PROPERTY: markdown_text,
                        _TEXT_FORMAT_PROPERTY: "markdown",
                    },
                ),
            )

    if text.strip():
        return (
            ClipboardPasteItem(
                type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
                properties={
                    _TEXT_PROPERTY: text,
                    _TEXT_FORMAT_PROPERTY: "plain",
                },
            ),
        )

    return url_items


def clipboard_table_paste_items(mime_data: QMimeData | None) -> ClipboardTablePasteItems | None:
    rows = _table_rows_from_clipboard(mime_data)
    if not rows:
        return None
    return ClipboardTablePasteItems(
        tabular=ClipboardPasteItem(
            type_id=_TABULAR_INPUT_NODE_TYPE_ID,
            properties={},
            artifact=ClipboardBytePayload(
                property_key=_TABULAR_INPUT_PATH_PROPERTY,
                data=_rows_to_tsv_bytes(rows),
                filename="clipboard-table.tsv",
                mime_type="text/tab-separated-values",
                artifact_prefix="clipboard_table",
                subdirectory="tabular",
                artifact_kind="clipboard_table_source",
            ),
        ),
        markdown=ClipboardPasteItem(
            type_id=PASSIVE_ANNOTATION_TEXT_TYPE_ID,
            properties={
                _TEXT_PROPERTY: _rows_to_markdown_table(rows),
                _TEXT_FORMAT_PROPERTY: "markdown",
            },
        ),
    )


def clipboard_paste_items_signature(items: tuple[ClipboardPasteItem, ...]) -> str:
    if not items:
        return ""
    return json.dumps(
        [item.signature_payload() for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def html_to_markdownish(raw_html: str) -> str:
    parser = _MarkdownishHTMLParser()
    try:
        parser.feed(str(raw_html or ""))
        parser.close()
    except Exception:  # noqa: BLE001
        return ""
    return _normalize_markdownish_text(parser.text())


def _table_rows_from_clipboard(mime_data: QMimeData | None) -> tuple[tuple[str, ...], ...]:
    if mime_data is None:
        return ()
    text = str(mime_data.text() or "") if mime_data.hasText() else ""
    if "\t" in text:
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
        rows = _normalize_table_rows(csv.reader(StringIO(normalized_text), delimiter="\t"))
        if rows:
            return rows
    if _has_html_fragment(mime_data):
        return _table_rows_from_html(mime_data.html())
    return ()


def _table_rows_from_html(raw_html: str) -> tuple[tuple[str, ...], ...]:
    parser = _TableHTMLParser()
    try:
        parser.feed(str(raw_html or ""))
        parser.close()
    except Exception:  # noqa: BLE001
        return ()
    for rows in parser.tables:
        normalized = _normalize_table_rows(rows)
        if normalized:
            return normalized
    return ()


def _normalize_table_rows(rows: Any) -> tuple[tuple[str, ...], ...]:
    normalized = [tuple(str(cell) for cell in row) for row in rows if row]
    while normalized and not any(cell.strip() for cell in normalized[-1]):
        normalized.pop()
    if not normalized:
        return ()
    width = max(len(row) for row in normalized)
    if width < 2 and len(normalized) < 2:
        return ()
    return tuple(tuple(row[index] if index < len(row) else "" for index in range(width)) for row in normalized)


def _rows_to_tsv_bytes(rows: tuple[tuple[str, ...], ...]) -> bytes:
    stream = StringIO()
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _rows_to_markdown_table(rows: tuple[tuple[str, ...], ...]) -> str:
    header, *body = rows
    lines = [
        _markdown_row(header),
        _markdown_row(["---"] * len(header)),
    ]
    lines.extend(_markdown_row(row) for row in body)
    return "\n".join(lines)


def _markdown_row(row: Any) -> str:
    return "| " + " | ".join(_markdown_cell(cell) for cell in row) + " |"


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", r"\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _single_remote_href_item_from_html(raw_html: str) -> ClipboardPasteItem | None:
    parser = _HrefHTMLParser()
    try:
        parser.feed(str(raw_html or ""))
        parser.close()
    except Exception:  # noqa: BLE001
        return None
    urls: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        normalized = html.unescape(str(href or "")).strip()
        if not _is_remote_url(normalized) or normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)
    return _item_from_remote_url(urls[0]) if len(urls) == 1 else None


def _has_html_fragment(mime_data: QMimeData) -> bool:
    return bool(mime_data.hasHtml() and str(mime_data.html() or "").strip())


def _has_local_file_url(urls: list[QUrl]) -> bool:
    return any(url.isLocalFile() for url in urls)


def _items_from_urls(urls: list[QUrl]) -> tuple[ClipboardPasteItem, ...]:
    items: list[ClipboardPasteItem] = []
    for url in urls:
        item = _item_from_url(url)
        if item is not None:
            items.append(item)
    return tuple(items)


def _item_from_url(url: QUrl) -> ClipboardPasteItem | None:
    if url.isLocalFile():
        path = str(url.toLocalFile() or "").strip()
        if not path:
            return None
        return _item_from_path(path)

    normalized = str(url.toString() or "").strip()
    if not _is_remote_url(normalized):
        return None
    return _item_from_remote_url(normalized)


def _item_from_path(path: str) -> ClipboardPasteItem | None:
    suffix = Path(path).suffix.lower()
    target = _target_for_suffix(suffix)
    if target is None:
        return None
    type_id, property_key = target
    return ClipboardPasteItem(type_id=type_id, properties={property_key: path})


def _item_from_remote_url(url: str) -> ClipboardPasteItem:
    suffix = PurePosixPath(unquote(urlparse(url).path or "")).suffix.lower()
    target = _target_for_suffix(suffix)
    if target is None:
        target = (WEB_PAGE_VIEWER_TYPE_ID, WEB_PAGE_VIEWER_START_LOCATION_PROPERTY)
    type_id, property_key = target
    return ClipboardPasteItem(type_id=type_id, properties={property_key: url})


def _item_from_plain_text_url(text: str) -> ClipboardPasteItem | None:
    normalized = str(text or "").strip()
    if not normalized or any(character.isspace() for character in normalized):
        return None
    url = QUrl(normalized)
    if url.isLocalFile():
        local_path = str(url.toLocalFile() or "").strip()
        return _item_from_path(local_path) if local_path else None
    if not _is_remote_url(normalized):
        return None
    return _item_from_remote_url(normalized)


def _is_remote_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _target_for_suffix(suffix: str) -> tuple[str, str] | None:
    if media_kind_from_source(f"source{suffix}"):
        return MEDIA_PANEL_TYPE_ID, _MEDIA_SOURCE_PROPERTY
    if suffix in _MAIL_SUFFIXES:
        return PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID, _SOURCE_PATH_PROPERTY
    if suffix in _HTML_SUFFIXES:
        return WEB_PAGE_VIEWER_TYPE_ID, WEB_PAGE_VIEWER_START_LOCATION_PROPERTY
    return None


def _image_item_from_qimage(mime_data: QMimeData) -> ClipboardPasteItem | None:
    if not mime_data.hasImage():
        return None
    image_data = mime_data.imageData()
    image: QImage | None = None
    if isinstance(image_data, QImage):
        image = image_data
    elif hasattr(image_data, "toImage"):
        candidate = image_data.toImage()
        if isinstance(candidate, QImage):
            image = candidate
    if image is None or image.isNull():
        return None
    data = _qimage_to_png_bytes(image)
    if not data:
        return None
    return ClipboardPasteItem(
        type_id=MEDIA_PANEL_TYPE_ID,
        properties={},
        artifact=ClipboardBytePayload(
            property_key=_MEDIA_SOURCE_PROPERTY,
            data=data,
            filename="clipboard-image.png",
            mime_type="image/png",
            artifact_prefix="clipboard_image",
            subdirectory="media",
            artifact_kind="clipboard_image_source",
        ),
    )


def _qimage_to_png_bytes(image: QImage) -> bytes:
    buffer_data = QByteArray()
    buffer = QBuffer(buffer_data)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        return b""
    try:
        if not image.save(buffer, "PNG", 100):
            return b""
        return bytes(buffer_data)
    finally:
        buffer.close()


def _byte_item_from_mime_data(mime_data: QMimeData) -> ClipboardPasteItem | None:
    for mime_type in mime_data.formats():
        normalized_mime = str(mime_type or "").strip().lower()
        target = _target_for_mime_type(normalized_mime)
        if target is None:
            continue
        raw_data = bytes(mime_data.data(mime_type))
        if not raw_data:
            continue
        type_id, property_key, filename, artifact_prefix, subdirectory, artifact_kind = target
        return ClipboardPasteItem(
            type_id=type_id,
            properties={},
            artifact=ClipboardBytePayload(
                property_key=property_key,
                data=raw_data,
                filename=filename,
                mime_type=normalized_mime,
                artifact_prefix=artifact_prefix,
                subdirectory=subdirectory,
                artifact_kind=artifact_kind,
            ),
        )
    return None


def _target_for_mime_type(mime_type: str) -> tuple[str, str, str, str, str, str] | None:
    if mime_type == "application/pdf":
        return (
            MEDIA_PANEL_TYPE_ID,
            _MEDIA_SOURCE_PROPERTY,
            "clipboard-document.pdf",
            "clipboard_pdf",
            "media",
            "clipboard_pdf_source",
        )
    if mime_type in _IMAGE_MIME_SUFFIXES:
        suffix = _IMAGE_MIME_SUFFIXES[mime_type]
        return (
            MEDIA_PANEL_TYPE_ID,
            _MEDIA_SOURCE_PROPERTY,
            f"clipboard-image{suffix}",
            "clipboard_image",
            "media",
            "clipboard_image_source",
        )
    if mime_type in _VIDEO_MIME_SUFFIXES:
        suffix = _VIDEO_MIME_SUFFIXES[mime_type]
        return (
            MEDIA_PANEL_TYPE_ID,
            _MEDIA_SOURCE_PROPERTY,
            f"clipboard-video{suffix}",
            "clipboard_video",
            "media",
            "clipboard_video_source",
        )
    return None


class _MarkdownishHTMLParser(HTMLParser):
    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "dl",
        "dt",
        "dd",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "main",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }
    _SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if normalized == "br":
            self._parts.append("\n")
        elif normalized == "li":
            self._parts.append("\n- ")
        elif normalized in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if normalized in self._BLOCK_TAGS or normalized == "li":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._parts.append(html.unescape(data))

    def text(self) -> str:
        return "".join(self._parts)


class _HrefHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)
                return


class _TableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized == "table":
            if self._table_depth == 0:
                self._current_table = []
            self._table_depth += 1
            return
        if self._table_depth != 1:
            return
        if normalized == "tr":
            self._current_row = []
        elif normalized in {"td", "th"} and self._current_row is not None:
            self._current_cell = []
        elif normalized == "br" and self._current_cell is not None:
            self._current_cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            self._current_row.append(_normalize_cell_text("".join(self._current_cell)))
            self._current_cell = None
            return
        if normalized == "tr" and self._current_row is not None and self._current_table is not None:
            self._current_table.append(self._current_row)
            self._current_row = None
            return
        if normalized == "table" and self._table_depth:
            self._table_depth -= 1
            if self._table_depth == 0 and self._current_table is not None:
                self.tables.append(self._current_table)
                self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)


def _normalize_cell_text(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t\f\v]+", " ", normalized).strip()


def _normalize_markdownish_text(text: str) -> str:
    lines = [
        re.sub(r"[ \t\f\v]+", " ", line).strip()
        for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    normalized_lines: list[str] = []
    previous_blank = True
    for line in lines:
        if not line:
            if not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(line)
        previous_blank = False
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    return "\n".join(normalized_lines).strip()


__all__ = [
    "ClipboardBytePayload",
    "ClipboardPasteItem",
    "ClipboardTablePasteItems",
    "classify_clipboard_paste_items",
    "clipboard_paste_items_signature",
    "clipboard_table_paste_items",
    "html_to_markdownish",
]
