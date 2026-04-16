from __future__ import annotations


def _coerce_dimension(value: object, *, fallback: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return fallback
    return numeric if numeric > 0 else fallback


def scalar_bar_args_for_viewport(
    viewport_width: object,
    viewport_height: object,
) -> dict[str, int | float | bool]:
    width = _coerce_dimension(viewport_width, fallback=320)
    height = _coerce_dimension(viewport_height, fallback=240)
    shortest_side = min(width, height)

    if shortest_side < 180:
        title_font_size = 9
        label_font_size = 8
        bar_height = 0.40
        bar_width = 0.08
        position_x = 0.88
        position_y = 0.12
    elif shortest_side < 260:
        title_font_size = 10
        label_font_size = 8
        bar_height = 0.46
        bar_width = 0.09
        position_x = 0.87
        position_y = 0.10
    else:
        title_font_size = 11
        label_font_size = 9
        bar_height = 0.52
        bar_width = 0.10
        position_x = 0.86
        position_y = 0.08

    return {
        "vertical": True,
        "title_font_size": title_font_size,
        "label_font_size": label_font_size,
        "height": bar_height,
        "width": bar_width,
        "position_x": position_x,
        "position_y": position_y,
    }


__all__ = ["scalar_bar_args_for_viewport"]
