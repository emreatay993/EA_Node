# Purpose: Qt-free loopback NDJSON server (AutomationServer) that authenticates with the instance token and hands requests to a dispatch callback.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_transport.py
"""Automation transport.

``AutomationServer`` runs entirely outside Qt: a listening ``socket`` on
``127.0.0.1`` (never ``0.0.0.0``), an accept thread, and one reader thread per
connection. The first frame must be a ``hello`` whose token matches via
``hmac.compare_digest``; anything else closes the socket with ``AUTH_FAILED``.
Each subsequent frame is decoded into ``AutomationRequest`` and passed to
``dispatch(request) -> AutomationResponse``; the callback blocks (the GUI bridge
resolves a ``Future``) and the response is written back on the same connection.
Frames over ``MAX_FRAME_BYTES`` -> ``PROTOCOL_ERROR`` and disconnect.

Guarantees beyond the wire contract:

- requests on one connection are handled strictly in order; connections are
  independent, so a slow dispatch, an oversized frame, or garbage on one
  connection never affects another;
- the reader never buffers more than ``MAX_FRAME_BYTES`` plus one receive chunk;
- exceptions raised by ``dispatch`` become ``INTERNAL`` failure frames and the
  connection stays usable;
- ``stop()`` closes the listener and every client socket so blocked reader
  threads wake up; ``running`` reflects the accept thread only.
"""

from __future__ import annotations

import dataclasses
import hmac
import ipaddress
import logging
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ea_node_editor.automation.errors import AUTH_FAILED, INTERNAL, PROTOCOL_ERROR, AutomationOpError
from ea_node_editor.automation.protocol import (
    MAX_FRAME_BYTES,
    PROTOCOL_VERSION,
    AutomationRequest,
    AutomationResponse,
    FrameError,
    HelloRequest,
    HelloResponse,
    decode_frame,
    encode_frame,
)

DispatchCallback = Callable[[AutomationRequest], AutomationResponse]

LOOPBACK_HOST = "127.0.0.1"

_LOGGER = logging.getLogger(__name__)
_RECV_CHUNK_BYTES = 64 * 1024
_ACCEPT_POLL_S = 0.25
_DRAIN_IDLE_S = 0.25
_DRAIN_LIMIT_BYTES = 2 * MAX_FRAME_BYTES
_HELLO_RESPONSE_ID = ""


@dataclass(slots=True)
class AutomationServer:
    token: str = field(repr=False)  # shared secret: never shown in repr/logs
    dispatch: DispatchCallback
    hello: HelloResponse
    port: int = 0
    host: str = LOOPBACK_HOST
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _listener: socket.socket | None = field(default=None, repr=False)
    _connections: dict[socket.socket, threading.Thread] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _connection_counter: int = field(default=0, repr=False)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def bound_address(self) -> tuple[str, int] | None:
        """``(host, port)`` the listener is bound to, or ``None`` when not listening."""
        listener = self._listener
        if listener is None:
            return None
        try:
            name = listener.getsockname()
        except OSError:
            return None
        return (str(name[0]), int(name[1]))

    def start(self) -> int:
        """Bind, start the accept thread, and return the bound port."""
        if self.running:
            return self.port
        if not self.token:
            raise ValueError("AutomationServer requires a non-empty token")
        _require_loopback(self.host)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self.host, int(self.port or 0)))
            listener.listen(16)
            listener.settimeout(_ACCEPT_POLL_S)
        except OSError:
            listener.close()
            raise
        self.port = int(listener.getsockname()[1])
        self._listener = listener
        self._stop_event.clear()
        thread = threading.Thread(target=self._accept_loop, name="corex-automation-accept", daemon=True)
        self._thread = thread
        thread.start()
        return self.port

    def stop(self, *, timeout_s: float = 2.0) -> None:
        """Close the listener and every connection, then join the threads (bounded by ``timeout_s``)."""
        self._stop_event.set()
        listener = self._listener
        self._listener = None
        if listener is not None:
            _close_quietly(listener)
        with self._lock:
            connections = dict(self._connections)
        for conn in connections:
            _close_quietly(conn)
        remaining = max(0.0, float(timeout_s))
        for thread in (self._thread, *connections.values()):
            if thread is None or thread is threading.current_thread():
                continue
            start = time.monotonic()
            thread.join(remaining)
            remaining = max(0.0, remaining - (time.monotonic() - start))

    # ------------------------------------------------------------------ accept

    def _accept_loop(self) -> None:
        listener = self._listener
        while not self._stop_event.is_set() and listener is not None:
            try:
                conn, addr = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if self._stop_event.is_set():
                    break
                _LOGGER.debug("automation accept failed", exc_info=True)
                self._stop_event.wait(_ACCEPT_POLL_S)
                continue
            if self._stop_event.is_set():
                _close_quietly(conn)
                break
            self._register_connection(conn, addr)

    def _register_connection(self, conn: socket.socket, addr: Any) -> None:
        try:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        with self._lock:
            self._connection_counter += 1
            name = f"corex-automation-conn-{self._connection_counter}"
            thread = threading.Thread(target=self._serve_connection, args=(conn, addr), name=name, daemon=True)
            self._connections[conn] = thread
        thread.start()

    def _unregister_connection(self, conn: socket.socket) -> None:
        with self._lock:
            self._connections.pop(conn, None)

    # -------------------------------------------------------------- connection

    def _serve_connection(self, conn: socket.socket, addr: Any) -> None:
        reader = _LineReader(conn)
        try:
            if not self._handshake(conn, reader, addr):
                return
            self._request_loop(conn, reader)
        except OSError:
            _LOGGER.debug("automation connection %s dropped", addr, exc_info=True)
        except Exception:  # pragma: no cover - defensive: a reader thread must never die noisily
            _LOGGER.exception("automation connection %s failed", addr)
        finally:
            self._unregister_connection(conn)
            _close_quietly(conn)

    def _handshake(self, conn: socket.socket, reader: _LineReader, addr: Any) -> bool:
        try:
            line = reader.readline()
        except FrameError:
            self._reject(conn, AUTH_FAILED, "first frame must be a hello request")
            return False
        if line is None:
            return False
        try:
            hello = HelloRequest.from_dict(decode_frame(line))
        except FrameError:
            self._reject(conn, AUTH_FAILED, "first frame must be a hello request")
            return False
        if not hmac.compare_digest(hello.token.encode("utf-8"), self.token.encode("utf-8")):
            _LOGGER.info("automation client %s rejected: bad token", addr)
            self._reject(conn, AUTH_FAILED, "automation token mismatch")
            return False
        if int(hello.protocol) != PROTOCOL_VERSION:
            self._reject(
                conn,
                PROTOCOL_ERROR,
                f"unsupported protocol version {hello.protocol}",
                details={"expected": PROTOCOL_VERSION, "received": int(hello.protocol)},
            )
            return False
        _send(conn, AutomationResponse.success(_HELLO_RESPONSE_ID, self.hello.to_dict()))
        _LOGGER.debug("automation client %s connected (%s)", addr, hello.client)
        return True

    def _request_loop(self, conn: socket.socket, reader: _LineReader) -> None:
        while not self._stop_event.is_set():
            try:
                line = reader.readline()
            except FrameError as exc:
                self._reject(conn, PROTOCOL_ERROR, str(exc))
                return
            if line is None:
                return
            try:
                payload = decode_frame(line)
            except FrameError as exc:
                self._reject(conn, PROTOCOL_ERROR, str(exc))
                return
            try:
                request = AutomationRequest.from_dict(payload)
            except FrameError as exc:
                self._reject(conn, PROTOCOL_ERROR, str(exc), request_id=_payload_id(payload))
                return
            response = self._dispatch_safely(request)
            self._send_response(conn, request, response)

    def _dispatch_safely(self, request: AutomationRequest) -> AutomationResponse:
        try:
            response = self.dispatch(request)
        except AutomationOpError as exc:
            return AutomationResponse.failure(request.id, exc)
        except Exception as exc:
            _LOGGER.exception("automation dispatch failed for op %s", request.op)
            return AutomationResponse.failure(
                request.id,
                AutomationOpError(
                    INTERNAL,
                    f"dispatch failed for {request.op}: {exc}",
                    details={"op": request.op, "exception": type(exc).__name__},
                ),
            )
        if not isinstance(response, AutomationResponse):
            return AutomationResponse.failure(
                request.id,
                AutomationOpError(INTERNAL, f"dispatch returned {type(response).__name__} instead of a response"),
            )
        if response.id != request.id:
            response = dataclasses.replace(response, id=request.id)
        return response

    def _send_response(self, conn: socket.socket, request: AutomationRequest, response: AutomationResponse) -> None:
        try:
            frame = encode_frame(response.to_dict())
        except (FrameError, TypeError, ValueError) as exc:
            fallback = AutomationResponse.failure(
                request.id,
                AutomationOpError(
                    INTERNAL,
                    f"response for {request.op} could not be encoded: {exc}",
                    hint="Narrow the request (fewer ids, smaller capture) so the result fits one frame.",
                    details={"op": request.op},
                ),
            )
            frame = encode_frame(fallback.to_dict())
        conn.sendall(frame)

    def _reject(
        self,
        conn: socket.socket,
        code: str,
        message: str,
        *,
        request_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        error = AutomationOpError(code, message, details=details)
        try:
            _send(conn, AutomationResponse.failure(request_id, error))
        except OSError:
            return
        _graceful_close(conn)


class _LineReader:
    """Bounded NDJSON line reader: never holds more than the frame cap plus one chunk."""

    __slots__ = ("_buffer", "_eof", "_sock")

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._buffer = bytearray()
        self._eof = False

    def readline(self) -> bytes | None:
        """Return the next non-empty line without its terminator, or ``None`` at EOF.

        Raises ``FrameError`` when the pending line exceeds ``MAX_FRAME_BYTES``.
        """
        while True:
            newline = self._buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self._buffer[:newline])
                del self._buffer[: newline + 1]
                if line.endswith(b"\r"):
                    line = line[:-1]
                if not line.strip():
                    continue
                if len(line) > MAX_FRAME_BYTES:
                    raise FrameError(f"frame exceeds {MAX_FRAME_BYTES} bytes")
                return line
            if len(self._buffer) > MAX_FRAME_BYTES:
                self._buffer.clear()
                raise FrameError(f"frame exceeds {MAX_FRAME_BYTES} bytes")
            if self._eof:
                return None
            chunk = self._sock.recv(_RECV_CHUNK_BYTES)
            if not chunk:
                self._eof = True
                if self._buffer.strip():
                    # Unterminated trailing data: treat as EOF; a client that
                    # half-sent a frame gets no response.
                    self._buffer.clear()
                continue
            self._buffer.extend(chunk)


def _require_loopback(host: str) -> None:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError(f"AutomationServer host must be a loopback IP address, got {host!r}") from None
    if not address.is_loopback or address.version != 4:
        raise ValueError(f"AutomationServer must bind an IPv4 loopback address, got {host!r}")


def _payload_id(payload: dict[str, Any]) -> str:
    value = payload.get("id")
    if value is None:
        return ""
    return str(value)


def _send(conn: socket.socket, response: AutomationResponse) -> None:
    conn.sendall(encode_frame(response.to_dict()))


def _graceful_close(conn: socket.socket) -> None:
    """Half-close, drain what the peer already sent, then close.

    Draining avoids a TCP reset that could discard the error frame we just
    wrote before the client reads it.
    """
    try:
        conn.shutdown(socket.SHUT_WR)
    except OSError:
        pass
    try:
        conn.settimeout(_DRAIN_IDLE_S)
        drained = 0
        while drained < _DRAIN_LIMIT_BYTES:
            chunk = conn.recv(_RECV_CHUNK_BYTES)
            if not chunk:
                break
            drained += len(chunk)
    except OSError:
        pass
    _close_quietly(conn)


def _close_quietly(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


__all__ = ["AutomationServer", "DispatchCallback", "LOOPBACK_HOST"]
