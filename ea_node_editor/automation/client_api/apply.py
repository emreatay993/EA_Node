# Purpose: CorexClient facade for graph.apply: ApplyApi.apply, a BatchBuilder that hands out $ref tokens, and the ref() helper.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_apply.py
"""``graph.apply`` client sugar (stdlib only).

::

    batch = corex.apply.batch()
    start = batch.add("node.add", {"type_id": "passive.flowchart.start", "x": 0, "y": 0}, id="start")
    step = batch.add("node.add", {"type_id": "passive.flowchart.process", "x": 320, "y": 0})
    batch.add("edge.connect", {"source_node_id": start, "source_port": "right",
                               "target_node_id": step, "target_port": "left"})
    outcome = batch.run(label="Build flowchart")      # one undo step
    outcome["ids"]["start"]                            # real node id

``add`` returns the ``$id`` token for the op (auto ids ``op1``, ``op2``, ...
when none is given). ``ref(id, "shell_node_id")`` builds ``$id.field`` tokens
for nested result fields. ``$ref`` tokens are only substituted in each op's
declared ``ref_fields``; write ``$$`` for a literal leading dollar there.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.automation.client import CorexClient

APPLY_OP = "graph.apply"


def ref(batch_id: str, path: str = "") -> str:
    """Return the ``$id`` (or ``$id.path``) token that later batch ops use to reference an earlier result."""
    name = str(batch_id or "").strip().lstrip("$")
    if not name:
        raise ValueError("batch_id must be a non-empty string")
    suffix = str(path or "").strip().strip(".")
    return f"${name}.{suffix}" if suffix else f"${name}"


class BatchBuilder:
    """Collects ``{"id", "op", "params"}`` entries for one ``graph.apply`` call."""

    def __init__(self, client: "CorexClient | None" = None) -> None:
        self._client = client
        self.ops: list[dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self.ops)

    def add(self, op: str, params: Mapping[str, Any] | None = None, id: str | None = None) -> str:  # noqa: A002 - mirrors the wire key
        """Append an op and return its ``$id`` token (auto ``opN`` id when ``id`` is None)."""
        op_name = str(op or "").strip()
        if not op_name:
            raise ValueError("op must be a non-empty string")
        batch_id = str(id).strip() if id is not None else self._next_auto_id()
        if not batch_id:
            raise ValueError("id must be a non-empty string when given")
        self.ops.append({"id": batch_id, "op": op_name, "params": dict(params or {})})
        return ref(batch_id)

    def run(self, atomic: bool = True, label: str = "", *, timeout_s: float | None = None) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("BatchBuilder.run needs a client; build it with client.apply.batch() or BatchBuilder(client)")
        return ApplyApi(self._client).apply(self.ops, atomic=atomic, label=label, timeout_s=timeout_s)

    def _next_auto_id(self) -> str:
        """Position-based ``opN`` (N = 1-based index of the new op), bumped past any user-supplied clash."""
        used = {str(entry.get("id") or "") for entry in self.ops}
        counter = len(self.ops) + 1
        while f"op{counter}" in used:
            counter += 1
        return f"op{counter}"


class ApplyApi:
    """Facade for ``graph.apply``.

    ``atomic=True`` (default): any failing op rolls the whole batch back and
    the call raises ``AutomationOpError(APPLY_FAILED)`` whose ``details``
    carry ``failed_index``, ``failed_op``, the inner ``error`` envelope and
    the ``results`` rows so far. ``atomic=False``: earlier ops are kept and the
    call returns normally with ``failed_index`` >= 0 and the failing row's
    ``error`` in ``results``; it still raises when the very first op fails
    (nothing applied).
    """

    def __init__(self, client: "CorexClient") -> None:
        self._client = client

    def call(self, op: str, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        return self._client.call(op, params, **kwargs)

    def apply(
        self,
        ops: Sequence[Mapping[str, Any]],
        atomic: bool = True,
        label: str = "",
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"ops": [dict(entry) for entry in ops], "atomic": bool(atomic)}
        if label:
            params["label"] = str(label)
        if timeout_s is None:
            return self._client.call(APPLY_OP, params)
        return self._client.call(APPLY_OP, params, timeout_s=float(timeout_s))

    def batch(self) -> BatchBuilder:
        """Return a ``BatchBuilder`` bound to this client (``.run()`` calls ``apply``)."""
        return BatchBuilder(self._client)


__all__ = ["APPLY_OP", "ApplyApi", "BatchBuilder", "ref"]
