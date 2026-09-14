# Purpose: Host the production composer session in the real fullscreen QML overlay probes.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_passive_graph_surface_host.py
from pathlib import Path
import tempfile
import time

import numpy as np
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtTest import QTest

from ea_node_editor.addons.tabular_data.loader_cache_service import TabularLoaderCacheService
from ea_node_editor.ui.tabular_composer_session import TabularComposerSession
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider


class ProbeSession(TabularComposerSession):
    @pyqtSlot("QVariantMap")
    def request_preview(self, request):
        self.requests.append(dict(request))
        super().request_preview(request)


class ComposerOverlayBridge(QObject):
    content_fullscreen_changed = pyqtSignal()

    def __init__(self, *, array=False):
        super().__init__()
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        source = self.directory / ("array.npy" if array else "table.csv")
        if array:
            np.save(source, np.arange(120 * 80, dtype=np.float64).reshape(120, 80))
        else:
            source.write_text("station,temp,count\n" + "".join(f"S{i},{20+i/10},{i}\n" for i in range(120)), encoding="utf-8")
        self.props = {"path": str(source), "data_view": {"version": 1, "mode": "array" if array else "source"}}
        loader = TabularLoaderCacheService(cache_dir=self.directory / "cache")
        self.session = ProbeSession(self, read_properties=lambda: self.props, apply_properties=self._apply,
                                    project_context=lambda: (None, None),
                                    provider_factory=lambda **kw: TabularPreviewProvider(service_factory=lambda: loader, **kw),
                                    choose_export=lambda scope, kind, name: str(self.directory / name))
        self.session.requests = []
        self.close_calls = 0
        self._open = True
        self.session.changed.connect(self.content_fullscreen_changed)
        self.session.close_ready.connect(self._close)
        self.session.applied.connect(self._close)
        self.session.begin(self.props)

    def _apply(self, values):
        self.props.update(values)
        return True

    @pyqtProperty(QObject, constant=True)
    def tabular_composer(self): return self.session
    @pyqtProperty(bool, notify=content_fullscreen_changed)
    def open(self): return self._open
    @pyqtProperty(str, constant=True)
    def node_id(self): return "composer_probe"
    @pyqtProperty(str, constant=True)
    def workspace_id(self): return "workspace_probe"
    @pyqtProperty(str, constant=True)
    def content_kind(self): return "tabular"
    @pyqtProperty(str, constant=True)
    def title(self): return "Tabular Data Input"
    @pyqtProperty(str, constant=True)
    def last_error(self): return ""
    @pyqtProperty(QObject, constant=True)
    def web_surface_bridge(self): return None
    @pyqtProperty("QVariantMap", constant=True)
    def media_payload(self): return {}
    @pyqtProperty("QVariantMap", constant=True)
    def viewer_payload(self): return {}
    @pyqtProperty("QVariantMap", constant=True)
    def web_editor_payload(self): return {}
    @pyqtProperty("QVariantMap", constant=True)
    def web_page_payload(self): return {}
    @pyqtProperty("QVariantMap", constant=True)
    def plot_payload(self): return {}
    @pyqtProperty("QVariantMap", notify=content_fullscreen_changed)
    def tabular_payload(self): return {"properties": self.props, "preview": self.session.state["preview"]}

    @pyqtSlot()
    def request_close(self): self.session.request_close()

    def _close(self):
        self._open = False
        self.close_calls += 1
        self.content_fullscreen_changed.emit()

    def wait(self, app, *, exporting=False):
        end = time.monotonic() + 10
        key = "export_busy" if exporting else "busy"
        while self.session.state[key]:
            app.processEvents()
            if time.monotonic() > end:
                raise AssertionError(self.session.state)
            QTest.qWait(10)
        app.processEvents()

    def shutdown(self):
        self.session.shutdown()
        self.temporary.cleanup()
