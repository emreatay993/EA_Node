# Purpose: Stdlib-only CorexClient: connects (attach/auto/private), speaks the NDJSON protocol, and exposes per-domain facades.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_client.py
"""``CorexClient`` (T08 owns the core; domain facades come from T05-T07/T09/T11).

Usage::

    from ea_node_editor.automation.client import CorexClient

    with CorexClient.launch("private") as corex:          # or CorexClient.connect()
        start = corex.nodes.add("passive.flowchart.start", 0, 0, title="Start")
        step = corex.nodes.add("passive.flowchart.process", 320, 0, title="Mesh")
        corex.edges.connect(start["node_id"], "right", step["node_id"], "left")
        corex.capture.screenshot()

``call(op, params, timeout_s)`` is the low-level entry point every facade uses;
it raises ``AutomationOpError`` for ``ok=false`` responses. The client is
synchronous, thread-safe per instance (one request at a time), and depends only
on the standard library plus the sibling ``protocol`` / ``errors`` /
``discovery`` / ``launcher`` modules.

Lifecycle
---------
- ``connect()`` resolves a live instance through discovery and performs the
  ``hello`` handshake with the token from the discovery record.
- ``launch()`` delegates to ``launcher.launch_corex`` and remembers the handle.
  ``close()`` settles an *owned* spawned instance: a private one is quit with
  ``discard_unsaved=true`` and terminated; an auto-spawned visible window is
  asked to quit with ``discard_unsaved=false`` and is *detached* (left running
  for the user) when it refuses, e.g. with ``PROJECT_DIRTY``. Attached
  instances are never quit.
- Request ids are ``r1``, ``r2``, ... per client. A request that times out on
  the client side keeps the connection usable: its id is remembered and the
  late response is discarded when it eventually arrives.
- Losing the connection raises ``APP_SHUTTING_DOWN`` (``retryable=False``);
  later calls keep failing until a new client is connected.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation import discovery, launcher
from ea_node_editor.automation.client_api.annotations import AnnotationsApi
from ea_node_editor.automation.client_api.app import AppApi
from ea_node_editor.automation.client_api.apply import ApplyApi
from ea_node_editor.automation.client_api.capture import CaptureApi
from ea_node_editor.automation.client_api.catalog import CatalogApi
from ea_node_editor.automation.client_api.edges import EdgesApi
from ea_node_editor.automation.client_api.graph import GraphApi
from ea_node_editor.automation.client_api.nodes import NodesApi
from ea_node_editor.automation.client_api.project import ProjectApi
from ea_node_editor.automation.client_api.run import RunApi
from ea_node_editor.automation.client_api.structure import StructureApi
from ea_node_editor.automation.client_api.workspaces import WorkspacesApi
from ea_node_editor.automation.discovery import InstanceRecord
from ea_node_editor.automation.errors import (
    APP_SHUTTING_DOWN,
    INTERNAL,
    INVALID_PARAMS,
    NOT_FOUND,
    PROTOCOL_ERROR,
    TIMEOUT,
    AutomationOpError,
)
from ea_node_editor.automation.launcher import CorexInstanceHandle
from ea_node_editor.automation.protocol import (
    DEFAULT_REQUEST_TIMEOUT_S,
    MAX_FRAME_BYTES,
    AutomationRequest,
    AutomationResponse,
    FrameError,
    HelloRequest,
    HelloResponse,
    decode_frame,
    encode_frame,
)

LOOPBACK_HOST = "127.0.0.1"
DEFAULT_CONNECT_TIMEOUT_S = 10.0
# Extra time beyond the request's own ``timeout_s`` before the client stops waiting
# for a response frame (the server normally answers ``TIMEOUT`` itself first).
RESPONSE_TIMEOUT_MARGIN_S = 5.0
QUIT_TIMEOUT_S = 5.0
# How long close() waits for a visible instance that accepted app.quit to exit on its own.
VISIBLE_EXIT_TIMEOUT_S = 15.0
_RECV_CHUNK_BYTES = 64 * 1024
_RECONNECT_HINT = "Reconnect with CorexClient.connect() or start a new instance with CorexClient.launch()."
_RESPONSIVE_HINT = "Retry with a larger timeout_s, or check that the COREX instance is responsive."


class CorexClient:
    """Synchronous automation client (see module docstring)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hello: HelloResponse | None = None
        self._record: InstanceRecord | None = None
        self._handle: CorexInstanceHandle | None = None
        self._socket: socket.socket | None = None
        self._buffer = bytearray()
        self._request_counter = 0
        self._abandoned_ids: set[str] = set()
        self._disconnect_reason = ""
        self.app = AppApi(self)
        self.catalog = CatalogApi(self)
        self.graph = GraphApi(self)
        self.nodes = NodesApi(self)
        self.edges = EdgesApi(self)
        self.structure = StructureApi(self)
        self.annotations = AnnotationsApi(self)
        self.workspaces = WorkspacesApi(self)
        self.project = ProjectApi(self)
        self.run = RunApi(self)
        self.capture = CaptureApi(self)
        self.apply = ApplyApi(self)

    # ------------------------------------------------------------------ state

    @property
    def hello(self) -> HelloResponse | None:
        return self._hello

    @property
    def instance(self) -> InstanceRecord | None:
        """Discovery record of the instance this client attached to (``None`` before connect)."""
        return self._record

    @property
    def handle(self) -> CorexInstanceHandle | None:
        """Launcher handle when the client came from ``launch()``; ``None`` after close."""
        return self._handle

    @property
    def connected(self) -> bool:
        return self._socket is not None

    # ----------------------------------------------------------- constructors

    @classmethod
    def connect(cls, instance_id: str | None = None, *, timeout_s: float = DEFAULT_CONNECT_TIMEOUT_S) -> "CorexClient":
        """Attach to a live instance found through discovery (``instance_id`` or the preferred one)."""
        record = discovery.find_instance(instance_id)
        if record is None:
            wanted = f" '{instance_id}'" if instance_id else ""
            raise AutomationOpError(
                NOT_FOUND,
                f"No live COREX automation instance{wanted} was found.",
                hint="Start COREX with --automation, or spawn one with CorexClient.launch('private'), then retry.",
                details={"instance_id": str(instance_id or "")},
                retryable=False,
            )
        client = cls()
        client._attach(record, timeout_s=timeout_s)
        return client

    @classmethod
    def launch(cls, mode: str = "auto", *, headless: bool = True, **launch_kwargs: Any) -> "CorexClient":
        """Spawn or attach via ``launcher.launch_corex`` and connect; an owned instance is quit on ``close()``."""
        handle = launcher.launch_corex(mode, headless=headless, **launch_kwargs)
        client = cls()
        client._handle = handle
        try:
            client._attach(handle.record)
        except BaseException:
            client._handle = None
            handle.terminate()
            raise
        return client

    # ------------------------------------------------------------------ calls

    def call(
        self,
        op: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
    ) -> dict[str, Any]:
        """Send one request and return its ``result``; ``ok=false`` raises the decoded ``AutomationOpError``."""
        op_name = str(op or "").strip()
        if not op_name:
            raise ValueError("op must be a non-empty string")
        if params is not None and not isinstance(params, Mapping):
            raise TypeError(f"params must be a mapping or None, got {type(params).__name__}")
        wait_s = max(0.0, float(timeout_s))
        with self._lock:
            sock = self._connected_socket_locked()
            self._request_counter += 1
            request_id = f"r{self._request_counter}"
            request = AutomationRequest(id=request_id, op=op_name, params=dict(params or {}), timeout_s=wait_s)
            details: dict[str, Any] = {"op": op_name, "request_id": request_id}
            try:
                frame = encode_frame(request.to_dict())
            except (FrameError, TypeError, ValueError) as exc:
                raise AutomationOpError(
                    INVALID_PARAMS,
                    f"Request {op_name} could not be encoded: {exc}",
                    hint="Send JSON-serialisable params that fit in one 8 MiB frame.",
                    details=details,
                    retryable=False,
                ) from exc
            deadline = time.monotonic() + wait_s + RESPONSE_TIMEOUT_MARGIN_S
            self._send_frame_locked(sock, frame, wait_s + RESPONSE_TIMEOUT_MARGIN_S, details)
            try:
                response = self._read_response_locked(sock, deadline)
            except TimeoutError as exc:
                self._abandoned_ids.add(request_id)
                raise AutomationOpError(
                    TIMEOUT,
                    f"No response to {op_name} within {wait_s + RESPONSE_TIMEOUT_MARGIN_S:.1f} s.",
                    hint=_RESPONSIVE_HINT,
                    details={**details, "timeout_s": wait_s},
                ) from exc
            except FrameError as exc:
                raise AutomationOpError(
                    PROTOCOL_ERROR,
                    f"COREX sent an invalid response frame for {op_name}: {exc}",
                    details=details,
                    retryable=False,
                ) from exc
            except OSError as exc:
                self._drop_socket_locked(str(exc) or type(exc).__name__)
                raise AutomationOpError(
                    APP_SHUTTING_DOWN,
                    f"Connection to COREX was lost while waiting for {op_name}: {exc}",
                    hint=_RECONNECT_HINT,
                    details=details,
                    retryable=False,
                ) from exc
            if response is None:
                self._drop_socket_locked("COREX closed the connection")
                raise AutomationOpError(
                    APP_SHUTTING_DOWN,
                    f"COREX closed the connection while {op_name} was pending.",
                    hint=_RECONNECT_HINT,
                    details=details,
                    retryable=False,
                )
        if response.id != request_id:
            raise AutomationOpError(
                PROTOCOL_ERROR,
                f"Response id {response.id!r} does not match request id {request_id!r} for {op_name}.",
                details={**details, "response_id": response.id},
                retryable=False,
            )
        if not response.ok:
            raise response.error or AutomationOpError(
                PROTOCOL_ERROR, f"{op_name} failed without an error envelope.", details=details, retryable=False
            )
        return dict(response.result)

    def ping(self) -> dict[str, Any]:
        """Round-trip ``app.status`` as a cheap liveness check."""
        return self.call("app.status")

    def close(self, *, quit_owned_instance: bool = True) -> None:
        """Close the connection and settle an owned spawned instance; safe to call repeatedly.

        With ``quit_owned_instance=True`` (default) an instance this client spawned is settled:

        - *private*: ``app.quit {"discard_unsaved": true}`` (best effort), a short wait,
          then ``handle.terminate()`` -- the process is stopped and its session-state
          directory deleted once it has exited.
        - *visible* (spawned by ``auto``): ``app.quit {"discard_unsaved": false}``. When
          COREX accepts, the client waits for the process to exit and cleans up
          (discovery file, session-state directory). When it refuses -- ``PROJECT_DIRTY``
          or any other error, including a lost connection -- the window is *detached*:
          left running for the user, never terminated, its session-state directory
          kept, and ``handle.detached`` set to ``True``.

        ``quit_owned_instance=False`` detaches without asking: the spawned instance keeps
        running and stays reachable through ``handle`` (a later ``close()`` applies the
        policy above). Attached (not spawned) instances are never quit.
        """
        handle = self._handle
        owned = handle is not None and handle.owned
        settle = owned and quit_owned_instance
        private = handle is not None and handle.private
        quit_accepted = False
        if settle and self.connected and (private or handle.alive):
            try:
                self.call("app.quit", {"discard_unsaved": private}, timeout_s=QUIT_TIMEOUT_S)
                quit_accepted = True
            except Exception:  # noqa: BLE001 - any refusal (PROJECT_DIRTY, timeout, lost link) decides the policy below
                quit_accepted = False
        with self._lock:
            self._close_socket_locked()
            self._disconnect_reason = ""
        if handle is None or (owned and not quit_owned_instance):
            return
        self._handle = None
        if not owned:
            return
        if private:
            if quit_accepted:
                handle.wait(timeout_s=QUIT_TIMEOUT_S)
            handle.terminate()
            return
        if quit_accepted:
            # The window agreed to close without losing work; reap it, or stop it if it lingers.
            handle.wait(timeout_s=VISIBLE_EXIT_TIMEOUT_S)
            handle.terminate()
            return
        if handle.process is not None and not handle.alive:
            handle.terminate()  # the user already closed it: cleanup only
            return
        handle.detached = True

    def __enter__(self) -> "CorexClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -------------------------------------------------------------- internals

    def _attach(self, record: InstanceRecord, *, timeout_s: float = DEFAULT_CONNECT_TIMEOUT_S) -> None:
        timeout = max(0.01, float(timeout_s))
        details = {"instance_id": record.instance_id, "port": int(record.port)}
        try:
            sock = socket.create_connection((LOOPBACK_HOST, int(record.port)), timeout=timeout)
        except OSError as exc:
            # A connect-phase timeout is not an app hang (the kernel accepts even when the GUI
            # thread is stuck); on Windows it is how a closed loopback port is reported.
            reason = "timed out" if isinstance(exc, TimeoutError) else (str(exc) or type(exc).__name__)
            raise AutomationOpError(
                NOT_FOUND,
                f"COREX instance '{record.instance_id}' is not accepting connections on port {record.port} ({reason}).",
                hint="The instance probably exited; start COREX with --automation or use CorexClient.launch().",
                details={**details, "reason": reason},
                retryable=False,
            ) from exc
        with self._lock:
            self._close_socket_locked()
            try:
                hello = self._handshake_locked(sock, record, time.monotonic() + timeout)
            except BaseException:
                _close_quietly(sock)
                raise
            self._socket = sock
            self._record = record
            self._hello = hello
            self._disconnect_reason = ""

    def _handshake_locked(self, sock: socket.socket, record: InstanceRecord, deadline: float) -> HelloResponse:
        _set_nodelay(sock)
        details = {"instance_id": record.instance_id, "port": int(record.port)}
        try:
            sock.sendall(encode_frame(HelloRequest(token=record.token).to_dict()))
            line = self._read_line_locked(sock, deadline)
            if line is None:
                raise AutomationOpError(
                    PROTOCOL_ERROR,
                    "COREX closed the connection during the hello handshake.",
                    hint=_RECONNECT_HINT,
                    details=details,
                    retryable=False,
                )
            response = AutomationResponse.from_dict(decode_frame(line))
        except FrameError as exc:
            raise AutomationOpError(
                PROTOCOL_ERROR, f"Invalid hello response from COREX: {exc}", hint=_RECONNECT_HINT, details=details, retryable=False
            ) from exc
        except TimeoutError as exc:
            raise AutomationOpError(
                TIMEOUT, "Timed out waiting for the COREX hello response.", hint=_RESPONSIVE_HINT, details=details
            ) from exc
        except OSError as exc:
            raise AutomationOpError(
                APP_SHUTTING_DOWN,
                f"Connection to COREX was lost during the hello handshake: {exc}",
                hint=_RECONNECT_HINT,
                details=details,
                retryable=False,
            ) from exc
        if not response.ok:
            raise response.error or AutomationOpError(
                PROTOCOL_ERROR, "COREX rejected the hello without an error envelope.", details=details, retryable=False
            )
        return HelloResponse.from_dict(response.result)

    def _send_frame_locked(self, sock: socket.socket, frame: bytes, timeout_s: float, details: dict[str, Any]) -> None:
        """Write one request frame with a fresh send timeout.

        A previous read leaves the socket timeout at whatever was left of *its*
        deadline, so the timeout is reset for every send. A failed send may leave a
        partial frame on the wire, so the connection is dropped afterwards.
        """
        op_name = str(details.get("op", ""))
        try:
            sock.settimeout(max(0.01, float(timeout_s)))
            sock.sendall(frame)
        except TimeoutError as exc:
            self._drop_socket_locked("a request could not be sent in time")
            raise AutomationOpError(
                TIMEOUT,
                f"Sending {op_name} to COREX did not finish within {timeout_s:.1f} s; the connection was closed.",
                hint=_RECONNECT_HINT,
                details={**details, "timeout_s": float(timeout_s)},
                retryable=False,
            ) from exc
        except OSError as exc:
            self._drop_socket_locked(str(exc) or type(exc).__name__)
            raise AutomationOpError(
                APP_SHUTTING_DOWN,
                f"Connection to COREX was lost while sending {op_name}: {exc}",
                hint=_RECONNECT_HINT,
                details=details,
                retryable=False,
            ) from exc

    def _connected_socket_locked(self) -> socket.socket:
        sock = self._socket
        if sock is not None:
            return sock
        if self._disconnect_reason:
            raise AutomationOpError(
                APP_SHUTTING_DOWN,
                f"CorexClient is disconnected: {self._disconnect_reason}",
                hint=_RECONNECT_HINT,
                retryable=False,
            )
        raise AutomationOpError(
            INTERNAL,
            "CorexClient is not connected to a COREX instance.",
            hint="Create the client with CorexClient.connect() or CorexClient.launch() before calling ops.",
            retryable=False,
        )

    def _read_response_locked(self, sock: socket.socket, deadline: float) -> AutomationResponse | None:
        """Next response that is not a late answer to an abandoned (timed-out) request; ``None`` at EOF."""
        while True:
            line = self._read_line_locked(sock, deadline)
            if line is None:
                return None
            response = AutomationResponse.from_dict(decode_frame(line))
            if response.id in self._abandoned_ids:
                self._abandoned_ids.discard(response.id)
                continue
            return response

    def _read_line_locked(self, sock: socket.socket, deadline: float) -> bytes | None:
        """One non-empty NDJSON line without its terminator, ``None`` at EOF.

        Raises ``FrameError`` past ``MAX_FRAME_BYTES`` and ``TimeoutError`` past ``deadline``.
        """
        buffer = self._buffer
        while True:
            newline = buffer.find(b"\n")
            if newline >= 0:
                line = bytes(buffer[:newline])
                del buffer[: newline + 1]
                if line.endswith(b"\r"):
                    line = line[:-1]
                if not line.strip():
                    continue
                if len(line) > MAX_FRAME_BYTES:
                    buffer.clear()
                    raise FrameError(f"frame exceeds {MAX_FRAME_BYTES} bytes")
                return line
            if len(buffer) > MAX_FRAME_BYTES:
                buffer.clear()
                raise FrameError(f"frame exceeds {MAX_FRAME_BYTES} bytes")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("timed out waiting for a response frame")
            sock.settimeout(remaining)
            chunk = sock.recv(_RECV_CHUNK_BYTES)
            if not chunk:
                return None
            buffer.extend(chunk)

    def _drop_socket_locked(self, reason: str) -> None:
        self._close_socket_locked()
        self._disconnect_reason = reason

    def _close_socket_locked(self) -> None:
        sock = self._socket
        self._socket = None
        self._buffer.clear()
        self._abandoned_ids.clear()
        if sock is not None:
            _close_quietly(sock)


def _set_nodelay(sock: socket.socket) -> None:
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass


def _close_quietly(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


__all__ = [
    "CorexClient",
    "DEFAULT_CONNECT_TIMEOUT_S",
    "QUIT_TIMEOUT_S",
    "RESPONSE_TIMEOUT_MARGIN_S",
    "VISIBLE_EXIT_TIMEOUT_S",
]
