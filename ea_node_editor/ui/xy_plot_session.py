# Purpose: Own transient XY sessions, guarded range writeback and bounded inspection state.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_plot_session.py
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import threading
import uuid
from collections import OrderedDict
from collections.abc import Mapping
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.runtime_contracts import DataTree, Interval1D, PlotValue
from ea_node_editor.ui.support.node_presentation import build_property_input_override_state
from ea_node_editor.ui.support.solution_output_cache import current_output_value
from ea_node_editor.web_host.webengine import check_webengine_available
from ea_node_editor.web_host.xy_transport import XYPlotWorker, decode_request, normalized_axes, normalized_view_state

RANGE_KEYS = {"x": ("x_axis_interval", "x_datetime_start", "x_datetime_end"), "y": ("y_axis_interval",)}


def _single_plot(tree: object) -> PlotValue | None:
    if isinstance(tree, DataTree) and tree.item_count == 1:
        value = next(item for _path, items in tree.branches for item in items)
        return value if type(value) is PlotValue else None
    return None


class XYPlotSession(QObject):
    outbound = pyqtSignal(str)
    command = pyqtSignal(str)
    stop_worker = pyqtSignal()
    close_requested = pyqtSignal(name="closeRequested")
    close_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, plot: PlotValue, initial: dict, sync_message: str, parent: QObject) -> None:
        super().__init__(parent)
        self.plot = plot
        self.token = uuid.uuid4().hex
        self.retired = False
        self.closing = False
        self._pending = 0
        self._initial = {"session": self.token, "state": initial, "sync_message": sync_message}
        self._cancelled = threading.Event()
        self._assets = tempfile.TemporaryDirectory(prefix="corex-xy-")
        destination = Path(self._assets.name)
        for name in ("index.html", "host.js", "host.css", "gestures.js"):
            source = resources.files("ea_node_editor").joinpath("web_assets", "xy_host", name)
            with resources.as_file(source) as path:
                shutil.copyfile(path, destination / name)
        with resources.as_file(resources.files("xy").joinpath("static", "index.js")) as path:
            shutil.copyfile(path, destination / "xy-widget.js")
        self.asset_url = (destination / "index.html").as_uri()
        self.thread = QThread(parent)
        self.worker = XYPlotWorker(plot, self.token, self._cancelled)
        self.worker.moveToThread(self.thread)
        self.command.connect(self.worker.receive)
        self.stop_worker.connect(self.worker.stop)
        self.worker.outbound.connect(self._receive)
        self.worker.processed.connect(self._processed)
        self.thread.finished.connect(self.worker.deleteLater)
        self._deadline = QTimer(self)
        self._deadline.setSingleShot(True)
        self._deadline.setInterval(2000)
        self._deadline.timeout.connect(lambda: self.close_ready.emit({}))
        self.thread.start()

    @pyqtProperty(str, constant=True)
    def initial_json(self) -> str:
        return json.dumps(self._initial, allow_nan=False)

    @pyqtSlot(str)
    def post(self, raw: str) -> None:
        if self.retired:
            return
        try:
            request = decode_request(raw)
            if request.get("session") != self.token:
                return
            if self._pending >= 128:
                raise ValueError("Plot request queue is full")
            self._pending += 1
            self.command.emit(raw)
        except Exception as error:
            self.host_failed(str(error))

    @pyqtSlot(str)
    def host_failed(self, message: str) -> None:
        if not self.retired:
            self.failed.emit(message)

    @pyqtSlot()
    def request_close(self) -> None:
        if not self.retired and not self.closing:
            self.closing = True
            self._deadline.start()
            self.close_requested.emit()

    @pyqtSlot()
    def _processed(self) -> None:
        self._pending = max(0, self._pending - 1)

    @pyqtSlot(str)
    def _receive(self, raw: str) -> None:
        if self.retired:
            return
        event = json.loads(raw)
        if event.get("session") != self.token:
            return
        if event.get("kind") == "flushed" and self.closing:
            self._deadline.stop()
            self.close_ready.emit(event)
        elif event.get("kind") == "error":
            self.failed.emit(event.get("message", "Plot renderer failed"))
        else:
            self.outbound.emit(raw)

    def retire(self) -> None:
        if self.retired:
            return
        self.retired = True
        self._deadline.stop()
        self._cancelled.set()
        self.stop_worker.emit()
        # Keep QObjects alive until the worker drains; late replies are ignored.

    def dispose(self) -> None:
        self._assets.cleanup()
        self.thread.deleteLater()
        self.deleteLater()


class XYPlotSessionOwner(QObject):
    """Composition-owned authority; no scene payload contains a PlotValue."""
    def __init__(self, *, model_provider, registry_provider, active_workspace_id_provider,
                 scene_bridge, run_state, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.model_provider = model_provider
        self.registry_provider = registry_provider
        self.active_workspace_id_provider = active_workspace_id_provider
        self.scene = scene_bridge
        self.run_state = run_state
        self.active: XYPlotSession | None = None
        self.panel_id = ""
        self.cache: OrderedDict[tuple[str, str], dict] = OrderedDict()
        self.project = None
        self.retiring: list[XYPlotSession] = []

    def _node(self, plot: PlotValue):
        model = self.model_provider()
        workspace = model.project.workspaces.get(plot.provenance.workspace_id) if model else None
        return workspace, workspace.nodes.get(plot.provenance.node_id) if workspace else None

    def accepted(self, plot: PlotValue) -> bool:
        workspace, node = self._node(plot)
        if node is None or node.type_id != "plot.signal" or self.active_workspace_id_provider() != plot.provenance.workspace_id:
            return False
        current = _single_plot(current_output_value(self.run_state, plot.provenance.workspace_id, node.node_id, "image"))
        execution_workspace = getattr(self.run_state, "node_execution_workspace_id", "")
        if execution_workspace == plot.provenance.workspace_id and any(node.node_id in getattr(self.run_state, key, ())
            for key in ("running_node_ids", "failed_node_ids", "blocked_node_ids", "empty_node_ids")):
            return False
        if self.active is not None and self.active.plot.value_signature == plot.value_signature:
            if getattr(self.active, "authored_properties", node.properties) != node.properties:
                return False
        return current is not None and current.value_signature == plot.value_signature

    def axis_permissions(self, plot: PlotValue) -> dict[str, bool]:
        workspace, node = self._node(plot)
        if node is None or node.locked or not node.properties.get("sync_fullscreen_ranges", True):
            return {"x": False, "y": False}
        registry = self.registry_provider()
        spec = registry.resolve_spec(node.type_id, node.properties)
        ports = {port.key: port for port in effective_ports(node=node, spec=spec, workspace_nodes=workspace.nodes)
                 if port.direction == "in" and port.exposed}
        connected = {edge.target_port_key for edge in workspace.edges.values()
                     if edge.enabled and edge.target_node_id == node.node_id and edge.target_port_key in ports}
        return {axis: not any(build_property_input_override_state(
            node=node, property_key=key, resolved_input_ports=ports, enabled_input_port_keys=connected,
        )["overridden_by_input"] for key in keys) for axis, keys in RANGE_KEYS.items()}

    def observe_graph(self) -> None:
        model = self.model_provider()
        project = model.project if model else None
        if project is not self.project:
            self.cache.clear()
            self.project = project
            self.retire()
        for key, entry in list(self.cache.items()):
            workspace = project.workspaces.get(key[0]) if project else None
            node = workspace.nodes.get(key[1]) if workspace else None
            if node is None or node.properties != entry["properties"]:
                self.cache.pop(key, None)

    def open(self, plot: PlotValue, panel_id: str) -> XYPlotSession:
        self.observe_graph()
        if self.active is not None and self.panel_id == panel_id and self.active.plot.value_signature == plot.value_signature:
            return self.active
        self.retire()
        key = (plot.provenance.workspace_id, plot.provenance.node_id)
        entry = self.cache.get(key)
        initial = {"ranges": {axis: list(bounds) for axis, bounds in
                              {"x": plot.settings.x_bounds, "y": plot.settings.y_bounds}.items() if bounds}, "selection": None}
        if entry and entry["data"] == plot.data_signature and entry["render"] == plot.render_signature:
            if entry.get("expected_bounds") == {"x": plot.settings.x_bounds, "y": plot.settings.y_bounds}:
                entry["settings"] = plot.settings_signature
                entry.pop("expected_bounds", None)
            if entry.get("settings") == plot.settings_signature:
                initial = copy.deepcopy(entry["state"])
                self.cache.move_to_end(key)
            else:
                self.cache.pop(key, None)
        elif entry:
            self.cache.pop(key, None)
        allowed = self.axis_permissions(plot)
        unavailable = [axis.upper() for axis in ("x", "y") if not allowed[axis]]
        message = ("Range synchronization unavailable for " + ", ".join(unavailable) + ". Local exploration is available."
                   if unavailable else "Final ranges synchronize to Signal Plot when fullscreen closes.")
        self.active = XYPlotSession(plot, initial, message, self)
        _, producer = self._node(plot)
        self.active.authored_properties = copy.deepcopy(producer.properties) if producer else {}
        self.panel_id = panel_id
        return self.active

    def close_updates(self, session: XYPlotSession, event: dict) -> tuple[str, dict]:
        """Prepare one guarded batch; caller retires the surface before committing."""
        if self.active is not session or not self.accepted(session.plot):
            return "", {}
        plot = session.plot
        workspace, node = self._node(plot)
        try:
            state = normalized_view_state(event["state"])
            changed = normalized_axes(event.get("changed_axes", []))
            automatic = normalized_axes(event.get("automatic", [])) & changed
        except (KeyError, TypeError, ValueError):
            return "", {}
        permissions = self.axis_permissions(plot)
        updates: dict[str, Any] = {}
        for axis in changed:
            if not permissions[axis]:
                continue
            bounds = None if axis in automatic else state["ranges"].get(axis)
            if bounds is None and axis not in automatic:
                continue
            if axis == "y" and plot.settings.logarithmic_y_axis and bounds and bounds[0] <= 0:
                continue
            if axis == "x" and plot.signals[0].x_kind == "datetime":
                try:
                    start, end = ([datetime.fromtimestamp(n / 1000, timezone.utc).isoformat().replace("+00:00", "Z") for n in bounds]
                                  if bounds else ("", ""))
                except (ValueError, OverflowError, OSError):
                    continue
                updates.update(x_datetime_start=start, x_datetime_end=end, x_axis_interval=None)
            else:
                updates[f"{axis}_axis_interval"] = Interval1D(*bounds) if bounds else None
        updates = {key: value for key, value in updates.items() if node.properties.get(key) != value}
        key = (plot.provenance.workspace_id, plot.provenance.node_id)
        self.cache[key] = {"data": plot.data_signature, "render": plot.render_signature,
                           "settings": plot.settings_signature, "properties": copy.deepcopy(node.properties), "state": state}
        self.cache.move_to_end(key)
        while len(self.cache) > 16:
            self.cache.popitem(last=False)
        return node.node_id, updates

    def commit(self, plot: PlotValue, node_id: str, updates: dict) -> bool:
        if not updates or node_id != plot.provenance.node_id or not self.accepted(plot):
            return False
        _, node = self._node(plot)
        key = (plot.provenance.workspace_id, node_id)
        entry = self.cache.get(key)
        if entry is None or node.properties != entry["properties"]:
            self.cache.pop(key, None)
            return False
        permissions = self.axis_permissions(plot)
        updates = {key: value for key, value in updates.items()
                   if any(key in keys and permissions[axis] for axis, keys in RANGE_KEYS.items())}
        if not updates:
            return False
        if entry:
            entry["properties"] = {**copy.deepcopy(node.properties), **updates}
            bounds = {"x": plot.settings.x_bounds, "y": plot.settings.y_bounds}
            for axis in ("x", "y"):
                if f"{axis}_axis_interval" in updates:
                    interval = updates[f"{axis}_axis_interval"]
                    bounds[axis] = (interval.start, interval.end) if interval else None
            if {"x_datetime_start", "x_datetime_end"} & updates.keys():
                properties = entry["properties"]
                bounds["x"] = tuple(datetime.fromisoformat(properties[key].replace("Z", "+00:00")).timestamp() * 1000
                                    for key in ("x_datetime_start", "x_datetime_end")) if properties.get("x_datetime_start") else None
            entry["expected_bounds"] = bounds
        result = bool(self.scene.set_node_properties(node_id, updates))
        if not result or node.properties != (entry["properties"] if entry else node.properties):
            self.cache.pop(key, None)
        return result

    def retire(self) -> None:
        session = self.active
        self.active = None
        self.panel_id = ""
        if session:
            self.retiring.append(session)
            session.thread.finished.connect(lambda: self._dispose(session))
            session.retire()

    def _dispose(self, session: XYPlotSession) -> None:
        if session in self.retiring:
            self.retiring.remove(session)
            session.dispose()

    def shutdown(self) -> None:
        self.retire()
        self.cache.clear()
        for session in list(self.retiring):
            session.thread.wait()
            self._dispose(session)


def session_presentation(session: XYPlotSession) -> dict:
    available = check_webengine_available()
    return {"session_id": session.token, "asset_url": session.asset_url,
            "webengine_available": bool(available.available), "webengine_reason": str(available.reason or "")}
