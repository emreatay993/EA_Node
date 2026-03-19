from __future__ import annotations

from importlib import import_module


_IMPLEMENTATION_MODULE = import_module("ea_node_editor.ui.perf.performance_harness")

__all__ = [name for name in dir(_IMPLEMENTATION_MODULE) if not name.startswith("__")]

globals().update(
    {
        name: getattr(_IMPLEMENTATION_MODULE, name)
        for name in __all__
    }
)


if __name__ == "__main__":
    raise SystemExit(main())
