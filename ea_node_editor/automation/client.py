# Purpose: Stdlib-only CorexClient: connects (attach/auto/private), speaks the NDJSON protocol, and exposes per-domain facades.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""``CorexClient`` (T08 owner: implement core; domain facades by T05-T07/T09/T11).

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
on the standard library plus the sibling ``protocol``/``errors`` modules.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any

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
from ea_node_editor.automation.protocol import DEFAULT_REQUEST_TIMEOUT_S, HelloResponse


class CorexClient:
    """Synchronous automation client (see module docstring)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hello: HelloResponse | None = None
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

    @property
    def hello(self) -> HelloResponse | None:
        return self._hello

    @classmethod
    def connect(cls, *, instance_id: str | None = None, timeout_s: float = 10.0) -> "CorexClient":
        raise NotImplementedError("CorexClient.connect is implemented in T08")

    @classmethod
    def launch(cls, mode: str = "auto", *, headless: bool = True, **launch_kwargs: Any) -> "CorexClient":
        raise NotImplementedError("CorexClient.launch is implemented in T08")

    def call(self, op: str, params: Mapping[str, Any] | None = None, *, timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S) -> dict[str, Any]:
        raise NotImplementedError("CorexClient.call is implemented in T08")

    def close(self, *, quit_owned_instance: bool = True) -> None:
        raise NotImplementedError("CorexClient.close is implemented in T08")

    def __enter__(self) -> "CorexClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


__all__ = ["CorexClient"]
