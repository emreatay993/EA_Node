# Purpose: Prove CorexClient against an in-test NDJSON server: discovery-driven connect, hello auth, call success/error/timeout/protocol faults, close/launch lifecycle.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_client.py
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from ea_node_editor.automation import client as client_module
from ea_node_editor.automation import discovery, errors, gate, launcher, protocol
from ea_node_editor.automation.client import CorexClient

TOKEN = "test-token-123"
INSTANCE_ID = "inst-test"


def _close_quietly(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


class _FakeCorexServer:
    """Minimal protocol-v1 NDJSON server built on ``protocol`` only (never ``transport``)."""

    def __init__(self, *, token: str = TOKEN) -> None:
        self.token = token
        self.hello = protocol.HelloResponse(app_version="0.0-test", instance_id=INSTANCE_ID, pid=os.getpid(), mode="private")
        self.received: list[dict[str, Any]] = []
        # app.quit behaviour: an error code to refuse with (e.g. PROJECT_DIRTY) and a hook run on success.
        self.quit_error_code: str | None = None
        self.on_quit: Any = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._connections: list[socket.socket] = []
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(8)
        self._listener.settimeout(0.1)
        self.port = int(self._listener.getsockname()[1])
        self._thread = threading.Thread(target=self._accept_loop, name="fake-corex-accept", daemon=True)
        self._thread.start()

    def record(self, **overrides: Any) -> discovery.InstanceRecord:
        values: dict[str, Any] = {
            "instance_id": INSTANCE_ID,
            "pid": os.getpid(),
            "port": self.port,
            "token": self.token,
            "mode": "private",
            "app_version": "0.0-test",
            "started_at": time.time(),
        }
        values.update(overrides)
        return discovery.InstanceRecord(**values)

    def ops(self) -> list[str]:
        with self._lock:
            return [payload["op"] for payload in self.received]

    def requests_for(self, op: str) -> list[dict[str, Any]]:
        with self._lock:
            return [payload for payload in self.received if payload["op"] == op]

    def close(self) -> None:
        self._stop.set()
        _close_quietly(self._listener)
        with self._lock:
            connections = list(self._connections)
        for conn in connections:
            _close_quietly(conn)
        self._thread.join(timeout=2.0)

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _addr = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with self._lock:
                self._connections.append(conn)
            threading.Thread(target=self._serve, args=(conn,), name="fake-corex-conn", daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        reader = conn.makefile("rb")
        try:
            first = reader.readline()
            if not first:
                return
            hello = protocol.HelloRequest.from_dict(protocol.decode_frame(first))
            if hello.token != self.token:
                self._send(conn, protocol.AutomationResponse.failure("", errors.AutomationOpError(errors.AUTH_FAILED, "automation token mismatch")))
                return
            self._send(conn, protocol.AutomationResponse.success("", self.hello.to_dict()))
            while not self._stop.is_set():
                raw = reader.readline()
                if not raw:
                    return
                payload = protocol.decode_frame(raw)
                request = protocol.AutomationRequest.from_dict(payload)
                with self._lock:
                    self.received.append(payload)
                if not self._respond(conn, request):
                    return
        except (OSError, ValueError):
            return
        finally:
            _close_quietly(conn)

    def _respond(self, conn: socket.socket, request: protocol.AutomationRequest) -> bool:
        op, params, request_id = request.op, request.params, request.id
        if op == "echo.op":
            response = protocol.AutomationResponse.success(request_id, {"echo": params})
        elif op == "err.op":
            error = errors.AutomationOpError(errors.NOT_FOUND, "nothing here", details={"id": params.get("id", "")})
            response = protocol.AutomationResponse.failure(request_id, error)
        elif op == "bad.id":
            response = protocol.AutomationResponse.success("r999", {"echo": params})
        elif op == "garbage.op":
            conn.sendall(b"this is not json\n")
            return True
        elif op == "drop.op":
            return False
        elif op == "slow.op":
            time.sleep(float(params.get("sleep_s", 1.0)))
            response = protocol.AutomationResponse.success(request_id, {"slept": True})
        elif op == "late.op":
            # Answer late and in two pieces (so the client's last read runs on a nearly spent
            # deadline), then stop reading for pause_s so the next request's send has to wait.
            time.sleep(float(params.get("sleep_s", 0.3)))
            frame = protocol.encode_frame(protocol.AutomationResponse.success(request_id, {"late": True}).to_dict())
            half = len(frame) // 2
            conn.sendall(frame[:half])
            time.sleep(0.05)
            conn.sendall(frame[half:])
            time.sleep(float(params.get("pause_s", 0.0)))
            return True
        elif op == "app.quit":
            if self.quit_error_code:
                error = errors.AutomationOpError(self.quit_error_code, "refusing to quit")
                response = protocol.AutomationResponse.failure(request_id, error)
            else:
                response = protocol.AutomationResponse.success(request_id, {"quitting": True})
                if self.on_quit is not None:
                    self.on_quit()
        elif op == "app.status":
            response = protocol.AutomationResponse.success(request_id, {"state": "idle"})
        else:
            response = protocol.AutomationResponse.failure(request_id, errors.AutomationOpError(errors.UNKNOWN_OP, f"unknown op {op}"))
        self._send(conn, response)
        return True

    @staticmethod
    def _send(conn: socket.socket, response: protocol.AutomationResponse) -> None:
        conn.sendall(protocol.encode_frame(response.to_dict()))


class _FakeProcess:
    """Popen stand-in that never exits on its own so ``close()`` has to terminate it."""

    def __init__(self) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.terminate_calls = 0
        self.kill_calls = 0

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is None:
            raise subprocess.TimeoutExpired("corex", timeout)
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.returncode = -15

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9


class _TimeoutSpySocket:
    """Socket proxy recording the socket timeout in force at every ``sendall``."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self.send_timeouts: list[float | None] = []

    def sendall(self, data: bytes) -> None:
        self.send_timeouts.append(self._sock.gettimeout())
        self._sock.sendall(data)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sock, name)


class CorexClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = _FakeCorexServer()
        self.addCleanup(self.server.close)

    def _connect(self, **kwargs: Any) -> CorexClient:
        with patch.object(discovery, "find_instance", return_value=self.server.record()):
            client = CorexClient.connect(**kwargs)
        self.addCleanup(client.close)
        return client

    # ------------------------------------------------------------- connect

    def test_connect_uses_discovery_and_completes_the_hello_handshake(self) -> None:
        record = self.server.record()
        with patch.object(discovery, "find_instance", return_value=record) as find_instance:
            client = CorexClient.connect(instance_id=INSTANCE_ID, timeout_s=3.0)
        self.addCleanup(client.close)
        find_instance.assert_called_once_with(INSTANCE_ID)
        self.assertTrue(client.connected)
        self.assertEqual(client.instance, record)
        self.assertIsNone(client.handle)
        assert client.hello is not None
        self.assertEqual(client.hello.instance_id, INSTANCE_ID)
        self.assertEqual(client.hello.mode, "private")
        self.assertEqual(client.hello.protocol, protocol.PROTOCOL_VERSION)

    def test_connect_without_a_live_instance_raises_not_found_with_a_hint(self) -> None:
        with patch.object(discovery, "find_instance", return_value=None):
            with self.assertRaises(errors.AutomationOpError) as raised:
                CorexClient.connect(instance_id="missing")
        self.assertEqual(raised.exception.code, errors.NOT_FOUND)
        self.assertIn("--automation", raised.exception.hint)
        self.assertEqual(raised.exception.details["instance_id"], "missing")
        self.assertFalse(raised.exception.retryable)

    def test_connect_with_a_wrong_token_raises_auth_failed(self) -> None:
        with patch.object(discovery, "find_instance", return_value=self.server.record(token="wrong")):
            with self.assertRaises(errors.AutomationOpError) as raised:
                CorexClient.connect()
        self.assertEqual(raised.exception.code, errors.AUTH_FAILED)

    def test_connect_to_a_closed_port_raises_not_found(self) -> None:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        closed_port = int(probe.getsockname()[1])
        probe.close()
        # Windows reports a closed loopback port late (SYN retries), so this also covers the connect-timeout path.
        with patch.object(discovery, "find_instance", return_value=self.server.record(port=closed_port)):
            with self.assertRaises(errors.AutomationOpError) as raised:
                CorexClient.connect(timeout_s=1.0)
        self.assertEqual(raised.exception.code, errors.NOT_FOUND)
        self.assertFalse(raised.exception.retryable)
        self.assertIn("not accepting connections", raised.exception.message)
        self.assertEqual(raised.exception.details["port"], closed_port)
        self.assertTrue(raised.exception.details["reason"])

    # ---------------------------------------------------------------- call

    def test_call_returns_the_result_and_numbers_requests(self) -> None:
        client = self._connect()
        first = client.call("echo.op", {"a": 1})
        second = client.call("echo.op")
        self.assertEqual(first, {"echo": {"a": 1}})
        self.assertEqual(second, {"echo": {}})
        self.assertEqual([payload["id"] for payload in self.server.received], ["r1", "r2"])
        self.assertEqual(self.server.received[0]["timeout_s"], protocol.DEFAULT_REQUEST_TIMEOUT_S)
        client.call("echo.op", timeout_s=7)
        self.assertEqual(self.server.received[2]["timeout_s"], 7.0)
        self.assertEqual(client.ping(), {"state": "idle"})
        self.assertEqual(self.server.ops()[-1], "app.status")

    def test_call_rejects_bad_local_arguments(self) -> None:
        client = self._connect()
        with self.assertRaises(ValueError):
            client.call("")
        with self.assertRaises(TypeError):
            client.call("echo.op", ["not", "a", "mapping"])  # type: ignore[arg-type]
        with self.assertRaises(errors.AutomationOpError) as raised:
            client.call("echo.op", {"blob": object()})
        self.assertEqual(raised.exception.code, errors.INVALID_PARAMS)
        self.assertEqual(self.server.received, [])

    def test_call_raises_the_decoded_error_envelope(self) -> None:
        client = self._connect()
        with self.assertRaises(errors.AutomationOpError) as raised:
            client.call("err.op", {"id": "node_9"})
        self.assertEqual(raised.exception.code, errors.NOT_FOUND)
        self.assertEqual(raised.exception.message, "nothing here")
        self.assertEqual(raised.exception.details, {"id": "node_9"})
        self.assertTrue(client.connected)
        self.assertEqual(client.call("echo.op", {"after": True}), {"echo": {"after": True}})

    def test_call_times_out_and_the_connection_stays_usable(self) -> None:
        client = self._connect()
        with patch.object(client_module, "RESPONSE_TIMEOUT_MARGIN_S", 0.05):
            started = time.monotonic()
            with self.assertRaises(errors.AutomationOpError) as raised:
                client.call("slow.op", {"sleep_s": 0.6}, timeout_s=0.1)
        elapsed = time.monotonic() - started
        self.assertEqual(raised.exception.code, errors.TIMEOUT)
        self.assertTrue(raised.exception.retryable)
        self.assertEqual(raised.exception.details["request_id"], "r1")
        self.assertLess(elapsed, 0.5)
        self.assertTrue(client.connected)
        # The late r1 response is discarded; r2 gets its own answer.
        self.assertEqual(client.call("echo.op", {"again": 1}), {"echo": {"again": 1}})

    def test_send_timeout_is_reset_after_a_call_that_used_most_of_its_deadline(self) -> None:
        client = self._connect()
        spy = _TimeoutSpySocket(client._socket)  # noqa: SLF001 - observe the live socket
        client._socket = spy  # type: ignore[assignment]  # noqa: SLF001
        with patch.object(client_module, "RESPONSE_TIMEOUT_MARGIN_S", 0.05):
            self.assertEqual(client.call("late.op", {"sleep_s": 0.3, "pause_s": 0.8}, timeout_s=0.5), {"late": True})
        leftover = spy.gettimeout()
        assert leftover is not None
        self.assertLess(leftover, 0.4, "precondition: the last read left a nearly spent timeout on the socket")
        # The server is not reading for ~0.8 s, so this multi-MiB frame cannot be written within the
        # leftover timeout; the send must run on the new request's own budget instead.
        blob = "x" * (3 * 1024 * 1024)
        result = client.call("echo.op", {"blob": blob})
        self.assertEqual(len(result["echo"]["blob"]), len(blob))
        self.assertGreaterEqual(spy.send_timeouts[-1], protocol.DEFAULT_REQUEST_TIMEOUT_S)
        self.assertTrue(client.connected)

    def test_mismatched_response_id_is_a_protocol_error(self) -> None:
        client = self._connect()
        with self.assertRaises(errors.AutomationOpError) as raised:
            client.call("bad.id")
        self.assertEqual(raised.exception.code, errors.PROTOCOL_ERROR)
        self.assertEqual(raised.exception.details["response_id"], "r999")
        self.assertEqual(raised.exception.details["request_id"], "r1")

    def test_garbage_response_is_a_protocol_error(self) -> None:
        client = self._connect()
        with self.assertRaises(errors.AutomationOpError) as raised:
            client.call("garbage.op")
        self.assertEqual(raised.exception.code, errors.PROTOCOL_ERROR)
        self.assertFalse(raised.exception.retryable)

    def test_connection_drop_raises_app_shutting_down_and_disconnects(self) -> None:
        client = self._connect()
        with self.assertRaises(errors.AutomationOpError) as raised:
            client.call("drop.op")
        self.assertEqual(raised.exception.code, errors.APP_SHUTTING_DOWN)
        self.assertFalse(raised.exception.retryable)
        self.assertFalse(client.connected)
        with self.assertRaises(errors.AutomationOpError) as again:
            client.call("echo.op")
        self.assertEqual(again.exception.code, errors.APP_SHUTTING_DOWN)
        self.assertFalse(again.exception.retryable)

    # --------------------------------------------------------------- close

    def test_close_is_idempotent_and_context_manager_closes(self) -> None:
        with self._connect() as client:
            self.assertTrue(client.connected)
            client.call("echo.op")
        self.assertFalse(client.connected)
        client.close()
        client.close(quit_owned_instance=False)
        with self.assertRaises(errors.AutomationOpError) as raised:
            client.call("echo.op")
        self.assertEqual(raised.exception.code, errors.INTERNAL)
        self.assertNotIn("app.quit", self.server.ops())

    def test_unconnected_client_reports_internal(self) -> None:
        client = CorexClient()
        self.assertFalse(client.connected)
        self.assertIsNone(client.instance)
        with self.assertRaises(errors.AutomationOpError) as raised:
            client.call("echo.op")
        self.assertEqual(raised.exception.code, errors.INTERNAL)
        client.close()

    # -------------------------------------------------------------- launch

    def _owned_handle(
        self, *, mode: str = gate.MODE_PRIVATE, **record_overrides: Any
    ) -> tuple[launcher.CorexInstanceHandle, _FakeProcess, Path]:
        process = _FakeProcess()
        session_dir = Path(tempfile.mkdtemp(prefix="corex-client-test-"))
        self.addCleanup(shutil.rmtree, session_dir, True)
        handle = launcher.CorexInstanceHandle(
            record=self.server.record(mode=mode, **record_overrides),
            process=process,
            owned=True,
            session_state_dir=session_dir,
            log_path=session_dir / "corex-automation.log",
            env={gate.ENV_MODE: mode},
        )
        return handle, process, session_dir

    def _launch_visible(self) -> tuple[CorexClient, launcher.CorexInstanceHandle, _FakeProcess, Path, Any]:
        handle, process, session_dir = self._owned_handle(mode=gate.MODE_VISIBLE)
        remove_patch = patch.object(discovery, "remove_instance_file", return_value=True)
        remove_instance_file = remove_patch.start()
        self.addCleanup(remove_patch.stop)
        with patch.object(launcher, "launch_corex", return_value=handle):
            client = CorexClient.launch("auto")
        self.assertFalse(handle.private)
        return client, handle, process, session_dir, remove_instance_file

    def test_close_quits_a_clean_visible_instance_and_cleans_up_after_it_exits(self) -> None:
        client, handle, process, session_dir, remove_instance_file = self._launch_visible()

        def exit_like_corex() -> None:
            process.returncode = 0

        self.server.on_quit = exit_like_corex
        client.close()
        quits = self.server.requests_for("app.quit")
        self.assertEqual([request["params"] for request in quits], [{"discard_unsaved": False}])
        self.assertEqual(process.terminate_calls, 0, "a window that quit on its own is never terminated")
        self.assertFalse(handle.detached)
        self.assertTrue(handle.terminated)
        self.assertFalse(session_dir.exists())
        remove_instance_file.assert_called_once_with(INSTANCE_ID)
        self.assertIsNone(client.handle)

    def test_close_detaches_a_dirty_visible_instance_and_keeps_its_session_dir(self) -> None:
        client, handle, process, session_dir, remove_instance_file = self._launch_visible()
        self.server.quit_error_code = errors.PROJECT_DIRTY
        client.close()
        quits = self.server.requests_for("app.quit")
        self.assertEqual([request["params"] for request in quits], [{"discard_unsaved": False}])
        self.assertTrue(handle.detached)
        self.assertFalse(handle.terminated)
        self.assertTrue(handle.alive)
        self.assertEqual((process.terminate_calls, process.kill_calls), (0, 0))
        self.assertTrue(session_dir.is_dir(), "the user's window keeps its session state")
        remove_instance_file.assert_not_called()
        self.assertFalse(client.connected)
        self.assertIsNone(client.handle)
        client.close()  # idempotent: nothing more is sent or stopped
        self.assertEqual(len(self.server.requests_for("app.quit")), 1)
        self.assertEqual(process.terminate_calls, 0)

    def test_close_detaches_a_visible_instance_when_the_connection_is_gone(self) -> None:
        client, handle, process, session_dir, remove_instance_file = self._launch_visible()
        with self.assertRaises(errors.AutomationOpError):
            client.call("drop.op")
        self.assertFalse(client.connected)
        client.close()
        self.assertEqual(self.server.requests_for("app.quit"), [])
        self.assertTrue(handle.detached)
        self.assertEqual(process.terminate_calls, 0)
        self.assertTrue(session_dir.is_dir())
        remove_instance_file.assert_not_called()

    def test_close_cleans_up_a_visible_instance_the_user_already_closed(self) -> None:
        client, handle, process, session_dir, remove_instance_file = self._launch_visible()
        process.returncode = 0
        client.close()
        self.assertEqual(self.server.requests_for("app.quit"), [])
        self.assertFalse(handle.detached)
        self.assertEqual(process.terminate_calls, 0)
        self.assertFalse(session_dir.exists())
        remove_instance_file.assert_called_once_with(INSTANCE_ID)

    def test_close_stops_a_clean_visible_instance_that_lingers_after_quit(self) -> None:
        client, handle, process, session_dir, _remove_instance_file = self._launch_visible()
        with patch.object(client_module, "VISIBLE_EXIT_TIMEOUT_S", 0.01):
            client.close()
        self.assertEqual([request["params"] for request in self.server.requests_for("app.quit")], [{"discard_unsaved": False}])
        self.assertFalse(handle.detached)
        self.assertEqual(process.terminate_calls, 1, "it accepted a non-discarding quit, so nothing unsaved is lost")
        self.assertFalse(session_dir.exists())

    def test_launch_delegates_to_the_launcher_and_quits_the_owned_instance_on_close(self) -> None:
        handle, process, session_dir = self._owned_handle()
        with patch.object(launcher, "launch_corex", return_value=handle) as launch_corex, patch.object(
            discovery, "remove_instance_file", return_value=True
        ) as remove_instance_file:
            client = CorexClient.launch("private", headless=False, startup_timeout_s=12.5)
            launch_corex.assert_called_once_with("private", headless=False, startup_timeout_s=12.5)
            self.assertTrue(client.connected)
            self.assertIs(client.handle, handle)
            self.assertEqual(client.instance, handle.record)
            self.assertEqual(client.call("echo.op", {"x": 1}), {"echo": {"x": 1}})
            client.close()
        quits = self.server.requests_for("app.quit")
        self.assertEqual(len(quits), 1)
        self.assertEqual(quits[0]["params"], {"discard_unsaved": True})
        self.assertFalse(client.connected)
        self.assertIsNone(client.handle)
        self.assertEqual(process.terminate_calls, 1)
        self.assertTrue(handle.terminated)
        remove_instance_file.assert_called_once_with(INSTANCE_ID)
        self.assertFalse(session_dir.exists())
        client.close()
        self.assertEqual(len(self.server.requests_for("app.quit")), 1)
        self.assertEqual(process.terminate_calls, 1)

    def test_launch_close_without_quit_detaches_and_keeps_the_instance(self) -> None:
        handle, process, session_dir = self._owned_handle()
        with patch.object(launcher, "launch_corex", return_value=handle), patch.object(
            discovery, "remove_instance_file", return_value=True
        ):
            client = CorexClient.launch("private")
            client.close(quit_owned_instance=False)
            self.assertFalse(client.connected)
            self.assertIs(client.handle, handle)
            self.assertEqual(process.terminate_calls, 0)
            self.assertTrue(session_dir.exists())
            self.assertEqual(self.server.requests_for("app.quit"), [])
            client.close()
        self.assertIsNone(client.handle)
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(self.server.requests_for("app.quit"), [])
        self.assertFalse(session_dir.exists())

    def test_launch_attach_failure_terminates_the_owned_instance(self) -> None:
        handle, process, _session_dir = self._owned_handle(token="wrong")
        with patch.object(launcher, "launch_corex", return_value=handle), patch.object(
            discovery, "remove_instance_file", return_value=True
        ):
            with self.assertRaises(errors.AutomationOpError) as raised:
                CorexClient.launch("private")
        self.assertEqual(raised.exception.code, errors.AUTH_FAILED)
        self.assertEqual(process.terminate_calls, 1)
        self.assertTrue(handle.terminated)

    def test_launch_attached_instance_is_never_quit(self) -> None:
        handle = launcher.CorexInstanceHandle(record=self.server.record(), owned=False)
        with patch.object(launcher, "launch_corex", return_value=handle), patch.object(
            discovery, "remove_instance_file", return_value=True
        ) as remove_instance_file:
            with CorexClient.launch("attach") as client:
                self.assertIs(client.handle, handle)
                client.call("echo.op")
        self.assertIsNone(client.handle)
        self.assertEqual(self.server.requests_for("app.quit"), [])
        remove_instance_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
