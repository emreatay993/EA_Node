# Purpose: Frozen NDJSON wire contract for the automation API: request/response/hello dataclasses and the frame codec.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_protocol.py
"""Automation wire protocol (version 1).

One JSON object per line (NDJSON) over a loopback TCP socket.

Handshake (first frame on every connection)::

    -> {"op": "hello", "token": "<token>", "client": "corex-client/0.1", "protocol": 1}
    <- {"ok": true, "result": {"app_version": "...", "protocol": 1,
                               "instance_id": "...", "pid": 1234, "mode": "visible"}}

Requests / responses::

    -> {"id": "r1", "op": "node.add", "params": {...}, "timeout_s": 30}
    <- {"id": "r1", "ok": true, "result": {...}}
    <- {"id": "r1", "ok": false, "error": {"code", "message", "hint", "details", "retryable"}}

The codec mirrors ``execution/protocol_codec.py``: frozen dataclasses plus
tolerant ``from_dict`` coercion, and an 8 MiB frame cap that both ends enforce.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ea_node_editor.automation.errors import (
    INTERNAL,
    PROTOCOL_ERROR,
    AutomationOpError,
)

PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 8 * 1024 * 1024
HELLO_OP = "hello"
DEFAULT_REQUEST_TIMEOUT_S = 30.0
MAX_REQUEST_TIMEOUT_S = 3600.0
CLIENT_NAME = "corex-client/0.1"

AutomationMode = str  # "visible" | "private"


class FrameError(ValueError):
    """Raised when a frame cannot be decoded or exceeds ``MAX_FRAME_BYTES``."""


@dataclass(frozen=True, slots=True)
class HelloRequest:
    token: str = field(repr=False)
    client: str = CLIENT_NAME
    protocol: int = PROTOCOL_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": HELLO_OP,
            "token": self.token,
            "client": self.client,
            "protocol": int(self.protocol),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HelloRequest":
        if str(payload.get("op") or "") != HELLO_OP:
            raise FrameError("first frame must be a hello request")
        return cls(
            token=str(payload.get("token") or ""),
            client=str(payload.get("client") or "unknown"),
            protocol=_int_value(payload.get("protocol"), PROTOCOL_VERSION),
        )


@dataclass(frozen=True, slots=True)
class HelloResponse:
    app_version: str
    instance_id: str
    pid: int
    mode: AutomationMode
    protocol: int = PROTOCOL_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_version": self.app_version,
            "protocol": int(self.protocol),
            "instance_id": self.instance_id,
            "pid": int(self.pid),
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HelloResponse":
        return cls(
            app_version=str(payload.get("app_version") or ""),
            instance_id=str(payload.get("instance_id") or ""),
            pid=_int_value(payload.get("pid"), 0),
            mode=str(payload.get("mode") or "visible"),
            protocol=_int_value(payload.get("protocol"), PROTOCOL_VERSION),
        )


@dataclass(frozen=True, slots=True)
class AutomationRequest:
    id: str
    op: str
    params: dict[str, Any] = field(default_factory=dict)
    timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "op": self.op,
            "params": dict(self.params),
            "timeout_s": float(self.timeout_s),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutomationRequest":
        request_id = str(payload.get("id") or "").strip()
        op = str(payload.get("op") or "").strip()
        if not op:
            raise FrameError("request is missing 'op'")
        params = payload.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, Mapping):
            raise FrameError("request 'params' must be an object")
        timeout = _float_value(payload.get("timeout_s"), DEFAULT_REQUEST_TIMEOUT_S)
        timeout = max(0.0, min(timeout, MAX_REQUEST_TIMEOUT_S))
        return cls(id=request_id, op=op, params=dict(params), timeout_s=timeout)


@dataclass(frozen=True, slots=True)
class AutomationResponse:
    id: str
    ok: bool
    result: dict[str, Any] = field(default_factory=dict)
    error: AutomationOpError | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.ok:
            return {"id": self.id, "ok": True, "result": dict(self.result)}
        error = self.error or AutomationOpError(INTERNAL, "unknown error")
        return {"id": self.id, "ok": False, "error": error.to_dict()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutomationResponse":
        request_id = str(payload.get("id") or "")
        if bool(payload.get("ok")):
            result = payload.get("result", {})
            if not isinstance(result, Mapping):
                raise FrameError("response 'result' must be an object")
            return cls(id=request_id, ok=True, result=dict(result))
        error_payload = payload.get("error")
        if not isinstance(error_payload, Mapping):
            error = AutomationOpError(PROTOCOL_ERROR, "response is missing an error envelope")
        else:
            error = AutomationOpError.from_dict(error_payload)
        return cls(id=request_id, ok=False, error=error)

    @classmethod
    def success(cls, request_id: str, result: Mapping[str, Any] | None) -> "AutomationResponse":
        return cls(id=request_id, ok=True, result=dict(result or {}))

    @classmethod
    def failure(cls, request_id: str, error: AutomationOpError) -> "AutomationResponse":
        return cls(id=request_id, ok=False, error=error)


def encode_frame(payload: Mapping[str, Any]) -> bytes:
    """Serialize one NDJSON frame (trailing newline included)."""
    text = json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":"), default=_json_default)
    data = text.encode("utf-8") + b"\n"
    if len(data) > MAX_FRAME_BYTES:
        raise FrameError(f"frame exceeds {MAX_FRAME_BYTES} bytes")
    return data


def decode_frame(line: bytes | str) -> dict[str, Any]:
    """Parse one NDJSON frame into a dict, enforcing the size cap."""
    raw = line.encode("utf-8") if isinstance(line, str) else bytes(line)
    if len(raw) > MAX_FRAME_BYTES:
        raise FrameError(f"frame exceeds {MAX_FRAME_BYTES} bytes")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameError(f"invalid JSON frame: {exc}") from None
    if not isinstance(payload, dict):
        raise FrameError("frame must be a JSON object")
    return payload


def _json_default(value: Any) -> Any:
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if hasattr(value, "__fspath__"):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return number


__all__ = [
    "AutomationMode",
    "AutomationRequest",
    "AutomationResponse",
    "CLIENT_NAME",
    "DEFAULT_REQUEST_TIMEOUT_S",
    "FrameError",
    "HELLO_OP",
    "HelloRequest",
    "HelloResponse",
    "MAX_FRAME_BYTES",
    "MAX_REQUEST_TIMEOUT_S",
    "PROTOCOL_VERSION",
    "decode_frame",
    "encode_frame",
]
