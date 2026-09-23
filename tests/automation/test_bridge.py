# Purpose: Prove the GUI-thread AutomationBridge (FIFO, no re-entrancy, guards, dialog watchdog, Deferred polling, shutdown) and the automation service lifecycle.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_bridge.py
from __future__ import annotations

import dataclasses
import itertools
import os
import threading
import time
import unittest
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from PyQt6.QtCore import QEventLoop, QObject, QTimer
from PyQt6.QtWidgets import QApplication, QDialog

from ea_node_editor import __version__
from ea_node_editor.automation.errors import (
    APP_BUSY,
    APP_BUSY_MODAL,
    APP_SHUTTING_DOWN,
    TIMEOUT,
    UNEXPECTED_DIALOG,
)
from ea_node_editor.automation.gate import AutomationGate
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.automation.protocol import AutomationRequest, AutomationResponse, HelloResponse
from ea_node_editor.ui.shell.automation import service as service_module
from ea_node_editor.ui.shell.automation.bridge import AutomationBridge
from ea_node_editor.ui.shell.automation.context import AutomationContext
from tests.automation import harness

READ_OP = "graph.get"  # read-only, every param optional
MUTATING_OP = "node.add"  # mutates_graph=True
DEFERRED_OP = "run.status"  # deferred=True in the catalog
CONTROL_OP = "run.control"  # second sync op for interleaving
NODE_PARAMS = {"type_id": "passive.flowchart.process", "x": 0, "y": 0}
CONTROL_PARAMS = {"action": "stop"}
FLOW_TYPE = "passive.flowchart.process"

_IDS = itertools.count(1)


def _request(op: str, params: Mapping[str, Any] | None = None, *, request_id: str = "", timeout_s: float = 30.0) -> AutomationRequest:
    return AutomationRequest(id=request_id or f"{op}#{next(_IDS)}", op=op, params=dict(params or {}), timeout_s=timeout_s)


def _pump(condition: Callable[[], bool], *, timeout_s: float = 5.0) -> bool:
    """Spin the Qt event loop until ``condition()`` holds (False on timeout)."""
    app = QApplication.instance()
    deadline = time.monotonic() + timeout_s
    while not condition():
        if time.monotonic() >= deadline:
            return False
        app.processEvents()
        time.sleep(0.002)
    return True


def _wait(future: "Future[AutomationResponse]", *, timeout_s: float = 5.0) -> AutomationResponse:
    if not _pump(future.done, timeout_s=timeout_s):
        raise AssertionError("automation future did not resolve in time")
    return future.result()


def _dialog(title: str) -> QDialog:
    dialog = QDialog()
    dialog.setWindowTitle(title)
    return dialog


class _BridgeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = harness.ensure_app()
        self.context = harness.build_context()
        self.calls: list[str] = []
        self._bridges: list[AutomationBridge] = []

    def tearDown(self) -> None:
        for bridge in self._bridges:
            bridge.shutdown()
        self.app.processEvents()
        self.assertIsNone(QApplication.activeModalWidget(), "a test leaked an active modal widget")

    def make_bridge(self, handlers: Mapping[str, Any], context: AutomationContext | None = None) -> AutomationBridge:
        bridge = AutomationBridge(context or self.context, handlers)
        self._bridges.append(bridge)
        return bridge

    def handlers(self, **overrides: Any) -> dict[str, Any]:
        def read(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            self.calls.append(READ_OP)
            return {"nodes": [], "workspace_id": context.workspace_id()}

        def mutate(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            self.calls.append(MUTATING_OP)
            node_id = context.scene.add_node_from_type(params["type_id"], float(params["x"]), float(params["y"]))
            return {"node_id": node_id}

        def control(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            self.calls.append(CONTROL_OP)
            return {"applied": True, "engine_state": "idle"}

        table: dict[str, Any] = {READ_OP: read, MUTATING_OP: mutate, CONTROL_OP: control}
        table.update(overrides)
        return table

    def assertFailure(self, response: AutomationResponse, code: str) -> None:
        self.assertFalse(response.ok, f"expected {code}, got success {response.result}")
        assert response.error is not None
        self.assertEqual(response.error.code, code, response.error.message)


class QueueOrderingTests(_BridgeTestCase):
    def test_submits_from_a_worker_thread_resolve_in_fifo_order(self) -> None:
        order: list[str] = []

        def read(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            order.append(params["workspace_id"])
            return {"seen": params["workspace_id"]}

        bridge = self.make_bridge({READ_OP: read})
        futures: list[Future[AutomationResponse]] = []

        def worker() -> None:
            for tag in ("r1", "r2", "r3"):
                futures.append(bridge.submit(_request(READ_OP, {"workspace_id": tag}, request_id=tag)))

        thread = threading.Thread(target=worker, name="automation-test-submitter")
        thread.start()
        thread.join(5.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(futures), 3)
        responses = [_wait(future) for future in futures]
        self.assertEqual(order, ["r1", "r2", "r3"])
        self.assertEqual([response.id for response in responses], ["r1", "r2", "r3"])
        self.assertTrue(all(response.ok for response in responses))
        self.assertEqual([response.result["seen"] for response in responses], ["r1", "r2", "r3"])
        self.assertEqual(bridge.queue_length, 0)
        self.assertFalse(bridge.busy)

    def test_handler_running_a_nested_event_loop_is_never_re_entered(self) -> None:
        depth = {"current": 0, "max": 0}
        order: list[str] = []
        snapshot: dict[str, Any] = {}
        late: list[Future[AutomationResponse]] = []

        def enter(tag: str) -> None:
            depth["current"] += 1
            depth["max"] = max(depth["max"], depth["current"])
            order.append(tag)

        def leave() -> None:
            depth["current"] -= 1

        def nested(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            enter("first")
            loop = QEventLoop()
            QTimer.singleShot(5, lambda: late.append(bridge.submit(_request(CONTROL_OP, CONTROL_PARAMS, request_id="second"))))
            QTimer.singleShot(40, loop.quit)
            loop.exec()
            snapshot["queued_while_busy"] = bridge.queue_length
            snapshot["busy_inside"] = bridge.busy
            leave()
            return {"first": True}

        def plain(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            enter("second")
            leave()
            return {"second": True}

        bridge = self.make_bridge({READ_OP: nested, CONTROL_OP: plain})
        first = bridge.submit(_request(READ_OP, request_id="first"))
        first_response = _wait(first)
        self.assertTrue(first_response.ok)
        self.assertEqual(len(late), 1)
        second_response = _wait(late[0])
        self.assertTrue(second_response.ok)
        self.assertEqual(order, ["first", "second"])
        self.assertEqual(depth["max"], 1, "the drain re-entered while a handler ran a nested event loop")
        self.assertEqual(snapshot["queued_while_busy"], 1)
        self.assertTrue(snapshot["busy_inside"])


class GuardTests(_BridgeTestCase):
    def test_host_teardown_flag_rejects_requests_before_dispatch(self) -> None:
        closing = dataclasses.replace(self.context, host=SimpleNamespace(_shell_teardown_started=True))
        bridge = self.make_bridge(self.handlers(), closing)
        response = _wait(bridge.submit(_request(READ_OP)))
        self.assertFailure(response, APP_SHUTTING_DOWN)
        self.assertEqual(self.calls, [])
        alive = dataclasses.replace(self.context, host=SimpleNamespace(_shell_teardown_started=False))
        bridge = self.make_bridge(self.handlers(), alive)
        self.assertTrue(_wait(bridge.submit(_request(READ_OP))).ok)
        self.assertEqual(self.calls, [READ_OP])

    def test_active_modal_widget_blocks_with_retryable_app_busy_modal(self) -> None:
        bridge = self.make_bridge(self.handlers())
        dialog = _dialog("Blocking Preferences")
        self.addCleanup(dialog.deleteLater)
        self.addCleanup(dialog.hide)
        dialog.setModal(True)
        dialog.show()
        with ExitStack() as stack:
            if QApplication.activeModalWidget() is not dialog:
                stack.enter_context(patch.object(QApplication, "activeModalWidget", return_value=dialog))
            response = _wait(bridge.submit(_request(READ_OP)))
        self.assertFailure(response, APP_BUSY_MODAL)
        assert response.error is not None
        self.assertTrue(response.error.retryable)
        self.assertEqual(response.error.details["title"], "Blocking Preferences")
        self.assertEqual(response.error.details["kind"], "modal")
        self.assertEqual(self.calls, [])
        dialog.hide()
        self.assertIsNone(QApplication.activeModalWidget())
        self.assertTrue(_wait(bridge.submit(_request(READ_OP))).ok)
        self.assertEqual(self.calls, [READ_OP])

    def test_active_popup_widget_blocks_with_app_busy_modal(self) -> None:
        bridge = self.make_bridge(self.handlers())
        popup = _dialog("Context Menu")
        with patch.object(QApplication, "activePopupWidget", return_value=popup):
            response = _wait(bridge.submit(_request(READ_OP)))
        self.assertFailure(response, APP_BUSY_MODAL)
        assert response.error is not None
        self.assertEqual(response.error.details["kind"], "popup")
        self.assertEqual(self.calls, [])

    def test_document_io_blocks_mutating_ops_but_not_reads(self) -> None:
        session = SimpleNamespace(document_io_active=lambda: True)
        context = dataclasses.replace(self.context, project_session=session)
        bridge = self.make_bridge(self.handlers(), context)
        blocked = _wait(bridge.submit(_request(MUTATING_OP, NODE_PARAMS)))
        self.assertFailure(blocked, APP_BUSY)
        assert blocked.error is not None
        self.assertTrue(blocked.error.retryable)
        self.assertEqual(self.calls, [])
        read = _wait(bridge.submit(_request(READ_OP)))
        self.assertTrue(read.ok)
        self.assertEqual(self.calls, [READ_OP])
        session.document_io_active = lambda: False
        added = _wait(bridge.submit(_request(MUTATING_OP, NODE_PARAMS)))
        self.assertTrue(added.ok, added.error)
        self.assertIn(added.result["node_id"], context.active_workspace().nodes)

    def test_request_whose_timeout_elapsed_in_the_queue_is_not_executed(self) -> None:
        def slow(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            self.calls.append("slow")
            loop = QEventLoop()
            QTimer.singleShot(60, loop.quit)
            loop.exec()
            return {}

        bridge = self.make_bridge(self.handlers(**{READ_OP: slow}))
        first = bridge.submit(_request(READ_OP))
        stale = bridge.submit(_request(CONTROL_OP, CONTROL_PARAMS, timeout_s=0.02))
        self.assertTrue(_wait(first).ok)
        response = _wait(stale)
        self.assertFailure(response, TIMEOUT)
        assert response.error is not None
        self.assertFalse(response.error.details["executed"])
        self.assertEqual(self.calls, ["slow"])


class WatchdogTests(_BridgeTestCase):
    def test_dialog_opened_by_a_handler_is_rejected_and_reported(self) -> None:
        opened: dict[str, Any] = {}

        def opens_dialog(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            dialog = _dialog("Surprise Prompt")
            opened["dialog"] = dialog
            dialog.open()
            opened["active_inside"] = QApplication.activeModalWidget() is dialog
            return {"done": True}

        bridge = self.make_bridge(self.handlers(**{READ_OP: opens_dialog}))
        response = _wait(bridge.submit(_request(READ_OP)))
        dialog = opened["dialog"]
        self.addCleanup(dialog.deleteLater)
        self.assertTrue(opened["active_inside"])
        self.assertFailure(response, UNEXPECTED_DIALOG)
        assert response.error is not None
        self.assertEqual(response.error.details["dialogs"], ["Surprise Prompt"])
        self.assertTrue(response.error.details["handler_completed"])
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)
        self.assertFalse(dialog.isVisible())
        self.assertIsNone(QApplication.activeModalWidget())
        self.assertTrue(_wait(bridge.submit(_request(CONTROL_OP, CONTROL_PARAMS))).ok)

    def test_dialog_blocking_in_exec_is_rejected_by_the_timer(self) -> None:
        opened: dict[str, Any] = {}

        def execs_dialog(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            dialog = _dialog("Blocking Question")
            opened["dialog"] = dialog
            started = time.monotonic()
            opened["code"] = dialog.exec()
            opened["blocked_s"] = time.monotonic() - started
            return {"after_exec": True}

        bridge = self.make_bridge(self.handlers(**{READ_OP: execs_dialog}))
        response = _wait(bridge.submit(_request(READ_OP)))
        self.addCleanup(opened["dialog"].deleteLater)
        self.assertFailure(response, UNEXPECTED_DIALOG)
        assert response.error is not None
        self.assertEqual(response.error.details["dialogs"], ["Blocking Question"])
        self.assertEqual(opened["code"], int(QDialog.DialogCode.Rejected))
        self.assertLess(opened["blocked_s"], 2.0)
        self.assertIsNone(QApplication.activeModalWidget())


class DeferredTests(_BridgeTestCase):
    def test_deferred_resolves_after_polls_and_other_requests_interleave(self) -> None:
        timeline: list[str] = []
        polls = {"count": 0}

        def poll() -> dict[str, Any] | None:
            polls["count"] += 1
            timeline.append(f"poll{polls['count']}")
            return {"polls": polls["count"]} if polls["count"] >= 3 else None

        def deferred_handler(context: AutomationContext, params: Mapping[str, Any]) -> Deferred:
            return Deferred(poll=poll, timeout_s=5.0, poll_interval_s=0.02, label="test-wait")

        def control(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            timeline.append("control")
            return {"applied": True}

        bridge = self.make_bridge({DEFERRED_OP: deferred_handler, CONTROL_OP: control})
        deferred_future = bridge.submit(_request(DEFERRED_OP, {"wait": True}, request_id="waiter"))
        self.assertTrue(_pump(lambda: bridge.pending_deferred))
        self.assertFalse(deferred_future.done())
        self.assertFalse(bridge.busy)
        control_response = _wait(bridge.submit(_request(CONTROL_OP, CONTROL_PARAMS, request_id="stopper")))
        self.assertTrue(control_response.ok)
        self.assertIn("control", timeline)
        deferred_response = _wait(deferred_future)
        self.assertTrue(deferred_response.ok, deferred_response.error)
        self.assertEqual(deferred_response.id, "waiter")
        self.assertEqual(deferred_response.result, {"polls": 3})
        self.assertEqual(polls["count"], 3)
        self.assertLess(timeline.index("control"), timeline.index("poll3"))
        self.assertFalse(bridge.pending_deferred)

    def test_deferred_timeout_without_on_timeout_fails_with_timeout(self) -> None:
        def deferred_handler(context: AutomationContext, params: Mapping[str, Any]) -> Deferred:
            return Deferred(poll=lambda: None, timeout_s=0.05, poll_interval_s=0.01, label="never")

        bridge = self.make_bridge({DEFERRED_OP: deferred_handler})
        started = time.monotonic()
        response = _wait(bridge.submit(_request(DEFERRED_OP, {"wait": True})))
        self.assertFailure(response, TIMEOUT)
        assert response.error is not None
        self.assertTrue(response.error.retryable)
        self.assertEqual(response.error.details["label"], "never")
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertFalse(bridge.pending_deferred)

    def test_deferred_timeout_with_on_timeout_returns_its_result(self) -> None:
        def deferred_handler(context: AutomationContext, params: Mapping[str, Any]) -> Deferred:
            return Deferred(
                poll=lambda: None,
                timeout_s=0.05,
                on_timeout=lambda: {"state": "running", "timed_out": True},
                poll_interval_s=0.01,
            )

        bridge = self.make_bridge({DEFERRED_OP: deferred_handler})
        response = _wait(bridge.submit(_request(DEFERRED_OP, {"wait": True})))
        self.assertTrue(response.ok, response.error)
        self.assertEqual(response.result, {"state": "running", "timed_out": True})

    def test_request_timeout_caps_the_deferred_deadline(self) -> None:
        def deferred_handler(context: AutomationContext, params: Mapping[str, Any]) -> Deferred:
            return Deferred(poll=lambda: None, timeout_s=30.0, poll_interval_s=0.01)

        bridge = self.make_bridge({DEFERRED_OP: deferred_handler})
        started = time.monotonic()
        response = _wait(bridge.submit(_request(DEFERRED_OP, {"wait": True}, timeout_s=0.05)))
        self.assertFailure(response, TIMEOUT)
        self.assertLess(time.monotonic() - started, 2.0)

    def test_two_deferreds_are_tracked_and_resolve_in_fifo_order(self) -> None:
        resolved: list[str] = []
        counters = {"a": 0, "b": 0}

        def make_poll(tag: str) -> Callable[[], dict[str, Any] | None]:
            def poll() -> dict[str, Any] | None:
                counters[tag] += 1
                return {"tag": tag} if counters[tag] >= 2 else None

            return poll

        def deferred_handler(context: AutomationContext, params: Mapping[str, Any]) -> Deferred:
            tag = "a" if params.get("log_tail") == 1 else "b"
            return Deferred(poll=make_poll(tag), timeout_s=5.0, poll_interval_s=0.01)

        bridge = self.make_bridge({DEFERRED_OP: deferred_handler})
        first = bridge.submit(_request(DEFERRED_OP, {"log_tail": 1}, request_id="a"))
        second = bridge.submit(_request(DEFERRED_OP, {"log_tail": 2}, request_id="b"))
        first.add_done_callback(lambda done: resolved.append(done.result().id))
        second.add_done_callback(lambda done: resolved.append(done.result().id))
        self.assertTrue(_wait(first).ok)
        self.assertTrue(_wait(second).ok)
        self.assertEqual(resolved, ["a", "b"])
        self.assertEqual(first.result().result, {"tag": "a"})
        self.assertEqual(second.result().result, {"tag": "b"})
        self.assertFalse(bridge.pending_deferred)


class HistoryTests(_BridgeTestCase):
    def test_mutating_handler_records_exactly_one_undo_step(self) -> None:
        def add_twice(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            first = context.scene.add_node_from_type(FLOW_TYPE, 0.0, 0.0)
            second = context.scene.add_node_from_type(FLOW_TYPE, 240.0, 0.0)
            return {"node_id": second, "first": first}

        bridge = self.make_bridge({MUTATING_OP: add_twice})
        workspace_id = self.context.workspace_id()
        self.assertEqual(self.context.runtime_history.undo_depth(workspace_id), 0)
        response = _wait(bridge.submit(_request(MUTATING_OP, NODE_PARAMS)))
        self.assertTrue(response.ok, response.error)
        self.assertEqual(len(self.context.active_workspace().nodes), 2)
        self.assertEqual(self.context.runtime_history.undo_depth(workspace_id), 1)


class ShutdownTests(_BridgeTestCase):
    def test_shutdown_fails_queued_requests_and_later_submits(self) -> None:
        late: list[Future[AutomationResponse]] = []
        seen: dict[str, Any] = {}

        def nested(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any]:
            loop = QEventLoop()

            def queue_more() -> None:
                late.append(bridge.submit(_request(CONTROL_OP, CONTROL_PARAMS, request_id="queued-1")))
                late.append(bridge.submit(_request(MUTATING_OP, NODE_PARAMS, request_id="queued-2")))

            def close_bridge() -> None:
                seen["queued_before_shutdown"] = bridge.queue_length
                bridge.shutdown()
                seen["queued_after_shutdown"] = bridge.queue_length

            QTimer.singleShot(5, queue_more)
            QTimer.singleShot(40, close_bridge)
            QTimer.singleShot(70, loop.quit)
            loop.exec()
            return {"first": True}

        bridge = self.make_bridge(self.handlers(**{READ_OP: nested}))
        first = _wait(bridge.submit(_request(READ_OP, request_id="running")))
        self.assertTrue(first.ok, "the op that was executing during shutdown keeps its real outcome")
        self.assertEqual(seen["queued_before_shutdown"], 2)
        self.assertEqual(seen["queued_after_shutdown"], 0)
        self.assertEqual(len(late), 2)
        for future in late:
            self.assertTrue(future.done())
            self.assertFailure(future.result(), APP_SHUTTING_DOWN)
        self.assertEqual(self.calls, [], "queued handlers must not run after shutdown")
        after = bridge.submit(_request(CONTROL_OP, CONTROL_PARAMS, request_id="after"))
        self.assertTrue(after.done(), "submit after shutdown must fail without touching the event loop")
        self.assertFailure(after.result(), APP_SHUTTING_DOWN)
        self.assertTrue(bridge.closed)

    def test_shutdown_fails_a_pending_deferred(self) -> None:
        def deferred_handler(context: AutomationContext, params: Mapping[str, Any]) -> Deferred:
            return Deferred(poll=lambda: None, timeout_s=30.0, poll_interval_s=0.01)

        bridge = self.make_bridge({DEFERRED_OP: deferred_handler})
        future = bridge.submit(_request(DEFERRED_OP, {"wait": True}))
        self.assertTrue(_pump(lambda: bridge.pending_deferred))
        bridge.shutdown()
        self.assertTrue(future.done())
        self.assertFailure(future.result(), APP_SHUTTING_DOWN)
        self.assertFalse(bridge.pending_deferred)
        bridge.shutdown()  # idempotent


class _FakeServer:
    instances: list["_FakeServer"] = []

    def __init__(self, *, token: str, dispatch: Callable[[AutomationRequest], AutomationResponse], hello: HelloResponse, port: int = 0) -> None:
        self.token = token
        self.dispatch = dispatch
        self.hello = hello
        self.port = port
        self.started = 0
        self.stopped = 0
        _FakeServer.instances.append(self)

    def start(self) -> int:
        self.started += 1
        if not self.port:
            self.port = 45123
        return self.port

    def stop(self, *, timeout_s: float = 2.0) -> None:
        self.stopped += 1


class _FailingServer(_FakeServer):
    def start(self) -> int:
        self.started += 1
        raise OSError("port in use")


class _WindowObject(QObject):
    """QObject host stand-in so the bridge parenting path is covered."""


def _window_namespace(context: AutomationContext, **extra: Any) -> SimpleNamespace:
    return SimpleNamespace(**{**_window_attributes(context), **extra})


def _window_attributes(context: AutomationContext) -> dict[str, Any]:
    return {
        "_shell_teardown_started": False,
        "scene": context.scene,
        "view": None,
        "model": context.model,
        "registry": context.registry,
        "workspace_manager": context.workspace_manager,
        "runtime_history": context.runtime_history,
        "workspace_navigation_controller": None,
        "shell_workspace_presenter": None,
        "workspace_edit_controller": SimpleNamespace(mutation_ui_effects=None),
        "project_session_controller": None,
        "run_controller": None,
        "run_state": None,
        "console_panel": None,
        "canvas_export_presenter": None,
        "quick_widget": None,
        "project_path": "",
    }


class ServiceLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = harness.ensure_app()
        self.context = harness.build_context()
        _FakeServer.instances.clear()
        self.written: list[Any] = []
        self.removed: list[str] = []
        self.registered: list[Any] = []
        self.connected: list[Any] = []
        fake_app = SimpleNamespace(aboutToQuit=SimpleNamespace(connect=self.connected.append))
        self._stack = ExitStack()
        self._stack.enter_context(patch.object(service_module, "AutomationServer", _FakeServer))
        self._stack.enter_context(patch.object(service_module, "write_instance_file", self._write))
        self._stack.enter_context(patch.object(service_module, "remove_instance_file", self._remove))
        self._stack.enter_context(patch.object(service_module.atexit, "register", self.registered.append))
        self._stack.enter_context(patch.object(service_module, "QApplication", SimpleNamespace(instance=lambda: fake_app)))
        self.addCleanup(self._stack.close)
        self.gate = AutomationGate(enabled=True, port=0, instance_id="svc-test-1", token="secret-token", mode="private")

    def _write(self, record: Any) -> Path:
        self.written.append(record)
        return Path(f"C:/fake/instances/{record.instance_id}.json")

    def _remove(self, instance_id: str) -> bool:
        self.removed.append(instance_id)
        return True

    def test_disabled_gate_returns_none_and_starts_nothing(self) -> None:
        gate = AutomationGate(enabled=False, port=0, instance_id="", token="", mode="visible")
        window = _window_namespace(self.context)
        self.assertIsNone(service_module.start_automation_if_enabled(window, gate=gate))
        self.assertEqual(_FakeServer.instances, [])
        self.assertEqual(self.written, [])
        self.assertEqual(self.registered, [])

    def test_start_publishes_discovery_and_stop_is_idempotent(self) -> None:
        window = _window_namespace(self.context, project_path=Path("C:/demo/flow.cxproj"))
        service = service_module.start_automation_if_enabled(window, gate=self.gate)
        assert service is not None
        self.addCleanup(service.stop)
        self.assertIsInstance(service, service_module.AutomationService)
        self.assertEqual(len(_FakeServer.instances), 1)
        server = _FakeServer.instances[0]
        self.assertIs(service.server, server)
        self.assertEqual(server.started, 1)
        self.assertEqual(server.token, "secret-token")
        self.assertEqual(
            server.hello,
            HelloResponse(app_version=__version__, instance_id="svc-test-1", pid=os.getpid(), mode="private"),
        )
        self.assertEqual(service.port, 45123)
        self.assertEqual(len(self.written), 1)
        record = self.written[0]
        self.assertEqual(record.instance_id, "svc-test-1")
        self.assertEqual(record.pid, os.getpid())
        self.assertEqual(record.port, 45123)
        self.assertEqual(record.token, "secret-token")
        self.assertEqual(record.mode, "private")
        self.assertEqual(record.app_version, __version__)
        self.assertEqual(record.project_path, str(Path("C:/demo/flow.cxproj")))
        self.assertAlmostEqual(record.started_at, time.time(), delta=30.0)
        self.assertEqual(service.instance_file, Path("C:/fake/instances/svc-test-1.json"))
        self.assertEqual(self.connected, [service.stop])
        self.assertEqual(self.registered, [service.stop])
        self.assertIsInstance(service.bridge, AutomationBridge)
        self.assertIsNone(service.bridge.parent(), "a non-QObject host cannot parent the bridge")
        self.assertIs(service.bridge.context.gate, self.gate)
        self.assertIs(service.bridge.context.scene, self.context.scene)

        # The server's dispatch callback blocks a worker thread on the GUI bridge.
        request = _request(READ_OP, request_id="via-dispatch")
        holder: dict[str, Any] = {}

        def worker() -> None:
            holder["response"] = server.dispatch(request)

        thread = threading.Thread(target=worker, name="automation-test-dispatch")
        thread.start()
        self.assertTrue(_pump(lambda: "response" in holder))
        thread.join(5.0)
        response = holder["response"]
        self.assertIsInstance(response, AutomationResponse)
        self.assertEqual(response.id, "via-dispatch")

        service.stop()
        self.assertTrue(service.stopped)
        self.assertEqual(self.removed, ["svc-test-1"])
        self.assertEqual(server.stopped, 1)
        after = service.bridge.submit(_request(READ_OP))
        self.assertTrue(after.done())
        assert after.result().error is not None
        self.assertEqual(after.result().error.code, APP_SHUTTING_DOWN)
        service.stop()
        self.assertEqual(self.removed, ["svc-test-1"])
        self.assertEqual(server.stopped, 1)

    def test_qobject_window_parents_the_bridge(self) -> None:
        window = _WindowObject()
        for name, value in _window_attributes(self.context).items():
            setattr(window, name, value)
        service = service_module.start_automation_if_enabled(window, gate=self.gate)
        assert service is not None
        self.addCleanup(service.stop)
        self.assertIs(service.bridge.parent(), window)
        self.assertEqual(self.written[0].project_path, "")

    def test_server_start_failure_tears_down_and_propagates(self) -> None:
        with patch.object(service_module, "AutomationServer", _FailingServer):
            with self.assertRaises(OSError):
                service_module.start_automation_if_enabled(_window_namespace(self.context), gate=self.gate)
        self.assertEqual(len(_FakeServer.instances), 1)
        self.assertEqual(_FakeServer.instances[0].stopped, 1)
        self.assertEqual(self.written, [])
        self.assertEqual(self.registered, [])


class AutomationServiceSignalTests(unittest.TestCase):
    def test_service_stop_is_connectable_to_a_real_qt_signal(self) -> None:
        # Regression: a slots dataclass without __weakref__ made
        # ``aboutToQuit.connect(service.stop)`` raise TypeError inside the startup
        # QTimer slot, which PyQt6 escalates to a fatal abort of the whole app.
        import weakref

        from PyQt6.QtCore import QObject, pyqtSignal

        from ea_node_editor.automation.gate import AutomationGate
        from ea_node_editor.ui.shell.automation.service import AutomationService

        class _Emitter(QObject):
            fired = pyqtSignal()

        class _Bridge:
            def __init__(self) -> None:
                self.shut = 0

            def shutdown(self) -> None:
                self.shut += 1

        class _Server:
            port = 0

            def __init__(self) -> None:
                self.stopped = 0

            def stop(self) -> None:
                self.stopped += 1

        gate = AutomationGate(enabled=True, port=0, instance_id="sig-test", token="t", mode="private")
        bridge = _Bridge()
        server = _Server()
        service = AutomationService(gate=gate, bridge=bridge, server=server)
        weakref.ref(service)  # must not raise
        emitter = _Emitter()
        emitter.fired.connect(service.stop)  # must not raise
        with patch("ea_node_editor.ui.shell.automation.service.remove_instance_file", return_value=True):
            emitter.fired.emit()
            emitter.fired.emit()
        self.assertEqual(bridge.shut, 1)
        self.assertEqual(server.stopped, 1)
        self.assertTrue(service.stopped)


if __name__ == "__main__":
    unittest.main()
