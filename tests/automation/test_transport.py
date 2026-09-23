# Purpose: Socket-level tests for AutomationServer (hello/token gate, NDJSON framing, per-connection ordering, error frames, stop) and the env gate.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_transport.py
from __future__ import annotations

import importlib
import json
import os
import socket
import threading
import unittest
from typing import Any
from unittest.mock import patch

from ea_node_editor.automation import errors, gate, protocol
from ea_node_editor.automation import transport as transport_module
from ea_node_editor.automation.transport import LOOPBACK_HOST, AutomationServer

TOKEN = "t0ken-for-tests"
HELLO = protocol.HelloResponse(app_version="0.0-test", instance_id="inst-test", pid=4242, mode="private")
SOCKET_TIMEOUT_S = 10.0


def _echo_dispatch(request: protocol.AutomationRequest) -> protocol.AutomationResponse:
    return protocol.AutomationResponse.success(request.id, {"op": request.op, "params": request.params})


class _Client:
    """Minimal raw NDJSON client used to poke the server from the test thread."""

    def __init__(self, port: int) -> None:
        self.sock = socket.create_connection((LOOPBACK_HOST, port), timeout=SOCKET_TIMEOUT_S)
        self.reader = self.sock.makefile("rb")

    def send(self, payload: dict[str, Any]) -> None:
        self.sock.sendall(protocol.encode_frame(payload))

    def send_raw(self, data: bytes) -> None:
        self.sock.sendall(data)

    def recv(self) -> dict[str, Any] | None:
        try:
            line = self.reader.readline()
        except (ConnectionResetError, ConnectionAbortedError, socket.timeout):
            return None
        if not line:
            return None
        return json.loads(line)

    def hello(self, token: str = TOKEN, **overrides: Any) -> dict[str, Any] | None:
        payload = protocol.HelloRequest(token=token).to_dict()
        payload.update(overrides)
        self.send(payload)
        return self.recv()

    def request(self, request_id: str, op: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        self.send({"id": request_id, "op": op, "params": params or {}})
        return self.recv()

    def closed_by_peer(self) -> bool:
        """True when the server has closed the connection (EOF or reset)."""
        try:
            return self.reader.readline() == b""
        except (ConnectionResetError, ConnectionAbortedError):
            return True

    def close(self) -> None:
        try:
            self.reader.close()
        finally:
            self.sock.close()


class _ServerTestCase(unittest.TestCase):
    dispatch: Any = staticmethod(_echo_dispatch)

    def setUp(self) -> None:
        self.server = AutomationServer(token=TOKEN, dispatch=self.dispatch, hello=HELLO)
        self.port = self.server.start()
        self.addCleanup(self.server.stop, timeout_s=5.0)

    def client(self, *, handshake: bool = True) -> _Client:
        client = _Client(self.port)
        self.addCleanup(client.close)
        if handshake:
            reply = client.hello()
            assert reply is not None and reply["ok"], reply
        return client


class ServerLifecycleTests(_ServerTestCase):
    def test_start_binds_an_ephemeral_loopback_port(self) -> None:
        self.assertGreater(self.port, 0)
        self.assertEqual(self.server.port, self.port)
        self.assertTrue(self.server.running)
        self.assertEqual(self.server.bound_address, (LOOPBACK_HOST, self.port))
        client = self.client(handshake=False)
        self.assertEqual(client.sock.getpeername()[0], LOOPBACK_HOST)

    def test_start_is_idempotent_while_running(self) -> None:
        self.assertEqual(self.server.start(), self.port)

    def test_stop_unblocks_connections_and_clears_running(self) -> None:
        client = self.client()
        self.server.stop(timeout_s=5.0)
        self.assertFalse(self.server.running)
        self.assertIsNone(self.server.bound_address)
        self.assertTrue(client.closed_by_peer())
        with self.assertRaises(OSError):
            socket.create_connection((LOOPBACK_HOST, self.port), timeout=1.0)
        # Stopping twice is harmless.
        self.server.stop(timeout_s=1.0)

    def test_restart_after_stop_binds_again(self) -> None:
        self.server.stop(timeout_s=5.0)
        new_port = self.server.start()
        self.assertGreater(new_port, 0)
        self.assertTrue(self.server.running)
        self.assertTrue(self.client().request("r1", "a.b")["ok"])


class ServerConstructionTests(unittest.TestCase):
    def test_stop_before_start_is_a_noop(self) -> None:
        server = AutomationServer(token=TOKEN, dispatch=_echo_dispatch, hello=HELLO)
        self.assertFalse(server.running)
        server.stop()
        self.assertFalse(server.running)
        self.assertIsNone(server.bound_address)

    def test_refuses_non_loopback_host_and_empty_token(self) -> None:
        for host in ("0.0.0.0", "", "localhost", "192.168.1.10", "::1"):
            with self.subTest(host=host):
                server = AutomationServer(token=TOKEN, dispatch=_echo_dispatch, hello=HELLO, host=host)
                with self.assertRaises(ValueError):
                    server.start()
                self.assertFalse(server.running)
        server = AutomationServer(token="", dispatch=_echo_dispatch, hello=HELLO)
        with self.assertRaises(ValueError):
            server.start()

    def test_repr_never_shows_the_token(self) -> None:
        server = AutomationServer(token=TOKEN, dispatch=_echo_dispatch, hello=HELLO)
        self.assertNotIn(TOKEN, repr(server))
        self.assertIn("AutomationServer", repr(server))
        self.assertEqual(server.token, TOKEN)

    def test_fixed_port_is_honoured(self) -> None:
        probe = socket.socket()
        probe.bind((LOOPBACK_HOST, 0))
        free_port = probe.getsockname()[1]
        probe.close()
        server = AutomationServer(token=TOKEN, dispatch=_echo_dispatch, hello=HELLO, port=free_port)
        self.assertEqual(server.start(), free_port)
        server.stop(timeout_s=5.0)


class HandshakeTests(_ServerTestCase):
    def test_hello_round_trip_returns_instance_identity(self) -> None:
        client = self.client(handshake=False)
        reply = client.hello()
        self.assertEqual(reply, {"id": "", "ok": True, "result": HELLO.to_dict()})

    def test_wrong_token_is_rejected_and_closed(self) -> None:
        client = self.client(handshake=False)
        reply = client.hello(token="nope")
        assert reply is not None
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], errors.AUTH_FAILED)
        self.assertEqual(reply["error"]["hint"], errors.default_hint(errors.AUTH_FAILED))
        self.assertTrue(client.closed_by_peer())

    def test_missing_hello_is_rejected_and_closed(self) -> None:
        client = self.client(handshake=False)
        reply = client.request("r1", "node.add", {"type_id": "x"})
        assert reply is not None
        self.assertEqual(reply["error"]["code"], errors.AUTH_FAILED)
        self.assertTrue(client.closed_by_peer())

    def test_garbage_before_hello_is_auth_failed(self) -> None:
        client = self.client(handshake=False)
        client.send_raw(b"GET / HTTP/1.1\r\n")
        reply = client.recv()
        assert reply is not None
        self.assertEqual(reply["error"]["code"], errors.AUTH_FAILED)
        self.assertTrue(client.closed_by_peer())

    def test_protocol_version_mismatch_after_valid_token_is_protocol_error(self) -> None:
        client = self.client(handshake=False)
        reply = client.hello(protocol=99)
        assert reply is not None
        self.assertEqual(reply["error"]["code"], errors.PROTOCOL_ERROR)
        self.assertEqual(reply["error"]["details"], {"expected": protocol.PROTOCOL_VERSION, "received": 99})
        self.assertTrue(client.closed_by_peer())

    def test_client_disconnecting_before_hello_does_not_break_the_server(self) -> None:
        early = self.client(handshake=False)
        early.close()
        self.assertTrue(self.client().request("r1", "x.y")["ok"])

    def test_silent_connection_is_closed_after_the_handshake_timeout(self) -> None:
        # A loopback peer that never says hello must not park a reader thread forever.
        with patch.object(transport_module, "HANDSHAKE_TIMEOUT_S", 0.2):
            silent = self.client(handshake=False)
            self.assertTrue(silent.closed_by_peer())
            # Authenticated connections have no idle limit once the hello succeeded.
            client = self.client()
            threading.Event().wait(0.4)
            self.assertTrue(client.request("r1", "x.y")["ok"])


class RequestFramingTests(_ServerTestCase):
    def test_echo_round_trip(self) -> None:
        client = self.client()
        reply = client.request("r1", "node.add", {"type_id": "passive.flowchart.start", "x": 1.5})
        self.assertEqual(
            reply,
            {"id": "r1", "ok": True, "result": {"op": "node.add", "params": {"type_id": "passive.flowchart.start", "x": 1.5}}},
        )

    def test_pipelined_requests_keep_order_and_ids(self) -> None:
        client = self.client()
        ids = [f"r{i}" for i in range(12)]
        for request_id in ids:
            client.send({"id": request_id, "op": "ping", "params": {"n": request_id}})
        replies = [client.recv() for _ in ids]
        self.assertEqual([reply["id"] for reply in replies], ids)
        self.assertEqual([reply["result"]["params"]["n"] for reply in replies], ids)

    def test_blank_lines_and_crlf_are_tolerated(self) -> None:
        client = self.client()
        client.send_raw(b"\r\n\n" + json.dumps({"id": "r1", "op": "x.y"}).encode() + b"\r\n")
        reply = client.recv()
        self.assertEqual(reply["id"], "r1")
        self.assertTrue(reply["ok"])

    def test_malformed_json_is_protocol_error_and_disconnect(self) -> None:
        client = self.client()
        client.send_raw(b"{not json}\n")
        reply = client.recv()
        assert reply is not None
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], errors.PROTOCOL_ERROR)
        self.assertTrue(client.closed_by_peer())

    def test_non_object_frame_is_protocol_error(self) -> None:
        client = self.client()
        client.send_raw(b"[1, 2, 3]\n")
        reply = client.recv()
        assert reply is not None
        self.assertEqual(reply["error"]["code"], errors.PROTOCOL_ERROR)
        self.assertTrue(client.closed_by_peer())

    def test_request_without_op_echoes_id_in_protocol_error(self) -> None:
        client = self.client()
        client.send({"id": "r9", "params": {}})
        reply = client.recv()
        assert reply is not None
        self.assertEqual(reply["id"], "r9")
        self.assertEqual(reply["error"]["code"], errors.PROTOCOL_ERROR)
        self.assertTrue(client.closed_by_peer())

    def test_oversized_frame_is_protocol_error_and_disconnect(self) -> None:
        client = self.client()
        blob = b'{"id":"big","op":"x.y","params":{"blob":"' + b"a" * (protocol.MAX_FRAME_BYTES + 16) + b'"}}\n'
        try:
            client.send_raw(blob)
            client.sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass  # the server may already have closed its side; the error frame is still readable
        reply = client.recv()
        assert reply is not None, "expected a PROTOCOL_ERROR frame before disconnect"
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], errors.PROTOCOL_ERROR)
        self.assertTrue(client.closed_by_peer())

    def test_oversized_frame_on_one_connection_does_not_affect_another(self) -> None:
        healthy = self.client()
        rogue = self.client()
        try:
            rogue.send_raw(b"a" * (protocol.MAX_FRAME_BYTES + 1024))
            rogue.sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        rogue_reply = rogue.recv()
        assert rogue_reply is not None
        self.assertEqual(rogue_reply["error"]["code"], errors.PROTOCOL_ERROR)
        self.assertTrue(rogue.closed_by_peer())
        self.assertTrue(healthy.request("still", "alive")["ok"])
        self.assertTrue(self.client().request("fresh", "alive")["ok"])


class DispatchBehaviourTests(unittest.TestCase):
    def _server(self, dispatch: Any) -> tuple[AutomationServer, int]:
        server = AutomationServer(token=TOKEN, dispatch=dispatch, hello=HELLO)
        port = server.start()
        self.addCleanup(server.stop, timeout_s=5.0)
        return server, port

    def _client(self, port: int) -> _Client:
        client = _Client(port)
        self.addCleanup(client.close)
        reply = client.hello()
        assert reply is not None and reply["ok"], reply
        return client

    def test_dispatch_exception_becomes_internal_and_connection_survives(self) -> None:
        def dispatch(request: protocol.AutomationRequest) -> protocol.AutomationResponse:
            if request.op == "boom":
                raise RuntimeError("kaboom")
            return _echo_dispatch(request)

        _, port = self._server(dispatch)
        client = self._client(port)
        with self.assertLogs("ea_node_editor.automation.transport", level="ERROR"):
            reply = client.request("r1", "boom")
        assert reply is not None
        self.assertEqual(reply["id"], "r1")
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], errors.INTERNAL)
        self.assertEqual(reply["error"]["details"]["exception"], "RuntimeError")
        self.assertIn("kaboom", reply["error"]["message"])
        self.assertTrue(client.request("r2", "fine")["ok"])

    def test_dispatch_raising_automation_op_error_is_forwarded_verbatim(self) -> None:
        def dispatch(request: protocol.AutomationRequest) -> protocol.AutomationResponse:
            raise errors.not_found("Node", "node_9")

        _, port = self._server(dispatch)
        reply = self._client(port).request("r1", "node.get")
        assert reply is not None
        self.assertEqual(reply["error"]["code"], errors.NOT_FOUND)
        self.assertEqual(reply["error"]["details"], {"kind": "Node", "id": "node_9"})

    def test_dispatch_returning_wrong_type_or_wrong_id_is_normalised(self) -> None:
        def dispatch(request: protocol.AutomationRequest) -> Any:
            if request.op == "none":
                return None
            return protocol.AutomationResponse.success("some-other-id", {"ok": 1})

        _, port = self._server(dispatch)
        client = self._client(port)
        none_reply = client.request("r1", "none")
        self.assertEqual(none_reply["id"], "r1")
        self.assertEqual(none_reply["error"]["code"], errors.INTERNAL)
        other = client.request("r2", "other")
        self.assertEqual(other, {"id": "r2", "ok": True, "result": {"ok": 1}})

    def test_unencodable_or_oversized_result_becomes_internal_error(self) -> None:
        def dispatch(request: protocol.AutomationRequest) -> protocol.AutomationResponse:
            if request.op == "huge":
                return protocol.AutomationResponse.success(request.id, {"blob": "z" * (protocol.MAX_FRAME_BYTES + 1)})
            return protocol.AutomationResponse.success(request.id, {"bad": object()})

        _, port = self._server(dispatch)
        client = self._client(port)
        for op in ("huge", "unserialisable"):
            with self.subTest(op=op):
                reply = client.request("r-" + op, op)
                assert reply is not None
                self.assertEqual(reply["id"], "r-" + op)
                self.assertEqual(reply["error"]["code"], errors.INTERNAL)
        # The connection is still usable afterwards.
        self.assertEqual(client.request("r3", "unserialisable")["error"]["code"], errors.INTERNAL)

    def test_two_concurrent_clients_are_served_independently(self) -> None:
        release = threading.Event()
        entered = threading.Event()

        def dispatch(request: protocol.AutomationRequest) -> protocol.AutomationResponse:
            if request.op == "slow":
                entered.set()
                release.wait(SOCKET_TIMEOUT_S)
            return _echo_dispatch(request)

        _, port = self._server(dispatch)
        slow = self._client(port)
        fast = self._client(port)
        slow.send({"id": "s1", "op": "slow"})
        self.assertTrue(entered.wait(SOCKET_TIMEOUT_S))
        # The other connection is not blocked by the in-flight slow dispatch.
        self.assertEqual(fast.request("f1", "quick")["id"], "f1")
        self.assertEqual(fast.request("f2", "quick")["id"], "f2")
        release.set()
        self.assertEqual(slow.recv()["id"], "s1")

    def test_stop_while_dispatch_blocks_returns_within_timeout(self) -> None:
        release = threading.Event()
        entered = threading.Event()

        def dispatch(request: protocol.AutomationRequest) -> protocol.AutomationResponse:
            entered.set()
            release.wait(SOCKET_TIMEOUT_S)
            return _echo_dispatch(request)

        server, port = self._server(dispatch)
        self.addCleanup(release.set)
        client = self._client(port)
        client.send({"id": "s1", "op": "slow"})
        self.assertTrue(entered.wait(SOCKET_TIMEOUT_S))
        server.stop(timeout_s=0.5)
        self.assertFalse(server.running)
        release.set()
        # The client sees EOF or a reset; no hang.
        self.assertTrue(client.closed_by_peer())


class GateTests(unittest.TestCase):
    """The gate reads the environment once at import; exercise it via reload."""

    GATE_KEYS = (gate.ENV_ENABLED, gate.ENV_PORT, gate.ENV_INSTANCE_ID, gate.ENV_TOKEN, gate.ENV_MODE)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._reload_disabled()

    @classmethod
    def _reload_disabled(cls) -> None:
        with patch.dict(os.environ):
            for key in cls.GATE_KEYS:
                os.environ.pop(key, None)
            importlib.reload(gate)
        assert not gate.automation_enabled()

    def setUp(self) -> None:
        self.addCleanup(self._reload_disabled)

    def _reload_with(self, **env: str) -> gate.AutomationGate:
        with patch.dict(os.environ):
            for key in self.GATE_KEYS:
                os.environ.pop(key, None)
            os.environ.update(env)
            importlib.reload(gate)
            self.assertNotIn(gate.ENV_TOKEN, os.environ, "token must be popped from os.environ")
        return gate.automation_gate()

    def test_disabled_by_default_and_token_still_popped(self) -> None:
        result = self._reload_with(COREX_AUTOMATION_TOKEN="leaked?")
        self.assertFalse(result.enabled)
        self.assertFalse(gate.automation_enabled())
        self.assertEqual(result.token, "")
        self.assertEqual(result.port, 0)
        self.assertEqual(result.mode, gate.MODE_VISIBLE)
        self.assertFalse(result.private)

    def test_enabled_without_token_or_id_generates_them(self) -> None:
        result = self._reload_with(COREX_AUTOMATION_ENABLED="1")
        self.assertTrue(result.enabled)
        self.assertGreaterEqual(len(result.token), 32)
        self.assertEqual(len(result.instance_id), 12)
        int(result.instance_id, 16)
        self.assertEqual(result.port, 0)
        self.assertEqual(result.mode, gate.MODE_VISIBLE)

    def test_enabled_with_explicit_values(self) -> None:
        result = self._reload_with(
            COREX_AUTOMATION_ENABLED="1",
            COREX_AUTOMATION_PORT=" 4321 ",
            COREX_AUTOMATION_INSTANCE_ID="launcher-abc",
            COREX_AUTOMATION_TOKEN="shh",
            COREX_AUTOMATION_MODE="PRIVATE",
        )
        self.assertEqual(
            result,
            gate.AutomationGate(enabled=True, port=4321, instance_id="launcher-abc", token="shh", mode=gate.MODE_PRIVATE),
        )
        self.assertTrue(result.private)

    def test_invalid_port_and_mode_fall_back(self) -> None:
        for port in ("notaport", "70000", "-1", "80.5", ""):
            with self.subTest(port=port):
                result = self._reload_with(COREX_AUTOMATION_ENABLED="1", COREX_AUTOMATION_PORT=port, COREX_AUTOMATION_MODE="weird")
                self.assertEqual(result.port, 0)
                self.assertEqual(result.mode, gate.MODE_VISIBLE)

    def test_only_the_literal_one_enables(self) -> None:
        for value in ("0", "true", "yes", "", " "):
            with self.subTest(value=value):
                self.assertFalse(self._reload_with(COREX_AUTOMATION_ENABLED=value).enabled)

    def test_gate_is_captured_once_and_ignores_later_environment_changes(self) -> None:
        result = self._reload_with(COREX_AUTOMATION_ENABLED="1", COREX_AUTOMATION_TOKEN="first")
        with patch.dict(os.environ, {gate.ENV_ENABLED: "0", gate.ENV_TOKEN: "second"}):
            self.assertIs(gate.automation_gate(), result)
            self.assertEqual(gate.automation_gate().token, "first")
            self.assertTrue(gate.automation_enabled())

    def test_gate_repr_never_shows_the_token(self) -> None:
        result = self._reload_with(COREX_AUTOMATION_ENABLED="1", COREX_AUTOMATION_TOKEN="gate-secret-value")
        self.assertEqual(result.token, "gate-secret-value")
        self.assertNotIn("gate-secret-value", repr(result))
        self.assertIn("enabled=True", repr(result))

    def test_generators_produce_fresh_values(self) -> None:
        self.assertNotEqual(gate.generate_token(), gate.generate_token())
        self.assertNotEqual(gate.generate_instance_id(), gate.generate_instance_id())
        self.assertEqual(gate.AUTOMATION_MODES, (gate.MODE_VISIBLE, gate.MODE_PRIVATE))


if __name__ == "__main__":
    unittest.main()
