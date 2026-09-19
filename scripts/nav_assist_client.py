# Purpose: Provide a pinned, bounded TypeSafe HTTP transport and strict typed response validation.
# Map: subsystems/verification_testing_docs_hygiene.md
# Tests: tests/test_nav_assist.py
"""Development-only transport; no SDK, endpoint overrides, retries or response logging."""
from __future__ import annotations

import http.client
import json
import math
import os
import queue
import socket
import ssl
import threading
from time import monotonic
from typing import Any

MODEL = "jev-1.13.0"
MAX_REQUEST_BYTES = 200_000
MAX_RESPONSE_BYTES = 256_000
MAX_QUESTIONS = 32
_DNS_SLOTS = threading.BoundedSemaphore(4)
ERRORS = {
    "missing_key": "TYPESAFE_API_KEY is not set in this process.",
    "authentication": "TypeSafe authentication failed.",
    "rate_limited": "TypeSafe rate limit reached; try again later.",
    "timeout": "TypeSafe request timed out.",
    "service": "TypeSafe service is unavailable.",
    "invalid_response": "TypeSafe returned an invalid typed response.",
    "request_limit": "The bounded TypeSafe request budget was exceeded.",
    "unsafe_input": "Potential credential material was excluded from the request.",
}


class ServiceUnavailable(RuntimeError):
    def __init__(self, code: str):
        self.code = code if code in ERRORS else "service"
        super().__init__(ERRORS[self.code])


def _number(value: Any, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ServiceUnavailable("invalid_response")
    if not minimum <= value <= maximum or not math.isfinite(value):
        raise ServiceUnavailable("invalid_response")
    return float(value)


def validate_response(response: Any, questions: dict[str, dict]) -> dict:
    """Require exact question/option identities and finite, consistent typed answers.

    The service rounds probabilities and weighted scores independently to hundredths.
    Allow the accumulated half-unit rounding error, never NaN or out-of-range values.
    """
    if not isinstance(response, dict) or response.get("model") != MODEL:
        raise ServiceUnavailable("invalid_response")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ServiceUnavailable("invalid_response")
    for identity, question in questions.items():
        answer = answers[identity]
        if not isinstance(answer, dict) or answer.get("type") != question["type"]:
            raise ServiceUnavailable("invalid_response")
        if question["type"] == "noul":
            _number(answer.get("noul"), 0, 1)
            continue
        criteria = question["criteria"]
        keys = {str(index) for index in range(len(criteria))} if question["type"] == "score" else set(criteria)
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != keys:
            raise ServiceUnavailable("invalid_response")
        values = {key: _number(value, 0, 1) for key, value in probabilities.items()}
        if abs(sum(values.values()) - 1) > 0.005 * len(keys) + 1e-9:
            raise ServiceUnavailable("invalid_response")
        _number(answer.get("confidence"), 0, 1)
        if question["type"] == "score":
            score = _number(answer.get("score"), 0, len(criteria) - 1)
            if answer.get("legend") != {str(index): value for index, value in enumerate(criteria)}:
                raise ServiceUnavailable("invalid_response")
            tolerance = max(0.01, 0.005 * (1 + sum(range(len(criteria))))) + 1e-9
            if abs(score - sum(int(key) * value for key, value in values.items())) > tolerance:
                raise ServiceUnavailable("invalid_response")
        elif question["type"] == "choice":
            choice = answer.get("choice")
            if not isinstance(choice, str) or choice not in keys or values[choice] + 0.01 < max(values.values()):
                raise ServiceUnavailable("invalid_response")
        else:
            raise ServiceUnavailable("invalid_response")
    usage = response.get("usage")
    if not isinstance(usage, dict) or any(
        type(usage.get(key)) is not int or not 0 <= usage[key] <= 10_000_000
        for key in ("input_tokens", "output_tokens")
    ):
        raise ServiceUnavailable("invalid_response")
    # Return only the contract fields: unexpected service text is never displayed.
    return {"model": MODEL, "answers": answers, "usage": {key: usage[key] for key in ("input_tokens", "output_tokens")}}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _deadline_socket(address, timeout, source_address, *, deadline: float):
    """Keep OS DNS latency inside the request deadline without leaking worker waits.

    Only the resolver uses a daemon thread. It cannot send request bytes or retain a
    credential, and a late result is discarded. HTTPSConnection still owns TLS/SNI
    and certificate verification with the original pinned hostname.
    """
    resolved = queue.Queue(maxsize=1)
    slots = _DNS_SLOTS
    if not slots.acquire(timeout=max(0.001, deadline - monotonic())):
        raise TimeoutError

    def resolve():
        try:
            resolved.put(socket.getaddrinfo(address[0], address[1], type=socket.SOCK_STREAM))
        except OSError:
            resolved.put(None)
        finally:
            slots.release()

    try:
        threading.Thread(target=resolve, daemon=True, name="nav-assist-dns").start()
    except RuntimeError:
        slots.release()
        raise OSError("DNS worker unavailable") from None
    try:
        addresses = resolved.get(timeout=max(0.001, deadline - monotonic()))
    except queue.Empty:
        raise TimeoutError from None
    if addresses is None:
        raise OSError("DNS resolution failed")
    for family, kind, protocol, _, endpoint in addresses:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError
        wire = socket.socket(family, kind, protocol)
        try:
            wire.settimeout(remaining)
            if source_address is not None:
                wire.bind(source_address)
            wire.connect(endpoint)
            wire.settimeout(max(0.001, deadline - monotonic()))
            return wire
        except OSError:
            wire.close()
    if monotonic() >= deadline:
        raise TimeoutError
    raise OSError("HTTPS connection failed")


class TypeSafeClient:
    def __init__(self, *, timeout: float = 4.0):
        self._key = os.environ.get("TYPESAFE_API_KEY", "").strip()
        if not self._key:
            raise ServiceUnavailable("missing_key")
        if any(not 33 <= ord(char) <= 126 for char in self._key):
            raise ServiceUnavailable("authentication")
        if not 0 < timeout <= 15:
            raise ValueError("timeout must be in (0, 15]")
        self.timeout = timeout

    def evaluate(self, state: dict, questions: dict[str, dict]) -> dict:
        payload = json.dumps({"model": MODEL, "state": state, "questions": questions}, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if not 1 <= len(questions) <= MAX_QUESTIONS or len(payload) > MAX_REQUEST_BYTES:
            raise ServiceUnavailable("request_limit")
        # Do not echo the key, redirect it, or accept a caller-controlled endpoint.
        if self._key.encode("utf-8") in payload:
            raise ServiceUnavailable("unsafe_input")
        connection = http.client.HTTPSConnection("api.typesafe.ai", timeout=self.timeout, context=ssl.create_default_context())
        expired = threading.Event()
        wire = []
        deadline = monotonic() + self.timeout
        # HTTPConnection's socket factory seam preserves its standard HTTPS/TLS
        # implementation while preventing its synchronous resolver from hanging.
        connection._create_connection = lambda address, timeout, source_address=None: _deadline_socket(
            address, timeout, source_address, deadline=deadline)

        def abort():
            expired.set()
            active = wire[0] if wire else connection.sock
            if active is not None:
                try:
                    active.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                active.close()

        timer = threading.Timer(self.timeout, abort)
        timer.daemon = True
        timer.start()
        try:
            connection.connect()
            if expired.is_set():
                raise ServiceUnavailable("timeout")
            wire.append(connection.sock)
            connection.sock.settimeout(max(0.001, deadline - monotonic()))
            connection.request("POST", "/v1/systemone", body=payload, headers={
                "Authorization": "Bearer " + self._key, "Content-Type": "application/json", "Accept": "application/json",
            })
            response = connection.getresponse()
            if expired.is_set():
                raise ServiceUnavailable("timeout")
            if response.status != 200:
                raise ServiceUnavailable({401: "authentication", 403: "authentication", 429: "rate_limited", 529: "rate_limited"}.get(response.status, "service"))
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if expired.is_set():
                raise ServiceUnavailable("timeout")
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ServiceUnavailable("invalid_response")
            try:
                value = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
            except (ValueError, UnicodeError, RecursionError):
                raise ServiceUnavailable("invalid_response") from None
            return validate_response(value, questions)
        except (TimeoutError, socket.timeout):
            raise ServiceUnavailable("timeout") from None
        except (OSError, http.client.HTTPException):
            raise ServiceUnavailable("timeout" if expired.is_set() else "service") from None
        finally:
            timer.cancel()
            connection.close()
