from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    app_bg: str
    app_fg: str
    panel_bg: str
    panel_alt_bg: str
    toolbar_bg: str
    border: str
    hover: str
    pressed: str
    input_bg: str
    input_border: str
    input_fg: str
    accent: str
    accent_strong: str
    status_bg: str
    status_border: str
    status_fg: str
    canvas_bg: str
    canvas_minor_grid: str
    canvas_major_grid: str


STITCH_DARK_V1 = ThemeTokens(
    app_bg="#1f1f1f",
    app_fg="#e8e8e8",
    panel_bg="#1b1d22",
    panel_alt_bg="#24262c",
    toolbar_bg="#2a2b30",
    border="#3a3d45",
    hover="#33373f",
    pressed="#2d3139",
    input_bg="#22242a",
    input_border="#4a4f5a",
    input_fg="#f0f2f5",
    accent="#60CDFF",
    accent_strong="#1D8CE0",
    status_bg="#24a2dc",
    status_border="#1b7daf",
    status_fg="#ffffff",
    canvas_bg="#1d1f24",
    canvas_minor_grid="#2b2f38",
    canvas_major_grid="#323746",
)

