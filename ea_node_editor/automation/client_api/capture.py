# Purpose: CorexClient facade for capture.screenshot plus screenshot_to / save_png helpers that decode inline PNGs.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

import base64
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient


def _compact(params: Mapping[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values so omitted keyword arguments never reach the closed param schemas."""
    return {key: value for key, value in params.items() if value is not None}


def save_png(image: Mapping[str, Any], path: str | Path) -> Path:
    """Write an image row's ``png_base64`` to ``path`` (ValueError when the row carries no inline data)."""
    encoded = str(image.get("png_base64") or "")
    if not encoded:
        raise ValueError("the image row has no png_base64 payload; call screenshot(inline=True)")
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(encoded))
    return target


class CaptureApi:
    """Facade for capture.screenshot (+ save_png helper).

    Every method builds catalog params and returns ``client.call(op, params)``;
    the server validates, so the facade never re-implements rules.
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    def screenshot(
        self,
        *,
        mode: str | None = None,
        view_ids: str | Iterable[str] | None = None,
        scale: int | None = None,
        crop_to_content: bool | None = None,
        output_dir: str | Path | None = None,
        filename_stem: str | None = None,
        inline: bool | None = None,
    ) -> dict[str, Any]:
        """Render canvas views (default: the active view) or grab the window; returns paths and inline PNGs."""
        ids = None if view_ids is None else ([view_ids] if isinstance(view_ids, str) else [str(value) for value in view_ids])
        params = _compact(
            {
                "mode": None if mode is None else str(mode),
                "view_ids": ids,
                "scale": None if scale is None else int(scale),
                "crop_to_content": None if crop_to_content is None else bool(crop_to_content),
                "output_dir": None if output_dir is None else str(output_dir),
                "filename_stem": None if filename_stem is None else str(filename_stem),
                "inline": None if inline is None else bool(inline),
            }
        )
        return self._client.call("capture.screenshot", params)

    def screenshot_to(self, path_or_dir: str | Path, **kwargs: Any) -> dict[str, Any]:
        """Screenshot into ``path_or_dir`` and make sure the PNG files exist on this machine.

        A ``.png`` path selects mode=window with that file stem; anything else is the
        output directory. The server writes the files itself when it shares the file
        system; when it does not (or ``png_base64`` came back inline for a different
        machine), the inline data is decoded into the same paths. The result gains
        ``saved_paths``.
        """
        target = Path(path_or_dir).expanduser()
        if target.suffix.lower() == ".png":
            kwargs.setdefault("mode", "window")
            kwargs.setdefault("filename_stem", target.stem)
            output_dir = target.parent
        else:
            output_dir = target
        kwargs.setdefault("inline", True)
        result = self.screenshot(output_dir=output_dir, **kwargs)
        saved: list[str] = []
        for image in result.get("images", []):
            reported = Path(str(image.get("path") or ""))
            local = reported if reported.is_file() else output_dir / (reported.name or "capture.png")
            if not local.is_file() and image.get("png_base64"):
                local = save_png(image, local)
            saved.append(str(local))
        result["saved_paths"] = saved
        return result


__all__ = ["CaptureApi", "save_png"]
