__all__ = ["ShellWindow"]


def __getattr__(name: str):
    if name == "ShellWindow":
        from ea_node_editor.ui.shell.window import ShellWindow

        return ShellWindow
    raise AttributeError(name)
