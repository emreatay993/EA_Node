# Purpose: Capture automation handler: canvas view PNGs (node shadows off for the grab) and window grabs, inline base64 (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

import base64
import os
import re
import struct
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication, QWidget

from ea_node_editor.automation.errors import CAPTURE_FAILED, NOT_FOUND, AutomationOpError
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.settings import SESSION_STATE_DIR_ENV_VAR
from ea_node_editor.ui.canvas_view_export import CanvasViewExportError
from ea_node_editor.ui.canvas_view_export_compositor import CanvasViewExportCompositeError
from ea_node_editor.ui.shell.automation.context import AutomationContext

CAPTURE_DIR_PREFIX = "corex-capture-"
SETTLE_MS = 150
FIDELITY_OFFSCREEN = "offscreen_layout"
FIDELITY_NATIVE = "native"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_STEM_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")
_CAPTURE_ERRORS = (CanvasViewExportError, CanvasViewExportCompositeError, OSError, RuntimeError, ValueError)

# One per-process default output folder so repeated captures land together.
_default_capture_dir: dict[str, Path] = {}


# ----------------------------------------------------------------- helpers


def default_capture_dir() -> Path:
    path = _default_capture_dir.get("path")
    if path is None or not path.is_dir():
        state_dir = str(os.environ.get(SESSION_STATE_DIR_ENV_VAR) or "").strip()
        if state_dir:
            # Spawned instances: keep captures inside the per-instance session folder so
            # they are removed with it when the instance quits.
            path = Path(state_dir) / "automation_captures"
            path.mkdir(parents=True, exist_ok=True)
        else:
            path = Path(tempfile.mkdtemp(prefix=CAPTURE_DIR_PREFIX))
        _default_capture_dir["path"] = path
    return path


def capture_fidelity() -> str:
    platform = str(os.environ.get("QT_QPA_PLATFORM") or "").strip().lower()
    return FIDELITY_OFFSCREEN if platform.startswith("offscreen") else FIDELITY_NATIVE


def settle_events(duration_ms: int = SETTLE_MS) -> None:
    """Let the QML scene apply pending property changes (shadow toggle, view switch) before grabbing."""
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    loop = QEventLoop()
    QTimer.singleShot(max(0, int(duration_ms)), loop.quit)
    loop.exec()
    if app is not None:
        app.processEvents()


def png_size(path: Path) -> tuple[int, int]:
    """(width, height) from the IHDR chunk; (0, 0) when the file is not a PNG."""
    try:
        with path.open("rb") as handle:
            header = handle.read(24)
    except OSError:
        return (0, 0)
    if len(header) < 24 or not header.startswith(_PNG_SIGNATURE) or header[12:16] != b"IHDR":
        return (0, 0)
    width, height = struct.unpack(">II", header[16:24])
    return (int(width), int(height))


def _sanitized_stem(value: Any, fallback: str) -> str:
    stem = _STEM_SANITIZER.sub("_", str(value or "").strip()).strip("._-")
    return stem or fallback


def _image_row(path: Path, *, view_id: str = "", view_name: str = "", inline: bool, **extra: Any) -> dict[str, Any]:
    width, height = png_size(path)
    row: dict[str, Any] = {
        "path": str(path),
        "width": width,
        "height": height,
        "view_id": view_id,
        "view_name": view_name,
        "size_bytes": path.stat().st_size if path.is_file() else 0,
        **extra,
    }
    if inline:
        row["png_base64"] = base64.b64encode(path.read_bytes()).decode("ascii")
    return row


def _capture_window(context: AutomationContext, host: Any, output_dir: Path, params: Mapping[str, Any], *, inline: bool) -> list[dict[str, Any]]:
    stem = _sanitized_stem(params.get("filename_stem"), "window")
    path = output_dir / f"{stem}.png"
    settle_events()
    # Never grabWindow(): offscreen has no screen. The QML host widget renders the
    # canvas; the whole ShellWindow is the fallback when the host is not a QWidget.
    widget = context.quick_widget if isinstance(context.quick_widget, QWidget) else host
    pixmap = widget.grab()
    if pixmap.isNull():
        raise AutomationOpError(CAPTURE_FAILED, "The window grab produced an empty image.", details={"mode": "window", "widget": type(widget).__name__})
    if not pixmap.save(str(path), "PNG"):
        raise AutomationOpError(CAPTURE_FAILED, f"Could not write the window grab to {path}.", details={"mode": "window", "path": str(path)})
    return [_image_row(path, inline=inline, widget=type(widget).__name__)]


def _capture_views(context: AutomationContext, output_dir: Path, params: Mapping[str, Any], *, inline: bool) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    workspace = context.active_workspace()
    workspace.ensure_default_view()
    requested = [str(view_id or "").strip() for view_id in (params.get("view_ids") or ()) if str(view_id or "").strip()]
    view_ids = requested or [str(workspace.active_view_id)]
    unknown = [view_id for view_id in view_ids if view_id not in workspace.views]
    if unknown:
        raise AutomationOpError(
            NOT_FOUND,
            f"Views {unknown} do not exist in the active workspace '{workspace.workspace_id}'.",
            hint="Call workspace.list for the view ids of the active workspace.",
            details={"view_ids": unknown, "available": list(workspace.views)},
        )
    scale = int(params.get("scale", 1))
    crop_to_content = bool(params.get("crop_to_content", True))
    presenter = context.workspace_presenter
    host = context.require_shell("capture.screenshot")
    preferences = host.app_preferences_controller
    shadow_was_on = bool(presenter.graphics_node_shadow)
    try:
        if shadow_was_on:
            # Offscreen, passive bodies do not render under the QML drop shadow (T00 spike).
            # Apply the change to this window only; never persist it to app_preferences.json,
            # which the user's own settings and other COREX instances share.
            graphics = preferences.graphics_settings()  # already a deep copy
            graphics.setdefault("canvas", {})["node_shadow"] = False
            preferences.apply_graphics_settings_to_host(host, graphics)
        settle_events()
        result = context.canvas_export.capture_canvas_view_pngs(
            view_ids=view_ids,
            output_dir=output_dir,
            scale=scale,
            crop_to_content=crop_to_content,
        )
    except _CAPTURE_ERRORS as exc:
        raise AutomationOpError(
            CAPTURE_FAILED,
            f"Canvas capture failed: {exc}",
            details={"mode": "views", "view_ids": view_ids, "reason": str(exc), "exception": type(exc).__name__},
        ) from exc
    finally:
        if shadow_was_on:
            preferences.apply_graphics_settings_to_host(host)
    images = [
        _image_row(
            Path(export.path),
            view_id=str(export.view_id),
            view_name=str(export.view_name),
            inline=inline,
            output_pixel_size=[int(export.output_pixel_size[0]), int(export.output_pixel_size[1])],
            device_pixel_ratio=float(export.device_pixel_ratio),
        )
        for export in result.exports
    ]
    failures = [{"view": str(failure.view_name), "message": str(failure.message)} for failure in result.failures]
    if not images:
        raise AutomationOpError(CAPTURE_FAILED, "No view could be captured.", details={"mode": "views", "view_ids": view_ids, "failures": failures})
    return images, failures


# ---------------------------------------------------------------- handlers


def screenshot(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "capture.screenshot"
    host = context.require_shell(op)
    mode = str(params.get("mode") or "views")
    inline = bool(params.get("inline", True))
    requested_dir = str(params.get("output_dir") or "").strip()
    output_dir = Path(requested_dir).expanduser() if requested_dir else default_capture_dir()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AutomationOpError(CAPTURE_FAILED, f"Cannot create output_dir {output_dir}: {exc}", details={"output_dir": str(output_dir)}) from exc
    failures: list[dict[str, str]] = []
    if mode == "window":
        images = _capture_window(context, host, output_dir, params, inline=inline)
    else:
        images, failures = _capture_views(context, output_dir, params, inline=inline)
    return {
        "images": images,
        "mode": mode,
        "fidelity": capture_fidelity(),
        "output_dir": str(output_dir),
        "failures": failures,
    }


HANDLERS = {
    'capture.screenshot': screenshot,
}

__all__ = ["CAPTURE_DIR_PREFIX", "HANDLERS", "capture_fidelity", "default_capture_dir", "png_size", "settle_events"]
