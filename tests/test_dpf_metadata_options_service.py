from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from ea_node_editor.ui_qml.dpf_metadata_options_service import (
    DpfMetadataOptionsCache,
    DpfMetadataOptionsService,
    load_dpf_metadata_options,
)


def _wait_for(condition, *, timeout_s: float = 5.0) -> bool:  # noqa: ANN001
    app = QApplication.instance()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def _options(_path: str) -> dict[str, tuple[str, ...]]:
    return {
        "result_name": ("displacement", "stress"),
        "set_ids": ("1", "2"),
        "time_values": ("0.0", "1.0"),
        "named_selection": ("ROTOR",),
    }


def test_metadata_request_is_async_cached_and_shared(tmp_path: Path) -> None:
    result_file = tmp_path / "result.rst"
    result_file.write_bytes(b"fixture")
    calls: list[str] = []

    def loader(path: str):  # noqa: ANN202
        calls.append(path)
        return _options(path)

    cache = DpfMetadataOptionsCache()
    service = DpfMetadataOptionsService(cache=cache, loader=loader)
    ready: list[tuple[str, str, int]] = []
    service.options_ready.connect(lambda ws, node, rev: ready.append((ws, node, rev)))
    try:
        first = service.request_options(
            workspace_id="ws", node_id="node-a", result_path=str(result_file)
        )
        second = service.request_options(
            workspace_id="ws", node_id="node-b", result_path=str(result_file)
        )
        assert first.state == second.state == "loading"
        assert _wait_for(lambda: len(ready) == 2)
        assert len(calls) == 1

        cached = service.request_options(
            workspace_id="ws", node_id="node-a", result_path=str(result_file)
        )
        assert cached.state == "ready"
        assert cached.entry is not None
        assert cached.entry.result_names == ("displacement", "stress")
        assert cached.entry.named_selections == ("ROTOR",)
    finally:
        service.shutdown()


def test_metadata_loader_accepts_numpy_like_arrays_without_boolean_coercion() -> None:
    class ArrayLike:
        def __init__(self, values):  # noqa: ANN001
            self._values = values

        def __iter__(self):
            return iter(self._values)

        def __bool__(self):
            raise ValueError("array truth value is ambiguous")

    metadata = SimpleNamespace(
        result_info=SimpleNamespace(available_results=[SimpleNamespace(name="stress")]),
        time_freq_support=SimpleNamespace(
            n_sets=2,
            time_frequencies=SimpleNamespace(data=ArrayLike([0.0, 1.0])),
        ),
        available_named_selections=ArrayLike(["ROTOR", "CASING"]),
    )
    dpf = SimpleNamespace(Model=lambda _path: SimpleNamespace(metadata=metadata))

    with patch(
        "ea_node_editor.execution.dpf_runtime.optional_imports.load_dpf_module",
        return_value=dpf,
    ):
        options = load_dpf_metadata_options("fixture.rst")

    assert options["time_values"] == ("0.0", "1.0")
    assert options["named_selection"] == ("ROTOR", "CASING")


def test_metadata_error_is_cached_and_exposed(tmp_path: Path) -> None:
    result_file = tmp_path / "broken.rst"
    result_file.write_bytes(b"fixture")
    service = DpfMetadataOptionsService(loader=lambda _path: (_ for _ in ()).throw(ValueError("bad rst")))
    ready: list[int] = []
    service.options_ready.connect(lambda _ws, _node, revision: ready.append(revision))
    try:
        assert service.request_options(
            workspace_id="ws", node_id="node", result_path=str(result_file)
        ).state == "loading"
        assert _wait_for(lambda: bool(ready))
        snapshot = service.request_options(
            workspace_id="ws", node_id="node", result_path=str(result_file)
        )
        assert snapshot.state == "error"
        assert "bad rst" in snapshot.error
    finally:
        service.shutdown()


def test_stale_completion_does_not_refresh_old_consumer(tmp_path: Path) -> None:
    result_file = tmp_path / "result.rst"
    result_file.write_bytes(b"fixture")
    service = DpfMetadataOptionsService(loader=_options)
    ready: list[tuple[str, str]] = []
    service.options_ready.connect(lambda ws, node, _revision: ready.append((ws, node)))
    try:
        consumer = ("ws", "node")
        service._latest_requests[consumer] = "new-request"  # noqa: SLF001
        service._in_flight["old-request"] = {consumer}  # noqa: SLF001
        service._on_finished(  # noqa: SLF001
            "old-request",
            "old-signature",
            str(result_file),
            _options(str(result_file)),
            "",
            False,
        )
        assert ready == []
    finally:
        service.shutdown()


def test_file_mtime_change_invalidates_cached_signature(tmp_path: Path) -> None:
    result_file = tmp_path / "result.rst"
    result_file.write_bytes(b"one")
    calls: list[str] = []

    def loader(path: str):  # noqa: ANN202
        calls.append(path)
        return _options(path)

    service = DpfMetadataOptionsService(loader=loader, freshness_interval_s=0.0)
    ready: list[int] = []
    service.options_ready.connect(lambda _ws, _node, revision: ready.append(revision))
    try:
        service.request_options(workspace_id="ws", node_id="node", result_path=str(result_file))
        assert _wait_for(lambda: len(ready) == 1)
        time.sleep(0.02)
        result_file.write_bytes(b"two")
        service.request_options(workspace_id="ws", node_id="node", result_path=str(result_file))
        assert _wait_for(lambda: len(ready) == 2)
        assert len(calls) == 2
    finally:
        service.shutdown()


def test_metadata_cache_is_lru_bounded() -> None:
    cache = DpfMetadataOptionsCache(limit=2)
    for signature in ("a", "b", "c"):
        cache.store(signature=signature, result_path=signature)
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("c") is not None


def test_cached_error_can_be_retried_after_explicit_invalidation(tmp_path: Path) -> None:
    result_file = tmp_path / "result.rst"
    result_file.write_bytes(b"fixture")
    calls = 0

    def loader(path: str):  # noqa: ANN202
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("temporary DPF failure")
        return _options(path)

    service = DpfMetadataOptionsService(loader=loader)
    ready: list[int] = []
    service.options_ready.connect(lambda _ws, _node, revision: ready.append(revision))
    try:
        service.request_options(workspace_id="ws", node_id="node", result_path=str(result_file))
        assert _wait_for(lambda: len(ready) == 1)
        assert service.request_options(
            workspace_id="ws", node_id="node", result_path=str(result_file)
        ).state == "error"

        service.invalidate_all()
        assert service.request_options(
            workspace_id="ws", node_id="node", result_path=str(result_file)
        ).state == "loading"
        assert _wait_for(lambda: len(ready) == 2)
        assert service.request_options(
            workspace_id="ws", node_id="node", result_path=str(result_file)
        ).state == "ready"
    finally:
        service.shutdown()
