# Purpose: Shell-free automation test harness: offscreen GraphSceneBridge + RuntimeGraphHistory + built-in registry behind an AutomationContext.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Shell-free harness for handler tests.

Pattern from ``ea_node_editor/ui/perf/performance_harness.py`` (mutation
instrumentation payload): a real ``GraphSceneBridge`` bound to a ``GraphModel``
and ``RuntimeGraphHistory`` under ``QT_QPA_PLATFORM=offscreen``, with the
built-in registry (public plugins skipped for speed). Fields that need the full
shell (``nav``, ``project_session``, ``run_controller``, ``canvas_export`` ...)
are ``None``; handlers that require them raise ``INTERNAL`` via
``context.require_shell``.

Use ``call(context, "node.add", {...})`` to run an op exactly the way the
bridge does (validation, grouped history, error translation) and to resolve a
``Deferred`` by polling with ``QApplication.processEvents``.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ea_node_editor.automation.errors import TIMEOUT, AutomationOpError  # noqa: E402
from ea_node_editor.automation.op_model import Deferred  # noqa: E402
from ea_node_editor.graph.model import GraphModel  # noqa: E402
from ea_node_editor.nodes.bootstrap import build_default_registry  # noqa: E402
from ea_node_editor.nodes.registry import NodeRegistry  # noqa: E402
from ea_node_editor.ui.shell.automation.context import AutomationContext  # noqa: E402
from ea_node_editor.ui.shell.automation.dispatch import HandlerTable, execute_op  # noqa: E402
from ea_node_editor.ui.shell.automation.registry import build_handler_table  # noqa: E402
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory  # noqa: E402
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge  # noqa: E402
from ea_node_editor.workspace.manager import WorkspaceManager  # noqa: E402


@lru_cache(maxsize=1)
def shared_registry() -> NodeRegistry:
    """Built-in registry without public plugins (fast, deterministic)."""
    return build_default_registry(include_public_plugins=False)


@lru_cache(maxsize=1)
def shared_handlers() -> dict[str, Any]:
    return build_handler_table()


def ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        from ea_node_editor.app import prepare_qt_application_attributes

        prepare_qt_application_attributes()
        app = QApplication([])
    return app


def build_context(*, registry: NodeRegistry | None = None) -> AutomationContext:
    """Fresh model + scene + history bound together, wrapped in an AutomationContext."""
    ensure_app()
    resolved_registry = registry or shared_registry()
    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    scene = GraphSceneBridge()
    history = RuntimeGraphHistory()
    scene.set_workspace(model, resolved_registry, workspace_id)
    scene.bind_runtime_history(history)
    return AutomationContext(
        host=None,
        scene=scene,
        view=None,
        stored_model=model,
        stored_registry=resolved_registry,
        stored_workspace_manager=WorkspaceManager(model),
        runtime_history=history,
        nav=None,
        workspace_presenter=None,
        workspace_edit=None,
        project_session=None,
        run_controller=None,
        run_state=None,
        console=None,
        canvas_export=None,
        effects=None,
        quick_widget=None,
        gate=None,
    )


def call(
    context: AutomationContext,
    op: str,
    params: Mapping[str, Any] | None = None,
    *,
    handlers: HandlerTable | None = None,
    poll_timeout_s: float = 10.0,
) -> dict[str, Any]:
    """Run one op like the bridge would and return its result dict (or raise)."""
    result = execute_op(context, handlers or shared_handlers(), op, params)
    if not isinstance(result, Deferred):
        return result
    return resolve_deferred(result, poll_timeout_s=poll_timeout_s)


def resolve_deferred(deferred: Deferred, *, poll_timeout_s: float = 10.0) -> dict[str, Any]:
    app = ensure_app()
    deadline = time.monotonic() + min(float(deferred.timeout_s), poll_timeout_s)
    while True:
        outcome = deferred.poll()
        if outcome is not None:
            return dict(outcome)
        if time.monotonic() >= deadline:
            if deferred.on_timeout is not None:
                return dict(deferred.on_timeout())
            raise AutomationOpError(TIMEOUT, f"Deferred op {deferred.label or ''} timed out in the harness.")
        app.processEvents()
        time.sleep(deferred.poll_interval_s)


def expect_error(context: AutomationContext, op: str, params: Mapping[str, Any] | None, code: str) -> AutomationOpError:
    """Assert helper: run an op and return the AutomationOpError with ``code``."""
    try:
        call(context, op, params)
    except AutomationOpError as exc:
        if exc.code != code:
            raise AssertionError(f"{op} raised {exc.code} ({exc.message}); expected {code}") from exc
        return exc
    raise AssertionError(f"{op} succeeded; expected error {code}")


__all__ = ["build_context", "call", "ensure_app", "expect_error", "resolve_deferred", "shared_handlers", "shared_registry"]
