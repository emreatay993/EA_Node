# Purpose: CorexClient facade for run.start / status / control plus run_and_wait / wait / stop sugar.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

from ea_node_editor.automation.protocol import DEFAULT_REQUEST_TIMEOUT_S

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient

DEFAULT_WAIT_TIMEOUT_S = 120.0
# The request timeout caps the server-side Deferred deadline, so wait calls send a
# request timeout a little longer than the wait itself.
WAIT_REQUEST_MARGIN_S = 5.0


def _compact(params: Mapping[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values so omitted keyword arguments never reach the closed param schemas."""
    return {key: value for key, value in params.items() if value is not None}


def _request_timeout(wait: bool, timeout_s: float | None) -> float:
    if not wait:
        return DEFAULT_REQUEST_TIMEOUT_S
    return float(timeout_s if timeout_s is not None else DEFAULT_WAIT_TIMEOUT_S) + WAIT_REQUEST_MARGIN_S


class RunApi:
    """Facade for run.start / status / control.

    Every method builds catalog params and returns ``client.call(op, params)``;
    the server validates, so the facade never re-implements rules.
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    def start(
        self,
        *,
        scope: str | None = None,
        node_ids: str | Iterable[str] | None = None,
        wait: bool = False,
        timeout_s: float | None = None,
        log_tail: int | None = None,
    ) -> dict[str, Any]:
        """Run the active workspace (or ``node_ids`` with scope=nodes); RUN_ACTIVE when a run is in flight."""
        ids = None if node_ids is None else ([node_ids] if isinstance(node_ids, str) else [str(value) for value in node_ids])
        params = _compact(
            {
                "scope": ("nodes" if ids is not None and scope is None else scope),
                "node_ids": ids,
                "wait": bool(wait),
                "timeout_s": None if timeout_s is None else float(timeout_s),
                "log_tail": None if log_tail is None else int(log_tail),
            }
        )
        return self._client.call("run.start", params, timeout_s=_request_timeout(bool(wait), timeout_s))

    def status(self, *, wait: bool = False, timeout_s: float | None = None, log_tail: int | None = None) -> dict[str, Any]:
        params = _compact(
            {
                "wait": bool(wait),
                "timeout_s": None if timeout_s is None else float(timeout_s),
                "log_tail": None if log_tail is None else int(log_tail),
            }
        )
        return self._client.call("run.status", params, timeout_s=_request_timeout(bool(wait), timeout_s))

    def control(self, action: str) -> dict[str, Any]:
        return self._client.call("run.control", {"action": str(action)})

    def stop(self) -> dict[str, Any]:
        """Stop the active run; ``applied`` is False (not an error) when nothing was running."""
        return self.control("stop")

    def pause(self) -> dict[str, Any]:
        return self.control("pause")

    def resume(self) -> dict[str, Any]:
        return self.control("resume")

    # ------------------------------------------------------------------- sugar

    def run_and_wait(
        self,
        timeout_s: float = DEFAULT_WAIT_TIMEOUT_S,
        *,
        node_ids: str | Iterable[str] | None = None,
        log_tail: int | None = None,
    ) -> dict[str, Any]:
        """``run.start(wait=true)``: returns the final status (``timed_out=True`` when the run outlived ``timeout_s``)."""
        return self.start(node_ids=node_ids, wait=True, timeout_s=float(timeout_s), log_tail=log_tail)

    def wait(self, timeout_s: float = DEFAULT_WAIT_TIMEOUT_S, *, log_tail: int | None = None) -> dict[str, Any]:
        """``run.status(wait=true)``: block until the instance is idle or ``timeout_s`` elapses."""
        return self.status(wait=True, timeout_s=float(timeout_s), log_tail=log_tail)


__all__ = ["DEFAULT_WAIT_TIMEOUT_S", "RunApi", "WAIT_REQUEST_MARGIN_S"]
