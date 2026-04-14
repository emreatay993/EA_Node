from __future__ import annotations


def _has_tooltip_text(text: object) -> bool:
    return bool(str(text or "").strip())


class TooltipManager:
    def __init__(self, *, info_tooltips_enabled: bool = True) -> None:
        self._info_tooltips_enabled = bool(info_tooltips_enabled)

    @property
    def info_tooltips_enabled(self) -> bool:
        return self._info_tooltips_enabled

    def set_info_tooltips_enabled(self, enabled: bool) -> bool:
        normalized = bool(enabled)
        changed = normalized != self._info_tooltips_enabled
        self._info_tooltips_enabled = normalized
        return changed

    def should_show_info_tooltip(self, text: object) -> bool:
        return self._info_tooltips_enabled and _has_tooltip_text(text)

    def should_show_warning_tooltip(self, text: object) -> bool:
        return _has_tooltip_text(text)

    def should_show_inactive_tooltip(self, text: object) -> bool:
        return _has_tooltip_text(text)


__all__ = ["TooltipManager"]
