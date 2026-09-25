# Purpose: Resolve a node's drawn canvas surface for automation handlers that need surface-owned facts (flowchart text fit).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
"""Drawn-surface lookup for automation handlers.

The shell canvas (QML object ``graphCanvas``) maps node ids to hosts with
``hostForNodeId``; a host's ``loadedSurfaceItem`` is the surface it has drawn and
stays null while the node is outside the loaded view, collapsed, or still loading.
Surface functions run synchronously on the GUI thread, so mutations they make
(a grow-to-fit resize) land in the calling op's undo step.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject, QObject, Qt
from PyQt6.QtQml import QJSValue

GRAPH_CANVAS_OBJECT_NAME = "graphCanvas"
FLOWCHART_SURFACE_OBJECT_NAME = "graphNodeFlowchartSurface"


def _qobject(value: Any) -> QObject | None:
    if isinstance(value, QJSValue):
        value = value.toQObject() if value.isQObject() else None
    return value if isinstance(value, QObject) else None


def _invoke(target: QObject, function_name: str, *args: Any) -> Any:
    try:
        return QMetaObject.invokeMethod(
            target,
            function_name,
            Qt.ConnectionType.DirectConnection,
            Q_RETURN_ARG("QVariant"),
            *(Q_ARG("QVariant", value) for value in args),
        )
    except (RuntimeError, TypeError):
        return None


def drawn_node_surface(quick_widget: Any, node_id: str) -> QObject | None:
    """The surface the shell canvas has drawn for ``node_id``, or None when it has not drawn one."""
    root = quick_widget.rootObject() if quick_widget is not None and hasattr(quick_widget, "rootObject") else None
    canvas = root.findChild(QObject, GRAPH_CANVAS_OBJECT_NAME) if root is not None else None
    if canvas is None:
        return None
    host = _qobject(_invoke(canvas, "hostForNodeId", str(node_id)))
    return _qobject(host.property("loadedSurfaceItem")) if host is not None else None


def drawn_flowchart_surface(quick_widget: Any, node_id: str) -> QObject | None:
    """``drawn_node_surface`` narrowed to flowchart shapes."""
    surface = drawn_node_surface(quick_widget, node_id)
    if surface is None or surface.objectName() != FLOWCHART_SURFACE_OBJECT_NAME:
        return None
    return surface


def call_surface(surface: QObject, function_name: str) -> dict[str, Any]:
    """Call a no-argument surface function that returns a plain object; {} when it returns nothing usable."""
    value = _invoke(surface, function_name)
    if isinstance(value, QJSValue):
        value = value.toVariant()
    return dict(value) if isinstance(value, dict) else {}


__all__ = [
    "FLOWCHART_SURFACE_OBJECT_NAME",
    "GRAPH_CANVAS_OBJECT_NAME",
    "call_surface",
    "drawn_flowchart_surface",
    "drawn_node_surface",
]
