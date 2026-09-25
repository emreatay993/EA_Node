# Purpose: CorexClient facade for node.* (fit_text included) plus sugar: add_path_pointer, add_panel, set_text_style.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_nodes.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

from ea_node_editor.text_style import rich_text_format_property_key, rich_text_style_property_key

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient

PATH_POINTER_TYPE_ID = "io.path_pointer"
PANEL_TYPE_ID = "data.panel"
_TEXT_STYLE_ALIASES = {"color": "text_color"}
# node.fit_text waits server-side (catalog default 5 s); the request waits that long plus a margin.
_FIT_TEXT_DEFAULT_WAIT_S = 5.0
_FIT_TEXT_REQUEST_MARGIN_S = 5.0


def _compact(params: Mapping[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values so omitted keyword arguments never reach the closed param schemas."""
    return {key: value for key, value in params.items() if value is not None}


def _placement(
    *,
    title: str | None,
    width: float | None,
    height: float | None,
    parent_node_id: str | None,
    select: bool | None,
) -> dict[str, Any]:
    return _compact(
        {
            "title": None if title is None else str(title),
            "width": None if width is None else float(width),
            "height": None if height is None else float(height),
            "parent_node_id": None if parent_node_id is None else str(parent_node_id),
            "select": None if select is None else bool(select),
        }
    )


class NodesApi:
    """Facade for node.* plus sugar: add_path_pointer, add_panel, set_text_style.

    Every method builds catalog params and returns ``client.call(op, params)``;
    the server validates, so the facade never re-implements rules.
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    # ---------------------------------------------------------------- node.add*

    def add(
        self,
        type_id: str,
        x: float,
        y: float,
        *,
        title: str | None = None,
        width: float | None = None,
        height: float | None = None,
        parent_node_id: str | None = None,
        select: bool | None = None,
        properties: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"type_id": str(type_id), "x": float(x), "y": float(y)}
        params.update(_placement(title=title, width=width, height=height, parent_node_id=parent_node_id, select=select))
        if properties is not None:
            params["properties"] = dict(properties)
        return self._client.call("node.add", params)

    def add_text(
        self,
        markdown: str,
        x: float,
        y: float,
        *,
        format: str | None = None,  # noqa: A002 - mirrors the catalog param name
        style: Mapping[str, Any] | None = None,
        title: str | None = None,
        width: float | None = None,
        height: float | None = None,
        parent_node_id: str | None = None,
        select: bool | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"markdown": str(markdown), "x": float(x), "y": float(y)}
        params.update(_placement(title=title, width=width, height=height, parent_node_id=parent_node_id, select=select))
        if format is not None:
            params["format"] = str(format)
        if style is not None:
            params["style"] = dict(style)
        return self._client.call("node.add_text", params)

    def add_media(
        self,
        path: str,
        x: float,
        y: float,
        *,
        fit_mode: str | None = None,
        show_title: bool | None = None,
        show_frame: bool | None = None,
        title: str | None = None,
        width: float | None = None,
        height: float | None = None,
        parent_node_id: str | None = None,
        select: bool | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"path": str(path), "x": float(x), "y": float(y)}
        params.update(_placement(title=title, width=width, height=height, parent_node_id=parent_node_id, select=select))
        params.update(
            _compact(
                {
                    "fit_mode": None if fit_mode is None else str(fit_mode),
                    "show_title": None if show_title is None else bool(show_title),
                    "show_frame": None if show_frame is None else bool(show_frame),
                }
            )
        )
        return self._client.call("node.add_media", params)

    def add_web_panel(
        self,
        x: float,
        y: float,
        *,
        url: str | None = None,
        html: str | None = None,
        display_mode: str | None = None,
        title: str | None = None,
        width: float | None = None,
        height: float | None = None,
        parent_node_id: str | None = None,
        select: bool | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"x": float(x), "y": float(y)}
        params.update(_placement(title=title, width=width, height=height, parent_node_id=parent_node_id, select=select))
        params.update(
            _compact(
                {
                    "url": None if url is None else str(url),
                    "html": None if html is None else str(html),
                    "display_mode": None if display_mode is None else str(display_mode),
                }
            )
        )
        return self._client.call("node.add_web_panel", params)

    # -------------------------------------------------------------- node.update

    def update(
        self,
        node_id: str,
        *,
        title: str | None = None,
        x: float | None = None,
        y: float | None = None,
        width: float | None = None,
        height: float | None = None,
        properties: Mapping[str, Any] | None = None,
        port_labels: Mapping[str, str] | None = None,
        exposed_ports: Mapping[str, bool] | None = None,
        collapsed: bool | None = None,
        locked: bool | None = None,
        move_contents: bool | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"node_id": str(node_id)}
        params.update(
            _compact(
                {
                    "title": None if title is None else str(title),
                    "x": None if x is None else float(x),
                    "y": None if y is None else float(y),
                    "width": None if width is None else float(width),
                    "height": None if height is None else float(height),
                    "properties": None if properties is None else dict(properties),
                    "port_labels": None if port_labels is None else {str(k): str(v) for k, v in port_labels.items()},
                    "exposed_ports": None if exposed_ports is None else {str(k): bool(v) for k, v in exposed_ports.items()},
                    "collapsed": None if collapsed is None else bool(collapsed),
                    "locked": None if locked is None else bool(locked),
                    "move_contents": None if move_contents is None else bool(move_contents),
                }
            )
        )
        return self._client.call("node.update", params)

    # ----------------------------------------------------------- node.set_style

    def set_style(
        self,
        node_id: str,
        style: Mapping[str, Any] | None = None,
        *,
        preset: str | None = None,
        replace: bool = False,
        clear: bool = False,
        propagate: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "node_id": str(node_id),
            "replace": bool(replace),
            "clear": bool(clear),
            "propagate": bool(propagate),
        }
        if style is not None:
            params["style"] = dict(style)
        if preset is not None:
            params["preset"] = str(preset)
        return self._client.call("node.set_style", params)

    def fit_text(self, node_id: str, mode: str | None = None, *, timeout_s: float | None = None) -> dict[str, Any]:
        """node.fit_text: set a flowchart shape's text fit (clip | grow | shrink) and read how its body fits.

        Omit ``mode`` to only report. The server waits up to ``timeout_s`` (default 5 s) for the canvas
        to draw the shape, so the request itself waits a little longer than that.
        """
        params = _compact(
            {
                "node_id": str(node_id),
                "mode": None if mode is None else str(mode),
                "timeout_s": None if timeout_s is None else float(timeout_s),
            }
        )
        wait_s = float(timeout_s if timeout_s is not None else _FIT_TEXT_DEFAULT_WAIT_S)
        return self._client.call("node.fit_text", params, timeout_s=wait_s + _FIT_TEXT_REQUEST_MARGIN_S)

    # ------------------------------------------------------ node.delete/duplicate

    def delete(self, node_ids: str | Iterable[str]) -> dict[str, Any]:
        ids = [node_ids] if isinstance(node_ids, str) else [str(node_id) for node_id in node_ids]
        return self._client.call("node.delete", {"node_ids": ids})

    def duplicate(
        self,
        node_ids: str | Iterable[str],
        *,
        offset_x: float | None = None,
        offset_y: float | None = None,
    ) -> dict[str, Any]:
        ids = [node_ids] if isinstance(node_ids, str) else [str(node_id) for node_id in node_ids]
        params: dict[str, Any] = {"node_ids": ids}
        params.update(
            _compact(
                {
                    "offset_x": None if offset_x is None else float(offset_x),
                    "offset_y": None if offset_y is None else float(offset_y),
                }
            )
        )
        return self._client.call("node.duplicate", params)

    # ------------------------------------------------------------------- sugar

    def add_path_pointer(self, path: str, x: float, y: float, mode: str = "file", **kwargs: Any) -> dict[str, Any]:
        """node.add io.path_pointer with ``properties.path`` / ``properties.mode`` (file | folder)."""
        properties = dict(kwargs.pop("properties", None) or {})
        properties.update({"path": str(path), "mode": str(mode)})
        return self.add(PATH_POINTER_TYPE_ID, x, y, properties=properties, **kwargs)

    def add_panel(self, x: float, y: float, **kwargs: Any) -> dict[str, Any]:
        """node.add data.panel (text / data display panel)."""
        return self.add(PANEL_TYPE_ID, x, y, **kwargs)

    def set_text_style(self, node_id: str, content_key: str = "body", **style: Any) -> dict[str, Any]:
        """node.update with rich-text slot keys (``<content_key>_<style_key>``; bare keys for content_key 'text').

        ``format`` maps to the slot format key and ``color`` is an alias for ``text_color``.
        """
        properties: dict[str, Any] = {}
        for raw_key, value in style.items():
            key = _TEXT_STYLE_ALIASES.get(str(raw_key), str(raw_key))
            if key == "format":
                properties[rich_text_format_property_key(content_key)] = value
            else:
                properties[rich_text_style_property_key(content_key, key)] = value
        return self.update(node_id, properties=properties)


__all__ = ["NodesApi", "PANEL_TYPE_ID", "PATH_POINTER_TYPE_ID"]
