# Purpose: Run bounded Mechanical lifecycle requests in one owned subprocess/thread.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_owner_protocol.py
from __future__ import annotations

import atexit
import ctypes
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Mapping
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from ea_node_editor.common.payload_tools import copy_json_safe

DEFAULT_OPERATION_TIMEOUT_SEC = 600.0
COOPERATIVE_CLOSE_TIMEOUT_SEC = 5.0
_MAX_BYTES = 1024 * 1024  # Control only; scientific/image values use COREX codecs.


class OwnerProtocolError(RuntimeError):
    pass


def _owner_python_executable() -> str:
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False) or not executable.is_file():
        raise RuntimeError(
            "Mechanical owner subprocess requires a Python module launcher; "
            "the packaged launcher route is not yet available"
        )
    return str(executable)


@dataclass(frozen=True, slots=True)
class OwnerIdentity:
    pid: int
    creation_time_ns: int
    transport_id: str


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("times", ctypes.c_longlong * 2),
        ("flags", wintypes.DWORD),
        ("working_set", ctypes.c_size_t * 2),
        ("active", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority", wintypes.DWORD),
        ("scheduling", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [("values", ctypes.c_ulonglong * 6)]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("basic", _BasicLimits),
        ("io", _IoCounters),
        ("memory", ctypes.c_size_t * 4),
    ]


class _WindowsKillJob:
    def __init__(self) -> None:
        if os.name != "nt":
            raise RuntimeError("Mechanical owner processes currently require Windows")
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _ExtendedLimits()
        limits.basic.flags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(
            self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process: subprocess.Popen[Any]) -> None:
        if not self.api.AssignProcessToJobObject(
            self.handle, wintypes.HANDLE(int(process._handle))
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def terminate(self) -> None:
        if self.handle and not self.api.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        handle, self.handle = getattr(self, "handle", None), None
        if handle:
            self.api.CloseHandle(handle)


def _creation_time_ns(process_handle: int | None = None) -> int:
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.GetCurrentProcess.restype = wintypes.HANDLE
    api.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    api.GetProcessTimes.restype = wintypes.BOOL
    handle = api.GetCurrentProcess() if process_handle is None else process_handle
    creation, exit_time, kernel, user = (wintypes.FILETIME() for _ in range(4))
    if not api.GetProcessTimes(
        wintypes.HANDLE(handle),
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    ticks = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
    return ticks * 100


def _creation_time_for_pid(pid: int) -> int:
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.restype = wintypes.HANDLE
    handle = api.OpenProcess(0x1000, False, int(pid))
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return _creation_time_ns(int(handle))
    finally:
        api.CloseHandle(handle)


def _request(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = copy_json_safe(
        payload, field_name="Mechanical owner request", max_encoded_bytes=_MAX_BYTES
    )
    required = {
        "request_id",
        "run_id",
        "session_id",
        "workspace_id",
        "expected_revision",
        "operation",
        "args",
    }
    if set(value) != required:
        raise ValueError("Mechanical owner request fields are invalid")
    for field in ("request_id", "run_id", "session_id", "workspace_id", "operation"):
        item = value[field]
        if not isinstance(item, str) or not item.strip() or len(item) > 512:
            raise ValueError(f"{field} must be a bounded non-empty string")
        value[field] = item.strip()
    revision = value["expected_revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise ValueError("expected_revision must be a non-negative integer")
    if not isinstance(value["args"], dict):
        raise ValueError("args must be a dictionary")
    return value


def _send(stream: Any, payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
    if len(encoded) > _MAX_BYTES:
        raise ValueError("Mechanical owner payload exceeds its bounded envelope")
    stream.write(encoded + b"\n")
    stream.flush()


def _receive(stream: Any) -> dict[str, Any]:
    encoded = stream.readline(_MAX_BYTES + 2)
    if not encoded:
        raise EOFError("Mechanical owner transport closed")
    if len(encoded) > _MAX_BYTES or not encoded.endswith(b"\n"):
        raise OwnerProtocolError("Mechanical owner payload framing is invalid")
    payload = json.loads(encoded)
    if not isinstance(payload, dict):
        raise OwnerProtocolError("Mechanical owner payload must be a dictionary")
    return copy_json_safe(
        payload, field_name="Mechanical owner payload", max_encoded_bytes=_MAX_BYTES
    )


def _child(port: int, token: str) -> int:
    connection = socket.create_connection(("127.0.0.1", port), timeout=10)
    stream = connection.makefile("rwb", buffering=0)
    _send(
        stream,
        {
            "type": "connected",
            "token": token,
            "pid": os.getpid(),
            "creation_time_ns": _creation_time_ns(),
        },
    )
    if _receive(stream) != {"type": "start", "token": token}:
        return 2
    # Native imports happen only after the parent assigns the kill-on-close job.
    from ea_node_editor.addons.mechanical.backend import execute_lifecycle_operation

    scope = None
    try:
        while True:
            request = _request(_receive(stream))
            try:
                request_scope = (
                    request["run_id"],
                    request["session_id"],
                    request["workspace_id"],
                )
                if request["operation"] != "close":
                    if scope is None:
                        scope = request_scope
                    elif scope != request_scope:
                        raise ValueError(
                            "Mechanical owner request identity does not match its session"
                        )
                result = execute_lifecycle_operation(
                    request["operation"], request["args"]
                )
                _send(
                    stream,
                    {"request_id": request["request_id"], "ok": True, "result": result},
                )
            except Exception as exc:  # noqa: BLE001
                _send(
                    stream,
                    {
                        "request_id": request["request_id"],
                        "ok": False,
                        "error": str(exc),
                    },
                )
            if request["operation"] == "close":
                return 0
    except (EOFError, OSError):
        return 0
    finally:
        stream.close()
        connection.close()


class MechanicalOwnerProcess:
    def __init__(self, *, start_timeout_sec: float = 10.0) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(start_timeout_sec)
        token = uuid.uuid4().hex
        flags = getattr(subprocess, "CREATE_SUSPENDED", 4) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        process = subprocess.Popen(
            [
                _owner_python_executable(),
                "-m",
                __name__,
                "--owner-child",
                str(listener.getsockname()[1]),
                token,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        job = _WindowsKillJob()
        connection = stream = None
        try:
            job.assign(process)
            status = ctypes.WinDLL("ntdll").NtResumeProcess(
                wintypes.HANDLE(int(process._handle))
            )
            if status:
                raise OSError(int(status), "NtResumeProcess failed")
            connection, _ = listener.accept()
            connection.settimeout(start_timeout_sec)
            stream = connection.makefile("rwb", buffering=0)
            ready = _receive(stream)
            owner_pid = int(ready["pid"])
            actual_creation = _creation_time_for_pid(owner_pid)
            self.identity = OwnerIdentity(
                owner_pid, int(ready["creation_time_ns"]), token
            )
            parent_pids = {parent.pid for parent in psutil.Process(owner_pid).parents()}
            if (
                ready.get("token") != token
                or process.pid not in parent_pids
                or self.identity.creation_time_ns != actual_creation
            ):
                raise OwnerProtocolError(
                    "Mechanical owner identity handshake failed: "
                    f"{self.identity!r} not owned by ({process.pid}, {actual_creation}, {token})"
                )
            _send(stream, {"type": "start", "token": token})
        except BaseException:
            job.terminate()
            process.wait(timeout=2)
            job.close()
            if stream is not None:
                stream.close()
            if connection is not None:
                connection.close()
            raise
        finally:
            listener.close()
        self._process, self._job = process, job
        self._connection, self._stream = connection, stream
        self._lock, self._close_lock = threading.Lock(), threading.Lock()
        self._closed, self._scope = False, None
        atexit.register(self.close)

    @property
    def alive(self) -> bool:
        if self._closed:
            return False
        try:
            process = psutil.Process(self.identity.pid)
            return (
                process.is_running()
                and process.status() != psutil.STATUS_ZOMBIE
                and _creation_time_for_pid(self.identity.pid)
                == self.identity.creation_time_ns
            )
        except (OSError, psutil.Error):
            return False

    def request(
        self,
        *,
        run_id: str,
        session_id: str,
        workspace_id: str,
        expected_revision: int,
        operation: str,
        args: Mapping[str, Any] | None = None,
        timeout_sec: float = DEFAULT_OPERATION_TIMEOUT_SEC,
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        payload = _request(
            {
                "request_id": request_id,
                "run_id": run_id,
                "session_id": session_id,
                "workspace_id": workspace_id,
                "expected_revision": expected_revision,
                "operation": operation,
                "args": dict(args or {}),
            }
        )
        with self._lock:
            if not self.alive:
                raise OwnerProtocolError("Mechanical owner process is closed")
            scope = (payload["run_id"], payload["session_id"], payload["workspace_id"])
            if self._scope is None:
                self._scope = scope
            elif self._scope != scope:
                raise OwnerProtocolError(
                    "Mechanical owner request identity does not match its session"
                )
            try:
                self._connection.settimeout(timeout_sec)
                _send(self._stream, payload)
                response = _receive(self._stream)
            except socket.timeout as exc:
                self.close()
                raise TimeoutError(
                    f"Mechanical owner operation {operation!r} timed out"
                ) from exc
            except (EOFError, OSError) as exc:
                raise OwnerProtocolError("Mechanical owner transport closed") from exc
        if response.get("request_id") != request_id:
            self.close()
            raise OwnerProtocolError("Mechanical owner response identity mismatch")
        if response.get("ok") is not True:
            raise OwnerProtocolError(
                str(response.get("error", "Mechanical owner operation failed"))
            )
        result = response.get("result")
        if not isinstance(result, dict):
            raise OwnerProtocolError("Mechanical owner result must be a dictionary")
        return result

    def close(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            if self.alive:
                try:
                    self._connection.settimeout(COOPERATIVE_CLOSE_TIMEOUT_SEC)
                    _send(
                        self._stream,
                        _request(
                            {
                                "request_id": uuid.uuid4().hex,
                                "run_id": "cleanup",
                                "session_id": "cleanup",
                                "workspace_id": "cleanup",
                                "expected_revision": 0,
                                "operation": "close",
                                "args": {},
                            }
                        ),
                    )
                    deadline = time.monotonic() + COOPERATIVE_CLOSE_TIMEOUT_SEC
                    while self.alive and time.monotonic() < deadline:
                        time.sleep(0.02)
                    if self.alive:
                        raise subprocess.TimeoutExpired(
                            "mechanical-owner", COOPERATIVE_CLOSE_TIMEOUT_SEC
                        )
                except (EOFError, OSError, socket.timeout, subprocess.TimeoutExpired):
                    self._job.terminate()
            if self.alive:
                raise RuntimeError("Mechanical owner process did not terminate")
            self._stream.close()
            self._connection.close()
            self._job.close()
            self._closed = True
            atexit.unregister(self.close)


def _main() -> int:
    return (
        _child(int(sys.argv[2]), sys.argv[3])
        if len(sys.argv) == 4 and sys.argv[1] == "--owner-child"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = [
    "COOPERATIVE_CLOSE_TIMEOUT_SEC",
    "DEFAULT_OPERATION_TIMEOUT_SEC",
    "MechanicalOwnerProcess",
    "OwnerIdentity",
    "OwnerProtocolError",
]
