from __future__ import annotations

from dataclasses import asdict, dataclass


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
    muted_fg: str
    group_title_fg: str
    panel_title_fg: str
    tab_bg: str
    tab_fg: str
    tab_selected_bg: str
    tab_selected_fg: str
    console_bg: str
    splitter_handle: str
    splitter_handle_hover: str
    scrollbar_handle: str
    status_hover_bg: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


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
    muted_fg="#d0d5de",
    group_title_fg="#bdc5d3",
    panel_title_fg="#f0f4fb",
    tab_bg="#2a2d34",
    tab_fg="#d8deea",
    tab_selected_bg="#2f343e",
    tab_selected_fg="#f2f4f8",
    console_bg="#15181d",
    splitter_handle="#272b33",
    splitter_handle_hover="#323742",
    scrollbar_handle="#4d5361",
    status_hover_bg="rgba(255, 255, 255, 0.13)",
)


STITCH_LIGHT_V1 = ThemeTokens(
    app_bg="#eef2f6",
    app_fg="#17212b",
    panel_bg="#f5f7fa",
    panel_alt_bg="#ffffff",
    toolbar_bg="#e5ebf2",
    border="#b7c2ce",
    hover="#dbe4ee",
    pressed="#cfd9e6",
    input_bg="#ffffff",
    input_border="#96a6ba",
    input_fg="#17212b",
    accent="#1D8CE0",
    accent_strong="#b9dcf7",
    status_bg="#dceefb",
    status_border="#9ec8e5",
    status_fg="#173449",
    canvas_bg="#f3f5f8",
    canvas_minor_grid="#d9dfe8",
    canvas_major_grid="#c0c9d6",
    muted_fg="#5f6b7a",
    group_title_fg="#4f5e70",
    panel_title_fg="#1b2733",
    tab_bg="#dce4ec",
    tab_fg="#314154",
    tab_selected_bg="#edf3f8",
    tab_selected_fg="#162231",
    console_bg="#ffffff",
    splitter_handle="#c3ccd8",
    splitter_handle_hover="#abb8c8",
    scrollbar_handle="#98a6b8",
    status_hover_bg="rgba(0, 0, 0, 0.08)",
)
