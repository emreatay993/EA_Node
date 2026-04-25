from __future__ import annotations

from ea_node_editor.ui.theme.registry import DEFAULT_THEME_ID, ThemeDefinition, resolve_theme


class ShellThemeService:
    def __init__(self, *, theme_id: object = DEFAULT_THEME_ID) -> None:
        self._theme = resolve_theme(theme_id)

    @property
    def theme(self) -> ThemeDefinition:
        return self._theme

    @property
    def theme_id(self) -> str:
        return self._theme.theme_id

    @property
    def label(self) -> str:
        return self._theme.label

    def palette(self) -> dict[str, str]:
        return self._theme.tokens.as_dict()

    def token(self, name: object) -> str:
        return str(self.palette().get(str(name).strip(), ""))

    def apply_theme(self, theme_id: object) -> bool:
        resolved = resolve_theme(theme_id)
        if resolved == self._theme:
            return False
        self._theme = resolved
        return True


__all__ = ["ShellThemeService"]
